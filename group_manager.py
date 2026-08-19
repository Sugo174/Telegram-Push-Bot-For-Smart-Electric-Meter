# group_manager.py
import sqlite3
import os
import sys

DB_PATH = "emis_events.db"

def get_db_connection():
    """Получить подключение к базе данных."""
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных {DB_PATH} не найдена!")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def list_groups():
    """Показать все группы."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT code, name FROM groups ORDER BY name")
    groups = cursor.fetchall()
    
    if not groups:
        print("📭 Нет созданных групп")
        conn.close()
        return []
    
    print("\n📋 Существующие группы:")
    print("-" * 50)
    for i, (code, name) in enumerate(groups, 1):
        # Получаем количество счётчиков
        cursor.execute("SELECT COUNT(*) FROM group_meters WHERE group_code = ?", (code,))
        count = cursor.fetchone()[0]
        print(f"{i}. Код: {code}")
        print(f"   Название: {name}")
        print(f"   Счётчиков: {count}")
        print("-" * 50)
    
    conn.close()
    return groups

def get_group_meters(group_code):
    """Получить список счётчиков группы."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT serial FROM group_meters WHERE group_code = ? ORDER BY serial", (group_code,))
    meters = [row[0] for row in cursor.fetchall()]
    conn.close()
    return meters

def update_group_meters(group_code, new_meters):
    """Обновить список счётчиков группы."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Удаляем старые счётчики
    cursor.execute("DELETE FROM group_meters WHERE group_code = ?", (group_code,))
    
    # Добавляем новые
    for serial in new_meters:
        cursor.execute("INSERT INTO group_meters (group_code, serial) VALUES (?, ?)", (group_code, serial))
    
    conn.commit()
    conn.close()
    print(f"✅ Список счётчиков для группы {group_code} обновлён!")

def add_new_group():
    """Добавить новую группу."""
    code = input("Введите код группы (например, EMIS-2026-001): ").strip()
    if not code:
        print("❌ Код не может быть пустым!")
        return
    
    name = input("Введите название группы: ").strip()
    if not name:
        print("❌ Название не может быть пустым!")
        return
    
    # Ввод счётчиков
    print("Введите счётчики (по одному на строку, пустая строка для завершения):")
    meters = []
    while True:
        serial = input(f"Счётчик #{len(meters)+1}: ").strip()
        if not serial:
            break
        if len(serial) != 11 or not serial.isdigit() or not (serial.startswith("971") or serial.startswith("976")):
            print("⚠️  Неверный формат счётчика (должно быть 11 цифр, начинаться с 971 или 976)")
            continue
        if serial in meters:
            print("⚠️  Счётчик уже добавлен")
            continue
        meters.append(serial)
    
    if not meters:
        print("❌ Должен быть хотя бы один счётчик!")
        return
    
    # Сохраняем в базу
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO groups (code, name) VALUES (?, ?)", (code, name))
        for serial in meters:
            cursor.execute("INSERT INTO group_meters (group_code, serial) VALUES (?, ?)", (code, serial))
        conn.commit()
        print(f"✅ Группа '{name}' (код: {code}) создана успешно!")
    except sqlite3.IntegrityError:
        print(f"❌ Группа с кодом '{code}' уже существует!")
    finally:
        conn.close()

def edit_existing_group(groups):
    """Редактировать существующую группу."""
    if not groups:
        return
    
    try:
        choice = int(input("Выберите номер группы для редактирования (0 для отмены): "))
        if choice == 0:
            return
        if choice < 1 or choice > len(groups):
            print("❌ Неверный номер группы!")
            return
        
        selected_code = groups[choice - 1][0]
        selected_name = groups[choice - 1][1]
        
        print(f"\nРедактирование группы: {selected_name} (код: {selected_code})")
        
        # Показываем текущие счётчики
        current_meters = get_group_meters(selected_code)
        print(f"Текущие счётчики: {', '.join(current_meters) if current_meters else 'нет'}")
        
        # Спрашиваем, что делать
        print("\nЧто вы хотите сделать?")
        print("1. Заменить весь список счётчиков")
        print("2. Добавить счётчики к существующим")
        print("3. Удалить группу")
        action = input("Выберите действие (1-3, Enter для отмены): ").strip()
        
        if action == "1":
            # Полная замена
            print("Введите новые счётчики (по одному на строку, пустая строка для завершения):")
            new_meters = []
            while True:
                serial = input(f"Счётчик #{len(new_meters)+1}: ").strip()
                if not serial:
                    break
                if len(serial) != 11 or not serial.isdigit() or not (serial.startswith("971") or serial.startswith("976")):
                    print("⚠️  Неверный формат счётчика")
                    continue
                if serial in new_meters:
                    print("⚠️  Счётчик уже добавлен")
                    continue
                new_meters.append(serial)
            
            if new_meters:
                update_group_meters(selected_code, new_meters)
            else:
                print("❌ Список счётчиков не может быть пустым!")
                
        elif action == "2":
            # Добавление к существующим
            existing = set(current_meters)
            print("Введите дополнительные счётчики (по одному на строку, пустая строка для завершения):")
            added = []
            while True:
                serial = input(f"Счётчик #{len(added)+1}: ").strip()
                if not serial:
                    break
                if len(serial) != 11 or not serial.isdigit() or not (serial.startswith("971") or serial.startswith("976")):
                    print("⚠️  Неверный формат счётчика")
                    continue
                if serial in existing:
                    print("⚠️  Счётчик уже есть в группе")
                    continue
                if serial in added:
                    print("⚠️  Счётчик уже добавляется")
                    continue
                added.append(serial)
                existing.add(serial)
            
            if added:
                all_meters = current_meters + added
                update_group_meters(selected_code, all_meters)
            else:
                print("ℹ️  Нет новых счётчиков для добавления")
                
        elif action == "3":
            # Удаление группы
            confirm = input(f"Вы уверены, что хотите удалить группу '{selected_name}'? (да/нет): ").strip().lower()
            if confirm == "да":
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM group_meters WHERE group_code = ?", (selected_code,))
                cursor.execute("DELETE FROM groups WHERE code = ?", (selected_code,))
                conn.commit()
                conn.close()
                print(f"✅ Группа '{selected_name}' удалена!")
            else:
                print("❌ Удаление отменено")
    
    except ValueError:
        print("❌ Неверный формат номера!")

def main():
    """Основное меню."""
    while True:
        print("\n" + "="*60)
        print("🔧 УПРАВЛЕНИЕ ГРУППАМИ ЭМИС")
        print("="*60)
        print("1. Просмотреть все группы")
        print("2. Создать новую группу")
        print("3. Редактировать существующую группу")
        print("4. Выход")
        print("-"*60)
        
        choice = input("Выберите действие (1-4): ").strip()
        
        if choice == "1":
            list_groups()
        elif choice == "2":
            add_new_group()
        elif choice == "3":
            groups = list_groups()
            if groups:
                edit_existing_group(groups)
        elif choice == "4":
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор!")

if __name__ == "__main__":
    main()
