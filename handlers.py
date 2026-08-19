# handlers.py
import asyncio
import aiosqlite
from datetime import datetime, timezone, timedelta
from database import (
    get_user,
    get_unread_events_count,
    get_user_events,
    get_user_events_count,
    clear_user_events,
    mark_events_as_read,
    remove_user_access,
    set_user_single_access,
    set_user_group_access,
    get_user_meters,
    get_group_name,
    get_group_meters,
    get_setting,
    set_setting
)

LANGS = {
    'ru': {
        'welcome': '👋 Добро пожаловать!\n\nВыберите способ подключения, язык или перейдите в главное меню:',
        'lang_btn': '🌐 Язык', 'lang_title': '🌐 Выберите язык:',
        'lang_ru': '🇷🇺 Русский', 'lang_en': '🇬🇧 English', 'lang_cn': '🇨🇳 中文',
        'main_menu': '🏠 Главное меню', 'archive_btn': '📦 Архив PUSH уведомлений (🆕:{unread})',
        'settings_btn': '⚙️ Настройки', 'group_info_btn': 'ℹ️ Информация о группе',
        'archive_title': '📦 Архив PUSH уведомлений', 'archive_empty': ' Архив пуст.',
        'page': '📄 Страница {c} из {t}', 'back': '🏠 Главное меню',
        'prev': '◀️ Назад', 'next': 'Вперёд ▶️', 'clear': '🗑️ Очистить архив',
        'clear_q': '⚠️ Очистить архив?\nВсе данные будут удалены безвозвратно.',
        'yes': '✅ Да', 'no': '❌ Нет', 'settings': '⚙️ Настройки PUSH',
        'not_conn': '⚠️ Вы ещё не подключены.', 'type_s': '🔢 Тип: Один счётчик',
        'type_g': '🔑 Тип: Группа счётчиков', 'conn_s': '🔢 Подключить счётчик по серийному №',
        'conn_g': '🔑 Подключить группу счётчиков по коду', 'disc': '🔌 Отключить получение PUSH',
        'disc_q': '⚠️ Отключить получение PUSH?\nВы перестанете получать PUSH от всех счётчиков.',
        'disc_ok': '🔌 Получение PUSH отключено.\nВыберите способ подключения:',
        'input_s': '✏️ Введите серийный номер счётчика (11 цифр, начинается с 971 или 976):',
        'input_g': '✏️ Введите код группы счётчиков:', 'cancel': '❌ Отмена',
        'err_s': '❌ Ошибка: В коде 11 цифр, начинается с 971 или 976.\nПопробуйте снова:',
        'err_g_e': ' Код не может быть пустым.\nПопробуйте снова:',
        'err_g_nf': '❌ Группа не найдена в базе.\nПопробуйте снова:',
        'ok_s': '✅ Счётчик № <b>{serial}</b> подключён!',
        'ok_g': '✅ Группа счётчиков <b>{name}</b> подключена!',
        'grp_info': 'ℹ️ Информация о группе счётчиков', 'grp_total': 'Всего счётчиков: <b>{total}</b>',
        'grp_list': '🔢 Список счётчиков:', 'grp_none': 'Счётчики не найдены.',
        'push_t': ' PUSH от счётчика', 'push_s': 'Серийный №: <b>{serial}</b>',
        'push_ip': 'IP: {ip}', 'push_c': 'Код: <b>0x{code:X}</b>', 'push_bit': 'Бит {bit}',
        'push_u': '📬 Непрочитанных: <b>{unread}</b>', 'lang_ok': '✅ Язык изменён!',
        'push_c': 'Код: <b>0x{code:X}</b>', 'arch_date': '📅 Дата: {date}',
        'arch_meter': '🔢 Счётчик: {serial}', 'arch_ip': '🌐 IP: {ip}'
    },
    'en': {
        'welcome': ' Welcome!\n\nChoose a connection method:',
        'lang_btn': '🌐 Language', 'lang_title': '🌐 Select Language:',
        'lang_ru': '🇷🇺 Русский', 'lang_en': '🇬🇧 English', 'lang_cn': '🇨🇳 中文',
        'main_menu': '🏠 Main Menu', 'archive_btn': '📦 PUSH Notification Archive (🆕:{unread})',
        'settings_btn': '⚙️ Settings', 'group_info_btn': 'ℹ️ Meter Group Info',
        'archive_title': '📦 PUSH Notification Archive', 'archive_empty': '📦 Archive is empty.',
        'page': '📄 Page {c} of {t}', 'back': '🏠 Main Menu',
        'prev': '◀️ Back', 'next': 'Next ▶️', 'clear': '🗑️ Clear Archive',
        'clear_q': '⚠️ Clear the archive?\nAll data will be permanently deleted.',
        'yes': '✅ Yes', 'no': '❌ No', 'settings': '⚙️PUSH settings',
        'not_conn': '️ You are not connected yet.', 'type_s': '🔢 Type: Single Meter',
        'type_g': '🔑 Type: Meter Group', 'conn_s': '🔢 Connect Meter by Serial #',
        'conn_g': '🔑 Connect Meter Group by Code', 'disc': '🔌 Disable PUSH Notifications',
        'disc_q': '⚠️ Disable PUSH notifications?\nYou will stop receiving PUSH from all meters.',
        'disc_ok': '🔌 PUSH notifications disabled.\nChoose a connection method:',
        'input_s': '✏️ Enter meter serial number (11 digits, starting with 971 or 976):',
        'input_g': '✏️ Enter meter group code:', 'cancel': '❌ Cancel',
        'err_s': '❌ Error: Must be 11 digits, starting with 971 or 976.\nTry again:',
        'err_g_e': '❌ Code cannot be empty.\nTry again:',
        'err_g_nf': '❌ Group not found in database.\nTry again:',
        'ok_s': '✅ Meter # <b>{serial}</b> connected!',
        'ok_g': '✅ Meter group <b>{name}</b> connected!',
        'grp_info': 'ℹ️ Meter Group Information', 'grp_total': 'Total meters: <b>{total}</b>',
        'grp_list': '🔢 Meter list:', 'grp_none': 'No meters found.',
        'push_t': '🚨 PUSH from meter', 'push_s': 'Serial #: <b>{serial}</b>',
        'push_ip': 'IP: {ip}', 'push_c': 'Code: <b>0x{code:X}</b>','push_bit': 'Bit {bit}',
        'push_u': '📬 Unread: <b>{unread}</b>', 'lang_ok': '✅ Language changed!',
        'push_c': 'Code: <b>0x{code:X}</b>', 'arch_date': '📅 Date: {date}',
        'arch_meter': '🔢 Meter: {serial}', 'arch_ip': '🌐 IP: {ip}'
    },
    'cn': {
        'welcome': '👋 欢迎！\n\n请选择连接方式：',
        'lang_btn': '🌐 语言', 'lang_title': '🌐 选择语言：',
        'lang_ru': '🇷🇺 Русский', 'lang_en': '🇬🇧 English', 'lang_cn': '🇨🇳 中文',
        'main_menu': '🏠 主菜单', 'archive_btn': '📦 PUSH 通知档案 (🆕:{unread})',
        'settings_btn': '⚙️ 设置', 'group_info_btn': 'ℹ️ 电表组信息',
        'archive_title': ' PUSH 通知档案', 'archive_empty': '📦 档案为空。',
        'page': '📄 第 {c} 页，共 {t} 页', 'back': '🏠 主菜单',
        'prev': '◀️ 上一页', 'next': '下一页 ▶️', 'clear': '️ 清空档案',
        'clear_q': '⚠️ 确定清空档案？\n所有数据将被永久删除。',
        'yes': '✅ 是', 'no': '❌ 否', 'settings': '⚙️PUSH 设置',
        'not_conn': '⚠️ 您尚未连接。', 'type_s': '🔢 类型：单表',
        'type_g': '🔑 类型：电表组', 'conn_s': '🔢 通过序列号连接电表',
        'conn_g': '🔑 通过代码连接电表组', 'disc': '🔌 关闭 PUSH 通知',
        'disc_q': '⚠️ 确定关闭 PUSH 通知？\n您将停止接收所有电表的 PUSH。',
        'disc_ok': '🔌 已关闭 PUSH 通知。\n请选择连接方式：',
        'input_s': '✏️ 请输入电表序列号（11 位数字，以 971 或 976 开头）：',
        'input_g': '✏️ 请输入电表组代码：', 'cancel': '❌ 取消',
        'err_s': '❌ 错误：必须为 11 位数字，且以 971 或 976 开头。\n请重试：',
        'err_g_e': ' 代码不能为空。\n请重试：',
        'err_g_nf': '❌ 数据库中未找到该组。\n请重试：',
        'ok_s': '✅ 电表 # <b>{serial}</b> 已连接！',
        'ok_g': '✅ 电表组 <b>{name}</b> 已连接！',
        'grp_info': 'ℹ️ 电表组信息', 'grp_total': '电表总数：<b>{total}</b>',
        'grp_list': '🔢 电表列表：', 'grp_none': '未找到电表。',
        'push_t': '🚨 电表 PUSH 通知', 'push_s': '序列号：<b>{serial}</b>',
        'push_ip': 'IP: {ip}', 'push_c': '代码：<b>0x{code:X}</b>', 'push_bit': '位 {bit}',
        'push_u': '📬 未读：<b>{unread}</b>', 'lang_ok': '✅ 语言已更改！',
        'push_c': '代码：<b>0x{code:X}</b>', 'arch_date': '📅 日期: {date}',
        'arch_meter': '🔢 电表: {serial}', 'arch_ip': '🌐 IP: {ip}'
    }
}

