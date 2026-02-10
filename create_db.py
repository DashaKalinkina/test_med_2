# init_db.py
import os
import sys

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from website import create_app, db

app = create_app()

with app.app_context():
    try:
        db.create_all()
        print("✅ База данных успешно создана!")
        print("📁 Файл БД: instance/database.db")
        
        # Проверяем созданные таблицы
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📊 Создано таблиц: {len(tables)}")
        for table in tables:
            print(f"   - {table}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")