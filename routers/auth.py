from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from database import get_db
from models import Usuario, Professor, Aluno, LoginRequest, LoginResponse, UserInfo, UserType
from auth import verify_password, create_access_token, get_current_user_info
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT token"""
    
    # Get user from database
    result = await db.execute(select(Usuario).where(Usuario.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.senha, user.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Determine user type and get additional info
    prof_result = await db.execute(select(Professor).where(Professor.email == user.email))
    professor = prof_result.scalar_one_or_none()
    
    if professor:
        user_type = UserType.professor
        user_info = {
            "email": user.email,
            "name": professor.name,
            "user_type": user_type.value,
            "id": professor.id
        }
    else:
        student_result = await db.execute(select(Aluno).where(Aluno.email == user.email))
        student = student_result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        user_type = UserType.aluno
        user_info = {
            "email": user.email,
            "name": student.name,
            "user_type": user_type.value,
            "id": student.id,
            "matricula": student.matricula
        }
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email, "user_type": user_type.value},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_type=user_type,
        user_info=user_info
    )


@router.post("/logout")
async def logout():
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info_endpoint(
    user_info: dict = Depends(get_current_user_info)
):
    """Get current user information"""
    return UserInfo(**user_info)
