from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List

from database import get_db
from models import (
    Usuario, Professor, Aluno, Turma, Disciplina, 
    IntegranteDaTurma, DiaDeAula, Presenca,
    UserInfo, TurmaResponse, AttendanceResponse
)
from auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[UserInfo])
async def get_all_users(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (admin only)"""
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access this endpoint"
        )
    
    # Get all users
    users_query = select(Usuario)
    users_result = await db.execute(users_query)
    users = users_result.scalars().all()
    
    user_info_list = []
    for user in users:
        user_type = None
        if hasattr(user, "professor") and user.professor:
            user_type = "professor"
        elif hasattr(user, "aluno") and user.aluno:
            user_type = "aluno"
        
        user_info = UserInfo(
            id=user.id,
            email=user.email,
            name=user.name,
            user_type=user_type
        )
        user_info_list.append(user_info)
    
    return user_info_list


@router.get("/classes", response_model=List[TurmaResponse])
async def get_all_classes(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all classes (admin only)"""
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access this endpoint"
        )
    
    # Get all classes with discipline information
    classes_query = select(Turma).options(selectinload(Turma.disciplina))
    classes_result = await db.execute(classes_query)
    classes = classes_result.scalars().all()
    
    # Add student counts to classes
    classes_with_counts = []
    for turma in classes:
        student_count_query = select(func.count(IntegranteDaTurma.id)).where(
            and_(
                IntegranteDaTurma.turma_id == turma.id,
                IntegranteDaTurma.tipo == "aluno"
            )
        )
        student_count_result = await db.execute(student_count_query)
        student_count = student_count_result.scalar() or 0
        
        turma_response = TurmaResponse.from_orm(turma)
        turma_response.student_count = student_count
        classes_with_counts.append(turma_response)
    
    return classes_with_counts


@router.get("/attendance", response_model=List[AttendanceResponse])
async def get_all_attendance(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all attendance records (admin only)"""
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access this endpoint"
        )
    
    # Get all attendance records
    attendance_query = select(Presenca).order_by(Presenca.timestamp.desc())
    attendance_result = await db.execute(attendance_query)
    attendance_records = attendance_result.scalars().all()
    
    # Enhance attendance records with student and class information
    enhanced_records = []
    for record in attendance_records:
        # Get student name
        student_query = select(Aluno).where(Aluno.id == record.aluno_id)
        student_result = await db.execute(student_query)
        student = student_result.scalar_one_or_none()
        student_name = student.name if student else None
        
        # Get class name
        class_day_query = select(DiaDeAula).where(DiaDeAula.id == record.dia_aula_id)
        class_day_result = await db.execute(class_day_query)
        class_day = class_day_result.scalar_one_or_none()
        
        turma_nome = None
        if class_day:
            turma_query = select(Turma).where(Turma.id == class_day.turma_id)
            turma_result = await db.execute(turma_query)
            turma = turma_result.scalar_one_or_none()
            turma_nome = turma.nome_turma if turma else None
        
        attendance_response = AttendanceResponse.from_orm(record)
        attendance_response.student_name = student_name
        attendance_response.turma_nome = turma_nome
        enhanced_records.append(attendance_response)
    
    return enhanced_records