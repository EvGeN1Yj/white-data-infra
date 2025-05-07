from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2 import sql
import logging

# Настройка логгера
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()


# Модели данных
class User(BaseModel):
    username: str


class ClassroomRequirement(BaseModel):
    course_name: str
    lecture_name: str
    required_capacity: int
    tech_requirements: List[str]
    total_students: int
    semester: int
    year: int


# Настройки аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Упрощенная проверка токена для тестирования
    # В реальном приложении нужно проверять JWT токен
    return User(username="testuser")


# Подключение к БД
def get_db_connection():
    return psycopg2.connect(
        dbname="university_db",
        user="user",
        password="password",
        host="postgres"
    )


@app.get("/reports/classroom_requirements/", response_model=List[ClassroomRequirement])
async def get_classroom_requirements(
        semester: int,
        year: int,
        current_user: User = Depends(get_current_user)
):
    """
    Возвращает отчет о требованиях к аудиториям для заданного семестра и года.
    Включает информацию о курсах, лекциях, количестве студентов и технических требованиях.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
                SELECT c.name                           AS course_name, \
                       l.name                           AS lecture_name, \
                       COUNT(DISTINCT s.student_number) AS total_students, \
                       l.tech_equipment, \
                       g.formation_year AS year,
                CASE 
                    WHEN EXTRACT(MONTH FROM sch.timestamp) BETWEEN 9 AND 12 THEN 1
                    WHEN EXTRACT(MONTH FROM sch.timestamp) BETWEEN 1 AND 6 THEN 2
                    ELSE 0
                END \
                AS semester
            FROM 
                lecture l
                JOIN course c ON l.id_course = c.id
                JOIN schedule sch ON l.id = sch.id_lecture
                JOIN groups g ON sch.id_group = g.id
                JOIN student s ON g.id = s.id_group
            WHERE 
                (EXTRACT(MONTH FROM sch.timestamp) BETWEEN 9 AND 12 AND \
                %s \
                = \
                1 \
                AND \
                EXTRACT \
                ( \
                YEAR \
                FROM \
                sch \
                . \
                timestamp \
                ) \
                = \
                %s \
                )
                OR
                ( \
                EXTRACT \
                ( \
                MONTH \
                FROM \
                sch \
                . \
                timestamp \
                ) \
                BETWEEN \
                1 \
                AND \
                6 \
                AND \
                %s \
                = \
                2 \
                AND \
                EXTRACT \
                ( \
                YEAR \
                FROM \
                sch \
                . \
                timestamp \
                ) \
                = \
                %s \
                )
                GROUP \
                BY
                c \
                . \
                name, \
                l \
                . \
                name, \
                l \
                . \
                tech_equipment, \
                g \
                . \
                formation_year, \
                semester
                HAVING
                CASE
                WHEN \
                EXTRACT \
                ( \
                MONTH \
                FROM \
                sch \
                . \
                timestamp \
                ) \
                BETWEEN \
                9 \
                AND \
                12 \
                THEN \
                1
                WHEN \
                EXTRACT \
                ( \
                MONTH \
                FROM \
                sch \
                . \
                timestamp \
                ) \
                BETWEEN \
                1 \
                AND \
                6 \
                THEN \
                2
                ELSE \
                0
                END \
                = \
                %s
                AND \
                EXTRACT \
                ( \
                YEAR \
                FROM \
                sch \
                . \
                timestamp \
                ) \
                = \
                %s \
                """

        cursor.execute(query, (semester, year, semester, year, semester, year))

        results = []
        for row in cursor.fetchall():
            course_name, lecture_name, total_students, tech_equipment, year, semester = row

            # Рассчитываем требуемую вместимость (студенты + 20% запаса)
            required_capacity = int(total_students * 1.2)

            # Определяем технические требования
            tech_requirements = []
            if tech_equipment:
                tech_requirements.extend(["projector", "sound_system"])
            if "программирование" in course_name.lower():
                tech_requirements.append("computers")
            if "лабораторная" in lecture_name.lower():
                tech_requirements.append("lab_equipment")

            results.append(ClassroomRequirement(
                course_name=course_name,
                lecture_name=lecture_name,
                required_capacity=required_capacity,
                tech_requirements=tech_requirements,
                total_students=total_students,
                semester=semester,
                year=year
            ))

        return results

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()