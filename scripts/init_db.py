"""
Database initialization script with sample data
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from database import async_session, create_tables
from models import Usuario, Disciplina, Professor, Aluno, Turma, IntegranteDaTurma, DiaDeAula
from auth import get_password_hash
from utils import generate_uuid


async def create_sample_data():
    """Create sample data for testing"""
    
    async with async_session() as db:
        try:
            # Create sample disciplinas
            disciplinas_data = [
                {"id": generate_uuid(), "name": "Banco de Dados", "description": "Fundamentos de bancos de dados relacionais"},
                {"id": generate_uuid(), "name": "Programação Web", "description": "Desenvolvimento de aplicações web"},
                {"id": generate_uuid(), "name": "Estruturas de Dados", "description": "Algoritmos e estruturas de dados"},
                {"id": generate_uuid(), "name": "Redes de Computadores", "description": "Conceitos de redes e protocolos"},
                {"id": generate_uuid(), "name": "Engenharia de Software", "description": "Metodologias de desenvolvimento de software"}
            ]
            
            disciplinas = []
            for data in disciplinas_data:
                disciplina = Disciplina(**data)
                disciplinas.append(disciplina)
                db.add(disciplina)
            
            await db.flush()
            
            # Create sample users (professors)
            prof_users_data = [
                {"email": "prof.silva@university.edu", "senha": get_password_hash("professor123")},
                {"email": "prof.santos@university.edu", "senha": get_password_hash("professor123")},
                {"email": "prof.oliveira@university.edu", "senha": get_password_hash("professor123")}
            ]
            
            prof_users = []
            for data in prof_users_data:
                user = Usuario(**data)
                prof_users.append(user)
                db.add(user)
            
            await db.flush()
            
            # Create professors
            professors_data = [
                {"id": generate_uuid(), "email": "prof.silva@university.edu", "name": "Dr. João Silva"},
                {"id": generate_uuid(), "email": "prof.santos@university.edu", "name": "Dra. Maria Santos"},
                {"id": generate_uuid(), "email": "prof.oliveira@university.edu", "name": "Dr. Carlos Oliveira"}
            ]
            
            professors = []
            for data in professors_data:
                professor = Professor(**data)
                professors.append(professor)
                db.add(professor)
            
            await db.flush()
            
            # Create sample student users
            student_users_data = [
                {"email": "aluno1@student.edu", "senha": get_password_hash("student123")},
                {"email": "aluno2@student.edu", "senha": get_password_hash("student123")},
                {"email": "aluno3@student.edu", "senha": get_password_hash("student123")},
                {"email": "aluno4@student.edu", "senha": get_password_hash("student123")},
                {"email": "aluno5@student.edu", "senha": get_password_hash("student123")}
            ]
            
            student_users = []
            for data in student_users_data:
                user = Usuario(**data)
                student_users.append(user)
                db.add(user)
            
            await db.flush()
            
            # Create students
            students_data = [
                {"id": generate_uuid(), "email": "aluno1@student.edu", "matricula": "2024001", "name": "Ana Costa"},
                {"id": generate_uuid(), "email": "aluno2@student.edu", "matricula": "2024002", "name": "Bruno Lima"},
                {"id": generate_uuid(), "email": "aluno3@student.edu", "matricula": "2024003", "name": "Carla Mendes"},
                {"id": generate_uuid(), "email": "aluno4@student.edu", "matricula": "2024004", "name": "Diego Pereira"},
                {"id": generate_uuid(), "email": "aluno5@student.edu", "matricula": "2024005", "name": "Elena Rodrigues"}
            ]
            
            students = []
            for data in students_data:
                student = Aluno(**data)
                students.append(student)
                db.add(student)
            
            await db.flush()
            
            # Create sample turmas
            turmas_data = [
                {"id": generate_uuid(), "nome_turma": "BD-2024-1", "disciplina_id": disciplinas[0].id, "year": datetime(2024, 1, 1)},
                {"id": generate_uuid(), "nome_turma": "WEB-2024-1", "disciplina_id": disciplinas[1].id, "year": datetime(2024, 1, 1)},
                {"id": generate_uuid(), "nome_turma": "ED-2024-1", "disciplina_id": disciplinas[2].id, "year": datetime(2024, 1, 1)}
            ]
            
            turmas = []
            for data in turmas_data:
                turma = Turma(**data)
                turmas.append(turma)
                db.add(turma)
            
            await db.flush()
            
            # Add professors to turmas
            integrantes_prof = [
                {"turma_id": turmas[0].id, "professor_id": professors[0].id, "tipo": "professor"},
                {"turma_id": turmas[1].id, "professor_id": professors[1].id, "tipo": "professor"},
                {"turma_id": turmas[2].id, "professor_id": professors[2].id, "tipo": "professor"}
            ]
            
            for data in integrantes_prof:
                integrante = IntegranteDaTurma(**data)
                db.add(integrante)
            
            # Add students to turmas
            integrantes_students = [
                # BD class - students 1, 2, 3
                {"turma_id": turmas[0].id, "aluno_id": students[0].id, "tipo": "aluno"},
                {"turma_id": turmas[0].id, "aluno_id": students[1].id, "tipo": "aluno"},
                {"turma_id": turmas[0].id, "aluno_id": students[2].id, "tipo": "aluno"},
                
                # WEB class - students 2, 3, 4
                {"turma_id": turmas[1].id, "aluno_id": students[1].id, "tipo": "aluno"},
                {"turma_id": turmas[1].id, "aluno_id": students[2].id, "tipo": "aluno"},
                {"turma_id": turmas[1].id, "aluno_id": students[3].id, "tipo": "aluno"},
                
                # ED class - students 3, 4, 5
                {"turma_id": turmas[2].id, "aluno_id": students[2].id, "tipo": "aluno"},
                {"turma_id": turmas[2].id, "aluno_id": students[3].id, "tipo": "aluno"},
                {"turma_id": turmas[2].id, "aluno_id": students[4].id, "tipo": "aluno"}
            ]
            
            for data in integrantes_students:
                integrante = IntegranteDaTurma(**data)
                db.add(integrante)
            
            # Create sample class sessions
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            tomorrow = today + timedelta(days=1)
            
            class_sessions = [
                {"id": generate_uuid(), "turma_id": turmas[0].id, "data": yesterday, "aula_foi_dada": True, "professor_id": professors[0].id},
                {"id": generate_uuid(), "turma_id": turmas[0].id, "data": today, "aula_foi_dada": False, "professor_id": professors[0].id},
                {"id": generate_uuid(), "turma_id": turmas[1].id, "data": today, "aula_foi_dada": False, "professor_id": professors[1].id},
                {"id": generate_uuid(), "turma_id": turmas[2].id, "data": tomorrow, "aula_foi_dada": False, "professor_id": professors[2].id}
            ]
            
            for data in class_sessions:
                session = DiaDeAula(**data)
                db.add(session)
            
            await db.commit()
            print("✅ Sample data created successfully!")
            
            # Print summary
            print("\n📊 Sample Data Summary:")
            print(f"   📚 Disciplinas: {len(disciplinas)}")
            print(f"   👨‍🏫 Professors: {len(professors)}")
            print(f"   👨‍🎓 Students: {len(students)}")
            print(f"   🏫 Classes (Turmas): {len(turmas)}")
            print(f"   📅 Class Sessions: {len(class_sessions)}")
            
            print("\n🔐 Sample Login Credentials:")
            print("   Professors:")
            for i, prof in enumerate(professors):
                print(f"     - {prof.email} / professor123")
            print("   Students:")
            for i, student in enumerate(students):
                print(f"     - {student.email} / student123")
                
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating sample data: {str(e)}")
            raise


async def main():
    """Main function"""
    print("🚀 Initializing database and creating sample data...")
    
    # Create tables
    await create_tables()
    print("✅ Database tables created!")
    
    # Create sample data
    await create_sample_data()
    
    print("\n🎉 Database initialization complete!")
    print("🌐 You can now start the API server with: uvicorn main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
