from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List

from database import get_db
from models import (
    Disciplina, Turma, IntegranteDaTurma, Aluno,
    DisciplinaResponse, StudentInfo, TurmaResponse
)
from auth import get_current_user, get_current_professor, get_current_student

router = APIRouter(tags=["General"])


@router.get("/disciplinas", response_model=List[DisciplinaResponse])
async def get_disciplinas(
    db: AsyncSession = Depends(get_db)
):
    """Get all available academic disciplines"""
    
    query = select(Disciplina).order_by(Disciplina.name)
    result = await db.execute(query)
    disciplinas = result.scalars().all()
    
    return [DisciplinaResponse.from_orm(d) for d in disciplinas]


@router.get("/turma/{turma_id}/students", response_model=List[StudentInfo])
async def get_turma_students(
    turma_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get students enrolled in a specific class"""
    
    # Validate turma exists
    turma_query = select(Turma).where(Turma.id == turma_id)
    turma_result = await db.execute(turma_query)
    turma = turma_result.scalar_one_or_none()
    
    if not turma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found"
        )
    
    # Check if user has access (professor who owns the class or student enrolled in it)
    access_query = select(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.turma_id == turma_id,
            or_(
                and_(
                    IntegranteDaTurma.professor_id.in_(
                        select(Professor.id).where(Professor.email == current_user.email)
                    ),
                    IntegranteDaTurma.tipo == "professor"
                ),
                and_(
                    IntegranteDaTurma.aluno_id.in_(
                        select(Aluno.id).where(Aluno.email == current_user.email)
                    ),
                    IntegranteDaTurma.tipo == "aluno"
                )
            )
        )
    )
    
    # Import here to avoid circular import
    from models import Professor
    
    access_result = await db.execute(access_query)
    if not access_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You must be the professor or a student in this class"
        )
    
    # Get students in the class
    students_query = select(Aluno).join(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.turma_id == turma_id,
            IntegranteDaTurma.tipo == "aluno"
        )
    ).order_by(Aluno.name)
    
    students_result = await db.execute(students_query)
    students = students_result.scalars().all()
    
    return [StudentInfo.from_orm(student) for student in students]
