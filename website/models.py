from website import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class MedicalWorker(UserMixin, db.Model):
    __tablename__ = 'medical_workers'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    specialization = db.Column(db.String(50), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    institution = db.Column(db.String(200))
    position = db.Column(db.String(100))
    years_experience = db.Column(db.Integer, default=0)
    is_moderator = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    tests_taken = db.relationship('TestResult', backref='worker', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<MedicalWorker {self.username}>'


class TestCategory(db.Model):
    __tablename__ = 'test_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    tests = db.relationship('Test', backref='category', lazy=True)


class Test(db.Model):
    __tablename__ = 'tests'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('test_categories.id'))
    difficulty = db.Column(db.String(20), default='medium')
    time_limit = db.Column(db.Integer, default=3600)  # в секундах
    passing_score = db.Column(db.Integer, default=70)  # процент

    # Тип теста и режим доступа
    # simple  - обычный тест (можно сразу проходить)
    # subscribed - тест, на который пользователь сначала подписывается
    access_type = db.Column(db.String(20), default='simple', nullable=False)

    # Ограничения по попыткам и активности
    max_attempts = db.Column(db.Integer, default=1)  # 0 или NULL = без ограничений
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)

    # Режим прохождения
    is_strict_mode = db.Column(db.Boolean, default=True)  # строгий экзаменационный режим
    shuffle_questions = db.Column(db.Boolean, default=False)
    shuffle_answers = db.Column(db.Boolean, default=False)

    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('medical_workers.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship('Question', backref='test', lazy=True)
    results = db.relationship('TestResult', backref='test', lazy=True)


class TestSubscription(db.Model):
    """
    Подписка пользователя на тест.
    Нужна только для тестов с access_type='subscribed'.
    """
    __tablename__ = 'test_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('medical_workers.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

    worker = db.relationship('MedicalWorker', backref='test_subscriptions', lazy=True)
    test = db.relationship('Test', backref='subscriptions', lazy=True)


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'))
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='single')  # single, multiple, text
    points = db.Column(db.Integer, default=1)
    image_filename = db.Column(db.String(255))  # ← НОВОЕ: имя файла изображения

    # Расширенное тегирование
    topic = db.Column(db.String(200))  # тема / раздел
    question_level = db.Column(db.String(20), default='medium')  # basic / medium / hard

    # Простейшая "история" — кто и когда редактировал
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_modified_by_id = db.Column(db.Integer, db.ForeignKey('medical_workers.id'))
    last_modified_by = db.relationship('MedicalWorker', foreign_keys=[last_modified_by_id])

    answers = db.relationship('Answer', backref='question', lazy=True)


class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)


class TestResult(db.Model):
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('medical_workers.id'))
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'))
    score = db.Column(db.Integer)
    percentage = db.Column(db.Float)
    passed = db.Column(db.Boolean)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    time_taken = db.Column(db.Integer)  # в секундах

    answers = db.relationship('UserAnswer', backref='result', lazy=True)


class UserAnswer(db.Model):
    __tablename__ = 'user_answers'

    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('test_results.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    answer_ids = db.Column(db.String(500))  # JSON строка с ID выбранных ответов
    text_answer = db.Column(db.Text)  # ← НОВОЕ: текстовый ответ пользователя
    is_correct = db.Column(db.Boolean)

@login_manager.user_loader
def load_user(id):
    return MedicalWorker.query.get(int(id))