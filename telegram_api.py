# telegram_api.py
import os
import ssl
import json
import aiohttp
from aiohttp_socks import ProxyConnector  
from dotenv import load_dotenv
from database import get_setting, set_setting

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


class TelegramAPI:
    def __init__(self):
        self.offset = 0

        # Отключаем проверку сертификата
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        # Правильный коннектор для SOCKS5 + SSL
        connector = ProxyConnector.from_url(PROXY_URL, ssl=ssl_ctx)
        self.session = aiohttp.ClientSession(connector=connector)

    async def close(self):
        await self.session.close()

    async def api_call(self, method, payload=None):
        url = f"{BASE_URL}/{method}"
        # proxy= больше НЕ нужен, коннектор уже настроен на туннель
        async with self.session.post(url, data=payload) as resp:
            return await resp.json()

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
