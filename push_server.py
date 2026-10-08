#push_server.py
import asyncio
import logging
import aiosqlite
import os

from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from database import (
    DB_PATH,
    decode_bitmask,
    add_user_event,
    get_unread_events_count,
)
from push_transport import read_push_packet
# Загрузка настроек
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))
PUSH_SERVER_PORT = int(os.getenv("PUSH_SERVER_PORT", "23224"))

# ---------------- LOGGING ----------------

logger = logging.getLogger("PUSH")
logger.setLevel(logging.INFO)


def configure_logging():
    """Настраивает файловое и консольное логирование сервера."""
    if logger.handlers:
        return

    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
    )

    file_handler = TimedRotatingFileHandler(
        filename=logs_dir / "push.log",
        when="midnight",
        interval=1,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# ---------------- PARSERS ----------------

def extract_serial(data: bytes) -> str:
    for i in range(len(data) - 10):
        chunk = data[i:i+11]
        if len(chunk) == 11 and all(0x30 <= b <= 0x39 for b in chunk):
            try:
                return chunk.decode("ascii")
            except:
                continue
    return ""


def extract_bitmask(data: bytes) -> int:
    last_value = 0
    pos = 0

    while True:
        pos = data.find(b"\x06", pos)
        if pos == -1:
            break
        if pos + 5 <= len(data):
            value_bytes = data[pos + 1:pos + 5]
            last_value = int.from_bytes(value_bytes, "big")
        pos += 1

    return last_value


# ---------------- DB ----------------

async def get_chat_ids_for_meter(serial: str) -> list[int]:
    chat_ids = set()
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Проверяем одиночное подключение
        cur = await db.execute("SELECT chat_id FROM user_single_meters WHERE serial = ?", (serial,))
        for row in await cur.fetchall():
            chat_ids.add(row[0])

        # 2. Проверяем групповое подключение (разбиваем JOIN на два запроса для точности)
        cur = await db.execute("SELECT group_code FROM group_meters WHERE serial = ?", (serial,))
        groups = await cur.fetchall()
        
        for (g_code,) in groups:
            # Ищем пользователей в этой группе (игнорируем access_type, чтобы избежать проблем с NULL)
            cur = await db.execute("SELECT chat_id FROM users WHERE group_code = ?", (g_code,))
            for row in await cur.fetchall():
                chat_ids.add(row[0])
                
    return list(chat_ids)


# ---------------- CLIENT HANDLER ----------------

async def handle_client(reader, writer):
    """Принимает полные пакеты до закрытия соединения клиентом."""

    addr = writer.get_extra_info("peername")
    ip = addr[0] if addr else "unknown"
    packet_count = 0

    logger.info("TCP-подключение от %s", addr)

    try:
        while True:
            # Читаем ровно один полный пакет.
            # Следующие байты остаются в потоке для следующего чтения.
            raw_data = await read_push_packet(reader)

            if raw_data is None:
                logger.info(
                    "Клиент %s закрыл соединение. Получено пакетов: %s",
                    addr,
                    packet_count,
                )
                break

            packet_count += 1

            logger.info(
                "От %s получен полный пакет №%s, %s байт | %s",
                addr,
                packet_count,
                len(raw_data),
                raw_data.hex(),
            )

            serial = extract_serial(raw_data)

            if (
                not serial.isdigit()
                or len(serial) != 11
                or not serial.startswith(("971", "976"))
            ):
                logger.warning(
                    "Пакет от %s пропущен: "
                    "поддерживаемый номер счётчика не найден",
                    addr,
                )
                continue

            # Проверяем подписку на этот счётчик.
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT 1 FROM user_single_meters WHERE serial = ?",
                    (serial,),
                )
                registered = await cursor.fetchone()

                if not registered:
                    cursor = await db.execute(
                        "SELECT 1 FROM group_meters WHERE serial = ?",
                        (serial,),
                    )
                    registered = await cursor.fetchone()

            if not registered:
                logger.info(
                    "Счётчик %s: подписок нет, пакет пропущен",
                    serial,
                )
                continue

            # Разбор маски пока прежний.
            # Следующим шагом заменим его разбором объектов DLMS.
            bitmask = extract_bitmask(raw_data)

            logger.info(
                "Счётчик %s | предполагаемая маска: 0x%X",
                serial,
                bitmask,
            )

            if bitmask == 0:
                logger.info(
                    "Счётчик %s: нулевая маска, "
                    "уведомление не создаём",
                    serial,
                )
                continue

            event_time = datetime.now(timezone.utc).isoformat()
            chat_ids = await get_chat_ids_for_meter(serial)

            if not chat_ids:
                logger.warning(
                    "Счётчик %s зарегистрирован, "
                    "но получатели не найдены",
                    serial,
                )
                continue

            for chat_id in chat_ids:
                try:
                    await add_user_event(
                        chat_id,
                        event_time,
                        serial,
                        ip,
                        bitmask,
                        raw_data.hex(),
                    )

                    logger.info(
                        "Счётчик %s: событие записано "
                        "в очередь для чата %s",
                        serial,
                        chat_id,
                    )

                except Exception:
                    logger.exception(
                        "Не удалось записать событие "
                        "счётчика %s для чата %s",
                        serial,
                        chat_id,
                    )

    except asyncio.TimeoutError:
        logger.warning(
            "Соединение %s: истекло время ожидания "
            "полного пакета. Получено пакетов: %s",
            addr,
            packet_count,
        )

    except ValueError as error:
        logger.warning(
            "Соединение %s: некорректный пакет — %s",
            addr,
            error,
        )

    except (ConnectionError, OSError) as error:
        logger.warning(
            "Соединение %s: сетевая ошибка — %s",
            addr,
            error,
        )

    except Exception:
        logger.exception(
            "Ошибка обработки соединения %s",
            addr,
        )

    finally:
        # Закрываем соединение и ограничиваем ожидание закрытия.
        try:
            writer.close()
            await asyncio.wait_for(
                writer.wait_closed(),
                timeout=5,
            )
        except asyncio.TimeoutError:
            writer.transport.abort()
            logger.debug(
                "Соединение %s закрыто принудительно "
                "после тайм-аута",
                addr,
            )
        except (ConnectionError, OSError):
            logger.debug(
                "Соединение %s уже оборвано клиентом",
                addr,
            )


# ---------------- SERVER ----------------

async def start_server():
    configure_logging()
    server = await asyncio.start_server(
        handle_client,
        "0.0.0.0",
        PUSH_SERVER_PORT
    )
    
    logger.info(f"PUSH server started on port {PUSH_SERVER_PORT}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(start_server())
