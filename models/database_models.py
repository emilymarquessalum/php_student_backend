from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime


class Usuario(Base):
    __tablename__ = "usuario"
    
    email = Column(String(255), primary_key=True)
    senha = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    professor = relationship("Professor", back_populates="usuario", uselist=False)
    aluno = relationship("Aluno", back_populates="usuario", uselist=False)


class Disciplina(Base):
    __tablename__ = "disciplina"
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    turmas = relationship("Turma", back_populates="disciplina")


class Turma(Base):
    __tablename__ = "turma"
    
    id = Column(String(255), primary_key=True)
    nome_turma = Column(String(255), nullable=False)
    disciplina_id = Column(String(255), ForeignKey("disciplina.id", ondelete="CASCADE"), nullable=False)
    year = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    disciplina = relationship("Disciplina", back_populates="turmas")
    integrantes = relationship("IntegranteDaTurma", back_populates="turma")
    dias_aula = relationship("DiaDeAula", back_populates="turma")


class Professor(Base):
    __tablename__ = "professor"
    
    id = Column(String(255), primary_key=True)
    email = Column(String(255), ForeignKey("usuario.email", ondelete="CASCADE"), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    usuario = relationship("Usuario", back_populates="professor")
    integrante_turmas = relationship("IntegranteDaTurma", back_populates="professor")
    dias_aula = relationship("DiaDeAula", back_populates="professor")


class Aluno(Base):
    __tablename__ = "aluno"
    
    id = Column(String(255), primary_key=True)
    email = Column(String(255), ForeignKey("usuario.email", ondelete="CASCADE"), nullable=False, unique=True)
    matricula = Column(String(255), nullable=False, unique=True)
    name = Column(String(255))
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    usuario = relationship("Usuario", back_populates="aluno")
    integrante_turmas = relationship("IntegranteDaTurma", back_populates="aluno")
    presencas = relationship("Presenca", back_populates="aluno")


class IntegranteDaTurma(Base):
    __tablename__ = "integrante_da_turma"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    turma_id = Column(String(255), ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)
    professor_id = Column(String(255), ForeignKey("professor.id", ondelete="CASCADE"), nullable=True)
    aluno_id = Column(String(255), ForeignKey("aluno.id", ondelete="CASCADE"), nullable=True)
    tipo = Column(String(20), nullable=False)
    joined_at = Column(DateTime, default=func.current_timestamp())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("tipo IN ('professor', 'aluno')", name="check_tipo"),
        CheckConstraint(
            "(tipo = 'professor' AND professor_id IS NOT NULL AND aluno_id IS NULL) OR "
            "(tipo = 'aluno' AND aluno_id IS NOT NULL AND professor_id IS NULL)",
            name="check_integrante_logic"
        ),
        UniqueConstraint("turma_id", "professor_id", name="unique_turma_professor"),
        UniqueConstraint("turma_id", "aluno_id", name="unique_turma_aluno"),
    )
    
    # Relationships
    turma = relationship("Turma", back_populates="integrantes")
    professor = relationship("Professor", back_populates="integrante_turmas")
    aluno = relationship("Aluno", back_populates="integrante_turmas")


class DiaDeAula(Base):
    __tablename__ = "dia_de_aula"
    
    id = Column(String(255), primary_key=True)
    turma_id = Column(String(255), ForeignKey("turma.id", ondelete="CASCADE"), nullable=False)
    data = Column(DateTime, nullable=False)
    aula_foi_dada = Column(Boolean, nullable=False, default=False)
    professor_id = Column(String(255), ForeignKey("professor.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    turma = relationship("Turma", back_populates="dias_aula")
    professor = relationship("Professor", back_populates="dias_aula")
    presencas = relationship("Presenca", back_populates="dia_aula")


class Presenca(Base):
    __tablename__ = "presenca"
    
    id = Column(String(255), primary_key=True)
    aluno_id = Column(String(255), ForeignKey("aluno.id", ondelete="CASCADE"), nullable=False)
    dia_aula_id = Column(String(255), ForeignKey("dia_de_aula.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.current_timestamp())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("aluno_id", "dia_aula_id", name="unique_aluno_dia_aula"),
    )
    
    # Relationships
    aluno = relationship("Aluno", back_populates="presencas")
    dia_aula = relationship("DiaDeAula", back_populates="presencas")
