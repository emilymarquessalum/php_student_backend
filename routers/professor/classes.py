from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List
from database import get_db
from models import Turma, Disciplina, IntegranteDaTurma, DiaDeAula, Presenca, Aluno, Professor
from models import TurmaResponse, DiaAulaResponse, AttendanceResponse, StudentInfo
from auth import get_current_professor

router = APIRouter(prefix="/professor/classes", tags=["Professor Classes"])

@router.get("", response_model=List[TurmaResponse])
async def list_classes(
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """List all classes for the authenticated professor."""
    query = select(Turma).join(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    result = await db.execute(query)
    turmas = result.scalars().all()
    return [TurmaResponse.from_orm(t) for t in turmas]

from models import TurmaCreate
from utils import generate_uuid
from datetime import datetime

@router.post("", response_model=TurmaResponse, status_code=201)
async def create_class(
    turma_data: TurmaCreate,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Create a new class (turma)."""
    # Validate disciplina exists
    disciplina_result = await db.execute(select(Disciplina).where(Disciplina.id == turma_data.disciplina_id))
    disciplina = disciplina_result.scalar_one_or_none()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina not found")
    # Parse year
    try:
        year_datetime = datetime.strptime(turma_data.year, "%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid year format. Use YYYY")
    turma_id = generate_uuid()
    new_turma = Turma(
        id=turma_id,
        nome_turma=turma_data.nome_turma,
        disciplina_id=turma_data.disciplina_id,
        year=year_datetime
    )
    db.add(new_turma)
    await db.flush()
    integrante = IntegranteDaTurma(
        turma_id=turma_id,
        professor_id=professor.id,
        tipo="professor"
    )
    db.add(integrante)
    await db.commit()
    await db.refresh(new_turma)
    await db.refresh(new_turma, ["disciplina"])
    return TurmaResponse.from_orm(new_turma)

@router.get("/{class_id}", response_model=TurmaResponse)
async def get_class_details(
    class_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific class, including students and attendance stats."""
    
    # Eagerly load the 'disciplina' relationship using selectinload
    turma_query = select(Turma).options(selectinload(Turma.disciplina)).where(Turma.id == class_id)
    turma_result = await db.execute(turma_query)
    turma = turma_result.scalar_one_or_none()
    
    if not turma:
        raise HTTPException(status_code=404, detail="Class not found")
        
    # Check professor ownership
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Você não tem permissão para acessar esta turma")

    # Get students (this part is fine as it's a direct query)
    students_query = select(Aluno).join(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.tipo == "aluno")
    )
    students_result = await db.execute(students_query)
    students = students_result.scalars().all()
    
    # Get attendance stats (this part is also fine)
    days_query = select(DiaDeAula).where(DiaDeAula.turma_id == class_id)
    days_result = await db.execute(days_query)
    days = days_result.scalars().all()

    # The from_orm call will now work because 'turma.disciplina' is already loaded
    turma_response = TurmaResponse.from_orm(turma)
    turma_response.student_count = len(students)
    
    return turma_response

from models import AulaCreate
from utils import combine_date_time
@router.post("/{class_id}/days", response_model=DiaAulaResponse, status_code=201)
async def create_class_day(
    class_id: str,
    day_data: AulaCreate,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Register a new class day (aula) for a class."""
    # Validate professor owns the class
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")
    # Combine date and time
    try:
        data_aula = combine_date_time(day_data.data_aula, day_data.hora_aula)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    dia_aula_id = generate_uuid()
    new_dia_aula = DiaDeAula(
        id=dia_aula_id,
        turma_id=class_id,
        data=data_aula,
        professor_id=professor.id
    )
    db.add(new_dia_aula)
    await db.commit()
    await db.refresh(new_dia_aula)
    return DiaAulaResponse.from_orm(new_dia_aula)

@router.get("/{class_id}/days", response_model=List[DiaAulaResponse])
async def list_class_days(
    class_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """List all class days for a class."""
    # Validate professor owns the class
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")
    days_query = select(DiaDeAula).where(DiaDeAula.turma_id == class_id)
    days_result = await db.execute(days_query)
    days = days_result.scalars().all()
    return [DiaAulaResponse.from_orm(day) for day in days]

@router.get("/{class_id}/days/{day_id}", response_model=DiaAulaResponse)
async def get_class_day_details(
    class_id: str,
    day_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Get details for a specific class day (including attendance list)."""
    # Validate professor owns the class
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")
    day_query = select(DiaDeAula).where(DiaDeAula.id == day_id, DiaDeAula.turma_id == class_id)
    day_result = await db.execute(day_query)
    day = day_result.scalar_one_or_none()
    if not day:
        raise HTTPException(status_code=404, detail="Class day not found")
    return DiaAulaResponse.from_orm(day)

from models import QRCodeData, QRCodeResponse
from utils import generate_qr_code
import time
@router.post("/{class_id}/days/{day_id}/qrcode", response_model=QRCodeResponse)
async def generate_qrcode(
    class_id: str,
    day_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Generate a QR code for attendance (returns QR data or image)."""
    # Validate professor owns the class
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")
    # Validate class day exists
    day_query = select(DiaDeAula).where(DiaDeAula.id == day_id, DiaDeAula.turma_id == class_id)
    day_result = await db.execute(day_query)
    day = day_result.scalar_one_or_none()
    if not day:
        raise HTTPException(status_code=404, detail="Class day not found")
    qr_data = QRCodeData(
        dia_aula_id=day_id,
        timestamp=int(time.time()),
        action="marcar_presenca"
    )
    qr_code_base64 = generate_qr_code(qr_data.dict())
    return QRCodeResponse(qr_data=qr_data, qr_code_base64=qr_code_base64)

@router.post("/{class_id}/students")
async def add_student_to_class( 
    class_id: str,
    student_data: dict,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Add a student to a class."""
    aluno_id = student_data.get("aluno_id")
    if not aluno_id:
        raise HTTPException(status_code=400, detail="Missing aluno_id")
    # Validate professor owns the class
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")
    # Validate student exists
    aluno_query = select(Aluno).where(Aluno.id == aluno_id)
    aluno_result = await db.execute(aluno_query)
    aluno = aluno_result.scalar_one_or_none()
    if not aluno:
        raise HTTPException(status_code=404, detail="Student not found")
    # Check if already enrolled
    existing_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.aluno_id == aluno_id, IntegranteDaTurma.tipo == "aluno")
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Student already enrolled")
    integrante = IntegranteDaTurma(
        turma_id=class_id,
        aluno_id=aluno_id,
        tipo="aluno"
    )
    db.add(integrante)
    await db.commit()
    return {"message": "Student added to class"}

@router.get("/{class_id}/info")
async def get_detailed_class_info(
    class_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a class."""
    # Validate professor's permission to access the class
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")

    # Get class details and eagerly load the related 'disciplina'
    turma_query = select(Turma).where(Turma.id == class_id).options(selectinload(Turma.disciplina))
    turma_result = await db.execute(turma_query)
    turma = turma_result.scalar_one_or_none()
    if not turma:
        raise HTTPException(status_code=404, detail="Class not found")

    # Get students (this will likely be another relationship that may need eager loading in a production app)
    students_query = select(Aluno).join(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.tipo == "aluno")
    )
    students_result = await db.execute(students_query)
    students = students_result.scalars().all()

    # Get class days
    class_days_query = select(DiaDeAula).where(DiaDeAula.turma_id == class_id)
    class_days_result = await db.execute(class_days_query)
    class_days = class_days_result.scalars().all()

    # Calculate attendance
    attendance_query = select(Presenca).join(DiaDeAula).where(DiaDeAula.turma_id == class_id)
    attendance_result = await db.execute(attendance_query)
    attendances = attendance_result.scalars().all()

    total_students = len(students)
    total_classes = len(class_days)
    total_attendance = len(attendances)
    avg_attendance = (total_attendance / total_classes) if total_classes > 0 else 0
    attendance_rate = (total_attendance / (total_classes * total_students)) if (total_classes * total_students) > 0 else 0

    return {
        "class": TurmaResponse.from_orm(turma),
        "class_days": (class_days),
        "students": [StudentInfo.from_orm(student) for student in students],
        "total_classes": total_classes,
        "total_students": total_students,
        "avg_attendance": avg_attendance,
        "attendance_rate": attendance_rate
    }

@router.get("/{class_id}/students/not-enrolled", response_model=List[StudentInfo])
async def list_students_not_in_class(
class_id: str,
professor: Professor = Depends(get_current_professor),
db: AsyncSession = Depends(get_db)
):
    # Validate professor's permission to access the class
    owner_query = select(IntegranteDaTurma).where(
    and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")

    # Fetch students not in the class
    subquery = select(IntegranteDaTurma.aluno_id).where(
    IntegranteDaTurma.turma_id == class_id
    )
    not_enrolled_students_query = select(Aluno).where(
    Aluno.id.not_in(subquery)
    )
    not_enrolled_students_result = await db.execute(not_enrolled_students_query)
    not_enrolled_students = not_enrolled_students_result.scalars().all()

    return [StudentInfo.from_orm(student) for student in not_enrolled_students]

@router.get("/{class_id}/students", response_model=List[StudentInfo])
async def list_students_in_class(
class_id: str,
professor: Professor = Depends(get_current_professor),
db: AsyncSession = Depends(get_db)
):
    """List all students in a class."""
    # Validate professor's permission to access the class
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")

    # Fetch students in the class
    students_query = select(Aluno).join(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.tipo == "aluno")
    )
    students_result = await db.execute(students_query)
    students = students_result.scalars().all()

    return [StudentInfo.from_orm(student) for student in students]

@router.delete("/{class_id}/students/{student_id}")
async def remove_student_from_class(
    class_id: str,
    student_id: str,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Remove a student from a class."""
    # Validate professor owns the class
    owner_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.professor_id == professor.id, IntegranteDaTurma.tipo == "professor")
    )
    owner_result = await db.execute(owner_query)
    if not owner_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You do not own this class")
    # Remove student
    delete_query = select(IntegranteDaTurma).where(
        and_(IntegranteDaTurma.turma_id == class_id, IntegranteDaTurma.aluno_id == student_id, IntegranteDaTurma.tipo == "aluno")
    )
    delete_result = await db.execute(delete_query)
    integrante = delete_result.scalar_one_or_none()
    if not integrante:
        raise HTTPException(status_code=404, detail="Student not enrolled in this class")
    await db.delete(integrante)
    await db.commit()
    return {"message": "Student removed from class"}
