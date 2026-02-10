from website import create_app, db
from website.models import MedicalWorker, Test, TestCategory, Question, Answer

app = create_app()

with app.app_context():
    print("Создание тестовых данных...")

    # Создаем тестового модератора
    moderator = MedicalWorker.query.filter_by(email='moderator@medtest.ru').first()
    if not moderator:
        moderator = MedicalWorker(
            email='moderator@medtest.ru',
            username='moderator',
            first_name='Модератор',
            last_name='Тестовый',
            specialization='doctor',
            license_number='MOD001',
            institution='Тестовая клиника',
            position='Главный врач',
            years_experience=5,
            is_moderator=True
        )
        moderator.set_password('mod123')
        db.session.add(moderator)
        print("✅ Создан тестовый модератор")

    # Создаем категории, если их нет
    if not TestCategory.query.first():
        categories = [
            'Анатомия',
            'Фармакология',
            'Хирургия',
            'Терапия',
            'Педиатрия'
        ]

        for cat_name in categories:
            category = TestCategory(name=cat_name, description=f'Тесты по {cat_name.lower()}')
            db.session.add(category)
        print("✅ Созданы категории тестов")

    # Создаем тестовый тест
    test = Test.query.filter_by(title='Тестовый тест по анатомии').first()
    if not test:
        category = TestCategory.query.filter_by(name='Анатомия').first()

        test = Test(
            title='Тестовый тест по анатомии',
            description='Базовый тест по анатомии человека',
            category_id=category.id if category else None,
            difficulty='easy',
            time_limit=1800,  # 30 минут
            passing_score=70,
            is_active=True,
            created_by=moderator.id if moderator else None
        )
        db.session.add(test)
        db.session.commit()

        # Добавляем вопросы
        questions_data = [
            {
                'text': 'Сколько костей в скелете взрослого человека?',
                'type': 'single',
                'points': 1,
                'answers': [
                    {'text': '206', 'correct': True},
                    {'text': '200', 'correct': False},
                    {'text': '210', 'correct': False},
                    {'text': '196', 'correct': False}
                ]
            },
            {
                'text': 'Какие органы относятся к пищеварительной системе?',
                'type': 'multiple',
                'points': 2,
                'answers': [
                    {'text': 'Желудок', 'correct': True},
                    {'text': 'Печень', 'correct': True},
                    {'text': 'Сердце', 'correct': False},
                    {'text': 'Тонкий кишечник', 'correct': True}
                ]
            }
        ]

        for q_data in questions_data:
            question = Question(
                test_id=test.id,
                text=q_data['text'],
                question_type=q_data['type'],
                points=q_data['points']
            )
            db.session.add(question)
            db.session.commit()

            for a_data in q_data['answers']:
                answer = Answer(
                    question_id=question.id,
                    text=a_data['text'],
                    is_correct=a_data['correct']
                )
                db.session.add(answer)

        db.session.commit()
        print("✅ Создан тестовый тест с вопросами")

    print("\n✅ Все тестовые данные созданы!")
    print("\nДанные для входа:")
    print("Модератор: moderator@medtest.ru / mod123")
    print("Администратор: admin@medtest.ru / admin123")