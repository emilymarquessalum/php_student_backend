# Assuming the main router objects are in files named the same as their parent folder
from .auth import router as auth_router
from .auth_register import router as auth_register_router
from .professor.professor import router as professor_router
from .professor.classes import router as professor_classes_router
from .student.student import router as student_router
from .student.classes import router as student_classes_router
from .attendance.attendance import router as attendance_router
from .qrcode.qrcode import router as qrcode_router
from .general import router as general_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "auth_register_router",
    "professor_router",
    "professor_classes_router",
    "student_router",
    "student_classes_router",
    "attendance_router",
    "qrcode_router",
    "general_router",
    "admin_router"
]