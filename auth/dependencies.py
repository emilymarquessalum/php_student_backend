from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from database import get_db
from models import Usuario, Professor, Aluno, UserType
from .auth_handler import verify_token

security = HTTPBearer()


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class PermissionError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)
    
    email = payload.get("sub")
    if not email:
        raise AuthenticationError("Invalid token")
    
    # Get user from database
    result = await db.execute(select(Usuario).where(Usuario.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("User not found")
    
    return user


async def get_current_professor(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user as professor (raises error if not professor)"""
    result = await db.execute(select(Professor).where(Professor.email == current_user.email))
    professor = result.scalar_one_or_none()
    
    if not professor:
        raise PermissionError("Professor access required")
    
    return professor


async def get_current_student(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user as student (raises error if not student)"""
    result = await db.execute(select(Aluno).where(Aluno.email == current_user.email))
    student = result.scalar_one_or_none()
    
    if not student:
        raise PermissionError("Student access required")
    
    return student


async def get_user_type(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserType:
    """Determine if current user is professor or student"""
    # Check if professor
    result = await db.execute(select(Professor).where(Professor.email == current_user.email))
    if result.scalar_one_or_none():
        return UserType.professor
    
    # Check if student
    result = await db.execute(select(Aluno).where(Aluno.email == current_user.email))
    if result.scalar_one_or_none():
        return UserType.aluno
    
    raise AuthenticationError("User type not found")


async def get_current_user_info(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed current user information"""
    user_type = await get_user_type(current_user, db)
    
    if user_type == UserType.professor:
        result = await db.execute(select(Professor).where(Professor.email == current_user.email))
        prof = result.scalar_one()
        return {
            "email": current_user.email,
            "name": prof.name,
            "user_type": user_type,
            "id": prof.id
        }
    else:
        result = await db.execute(select(Aluno).where(Aluno.email == current_user.email))
        student = result.scalar_one()
        return {
            "email": current_user.email,
            "name": student.name,
            "user_type": user_type,
            "id": student.id,
            "matricula": student.matricula
        }
