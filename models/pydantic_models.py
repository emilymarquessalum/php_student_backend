from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class UserType(str, Enum):
    professor = "professor"
    aluno = "aluno"


# Authentication Models
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_type: UserType
    user_info: dict


class UserInfo(BaseModel):
    email: str
    name: str
    user_type: UserType
    id: str


# Base Models
class DisciplinaBase(BaseModel):
    name: str
    description: Optional[str] = None


class DisciplinaCreate(DisciplinaBase):
    pass


class DisciplinaResponse(DisciplinaBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Turma Models
class TurmaCreate(BaseModel):
    nome_turma: str
    disciplina_id: str
    year: str


class TurmaResponse(BaseModel):
    id: str
    nome_turma: str
    disciplina_id: str
    year: datetime
    created_at: datetime
    disciplina: Optional[DisciplinaResponse] = None
    student_count: Optional[int] = None

    class Config:
        from_attributes = True


# Class Session Models
class AulaCreate(BaseModel):
    turma_id: str
    data_aula: str  # Date in YYYY-MM-DD format
    hora_aula: str  # Time in HH:MM format


class DiaAulaResponse(BaseModel):
    id: str
    turma_id: str
    data: datetime
    aula_foi_dada: bool
    professor_id: str
    created_at: datetime
    attendance_count: Optional[int] = None

    class Config:
        from_attributes = True


# QR Code Models
class QRCodeData(BaseModel):
    dia_aula_id: str
    timestamp: int
    action: str = "marcar_presenca"


class QRCodeResponse(BaseModel):
    qr_data: QRCodeData
    qr_code_base64: Optional[str] = None


# Attendance Models
class AttendanceRequest(BaseModel):
    dia_aula_id: str 
    action: str


class AttendanceResponse(BaseModel):
    id: str
    aluno_id: str
    dia_aula_id: str
    timestamp: datetime
    student_name: Optional[str] = None
    turma_nome: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceCount(BaseModel):
    dia_aula_id: str
    total_students: int
    present_students: int
    attendance_percentage: float


# Student Models
class StudentInfo(BaseModel):
    id: str
    email: str
    matricula: str
    name: Optional[str] = None

    class Config:
        from_attributes = True


class StudentEnrollment(BaseModel):
    turma_id: str


# Dashboard Models
class ProfessorDashboard(BaseModel):
    total_classes: int
    total_students: int
    today_classes: int
    recent_classes: List[DiaAulaResponse]
    classes: List[TurmaResponse]


class ProfessorStats(BaseModel):
    total_classes: int
    total_students: int
    classes_today: int
    attendance_rate: float
    class_stats: List[dict]


class StudentDashboard(BaseModel):
    enrolled_classes: int
    total_attendance: int
    attendance_percentage: float
    recent_attendance: List[AttendanceResponse]
    classes: List[TurmaResponse]


# Error Models
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    detail: List[dict]
    error_code: str = "validation_error"


# User Creation Models (for registration)
class ProfessorCreate(BaseModel):
    email: EmailStr
    senha: str
    name: str


class AlunoCreate(BaseModel):
    email: EmailStr
    senha: str
    matricula: str
    name: Optional[str] = None


# Success Response
class SuccessResponse(BaseModel):
    message: str
    data: Optional[Any] = None
