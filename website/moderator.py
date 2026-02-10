from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from website import db
from website.models import Test, TestCategory, Question, Answer, MedicalWorker, TestResult, TestSubscription
from website.forms import TestForm
from datetime import datetime

moderator_bp = Blueprint('moderator', __name__)


# ========== ГЛАВНАЯ ПАНЕЛЬ МОДЕРАТОРА ==========
@moderator_bp.route('/')
@login_required
def panel():
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    # Тесты, созданные модератором
    my_tests = Test.query.filter_by(created_by=current_user.id).all()

    # Все тесты для модерации
    all_tests = Test.query.all()

    # Активные тесты
    active_tests = Test.query.filter_by(is_active=True).count()

    return render_template('moderator_panel.html',
                           my_tests=my_tests,
                           all_tests=all_tests,
                           active_tests=active_tests)


@moderator_bp.route('/test/<int:test_id>/subscribers')
@login_required
def test_subscribers(test_id):
    """Список подписанных пользователей для теста по подписке."""
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test = Test.query.get_or_404(test_id)

    if test.access_type != 'subscribed':
        flash('Этот тест не является тестом по подписке.', 'info')
        return redirect(url_for('moderator.panel'))

    subscriptions = TestSubscription.query.filter_by(test_id=test_id).all()
    workers = MedicalWorker.query.order_by(MedicalWorker.last_name, MedicalWorker.first_name).all()

    return render_template('moderator_subscribers.html',
                           test=test,
                           subscriptions=subscriptions,
                           workers=workers)


@moderator_bp.route('/test/<int:test_id>/assign', methods=['POST'])
@login_required
def assign_subscriber(test_id):
    """Назначить тест конкретному пользователю (создать подписку)."""
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test = Test.query.get_or_404(test_id)
    if test.access_type != 'subscribed':
        flash('Назначение доступно только для тестов по подписке.', 'info')
        return redirect(url_for('moderator.panel'))

    worker_id = request.form.get('worker_id')
    if not worker_id:
        flash('Выберите пользователя для назначения.', 'warning')
        return redirect(url_for('moderator.test_subscribers', test_id=test_id))

    worker = MedicalWorker.query.get(worker_id)
    if not worker:
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('moderator.test_subscribers', test_id=test_id))

    existing = TestSubscription.query.filter_by(worker_id=worker.id, test_id=test_id).first()
    if existing:
        flash('Этот тест уже назначен выбранному пользователю.', 'info')
        return redirect(url_for('moderator.test_subscribers', test_id=test_id))

    sub = TestSubscription(worker_id=worker.id, test_id=test_id)
    db.session.add(sub)
    db.session.commit()

    flash(f'Тест "{test.title}" назначен пользователю {worker.get_full_name()}.', 'success')
    return redirect(url_for('moderator.test_subscribers', test_id=test_id))


@moderator_bp.route('/test/<int:test_id>/subscription/<int:sub_id>/delete', methods=['POST'])
@login_required
def delete_subscription(test_id, sub_id):
    """Снять назначение теста с пользователя."""
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test = Test.query.get_or_404(test_id)
    subscription = TestSubscription.query.get_or_404(sub_id)

    if subscription.test_id != test.id:
        flash('Некорректное назначение.', 'danger')
        return redirect(url_for('moderator.test_subscribers', test_id=test_id))

    db.session.delete(subscription)
    db.session.commit()

    flash('Назначение теста для пользователя удалено.', 'info')
    return redirect(url_for('moderator.test_subscribers', test_id=test_id))


# ========== СОЗДАНИЕ ТЕСТА ==========
@moderator_bp.route('/test/create', methods=['GET', 'POST'])
@login_required
def create_test():
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    form = TestForm()

    if form.validate_on_submit():
        test = Test(
            title=form.title.data,
            description=form.description.data,
            difficulty=form.difficulty.data,
            time_limit=form.time_limit.data * 60,  # конвертируем минуты в секунды
            passing_score=form.passing_score.data,
            access_type=form.access_type.data,
            max_attempts=form.max_attempts.data or 0,
            created_by=current_user.id
        )

        db.session.add(test)
        db.session.commit()

        flash('Тест успешно создан! Теперь добавьте вопросы.', 'success')
        return redirect(url_for('moderator.add_questions', test_id=test.id))

    return render_template('create_test.html', form=form)


# ========== ПРОСМОТР И ДОБАВЛЕНИЕ ВОПРОСОВ ==========
@moderator_bp.route('/test/<int:test_id>/questions')
@login_required
def add_questions(test_id):
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test = Test.query.get_or_404(test_id)

    # Проверяем, что тест создан текущим модератором
    if test.created_by != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('moderator.panel'))

    questions = Question.query.filter_by(test_id=test_id).all()

    from website.moderator_forms import AddQuestionForm
    form = AddQuestionForm()

    return render_template('add_questions.html', test=test, questions=questions, form=form)


# ========== ПРОСМОТР РЕЗУЛЬТАТОВ ==========
@moderator_bp.route('/results')
@login_required
def view_results():
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    results = TestResult.query.order_by(TestResult.completed_at.desc()).all()

    return render_template('moderator_results.html', results=results)


# ========== ПЕРЕКЛЮЧЕНИЕ АКТИВНОСТИ ТЕСТА ==========
@moderator_bp.route('/test/<int:test_id>/toggle')
@login_required
def toggle_test(test_id):
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test = Test.query.get_or_404(test_id)
    test.is_active = not test.is_active

    db.session.commit()

    status = 'активирован' if test.is_active else 'деактивирован'
    flash(f'Тест "{test.title}" {status}', 'success')
    return redirect(url_for('moderator.panel'))


