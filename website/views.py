from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from website import db
from website.models import Test, TestCategory, TestResult, Question, Answer, UserAnswer, MedicalWorker, TestSubscription
from website.forms import TestForm
from datetime import datetime
import json

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        # Последние тесты пользователя
        recent_results = TestResult.query.filter_by(
            worker_id=current_user.id
        ).order_by(TestResult.completed_at.desc()).limit(5).all()

        # Доступные тесты
        available_tests = Test.query.filter_by(is_active=True).all()

        return render_template('index.html',
                               recent_results=recent_results,
                               available_tests=available_tests)
    return render_template('index.html')


@main_bp.route('/profile')
@login_required
def profile():
    # Статистика пользователя
    results = TestResult.query.filter_by(worker_id=current_user.id).all()

    # Фильтруем только завершенные тесты для статистики
    completed_results = [r for r in results if r.completed_at]
    total_tests = len(completed_results)
    passed_tests = len([r for r in completed_results if r.passed])

    # Средний балл только по завершенным тестам
    if total_tests > 0:
        avg_score = sum([r.percentage for r in completed_results]) / total_tests
    else:
        avg_score = 0

    # Последние 10 результатов
    recent_results = TestResult.query.filter_by(
        worker_id=current_user.id
    ).order_by(TestResult.started_at.desc()).limit(10).all()

    return render_template('profile.html',
                           user=current_user,
                           total_tests=total_tests,
                           passed_tests=passed_tests,
                           avg_score=round(avg_score, 1),
                           recent_results=recent_results)


@main_bp.route('/tests')
@login_required
def tests():
    categories = TestCategory.query.all()
    all_tests = Test.query.filter_by(is_active=True).all()

    # Фильтруем: обычные тесты видны всем, тесты по подписке — только назначенным пользователям
    tests_list = []
    for test in all_tests:
        if test.access_type == 'simple':
            tests_list.append(test)
        else:
            subscription = TestSubscription.query.filter_by(
                worker_id=current_user.id,
                test_id=test.id
            ).first()
            if subscription:
                tests_list.append(test)

    # Определяем статус теста для пользователя
    tests_with_status = []
    for test in tests_list:
        result = TestResult.query.filter_by(
            worker_id=current_user.id,
            test_id=test.id
        ).first()

        # есть ли подписка
        subscription = None
        if test.access_type == 'subscribed':
            subscription = TestSubscription.query.filter_by(
                worker_id=current_user.id,
                test_id=test.id
            ).first()

        status = 'not_started'
        if result:
            status = 'passed' if result.passed else 'failed'

        tests_with_status.append({
            'test': test,
            'status': status,
            'result': result,
            'subscription': subscription
        })

    return render_template('tests.html',
                           tests=tests_with_status,
                           categories=categories)


@main_bp.route('/test/<int:test_id>')
@login_required
def test_detail(test_id):
    test = Test.query.get_or_404(test_id)

    # Проверяем, не проходил ли пользователь уже этот тест
    existing_result = TestResult.query.filter_by(
        worker_id=current_user.id,
        test_id=test_id
    ).first()

    # Для обычных тестов сохраняем текущее поведение (1 попытка по умолчанию)
    if test.access_type == 'simple' and existing_result:
        return redirect(url_for('main.test_result', result_id=existing_result.id))

    # Для теста по подписке проверяем, есть ли назначение (подписка)
    if test.access_type == 'subscribed':
        subscription = TestSubscription.query.filter_by(
            worker_id=current_user.id,
            test_id=test.id
        ).first()
        if not subscription:
            flash('Этот тест недоступен для вашего аккаунта.', 'warning')
            return redirect(url_for('main.tests'))

    return render_template('test_detail.html', test=test)


