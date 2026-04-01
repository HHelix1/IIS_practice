# prompt_for_data_generation.py
"""
ПРОМПТ ДЛЯ ГЕНЕРАЦИИ ТЕСТОВЫХ ДАННЫХ
Система учета обучения сотрудников
Дата: 04 марта 2026 г.
"""

DATA_GENERATION_PROMPT = {
    "project": "Employee Training System",
    "description": "Генерация синтетических данных для тестирования системы учета обучения сотрудников",

    "business_rules": {
        "employees": [
            "Каждый сотрудник имеет уникальный email",
            "Дата рождения: от 1960 до 2005 года",
            "Стаж работы: от 1 до 40 лет",
            "Телефон в формате +7XXXXXXXXXX",
            "Должности: Software Engineer, HR Manager, Sales Director, Marketing Specialist, Financial Analyst, Operations Manager, QA Engineer, DevOps Engineer, Product Manager, Business Analyst"
        ],

        "users": [
            "Каждый пользователь связан с сотрудником",
            "Email пользователя совпадает с email сотрудника",
            "Права доступа: admin (10%), hr (20%), manager (30%), user (40%)",
            "Биометрия включена у 60% пользователей"
        ],

        "biometric_data": [
            "Типы: fingerprint (50%), face (30%), voice (15%), iris (5%)",
            "Дата создания: последние 2 года",
            "У каждого пользователя может быть несколько типов",
            "Статус: active (90%), inactive (10%)"
        ],

        "educational_programs": [
            "Номер протокола: ПРОТ-ГГГГ-XXXX (уникальный)",
            "Названия: на основе реальных курсов",
            "Категории: Technical (40%), Management (25%), Soft Skills (20%), Compliance (10%), Safety (5%)",
            "Провайдеры: Internal Academy, Coursera, Udemy, LinkedIn Learning, Stepik, Skillbox"
        ],

        "training_assignments": [
            "Дата начала: от 2023-01-01 до 2026-03-04",
            "Длительность: от 7 до 180 дней",
            "Статусы: planned (25%), in_progress (15%), completed (55%), cancelled (5%)",
            "У сотрудника не может быть пересекающихся назначений"
        ],

        "recommendations": [
            "Оценка рекомендации (score): от 0.6 до 1.0",
            "Основание: на основе профиля сотрудника",
            "Дата создания: последние 3 месяца"
        ]
    },

    "data_volume": {
        "users": 100,
        "employees": 500,
        "biometric_data": 300,
        "educational_programs": 50,
        "training_assignments": 2000,
        "recommendations": 1000
    },

    "statistical_properties": {
        "correlations": [
            {"from": "employees.position", "to": "educational_programs.category", "strength": 0.7},
            {"from": "employees.work_duration", "to": "training_assignments.status", "strength": 0.5}
        ],
        "distributions": {
            "employees.work_duration": "exponential(mean=8)",
            "training_assignments.duration": "normal(mean=30, std=15)",
            "recommendations.score": "beta(alpha=5, beta=2)"
        }
    }
}