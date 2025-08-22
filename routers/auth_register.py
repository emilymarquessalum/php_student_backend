from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import ProfessorCreate, AlunoCreate, Usuario, Professor, Aluno
from auth import get_password_hash
from utils import generate_uuid

router = APIRouter(prefix="/auth", tags=["Authentication"]) 

@router.post("/register/student", status_code=201)
async def register_student(
    user_in: AlunoCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new student"""
    # Check if user exists
    result = await db.execute(select(Usuario).where(Usuario.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Create user
    user = Usuario(email=user_in.email, senha=get_password_hash(user_in.senha))
    db.add(user)
    await db.flush()
    
    # Create student
    aluno = Aluno(
        id=generate_uuid(), 
        email=user_in.email, 
        matricula=user_in.matricula, 
        name=user_in.name
    )
    db.add(aluno)
    await db.commit()
    
    return {"message": "Student registered successfully"}


@router.post("/register/professor", status_code=201)
async def register_professor(
    user_in: ProfessorCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new professor"""
    # Check if user exists
    result = await db.execute(select(Usuario).where(Usuario.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Create user
    user = Usuario(email=user_in.email, senha=get_password_hash(user_in.senha))
    db.add(user)
    await db.flush()
    
    # Create professor
    professor = Professor(
        id=generate_uuid(), 
        email=user_in.email, 
        name=user_in.name
    )
    db.add(professor)
    await db.commit()
    
    return {"message": "Professor registered successfully"}