@main_bp.route('/test/<int:test_id>/start', methods=['POST'])
@login_required
def start_test(test_id):
    test = Test.query.get_or_404(test_id)

    # Если тест по подписке — проверяем наличие подписки (назначения)
    if test.access_type == 'subscribed':
        subscription = TestSubscription.query.filter_by(
            worker_id=current_user.id,
            test_id=test.id
        ).first()
        if not subscription:
            flash('Этот тест недоступен для вашего аккаунта.', 'warning')
            return redirect(url_for('main.test_detail', test_id=test_id))

    # Проверяем лимит попыток (если задан)
    if test.max_attempts and test.max_attempts > 0:
        attempts_count = TestResult.query.filter_by(
            worker_id=current_user.id,
            test_id=test_id
        ).count()
        if attempts_count >= test.max_attempts:
            flash('Достигнут лимит попыток для этого теста.', 'warning')
            return redirect(url_for('main.test_result',
                                    result_id=TestResult.query.filter_by(
                                        worker_id=current_user.id,
                                        test_id=test_id
                                    ).order_by(TestResult.completed_at.desc()).first().id))

    # Создаем запись о начале теста
    result = TestResult(
        worker_id=current_user.id,
        test_id=test_id,
        started_at=datetime.utcnow()
    )

    db.session.add(result)
    db.session.commit()

    return redirect(url_for('main.take_test', result_id=result.id))


@main_bp.route('/test/take/<int:result_id>', methods=['GET', 'POST'])
@login_required
def take_test(result_id):
    result = TestResult.query.get_or_404(result_id)

    # Проверяем, что тест принадлежит пользователю
    if result.worker_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.tests'))

    # Проверяем, не завершен ли уже тест
    if result.completed_at:
        return redirect(url_for('main.test_result', result_id=result.id))

    test = result.test
    questions = Question.query.filter_by(test_id=test.id).all()

    if request.method == 'POST':
        # Обработка ответов
        score = 0
        total_points = 0

        for question in questions:
            total_points += question.points

            if question.question_type == 'single':
                answer_id = request.form.get(f'question_{question.id}')
                if answer_id:
                    answer = Answer.query.get(int(answer_id))
                    is_correct = answer.is_correct if answer else False

                    user_answer = UserAnswer(
                        result_id=result.id,
                        question_id=question.id,
                        answer_ids=json.dumps([int(answer_id)]),
                        is_correct=is_correct
                    )

                    if is_correct:
                        score += question.points

                    db.session.add(user_answer)

            elif question.question_type == 'multiple':
                answer_ids = request.form.getlist(f'question_{question.id}')
                if answer_ids:
                    answer_ids = [int(id) for id in answer_ids]
                    correct_answers = Answer.query.filter_by(
                        question_id=question.id,
                        is_correct=True
                    ).all()

                    correct_ids = [a.id for a in correct_answers]

                    # Проверяем, все ли правильные ответы выбраны и нет ли неправильных
                    is_correct = (set(answer_ids) == set(correct_ids))

                    user_answer = UserAnswer(
                        result_id=result.id,
                        question_id=question.id,
                        answer_ids=json.dumps(answer_ids),
                        is_correct=is_correct
                    )

                    if is_correct:
                        score += question.points

                    db.session.add(user_answer)

            elif question.question_type == 'text':
                text_answer = request.form.get(f'question_text_{question.id}', '').strip()
                if text_answer:
                    # Ищем правильный ответ (должен быть только один для текстовых вопросов)
                    correct_answer = Answer.query.filter_by(
                        question_id=question.id,
                        is_correct=True
                    ).first()

                    # Простая проверка (можно сделать более сложную, например, с допуском опечаток)
                    is_correct = False
                    if correct_answer:
                        # Сравниваем в нижнем регистре для нечувствительности к регистру
                        is_correct = (text_answer.lower() == correct_answer.text.lower())

                    user_answer = UserAnswer(
                        result_id=result.id,
                        question_id=question.id,
                        text_answer=text_answer,
                        is_correct=is_correct
                    )

                    if is_correct:
                        score += question.points

                    db.session.add(user_answer)

        # Завершаем тест
        percentage = (score / total_points * 100) if total_points > 0 else 0
        passed = percentage >= test.passing_score

        result.score = score
        result.percentage = percentage
        result.passed = passed
        result.completed_at = datetime.utcnow()
        result.time_taken = (result.completed_at - result.started_at).seconds

        db.session.commit()

        return redirect(url_for('main.test_result', result_id=result.id))

    return render_template('test_detail.html',
                           test=test,
                           questions=questions,
                           result_id=result.id)


