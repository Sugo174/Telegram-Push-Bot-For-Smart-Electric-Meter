#app.py
import asyncio
from telegram_api import TelegramAPI
from datetime import datetime, timezone, timedelta
from handlers import (
    process_update,
    LANGS,
    BITS_TRANSLATION,
    t
)
from database import (
    init_db,
    get_unsent_events,
    mark_event_sent,
    init_multiuser_tables,
    decode_bitmask,
    get_unread_events_count,  
    get_user,                 
    get_user_events_count
)

async def notification_loop(tg):
    print("Бот ЭМИС-Дешефратор PUSH-кодов запущен")
    while True:
        try:
            events = await get_unsent_events()
            
            for ev in events:               
                user = await get_user(ev["chat_id"])
                lang_code = user.get('lang', 'ru') if user else 'ru'
                decoded = await decode_bitmask(ev["bitmask"])

                # Формируем время события в GMT+5
                try:
                    ts = ev.get('timestamp') or ev.get('event_timestamp')
                    utc_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    gmt5 = timezone(timedelta(hours=5))
                    local_time = utc_time.astimezone(gmt5)
                    time_str = local_time.strftime("%H:%M (GMT+5)")
                except Exception:
                    # Фоллбэк на текущее время сервера, если поле timestamp отсутствует/сломано
                    time_str = datetime.now(timezone(timedelta(hours=5))).strftime("%H:%M (GMT+5)")

                text = f"{t(lang_code, 'push_t')}\n"
                text += f"🕒 {time_str}\n"
                text += f"{t(lang_code, 'push_s', serial=ev['serial'])}\n"
                text += f"{t(lang_code, 'push_ip', ip=ev['ip'])}\n"
                text += f"{t(lang_code, 'push_c', code=ev['bitmask'])}\n\n"

                for d in decoded:
                    tr_desc = BITS_TRANSLATION.get(d['bit'], {}).get(lang_code, d['description'])
                    text += f"{t(lang_code, 'push_bit', bit=d['bit'])}: {tr_desc}\n"

                keyboard = {"inline_keyboard": [[{"text": t(lang_code, 'back'), "callback_data": "back_to_menu"}]]}

                await tg.send_clean_message(ev["chat_id"], text, keyboard)
                await mark_event_sent(ev["id"])

        except Exception as e:
            import traceback
            print(f"❌ Ошибка в notification_loop: {e}")
            traceback.print_exc()
            
        await asyncio.sleep(2)

async def main():
    await init_db()
    await init_multiuser_tables()

    tg = TelegramAPI()

    print("Bot started")

    asyncio.create_task(notification_loop(tg))

    while True:
        try:
            updates = await tg.get_updates()

            for upd in updates:
                await process_update(tg, upd)

        except Exception as e:
            print("Polling error:", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
