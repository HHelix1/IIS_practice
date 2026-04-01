from sqlalchemy.orm import Session
import models
import schemas

# Образовательные программы
def create_education(db: Session, education: schemas.EducationCreate):
    """Создание образовательной программы"""
    db_education = models.EducationProgram(
        name=education.name,
        protocol_number=education.protocol_number,
        description=education.description
    )
    db.add(db_education)
    db.commit()
    db.refresh(db_education)
    return db_education

def get_educations(db: Session, skip: int = 0, limit: int = 100):
    """Получение всех образовательных программ"""
    return db.query(models.EducationProgram).offset(skip).limit(limit).all()

def get_education(db: Session, education_id: int):
    """Получение образовательной программы по ID"""
    return db.query(models.EducationProgram).filter(models.EducationProgram.id == education_id).first()

# Сотрудники
def create_employee(db: Session, employee: schemas.EmployeeCreate):
    """Создание сотрудника"""
    db_employee = models.Employee(
        full_name=employee.full_name,
        position=employee.position,
        email=employee.email,
        phone_number=employee.phone_number,
        birth_date=employee.birth_date
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

def get_employees(db: Session, skip: int = 0, limit: int = 100):
    """Получение всех сотрудников"""
    return db.query(models.Employee).offset(skip).limit(limit).all()

def get_employee(db: Session, employee_id: int):
    """Получение сотрудника по ID"""
    return db.query(models.Employee).filter(models.Employee.id == employee_id).first()

# Учет обучения
def create_training(db: Session, training: schemas.TrainingCreate):
    """Создание записи об обучении"""
    db_training = models.TrainingRecord(
        employee_id=training.employee_id,
        education_id=training.education_id,
        start_date=training.start_date,
        end_date=training.end_date,
        status=training.status
    )
    db.add(db_training)
    db.commit()
    db.refresh(db_training)
    return db_training

def get_trainings(db: Session, skip: int = 0, limit: int = 100):
    """Получение всех записей об обучении"""
    return db.query(models.TrainingRecord).offset(skip).limit(limit).all()

def get_employee_trainings(db: Session, employee_id: int):
    """Получение истории обучения сотрудника"""
    return db.query(models.TrainingRecord).filter(
        models.TrainingRecord.employee_id == employee_id
    ).all()