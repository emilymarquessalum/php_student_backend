from .database_models import (
    Usuario, Disciplina, Turma, Professor, Aluno,
    IntegranteDaTurma, DiaDeAula, Presenca
)
from .pydantic_models import (
    LoginRequest, LoginResponse, UserInfo, UserType,
    DisciplinaCreate, DisciplinaResponse,
    TurmaCreate, TurmaResponse,
    AulaCreate, DiaAulaResponse,
    QRCodeData, QRCodeResponse,
    AttendanceRequest, AttendanceResponse, AttendanceCount,
    StudentInfo, StudentEnrollment,
    ProfessorDashboard, StudentDashboard, ProfessorStats,
    ErrorResponse, ValidationErrorResponse,
    ProfessorCreate, AlunoCreate, SuccessResponse
)

__all__ = [
    # Database models
    "Usuario", "Disciplina", "Turma", "Professor", "Aluno",
    "IntegranteDaTurma", "DiaDeAula", "Presenca",
    
    # Pydantic models
    "LoginRequest", "LoginResponse", "UserInfo", "UserType",
    "DisciplinaCreate", "DisciplinaResponse",
    "TurmaCreate", "TurmaResponse",
    "AulaCreate", "DiaAulaResponse",
    "QRCodeData", "QRCodeResponse",
    "AttendanceRequest", "AttendanceResponse", "AttendanceCount",
    "StudentInfo", "StudentEnrollment",
    "ProfessorDashboard", "StudentDashboard", "ProfessorStats",
    "ErrorResponse", "ValidationErrorResponse",
    "ProfessorCreate", "AlunoCreate", "SuccessResponse"
]
