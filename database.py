# database.py
import aiosqlite

DB_PATH = "emis_events.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Включаем WAL-режим для параллельного доступа
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        # Таблица событий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_bits (
                bit_number INTEGER PRIMARY KEY,
                description TEXT NOT NULL
            )
        """)
        # Таблица настроек
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

async def seed_data():
    data = [
        (0, "Событие в журнале самодиагностики"),
        (1, "Перерыв питания"),
        (2, "Событие в журнале параметров качества сети"),
        (3, "Воздействие магнитного поля"),
        (4, "Вскрытие крышки отсека зажимов"),
        (5, "Вскрытие корпуса"),
        (6, "Превышение лимита активной мощности"),
        (7, "Срабатывание реле по максимальному току"),
        (8, "Срабатывание реле по магнитному полю"),
        (9, "Срабатывание реле по максимальному напряжению"),
        (10, "Срабатывание реле по небалансу токов"),
        (11, "Срабатывание реле по превышению температуры"),
        (12, "Изменение состояния дискретных входов"),
        (13, "Событие в журнале программирования"),
        (14, "Превышение текущего лимита небаланса тока"),
        (15, "Срабатывание реле по матрице событий"),
        (16, "Возврат реле в замкнутое состояние"),
        (17, "Обрыв нейтрального провода"),
        (18, "Обрыв или КЗ фазного провода"),
        (19, "Резерв"),
        (20, "Пропадание напряжения на время более 10 часов"),
    ]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT OR IGNORE INTO event_bits (bit_number, description) VALUES (?, ?)",
            data
        )
        await db.commit()

async def decode_bitmask(bitmask: int) -> list[dict]:
    events = []
    for bit in range(21):
        if bitmask & (1 << bit):
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT description FROM event_bits WHERE bit_number = ?",
                    (bit,)
                )
                row = await cursor.fetchone()
                if row:
                    events.append({"bit": bit, "description": row[0]})
    return events

async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()

async def init_user_events_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_chat_id INTEGER NOT NULL,
                event_timestamp TEXT NOT NULL,
                serial TEXT NOT NULL,
                ip TEXT NOT NULL,
                bitmask INTEGER NOT NULL,
                raw_data TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                is_sent INTEGER DEFAULT 0  ← ДОБАВИТЬ ЭТУ СТРОКУ
            )
        """)
        await db.commit()

async def add_user_event(chat_id: int, timestamp: str, serial: str, ip: str, bitmask: int, raw_data: str):
    """Сохранить событие для конкретного пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_events 
            (user_chat_id, event_timestamp, serial, ip, bitmask, raw_data)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, timestamp, serial, ip, bitmask, raw_data)
        )
        await db.commit()

async def get_user_events(chat_id: int, page: int = 0, limit: int = 5) -> list:
    """Получить события конкретного пользователя."""
    offset = page * limit
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, event_timestamp, serial, ip, bitmask 
            FROM user_events 
            WHERE user_chat_id = ?
            ORDER BY id DESC 
            LIMIT ? OFFSET ?
            """,
            (chat_id, limit, offset)
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            bitmask = row[4]
            decoded = await decode_bitmask(bitmask)
            result.append({
                "id": row[0],
                "timestamp": row[1],
                "serial": row[2],
                "ip": row[3],
                "bitmask": bitmask,
                "decoded_events": decoded
            })
        return result

async def get_user_events_count(chat_id: int) -> int:
    """Получить количество событий пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM user_events WHERE user_chat_id = ?",
            (chat_id,)
        )
        count = await cursor.fetchone()
        return count[0]

async def clear_user_events(chat_id: int):
    """Очистить события конкретного пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_events WHERE user_chat_id = ?",
            (chat_id,)
        )
        await db.commit()


async def get_unsent_events():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT
                id,
                user_chat_id,
                event_timestamp,
                serial,
                ip,
                bitmask
            FROM user_events
            WHERE is_sent = 0
            ORDER BY id ASC
        """)

        rows = await cursor.fetchall()

        result = []

        for row in rows:
            result.append({
                "id": row[0],
                "chat_id": row[1],
                "timestamp": row[2],
                "serial": row[3],
                "ip": row[4],
                "bitmask": row[5]
            })

        return result


async def mark_event_sent(event_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE user_events
            SET is_sent = 1
            WHERE id = ?
        """, (event_id,))

        await db.commit()


