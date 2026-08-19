#push_server.py
import asyncio
import logging
import aiosqlite
import os

from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler

from database import (
    decode_bitmask,
    add_user_event,
    get_unread_events_count
)
# Загрузка настроек
from dotenv import load_dotenv
load_dotenv()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))
DB_PATH = os.path.abspath("emis_events.db")

# ---------------- LOGGING ----------------

os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("PUSH")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("[%(asctime)s] %(levelname)s:%(name)s: %(message)s")

file_handler = TimedRotatingFileHandler(
    filename="logs/push.log",
    when="midnight",
    interval=1,
    encoding="utf-8"
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
    addr = writer.get_extra_info("peername")
    ip = addr[0] if addr else "unknown"

    try:
        raw_data = await asyncio.wait_for(reader.read(4096), timeout=10)
        if not raw_data:
            return

        # Фильтрация мусора
        if raw_data.startswith((b"GET ", b"POST ", b"HTTP")):
            return

        serial = extract_serial(raw_data)
        if not serial.isdigit() or len(serial) != 11:
            return

        if not (serial.startswith("971") or serial.startswith("976")):
            return

        if serial.startswith("000") or serial == "19700101000":
            return

        # Проверка авторизации
        async with aiosqlite.connect("emis_events.db") as db:
            cursor = await db.execute(
                "SELECT 1 FROM user_single_meters WHERE serial = ?",
                (serial,)
            )
            if not await cursor.fetchone():
                cursor = await db.execute(
                    "SELECT 1 FROM group_meters WHERE serial = ?",
                    (serial,)
                )
                if not await cursor.fetchone():
                    return

        if b"\x06" not in raw_data:
            return

        bitmask = extract_bitmask(raw_data)
        if bitmask == 0:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logger.info(f"[{timestamp}] От IP {ip} | Счётчик №{serial} | Пакет: {raw_data.hex()}")

        events = await decode_bitmask(bitmask)
        event_time = datetime.now(timezone.utc).isoformat()

        chat_ids = await get_chat_ids_for_meter(serial)

        chat_ids = await get_chat_ids_for_meter(serial)

        for chat_id in chat_ids:

            try:
                await add_user_event(chat_id, event_time, serial, ip, bitmask, raw_data.hex())
      
            except Exception as e:
                logger.error(f"❌ Ошибка обработки для чата {chat_id}: {e}")

    except Exception as e:
        # Игнорируем сетевой шум (таймауты, обрывы, сканеры)
        if not isinstance(e, (asyncio.TimeoutError, ConnectionResetError, OSError)):
            logger.error(f"❌ Ошибка обработки {ip}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


# ---------------- SERVER ----------------

async def start_server():
    server = await asyncio.start_server(
        handle_client,
        "0.0.0.0",
        23224
    )

    logger.info("PUSH server started on port 23224")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(start_server())