# В moderator.py добавьте после функции toggle_test:

@moderator_bp.route('/test/<int:test_id>/delete', methods=['POST'])
@login_required
def delete_test(test_id):
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test = Test.query.get_or_404(test_id)

    # Проверяем, что тест создан текущим модератором или пользователь - админ
    if test.created_by != current_user.id and not current_user.is_admin:
        flash('Вы не можете удалить этот тест', 'danger')
        return redirect(url_for('moderator.panel'))

    # Получаем название теста до удаления (для сообщения)
    test_title = test.title

    try:
        # Удаляем связанные данные (каскадное удаление)
        # 1. Удаляем ответы пользователей на вопросы этого теста
        from website.models import UserAnswer, TestResult

        # Находим все результаты этого теста
        test_results = TestResult.query.filter_by(test_id=test_id).all()
        result_ids = [result.id for result in test_results]

        # Удаляем ответы пользователей
        if result_ids:
            UserAnswer.query.filter(UserAnswer.result_id.in_(result_ids)).delete(synchronize_session=False)

        # 2. Удаляем результаты теста
        TestResult.query.filter_by(test_id=test_id).delete(synchronize_session=False)

        # 3. Удаляем ответы на вопросы
        questions = Question.query.filter_by(test_id=test_id).all()
        question_ids = [q.id for q in questions]

        if question_ids:
            Answer.query.filter(Answer.question_id.in_(question_ids)).delete(synchronize_session=False)

        # 4. Удаляем вопросы
        Question.query.filter_by(test_id=test_id).delete(synchronize_session=False)

        # 5. Удаляем сам тест
        db.session.delete(test)

        db.session.commit()

        flash(f'Тест "{test_title}" успешно удален', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении теста: {str(e)}', 'danger')

    return redirect(url_for('moderator.panel'))


@moderator_bp.route('/tests/delete_multiple', methods=['POST'])
@login_required
def delete_multiple_tests():
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test_ids = request.form.getlist('test_ids')

    if not test_ids:
        flash('Не выбраны тесты для удаления', 'warning')
        return redirect(url_for('moderator.panel'))

    deleted_count = 0
    error_tests = []

    for test_id in test_ids:
        try:
            test = Test.query.get(test_id)

            if not test:
                continue

            # Проверяем права
            if test.created_by != current_user.id and not current_user.is_admin:
                error_tests.append(f"{test.title} (нет прав)")
                continue

            # Удаляем тест
            db.session.delete(test)
            deleted_count += 1

        except Exception as e:
            error_tests.append(f"{test.title if test else test_id} ({str(e)})")

    try:
        db.session.commit()

        if deleted_count > 0:
            flash(f'Успешно удалено {deleted_count} тестов', 'success')

        if error_tests:
            flash(f'Ошибки при удалении: {", ".join(error_tests)}', 'warning')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении тестов: {str(e)}', 'danger')

    return redirect(url_for('moderator.panel'))

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФАЙЛОВ ==========
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_uploaded_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Добавляем timestamp для уникальности
        import time
        timestamp = str(int(time.time()))
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"

        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        return filename
    return None


@moderator_bp.route('/test/<int:test_id>/add_question', methods=['POST'])
@login_required
def add_question(test_id):
    """Добавление вопроса из модального окна (текст, тема, картинка, ответы)."""
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test = Test.query.get_or_404(test_id)

    # Проверяем, что тест создан текущим модератором
    if test.created_by != current_user.id and not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('moderator.panel'))

    question_text = (request.form.get('question_text') or '').strip()
    question_type = request.form.get('question_type')
    topic = (request.form.get('topic') or '').strip()
    question_level = request.form.get('question_level') or 'medium'
    points_raw = request.form.get('points', '1')

    # Простая серверная валидация
    if not question_text:
        flash('Введите текст вопроса.', 'danger')
        return redirect(url_for('moderator.add_questions', test_id=test_id))

    try:
        points = int(points_raw)
        if points < 1:
            points = 1
    except ValueError:
        points = 1

    # Сохраняем изображение, если есть
    image_file = request.files.get('image')
    image_filename = save_uploaded_file(image_file) if image_file else None

    # Создаем вопрос
    question = Question(
        test_id=test_id,
        text=question_text,
        question_type=question_type,
        points=points,
        image_filename=image_filename,
        topic=topic,
        question_level=question_level,
        last_modified_by_id=current_user.id
    )

    db.session.add(question)
    db.session.commit()

    # Добавляем ответы
    if question_type in ['single', 'multiple']:
        i = 0
        while True:
            answer_text = request.form.get(f'question-answers-{i}-text')
            if not answer_text:
                i += 1
                if i > 20:
                    break
                continue

            if question_type == 'single':
                correct_answer_index = request.form.get('correct_answer')
                is_correct = (correct_answer_index == str(i))
            else:
                is_correct = request.form.get(f'question-answers-{i}-is_correct') == 'true'

            answer = Answer(
                question_id=question.id,
                text=answer_text.strip(),
                is_correct=is_correct
            )
            db.session.add(answer)
            i += 1

    elif question_type == 'text':
        correct_text = (request.form.get('text_correct_answer') or '').strip()
        if correct_text:
            answer = Answer(
                question_id=question.id,
                text=correct_text.lower(),
                is_correct=True
            )
            db.session.add(answer)

    db.session.commit()
    flash('Вопрос успешно добавлен!', 'success')
    return redirect(url_for('moderator.add_questions', test_id=test_id))