# telegram_api.py
import os
import ssl
import json
import aiohttp
import asyncio
import logging
from aiohttp_socks import ProxyConnector  
from dotenv import load_dotenv
from database import get_setting, set_setting

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(
    total=45,
    connect=15,
    sock_read=40,
)

class TelegramAPI:
    def __init__(self):
        self.offset = 0
        self._reconnect_lock = asyncio.Lock()
        self.session = self._create_session()

    def _create_session(self) -> aiohttp.ClientSession:
        """Создаёт новое соединение с Telegram через SOCKS5-прокси."""
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        connector = ProxyConnector.from_url(
            PROXY_URL,
            ssl=ssl_ctx,
        )

        return aiohttp.ClientSession(
            connector=connector,
            timeout=REQUEST_TIMEOUT,
        )

    async def close(self):
        """Закрывает соединение с Telegram API."""
        if not self.session.closed:
            await self.session.close()

    async def reconnect(self):
        """Пересоздаёт соединение после тайм-аута или сетевой ошибки."""
        async with self._reconnect_lock:
            if not self.session.closed:
                await self.session.close()

            self.session = self._create_session()

    async def api_call(self, method, payload=None):
        """Выполняет запрос к Telegram API и повторяет его при сбое."""
        url = f"{BASE_URL}/{method}"

        for attempt in range(1, 3):
            try:
                async with self.session.post(
                    url,
                    data=payload,
                ) as response:
                    response.raise_for_status()
                    return await response.json()

            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                logger.warning(
                    "Telegram API request failed: %s, attempt %s of 2: %s",
                    method,
                    attempt,
                    error,
                )

                if attempt == 2:
                    raise

                await self.reconnect()
                await asyncio.sleep(2)

    async def send_message(self, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        return await self.api_call("sendMessage", payload)

    async def edit_message(self, chat_id, message_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        return await self.api_call("editMessageText", payload)

    async def delete_message(self, chat_id, message_id):
        return await self.api_call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    async def send_clean_message(self, chat_id, text, reply_markup=None):
        """Удаляет предыдущее сообщение и отправляет новое (режим одного окна)."""
        key = f"last_msg_{chat_id}"
        last_msg_id = await get_setting(key)
        
        if last_msg_id:
            try:
                await self.delete_message(chat_id, int(last_msg_id))
            except:
                pass
        
        result = await self.send_message(chat_id, text, reply_markup)
        if result.get("ok"):
            await set_setting(key, str(result["result"]["message_id"]))
        return result

    async def get_updates(self):
        payload = {"timeout": 30, "offset": self.offset}
        result = await self.api_call("getUpdates", payload)

        if not result.get("ok"):
            return []

        updates = result.get("result", [])
        if updates:
            self.offset = updates[-1]["update_id"] + 1

        return updates