BITS_TRANSLATION = {
    0: {'ru': 'Событие в журнале самодиагностики', 'en': 'Self-diagnosis log event', 'cn': '自检日志事件'},
    1: {'ru': 'Перерыв питания', 'en': 'Power interruption', 'cn': '电源中断'},
    2: {'ru': 'Событие в журнале параметров качества сети', 'en': 'Power quality log event', 'cn': '电能质量日志事件'},
    3: {'ru': 'Воздействие магнитного поля', 'en': 'Magnetic field impact', 'cn': '磁场干扰'},
    4: {'ru': 'Вскрытие крышки отсека зажимов', 'en': 'Terminal cover opened', 'cn': '接线端子盖打开'},
    5: {'ru': 'Вскрытие корпуса', 'en': 'Body cover opened', 'cn': '表壳打开'},
    6: {'ru': 'Превышение лимита активной мощности', 'en': 'Active power limit exceeded', 'cn': '有功功率超限'},
    7: {'ru': 'Срабатывание реле по максимальному току', 'en': 'Overcurrent relay tripped', 'cn': '过流继电器动作'},
    8: {'ru': 'Срабатывание реле по магнитному полю', 'en': 'Magnetic field relay tripped', 'cn': '磁场继电器动作'},
    9: {'ru': 'Срабатывание реле по максимальному напряжению', 'en': 'Overvoltage relay tripped', 'cn': '过压继电器动作'},
    10: {'ru': 'Срабатывание реле по небалансу токов', 'en': 'Current unbalance relay tripped', 'cn': '电流不平衡继电器动作'},
    11: {'ru': 'Срабатывание реле по превышению температуры', 'en': 'Overtemperature relay tripped', 'cn': '过热继电器动作'},
    12: {'ru': 'Изменение состояния дискретных входов', 'en': 'Discrete input state change', 'cn': '数字输入状态改变'},
    13: {'ru': 'Событие в журнале программирования', 'en': 'Programming log event', 'cn': '编程日志事件'},
    14: {'ru': 'Превышение текущего лимита небаланса тока', 'en': 'Current unbalance limit exceeded', 'cn': '电流不平衡超限'},
    15: {'ru': 'Срабатывание реле по матрице событий', 'en': 'Event matrix relay tripped', 'cn': '事件矩阵继电器动作'},
    16: {'ru': 'Возврат реле в замкнутое состояние', 'en': 'Relay closed state restored', 'cn': '继电器恢复闭合'},
    17: {'ru': 'Обрыв нейтрального провода', 'en': 'Neutral wire broken', 'cn': '零线断开'},
    18: {'ru': 'Обрыв или КЗ фазного провода', 'en': 'Phase wire broken or shorted', 'cn': '相线断开或短路'},
    19: {'ru': 'Резерв', 'en': 'Reserved', 'cn': '保留'},
    20: {'ru': 'Пропадание напряжения > 10 часов', 'en': 'Voltage loss > 10 hours', 'cn': '电压丢失超10小时'}
}

