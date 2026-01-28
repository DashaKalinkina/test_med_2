from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from website import db
from website.models import Test, TestCategory, Question, Answer, MedicalWorker
from website.forms import TestForm
from datetime import datetime

moderator_bp = Blueprint('moderator', __name__)


@moderator_bp.route('/')
@login_required
def panel():
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    # Тесты, созданные модератором
    my_tests = Test.query.filter_by(created_by=current_user.id).all()

    # Все активные тесты для модерации
    all_tests = Test.query.all()

    return render_template('moderator_panel.html.html',
                           my_tests=my_tests,
                           all_tests=all_tests)


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
            created_by=current_user.id
        )

        db.session.add(test)
        db.session.commit()

        flash('Тест успешно создан! Теперь добавьте вопросы.', 'success')
        return redirect(url_for('moderator.add_questions', test_id=test.id))

    return render_template('create_test.html', form=form)


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

    return render_template('add_questions.html', test=test, questions=questions)


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


@moderator_bp.route('/results')
@login_required
def view_results():
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    results = TestResult.query.order_by(TestResult.completed_at.desc()).all()

    return render_template('moderator_results.html', results=results)


@moderator_bp.route('/test/<int:test_id>/add_question', methods=['POST'])
@login_required
def add_question(test_id):
    if not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    test = Test.query.get_or_404(test_id)

    # Проверяем, что тест создан текущим модератором
    if test.created_by != current_user.id and not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('moderator.panel'))

    # Получаем данные из формы
    question_text = request.form.get('question_text')
    question_type = request.form.get('question_type')
    points = int(request.form.get('points', 1))

    # Создаем вопрос
    question = Question(
        test_id=test_id,
        text=question_text,
        question_type=question_type,
        points=points
    )

    db.session.add(question)
    db.session.commit()

    # Добавляем ответы
    i = 1
    while True:
        answer_text = request.form.get(f'answer_text_{i}')
        if not answer_text:
            break

        is_correct = request.form.get(f'is_correct_{i}') == 'true'

        answer = Answer(
            question_id=question.id,
            text=answer_text,
            is_correct=is_correct
        )

        db.session.add(answer)
        i += 1

    db.session.commit()
    flash('Вопрос успешно добавлен!', 'success')
    return redirect(url_for('moderator.add_questions', test_id=test_id))