import datetime
import logging
from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any
import psycopg2
from neo4j import GraphDatabase
from pymongo import MongoClient
import os

# Настройка логгера
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ----- Configuration -----

# Init FastAPI
app = FastAPI()

# Подключение к PostgreSQL
pg_conn = psycopg2.connect(host="postgres", port="5432", database="university_db", user="user", password="password")
pg_conn.autocommit = True

# Подключение к Neo4j

neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))

# Подключение к MongoDB
mongo_client = MongoClient(f"mongodb://mongo:27017/")
mongo_db = mongo_client['university']


@app.get("/auditorium-requirements", response_model=List[Dict[str, Any]])
async def get_auditorium_requirements(
        year: int = Query(..., description="Год обучения"),
        semester: int = Query(..., description="Семестр (1 или 2)")
) -> List[Dict[str, Any]]:
    try:
        # Определяем период семестра
        if semester == 1:
            start_date = datetime.date(year, 9, 1)  # Осенний семестр
            end_date = datetime.date(year, 12, 31)
        else:
            start_date = datetime.date(year, 2, 1)  # Весенний семестр
            end_date = datetime.date(year, 6, 30)

        # 1. Получаем базовую информацию о курсах и лекциях из PostgreSQL
        with pg_conn.cursor() as cur:
            cur.execute("""
                        SELECT DISTINCT lc.id  AS course_id,
                                        lc.name  AS course_name,
                                        l.id AS lecture_id,
                                        l.topic,
                                        l.tech_requirements,
                                        l.is_special,
                                        MIN(a.attendance_date)::date as lecture_date,
                                        d.id  AS department_id,
                                        d.name AS department_name,
                                        s.auditorium,
                                        s.capacity
                        FROM lecture_course lc
                                 JOIN lectures l ON l.course_id = lc.id
                                 JOIN departments d ON lc.department_id = d.id
                                 JOIN schedule s ON s.lecture_id = l.id
                                 JOIN attendance a ON a.schedule_id = s.id
                        WHERE a.attendance_date::date BETWEEN %s AND %s
                          AND l.tech_requirements IS NOT NULL
                        GROUP BY lc.id, lc.name, l.id, l.topic,
                                 l.tech_requirements, l.is_special, d.id, d.name,
                                 s.auditorium, s.capacity
                        ORDER BY MIN(a.attendance_date)::date
                        """, (start_date, end_date))

            lectures_data = cur.fetchall()

        result = []
        for (course_id, course_name, lecture_id, topic, tech_requirements,
             is_special, lecture_date, department_id, department_name,
             auditorium, capacity) in lectures_data:

            # 2. Получаем количество студентов из Neo4j
            with neo4j_driver.session() as session:
                student_count = session.run("""
                    MATCH (l:Lecture {id: $lecture_id})<-[:HAS_SCHEDULE]-(g:Group)
                    MATCH (s:Student)-[:BELONGS_TO]->(g)
                    RETURN count(DISTINCT s) as student_count
                """, lecture_id=lecture_id).single()["student_count"]

            # 3. Получаем информацию об университете из MongoDB
            org_info = mongo_db.university.find_one(
                {"institutes.departments.id": department_id},
                {"name": 1, "institutes.name": 1, "institutes.departments": 1}
            )

            institute_name = ""
            university_name = ""
            if org_info:
                university_name = org_info.get("name", "")
                for inst in org_info.get("institutes", []):
                    for dept in inst.get("departments", []):
                        if dept.get("id") == department_id:
                            institute_name = inst.get("name", "")
                            break
                    if institute_name:
                        break

            # Рассчитываем требуемую вместимость с запасом 10%
            required_capacity = int(student_count * 1.1)

            report = {
                "course_info": {
                    "course_id": course_id,
                    "course_name": course_name,
                    "department": department_name,
                    "institute": institute_name,
                    "university": university_name
                },
                "lecture_info": {
                    "lecture_id": lecture_id,
                    "topic": topic,
                    "tech_requirements": tech_requirements or "Не указаны",
                    "date": lecture_date.isoformat(),
                    "is_special": is_special,
                    "auditorium": {
                        "number": auditorium,
                        "capacity": capacity
                    }
                },
                "student_count": student_count,
                "required_capacity": required_capacity
            }
            result.append(report)

        return result

    except Exception as e:
        logger.error(f"Error in get_auditorium_requirements: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))