from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import get_db
from models import DiaDeAula, Professor, Aluno, QRCodeData, QRCodeResponse, AttendanceRequest, AttendanceResponse
from auth import get_current_professor, get_current_student
from utils import generate_qr_code, parse_qr_data, validate_qr_timestamp
import time

router = APIRouter(prefix="/qrcode", tags=["QR Code"])

from models import DiaDeAula
from utils import generate_qr_code
import time
@router.post("/generate", response_model=QRCodeResponse)
async def generate_qrcode(
    data: QRCodeData,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db)
):
    """Generate QR code data for a class day (professor only)."""
    # Validate class day exists and professor owns it
    day_query = select(DiaDeAula).where(DiaDeAula.id == data.dia_aula_id, DiaDeAula.professor_id == professor.id)
    day_result = await db.execute(day_query)
    day = day_result.scalar_one_or_none()
    if not day:
        raise HTTPException(status_code=404, detail="Class day not found or access denied")
    qr_data = QRCodeData(
        dia_aula_id=data.dia_aula_id,
        timestamp=int(time.time()),
        action="marcar_presenca"
    )
    qr_code_base64 = generate_qr_code(qr_data.dict())
    return QRCodeResponse(qr_data=qr_data, qr_code_base64=qr_code_base64)

from routers.attendance.attendance import mark_attendance
@router.post("/scan", response_model=AttendanceResponse)
async def scan_qrcode(
    data: AttendanceRequest,
    student: Aluno = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Student submits scanned QR code data to mark attendance."""
    # Reuse mark_attendance logic
    return await mark_attendance(data, student, db)
