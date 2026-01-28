import os
from decouple import config


class Config:
    SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL', default='sqlite:///medical_tests.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Настройки тестирования
    TEST_TIME_LIMIT = 3600  # 1 час в секундах
    PASSING_SCORE = 70  # Процент для успешной сдачи