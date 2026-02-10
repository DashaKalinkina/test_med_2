import os
from decouple import config


class Config:
    SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL', default='sqlite:///medical_tests.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Настройки загрузки файлов
    UPLOAD_FOLDER = 'website/static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

    # Настройки тестирования
    TEST_TIME_LIMIT = 3600  # 1 час в секундах
    PASSING_SCORE = 70  # Процент для успешной сдачи

    @staticmethod
    def init_app(app):
        # Создаем папку для загрузок, если она не существует
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)