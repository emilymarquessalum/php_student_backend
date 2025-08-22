from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
import time

from database import get_db
from models import (
    Aluno, Turma, IntegranteDaTurma, DiaDeAula, Presenca, Disciplina,
    TurmaResponse, AttendanceRequest, AttendanceResponse,
    StudentDashboard, StudentEnrollment, SuccessResponse
)
from auth import get_current_student
from utils import parse_qr_data, validate_qr_timestamp, generate_uuid, calculate_attendance_percentage

router = APIRouter(prefix="/student", tags=["Student"])


@router.get("/dashboard", response_model=StudentDashboard)
async def get_student_dashboard(
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get student dashboard with statistics"""
    
    # Get enrolled classes count
    enrolled_classes_query = select(func.count(IntegranteDaTurma.id)).where(
        and_(
            IntegranteDaTurma.aluno_id == student.id,
            IntegranteDaTurma.tipo == "aluno"
        )
    )
    enrolled_classes_result = await db.execute(enrolled_classes_query)
    enrolled_classes = enrolled_classes_result.scalar() or 0
    
    # Get total attendance count
    total_attendance_query = select(func.count(Presenca.id)).where(
        Presenca.aluno_id == student.id
    )
    total_attendance_result = await db.execute(total_attendance_query)
    total_attendance = total_attendance_result.scalar() or 0
    
    # Get total possible classes (completed classes in enrolled turmas)
    total_classes_query = select(func.count(DiaDeAula.id)).where(
        and_(
            DiaDeAula.turma_id.in_(
                select(IntegranteDaTurma.turma_id).where(
                    and_(
                        IntegranteDaTurma.aluno_id == student.id,
                        IntegranteDaTurma.tipo == "aluno"
                    )
                )
            ),
            DiaDeAula.aula_foi_dada == True
        )
    )
    total_classes_result = await db.execute(total_classes_query)
    total_classes = total_classes_result.scalar() or 0
    
    # Calculate attendance percentage
    attendance_percentage = calculate_attendance_percentage(total_attendance, total_classes)
    
    # Get recent attendance
    recent_attendance_query = select(Presenca).options(
        selectinload(Presenca.dia_aula).selectinload(DiaDeAula.turma)
    ).where(
        Presenca.aluno_id == student.id
    ).order_by(Presenca.timestamp.desc()).limit(5)
    
    recent_attendance_result = await db.execute(recent_attendance_query)
    recent_attendance = recent_attendance_result.scalars().all()
    
    # Get student's classes
    classes_query = select(Turma).options(
        selectinload(Turma.disciplina)
    ).join(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.aluno_id == student.id,
            IntegranteDaTurma.tipo == "aluno"
        )
    )
    
    classes_result = await db.execute(classes_query)
    classes = classes_result.scalars().all()
    
    # Prepare recent attendance responses
    recent_attendance_responses = []
    for presenca in recent_attendance:
        response = AttendanceResponse.from_orm(presenca)
        response.student_name = student.name
        response.turma_nome = presenca.dia_aula.turma.nome_turma
        recent_attendance_responses.append(response)
    
    return StudentDashboard(
        enrolled_classes=enrolled_classes,
        total_attendance=total_attendance,
        attendance_percentage=attendance_percentage,
        recent_attendance=recent_attendance_responses,
        classes=[TurmaResponse.from_orm(c) for c in classes]
    )


@router.get("/turmas", response_model=List[TurmaResponse])
async def get_student_turmas(
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get classes student is enrolled in"""
    
    query = select(Turma).options(
        selectinload(Turma.disciplina)
    ).join(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.aluno_id == student.id,
            IntegranteDaTurma.tipo == "aluno"
        )
    )
    
    result = await db.execute(query)
    turmas = result.scalars().all()
    
    return [TurmaResponse.from_orm(turma) for turma in turmas]


