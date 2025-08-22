from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, date
import time

from database import get_db
from models import (
    Professor, Turma, Disciplina, IntegranteDaTurma, DiaDeAula, Presenca,
    TurmaCreate, TurmaResponse, AulaCreate, DiaAulaResponse,
    QRCodeData, QRCodeResponse, ProfessorDashboard, ProfessorStats, AttendanceCount,
    SuccessResponse
)
from auth import get_current_professor
from utils import generate_uuid, combine_date_time, generate_qr_code, calculate_attendance_percentage

router = APIRouter(prefix="/professor", tags=["Professor"])


@router.get("/dashboard", response_model=ProfessorDashboard)
async def get_professor_dashboard(
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Get professor dashboard with statistics"""
    
    # Get professor's classes count
    classes_query = select(func.count(IntegranteDaTurma.id)).where(
        and_(
            IntegranteDaTurma.professor_id == professor.id,
            IntegranteDaTurma.tipo == "professor"
        )
    )
    total_classes_result = await db.execute(classes_query)
    total_classes = total_classes_result.scalar() or 0
    
    # Get total students across all classes
    students_query = select(func.count(IntegranteDaTurma.id)).where(
        IntegranteDaTurma.turma_id.in_(
            select(IntegranteDaTurma.turma_id).where(
                and_(
                    IntegranteDaTurma.professor_id == professor.id,
                    IntegranteDaTurma.tipo == "professor"
                )
            )
        ),
        IntegranteDaTurma.tipo == "aluno"
    )
    total_students_result = await db.execute(students_query)
    total_students = total_students_result.scalar() or 0
    
    # Get today's classes
    today = date.today()
    today_classes_query = select(func.count(DiaDeAula.id)).where(
        and_(
            DiaDeAula.professor_id == professor.id,
            func.date(DiaDeAula.data) == today
        )
    )
    today_classes_result = await db.execute(today_classes_query)
    today_classes = today_classes_result.scalar() or 0
    
    # Get recent classes
    recent_classes_query = select(DiaDeAula).where(
        DiaDeAula.professor_id == professor.id
    ).order_by(DiaDeAula.created_at.desc()).limit(5)
    
    recent_classes_result = await db.execute(recent_classes_query)
    recent_classes = recent_classes_result.scalars().all()
    
    # Get professor's classes with student counts
    classes_query = select(Turma).options(
        selectinload(Turma.disciplina)
    ).join(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.professor_id == professor.id,
            IntegranteDaTurma.tipo == "professor"
        )
    )
    
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
    
    return ProfessorDashboard(
        total_classes=total_classes,
        total_students=total_students,
        today_classes=today_classes,
        recent_classes=[DiaAulaResponse.from_orm(c) for c in recent_classes],
        classes=classes_with_counts
    )


@router.post("/turma", response_model=TurmaResponse)
async def create_turma(
    turma_data: TurmaCreate,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Create a new class"""
    
    # Validate disciplina exists
    disciplina_result = await db.execute(select(Disciplina).where(Disciplina.id == turma_data.disciplina_id))
    disciplina = disciplina_result.scalar_one_or_none()
    
    if not disciplina:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disciplina not found"
        )
    
    # Parse year
    try:
        year_datetime = datetime.strptime(turma_data.year, "%Y")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year format. Use YYYY"
        )
    
    # Create turma
    turma_id = generate_uuid()
    new_turma = Turma(
        id=turma_id,
        nome_turma=turma_data.nome_turma,
        disciplina_id=turma_data.disciplina_id,
        year=year_datetime
    )
    
    db.add(new_turma)
    await db.flush()
    
    # Add professor to turma
    integrante = IntegranteDaTurma(
        turma_id=turma_id,
        professor_id=professor.id,
        tipo="professor"
    )
    
    db.add(integrante)
    await db.commit()
    await db.refresh(new_turma)
    
    # Load disciplina for response
    await db.refresh(new_turma, ["disciplina"])
    
    return TurmaResponse.from_orm(new_turma)


