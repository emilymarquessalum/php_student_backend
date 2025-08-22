from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List
from database import get_db
from models import Presenca, DiaDeAula, Aluno, AttendanceRequest, AttendanceResponse, StudentInfo
from auth import get_current_student
from utils import generate_uuid, validate_qr_timestamp
from datetime import datetime

router = APIRouter(prefix="/attendance", tags=["Attendance"])

from utils import validate_qr_timestamp, generate_uuid
from datetime import datetime
from models import DiaDeAula, IntegranteDaTurma
@router.post("/mark", response_model=AttendanceResponse)
async def mark_attendance(
    data: AttendanceRequest,
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for a student (QR/manual/facial recognition)."""
    # Validate QR code timestamp
    #if not validate_qr_timestamp(data.timestamp, max_age_minutes=30): 
    #    raise HTTPException(status_code=400, detail="QR code has expired")
    if data.action != "marcar_presenca":
        raise HTTPException(status_code=400, detail="Invalid QR code action")
    # Get dia de aula
    dia_aula_query = select(DiaDeAula).where(DiaDeAula.id == data.dia_aula_id)
    dia_aula_result = await db.execute(dia_aula_query)
    dia_aula = dia_aula_result.scalar_one_or_none()
    if not dia_aula:
        raise HTTPException(status_code=404, detail="Class session not found")
    # Check if student is enrolled in the class
    enrollment_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == dia_aula.turma_id, IntegranteDaTurma.aluno_id == student.id, IntegranteDaTurma.tipo == "aluno")
    )
    enrollment_result = await db.execute(enrollment_query)
    if not enrollment_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")
    # Check if attendance already marked
    existing_attendance_query = select(Presenca).where(
        and_(Presenca.aluno_id == student.id, Presenca.dia_aula_id == data.dia_aula_id)
    )
    existing_attendance_result = await db.execute(existing_attendance_query)
    if existing_attendance_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Attendance already marked for this class session")
    attendance_id = generate_uuid()
    new_attendance = Presenca(
        id=attendance_id,
        aluno_id=student.id,
        dia_aula_id=data.dia_aula_id,
        timestamp=datetime.utcnow()
    )
    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    return AttendanceResponse.from_orm(new_attendance)

@router.get("/{day_id}/count")
async def get_attendance_count(
    day_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the number of students present for a specific class day."""
    # Get the count of attendance records for this day
    attendance_count_query = select(func.count(Presenca.id)).where(Presenca.dia_aula_id == day_id)
    attendance_count_result = await db.execute(attendance_count_query)
    attendance_count = attendance_count_result.scalar_one()
    return {"attendance_count": attendance_count}

@router.get("/{day_id}/list", response_model=List[StudentInfo])
async def get_attendance_list(
    day_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the list of students present for a specific class day."""
    # Get all attendance records for this day
    attendance_query = select(Presenca).where(Presenca.dia_aula_id == day_id)
    attendance_result = await db.execute(attendance_query)
    presencas = attendance_result.scalars().all()
    # Get student info for each attendance
    students = []
    for presenca in presencas:
        aluno_query = select(Aluno).where(Aluno.id == presenca.aluno_id)
        aluno_result = await db.execute(aluno_query)
        aluno = aluno_result.scalar_one_or_none()
        if aluno:
            students.append(StudentInfo.from_orm(aluno))
    return students
