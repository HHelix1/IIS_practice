from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, DateTime, text, inspect, func, and_
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional, List
from datetime import date, datetime, timedelta
import uvicorn
import logging
import random
import pandas as pd
import numpy as np
from faker import Faker
import os
import shutil
import sys
import time

# ==================== НАСТРОЙКА ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

fake = Faker('ru_RU')
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# ==================== БАЗА ДАННЫХ ====================
SQLALCHEMY_DATABASE_URL = "sqlite:///./employee_training.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==================== МОДЕЛИ БД ====================

class User(Base):
    """Пользователь"""
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    Full_name = Column(String(255), nullable=False)
    Position = Column(String(100), nullable=True)
    email = Column(String(100), nullable=False, unique=True)
    Phone_number = Column(String(20), nullable=True)
    Birth_date = Column(Date, nullable=True)
    Work_duration = Column(Date, nullable=True)

    biometrics = relationship("Biometric", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user")


class Employee(Base):
    """Сотрудники"""
    __tablename__ = "employees"

    Worker_id = Column(Integer, primary_key=True, index=True)
    Full_name = Column(String(255), nullable=False)
    Position = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    Phone_number = Column(String(20), nullable=False)
    Birth_date = Column(Date, nullable=True)
    Work_duration = Column(Date, nullable=True)

    trainings = relationship("Training", back_populates="employee", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="employee")


class EducationProgram(Base):
    """Образовательная программа"""
    __tablename__ = "education_programs"

    Education_Id = Column(Integer, primary_key=True, index=True)
    Protocol_number = Column(Integer, nullable=False, unique=True)
    Name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trainings = relationship("Training", back_populates="program", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="program")


class Training(Base):
    """Сотрудник и обучение"""
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    Worker_id = Column(Integer, ForeignKey("employees.Worker_id", ondelete="CASCADE"))
    Education_Id = Column(Integer, ForeignKey("education_programs.Education_Id", ondelete="CASCADE"))
    Begin_date = Column(Date, nullable=False)
    End_date = Column(Date, nullable=False)
    status = Column(String(50), default="planned")

    employee = relationship("Employee", back_populates="trainings")
    program = relationship("EducationProgram", back_populates="trainings")


class Biometric(Base):
    """Биометрия"""
    __tablename__ = "biometrics"

    biometric_id = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user", ondelete="CASCADE"))
    biometric_type = Column(String(50), nullable=False)
    creation_date = Column(Date, nullable=False, default=date.today)

    user = relationship("User", back_populates="biometrics")


class Recommendation(Base):
    """Рекомендация по обучению"""
    __tablename__ = "recommendations"

    recommendation_id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("employees.Worker_id", ondelete="CASCADE"))
    education_id = Column(Integer, ForeignKey("education_programs.Education_Id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id_user", ondelete="SET NULL"), nullable=True)
    score = Column(Integer, nullable=False)
    creation_date = Column(Date, nullable=False, default=date.today)

    employee = relationship("Employee", back_populates="recommendations")
    program = relationship("EducationProgram", back_populates="recommendations")
    user = relationship("User", back_populates="recommendations")


# ==================== НАСТРОЙКА ШАБЛОНОВ ====================
templates = Jinja2Templates(directory="templates")

# Создаем папку для шаблонов, если её нет
os.makedirs("templates", exist_ok=True)