@router.get("/turmas", response_model=List[TurmaResponse])
async def get_professor_turmas(
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Get professor's classes"""
    
    query = select(Turma).options(
        selectinload(Turma.disciplina)
    ).join(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.professor_id == professor.id,
            IntegranteDaTurma.tipo == "professor"
        )
    )
    
    result = await db.execute(query)
    turmas = result.scalars().all()
    
    # Add student counts
    turmas_with_counts = []
    for turma in turmas:
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
        turmas_with_counts.append(turma_response)
    
    return turmas_with_counts


@router.post("/aula", response_model=DiaAulaResponse)
async def create_aula(
    aula_data: AulaCreate,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Create a new class session"""
    
    # Validate professor owns the turma
    ownership_query = select(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.turma_id == aula_data.turma_id,
            IntegranteDaTurma.professor_id == professor.id,
            IntegranteDaTurma.tipo == "professor"
        )
    )
    
    ownership_result = await db.execute(ownership_query)
    if not ownership_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create sessions for this class"
        )
    
    # Combine date and time
    try:
        data_aula = combine_date_time(aula_data.data_aula, aula_data.hora_aula)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Create dia de aula
    dia_aula_id = generate_uuid()
    new_dia_aula = DiaDeAula(
        id=dia_aula_id,
        turma_id=aula_data.turma_id,
        data=data_aula,
        professor_id=professor.id
    )
    
    db.add(new_dia_aula)
    await db.commit()
    await db.refresh(new_dia_aula)
    
    return DiaAulaResponse.from_orm(new_dia_aula)


@router.get("/aula/{dia_aula_id}/qr", response_model=QRCodeResponse)
async def get_qr_code(
    dia_aula_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Generate QR code for attendance"""
    
    # Validate dia de aula exists and professor owns it
    query = select(DiaDeAula).where(
        and_(
            DiaDeAula.id == dia_aula_id,
            DiaDeAula.professor_id == professor.id
        )
    )
    
    result = await db.execute(query)
    dia_aula = result.scalar_one_or_none()
    
    if not dia_aula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class session not found or access denied"
        )
    
    # Generate QR code data
    qr_data = QRCodeData(
        dia_aula_id=dia_aula_id,
        timestamp=int(time.time()),
        action="marcar_presenca"
    )
    
    # Generate QR code image
    qr_code_base64 = generate_qr_code(qr_data.dict())
    
    return QRCodeResponse(
        qr_data=qr_data,
        qr_code_base64=qr_code_base64
    )


@router.get("/aula/{dia_aula_id}/attendance", response_model=AttendanceCount)
async def get_attendance_count(
    dia_aula_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Get real-time attendance count for a class session"""
    
    # Validate dia de aula exists and professor owns it
    dia_aula_query = select(DiaDeAula).where(
        and_(
            DiaDeAula.id == dia_aula_id,
            DiaDeAula.professor_id == professor.id
        )
    )
    
    dia_aula_result = await db.execute(dia_aula_query)
    dia_aula = dia_aula_result.scalar_one_or_none()
    
    if not dia_aula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class session not found or access denied"
        )
    
    # Get total students in the class
    total_students_query = select(func.count(IntegranteDaTurma.id)).where(
        and_(
            IntegranteDaTurma.turma_id == dia_aula.turma_id,
            IntegranteDaTurma.tipo == "aluno"
        )
    )
    total_students_result = await db.execute(total_students_query)
    total_students = total_students_result.scalar() or 0
    
    # Get present students count
    present_students_query = select(func.count(Presenca.id)).where(
        Presenca.dia_aula_id == dia_aula_id
    )
    present_students_result = await db.execute(present_students_query)
    present_students = present_students_result.scalar() or 0
    
    # Calculate percentage
    attendance_percentage = calculate_attendance_percentage(present_students, total_students)
    
    return AttendanceCount(
        dia_aula_id=dia_aula_id,
        total_students=total_students,
        present_students=present_students,
        attendance_percentage=attendance_percentage
    )


@router.post("/aula/{dia_aula_id}/finish", response_model=SuccessResponse)
async def finish_aula(
    dia_aula_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Mark class session as completed"""
    
    # Get and validate dia de aula
    query = select(DiaDeAula).where(
        and_(
            DiaDeAula.id == dia_aula_id,
            DiaDeAula.professor_id == professor.id
        )
    )
    
    result = await db.execute(query)
    dia_aula = result.scalar_one_or_none()
    
    if not dia_aula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class session not found or access denied"
        )
    
    # Mark as completed
    dia_aula.aula_foi_dada = True
    await db.commit()
    
    return SuccessResponse(
        message="Class session marked as completed",
        data={"dia_aula_id": dia_aula_id}
    )


