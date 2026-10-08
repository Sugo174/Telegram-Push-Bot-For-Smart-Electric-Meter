"""
Приём полных DLMS Wrapper-пакетов из TCP-соединения.

TCP передаёт поток байтов: одно сообщение может прийти частями,
а несколько сообщений — вместе. Границы определяем по заголовку.
"""

import asyncio


# =============================================================================
# 1. Настройки приёма
# =============================================================================

WRAPPER_HEADER_SIZE = 8

# Время ожидания заголовка или оставшейся части пакета.
# Это срок сетевого ожидания, а не интервал отправки счётчика.
READ_TIMEOUT_SECONDS = 60


# =============================================================================
# 2. Чтение одного пакета
# =============================================================================

async def read_push_packet(
    reader: asyncio.StreamReader,
    timeout: float = READ_TIMEOUT_SECONDS,
) -> bytes | None:
    """Читает один полный пакет из TCP-потока.

    Args:
        reader: Входящий поток подключённого клиента.
        timeout: Допустимое ожидание каждой стадии чтения в секундах.

    Returns:
        Заголовок и тело пакета. None, если клиент закрыл соединение
        между пакетами.

    Raises:
        asyncio.TimeoutError: Клиент не передал данные вовремя.
        ValueError: Заголовок неверный или пакет передан не полностью.
        OSError: Произошла ошибка сетевого соединения.
    """

    try:
        header = await asyncio.wait_for(
            reader.readexactly(WRAPPER_HEADER_SIZE),
            timeout=timeout,
        )
    except asyncio.IncompleteReadError as error:
        if not error.partial:
            # Обычное закрытие соединения между сообщениями.
            return None

        raise ValueError(
            "Соединение закрыто посреди заголовка: "
            f"получено {len(error.partial)} из "
            f"{WRAPPER_HEADER_SIZE} байт."
        ) from error

    version = int.from_bytes(header[0:2], byteorder="big")

    if version != 1:
        raise ValueError(
            f"Неподдерживаемая версия Wrapper: {version}."
        )

    # Последние два байта заголовка задают длину тела,
    # без учёта восьми байт самого заголовка.
    payload_size = int.from_bytes(header[6:8], byteorder="big")

    if payload_size == 0:
        raise ValueError("Получен Wrapper-пакет с пустым телом.")

    try:
        payload = await asyncio.wait_for(
            reader.readexactly(payload_size),
            timeout=timeout,
        )
    except asyncio.IncompleteReadError as error:
        raise ValueError(
            "Соединение закрыто посреди тела пакета: "
            f"получено {len(error.partial)} из "
            f"{payload_size} байт."
        ) from error

    return header + payload