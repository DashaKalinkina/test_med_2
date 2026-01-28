from website import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Создаем таблицы, если они не существуют
        db.create_all()

        # Создаем тестовые категории, если их нет
        from website.models import TestCategory

        if not TestCategory.query.first():
            categories = [
                TestCategory(name='Анатомия', description='Тесты по анатомии человека'),
                TestCategory(name='Фармакология', description='Тесты по лекарственным препаратам'),
                TestCategory(name='Хирургия', description='Тесты по хирургическим процедурам'),
                TestCategory(name='Терапия', description='Тесты по терапии заболеваний'),
                TestCategory(name='Педиатрия', description='Тесты по детским болезням'),
                TestCategory(name='Гигиена', description='Тесты по медицинской гигиене'),
            ]

            for category in categories:
                db.session.add(category)

            db.session.commit()
            print("Созданы тестовые категории")

    app.run(debug=True, host='0.0.0.0', port=5000)