@router.get("/stats", response_model=ProfessorStats)
async def get_professor_stats(
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed professor statistics"""
    
    # Get professor's classes count
    classes_query = select(func.count(IntegranteDaTurma.id)).where(
        and_(
            IntegranteDaTurma.professor_id == professor.id,
            IntegranteDaTurma.tipo == "professor"
        )
    )
    total_classes_result = await db.execute(classes_query)
    total_classes = total_classes_result.scalar() or 0
    
    # Get total students across all classes
    students_query = select(func.count(IntegranteDaTurma.id)).where(
        IntegranteDaTurma.turma_id.in_(
            select(IntegranteDaTurma.turma_id).where(
                and_(
                    IntegranteDaTurma.professor_id == professor.id,
                    IntegranteDaTurma.tipo == "professor"
                )
            )
        ),
        IntegranteDaTurma.tipo == "aluno"
    )
    total_students_result = await db.execute(students_query)
    total_students = total_students_result.scalar() or 0
    
    # Get today's classes
    today = date.today()
    today_classes_query = select(func.count(DiaDeAula.id)).where(
        and_(
            DiaDeAula.professor_id == professor.id,
            func.date(DiaDeAula.data) == today
        )
    )
    today_classes_result = await db.execute(today_classes_query)
    classes_today = today_classes_result.scalar() or 0
    
    # Calculate overall attendance rate
    attendance_rate = 0.0
    
    # Get all class days for this professor
    class_days_query = select(DiaDeAula).where(DiaDeAula.professor_id == professor.id)
    class_days_result = await db.execute(class_days_query)
    class_days = class_days_result.scalars().all()
    
    total_attendance_count = 0
    total_possible_attendance = 0
    
    # Get class stats with attendance information
    class_stats = []
    
    # Get professor's classes
    classes_query = select(Turma).options(
        selectinload(Turma.disciplina)
    ).join(IntegranteDaTurma).where(
        and_(
            IntegranteDaTurma.professor_id == professor.id,
            IntegranteDaTurma.tipo == "professor"
        )
    )
    
    classes_result = await db.execute(classes_query)
    classes = classes_result.scalars().all()
    
    for turma in classes:
        # Get student count for this class
        student_count_query = select(func.count(IntegranteDaTurma.id)).where(
            and_(
                IntegranteDaTurma.turma_id == turma.id,
                IntegranteDaTurma.tipo == "aluno"
            )
        )
        student_count_result = await db.execute(student_count_query)
        student_count = student_count_result.scalar() or 0
        
        # Get class days for this class
        class_days_query = select(DiaDeAula).where(DiaDeAula.turma_id == turma.id)
        class_days_result = await db.execute(class_days_query)
        class_days = class_days_result.scalars().all()
        
        class_attendance_count = 0
        class_possible_attendance = 0
        
        for day in class_days:
            # Get attendance count for this day
            attendance_query = select(func.count(Presenca.id)).where(Presenca.dia_aula_id == day.id)
            attendance_result = await db.execute(attendance_query)
            attendance_count = attendance_result.scalar() or 0
            
            class_attendance_count += attendance_count
            class_possible_attendance += student_count
            
            total_attendance_count += attendance_count
            total_possible_attendance += student_count
        
        # Calculate class attendance rate
        class_attendance_rate = 0.0
        if class_possible_attendance > 0:
            class_attendance_rate = class_attendance_count / class_possible_attendance * 100
        
        class_stats.append({
            "class_id": turma.id,
            "class_name": turma.nome_turma,
            "discipline": turma.disciplina.name if turma.disciplina else None,
            "student_count": student_count,
            "attendance_rate": class_attendance_rate
        })
    
    # Calculate overall attendance rate
    if total_possible_attendance > 0:
        attendance_rate = total_attendance_count / total_possible_attendance * 100
    
    return ProfessorStats(
        total_classes=total_classes,
        total_students=total_students,
        classes_today=classes_today,
        attendance_rate=attendance_rate,
        class_stats=class_stats
    )
