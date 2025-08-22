from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List
from database import get_db
from models import Turma, IntegranteDaTurma, DiaDeAula, Presenca, Aluno, Disciplina, Professor
from models import TurmaResponse, DiaAulaResponse, AttendanceResponse, StudentInfo
from auth import get_current_student

router = APIRouter(prefix="/student/classes", tags=["Student Classes"])

@router.get("", response_model=List[TurmaResponse])
async def list_student_classes(
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """List all classes the student is enrolled in."""
    query = select(Turma).join(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.aluno_id == student.id, IntegranteDaTurma.tipo == "aluno")
    )
    result = await db.execute(query)
    turmas = result.scalars().all()
    return [TurmaResponse.from_orm(t) for t in turmas]

@router.get("/{class_id}", response_model=TurmaResponse)
async def get_student_class_details(
    class_id: str,
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a class."""
    turma_query = select(Turma).where(Turma.id == class_id)
    turma_result = await db.execute(turma_query)
    turma = turma_result.scalar_one_or_none()
    if not turma:
        raise HTTPException(status_code=404, detail="Class not found")
    # Check student enrollment
    enrollment_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.aluno_id == student.id, IntegranteDaTurma.tipo == "aluno")
    )
    enrollment_result = await db.execute(enrollment_query)
    if not enrollment_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")
    # Get students
    students_query = select(Aluno).join(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.tipo == "aluno")
    )
    students_result = await db.execute(students_query)
    students = students_result.scalars().all()
    turma_response = TurmaResponse.from_orm(turma)
    turma_response.student_count = len(students)
    return turma_response

@router.get("/{class_id}/days", response_model=List[DiaAulaResponse])
async def list_student_class_days(
    class_id: str,
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """List all class days for a class."""
    # Check student enrollment
    enrollment_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.aluno_id == student.id, IntegranteDaTurma.tipo == "aluno")
    )
    enrollment_result = await db.execute(enrollment_query)
    if not enrollment_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")
    days_query = select(DiaDeAula).where(DiaDeAula.turma_id == class_id)
    days_result = await db.execute(days_query)
    days = days_result.scalars().all()
    return [DiaAulaResponse.from_orm(day) for day in days]


@router.get("/{class_id}/day/{day_id}", response_model=DiaAulaResponse)
async def get_student_class_day_details(
    class_id: str,
    day_id: str,
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific day of class."""
    # Verify student enrollment
    enrollment_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.aluno_id == student.id, IntegranteDaTurma.tipo == "aluno")
    )
    enrollment_result = await db.execute(enrollment_query)
    if not enrollment_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")
    
    # Fetch day details
    day_query = select(DiaDeAula).where(
        and_(DiaDeAula.id == day_id, DiaDeAula.turma_id == class_id)
    )
    day_result = await db.execute(day_query)
    day = day_result.scalar_one_or_none()
    
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    
    return DiaAulaResponse.from_orm(day)