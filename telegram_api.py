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
        # Каждый чат заменяет сообщения последовательно.
        # Это защищает от одновременного PUSH и нажатия кнопки.
        self._chat_locks = {}
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
                    result = await response.json()

                    # Telegram сообщает причину отказа в JSON.
                    # Например: сообщение слишком старое для удаления.
                    if response.status >= 500:
                        response.raise_for_status()

                    if not result.get("ok"):
                        logger.warning(
                            "Telegram rejected %s: %s",
                            method,
                            result.get("description", "Unknown error"),
                        )

                    return result

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
        # Явно заменяем клавиатуру, включая удаление прежних кнопок.
        payload["reply_markup"] = json.dumps(
            reply_markup
            if reply_markup is not None
            else {"inline_keyboard": []}
        )
        return await self.api_call("editMessageText", payload)

    async def delete_message(self, chat_id, message_id):
        return await self.api_call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    async def send_clean_message(
        self,
        chat_id,
        text,
        reply_markup=None,
        *,
        is_notification=False,
    ):
        """Заменяет последнее окно и сохраняет его ID.

        Для обычных экранов использует редактирование, если удаление
        запрещено. Уведомления отправляет новым сообщением, чтобы
        пользователь получил уведомление Telegram.
        """
        lock = self._chat_locks.setdefault(chat_id, asyncio.Lock())

        async with lock:
            key = f"last_msg_{chat_id}"
            saved_id = await get_setting(key)
            previous_id = int(saved_id) if saved_id else None
            previous_remains = False

            if previous_id is not None:
                deletion = await self.delete_message(
                    chat_id,
                    previous_id,
                )

                if not deletion.get("ok"):
                    description = deletion.get("description", "").lower()

                    if "message to delete not found" in description:
                        # Пользователь уже удалил это сообщение.
                        previous_id = None

                    elif "message can't be deleted" in description:
                        previous_remains = True

                        if not is_notification:
                            edited = await self.edit_message(
                                chat_id,
                                previous_id,
                                text,
                                reply_markup,
                            )

                            edit_description = edited.get(
                                "description", ""
                            ).lower()

                            if edited.get("ok"):
                                return edited

                            if "message is not modified" in edit_description:
                                # Нужный экран уже отображается.
                                return {"ok": True, "result": True}

                            if "message to edit not found" in edit_description:
                                previous_id = None
                                previous_remains = False
                            else:
                                # При неизвестном отказе не создаём дубликат.
                                return edited

                    else:
                        # При других ошибках сохраняем старый ID
                        # и передаём ошибку вызывающему коду.
                        return deletion

            sent = await self.send_message(
                chat_id,
                text,
                reply_markup,
            )

            if not sent.get("ok"):
                return sent

            # Запоминаем новое сообщение только после подтверждения.
            await set_setting(
                key,
                str(sent["result"]["message_id"]),
            )

            if previous_remains and previous_id is not None:
                # Старый PUSH или экран остаётся без рабочих кнопок.
                try:
                    await self.api_call(
                        "editMessageReplyMarkup",
                        {
                            "chat_id": chat_id,
                            "message_id": previous_id,
                            "reply_markup": json.dumps(
                                {"inline_keyboard": []}
                            ),
                        },
                    )
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    logger.warning(
                        "Could not remove buttons from old message "
                        "%s in chat %s",
                        previous_id,
                        chat_id,
                    )

            return sent

    async def get_updates(self):
        payload = {"timeout": 30, "offset": self.offset}
        result = await self.api_call("getUpdates", payload)

        if not result.get("ok"):
            return []

        updates = result.get("result", [])
        if updates:
            self.offset = updates[-1]["update_id"] + 1

        return updates