def t(lang, key, **kw):
    return LANGS.get(lang, LANGS['ru']).get(key, key).format(**kw) if kw else LANGS.get(lang, LANGS['ru']).get(key, key)

async def get_main_menu(chat_id, lang=None):
    user = await get_user(chat_id)  # ← user объявляется СРАЗУ
    
    if lang is None:
        lang = user.get("lang", "ru") if user else "ru"
        
    unread = await get_unread_events_count(chat_id)
    
    kb = [[{"text": t(lang, 'archive_btn', unread=unread), "callback_data": "show_archive"}]]
    
    if user and user.get("access_type") == "group":
        kb.append([{"text": t(lang, 'group_info_btn'), "callback_data": "group_info"}])
        
    kb.append([{"text": t(lang, 'settings_btn'), "callback_data": "show_settings"}])
    kb.append([{"text": t(lang, 'lang_btn'), "callback_data": "select_lang"}])
    return {"inline_keyboard": kb}


async def show_main_menu(tg, chat_id, lang=None):
    if lang is None:
        user = await get_user(chat_id)
        lang = user.get("lang") if user else (await get_setting(f"user_lang_{chat_id}") or "ru")
        
    await tg.send_clean_message(chat_id, t(lang, 'main_menu'), await get_main_menu(chat_id, lang))
    

