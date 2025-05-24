from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any

# Database clients initialization
import psycopg2
from psycopg2.extras import RealDictCursor
from neo4j import GraphDatabase
import redis
from pymongo import MongoClient
import json

# Create persistent connections
pg_conn = psycopg2.connect(dbname="university_db", user="user", password="password", host="postgres")
pg_cur = pg_conn.cursor(cursor_factory=RealDictCursor)

neo_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))

redis_conn = redis.Redis(host="redis", port=6379, db=0)

mongo_conn = MongoClient("mongodb://mongo:27017/")

app = FastAPI()

#Получаем id группы и кафедры
def get_group_info(name: str) -> Dict[str, Any]:
    pg_cur.execute(
        """
        SELECT id AS grp_id, department_id
        FROM groups
        WHERE name = %s
        """,
        (name,)
    )
    return pg_cur.fetchone() or {}

#Получаем список специальных курсов для указанной группы
def get_courses(group_name: str) -> List[Dict[str, Any]]:

    pg_cur.execute(
        """
        SELECT lc.id AS course_id,
               lc.name AS course_name,
               lc.planned_hours,
               l.id AS lecture_id
        FROM lecture_course lc
        JOIN lectures l ON lc.id = l.course_id
        JOIN schedule s ON l.id = s.lecture_id
        JOIN groups g ON g.id = s.group_id
        WHERE l.is_special = TRUE AND g.name = %s
        """,
        (group_name,)
    )
    return pg_cur.fetchall()

#Получаем расписание из Neo4j для группы и списка лекций, инфу о студенте
def get_schedules(group_name: str, lec_ids: List[int]) -> List[tuple]:
    query = (
        """
        MATCH (g:Group {name: $grp})-[sch:HAS_SCHEDULE]->(l:Lecture)
        WHERE l.id IN $lec_ids
        WITH g, l, sch
        MATCH (s:Student)-[:BELONGS_TO]->(g)
        RETURN s.id AS student_id, l.id AS lecture_id, sch.schedule_id AS sched_id
        """
    )
    with neo_driver.session() as session:
        res = session.run(query, grp=group_name, lec_ids=lec_ids)
        return [(r['student_id'], r['lecture_id'], r['sched_id']) for r in res]

#Подсчёт посещаемости
def count_presence(student_id: int, sched_id: int) -> int:
    pg_cur.execute(
        """
        SELECT COUNT(*) * 2 AS attended
        FROM attendance
        WHERE student_id = %s AND schedule_id = %s
          AND status IN ('presence','late')
        """,
        (student_id, sched_id)
    )
    return pg_cur.fetchone().get('attended', 0)

#Получаем инфу о студентах
def get_students(sids: List[int]) -> Dict[int, Any]:
    students = {}
    for sid in sids:
        data = redis_conn.get(f"student:{sid}")
        if data:
            students[sid] = json.loads(data)
    return students

#Получаем организационную структуру университетов
def get_org_structure(dept_id: int) -> Dict[str, Any]:
    rec = mongo_conn['university'].university.find_one(
        {"institutes.departments.id": dept_id},
        {"institutes": 1, "name": 1}
    ) or {}
    for inst in rec.get('institutes', []):
        for dept in inst.get('departments', []):
            if dept['id'] == dept_id:
                return {
                    'department': dept['name'],
                    'institute': inst['name'],
                    'university': rec.get('name', '')
                }
    return {}

# --- Endpoint ---
@app.get("/group-attendance", response_model=List)
async def attendance_report(group_name: str = Query(..., description="Название группы, например SRSE-767")) -> List[Dict[str, Any]]:
    grp = get_group_info(group_name)
    if not grp:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    courses = get_courses(group_name)
    if not courses:
        raise HTTPException(status_code=404, detail="Курсы не найдены для группы")

    schedules = get_schedules(group_name, [c['lecture_id'] for c in courses])
    attendance_map: Dict[int, Dict[int, int]] = {}
    for sid, lid, sched_id in schedules:
        attended = count_presence(sid, sched_id)
        attendance_map.setdefault(sid, {})[lid] = attended

    students = get_students(list(attendance_map.keys()))
    org = get_org_structure(grp['department_id'])

    response: List[Dict[str, Any]] = []
    for course in courses:
        for sid, info in students.items():
            response.append({
                'group': group_name,
                'student_full_name': info.get('full_name'),
                'course': course['course_name'],
                'planned_hours': course['planned_hours'],
                'attended_hours': attendance_map.get(sid, {}).get(course['lecture_id'], 0),
                'department': org.get('department'),
                'institute': org.get('institute'),
                'university': org.get('university')
            })
    return response