@main_bp.route('/test/result/<int:result_id>')
@login_required
def test_result(result_id):
    result = TestResult.query.get_or_404(result_id)

    # Проверяем, что результат принадлежит пользователю
    if result.worker_id != current_user.id and not current_user.is_moderator:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.tests'))

    # Получаем ответы пользователя
    user_answers = UserAnswer.query.filter_by(result_id=result_id).all()

    # Для каждого ответа получаем информацию о вопросе и выбранных ответах
    detailed_answers = []
    for ua in user_answers:
        question = Question.query.get(ua.question_id)
        answer_ids = json.loads(ua.answer_ids) if ua.answer_ids else []
        answers = Answer.query.filter(Answer.id.in_(answer_ids)).all() if answer_ids else []

        # Получаем все правильные ответы для этого вопроса
        correct_answers = Answer.query.filter_by(
            question_id=ua.question_id,
            is_correct=True
        ).all()

        detailed_answers.append({
            'question': question,
            'user_answers': answers,
            'correct_answers': correct_answers,
            'is_correct': ua.is_correct
        })

    return render_template('test_result.html',
                           result=result,
                           detailed_answers=detailed_answers)


@main_bp.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    # Статистика для админ-панели
    total_users = MedicalWorker.query.count()
    total_tests = Test.query.count()
    total_results = TestResult.query.count()
    active_tests = Test.query.filter_by(is_active=True).count()

    recent_results = TestResult.query.filter(
        TestResult.completed_at.isnot(None)
    ).order_by(
        TestResult.completed_at.desc()
    ).limit(10).all()

    return render_template('admin_panel.html',
                           total_users=total_users,
                           total_tests=total_tests,
                           total_results=total_results,
                           active_tests=active_tests,
                           recent_results=recent_results)


# Админские функции управления пользователями
@main_bp.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    users = MedicalWorker.query.order_by(MedicalWorker.created_at.desc()).all()
    return render_template('admin_users.html', users=users)


@main_bp.route('/admin/user/<int:user_id>/toggle_admin')
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    user = MedicalWorker.query.get_or_404(user_id)

    # Нельзя снять права администратора с самого себя
    if user.id == current_user.id:
        flash('Нельзя изменить свои собственные права администратора', 'warning')
        return redirect(url_for('main.admin_users'))

    user.is_admin = not user.is_admin
    db.session.commit()

    status = 'назначен' if user.is_admin else 'снят'
    flash(f'Пользователь {user.get_full_name()} {status} администратором', 'success')
    return redirect(url_for('main.admin_users'))


@main_bp.route('/admin/user/<int:user_id>/toggle_moderator')
@login_required
def toggle_moderator(user_id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    user = MedicalWorker.query.get_or_404(user_id)

    # Нельзя снять права модератора с самого себя, если это единственный админ
    if user.id == current_user.id and user.is_admin:
        flash('Нельзя изменить свои собственные права модератора', 'warning')
        return redirect(url_for('main.admin_users'))

    user.is_moderator = not user.is_moderator
    db.session.commit()

    status = 'назначен' if user.is_moderator else 'снят'
    flash(f'Пользователь {user.get_full_name()} {status} модератором', 'success')
    return redirect(url_for('main.admin_users'))


@main_bp.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

    user = MedicalWorker.query.get_or_404(user_id)

    # Нельзя удалить самого себя
    if user.id == current_user.id:
        flash('Нельзя удалить свой собственный аккаунт', 'danger')
        return redirect(url_for('main.admin_users'))

    # Удаляем связанные данные пользователя
    TestResult.query.filter_by(worker_id=user_id).delete()

    # Удаляем пользователя
    db.session.delete(user)
    db.session.commit()

    flash(f'Пользователь {user.get_full_name()} удален', 'success')
    return redirect(url_for('main.admin_users'))