async def show_archive(tg, chat_id, page=0):
    user = await get_user(chat_id)
    # Единый fallback: если юзера нет, берём язык из сохранённых настроек
    lang = user.get("lang") if user else (await get_setting(f"user_lang_{chat_id}") or "ru")
    
    limit = 5
    events = await get_user_events(chat_id, page=page, limit=limit)
    total = await get_user_events_count(chat_id)
    
    total_pages = max(1, (total + limit - 1) // limit) if total > 0 else 1
    current_page = min(page + 1, total_pages)
    await mark_events_as_read(chat_id)

    if not events:
        text = t(lang, 'archive_empty')
    else:
        text = f"{t(lang, 'archive_title')} ({t(lang, 'page', c=current_page, t=total_pages)})\n\n"
        for ev in events:
            try:
                utc_time = datetime.fromisoformat(ev['timestamp'].replace('Z', '+00:00'))
                gmt5 = timezone(timedelta(hours=5))
                local_time = utc_time.astimezone(gmt5)
                date_time_str = local_time.strftime("%d.%m.%Y %H:%M (GMT+5)")
            except:
                date_time_str = ev['timestamp'][:16]  

            text += f"📅 {date_time_str}\n"  
            text += f"{t(lang, 'arch_meter', serial=ev['serial'])}\n"
            text += f"{t(lang, 'arch_ip', ip=ev['ip'])}\n"
            
            for d in ev["decoded_events"]:
                tr_desc = BITS_TRANSLATION.get(d['bit'], {}).get(lang, d['description'])
                text += f" {t(lang, 'push_bit', bit=d['bit'])}: {tr_desc}\n"
            text += f"{'─' * 20}\n"

    keyboard = {"inline_keyboard": []}
    buttons = []
    if page > 0: buttons.append({"text": t(lang, 'prev'), "callback_data": f"hist_page_{page-1}"})
    if (page + 1) * limit < total: buttons.append({"text": t(lang, 'next'), "callback_data": f"hist_page_{page+1}"})
    if buttons: keyboard["inline_keyboard"].append(buttons)
    
    keyboard["inline_keyboard"].append([{"text": t(lang, 'clear'), "callback_data": "clear_history"}])
    keyboard["inline_keyboard"].append([{"text": t(lang, 'back'), "callback_data": "back_to_menu"}])

    await tg.send_clean_message(chat_id, text, keyboard)
    

async def show_group_info(tg, chat_id, page=0):
    user = await get_user(chat_id)
    if not user: return
    lang = user.get('lang', 'ru')
    if user.get("access_type") != "group":
        await tg.send_clean_message(chat_id, t(lang, 'not_conn'), await get_main_menu(chat_id))
        return

    group_code = user["group_code"]
    group_name = await get_group_name(group_code)
    all_meters = await get_group_meters(group_code)
    total = len(all_meters)

    limit = 10
    total_pages = max(1, (total + limit - 1) // limit)
    current_page = min(page + 1, total_pages)

    start_idx = page * limit
    end_idx = start_idx + limit
    page_meters = all_meters[start_idx:end_idx]

    text = f"{t(lang, 'grp_info')}\n\n"
    text += f"{t(lang, 'type_g').split(':')[0]}: <b>{group_name or group_code}</b>\n"
    text += f"{t(lang, 'grp_total', total=total)}\n\n"

    if page_meters:
        text += f"{t(lang, 'grp_list')}\n"
        for serial in page_meters:
            text += f"<code>{serial}</code>\n"
        text += f"\n{t(lang, 'page', c=current_page, t=total_pages)}"
    else:
        text += t(lang, 'grp_none')

    keyboard = {"inline_keyboard": []}
    nav = []
    if page > 0: nav.append({"text": t(lang, 'prev'), "callback_data": f"group_page_{page-1}"})
    if end_idx < total: nav.append({"text": t(lang, 'next'), "callback_data": f"group_page_{page+1}"})
    if nav: keyboard["inline_keyboard"].append(nav)
    keyboard["inline_keyboard"].append([{"text": t(lang, 'back'), "callback_data": "back_to_menu"}])

    await tg.send_clean_message(chat_id, text, keyboard)
    

async def show_settings(tg, chat_id):
    user = await get_user(chat_id)
    lang = user.get("lang") if user else None
    if not lang:
        lang = await get_setting(f"user_lang_{chat_id}") or "ru"

    if not user or not user.get("access_type"):
        text = t(lang, 'not_conn')
    elif user["access_type"] == "single":
        meters = await get_user_meters(chat_id)
        serial = meters[0] if meters else "?"
        text = f"{t(lang, 'type_s')}\n{t(lang, 'conn_s').replace('🔢 ','')}: <b>{serial}</b>"
    else:
        gn = await get_group_name(user["group_code"])
        text = f"{t(lang, 'type_g')}\n{t(lang, 'conn_g').replace('🔑 ','')}: <b>{gn or user['group_code']}</b>"

    kb = {"inline_keyboard": [
        [{"text": t(lang, 'conn_s'), "callback_data": "set_serial"}],
        [{"text": t(lang, 'conn_g'), "callback_data": "set_group"}],
        [{"text": t(lang, 'disc'), "callback_data": "disconnect_access"}],
        [{"text": t(lang, 'back'), "callback_data": "back_to_menu"}]
    ]}
    await tg.send_clean_message(chat_id, text, kb)
    

async def start_set_serial(tg, chat_id):
    user = await get_user(chat_id)
    lang = user.get("lang") if user else (await get_setting(f"user_lang_{chat_id}") or "ru")
    await set_setting(f"waiting_group_{chat_id}", "0")
    await set_setting(f"waiting_serial_{chat_id}", "1")
    await tg.send_clean_message(chat_id, t(lang, 'input_s'), {"inline_keyboard": [[{"text": t(lang, 'cancel'), "callback_data": "cancel_input"}]]})

async def start_set_group(tg, chat_id):
    user = await get_user(chat_id)
    lang = user.get("lang") if user else (await get_setting(f"user_lang_{chat_id}") or "ru")
    await set_setting(f"waiting_serial_{chat_id}", "0")
    await set_setting(f"waiting_group_{chat_id}", "1")
    await tg.send_clean_message(chat_id, t(lang, 'input_g'), {"inline_keyboard": [[{"text": t(lang, 'cancel'), "callback_data": "cancel_input"}]]})

async def process_serial_input(tg, chat_id, serial: str):
    user = await get_user(chat_id)
    lang = user.get("lang") if user else (await get_setting(f"user_lang_{chat_id}") or "ru")
    await set_setting(f"waiting_serial_{chat_id}", "0")
    is_valid = serial.isdigit() and len(serial) == 11 and (serial.startswith("971") or serial.startswith("976"))
    if not is_valid:
        await tg.send_clean_message(chat_id, t(lang, 'err_s'), {"inline_keyboard": [[{"text": t(lang, 'cancel'), "callback_data": "cancel_input"}]]})
        await set_setting(f"waiting_serial_{chat_id}", "1")
        return
    await set_user_single_access(chat_id, f"User_{chat_id}", serial)
    await tg.send_clean_message(chat_id, t(lang, 'ok_s', serial=serial), {"inline_keyboard": [[{"text": t(lang, 'settings_btn'), "callback_data": "show_settings"}], [{"text": t(lang, 'back'), "callback_data": "back_to_menu"}]]})

async def process_group_input(tg, chat_id, code: str):
    user = await get_user(chat_id)
    lang = user.get("lang") if user else (await get_setting(f"user_lang_{chat_id}") or "ru")
    await set_setting(f"waiting_group_{chat_id}", "0")
    code = code.strip()
    if not code:
        await tg.send_clean_message(chat_id, t(lang, 'err_g_e'), {"inline_keyboard": [[{"text": t(lang, 'cancel'), "callback_data": "cancel_input"}]]})
        await set_setting(f"waiting_group_{chat_id}", "1")
        return
    group_name = await get_group_name(code)
    if not group_name:
        await tg.send_clean_message(chat_id, t(lang, 'err_g_nf'), {"inline_keyboard": [[{"text": t(lang, 'cancel'), "callback_data": "cancel_input"}]]})
        await set_setting(f"waiting_group_{chat_id}", "1")
        return
    await set_user_group_access(chat_id, f"User_{chat_id}", code)
    await tg.send_clean_message(chat_id, t(lang, 'ok_g', name=group_name), {"inline_keyboard": [[{"text": t(lang, 'settings_btn'), "callback_data": "show_settings"}], [{"text": t(lang, 'back'), "callback_data": "back_to_menu"}]]})    
    
async def process_callback(tg, callback):
    data = callback["data"]
    chat_id = callback["message"]["chat"]["id"]
    
    # Немедленно подтверждаем Telegram, чтобы не было повторных отправок
    try:
        await callback.answer()
    except:
        pass

    user = await get_user(chat_id)
    lang = user.get("lang") if user else (await get_setting(f"user_lang_{chat_id}") or "ru")

    if data == "cancel_input":
        await set_setting(f"waiting_serial_{chat_id}", "0")
        await set_setting(f"waiting_group_{chat_id}", "0")
        await show_settings(tg, chat_id)
        return

    elif data == "show_archive": await show_archive(tg, chat_id, page=0)
    elif data.startswith("hist_page_"): await show_archive(tg, chat_id, page=int(data.split("_")[-1]))
    
    elif data == "clear_history":
        await tg.send_clean_message(chat_id, t(lang, 'clear_q'), {
            "inline_keyboard": [
                [{"text": t(lang, 'yes'), "callback_data": "confirm_clear_yes"}],
                [{"text": t(lang, 'no'), "callback_data": "confirm_clear_no"}]
            ]
        })
    elif data == "confirm_clear_yes":
        await clear_user_events(chat_id)
        await show_archive(tg, chat_id, page=0)
    elif data == "confirm_clear_no":
        await show_archive(tg, chat_id, page=0)

    elif data == "back_to_menu": 
        await show_main_menu(tg, chat_id, lang=lang)  # Передаём язык явно
        return
    elif data == "show_settings": await show_settings(tg, chat_id)
    elif data == "set_serial": await start_set_serial(tg, chat_id)
    elif data == "set_group": await start_set_group(tg, chat_id)
    
    elif data == "select_lang":
        await tg.send_clean_message(chat_id, t(lang, 'lang_title'), {
            "inline_keyboard": [
                [{"text": t(lang, 'lang_ru'), "callback_data": "lang_ru"}],
                [{"text": t(lang, 'lang_en'), "callback_data": "lang_en"}],
                [{"text": t(lang, 'lang_cn'), "callback_data": "lang_cn"}]
            ]
        })
    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        async with aiosqlite.connect("emis_events.db") as db:
            # Простое UPDATE/INSERT без сложных конфликтов
            await db.execute("UPDATE users SET lang = ? WHERE chat_id = ?", (new_lang, chat_id))
            if db.total_changes == 0:
                await db.execute("INSERT INTO users (chat_id, name, access_type, lang) VALUES (?, ?, ?, ?)", 
                                 (chat_id, f"User_{chat_id}", "single", new_lang))
            await db.commit()
        await asyncio.sleep(0.1)  # Гарантируем сброс WAL-кэша SQLite
        await show_main_menu(tg, chat_id, lang=new_lang)
        return

    elif data == "group_info": await show_group_info(tg, chat_id, page=0)
    elif data.startswith("group_page_"): await show_group_info(tg, chat_id, page=int(data.split("_")[-1]))

    elif data == "disconnect_access":
        await tg.send_clean_message(chat_id, t(lang, 'disc_q'), {
            "inline_keyboard": [
                [{"text": t(lang, 'yes'), "callback_data": "confirm_disconnect_yes"}],
                [{"text": t(lang, 'no'), "callback_data": "confirm_disconnect_no"}]
            ]
        })
    elif data == "confirm_disconnect_yes":
        await remove_user_access(chat_id)
        await tg.send_clean_message(chat_id, t(lang, 'disc_ok'), {
            "inline_keyboard": [
                [{"text": t(lang, 'conn_s'), "callback_data": "set_serial"}],
                [{"text": t(lang, 'conn_g'), "callback_data": "set_group"}],
                [{"text": t(lang, 'back'), "callback_data": "back_to_menu"}]
            ]
        })
    elif data == "confirm_disconnect_no":
        await show_settings(tg, chat_id)
        

async def process_message(tg, message):
    chat_id = message["chat"]["id"]
    msg_id = int(message["message_id"])
    text = message.get("text", "").strip()

    try:
        await tg.delete_message(chat_id, msg_id)
        await asyncio.sleep(0.15)
    except: pass

    if not text: return

    if text == "/start":
        kb = {"inline_keyboard": [
            [{"text": t('ru', 'conn_s'), "callback_data": "set_serial"}],
            [{"text": t('ru', 'conn_g'), "callback_data": "set_group"}],
            [{"text": t('ru', 'lang_btn'), "callback_data": "select_lang"}],
            [{"text": t('ru', 'main_menu'), "callback_data": "back_to_menu"}]
        ]}
        await tg.send_clean_message(chat_id, t('ru', 'welcome'), kb)
        return

    # Проверка режимов ввода
    if await get_setting(f"waiting_serial_{chat_id}") == "1":
        await process_serial_input(tg, chat_id, text)
        return
    if await get_setting(f"waiting_group_{chat_id}") == "1":
        await process_group_input(tg, chat_id, text)
        return

    # Обычная логика
    user = await get_user(chat_id)
    if user:
        await show_main_menu(tg, chat_id)
    else:
        kb = {"inline_keyboard": [
            [{"text": t('ru', 'conn_s'), "callback_data": "set_serial"}],
            [{"text": t('ru', 'conn_g'), "callback_data": "set_group"}],
            [{"text": t('ru', 'lang_btn'), "callback_data": "select_lang"}]
        ]}
        await tg.send_clean_message(chat_id, t('ru', 'welcome'), kb)

async def process_update(tg, update):
    if "message" in update:
        await process_message(tg, update["message"])
    elif "callback_query" in update:
        await process_callback(tg, update["callback_query"])
