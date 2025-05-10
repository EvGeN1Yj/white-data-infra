import datetime
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from neo4j import GraphDatabase

# Настройка логгера
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ----- Configuration -----
PG_HOST = "postgres"
PG_PORT = 5432
PG_DB = "university_db"
PG_USER = "user"
PG_PASS = "password"

NEO4J_URI = "bolt://neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Init FastAPI
app = FastAPI()

# Init Postgres sync connection
pg_conn = psycopg2.connect(
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DB,
    user=PG_USER,
    password=PG_PASS
)
pg_conn.autocommit = True

# Init Neo4j sync driver
neo4j_driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

# ----- Pydantic models -----
class LectureReport(BaseModel):
    course_id: int
    course_name: str
    lecture_id: int
    lecture_topic: str
    tech_requirements: Optional[str]
    attendees_count: int

class RoomReportResponse(BaseModel):
    year: int
    semester: int
    data: List[LectureReport]


class LectureInfo(BaseModel):
    course_name: str
    topic: str
    tech_requirements: str
    total_listeners: int


@app.get("/auditorium-requirements", response_model=[])
def get_auditorium_requirements(year: int = Query(...), semester: int = Query(...)):
    result = []

    try:
        cur = pg_conn.cursor()

        # 1. Получаем данные по лекциям и группам, участвующим в семестре и году (предположим, семестр влияет на название курса)
        start, end = datetime.date(year,6,1), datetime.date(year,12,30)
        if semester == 2:
            start, end = datetime.date(year,1,1), datetime.date(year,6,30)

        cur.execute("""
            SELECT 
                lc.name AS course_name,
                l.id AS lecture_id,
                l.topic,
                l.tech_requirements,
                COUNT(DISTINCT s.id) AS total_listeners
            FROM lecture_course lc
            JOIN lectures l ON l.course_id = lc.id
            JOIN schedule sch ON sch.lecture_id = l.id
            JOIN attendance AS A ON A.schedule_id = A.id
            JOIN groups g ON sch.group_id = g.id
            JOIN students s ON s.group_id = g.id
            WHERE A.attendance_date BETWEEN %s and %s 
            GROUP BY lc.name, l.id, l.topic, l.tech_requirements
        """, (start, end))

        lectures = cur.fetchall()
        logging.info("Auditorium requirements fetched ", len(lectures))

        for course_name, lecture_id, topic, tech_requirements, total_listeners in lectures:
            # 2. Используем Neo4j для уточнения, если это специальная лекция или требуется особое оборудование
            with neo4j_driver.session() as session:
                special_flag = session.run(
                    """
                    MATCH (lec:Lecture {id: $lecture_id})
                    RETURN lec.is_special AS is_special
                    """,
                    lecture_id=lecture_id
                ).single()

                is_special = special_flag["is_special"] if special_flag else False
            result.append({
                "course_name":course_name,
                "topic":topic + (" (Спец.)" if is_special else ""),
                "tech_requirements":tech_requirements or "Не указаны",
                "total_listeners":total_listeners
            })

        cur.close()
        return result

    except Exception as e:
        return [{"error": str(e)}]