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

class StudentReport(BaseModel):
    student_id: str  # Изменил на str, так как student_number это строка
    full_name: str
    student_record: str
    group_name: str
    course: int
    kafedra_name: str
    attendance_percent: float
    report_period: str
    search_term: str
    matching_lectures: List[str]

# Настройки аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # В реальном приложении здесь должна быть проверка токена
    # Для примера просто возвращаем тестового пользователя
    return User(username="testuser")

# Подключение к БД
def get_db_connection():
    return psycopg2.connect(
        dbname="university_db",
        user="user",
        password="password",
        host="postgres"
    )

@app.get("/reports/low_attendance/", response_model=List[StudentReport])
async def get_low_attendance_report(
    search_term: str,
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Исправленный SQL-запрос с учетом вашей структуры данных
        query = """
            WITH lecture_matches AS (
                SELECT l.id
                FROM lecture l
                WHERE l.name ILIKE %s
            ),
            student_attendance AS (
                SELECT 
                    s.student_number AS student_id,
                    s.fullname AS full_name,
                    s.student_number AS student_record,
                    g.name AS group_name,
                    g.formation_year AS course,
                    d.name AS kafedra_name,
                    COUNT(a.id) FILTER (WHERE a.status = TRUE) AS present_count,
                    COUNT(a.id) AS total_count
                FROM 
                    student s
                    JOIN groups g ON s.id_group = g.id
                    JOIN department d ON g.id_department = d.id
                    JOIN attendance a ON s.student_number = a.id_student
                    JOIN schedule sch ON a.id_schedule = sch.id
                    JOIN lecture l ON sch.id_lecture = l.id
                WHERE 
                    l.id IN (SELECT id FROM lecture_matches)
                    AND a.week_start BETWEEN %s AND %s
                GROUP BY 
                    s.student_number, s.fullname, g.name, g.formation_year, d.name
                HAVING 
                    COUNT(a.id) > 0
            )
            SELECT 
                student_id,
                full_name,
                student_record,
                group_name,
                course,
                kafedra_name,
                (present_count::float / NULLIF(total_count, 0)) * 100 AS attendance_percent,
                %s AS report_period,
                %s AS search_term,
                ARRAY(
                    SELECT DISTINCT l.name 
                    FROM lecture l
                    JOIN schedule sch ON l.id = sch.id_lecture
                    JOIN attendance att ON sch.id = att.id_schedule
                    WHERE att.id_student = sa.student_id
                    AND l.name ILIKE %s
                    AND att.week_start BETWEEN %s AND %s
                ) AS matching_lectures
            FROM 
                student_attendance sa
            ORDER BY 
                attendance_percent ASC
            LIMIT 10
        """

        search_pattern = f"%{search_term}%"
        cursor.execute(query, (
            search_pattern,
            start_date,
            end_date,
            f"{start_date} - {end_date}",
            search_term,
            search_pattern,
            start_date,
            end_date
        ))

        results = []
        for row in cursor.fetchall():
            results.append(StudentReport(
                student_id=row[0],
                full_name=row[1],
                student_record=row[2],
                group_name=row[3],
                course=row[4],
                kafedra_name=row[5],
                attendance_percent=row[6],
                report_period=row[7],
                search_term=row[8],
                matching_lectures=row[9] if row[9] else []
            ))

        return results
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()