# Создаем HTML шаблоны
with open("templates/base.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Система обучения сотрудников{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .navbar-brand { font-weight: bold; }
        .footer { margin-top: 50px; padding: 20px 0; background-color: #f8f9fa; }
        .recommendation-card { transition: transform 0.2s; }
        .recommendation-card:hover { transform: translateY(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .score-high { color: #28a745; font-weight: bold; }
        .score-medium { color: #ffc107; font-weight: bold; }
        .score-low { color: #dc3545; font-weight: bold; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">🎓 Система обучения</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Главная</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/employees">Сотрудники</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/programs">Программы</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/recommendations">Рекомендации</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>

    <footer class="footer">
        <div class="container text-center">
            <p class="text-muted">© 2024 Система учета обучения сотрудников</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>""")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write("""{% extends "base.html" %}

{% block title %}Главная - Система обучения{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col">
        <h1>Система учета обучения сотрудников</h1>
        <p class="lead">Поиск рекомендаций по обучению для сотрудников</p>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-8 mx-auto">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Поиск сотрудника для получения рекомендаций</h5>
            </div>
            <div class="card-body">
                <form id="searchForm" onsubmit="searchEmployee(event)">
                    <div class="input-group mb-3">
                        <input type="text" id="searchInput" class="form-control form-control-lg" 
                               placeholder="Введите ФИО сотрудника или email" required>
                        <button class="btn btn-primary" type="submit">
                            <span class="spinner-border spinner-border-sm d-none" id="searchSpinner" role="status"></span>
                            Найти
                        </button>
                    </div>
                </form>
                <div id="searchResults"></div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-4 mb-3">
        <div class="card text-center h-100">
            <div class="card-body">
                <h3 class="card-title">{{ stats.employees }}</h3>
                <p class="card-text">Сотрудников</p>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-3">
        <div class="card text-center h-100">
            <div class="card-body">
                <h3 class="card-title">{{ stats.education_programs }}</h3>
                <p class="card-text">Программ обучения</p>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-3">
        <div class="card text-center h-100">
            <div class="card-body">
                <h3 class="card-title">{{ stats.recommendations }}</h3>
                <p class="card-text">Рекомендаций</p>
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">⚡ Быстрый доступ</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <a href="/employees" class="btn btn-outline-primary w-100 mb-2">Сотрудники</a>
                    </div>
                    <div class="col-md-3">
                        <a href="/programs" class="btn btn-outline-success w-100 mb-2">Программы</a>
                    </div>
                    <div class="col-md-3">
                        <a href="/recommendations" class="btn btn-outline-info w-100 mb-2">Рекомендации</a>
                    </div>
                    <div class="col-md-3">
                        <button onclick="generateData()" class="btn btn-outline-warning w-100 mb-2"> Сгенерировать данные</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
<script>
function searchEmployee(event) {
    event.preventDefault();
    const query = document.getElementById('searchInput').value;
    const spinner = document.getElementById('searchSpinner');
    const resultsDiv = document.getElementById('searchResults');

    spinner.classList.remove('d-none');

    fetch(`/api/search-employee?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.found) {
                window.location.href = `/employee/${data.worker_id}/recommendations`;
            } else {
                resultsDiv.innerHTML = `
                    <div class="alert alert-warning">
                        Сотрудник не найден. Показаны похожие результаты:
                        <ul class="mt-2">
                            ${data.similar.map(e => `<li><a href="/employee/${e.Worker_id}/recommendations">${e.Full_name} (${e.Position})</a></li>`).join('')}
                        </ul>
                    </div>
                `;
            }
        })
        .catch(error => {
            resultsDiv.innerHTML = `<div class="alert alert-danger">Ошибка: ${error}</div>`;
        })
        .finally(() => {
            spinner.classList.add('d-none');
        });
}

function generateData() {
    if (confirm('Сгенерировать тестовые данные? Это может занять некоторое время.')) {
        fetch('/api/generate-data', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                alert('Данные успешно сгенерированы!');
                location.reload();
            })
            .catch(error => {
                alert('Ошибка при генерации данных: ' + error);
            });
    }
}
</script>
{% endblock %}""")

with open("templates/employees.html", "w", encoding="utf-8") as f:
    f.write("""{% extends "base.html" %}

{% block title %}Сотрудники{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col">
        <h1>Сотрудники</h1>
    </div>
    <div class="col-auto">
        <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addEmployeeModal">
            + Добавить сотрудника
        </button>
    </div>
</div>

<div class="row mb-3">
    <div class="col">
        <input type="text" id="searchInput" class="form-control" placeholder="Поиск по ФИО или email...">
    </div>
</div>

<div class="row">
    <div class="col">
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>ФИО</th>
                        <th>Должность</th>
                        <th>Email</th>
                        <th>Телефон</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody id="employeesTable">
                    {% for employee in employees %}
                    <tr>
                        <td>{{ employee.Worker_id }}</td>
                        <td>{{ employee.Full_name }}</td>
                        <td>{{ employee.Position }}</td>
                        <td>{{ employee.email }}</td>
                        <td>{{ employee.Phone_number }}</td>
                        <td>
                            <a href="/employee/{{ employee.Worker_id }}/recommendations" class="btn btn-sm btn-info">
                                Рекомендации
                            </a>
                            <button class="btn btn-sm btn-warning" onclick="editEmployee({{ employee.Worker_id }})">
                                
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteEmployee({{ employee.Worker_id }})">
                                ️
                            </button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Модальное окно добавления сотрудника -->
<div class="modal fade" id="addEmployeeModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Добавить сотрудника</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="addEmployeeForm">
                    <div class="mb-3">
                        <label class="form-label">ФИО *</label>
                        <input type="text" name="Full_name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Должность *</label>
                        <input type="text" name="Position" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email *</label>
                        <input type="email" name="email" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Телефон *</label>
                        <input type="text" name="Phone_number" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Дата рождения</label>
                        <input type="date" name="Birth_date" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Дата начала работы</label>
                        <input type="date" name="Work_duration" class="form-control">
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-primary" onclick="saveEmployee()">Сохранить</button>
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
<script>
document.getElementById('searchInput').addEventListener('keyup', function() {
    const searchText = this.value.toLowerCase();
    const rows = document.querySelectorAll('#employeesTable tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchText) ? '' : 'none';
    });
});

function saveEmployee() {
    const form = document.getElementById('addEmployeeForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Преобразуем пустые даты в null
    if (!data.Birth_date) data.Birth_date = null;
    if (!data.Work_duration) data.Work_duration = null;

    fetch('/api/employees/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            return response.json().then(err => { throw new Error(err.detail); });
        }
    })
    .catch(error => {
        alert('Ошибка: ' + error.message);
    });
}

function deleteEmployee(id) {
    if (confirm('Удалить сотрудника?')) {
        fetch(`/api/employees/${id}`, { method: 'DELETE' })
            .then(response => {
                if (response.ok) {
                    location.reload();
                } else {
                    alert('Ошибка при удалении');
                }
            });
    }
}

function editEmployee(id) {
    alert('Редактирование сотрудника будет доступно в следующей версии');
}
</script>
{% endblock %}""")

with open("templates/employee_recommendations.html", "w", encoding="utf-8") as f:
    f.write("""{% extends "base.html" %}

{% block title %}Рекомендации для {{ employee.Full_name }}{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/">Главная</a></li>
                <li class="breadcrumb-item"><a href="/employees">Сотрудники</a></li>
                <li class="breadcrumb-item active">{{ employee.Full_name }}</li>
            </ol>
        </nav>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">👤 Информация о сотруднике</h5>
            </div>
            <div class="card-body">
                <h4>{{ employee.Full_name }}</h4>
                <p><strong>Должность:</strong> {{ employee.Position }}</p>
                <p><strong>Email:</strong> {{ employee.email }}</p>
                <p><strong>Телефон:</strong> {{ employee.Phone_number }}</p>
                {% if employee.Birth_date %}
                <p><strong>Дата рождения:</strong> {{ employee.Birth_date.strftime('%d.%m.%Y') }}</p>
                {% endif %}
                {% if employee.Work_duration %}
                <p><strong>Дата начала работы:</strong> {{ employee.Work_duration.strftime('%d.%m.%Y') }}</p>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="col-md-8">
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">Статистика</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-sm-4">
                        <div class="text-center">
                            <h3>{{ stats.total_trainings }}</h3>
                            <p>Всего обучений</p>
                        </div>
                    </div>
                    <div class="col-sm-4">
                        <div class="text-center">
                            <h3>{{ stats.completed_trainings }}</h3>
                            <p>Завершено</p>
                        </div>
                    </div>
                    <div class="col-sm-4">
                        <div class="text-center">
                            <h3>{{ stats.avg_score|round(1) }}</h3>
                            <p>Средний балл</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col">
        <div class="card">
            <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Рекомендованные программы обучения</h5>
                <span class="badge bg-light text-dark">{{ recommendations|length }} рекомендаций</span>
            </div>
            <div class="card-body">
                {% if recommendations %}
                <div class="row">
                    {% for rec in recommendations %}
                    <div class="col-md-6 mb-3">
                        <div class="card recommendation-card h-100">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start">
                                    <h5 class="card-title">{{ rec.program.Name }}</h5>
                                    <span class="badge {% if rec.score >= 80 %}bg-success{% elif rec.score >= 60 %}bg-warning{% else %}bg-danger{% endif %}">
                                        {{ rec.score }}%
                                    </span>
                                </div>
                                <h6 class="card-subtitle mb-2 text-muted">
                                    Протокол №{{ rec.program.Protocol_number }}
                                </h6>
                                <p class="card-text">
                                    <small>Рекомендовано: {{ rec.creation_date.strftime('%d.%m.%Y') }}</small>
                                </p>
                                {% if rec.user %}
                                <p class="card-text">
                                    <small>Менеджер: {{ rec.user.Full_name }}</small>
                                </p>
                                {% endif %}
                                <button class="btn btn-sm btn-outline-primary" 
                                        onclick="assignTraining({{ employee.Worker_id }}, {{ rec.program.Education_Id }})">
                                    Назначить обучение
                                </button>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="alert alert-info">
                    Нет рекомендаций для этого сотрудника. 
                    <button class="btn btn-sm btn-primary" onclick="generateRecommendations({{ employee.Worker_id }})">
                        Сгенерировать рекомендации
                    </button>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<div class="row mt-4">
    <div class="col">
        <div class="card">
            <div class="card-header bg-secondary text-white">
                <h5 class="mb-0">История обучений</h5>
            </div>
            <div class="card-body">
                {% if trainings %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Программа</th>
                                <th>Дата начала</th>
                                <th>Дата окончания</th>
                                <th>Статус</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for training in trainings %}
                            <tr>
                                <td>{{ training.program.Name }}</td>
                                <td>{{ training.Begin_date.strftime('%d.%m.%Y') }}</td>
                                <td>{{ training.End_date.strftime('%d.%m.%Y') }}</td>
                                <td>
                                    <span class="badge {% if training.status == 'completed' %}bg-success{% elif training.status == 'in_progress' %}bg-primary{% elif training.status == 'planned' %}bg-info{% else %}bg-secondary{% endif %}">
                                        {{ training.status }}
                                    </span>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="alert alert-secondary">
                    Нет записей об обучении
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
<script>
function assignTraining(workerId, programId) {
    const data = {
        Worker_id: workerId,
        Education_Id: programId,
        Begin_date: new Date().toISOString().split('T')[0],
        End_date: new Date(Date.now() + 90*24*60*60*1000).toISOString().split('T')[0],
        status: 'planned'
    };

    fetch('/api/trainings/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        alert('Обучение успешно назначено!');
        location.reload();
    })
    .catch(error => {
        alert('Ошибка: ' + error);
    });
}

function generateRecommendations(workerId) {
    fetch(`/api/generate-employee-recommendations/${workerId}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            alert(`Сгенерировано ${data.count} рекомендаций`);
            location.reload();
        })
        .catch(error => {
            alert('Ошибка: ' + error);
        });
}
</script>
{% endblock %}""")

with open("templates/programs.html", "w", encoding="utf-8") as f:
    f.write("""{% extends "base.html" %}

{% block title %}Программы обучения{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col">
        <h1>Программы обучения</h1>
    </div>
    <div class="col-auto">
        <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addProgramModal">
            + Добавить программу
        </button>
    </div>
</div>

<div class="row mb-3">
    <div class="col">
        <input type="text" id="searchInput" class="form-control" placeholder="Поиск по названию или номеру протокола...">
    </div>
</div>

<div class="row">
    <div class="col">
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Номер протокола</th>
                        <th>Название программы</th>
                        <th>Дата создания</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody id="programsTable">
                    {% for program in programs %}
                    <tr>
                        <td>{{ program.Education_Id }}</td>
                        <td>{{ program.Protocol_number }}</td>
                        <td>{{ program.Name }}</td>
                        <td>{{ program.created_at.strftime('%d.%m.%Y') if program.created_at else 'Н/Д' }}</td>
                        <td>
                            <button class="btn btn-sm btn-warning" onclick="editProgram({{ program.Education_Id }})">
                                
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteProgram({{ program.Education_Id }})">
                                ️
                            </button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Модальное окно добавления программы -->
<div class="modal fade" id="addProgramModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Добавить программу обучения</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="addProgramForm">
                    <div class="mb-3">
                        <label class="form-label">Номер протокола *</label>
                        <input type="number" name="Protocol_number" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Название программы *</label>
                        <input type="text" name="Name" class="form-control" required>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-primary" onclick="saveProgram()">Сохранить</button>
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
<script>
document.getElementById('searchInput').addEventListener('keyup', function() {
    const searchText = this.value.toLowerCase();
    const rows = document.querySelectorAll('#programsTable tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchText) ? '' : 'none';
    });
});

function saveProgram() {
    const form = document.getElementById('addProgramForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    fetch('/api/education/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            return response.json().then(err => { throw new Error(err.detail); });
        }
    })
    .catch(error => {
        alert('Ошибка: ' + error.message);
    });
}

function deleteProgram(id) {
    if (confirm('Удалить программу обучения?')) {
        fetch(`/api/education/${id}`, { method: 'DELETE' })
            .then(response => {
                if (response.ok) {
                    location.reload();
                } else {
                    alert('Ошибка при удалении');
                }
            });
    }
}

function editProgram(id) {
    alert('Редактирование программы будет доступно в следующей версии');
}
</script>
{% endblock %}""")

with open("templates/recommendations.html", "w", encoding="utf-8") as f:
    f.write("""{% extends "base.html" %}

{% block title %}Все рекомендации{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col">
        <h1>Рекомендации по обучению</h1>
        <p class="lead">Список всех рекомендаций, отсортированных по рейтингу</p>
    </div>
</div>

<div class="row mb-3">
    <div class="col-md-6">
        <input type="text" id="searchInput" class="form-control" placeholder="Поиск по сотруднику или программе...">
    </div>
    <div class="col-md-3">
        <select id="scoreFilter" class="form-select">
            <option value="all">Все оценки</option>
            <option value="high">Высокие (80-100)</option>
            <option value="medium">Средние (60-79)</option>
            <option value="low">Низкие (0-59)</option>
        </select>
    </div>
</div>

<div class="row">
    <div class="col">
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Сотрудник</th>
                        <th>Программа</th>
                        <th>Оценка</th>
                        <th>Дата</th>
                        <th>Менеджер</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody id="recommendationsTable">
                    {% for rec in recommendations %}
                    <tr data-score="{{ rec.score }}">
                        <td>{{ rec.recommendation_id }}</td>
                        <td>
                            <a href="/employee/{{ rec.employee.Worker_id }}/recommendations">
                                {{ rec.employee.Full_name }}
                            </a>
                        </td>
                        <td>{{ rec.program.Name }}</td>
                        <td>
                            <span class="badge {% if rec.score >= 80 %}bg-success{% elif rec.score >= 60 %}bg-warning{% else %}bg-danger{% endif %}">
                                {{ rec.score }}%
                            </span>
                        </td>
                        <td>{{ rec.creation_date.strftime('%d.%m.%Y') }}</td>
                        <td>
                            {% if rec.user %}
                                {{ rec.user.Full_name }}
                            {% else %}
                                <span class="text-muted">Не назначен</span>
                            {% endif %}
                        </td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="deleteRecommendation({{ rec.recommendation_id }})">
                                
                            </button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
<script>
document.getElementById('searchInput').addEventListener('keyup', filterTable);
document.getElementById('scoreFilter').addEventListener('change', filterTable);

function filterTable() {
    const searchText = document.getElementById('searchInput').value.toLowerCase();
    const scoreFilter = document.getElementById('scoreFilter').value;
    const rows = document.querySelectorAll('#recommendationsTable tr');

    rows.forEach(row => {
        let showRow = true;
        const text = row.textContent.toLowerCase();
        const score = parseInt(row.dataset.score);

        // Фильтр по тексту
        if (searchText && !text.includes(searchText)) {
            showRow = false;
        }

        // Фильтр по оценке
        if (scoreFilter === 'high' && score < 80) showRow = false;
        if (scoreFilter === 'medium' && (score < 60 || score >= 80)) showRow = false;
        if (scoreFilter === 'low' && score >= 60) showRow = false;

        row.style.display = showRow ? '' : 'none';
    });
}

function deleteRecommendation(id) {
    if (confirm('Удалить рекомендацию?')) {
        fetch(`/api/recommendations/${id}`, { method: 'DELETE' })
            .then(response => {
                if (response.ok) {
                    location.reload();
                } else {
                    alert('Ошибка при удалении');
                }
            });
    }
}
</script>
{% endblock %}""")

# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================

def init_db():
    """Инициализация базы данных - создает таблицы если их нет"""
    db_file = "employee_training.db"

    if os.path.exists(db_file):
        logger.info(f"База данных {db_file} уже существует")
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Существующие таблицы: {existing_tables}")
    else:
        logger.info(f"Создание новой базы данных: {db_file}")

    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы созданы/проверены в базе данных")


# ==================== СХЕМЫ PYDANTIC ====================

class UserCreate(BaseModel):
    Full_name: str
    Position: Optional[str] = None
    email: str
    Phone_number: Optional[str] = None
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Некорректный email')
        return v


class UserUpdate(BaseModel):
    Full_name: Optional[str] = None
    Position: Optional[str] = None
    email: Optional[str] = None
    Phone_number: Optional[str] = None
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v and '@' not in v:
            raise ValueError('Некорректный email')
        return v


class UserResponse(BaseModel):
    id_user: int
    Full_name: str
    Position: Optional[str] = None
    email: str
    Phone_number: Optional[str] = None
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    Full_name: str
    Position: str
    email: str
    Phone_number: str
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Некорректный email')
        return v


class EmployeeUpdate(BaseModel):
    Full_name: Optional[str] = None
    Position: Optional[str] = None
    email: Optional[str] = None
    Phone_number: Optional[str] = None
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v and '@' not in v:
            raise ValueError('Некорректный email')
        return v


class EmployeeResponse(BaseModel):
    Worker_id: int
    Full_name: str
    Position: str
    email: str
    Phone_number: str
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class EducationCreate(BaseModel):
    Protocol_number: int
    Name: str

    @field_validator('Protocol_number')
    @classmethod
    def validate_protocol(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Номер протокола должен быть положительным числом")
        return v


class EducationUpdate(BaseModel):
    Protocol_number: Optional[int] = None
    Name: Optional[str] = None

    @field_validator('Protocol_number')
    @classmethod
    def validate_protocol(cls, v: int) -> int:
        if v and v <= 0:
            raise ValueError("Номер протокола должен быть положительным числом")
        return v


class EducationResponse(BaseModel):
    Education_Id: int
    Protocol_number: int
    Name: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TrainingCreate(BaseModel):
    Worker_id: int
    Education_Id: int
    Begin_date: date
    End_date: date
    status: str = "planned"

    @model_validator(mode='after')
    def validate_dates(self):
        if self.End_date < self.Begin_date:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self


class TrainingUpdate(BaseModel):
    Worker_id: Optional[int] = None
    Education_Id: Optional[int] = None
    Begin_date: Optional[date] = None
    End_date: Optional[date] = None
    status: Optional[str] = None

    @model_validator(mode='after')
    def validate_dates(self):
        if self.Begin_date and self.End_date and self.End_date < self.Begin_date:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self


class TrainingResponse(BaseModel):
    id: int
    Worker_id: int
    Education_Id: int
    Begin_date: date
    End_date: date
    status: str

    model_config = ConfigDict(from_attributes=True)


class BiometricCreate(BaseModel):
    id_user: int
    biometric_type: str


class BiometricUpdate(BaseModel):
    biometric_type: Optional[str] = None


class BiometricResponse(BaseModel):
    biometric_id: int
    id_user: int
    biometric_type: str
    creation_date: date

    model_config = ConfigDict(from_attributes=True)


class RecommendationCreate(BaseModel):
    worker_id: int
    education_id: int
    user_id: Optional[int] = None
    score: int

    @field_validator('score')
    @classmethod
    def validate_score(cls, v: int) -> int:
        if v < 0 or v > 100:
            raise ValueError("Оценка должна быть от 0 до 100")
        return v


class RecommendationUpdate(BaseModel):
    worker_id: Optional[int] = None
    education_id: Optional[int] = None
    user_id: Optional[int] = None
    score: Optional[int] = None

    @field_validator('score')
    @classmethod
    def validate_score(cls, v: int) -> int:
        if v and (v < 0 or v > 100):
            raise ValueError("Оценка должна быть от 0 до 100")
        return v


class RecommendationResponse(BaseModel):
    recommendation_id: int
    worker_id: int
    education_id: int
    user_id: Optional[int] = None
    score: int
    creation_date: date

    model_config = ConfigDict(from_attributes=True)


# ==================== CRUD ОПЕРАЦИИ ====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== ПОЛЬЗОВАТЕЛИ ====================

def create_user(db: Session, user: UserCreate):
    try:
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail=f"Email {user.email} уже используется")

        db_user = User(**user.model_dump())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Создан пользователь с id: {db_user.id_user}")
        return db_user
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {str(e)}")
        db.rollback()
        raise


def get_users(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(User).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей: {str(e)}")
        raise


def get_user(db: Session, user_id: int):
    try:
        return db.query(User).filter(User.id_user == user_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {str(e)}")
        raise


def update_user(db: Session, user_id: int, user_update: UserUpdate):
    try:
        db_user = db.query(User).filter(User.id_user == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if user_update.email and user_update.email != db_user.email:
            existing_user = db.query(User).filter(User.email == user_update.email).first()
            if existing_user:
                raise HTTPException(status_code=400, detail=f"Email {user_update.email} уже используется")

        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.commit()
        db.refresh(db_user)
        logger.info(f"Обновлен пользователь с id: {user_id}")
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя: {str(e)}")
        db.rollback()
        raise


def delete_user(db: Session, user_id: int):
    try:
        db_user = db.query(User).filter(User.id_user == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        db.delete(db_user)
        db.commit()
        logger.info(f"Удален пользователь с id: {user_id}")
        return {"message": "Пользователь успешно удален"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {str(e)}")
        db.rollback()
        raise


# ==================== СОТРУДНИКИ ====================

def create_employee(db: Session, employee: EmployeeCreate):
    try:
        existing_employee = db.query(Employee).filter(Employee.email == employee.email).first()
        if existing_employee:
            raise HTTPException(status_code=400, detail=f"Email {employee.email} уже используется")

        db_employee = Employee(**employee.model_dump())
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        logger.info(f"Создан сотрудник с id: {db_employee.Worker_id}")
        return db_employee
    except Exception as e:
        logger.error(f"Ошибка при создании сотрудника: {str(e)}")
        db.rollback()
        raise


def get_employees(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(Employee).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении сотрудников: {str(e)}")
        raise


def get_employee(db: Session, worker_id: int):
    try:
        return db.query(Employee).filter(Employee.Worker_id == worker_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении сотрудника: {str(e)}")
        raise


def update_employee(db: Session, worker_id: int, employee_update: EmployeeUpdate):
    try:
        db_employee = db.query(Employee).filter(Employee.Worker_id == worker_id).first()
        if not db_employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        if employee_update.email and employee_update.email != db_employee.email:
            existing_employee = db.query(Employee).filter(Employee.email == employee_update.email).first()
            if existing_employee:
                raise HTTPException(status_code=400, detail=f"Email {employee_update.email} уже используется")

        update_data = employee_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_employee, field, value)

        db.commit()
        db.refresh(db_employee)
        logger.info(f"Обновлен сотрудник с id: {worker_id}")
        return db_employee
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении сотрудника: {str(e)}")
        db.rollback()
        raise


def delete_employee(db: Session, worker_id: int):
    try:
        db_employee = db.query(Employee).filter(Employee.Worker_id == worker_id).first()
        if not db_employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        db.delete(db_employee)
        db.commit()
        logger.info(f"Удален сотрудник с id: {worker_id}")
        return {"message": "Сотрудник успешно удален"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении сотрудника: {str(e)}")
        db.rollback()
        raise


# ==================== ОБРАЗОВАТЕЛЬНЫЕ ПРОГРАММЫ ====================

def create_education(db: Session, education: EducationCreate):
    try:
        existing_program = db.query(EducationProgram).filter(
            EducationProgram.Protocol_number == education.Protocol_number
        ).first()
        if existing_program:
            raise HTTPException(
                status_code=400,
                detail=f"Программа с номером протокола {education.Protocol_number} уже существует"
            )

        db_education = EducationProgram(**education.model_dump())
        db.add(db_education)
        db.commit()
        db.refresh(db_education)
        logger.info(f"Создана программа с id: {db_education.Education_Id}")
        return db_education
    except Exception as e:
        logger.error(f"Ошибка при создании программы: {str(e)}")
        db.rollback()
        raise


def get_educations(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(EducationProgram).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении программ: {str(e)}")
        raise


def get_education(db: Session, education_id: int):
    try:
        return db.query(EducationProgram).filter(EducationProgram.Education_Id == education_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении программы: {str(e)}")
        raise


def update_education(db: Session, education_id: int, education_update: EducationUpdate):
    try:
        db_education = db.query(EducationProgram).filter(EducationProgram.Education_Id == education_id).first()
        if not db_education:
            raise HTTPException(status_code=404, detail="Программа не найдена")

        if education_update.Protocol_number and education_update.Protocol_number != db_education.Protocol_number:
            existing_program = db.query(EducationProgram).filter(
                EducationProgram.Protocol_number == education_update.Protocol_number
            ).first()
            if existing_program:
                raise HTTPException(
                    status_code=400,
                    detail=f"Программа с номером протокола {education_update.Protocol_number} уже существует"
                )

        update_data = education_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_education, field, value)

        db.commit()
        db.refresh(db_education)
        logger.info(f"Обновлена программа с id: {education_id}")
        return db_education
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении программы: {str(e)}")
        db.rollback()
        raise


def delete_education(db: Session, education_id: int):
    try:
        db_education = db.query(EducationProgram).filter(EducationProgram.Education_Id == education_id).first()
        if not db_education:
            raise HTTPException(status_code=404, detail="Программа не найдена")

        db.delete(db_education)
        db.commit()
        logger.info(f"Удалена программа с id: {education_id}")
        return {"message": "Программа успешно удалена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении программы: {str(e)}")
        db.rollback()
        raise


# ==================== ОБУЧЕНИЕ ====================

def create_training(db: Session, training: TrainingCreate):
    try:
        employee = db.query(Employee).filter(Employee.Worker_id == training.Worker_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail=f"Сотрудник с id {training.Worker_id} не найден")

        program = db.query(EducationProgram).filter(EducationProgram.Education_Id == training.Education_Id).first()
        if not program:
            raise HTTPException(status_code=404, detail=f"Программа с id {training.Education_Id} не найдена")

        db_training = Training(**training.model_dump())
        db.add(db_training)
        db.commit()
        db.refresh(db_training)
        logger.info(f"Создано обучение с id: {db_training.id}")
        return db_training
    except Exception as e:
        logger.error(f"Ошибка при создании обучения: {str(e)}")
        db.rollback()
        raise


def get_trainings(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(Training).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении обучений: {str(e)}")
        raise


def get_training(db: Session, training_id: int):
    try:
        return db.query(Training).filter(Training.id == training_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении обучения: {str(e)}")
        raise


def get_employee_trainings(db: Session, worker_id: int):
    try:
        return db.query(Training).filter(Training.Worker_id == worker_id).all()
    except Exception as e:
        logger.error(f"Ошибка при получении обучений сотрудника: {str(e)}")
        raise


def update_training(db: Session, training_id: int, training_update: TrainingUpdate):
    try:
        db_training = db.query(Training).filter(Training.id == training_id).first()
        if not db_training:
            raise HTTPException(status_code=404, detail="Обучение не найдено")

        if training_update.Worker_id:
            employee = db.query(Employee).filter(Employee.Worker_id == training_update.Worker_id).first()
            if not employee:
                raise HTTPException(status_code=404, detail=f"Сотрудник с id {training_update.Worker_id} не найден")

        if training_update.Education_Id:
            program = db.query(EducationProgram).filter(
                EducationProgram.Education_Id == training_update.Education_Id).first()
            if not program:
                raise HTTPException(status_code=404, detail=f"Программа с id {training_update.Education_Id} не найдена")

        update_data = training_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_training, field, value)

        db.commit()
        db.refresh(db_training)
        logger.info(f"Обновлено обучение с id: {training_id}")
        return db_training
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении обучения: {str(e)}")
        db.rollback()
        raise


def delete_training(db: Session, training_id: int):
    try:
        db_training = db.query(Training).filter(Training.id == training_id).first()
        if not db_training:
            raise HTTPException(status_code=404, detail="Обучение не найдено")

        db.delete(db_training)
        db.commit()
        logger.info(f"Удалено обучение с id: {training_id}")
        return {"message": "Обучение успешно удалено"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении обучения: {str(e)}")
        db.rollback()
        raise


# ==================== БИОМЕТРИЯ ====================

def create_biometric(db: Session, biometric: BiometricCreate):
    try:
        user = db.query(User).filter(User.id_user == biometric.id_user).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"Пользователь с id {biometric.id_user} не найден")

        max_id = db.query(func.max(Biometric.biometric_id)).scalar() or 0
        new_id = max_id + 1

        db_biometric = Biometric(
            biometric_id=new_id,
            id_user=biometric.id_user,
            biometric_type=biometric.biometric_type,
            creation_date=date.today()
        )
        db.add(db_biometric)
        db.commit()
        db.refresh(db_biometric)
        logger.info(f"Создана биометрия с id: {db_biometric.biometric_id}")
        return db_biometric
    except Exception as e:
        logger.error(f"Ошибка при создании биометрии: {str(e)}")
        db.rollback()
        raise


def get_biometrics(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(Biometric).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении биометрии: {str(e)}")
        raise


def get_biometric(db: Session, biometric_id: int):
    try:
        return db.query(Biometric).filter(Biometric.biometric_id == biometric_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении биометрии: {str(e)}")
        raise


def get_user_biometrics(db: Session, user_id: int):
    try:
        return db.query(Biometric).filter(Biometric.id_user == user_id).all()
    except Exception as e:
        logger.error(f"Ошибка при получении биометрии пользователя: {str(e)}")
        raise


def update_biometric(db: Session, biometric_id: int, biometric_update: BiometricUpdate):
    try:
        db_biometric = db.query(Biometric).filter(Biometric.biometric_id == biometric_id).first()
        if not db_biometric:
            raise HTTPException(status_code=404, detail="Биометрия не найдена")

        update_data = biometric_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_biometric, field, value)

        db.commit()
        db.refresh(db_biometric)
        logger.info(f"Обновлена биометрия с id: {biometric_id}")
        return db_biometric
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении биометрии: {str(e)}")
        db.rollback()
        raise


def delete_biometric(db: Session, biometric_id: int):
    try:
        db_biometric = db.query(Biometric).filter(Biometric.biometric_id == biometric_id).first()
        if not db_biometric:
            raise HTTPException(status_code=404, detail="Биометрия не найдена")

        db.delete(db_biometric)
        db.commit()
        logger.info(f"Удалена биометрия с id: {biometric_id}")
        return {"message": "Биометрия успешно удалена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении биометрии: {str(e)}")
        db.rollback()
        raise


# ==================== РЕКОМЕНДАЦИИ ====================

def create_recommendation(db: Session, recommendation: RecommendationCreate):
    try:
        employee = db.query(Employee).filter(Employee.Worker_id == recommendation.worker_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail=f"Сотрудник с id {recommendation.worker_id} не найден")

        program = db.query(EducationProgram).filter(
            EducationProgram.Education_Id == recommendation.education_id).first()
        if not program:
            raise HTTPException(status_code=404, detail=f"Программа с id {recommendation.education_id} не найдена")

        if recommendation.user_id:
            user = db.query(User).filter(User.id_user == recommendation.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail=f"Пользователь с id {recommendation.user_id} не найден")

        max_id = db.query(func.max(Recommendation.recommendation_id)).scalar() or 0
        new_id = max_id + 1

        db_recommendation = Recommendation(
            recommendation_id=new_id,
            worker_id=recommendation.worker_id,
            education_id=recommendation.education_id,
            user_id=recommendation.user_id,
            score=recommendation.score,
            creation_date=date.today()
        )
        db.add(db_recommendation)
        db.commit()
        db.refresh(db_recommendation)
        logger.info(f"Создана рекомендация с id: {db_recommendation.recommendation_id}")
        return db_recommendation
    except Exception as e:
        logger.error(f"Ошибка при создании рекомендации: {str(e)}")
        db.rollback()
        raise


def get_recommendations(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(Recommendation).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {str(e)}")
        raise


def get_recommendation(db: Session, recommendation_id: int):
    try:
        return db.query(Recommendation).filter(Recommendation.recommendation_id == recommendation_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендации: {str(e)}")
        raise


def get_employee_recommendations(db: Session, worker_id: int):
    try:
        return db.query(Recommendation) \
            .filter(Recommendation.worker_id == worker_id) \
            .order_by(Recommendation.score.desc()) \
            .all()
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций сотрудника: {str(e)}")
        raise


def get_user_recommendations(db: Session, user_id: int):
    try:
        return db.query(Recommendation).filter(Recommendation.user_id == user_id).all()
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций пользователя: {str(e)}")
        raise


def update_recommendation(db: Session, recommendation_id: int, recommendation_update: RecommendationUpdate):
    try:
        db_recommendation = db.query(Recommendation).filter(
            Recommendation.recommendation_id == recommendation_id).first()
        if not db_recommendation:
            raise HTTPException(status_code=404, detail="Рекомендация не найдена")

        if recommendation_update.worker_id:
            employee = db.query(Employee).filter(Employee.Worker_id == recommendation_update.worker_id).first()
            if not employee:
                raise HTTPException(status_code=404,
                                    detail=f"Сотрудник с id {recommendation_update.worker_id} не найден")

        if recommendation_update.education_id:
            program = db.query(EducationProgram).filter(
                EducationProgram.Education_Id == recommendation_update.education_id).first()
            if not program:
                raise HTTPException(status_code=404,
                                    detail=f"Программа с id {recommendation_update.education_id} не найдена")

        if recommendation_update.user_id:
            user = db.query(User).filter(User.id_user == recommendation_update.user_id).first()
            if not user:
                raise HTTPException(status_code=404,
                                    detail=f"Пользователь с id {recommendation_update.user_id} не найден")

        update_data = recommendation_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_recommendation, field, value)

        db.commit()
        db.refresh(db_recommendation)
        logger.info(f"Обновлена рекомендация с id: {recommendation_id}")
        return db_recommendation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении рекомендации: {str(e)}")
        db.rollback()
        raise


def delete_recommendation(db: Session, recommendation_id: int):
    try:
        db_recommendation = db.query(Recommendation).filter(
            Recommendation.recommendation_id == recommendation_id).first()
        if not db_recommendation:
            raise HTTPException(status_code=404, detail="Рекомендация не найдена")

        db.delete(db_recommendation)
        db.commit()
        logger.info(f"Удалена рекомендация с id: {recommendation_id}")
        return {"message": "Рекомендация успешно удалена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении рекомендации: {str(e)}")
        db.rollback()
        raise


# ==================== НОВЫЕ ФУНКЦИИ ДЛЯ РЕКОМЕНДАЦИЙ ====================

def generate_employee_recommendations(db: Session, worker_id: int, count: int = 5):
    """Генерация рекомендаций для конкретного сотрудника"""
    try:
        employee = db.query(Employee).filter(Employee.Worker_id == worker_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        # Получаем программы, которые сотрудник уже прошел
        completed_programs = db.query(Training.Education_Id) \
            .filter(Training.Worker_id == worker_id) \
            .filter(Training.status == 'completed') \
            .all()
        completed_ids = [p[0] for p in completed_programs]

        # Получаем все программы
        all_programs = db.query(EducationProgram).all()
        available_programs = [p for p in all_programs if p.Education_Id not in completed_ids]

        if not available_programs:
            return []

        # Генерируем случайные рекомендации
        users = db.query(User).all()
        recommendations = []
        max_id = db.query(func.max(Recommendation.recommendation_id)).scalar() or 0

        for i in range(min(count, len(available_programs))):
            program = random.choice(available_programs)
            available_programs.remove(program)

            max_id += 1
            score = random.randint(65, 98)
            user = random.choice(users) if users and random.random() > 0.3 else None

            recommendation = Recommendation(
                recommendation_id=max_id,
                worker_id=worker_id,
                education_id=program.Education_Id,
                user_id=user.id_user if user else None,
                score=score,
                creation_date=date.today()
            )
            db.add(recommendation)
            recommendations.append(recommendation)

        db.commit()
        for rec in recommendations:
            db.refresh(rec)

        logger.info(f"Сгенерировано {len(recommendations)} рекомендаций для сотрудника {worker_id}")
        return recommendations

    except Exception as e:
        logger.error(f"Ошибка при генерации рекомендаций: {str(e)}")
        db.rollback()
        raise


def search_employee(db: Session, query: str):
    """Поиск сотрудника по имени или email"""
    try:
        # Точное совпадение
        employee = db.query(Employee) \
            .filter(
            (Employee.Full_name.ilike(f"%{query}%")) |
            (Employee.email.ilike(f"%{query}%"))
        ) \
            .first()

        if employee:
            return {"found": True, "worker_id": employee.Worker_id}

        # Похожие результаты
        similar = db.query(Employee) \
            .filter(
            (Employee.Full_name.ilike(f"%{query}%")) |
            (Employee.email.ilike(f"%{query}%"))
        ) \
            .limit(5) \
            .all()

        return {
            "found": False,
            "similar": [
                {
                    "Worker_id": e.Worker_id,
                    "Full_name": e.Full_name,
                    "Position": e.Position,
                    "email": e.email
                }
                for e in similar
            ]
        }
    except Exception as e:
        logger.error(f"Ошибка при поиске сотрудника: {str(e)}")
        raise


def get_employee_stats(db: Session, worker_id: int):
    """Получение статистики по сотруднику"""
    try:
        trainings = db.query(Training).filter(Training.Worker_id == worker_id).all()
        recommendations = db.query(Recommendation).filter(Recommendation.worker_id == worker_id).all()

        total_trainings = len(trainings)
        completed_trainings = len([t for t in trainings if t.status == 'completed'])

        if recommendations:
            avg_score = sum(r.score for r in recommendations) / len(recommendations)
        else:
            avg_score = 0

        return {
            "total_trainings": total_trainings,
            "completed_trainings": completed_trainings,
            "avg_score": avg_score
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики сотрудника: {str(e)}")
        raise


# ==================== ГЕНЕРАТОР ТЕСТОВЫХ ДАННЫХ ====================

class DataGenerator:
    """Генератор тестовых данных (добавляет только новые записи)"""

    def __init__(self):
        self.data = {}
        logger.info("Инициализация генератора данных")

    def get_next_ids(self, db: Session):
        """Получение следующих доступных ID из базы данных"""
        next_ids = {}

        next_ids['users'] = db.query(func.max(User.id_user)).scalar() or 0
        next_ids['employees'] = db.query(func.max(Employee.Worker_id)).scalar() or 0
        next_ids['programs'] = db.query(func.max(EducationProgram.Education_Id)).scalar() or 0
        next_ids['trainings'] = db.query(func.max(Training.id)).scalar() or 0
        next_ids['biometrics'] = db.query(func.max(Biometric.biometric_id)).scalar() or 0
        next_ids['recommendations'] = db.query(func.max(Recommendation.recommendation_id)).scalar() or 0

        logger.info(f"Текущие максимальные ID в БД: {next_ids}")
        return next_ids

    def generate_all(self, counts=None, db_session=None):
        """Генерация всех данных (только новые записи)"""
        if counts is None:
            counts = {
                'users': 10,
                'employees': 20,
                'programs': 5,
                'trainings': 50,
                'biometrics': 15,
                'recommendations': 30
            }

        next_ids = {'users': 0, 'employees': 0, 'programs': 0, 'trainings': 0, 'biometrics': 0, 'recommendations': 0}
        if db_session:
            db_next_ids = self.get_next_ids(db_session)
            next_ids = db_next_ids

        logger.info("=" * 60)
        logger.info("НАЧАЛО ГЕНЕРАЦИИ НОВЫХ ТЕСТОВЫХ ДАННЫХ")
        logger.info(
            f"Стартовые ID: users={next_ids['users'] + 1}, employees={next_ids['employees'] + 1}, programs={next_ids['programs'] + 1}")
        logger.info("=" * 60)

        # Пользователи
        users = []
        start_id = next_ids['users'] + 1
        for i in range(start_id, start_id + counts['users']):
            users.append({
                'id_user': i,
                'Full_name': fake.name(),
                'Position': fake.job(),
                'email': f"user{i}@example.com",
                'Phone_number': fake.phone_number(),
                'Birth_date': fake.date_of_birth(minimum_age=18, maximum_age=65),
                'Work_duration': fake.date_between(start_date='-10y', end_date='-1y')
            })
        self.data['users'] = pd.DataFrame(users)
        logger.info(
            f"Сгенерировано {len(users)} новых пользователей (ID от {start_id} до {start_id + counts['users'] - 1})")

        # Сотрудники
        employees = []
        start_id = next_ids['employees'] + 1
        for i in range(start_id, start_id + counts['employees']):
            employees.append({
                'Worker_id': i,
                'Full_name': fake.name(),
                'Position': fake.job(),
                'email': f"employee{i}@company.ru",
                'Phone_number': fake.phone_number(),
                'Birth_date': fake.date_of_birth(minimum_age=18, maximum_age=65),
                'Work_duration': fake.date_between(start_date='-15y', end_date='-1y')
            })
        self.data['employees'] = pd.DataFrame(employees)
        logger.info(
            f"Сгенерировано {len(employees)} новых сотрудников (ID от {start_id} до {start_id + counts['employees'] - 1})")

        # Программы
        programs = []
        start_id = next_ids['programs'] + 1
        used_protocols = set()

        if db_session:
            existing_protocols = db_session.query(EducationProgram.Protocol_number).all()
            used_protocols = {p[0] for p in existing_protocols}

        for i in range(start_id, start_id + counts['programs']):
            while True:
                protocol = random.randint(1000, 9999)
                if protocol not in used_protocols:
                    used_protocols.add(protocol)
                    break

            programs.append({
                'Education_Id': i,
                'Protocol_number': protocol,
                'Name': fake.catch_phrase(),
                'created_at': fake.date_time_between(start_date='-2y', end_date='now')
            })
        self.data['programs'] = pd.DataFrame(programs)
        logger.info(
            f"Сгенерировано {len(programs)} новых программ (ID от {start_id} до {start_id + counts['programs'] - 1})")

        # Обучение
        trainings = []
        start_id = next_ids['trainings'] + 1
        max_employee = next_ids['employees'] + counts['employees']
        max_program = next_ids['programs'] + counts['programs']

        for i in range(start_id, start_id + counts['trainings']):
            begin = fake.date_between(start_date='-1y', end_date='+3m')
            end = begin + timedelta(days=random.randint(7, 90))
            trainings.append({
                'id': i,
                'Worker_id': random.randint(1, max_employee),
                'Education_Id': random.randint(1, max_program),
                'Begin_date': begin,
                'End_date': end,
                'status': random.choice(['planned', 'in_progress', 'completed', 'cancelled'])
            })
        self.data['trainings'] = pd.DataFrame(trainings)
        logger.info(
            f"Сгенерировано {len(trainings)} новых записей об обучении (ID от {start_id} до {start_id + counts['trainings'] - 1})")

        # Биометрия
        biometrics = []
        start_id = next_ids['biometrics'] + 1
        max_user = next_ids['users'] + counts['users']

        for i in range(start_id, start_id + counts['biometrics']):
            biometrics.append({
                'biometric_id': i,
                'id_user': random.randint(1, max_user),
                'biometric_type': random.choice(['fingerprint', 'face', 'voice', 'iris']),
                'creation_date': fake.date_between(start_date='-1y', end_date='now')
            })
        self.data['biometrics'] = pd.DataFrame(biometrics)
        logger.info(
            f"Сгенерировано {len(biometrics)} новых биометрических записей (ID от {start_id} до {start_id + counts['biometrics'] - 1})")

        # Рекомендации
        recommendations = []
        start_id = next_ids['recommendations'] + 1

        for i in range(start_id, start_id + counts['recommendations']):
            user_id = random.randint(1, max_user) if random.random() > 0.3 else None
            recommendations.append({
                'recommendation_id': i,
                'worker_id': random.randint(1, max_employee),
                'education_id': random.randint(1, max_program),
                'user_id': user_id,
                'score': random.randint(60, 100),
                'creation_date': fake.date_between(start_date='-3m', end_date='now')
            })
        self.data['recommendations'] = pd.DataFrame(recommendations)
        logger.info(
            f"Сгенерировано {len(recommendations)} новых рекомендаций (ID от {start_id} до {start_id + counts['recommendations'] - 1})")

        logger.info("=" * 60)
        logger.info(f"ГЕНЕРАЦИЯ ЗАВЕРШЕНА. ВСЕГО НОВЫХ ЗАПИСЕЙ: {sum(len(df) for df in self.data.values())}")
        logger.info("=" * 60)

        return self.data

    def export_to_csv(self, output_dir='generated_data'):
        """Экспорт в CSV"""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for table_name, df in self.data.items():
            output_file = os.path.join(output_dir, f"{table_name}_{timestamp}.csv")
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            logger.info(f"Сохранено: {output_file}")

        self.create_report(output_dir, timestamp)

    def create_report(self, output_dir, timestamp):
        """Создание отчета"""
        report = f"""# ОТЧЕТ ПО ГЕНЕРАЦИИ ТЕСТОВЫХ ДАННЫХ
## Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}

## Сгенерировано новых записей:
- **Пользователи**: {len(self.data.get('users', []))}
- **Сотрудники**: {len(self.data.get('employees', []))}
- **Образовательные программы**: {len(self.data.get('programs', []))}
- **Обучение**: {len(self.data.get('trainings', []))}
- **Биометрия**: {len(self.data.get('biometrics', []))}
- **Рекомендации**: {len(self.data.get('recommendations', []))}

## Файлы:
"""
        for file in os.listdir(output_dir):
            if timestamp in file:
                size = os.path.getsize(os.path.join(output_dir, file))
                report += f"- {file}: {size} байт\n"

        report_file = f'generation_report_{timestamp}.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"✓ Отчет создан: {report_file}")


# ==================== ФУНКЦИИ ЗАГРУЗКИ В БД ====================

def load_users_to_db(db: Session, users_df: pd.DataFrame):
    """Загрузка новых пользователей в БД"""
    count = 0
    for _, row in users_df.iterrows():
        try:
            user = User(
                id_user=row['id_user'],
                Full_name=row['Full_name'],
                Position=row['Position'],
                email=row['email'],
                Phone_number=row['Phone_number'],
                Birth_date=row['Birth_date'],
                Work_duration=row['Work_duration']
            )
            db.add(user)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке пользователя {row.get('id_user')}: {str(e)}")
            db.rollback()
            raise

    db.commit()
    logger.info(f"Загружено {count} новых пользователей в БД")
    return count


def load_employees_to_db(db: Session, employees_df: pd.DataFrame):
    """Загрузка новых сотрудников в БД"""
    count = 0
    for _, row in employees_df.iterrows():
        try:
            employee = Employee(
                Worker_id=row['Worker_id'],
                Full_name=row['Full_name'],
                Position=row['Position'],
                email=row['email'],
                Phone_number=row['Phone_number'],
                Birth_date=row['Birth_date'],
                Work_duration=row['Work_duration']
            )
            db.add(employee)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке сотрудника {row.get('Worker_id')}: {str(e)}")
            db.rollback()
            raise

    db.commit()
    logger.info(f"Загружено {count} новых сотрудников в БД")
    return count


def load_programs_to_db(db: Session, programs_df: pd.DataFrame):
    """Загрузка новых образовательных программ в БД"""
    count = 0
    for _, row in programs_df.iterrows():
        try:
            program = EducationProgram(
                Education_Id=row['Education_Id'],
                Protocol_number=row['Protocol_number'],
                Name=row['Name'],
                created_at=row['created_at']
            )
            db.add(program)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке программы {row.get('Education_Id')}: {str(e)}")
            db.rollback()
            raise

    db.commit()
    logger.info(f"Загружено {count} новых программ в БД")
    return count


def load_trainings_to_db(db: Session, trainings_df: pd.DataFrame):
    """Загрузка новых обучений в БД"""
    count = 0
    for _, row in trainings_df.iterrows():
        try:
            training = Training(
                id=row['id'],
                Worker_id=row['Worker_id'],
                Education_Id=row['Education_Id'],
                Begin_date=row['Begin_date'],
                End_date=row['End_date'],
                status=row['status']
            )
            db.add(training)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке обучения {row.get('id')}: {str(e)}")
            db.rollback()
            raise

    db.commit()
    logger.info(f"Загружено {count} новых обучений в БД")
    return count


def load_biometrics_to_db(db: Session, biometrics_df: pd.DataFrame):
    """Загрузка новых биометрических записей в БД"""
    count = 0
    for _, row in biometrics_df.iterrows():
        try:
            biometric = Biometric(
                biometric_id=row['biometric_id'],
                id_user=row['id_user'],
                biometric_type=row['biometric_type'],
                creation_date=row['creation_date']
            )
            db.add(biometric)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке биометрии {row.get('biometric_id')}: {str(e)}")
            db.rollback()
            raise

    db.commit()
    logger.info(f"Загружено {count} новых биометрических записей в БД")
    return count


def load_recommendations_to_db(db: Session, recommendations_df: pd.DataFrame):
    """Загрузка новых рекомендаций в БД"""
    count = 0
    for _, row in recommendations_df.iterrows():
        try:
            user_id = row['user_id']
            if pd.isna(user_id):
                user_id = None
            else:
                user_id = int(user_id)

            recommendation = Recommendation(
                recommendation_id=row['recommendation_id'],
                worker_id=row['worker_id'],
                education_id=row['education_id'],
                user_id=user_id,
                score=row['score'],
                creation_date=row['creation_date']
            )
            db.add(recommendation)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке рекомендации {row.get('recommendation_id')}: {str(e)}")
            db.rollback()
            raise

    db.commit()
    logger.info(f"Загружено {count} новых рекомендаций в БД")
    return count


# ==================== FASTAPI ПРИЛОЖЕНИЕ ====================

app = FastAPI(
    title="Employee Training System",
    version="1.0.0",
    description="Система учета обучения сотрудников"
)


# ==================== UI ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Главная страница"""
    stats = {
        "employees": db.query(Employee).count(),
        "education_programs": db.query(EducationProgram).count(),
        "recommendations": db.query(Recommendation).count()
    }
    return templates.TemplateResponse("index.html", {"request": request, "stats": stats})


@app.get("/employees", response_class=HTMLResponse)
async def employees_page(request: Request, db: Session = Depends(get_db)):
    """Страница со списком сотрудников"""
    employees = db.query(Employee).all()
    return templates.TemplateResponse("employees.html", {"request": request, "employees": employees})


@app.get("/employee/{worker_id}/recommendations", response_class=HTMLResponse)
async def employee_recommendations_page(request: Request, worker_id: int, db: Session = Depends(get_db)):
    """Страница с рекомендациями для сотрудника"""
    employee = get_employee(db, worker_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    recommendations = get_employee_recommendations(db, worker_id)
    trainings = get_employee_trainings(db, worker_id)
    stats = get_employee_stats(db, worker_id)

    # Загружаем связанные данные
    for rec in recommendations:
        rec.program = db.query(EducationProgram).filter(
            EducationProgram.Education_Id == rec.education_id).first()
        if rec.user_id:
            rec.user = db.query(User).filter(User.id_user == rec.user_id).first()

    for training in trainings:
        training.program = db.query(EducationProgram).filter(
            EducationProgram.Education_Id == training.Education_Id).first()

    return templates.TemplateResponse(
        "employee_recommendations.html",
        {
            "request": request,
            "employee": employee,
            "recommendations": recommendations,
            "trainings": trainings,
            "stats": stats
        }
    )


@app.get("/programs", response_class=HTMLResponse)
async def programs_page(request: Request, db: Session = Depends(get_db)):
    """Страница с программами обучения"""
    programs = db.query(EducationProgram).all()
    return templates.TemplateResponse("programs.html", {"request": request, "programs": programs})


@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page(request: Request, db: Session = Depends(get_db)):
    """Страница с рекомендациями"""
    recommendations = db.query(Recommendation).order_by(Recommendation.score.desc()).limit(50).all()

    for rec in recommendations:
        rec.employee = db.query(Employee).filter(Employee.Worker_id == rec.worker_id).first()
        rec.program = db.query(EducationProgram).filter(EducationProgram.Education_Id == rec.education_id).first()

    return templates.TemplateResponse(
        "recommendations.html",
        {"request": request, "recommendations": recommendations}
    )


# ==================== API ROUTES ====================

@app.get("/health")
def health_check():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@app.post("/api/users/", response_model=UserResponse, status_code=201)
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user(db, user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/users/", response_model=List[UserResponse])
def get_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return get_users(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    try:
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.put("/api/users/{user_id}", response_model=UserResponse)
def update_user_endpoint(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    try:
        return update_user(db, user_id, user_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.patch("/api/users/{user_id}", response_model=UserResponse)
def patch_user_endpoint(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    try:
        return update_user(db, user_id, user_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.delete("/api/users/{user_id}")
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    try:
        return delete_user(db, user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


# ==================== СОТРУДНИКИ ====================

@app.post("/api/employees/", response_model=EmployeeResponse, status_code=201)
def create_employee_endpoint(employee: EmployeeCreate, db: Session = Depends(get_db)):
    try:
        return create_employee(db, employee)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании сотрудника: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/employees/", response_model=List[EmployeeResponse])
def get_employees_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return get_employees(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Ошибка при получении сотрудников: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/employees/{worker_id}", response_model=EmployeeResponse)
def get_employee_endpoint(worker_id: int, db: Session = Depends(get_db)):
    try:
        employee = get_employee(db, worker_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")
        return employee
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении сотрудника: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.put("/api/employees/{worker_id}", response_model=EmployeeResponse)
def update_employee_endpoint(worker_id: int, employee_update: EmployeeUpdate, db: Session = Depends(get_db)):
    try:
        return update_employee(db, worker_id, employee_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении сотрудника: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.patch("/api/employees/{worker_id}", response_model=EmployeeResponse)
def patch_employee_endpoint(worker_id: int, employee_update: EmployeeUpdate, db: Session = Depends(get_db)):
    try:
        return update_employee(db, worker_id, employee_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении сотрудника: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.delete("/api/employees/{worker_id}")
def delete_employee_endpoint(worker_id: int, db: Session = Depends(get_db)):
    try:
        return delete_employee(db, worker_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении сотрудника: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


# ==================== ОБРАЗОВАТЕЛЬНЫЕ ПРОГРАММЫ ====================

@app.post("/api/education/", response_model=EducationResponse, status_code=201)
def create_education_endpoint(education: EducationCreate, db: Session = Depends(get_db)):
    try:
        return create_education(db, education)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании программы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/education/", response_model=List[EducationResponse])
def get_education_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return get_educations(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Ошибка при получении программ: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/education/{education_id}", response_model=EducationResponse)
def get_education_by_id_endpoint(education_id: int, db: Session = Depends(get_db)):
    try:
        education = get_education(db, education_id)
        if not education:
            raise HTTPException(status_code=404, detail="Программа не найдена")
        return education
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении программы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.put("/api/education/{education_id}", response_model=EducationResponse)
def update_education_endpoint(education_id: int, education_update: EducationUpdate, db: Session = Depends(get_db)):
    try:
        return update_education(db, education_id, education_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении программы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.patch("/api/education/{education_id}", response_model=EducationResponse)
def patch_education_endpoint(education_id: int, education_update: EducationUpdate, db: Session = Depends(get_db)):
    try:
        return update_education(db, education_id, education_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении программы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.delete("/api/education/{education_id}")
def delete_education_endpoint(education_id: int, db: Session = Depends(get_db)):
    try:
        return delete_education(db, education_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении программы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


# ==================== ОБУЧЕНИЕ ====================

@app.post("/api/trainings/", response_model=TrainingResponse, status_code=201)
def create_training_endpoint(training: TrainingCreate, db: Session = Depends(get_db)):
    try:
        return create_training(db, training)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании обучения: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/trainings/", response_model=List[TrainingResponse])
def get_trainings_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return get_trainings(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Ошибка при получении обучений: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/trainings/{training_id}", response_model=TrainingResponse)
def get_training_endpoint(training_id: int, db: Session = Depends(get_db)):
    try:
        training = get_training(db, training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Обучение не найдено")
        return training
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении обучения: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/employees/{worker_id}/trainings", response_model=List[TrainingResponse])
def get_employee_trainings_endpoint(worker_id: int, db: Session = Depends(get_db)):
    try:
        return get_employee_trainings(db, worker_id)
    except Exception as e:
        logger.error(f"Ошибка при получении обучений сотрудника: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.put("/api/trainings/{training_id}", response_model=TrainingResponse)
def update_training_endpoint(training_id: int, training_update: TrainingUpdate, db: Session = Depends(get_db)):
    try:
        return update_training(db, training_id, training_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении обучения: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.patch("/api/trainings/{training_id}", response_model=TrainingResponse)
def patch_training_endpoint(training_id: int, training_update: TrainingUpdate, db: Session = Depends(get_db)):
    try:
        return update_training(db, training_id, training_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении обучения: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.delete("/api/trainings/{training_id}")
def delete_training_endpoint(training_id: int, db: Session = Depends(get_db)):
    try:
        return delete_training(db, training_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении обучения: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


# ==================== БИОМЕТРИЯ ====================

@app.post("/api/biometrics/", response_model=BiometricResponse, status_code=201)
def create_biometric_endpoint(biometric: BiometricCreate, db: Session = Depends(get_db)):
    try:
        return create_biometric(db, biometric)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании биометрии: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/biometrics/", response_model=List[BiometricResponse])
def get_biometrics_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return get_biometrics(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Ошибка при получении биометрии: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/biometrics/{biometric_id}", response_model=BiometricResponse)
def get_biometric_endpoint(biometric_id: int, db: Session = Depends(get_db)):
    try:
        biometric = get_biometric(db, biometric_id)
        if not biometric:
            raise HTTPException(status_code=404, detail="Биометрия не найдена")
        return biometric
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении биометрии: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/users/{user_id}/biometrics", response_model=List[BiometricResponse])
def get_user_biometrics_endpoint(user_id: int, db: Session = Depends(get_db)):
    try:
        return get_user_biometrics(db, user_id)
    except Exception as e:
        logger.error(f"Ошибка при получении биометрии пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.put("/api/biometrics/{biometric_id}", response_model=BiometricResponse)
def update_biometric_endpoint(biometric_id: int, biometric_update: BiometricUpdate, db: Session = Depends(get_db)):
    try:
        return update_biometric(db, biometric_id, biometric_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении биометрии: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.patch("/api/biometrics/{biometric_id}", response_model=BiometricResponse)
def patch_biometric_endpoint(biometric_id: int, biometric_update: BiometricUpdate, db: Session = Depends(get_db)):
    try:
        return update_biometric(db, biometric_id, biometric_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении биометрии: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.delete("/api/biometrics/{biometric_id}")
def delete_biometric_endpoint(biometric_id: int, db: Session = Depends(get_db)):
    try:
        return delete_biometric(db, biometric_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении биометрии: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


# ==================== РЕКОМЕНДАЦИИ ====================

@app.post("/api/recommendations/", response_model=RecommendationResponse, status_code=201)
def create_recommendation_endpoint(recommendation: RecommendationCreate, db: Session = Depends(get_db)):
    try:
        return create_recommendation(db, recommendation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании рекомендации: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/recommendations/", response_model=List[RecommendationResponse])
def get_recommendations_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return get_recommendations(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation_endpoint(recommendation_id: int, db: Session = Depends(get_db)):
    try:
        recommendation = get_recommendation(db, recommendation_id)
        if not recommendation:
            raise HTTPException(status_code=404, detail="Рекомендация не найдена")
        return recommendation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендации: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/employees/{worker_id}/recommendations", response_model=List[RecommendationResponse])
def get_employee_recommendations_endpoint(worker_id: int, db: Session = Depends(get_db)):
    try:
        return get_employee_recommendations(db, worker_id)
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций сотрудника: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/users/{user_id}/recommendations", response_model=List[RecommendationResponse])
def get_user_recommendations_endpoint(user_id: int, db: Session = Depends(get_db)):
    try:
        return get_user_recommendations(db, user_id)
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.put("/api/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def update_recommendation_endpoint(recommendation_id: int, recommendation_update: RecommendationUpdate,
                                   db: Session = Depends(get_db)):
    try:
        return update_recommendation(db, recommendation_id, recommendation_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении рекомендации: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.patch("/api/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def patch_recommendation_endpoint(recommendation_id: int, recommendation_update: RecommendationUpdate,
                                  db: Session = Depends(get_db)):
    try:
        return update_recommendation(db, recommendation_id, recommendation_update)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении рекомендации: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.delete("/api/recommendations/{recommendation_id}")
def delete_recommendation_endpoint(recommendation_id: int, db: Session = Depends(get_db)):
    try:
        return delete_recommendation(db, recommendation_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении рекомендации: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


# ==================== НОВЫЕ API ENDPOINTS ДЛЯ РЕКОМЕНДАЦИЙ ====================

@app.get("/api/search-employee")
def search_employee_endpoint(q: str, db: Session = Depends(get_db)):
    """Поиск сотрудника по имени или email"""
    try:
        return search_employee(db, q)
    except Exception as e:
        logger.error(f"Ошибка при поиске сотрудника: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.post("/api/generate-employee-recommendations/{worker_id}")
def generate_employee_recommendations_endpoint(worker_id: int, count: int = 5, db: Session = Depends(get_db)):
    """Генерация рекомендаций для конкретного сотрудника"""
    try:
        recommendations = generate_employee_recommendations(db, worker_id, count)
        return {"message": f"Сгенерировано {len(recommendations)} рекомендаций", "count": len(recommendations)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации рекомендаций: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/employee/{worker_id}/stats")
def get_employee_stats_endpoint(worker_id: int, db: Session = Depends(get_db)):
    """Получение статистики по сотруднику"""
    try:
        return get_employee_stats(db, worker_id)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


# ==================== ГЕНЕРАЦИЯ ДАННЫХ ====================

@app.post("/api/generate-data")
def generate_test_data(
        users: int = 10,
        employees: int = 20,
        programs: int = 5,
        trainings: int = 50,
        biometrics: int = 15,
        recommendations: int = 30
):
    """
    Генерация новых тестовых данных

    Параметры:
    - users: количество новых пользователей
    - employees: количество новых сотрудников
    - programs: количество новых программ
    - trainings: количество новых записей об обучении
    - biometrics: количество новых биометрических записей
    - recommendations: количество новых рекомендаций
    """
    try:
        db = SessionLocal()

        generator = DataGenerator()

        counts = {
            'users': users,
            'employees': employees,
            'programs': programs,
            'trainings': trainings,
            'biometrics': biometrics,
            'recommendations': recommendations
        }

        generator.generate_all(counts, db_session=db)
        db.close()

        generator.export_to_csv('generated_data')

        db = SessionLocal()
        total_records = 0
        total_records += load_users_to_db(db, generator.data['users'])
        total_records += load_employees_to_db(db, generator.data['employees'])
        total_records += load_programs_to_db(db, generator.data['programs'])
        total_records += load_trainings_to_db(db, generator.data['trainings'])
        total_records += load_biometrics_to_db(db, generator.data['biometrics'])
        total_records += load_recommendations_to_db(db, generator.data['recommendations'])

        stats = {
            "users": db.query(User).count(),
            "employees": db.query(Employee).count(),
            "education_programs": db.query(EducationProgram).count(),
            "trainings": db.query(Training).count(),
            "biometrics": db.query(Biometric).count(),
            "recommendations": db.query(Recommendation).count()
        }
        db.close()

        return {
            "message": "Новые тестовые данные успешно добавлены!",
            "generated": counts,
            "new_records_added": total_records,
            "total_records_in_db": stats,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Ошибка при генерации данных: {str(e)}")
        return {
            "message": f"Ошибка: {str(e)}",
            "status": "error"
        }


@app.get("/api/db-stats")
def get_db_stats(db: Session = Depends(get_db)):
    """Получение статистики по базе данных"""
    try:
        stats = {
            "users": db.query(User).count(),
            "employees": db.query(Employee).count(),
            "education_programs": db.query(EducationProgram).count(),
            "trainings": db.query(Training).count(),
            "biometrics": db.query(Biometric).count(),
            "recommendations": db.query(Recommendation).count(),
            "status": "success"
        }
        return stats
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        return {"status": "error", "message": str(e)}


# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    init_db()

    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        print("=" * 60)
        print("ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ")
        print("=" * 60)
        print("Структура БД:")
        print("  • Пользователь")
        print("  • Сотрудники")
        print("  • Образовательная программа")
        print("  • Сотрудник и обучение")
        print("  • Биометрия")
        print("  • Рекомендация по обучению")
        print("=" * 60)

        db = SessionLocal()

        generator = DataGenerator()
        generator.generate_all({
            'users': 50,
            'employees': 200,
            'programs': 30,
            'trainings': 500,
            'biometrics': 100,
            'recommendations': 300
        }, db_session=db)

        db.close()

        generator.export_to_csv('generated_data')

        db = SessionLocal()
        load_users_to_db(db, generator.data['users'])
        load_employees_to_db(db, generator.data['employees'])
        load_programs_to_db(db, generator.data['programs'])
        load_trainings_to_db(db, generator.data['trainings'])
        load_biometrics_to_db(db, generator.data['biometrics'])
        load_recommendations_to_db(db, generator.data['recommendations'])
        db.close()

        print("=" * 60)
        print("ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 60)
        print("\nРезультаты в папке: generated_data")
        print("Данные загружены в БД: employee_training.db")

    else:
        print("=" * 60)
        print("ЗАПУСК EMPLOYEE TRAINING SYSTEM")
        print("=" * 60)
        print("Веб-интерфейс: http://localhost:8000")
        print("Документация API: http://localhost:8000/docs")
        print("=" * 60)
        print("Доступные страницы:")
        print("  • /                    - Главная с поиском")
        print("  • /employees           - Список сотрудников")
        print("  • /programs            - Программы обучения")
        print("  • /recommendations     - Все рекомендации")
        print("  • /employee/{id}/recommendations - Рекомендации сотрудника")
        print("=" * 60)
        print("Для генерации тестовых данных используйте:")
        print("   python main.py --generate")
        print("   или через API: POST /api/generate-data")
        print("=" * 60)

        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