@router.post("/attendance", response_model=AttendanceResponse)
async def mark_attendance(
    attendance_data: AttendanceRequest,
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance using QR code data"""
    
    # Validate QR code timestamp
    if not validate_qr_timestamp(attendance_data.timestamp, max_age_minutes=30):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR code has expired"
        )
    
    # Validate action
    if attendance_data.action != "marcar_presenca":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid QR code action"
        )
    
    # Get dia de aula
    dia_aula_query = select(DiaDeAula).options(
        selectinload(DiaDeAula.turma)
    ).where(DiaDeAula.id == attendance_data.dia_aula_id)
    
    dia_aula_result = await db.execute(dia_aula_query)
    dia_aula = dia_aula_result.scalar_one_or_none()
    
    if not dia_aula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class session not found"
        )
    
    # Check if student is enrolled in the class
    enrollment_query = select(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.turma_id == dia_aula.turma_id,
            IntegranteDaTurma.aluno_id == student.id,
            IntegranteDaTurma.tipo == "aluno"
        )
    )
    
    enrollment_result = await db.execute(enrollment_query)
    if not enrollment_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this class"
        )
    
    # Check if attendance already marked
    existing_attendance_query = select(Presenca).where(
        and_(
            Presenca.aluno_id == student.id,
            Presenca.dia_aula_id == attendance_data.dia_aula_id
        )
    )
    
    existing_attendance_result = await db.execute(existing_attendance_query)
    if existing_attendance_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance already marked for this class session"
        )
    
    # Create attendance record
    attendance_id = generate_uuid()
    new_attendance = Presenca(
        id=attendance_id,
        aluno_id=student.id,
        dia_aula_id=attendance_data.dia_aula_id,
        timestamp=datetime.utcnow()
    )
    
    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    
    # Prepare response
    response = AttendanceResponse.from_orm(new_attendance)
    response.student_name = student.name
    response.turma_nome = dia_aula.turma.nome_turma
    
    return response

@router.get("/attendance/{dia_aula_id}/check", response_model=SuccessResponse)
async def check_attendance(
    dia_aula_id: str,
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Check if a student attended a specific class day"""

    # Query attendance record for the specific dia_aula_id
    attendance_query = select(Presenca).where(
        and_(
            Presenca.aluno_id == student.id,
            Presenca.dia_aula_id == dia_aula_id
        )
    )

    attendance_result = await db.execute(attendance_query)
    attendance_exists = attendance_result.scalar_one_or_none()

    if not attendance_exists:
        return SuccessResponse(
            message=f"No attendance record found for class session {dia_aula_id}."
        )

    return SuccessResponse(
        message=f"Attendance confirmed for class session {dia_aula_id}.",
        data={
            "dia_aula_id": dia_aula_id,
            "timestamp": attendance_exists.timestamp
        }
    )

@router.get("/attendance/history", response_model=List[AttendanceResponse])
async def get_attendance_history(
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get student's attendance history"""
    
    query = select(Presenca).options(
        selectinload(Presenca.dia_aula).selectinload(DiaDeAula.turma)
    ).where(
        Presenca.aluno_id == student.id
    ).order_by(Presenca.timestamp.desc())
    
    result = await db.execute(query)
    presencas = result.scalars().all()
    
    # Prepare responses
    responses = []
    for presenca in presencas:
        response = AttendanceResponse.from_orm(presenca)
        response.student_name = student.name
        response.turma_nome = presenca.dia_aula.turma.nome_turma
        responses.append(response)
    
    return responses


@router.post("/turma/{turma_id}/join", response_model=SuccessResponse)
async def join_turma(
    turma_id: str,
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Join a class"""
    
    # Validate turma exists
    turma_query = select(Turma).where(Turma.id == turma_id)
    turma_result = await db.execute(turma_query)
    turma = turma_result.scalar_one_or_none()
    
    if not turma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found"
        )
    
    # Check if already enrolled
    existing_query = select(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.turma_id == turma_id,
            IntegranteDaTurma.aluno_id == student.id,
            IntegranteDaTurma.tipo == "aluno"
        )
    )
    
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already enrolled in this class"
        )
    
    # Create enrollment
    enrollment = IntegranteDaTurma(
        turma_id=turma_id,
        aluno_id=student.id,
        tipo="aluno"
    )
    
    db.add(enrollment)
    await db.commit()
    
    return SuccessResponse(
        message="Successfully joined the class",
        data={"turma_id": turma_id, "turma_nome": turma.nome_turma}
    )
