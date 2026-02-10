from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, IntegerField, FieldList, FormField, BooleanField, \
    SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class AnswerForm(FlaskForm):
    text = StringField('Текст ответа', validators=[Optional()])  # Сделаем Optional для динамического добавления
    is_correct = BooleanField('Правильный ответ')


class QuestionForm(FlaskForm):
    text = TextAreaField('Текст вопроса', validators=[DataRequired()],
                         render_kw={"placeholder": "Введите текст вопроса..."})
    question_type = SelectField('Тип вопроса', choices=[
        ('single', 'Один правильный ответ'),
        ('multiple', 'Несколько правильных ответов'),
        ('text', 'Текстовый ответ (слово/фраза)')
    ], validators=[DataRequired()])
    points = IntegerField('Баллы', default=1, validators=[DataRequired(), NumberRange(min=1, max=10)])
    topic = StringField('Тема / раздел', validators=[Optional()],
                        render_kw={"placeholder": "Например: Кардиология, Вакцинация детей..."})
    question_level = SelectField(
        'Уровень сложности вопроса',
        choices=[
            ('basic', 'Базовый'),
            ('medium', 'Средний'),
            ('hard', 'Сложный')
        ],
        default='medium'
    )
    image = FileField('Изображение к вопросу', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Только изображения JPG, PNG, GIF!')
    ])

    # Для одиночных и множественных ответов
    answers = FieldList(FormField(AnswerForm), min_entries=2)

    # Для текстовых ответов
    correct_text_answer = StringField('Правильный текстовый ответ',
                                      validators=[Optional()],
                                      render_kw={"placeholder": "Введите правильный ответ..."})


class AddQuestionForm(FlaskForm):
    question = FormField(QuestionForm)
    submit = SubmitField('Добавить вопрос')