# --- СЧЁТЧИК НЕПРОЧИТАННЫХ PUSH ---
async def get_unread_count(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT unread_push_count FROM user_state WHERE chat_id = ?",
            (chat_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

async def increment_unread_count(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Пытаемся обновить существующую запись
        await db.execute("""
            UPDATE user_state 
            SET unread_push_count = unread_push_count + 1 
            WHERE chat_id = ?
        """, (chat_id,))
        
        # Если записи не было — вставляем новую
        await db.execute("""
            INSERT OR IGNORE INTO user_state (chat_id, unread_push_count, in_archive)
            VALUES (?, 1, 0)
        """, (chat_id,))
        
        await db.commit()
        

async def reset_unread_count(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_state (chat_id, unread_push_count, in_archive)
            VALUES (?, 0, COALESCE((SELECT in_archive FROM user_state WHERE chat_id = ?), 0))
        """, (chat_id, chat_id))
        await db.commit()


# --- МНОГОПОЛЬЗОВАТЕЛЬСКАЯ СИСТЕМА ---
async def init_multiuser_tables():
    """Инициализация таблиц для мультипользовательского режима."""
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Создаем таблицы (если их нет)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                access_type TEXT CHECK(access_type IN ('single', 'group')) NOT NULL,
                group_code TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_meters (
                group_code TEXT NOT NULL,
                serial TEXT NOT NULL,
                FOREIGN KEY(group_code) REFERENCES groups(code),
                UNIQUE(group_code, serial)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_single_meters (
                chat_id INTEGER PRIMARY KEY,
                serial TEXT NOT NULL
            )
        """)
        
        # 2. ДОБАВЛЯЕМ КОЛОНКУ LANG 
        try:
            await db.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'ru'")
            await db.commit()
        except aiosqlite.OperationalError:
            pass  
            
        await db.commit()


# --- РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ---
async def get_user(chat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT chat_id, name, access_type, group_code, lang FROM users WHERE chat_id = ?",
            (chat_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "chat_id": row[0],
                "name": row[1],
                "access_type": row[2],
                "group_code": row[3],
                "lang": row[4] or "ru"  
            }
    return None

async def set_user_single_access(chat_id: int, name: str, serial: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Пробуем взять язык из users
        cursor = await db.execute("SELECT lang FROM users WHERE chat_id = ?", (chat_id,))
        row = await cursor.fetchone()
        lang = row[0] if row else None
        
        # 2. Если users пуст (после отключения), берём из settings
        if not lang:
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (f"user_lang_{chat_id}",))
            row = await cursor.fetchone()
            lang = row[0] if row else "ru"
            
        await db.execute("DELETE FROM user_single_meters WHERE chat_id = ?", (chat_id,))
        await db.execute(
            "INSERT OR REPLACE INTO users (chat_id, name, access_type, group_code, lang) VALUES (?, ?, 'single', NULL, ?)",
            (chat_id, name, lang)
        )
        await db.execute("INSERT INTO user_single_meters (chat_id, serial) VALUES (?, ?)", (chat_id, serial))
        await db.commit()

async def set_user_group_access(chat_id: int, name: str, group_code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT lang FROM users WHERE chat_id = ?", (chat_id,))
        row = await cursor.fetchone()
        lang = row[0] if row else None
        
        if not lang:
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (f"user_lang_{chat_id}",))
            row = await cursor.fetchone()
            lang = row[0] if row else "ru"
            
        await db.execute("DELETE FROM user_single_meters WHERE chat_id = ?", (chat_id,))
        await db.execute(
            "INSERT OR REPLACE INTO users (chat_id, name, access_type, group_code, lang) VALUES (?, ?, 'group', ?, ?)",
            (chat_id, name, group_code, lang)
        )
        await db.commit()


# --- РАБОТА С ГРУППАМИ ---
async def get_group_meters(group_code: str) -> list[str]:
    """Получить список счётчиков группы."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT serial FROM group_meters WHERE group_code = ?",
            (group_code,)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def get_group_name(group_code: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT name FROM groups WHERE code = ? COLLATE NOCASE",
            (group_code.strip(),)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

# --- ПОЛУЧЕНИЕ ВСЕХ СЧЁТЧИКОВ ПОЛЬЗОВАТЕЛЯ ---
async def get_user_meters(chat_id: int) -> list[str]:
    """Получить все счётчики, доступные пользователю."""
    user = await get_user(chat_id)
    if not user:
        return []
    
    if user["access_type"] == "single":
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT serial FROM user_single_meters WHERE chat_id = ?",
                (chat_id,)
            )
            row = await cursor.fetchone()
            return [row[0]] if row else []
    else:
        return await get_group_meters(user["group_code"])

async def get_unread_events_count(chat_id: int) -> int:
    """Получить количество НЕПРОЧИТАННЫХ событий."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM user_events WHERE user_chat_id = ? AND is_read = 0",
            (chat_id,)
        )
        count = await cursor.fetchone()
        return count[0]

async def mark_events_as_read(chat_id: int):
    """Пометить все события пользователя как прочитанные."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE user_events SET is_read = 1 WHERE user_chat_id = ?",
            (chat_id,)
        )
        await db.commit()

async def remove_user_access(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Сохраняем язык в settings перед удалением
        cursor = await db.execute("SELECT lang FROM users WHERE chat_id = ?", (chat_id,))
        row = await cursor.fetchone()
        saved_lang = row[0] if row else "ru"
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (f"user_lang_{chat_id}", saved_lang)
        )
        
        # 2. Удаляем доступ (пользователь исчезает из users, язык остаётся в settings)
        await db.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
        await db.execute("DELETE FROM user_single_meters WHERE chat_id = ?", (chat_id,))
        await db.commit() 



