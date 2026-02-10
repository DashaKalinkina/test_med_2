from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from website.models import MedicalWorker

SPECIALIZATION_CHOICES = [
    ('doctor', 'Врач'),
    ('nurse', 'Медсестра/медбрат'),
    ('paramedic', 'Фельдшер'),
    ('intern', 'Интерн'),
    ('administrator', 'Администратор'),
]


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    specialization = SelectField('Специализация', choices=SPECIALIZATION_CHOICES, validators=[DataRequired()])
    license_number = StringField('Номер лицензии', validators=[DataRequired()])
    institution = StringField('Учреждение')
    position = StringField('Должность')
    years_experience = IntegerField('Стаж (лет)', default=0)
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_email(self, email):
        user = MedicalWorker.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован.')

    def validate_username(self, username):
        user = MedicalWorker.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято.')

    def validate_license_number(self, license_number):
        user = MedicalWorker.query.filter_by(license_number=license_number.data).first()
        if user:
            raise ValidationError('Этот номер лицензии уже зарегистрирован.')


class TestForm(FlaskForm):
    title = StringField('Название теста', validators=[DataRequired()])
    description = TextAreaField('Описание теста')
    difficulty = SelectField('Сложность', choices=[
        ('easy', 'Легкий'),
        ('medium', 'Средний'),
        ('hard', 'Сложный')
    ])
    time_limit = IntegerField('Лимит времени (минут)', default=60)
    passing_score = IntegerField('Проходной балл (%)', default=70)
    access_type = SelectField(
        'Тип доступа к тесту',
        choices=[
            ('simple', 'Обычный тест (сразу доступен)'),
            ('subscribed', 'Тест по подписке (нужно записаться)'),
        ],
        default='simple'
    )
    max_attempts = IntegerField(
        'Максимум попыток',
        default=1
    )
    submit = SubmitField('Создать тест')