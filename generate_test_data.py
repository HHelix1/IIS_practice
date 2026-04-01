# generate_test_data_final.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from faker import Faker
import json
import os
import logging
import hashlib
import shutil

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация Faker для генерации реалистичных данных
fake = Faker('ru_RU')
Faker.seed(42)
np.random.seed(42)
random.seed(42)


class TrainingDataGenerator:
    """Генератор тестовых данных для системы учета обучения"""

    def __init__(self):
        self.data = {}
        self.relations = {}
        logger.info("Инициализация генератора данных")

    def generate_employees(self, count=500):
        """Генерация данных сотрудников"""
        logger.info(f"Генерация {count} сотрудников...")

        positions = [
            'Software Engineer', 'Senior Software Engineer', 'QA Engineer',
            'DevOps Engineer', 'Product Manager', 'Project Manager',
            'HR Manager', 'HR Specialist', 'Sales Manager', 'Sales Director',
            'Marketing Specialist', 'Marketing Director', 'Financial Analyst',
            'Operations Manager', 'Business Analyst', 'Data Scientist',
            'System Administrator', 'Technical Support', 'Customer Success'
        ]

        departments = ['IT', 'HR', 'Sales', 'Marketing', 'Finance', 'Operations']

        employees = []
        used_emails = set()

        for i in range(1, count + 1):
            # Генерация уникального email
            while True:
                first_name = fake.first_name()
                last_name = fake.last_name()
                email = f"{first_name.lower()}.{last_name.lower()}@company.ru"
                if email not in used_emails:
                    used_emails.add(email)
                    break

            # Генерация даты рождения (от 25 до 60 лет)
            birth_date = fake.date_of_birth(
                minimum_age=25,
                maximum_age=60
            )

            # Генерация даты приема (от 1 до 25 лет стажа)
            hire_date = fake.date_between(
                start_date='-25y',
                end_date='-1y'
            )

            # Расчет стажа в годах
            work_duration = (datetime.now().date() - hire_date).days / 365

            employee = {
                'Worker_id': i,
                'Full_name': f"{last_name} {first_name} {fake.middle_name()}",
                'Position': random.choice(positions),
                'Department': random.choice(departments),
                'email': email,
                'Phone_number': f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                'Birth_date': birth_date,
                'Hire_date': hire_date,
                'Work_duration': round(work_duration, 1),
                'Salary': random.randint(60000, 300000),
                'Is_active': random.random() > 0.05  # 95% активных
            }
            employees.append(employee)

        self.data['employees'] = pd.DataFrame(employees)
        logger.info(f"✓ Сгенерировано {len(employees)} сотрудников")
        return self.data['employees']

    def generate_users(self, count=100):
        """Генерация пользователей системы"""
        logger.info(f"Генерация {count} пользователей...")

        employees_df = self.data.get('employees')
        if employees_df is None or len(employees_df) < count:
            raise ValueError("Недостаточно сотрудников для создания пользователей")

        # Выбираем случайных сотрудников
        selected_employees = employees_df.sample(n=count)

        access_rights_choices = ['admin', 'hr', 'manager', 'user']
        access_rights_weights = [0.1, 0.2, 0.3, 0.4]

        users = []
        for i, (_, emp) in enumerate(selected_employees.iterrows(), 1):
            # Пароль (захэшированный)
            password = fake.password(length=12)
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            user = {
                'id_user': i,
                'Worker_id': int(emp['Worker_id']),
                'Full_name': emp['Full_name'],
                'email': emp['email'],
                'password_hash': password_hash,
                'access_rights': random.choices(access_rights_choices, weights=access_rights_weights)[0],
                'biometric_enabled': random.random() < 0.6,  # 60% с биометрией
                'last_login': fake.date_time_between(start_date='-30d', end_date='now'),
                'created_at': fake.date_time_between(start_date='-2y', end_date='-30d'),
                'is_active': random.random() > 0.05
            }
            users.append(user)

        self.data['users'] = pd.DataFrame(users)
        logger.info(f"✓ Сгенерировано {len(users)} пользователей")
        return self.data['users']

    def generate_biometric_data(self, count=300):
        """Генерация биометрических данных"""
        logger.info(f"Генерация {count} биометрических записей...")

        users_df = self.data.get('users')
        if users_df is None:
            raise ValueError("Сначала сгенерируйте пользователей")

        users_with_biometric = users_df[users_df['biometric_enabled'] == True]

        biometric_types = ['fingerprint', 'face', 'voice', 'iris']
        biometric_weights = [0.5, 0.3, 0.15, 0.05]

        biometric_data = []
        used_combinations = set()

        for i in range(1, count + 1):
            # Выбор случайного пользователя с биометрией
            user = users_with_biometric.sample(n=1).iloc[0]

            # Выбор уникального типа биометрии для пользователя
            while True:
                bio_type = random.choices(biometric_types, weights=biometric_weights)[0]
                key = (user['id_user'], bio_type)
                if key not in used_combinations:
                    used_combinations.add(key)
                    break

            # Генерация биометрического шаблона (симуляция)
            template_hash = hashlib.sha256(
                f"{user['id_user']}_{bio_type}_{random.random()}".encode()
            ).hexdigest()[:16]

            biometric = {
                'biometric_id': i,
                'id_user': int(user['id_user']),
                'biometric_type': bio_type,
                'template_hash': template_hash,
                'confidence_score': round(random.uniform(0.75, 0.99), 2),
                'creation_date': fake.date_time_between(
                    start_date=user['created_at'],
                    end_date='now'
                ),
                'last_used': fake.date_time_between(start_date='-30d', end_date='now'),
                'is_active': random.random() < 0.9,  # 90% активных
                'failed_attempts': np.random.poisson(0.3),
                'device_name': random.choice([
                    'iPhone 13', 'MacBook Pro', 'Samsung Galaxy', 'iPad Pro',
                    'Windows PC', 'Android Phone', 'Biometric Scanner'
                ])
            }
            biometric_data.append(biometric)

        self.data['biometric_data'] = pd.DataFrame(biometric_data)
        logger.info(f"✓ Сгенерировано {len(biometric_data)} биометрических записей")
        return self.data['biometric_data']

    def generate_educational_programs(self, count=50):
        """Генерация образовательных программ"""
        logger.info(f"Генерация {count} образовательных программ...")

        # Шаблоны названий программ
        program_templates = {
            'Technical': [
                'Python для начинающих', 'Продвинутый Java', 'Веб-разработка на React',
                'DevOps практики', 'Кибербезопасность', 'Облачные технологии AWS',
                'SQL оптимизация', 'Алгоритмы и структуры данных', 'Machine Learning',
                'Data Science с нуля', 'Docker и Kubernetes', 'Microservices архитектура'
            ],
            'Management': [
                'Управление проектами', 'Agile и Scrum', 'Лидерство для руководителей',
                'Управление командой', 'Стратегический менеджмент', 'Тайм-менеджмент',
                'Управление изменениями', 'Эмоциональный интеллект для руководителей'
            ],
            'Soft Skills': [
                'Эффективная коммуникация', 'Публичные выступления', 'Конфликтология',
                'Навыки переговоров', 'Критическое мышление', 'Креативность в бизнесе'
            ],
            'Compliance': [
                'Трудовое законодательство', 'Защита персональных данных',
                'Антикоррупционная политика', 'Охрана труда', 'Пожарная безопасность'
            ],
            'Safety': [
                'Первая помощь', 'Промышленная безопасность', 'Электробезопасность',
                'Безопасность на производстве', 'Экологическая безопасность'
            ]
        }

        providers = [
            'Internal Academy', 'Coursera', 'Udemy', 'LinkedIn Learning',
            'Stepik', 'Skillbox', 'GeekBrains', 'OTUS', 'Нетология', 'Eduson'
        ]

        programs = []
        years = [2023, 2024, 2025, 2026]

        for i in range(1, count + 1):
            category = random.choices(
                list(program_templates.keys()),
                weights=[0.4, 0.25, 0.2, 0.1, 0.05]
            )[0]

            name = random.choice(program_templates[category])
            if random.random() > 0.5:
                name += f" (Уровень {random.choice(['1', '2', '3'])})"

            year = random.choice(years)
            protocol_number = f"ПРОТ-{year}-{random.randint(100, 999)}"

            start_date = fake.date_between(
                start_date=f'-{random.randint(1, 3)}y',
                end_date='+6m'
            )
            duration_days = random.randint(7, 180)
            end_date = start_date + timedelta(days=duration_days)

            program = {
                'Education_id': i,
                'Name': name,
                'Category': category,
                'Protocol_number': protocol_number,
                'Description': fake.text(max_nb_chars=200),
                'Provider': random.choice(providers),
                'Duration_hours': random.randint(4, 160),
                'Start_date': start_date,
                'End_date': end_date,
                'Cost': random.randint(5000, 150000),
                'Max_participants': random.randint(10, 100),
                'Format': random.choice(['online', 'offline', 'mixed']),
                'Is_active': random.random() < 0.8,
                'Created_at': fake.date_time_between(start_date='-2y', end_date='-1m')
            }
            programs.append(program)

        self.data['educational_programs'] = pd.DataFrame(programs)
        logger.info(f"✓ Сгенерировано {len(programs)} образовательных программ")
        return self.data['educational_programs']

    def generate_training_assignments(self, count=2000):
        """Генерация назначений на обучение"""
        logger.info(f"Генерация {count} записей об обучении...")

        employees_df = self.data['employees']
        programs_df = self.data['educational_programs']

        statuses = ['planned', 'in_progress', 'completed', 'cancelled']
        status_weights = [0.25, 0.15, 0.55, 0.05]

        assignments = []

        for i in range(1, count + 1):
            # Выбор случайного сотрудника и программы
            employee = employees_df.sample(n=1).iloc[0]
            program = programs_df.sample(n=1).iloc[0]

            # Генерация дат
            start_date = fake.date_between(start_date='-2y', end_date='+3m')

            # Длительность от 7 до 180 дней
            duration = random.randint(7, 180)
            end_date = start_date + timedelta(days=duration)

            # Статус с учетом дат
            status = random.choices(statuses, weights=status_weights)[0]

            if status == 'completed':
                completion_date = end_date - timedelta(days=random.randint(0, 10))
                result = random.choice(['Passed', 'Passed', 'Passed', 'Failed'])
                score = random.randint(60, 100) if result == 'Passed' else random.randint(30, 59)
            elif status == 'in_progress':
                completion_date = None
                result = None
                score = None
            elif status == 'planned':
                completion_date = None
                result = None
                score = None
            else:  # cancelled
                completion_date = None
                result = 'Cancelled'
                score = None
                # Дата отмены раньше окончания
                end_date = start_date + timedelta(days=random.randint(1, duration // 2))

            assignment = {
                'id_worker_education': i,
                'Worker_id': int(employee['Worker_id']),
                'Education_id': int(program['Education_id']),
                'Begin_date': start_date,
                'End_date': end_date,
                'status': status,
                'completion_date': completion_date,
                'result': result,
                'score': score,
                'feedback': fake.text(max_nb_chars=100) if status == 'completed' and random.random() > 0.5 else None
            }
            assignments.append(assignment)

        self.data['training_assignments'] = pd.DataFrame(assignments)
        logger.info(f"✓ Сгенерировано {len(assignments)} записей об обучении")
        return self.data['training_assignments']

    def generate_recommendations(self, count=1000):
        """Генерация рекомендаций по обучению"""
        logger.info(f"Генерация {count} рекомендаций...")

        employees_df = self.data['employees']
        programs_df = self.data['educational_programs']
        trainings_df = self.data.get('training_assignments', pd.DataFrame())

        recommendations = []
        used_combinations = set()

        # Получаем список уже пройденных обучений
        completed_trainings = set()
        if not trainings_df.empty:
            for _, row in trainings_df.iterrows():
                completed_trainings.add((row['Worker_id'], row['Education_id']))

        for i in range(1, count + 1):
            # Выбор случайного сотрудника
            employee = employees_df.sample(n=1).iloc[0]

            # Выбор программы, которую сотрудник еще не проходил
            attempts = 0
            while attempts < 100:  # Защита от бесконечного цикла
                program = programs_df.sample(n=1).iloc[0]

                key = (employee['Worker_id'], program['Education_id'])
                if key not in completed_trainings and key not in used_combinations:
                    used_combinations.add(key)
                    break
                attempts += 1

            if attempts >= 100:
                continue  # Пропускаем, если не нашли подходящую

            # Расчет скоринга рекомендации
            base_score = random.uniform(0.6, 0.95)

            # Повышаем скоринг, если программа соответствует должности
            if (employee['Department'] == 'IT' and program['Category'] == 'Technical') or \
                    (employee['Department'] == 'HR' and program['Category'] in ['Management', 'Soft Skills']) or \
                    (employee['Department'] == 'Sales' and program['Category'] in ['Management', 'Soft Skills']):
                base_score += 0.15

            score = min(base_score, 1.0)

            # Причины рекомендации
            reasons = [
                'Соответствует вашей должности',
                'Популярная программа в вашем отделе',
                'Рекомендовано на основе ваших навыков',
                'Необходимо для карьерного роста',
                'Обязательное обучение',
                'Повышение квалификации'
            ]

            recommendation = {
                'recommendation_id': i,
                'worker_id': int(employee['Worker_id']),
                'education_id': int(program['Education_id']),
                'score': round(score, 2),
                'reason': random.choice(reasons),
                'creation_date': fake.date_time_between(start_date='-3m', end_date='now'),
                'is_viewed': random.random() < 0.4,
                'is_accepted': random.random() < 0.2,
                'priority': random.randint(1, 5)
            }
            recommendations.append(recommendation)

        self.data['recommendations'] = pd.DataFrame(recommendations)
        logger.info(f"✓ Сгенерировано {len(recommendations)} рекомендаций")
        return self.data['recommendations']

    def validate_data(self):
        """Валидация сгенерированных данных"""
        logger.info("Валидация данных...")

        validation_results = {}

        # Проверка уникальности email сотрудников
        employees_df = self.data.get('employees')
        if employees_df is not None:
            unique_emails = employees_df['email'].nunique() == len(employees_df)
            validation_results['employees_unique_emails'] = unique_emails
            logger.info(f"✓ Уникальность email сотрудников: {unique_emails}")

        # Проверка связей внешних ключей
        if all(k in self.data for k in ['training_assignments', 'employees']):
            assignments_df = self.data['training_assignments']
            employees_ids = set(self.data['employees']['Worker_id'])
            valid_employees = assignments_df['Worker_id'].isin(employees_ids).all()
            validation_results['valid_employee_refs'] = valid_employees
            logger.info(f"✓ Корректность ссылок на сотрудников: {valid_employees}")

        # Проверка дат
        if 'training_assignments' in self.data:
            assignments_df = self.data['training_assignments']
            valid_dates = (assignments_df['End_date'] >= assignments_df['Begin_date']).all()
            validation_results['valid_training_dates'] = valid_dates
            logger.info(f"✓ Корректность дат обучения: {valid_dates}")

        # Проверка скоринга рекомендаций
        if 'recommendations' in self.data:
            recommendations_df = self.data['recommendations']
            valid_scores = (recommendations_df['score'].between(0, 1)).all()
            validation_results['valid_scores'] = valid_scores
            logger.info(f"✓ Корректность скоринга: {valid_scores}")

        return validation_results

    def generate_all(self):
        """Генерация всех данных"""
        logger.info("=" * 60)
        logger.info("НАЧАЛО ГЕНЕРАЦИИ ТЕСТОВЫХ ДАННЫХ")
        logger.info("=" * 60)

        self.generate_employees(500)
        self.generate_users(100)
        self.generate_biometric_data(300)
        self.generate_educational_programs(50)
        self.generate_training_assignments(2000)
        self.generate_recommendations(1000)

        validation = self.validate_data()

        logger.info("=" * 60)
        logger.info("ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
        logger.info("=" * 60)

        return self.data, validation

    def export_to_csv(self, output_dir='generated_data'):
        """Экспорт данных в CSV файлы"""
        os.makedirs(output_dir, exist_ok=True)

        for table_name, df in self.data.items():
            output_file = os.path.join(output_dir, f"{table_name}.csv")
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            logger.info(f"✓ Сохранено: {output_file}")

        # Создание архива
        shutil.make_archive(
            'training_data_archive',
            'zip',
            output_dir
        )
        logger.info(f"✓ Создан архив: training_data_archive.zip")

        return output_dir

    def export_to_sql(self, db_path='sqlite:///./employee_training.db'):
        """Экспорт данных в SQLite базу данных"""
        from sqlalchemy import create_engine

        engine = create_engine(db_path)

        for table_name, df in self.data.items():
            # Маппинг названий таблиц
            sql_table_map = {
                'employees': 'employees',
                'users': 'users',
                'biometric_data': 'biometric_data',
                'educational_programs': 'education_programs',
                'training_assignments': 'training_records',
                'recommendations': 'recommendations'
            }

            sql_table = sql_table_map.get(table_name, table_name)
            df.to_sql(sql_table, engine, if_exists='append', index=False)
            logger.info(f"✓ Загружено в БД: {sql_table}")

        logger.info("✓ Данные загружены в SQLite базу данных")


def generate_report(data, validation, output_file='generation_report.md'):
    """Генерация отчета в формате Markdown"""

    report = f"""# ОТЧЕТ ПО ГЕНЕРАЦИИ ТЕСТОВЫХ ДАННЫХ
## Практическое занятие №5
## Дата: {datetime.now().strftime('%d %B %Y г.')}

## 1. Цель работы
Заполнение базы данных системы управления обучением тестовыми данными 
с использованием генеративных моделей.

## 2. Выбранный инструмент

**Faker + Pandas (кастомная генерация)**

**Обоснование выбора:**
- Простота использования и отладки
- Полный контроль над генерируемыми данными
- Возможность точного соблюдения бизнес-правил
- Отсутствие проблем с совместимостью библиотек

## 3. Параметры генерации

### 3.1 Целевые объемы данных

| Таблица | Целевое количество | Сгенерировано | Статус |
|---------|-------------------|---------------|--------|
"""

    tables_info = {
        'employees': 'Сотрудники',
        'users': 'Пользователи',
        'biometric_data': 'Биометрия',
        'educational_programs': 'Образовательные программы',
        'training_assignments': 'Назначения на обучение',
        'recommendations': 'Рекомендации'
    }

    for table_key, table_name in tables_info.items():
        if table_key in data:
            report += f"| {table_name} | {len(data[table_key])} | {len(data[table_key])} | ✅ |\n"

    report += """ ### 3.2 Параметры генерации

```python
{
    'employees': 500,
    'users': 100,
    'biometric_data': 300,
    'educational_programs': 50,
    'training_assignments': 2000,
    'recommendations': 1000
}"""

    # ============== ДОБАВИТЬ ЭТОТ КОД В КОНЕЦ ФАЙЛА generate_test_data.py ==============

    class TrainingDataGenerator:
        """Генератор тестовых данных для системы учета обучения"""

        def __init__(self):
            self.data = {}
            self.relations = {}
            logger.info("Инициализация генератора данных")

        def generate_employees(self, count=500):
            """Генерация данных сотрудников"""
            logger.info(f"Генерация {count} сотрудников...")

            positions = [
                'Software Engineer', 'Senior Software Engineer', 'QA Engineer',
                'DevOps Engineer', 'Product Manager', 'Project Manager',
                'HR Manager', 'HR Specialist', 'Sales Manager', 'Sales Director',
                'Marketing Specialist', 'Marketing Director', 'Financial Analyst',
                'Operations Manager', 'Business Analyst', 'Data Scientist',
                'System Administrator', 'Technical Support', 'Customer Success'
            ]

            departments = ['IT', 'HR', 'Sales', 'Marketing', 'Finance', 'Operations']

            employees = []
            used_emails = set()

            for i in range(1, count + 1):
                # Генерация уникального email
                while True:
                    first_name = fake.first_name()
                    last_name = fake.last_name()
                    email = f"{first_name.lower()}.{last_name.lower()}@company.ru"
                    if email not in used_emails:
                        used_emails.add(email)
                        break

                # Генерация даты рождения (от 25 до 60 лет)
                birth_date = fake.date_of_birth(
                    minimum_age=25,
                    maximum_age=60
                )

                # Генерация даты приема (от 1 до 25 лет стажа)
                hire_date = fake.date_between(
                    start_date='-25y',
                    end_date='-1y'
                )

                # Расчет стажа в годах
                work_duration = (datetime.now().date() - hire_date).days / 365

                employee = {
                    'Worker_id': i,
                    'Full_name': f"{last_name} {first_name} {fake.middle_name()}",
                    'Position': random.choice(positions),
                    'Department': random.choice(departments),
                    'email': email,
                    'Phone_number': f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                    'Birth_date': birth_date,
                    'Hire_date': hire_date,
                    'Work_duration': round(work_duration, 1),
                    'Salary': random.randint(60000, 300000),
                    'Is_active': random.random() > 0.05  # 95% активных
                }
                employees.append(employee)

            self.data['employees'] = pd.DataFrame(employees)
            logger.info(f"✓ Сгенерировано {len(employees)} сотрудников")
            return self.data['employees']

        def generate_users(self, count=100):
            """Генерация пользователей системы"""
            logger.info(f"Генерация {count} пользователей...")

            employees_df = self.data.get('employees')
            if employees_df is None or len(employees_df) < count:
                raise ValueError("Недостаточно сотрудников для создания пользователей")

            # Выбираем случайных сотрудников
            selected_employees = employees_df.sample(n=count)

            access_rights_choices = ['admin', 'hr', 'manager', 'user']
            access_rights_weights = [0.1, 0.2, 0.3, 0.4]

            users = []
            for i, (_, emp) in enumerate(selected_employees.iterrows(), 1):
                # Пароль (захэшированный)
                password = fake.password(length=12)
                password_hash = hashlib.sha256(password.encode()).hexdigest()

                user = {
                    'id_user': i,
                    'Worker_id': int(emp['Worker_id']),
                    'Full_name': emp['Full_name'],
                    'email': emp['email'],
                    'password_hash': password_hash,
                    'access_rights': random.choices(access_rights_choices, weights=access_rights_weights)[0],
                    'biometric_enabled': random.random() < 0.6,  # 60% с биометрией
                    'last_login': fake.date_time_between(start_date='-30d', end_date='now'),
                    'created_at': fake.date_time_between(start_date='-2y', end_date='-30d'),
                    'is_active': random.random() > 0.05
                }
                users.append(user)

            self.data['users'] = pd.DataFrame(users)
            logger.info(f"✓ Сгенерировано {len(users)} пользователей")
            return self.data['users']

        def generate_biometric_data(self, count=300):
            """Генерация биометрических данных"""
            logger.info(f"Генерация {count} биометрических записей...")

            users_df = self.data.get('users')
            if users_df is None:
                raise ValueError("Сначала сгенерируйте пользователей")

            users_with_biometric = users_df[users_df['biometric_enabled'] == True]

            biometric_types = ['fingerprint', 'face', 'voice', 'iris']
            biometric_weights = [0.5, 0.3, 0.15, 0.05]

            biometric_data = []
            used_combinations = set()

            for i in range(1, count + 1):
                # Выбор случайного пользователя с биометрией
                user = users_with_biometric.sample(n=1).iloc[0]

                # Выбор уникального типа биометрии для пользователя
                while True:
                    bio_type = random.choices(biometric_types, weights=biometric_weights)[0]
                    key = (user['id_user'], bio_type)
                    if key not in used_combinations:
                        used_combinations.add(key)
                        break

                # Генерация биометрического шаблона (симуляция)
                template_hash = hashlib.sha256(
                    f"{user['id_user']}_{bio_type}_{random.random()}".encode()
                ).hexdigest()[:16]

                biometric = {
                    'biometric_id': i,
                    'id_user': int(user['id_user']),
                    'biometric_type': bio_type,
                    'template_hash': template_hash,
                    'confidence_score': round(random.uniform(0.75, 0.99), 2),
                    'creation_date': fake.date_time_between(
                        start_date=user['created_at'],
                        end_date='now'
                    ),
                    'last_used': fake.date_time_between(start_date='-30d', end_date='now'),
                    'is_active': random.random() < 0.9,  # 90% активных
                    'failed_attempts': np.random.poisson(0.3),
                    'device_name': random.choice([
                        'iPhone 13', 'MacBook Pro', 'Samsung Galaxy', 'iPad Pro',
                        'Windows PC', 'Android Phone', 'Biometric Scanner'
                    ])
                }
                biometric_data.append(biometric)

            self.data['biometric_data'] = pd.DataFrame(biometric_data)
            logger.info(f"✓ Сгенерировано {len(biometric_data)} биометрических записей")
            return self.data['biometric_data']

        def generate_educational_programs(self, count=50):
            """Генерация образовательных программ"""
            logger.info(f"Генерация {count} образовательных программ...")

            # Шаблоны названий программ
            program_templates = {
                'Technical': [
                    'Python для начинающих', 'Продвинутый Java', 'Веб-разработка на React',
                    'DevOps практики', 'Кибербезопасность', 'Облачные технологии AWS',
                    'SQL оптимизация', 'Алгоритмы и структуры данных', 'Machine Learning',
                    'Data Science с нуля', 'Docker и Kubernetes', 'Microservices архитектура'
                ],
                'Management': [
                    'Управление проектами', 'Agile и Scrum', 'Лидерство для руководителей',
                    'Управление командой', 'Стратегический менеджмент', 'Тайм-менеджмент',
                    'Управление изменениями', 'Эмоциональный интеллект для руководителей'
                ],
                'Soft Skills': [
                    'Эффективная коммуникация', 'Публичные выступления', 'Конфликтология',
                    'Навыки переговоров', 'Критическое мышление', 'Креативность в бизнесе'
                ],
                'Compliance': [
                    'Трудовое законодательство', 'Защита персональных данных',
                    'Антикоррупционная политика', 'Охрана труда', 'Пожарная безопасность'
                ],
                'Safety': [
                    'Первая помощь', 'Промышленная безопасность', 'Электробезопасность',
                    'Безопасность на производстве', 'Экологическая безопасность'
                ]
            }

            providers = [
                'Internal Academy', 'Coursera', 'Udemy', 'LinkedIn Learning',
                'Stepik', 'Skillbox', 'GeekBrains', 'OTUS', 'Нетология', 'Eduson'
            ]

            programs = []
            years = [2023, 2024, 2025, 2026]

            for i in range(1, count + 1):
                category = random.choices(
                    list(program_templates.keys()),
                    weights=[0.4, 0.25, 0.2, 0.1, 0.05]
                )[0]

                name = random.choice(program_templates[category])
                if random.random() > 0.5:
                    name += f" (Уровень {random.choice(['1', '2', '3'])})"

                year = random.choice(years)
                protocol_number = f"ПРОТ-{year}-{random.randint(100, 999)}"

                start_date = fake.date_between(
                    start_date=f'-{random.randint(1, 3)}y',
                    end_date='+6m'
                )
                duration_days = random.randint(7, 180)
                end_date = start_date + timedelta(days=duration_days)

                program = {
                    'Education_id': i,
                    'Name': name,
                    'Category': category,
                    'Protocol_number': protocol_number,
                    'Description': fake.text(max_nb_chars=200),
                    'Provider': random.choice(providers),
                    'Duration_hours': random.randint(4, 160),
                    'Start_date': start_date,
                    'End_date': end_date,
                    'Cost': random.randint(5000, 150000),
                    'Max_participants': random.randint(10, 100),
                    'Format': random.choice(['online', 'offline', 'mixed']),
                    'Is_active': random.random() < 0.8,
                    'Created_at': fake.date_time_between(start_date='-2y', end_date='-1m')
                }
                programs.append(program)

            self.data['educational_programs'] = pd.DataFrame(programs)
            logger.info(f"✓ Сгенерировано {len(programs)} образовательных программ")
            return self.data['educational_programs']

        def generate_training_assignments(self, count=2000):
            """Генерация назначений на обучение"""
            logger.info(f"Генерация {count} записей об обучении...")

            employees_df = self.data['employees']
            programs_df = self.data['educational_programs']

            statuses = ['planned', 'in_progress', 'completed', 'cancelled']
            status_weights = [0.25, 0.15, 0.55, 0.05]

            assignments = []

            for i in range(1, count + 1):
                # Выбор случайного сотрудника и программы
                employee = employees_df.sample(n=1).iloc[0]
                program = programs_df.sample(n=1).iloc[0]

                # Генерация дат
                start_date = fake.date_between(start_date='-2y', end_date='+3m')

                # Длительность от 7 до 180 дней
                duration = random.randint(7, 180)
                end_date = start_date + timedelta(days=duration)

                # Статус с учетом дат
                status = random.choices(statuses, weights=status_weights)[0]

                if status == 'completed':
                    completion_date = end_date - timedelta(days=random.randint(0, 10))
                    result = random.choice(['Passed', 'Passed', 'Passed', 'Failed'])
                    score = random.randint(60, 100) if result == 'Passed' else random.randint(30, 59)
                elif status == 'in_progress':
                    completion_date = None
                    result = None
                    score = None
                elif status == 'planned':
                    completion_date = None
                    result = None
                    score = None
                else:  # cancelled
                    completion_date = None
                    result = 'Cancelled'
                    score = None
                    # Дата отмены раньше окончания
                    end_date = start_date + timedelta(days=random.randint(1, duration // 2))

                assignment = {
                    'id_worker_education': i,
                    'Worker_id': int(employee['Worker_id']),
                    'Education_id': int(program['Education_id']),
                    'Begin_date': start_date,
                    'End_date': end_date,
                    'status': status,
                    'completion_date': completion_date,
                    'result': result,
                    'score': score,
                    'feedback': fake.text(max_nb_chars=100) if status == 'completed' and random.random() > 0.5 else None
                }
                assignments.append(assignment)

            self.data['training_assignments'] = pd.DataFrame(assignments)
            logger.info(f"✓ Сгенерировано {len(assignments)} записей об обучении")
            return self.data['training_assignments']

        def generate_recommendations(self, count=1000):
            """Генерация рекомендаций по обучению"""
            logger.info(f"Генерация {count} рекомендаций...")

            employees_df = self.data['employees']
            programs_df = self.data['educational_programs']
            trainings_df = self.data.get('training_assignments', pd.DataFrame())

            recommendations = []
            used_combinations = set()

            # Получаем список уже пройденных обучений
            completed_trainings = set()
            if not trainings_df.empty:
                for _, row in trainings_df.iterrows():
                    completed_trainings.add((row['Worker_id'], row['Education_id']))

            for i in range(1, count + 1):
                # Выбор случайного сотрудника
                employee = employees_df.sample(n=1).iloc[0]

                # Выбор программы, которую сотрудник еще не проходил
                attempts = 0
                while attempts < 100:  # Защита от бесконечного цикла
                    program = programs_df.sample(n=1).iloc[0]

                    key = (employee['Worker_id'], program['Education_id'])
                    if key not in completed_trainings and key not in used_combinations:
                        used_combinations.add(key)
                        break
                    attempts += 1

                if attempts >= 100:
                    continue  # Пропускаем, если не нашли подходящую

                # Расчет скоринга рекомендации
                base_score = random.uniform(0.6, 0.95)

                # Повышаем скоринг, если программа соответствует должности
                if (employee['Department'] == 'IT' and program['Category'] == 'Technical') or \
                        (employee['Department'] == 'HR' and program['Category'] in ['Management', 'Soft Skills']) or \
                        (employee['Department'] == 'Sales' and program['Category'] in ['Management', 'Soft Skills']):
                    base_score += 0.15

                score = min(base_score, 1.0)

                # Причины рекомендации
                reasons = [
                    'Соответствует вашей должности',
                    'Популярная программа в вашем отделе',
                    'Рекомендовано на основе ваших навыков',
                    'Необходимо для карьерного роста',
                    'Обязательное обучение',
                    'Повышение квалификации'
                ]

                recommendation = {
                    'recommendation_id': i,
                    'worker_id': int(employee['Worker_id']),
                    'education_id': int(program['Education_id']),
                    'score': round(score, 2),
                    'reason': random.choice(reasons),
                    'creation_date': fake.date_time_between(start_date='-3m', end_date='now'),
                    'is_viewed': random.random() < 0.4,
                    'is_accepted': random.random() < 0.2,
                    'priority': random.randint(1, 5)
                }
                recommendations.append(recommendation)

            self.data['recommendations'] = pd.DataFrame(recommendations)
            logger.info(f"✓ Сгенерировано {len(recommendations)} рекомендаций")
            return self.data['recommendations']

        def validate_data(self):
            """Валидация сгенерированных данных"""
            logger.info("Валидация данных...")

            validation_results = {}

            # Проверка уникальности email сотрудников
            employees_df = self.data.get('employees')
            if employees_df is not None:
                unique_emails = employees_df['email'].nunique() == len(employees_df)
                validation_results['employees_unique_emails'] = unique_emails
                logger.info(f"✓ Уникальность email сотрудников: {unique_emails}")

            # Проверка связей внешних ключей
            if all(k in self.data for k in ['training_assignments', 'employees']):
                assignments_df = self.data['training_assignments']
                employees_ids = set(self.data['employees']['Worker_id'])
                valid_employees = assignments_df['Worker_id'].isin(employees_ids).all()
                validation_results['valid_employee_refs'] = valid_employees
                logger.info(f"✓ Корректность ссылок на сотрудников: {valid_employees}")

            # Проверка дат
            if 'training_assignments' in self.data:
                assignments_df = self.data['training_assignments']
                valid_dates = (assignments_df['End_date'] >= assignments_df['Begin_date']).all()
                validation_results['valid_training_dates'] = valid_dates
                logger.info(f"✓ Корректность дат обучения: {valid_dates}")

            # Проверка скоринга рекомендаций
            if 'recommendations' in self.data:
                recommendations_df = self.data['recommendations']
                valid_scores = (recommendations_df['score'].between(0, 1)).all()
                validation_results['valid_scores'] = valid_scores
                logger.info(f"✓ Корректность скоринга: {valid_scores}")

            return validation_results

        def generate_all(self):
            """Генерация всех данных"""
            logger.info("=" * 60)
            logger.info("НАЧАЛО ГЕНЕРАЦИИ ТЕСТОВЫХ ДАННЫХ")
            logger.info("=" * 60)

            self.generate_employees(500)
            self.generate_users(100)
            self.generate_biometric_data(300)
            self.generate_educational_programs(50)
            self.generate_training_assignments(2000)
            self.generate_recommendations(1000)

            validation = self.validate_data()

            logger.info("=" * 60)
            logger.info("ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
            logger.info("=" * 60)

            return self.data, validation

        def export_to_csv(self, output_dir='generated_data'):
            """Экспорт данных в CSV файлы"""
            import os
            import shutil

            os.makedirs(output_dir, exist_ok=True)

            for table_name, df in self.data.items():
                output_file = os.path.join(output_dir, f"{table_name}.csv")
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                logger.info(f"✓ Сохранено: {output_file}")

            # Создание архива
            shutil.make_archive(
                'training_data_archive',
                'zip',
                output_dir
            )
            logger.info(f"✓ Создан архив: training_data_archive.zip")

            return output_dir

    def generate_report(data, validation, output_file='generation_report.md'):
        """Генерация отчета в формате Markdown"""

        report = f"""# ОТЧЕТ ПО ГЕНЕРАЦИИ ТЕСТОВЫХ ДАННЫХ
    ## Дата: {datetime.now().strftime('%d %B %Y г.')}

    ## 1. Цель работы
    Заполнение базы данных системы управления обучением тестовыми данными.

    ## 2. Результаты генерации

    ### 2.1 Объемы данных

    | Таблица | Количество записей |
    |---------|-------------------|
    """

        tables_info = {
            'employees': 'Сотрудники',
            'users': 'Пользователи',
            'biometric_data': 'Биометрия',
            'educational_programs': 'Образовательные программы',
            'training_assignments': 'Назначения на обучение',
            'recommendations': 'Рекомендации'
        }

        for table_key, table_name in tables_info.items():
            if table_key in data:
                report += f"| {table_name} | {len(data[table_key])} |\n"

        report += """
    ### 2.2 Валидация данных

    | Проверка | Результат |
    |----------|-----------|
    """

        for check, result in validation.items():
            result_str = "✅ Успешно" if result else "❌ Ошибка"
            check_names = {
                'employees_unique_emails': 'Уникальность email сотрудников',
                'valid_employee_refs': 'Корректность ссылок на сотрудников',
                'valid_training_dates': 'Корректность дат обучения',
                'valid_scores': 'Корректность скоринга'
            }
            check_name = check_names.get(check, check)
            report += f"| {check_name} | {result_str} |\n"

        report += """
    ## 3. Состав архива

    Архив `training_data_archive.zip` содержит:
    - employees.csv
    - users.csv
    - biometric_data.csv
    - educational_programs.csv
    - training_assignments.csv
    - recommendations.csv

    ## 4. Выводы

    Генерация тестовых данных выполнена успешно. Все данные соответствуют структуре БД и готовы к использованию.
    """

        # Сохранение отчета
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"✓ Отчет сохранен: {output_file}")
        return report

    # ============== ЗАМЕНИТЕ СУЩЕСТВУЮЩИЙ БЛОК if __name__ == "__main__" НА ЭТОТ ==============

    if __name__ == "__main__":
        print("=" * 60)
        print("ГЕНЕРАТОР ТЕСТОВЫХ ДАННЫХ")
        print("=" * 60)

        # Создаем генератор
        generator = TrainingDataGenerator()

        # Генерируем все данные
        data, validation = generator.generate_all()

        # Экспортируем в CSV
        generator.export_to_csv('generated_data')

        # Генерируем отчет
        generate_report(data, validation, 'generation_report.md')

        print("=" * 60)
        print("ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 60)
        print("Результаты сохранены в папке: generated_data")
        print("Отчет: generation_report.md")
        print("Архив: training_data_archive.zip")