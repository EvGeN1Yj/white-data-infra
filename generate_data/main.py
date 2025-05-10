import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from psycopg2 import sql
from faker import Faker
from faker.providers import BaseProvider
import random
import json
import redis
from elasticsearch import Elasticsearch, helpers
from pymongo import MongoClient
from neo4j import GraphDatabase
import os
from datetime import datetime, date, timedelta
fake = Faker('ru_RU')  # Для русскоязычных данных

def new_university():
    return {
        "name": ''.join(fake.random_uppercase_letter() for _ in range(random.randint(3, 5))),
        "address": f"{fake.city()}, {fake.street_address()}"
    }

def new_department():
    return f"Кафедра {fake.company()}"  # В Faker нет department_name(), используем company()

def new_institute():
    return {
        "name": f"Институт {fake.word().title()}"
    }

def new_specialty():
    # Возвращает список: [code, specialty_name]
    code = ".".join(f"{random.randint(0, 99):02d}" for _ in range(3))
    name = fake.job()
    return {"code": code, "name": name}

def new_lecture_material():
    return {
        "name": f"Текст Лекции. Тэги: {fake.word()}, {fake.word()}, {fake.word()}",
        "description": fake.text()
    }

def new_student():
    return {
        "full_name": fake.name(),
        "student_record": f"{fake.random_uppercase_letter()}{random.randint(0,999):03d}"
    }

def new_group():
    name = "".join(f"{fake.random_uppercase_letter()}" for _ in range(4)) + f"-{random.randint(0,999):03d}"
    return {
        "name": name,
        "course": random.randint(1,4)
    }

def new_lecture_course():
    return {
        "name": fake.word().title(),
        "planned_hours": random.randint(8,80)
    }

def new_lecture():
    reqs_count = random.randint(0, 10)
    reqs_words = [fake.word() for _ in range(reqs_count)]
    reqs = ", ".join(reqs_words)
    return {
        "topic": fake.word().title(),
        "is_special": bool(random.randint(0, 1)),
        "tech_requirements": reqs
    }

def new_schedule():
    return {
        "auditorium": f"{fake.random_uppercase_letter()}-{random.randint(1,999):03d}",
        "capacity": random.randint(30,100)
    }

def convert_to_monday(input_date):
    if isinstance(input_date, str):
        try:
            given_date = datetime.strptime(input_date, '%Y-%m-%d %H:%M:%S').date()
        except ValueError:
            given_date = datetime.strptime(input_date, '%Y-%m-%d').date()
    else:
        given_date = input_date.date() if isinstance(input_date, datetime) else input_date
    day_of_week = given_date.isoweekday()
    delta = timedelta(days=day_of_week - 1)
    monday_date = given_date - delta
    return monday_date.isoformat()


def generate_random_date(start_date, end_date):
    days_between = (end_date - start_date).days
    times = ['9:00', '11:00', '13:00', '15:00']
    random_days = random.randint(0, days_between)
    #random_days = random.randrange(time_between.days)
    #random_date = start_date + timedelta(days=random_days)
    random_date = start_date + timedelta(days=random_days)
    random_time = random.choice(times)
    random_datetime = datetime.strptime(f"{random_date.strftime('%Y-%m-%d')} {random_time}",'%Y-%m-%d %H:%M')
    return random_datetime


start_date_semester = datetime.strptime("2025-01-10", "%Y-%m-%d")
end_date_semester = datetime.strptime("2025-12-20", "%Y-%m-%d")

def insert_universities(cur, num):
    universities = [new_university() for _ in range(num)]
    values = [(u["name"], u["address"]) for u in universities]
    sql = "INSERT INTO universities (name, address) VALUES (%s, %s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, name FROM universities;")
    return cur.fetchall()

def insert_institutes(cur, universities, institutes_per_uni):
    institutes = []
    for uni in universities:
        uni_id = uni[0]  
        for _ in range(institutes_per_uni):
            inst = new_institute()
            inst["university_id"] = uni_id
            institutes.append(inst)
    values = [(inst["name"], inst["university_id"]) for inst in institutes]
    sql = "INSERT INTO institutes (name, university_id) VALUES (%s, %s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, name, university_id FROM institutes;")
    return cur.fetchall()

def insert_departments(cur, institutes, departments_per_inst):
    departments = []
    for inst in institutes:
        inst_id = inst[0]
        for _ in range(departments_per_inst):
            dept = {
                "name": new_department(),
                "institute_id": inst_id
            }
            departments.append(dept)
    values = [(d["name"], d["institute_id"]) for d in departments]
    sql = "INSERT INTO departments (name, institute_id) VALUES (%s, %s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, name, institute_id FROM departments;")
    return cur.fetchall()


def insert_specialties(cur, num):
    specialties = [new_specialty() for _ in range(num)]
    values = [(s["code"], s["name"]) for s in specialties]
    sql = "INSERT INTO specialties (code, name) VALUES (%s, %s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, code FROM specialties;")
    return cur.fetchall()

def insert_lecture_courses(cur, departments, specialties, courses_per_dept):
    courses = []
    for dept in departments:
        dept_id = dept[0]
        for _ in range(courses_per_dept):
            lc = new_lecture_course()
            lc["department_id"] = dept_id
            lc["specialty_id"] = random.choice(specialties)[0]
            courses.append(lc)
    values = [(c["name"], c["department_id"], c["specialty_id"], c["planned_hours"]) for c in courses]
    sql = "INSERT INTO lecture_course (name, department_id, specialty_id, planned_hours) VALUES (%s,%s,%s,%s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, department_id FROM lecture_course;")
    return cur.fetchall()

def insert_lectures(cur, courses, lectures_per_course):
    lectures = []
    for course in courses:
        course_id = course[0]
        for _ in range(lectures_per_course):
            lec = new_lecture()
            lec["course_id"] = course_id
            lectures.append(lec)
    values = [(l["topic"], l["course_id"], l["is_special"], l["tech_requirements"]) for l in lectures]
    sql = "INSERT INTO lectures (topic, course_id, is_special, tech_requirements) VALUES (%s,%s,%s,%s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, course_id FROM lectures;")
    return cur.fetchall()

def insert_lecture_materials(cur, lectures, materials_per_lecture):
    materials = []
    for lec in lectures:
        lec_id = lec[0]
        for _ in range(materials_per_lecture):
            mat = new_lecture_material()
            mat["lecture_id"] = lec_id
            materials.append(mat)
    values = [(m["name"], m["description"], m["lecture_id"]) for m in materials]
    sql = "INSERT INTO lecture_materials (name, description, lecture_id) VALUES (%s,%s,%s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id FROM lecture_materials;")
    return cur.fetchall()

def insert_groups(cur, departments, groups_per_dept):
    groups = []
    for dept in departments:
        dept_id = dept[0]
        for _ in range(groups_per_dept):
            gr = new_group()
            gr["department_id"] = dept_id
            groups.append(gr)
    values = [(g["name"], g["course"], g["department_id"]) for g in groups]
    sql = "INSERT INTO groups (name, course, department_id) VALUES (%s,%s,%s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, department_id FROM groups;")
    return cur.fetchall()

def insert_students(cur, groups, students_per_group):
    students = []
    for grp in groups:
        group_id = grp[0]
        for _ in range(students_per_group):
            st = new_student()
            st["group_id"] = group_id
            students.append(st)
    values = [(s["full_name"], s["student_record"], s["group_id"]) for s in students]
    sql = "INSERT INTO students (full_name, student_record, group_id) VALUES (%s,%s,%s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, group_id FROM students;")
    return cur.fetchall()

def insert_schedule(cur, groups, lectures, schedules_per_group):
    schedules = []
    for group in groups:
        for i in range(schedules_per_group):
            lec = random.choice(lectures)
            sch = new_schedule()
            sch["group_id"] = group[0]
            sch["lecture_id"] = lec[0]
            schedules.append(sch)
    '''
    for grp in groups:
        group_id = grp[0]
        lec = random.choice(lectures)
        sch = new_schedule()
        sch["group_id"] = group_id
        sch["lecture_id"] = lec[0]
        schedules.append(sch)
    '''
    values = [(s["auditorium"], s["group_id"], s["lecture_id"], s["capacity"]) for s in schedules]
    sql = "INSERT INTO schedule (auditorium, group_id, lecture_id, capacity) VALUES (%s,%s,%s,%s);"
    cur.executemany(sql, values)
    cur.execute("SELECT id, group_id FROM schedule;")
    return cur.fetchall()

def insert_attendance(cur, students, schedules):
    attendance = []
    possible_status = ['presence', 'absence', 'late']
    
    # group_id -> список student_id
    group_students = {}
    for st in students:
        st_id, group_id = st
        group_students.setdefault(group_id, []).append(st_id)
    
    for sch in schedules:
        schedule_id, group_id = sch
        
        random_date = generate_random_date(start_date_semester, end_date_semester)
        week_start_date = convert_to_monday(str(random_date))
        for st_id in group_students.get(group_id, []):
            # Случайное количество записей посещаемости для данного студента по этому расписанию
            num_records = random.randint(4,50)
            for _ in range(num_records):
                
                att = {
                    "student_id": st_id,
                    "schedule_id": schedule_id,
                    "attendance_date": random_date,
                    "week_start": week_start_date,
                    "status": random.choice(possible_status)
                }
                attendance.append(att)
    
    values = [(a["student_id"], a["schedule_id"], a["attendance_date"], a["week_start"], a["status"]) for a in attendance]
    sql = "INSERT INTO attendance (student_id, schedule_id, attendance_date, week_start, status) VALUES (%s, %s, %s, %s, %s);"
    cur.executemany(sql, values)


pg_conn = psycopg2.connect(host="postgres", port="5432", database="university_db", user="user", password="password")

# Redis
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# Elasticsearch
es = Elasticsearch(hosts=["http://elasticsearch:9200"])
ES_INDEX = "lecture_materials" 

# MongoDB
mongo_client = MongoClient("mongodb://mongo:27017/")
mongo_db = mongo_client["university"]

# Neo4j
neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))


def read_sql(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError("Файл sql не найден")
    with open(filepath, 'r') as f:
        sql_queries = f.read()
    queries = [q.strip() for q in sql_queries.split(";") if q.strip()]

    return queries    

def read_sql_by_delimeter(filepath, delim):
    if not os.path.exists(filepath):
        raise FileNotFoundError("Файл sql не найден")
    with open(filepath, 'r') as f:
        sql_queries = f.read()
    queries = [q.strip() for q in sql_queries.split(delim) if q.strip()]

    return queries

def create_tables():
    try:
        queries = read_sql("create.sql")
        pg_conn.autocommit = True
        cur = pg_conn.cursor()
        for q in queries:
            print(q)
            cur.execute(q)
        #funcs_trigs = read_sql_by_delimeter("functions.sql", "@")
        date_start = '2025-01-06'
        date_current_format = datetime.strptime(date_start, '%Y-%m-%d')
        date_end = '2025-12-28'
        date_end_format = datetime.strptime(date_end, '%Y-%m-%d')
        i = 1
        while date_current_format < (date_end_format - timedelta(days=7)):
            
            print(f"Заполнение партиции {i}:")
            print(f"Начало: {str(date_current_format.strftime('%Y-%m-%d'))} -> Конец: {str((date_current_format+timedelta(days=7)).strftime('%Y-%m-%d'))}")
            cur.execute(f"CREATE TABLE attendance_2025_{i} PARTITION OF attendance FOR VALUES FROM ('{str(date_current_format.strftime('%Y-%m-%d'))}') TO ('{str((date_current_format+timedelta(days=6)).strftime('%Y-%m-%d'))}');")
            date_current_format += timedelta(days=7)
            i+=1
        cur.close()
        
        print("Созданы таблицы")
    except Exception as e:
        print(e)

create_tables()

try:
    print("Генерация запущена")
    with pg_conn:
        with pg_conn.cursor() as cur:
            universities = insert_universities(cur, 1)
            #print("Добавленные университеты:", universities)
            
            institutes = insert_institutes(cur, universities, 3)
            #print("Добавленные институты:", institutes)
            
            departments = insert_departments(cur, institutes, 3)
            #print("Добавленные кафедры:", departments)
            
            specialties = insert_specialties(cur, 3)
            #print("Добавленные специальности:", specialties)
            #
            courses = insert_lecture_courses(cur, departments, specialties, 3)
            #print("Добавленные курсы:", courses)
            
            lectures = insert_lectures(cur, courses, 5)
            #print("Добавленные лекции:", lectures)
            
            lecture_materials = insert_lecture_materials(cur, lectures, 1)
            #print("Добавленные материалы лекций:", lecture_materials)

            groups = insert_groups(cur, departments, 3)
            #print("Добавленные группы:", groups)
                
            students = insert_students(cur, groups, 10)
            #print("Добавленные студенты:", students)
                
            schedules = insert_schedule(cur, groups, lectures, 10)
            #print("Добавленное расписание")
       
            insert_attendance(cur, students, schedules)
            print("Добавлены записи о посещаемости успешно!")

except Exception as e:
    print(e)

finally:
    pg_conn.commit()


def fetch_all(query):
    with pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        results = cur.fetchall()
    return results


# Добавление студентов в Redis
def add_students_to_redis():
    query = "SELECT id, full_name, student_record, group_id FROM students;"
    students = fetch_all(query)
    for student in students:
        key = f"student:{student['id']}"
        value = json.dumps(student, ensure_ascii=False)
        redis_client.set(key, value)
    print(f"Добавление {len(students)} студентов в Redis.")

#Добавление lecture_materials в Elasticsearch
def add_lecture_materials_to_es():
    query = "SELECT id, name, description, lecture_id FROM lecture_materials;"
    materials = fetch_all(query)
    
    actions = [
        {
            "_index": ES_INDEX,
            "_id": material["id"],
            "_source": material
        }
        for material in materials
    ]
    
    if actions:
        helpers.bulk(es, actions)
    print(f"Добавлено {len(materials)} материалов лекций в Elasticsearch (индекс '{ES_INDEX}').")


# Добавление данных об университетах, институтах и кафедрах в MongoDB
def add_universities_to_mongo():
    universities = fetch_all("SELECT id, name, address FROM universities;")
    institutes = fetch_all("SELECT id, name, university_id FROM institutes;")
    departments = fetch_all("SELECT id, name, institute_id FROM departments;")
    

    uni_dict = {}
    for uni in universities:
        uni_dict[uni["id"]] = {
            "id": uni["id"],
            "name": uni["name"],
            "address": uni["address"],
            "institutes": []
        }
    
    inst_dict = {}
    for inst in institutes:
        inst_dict[inst["id"]] = {
            "id": inst["id"],
            "name": inst["name"],
            "departments": []
        }
        uni = uni_dict.get(inst["university_id"])
        if uni:
            uni["institutes"].append(inst_dict[inst["id"]])
    
    for dept in departments:

        inst = inst_dict.get(dept["institute_id"])
        if inst:
            inst["departments"].append({
                "id": dept["id"],
                "name": dept["name"]
            })
    
    collection = mongo_db["university"]
    collection.delete_many({})
    
    documents = list(uni_dict.values())
    if documents:
        collection.insert_many(documents)
    print(f"Добавлено {len(documents)} университетов с вложенными институтами и кафедрами в MongoDB.")



def add_relationships_to_neo4j():
    # Получаем все необходимые данные из PostgreSQL
    students = fetch_all("""
        SELECT id, full_name, group_id 
        FROM students;
    """)
    
    groups = fetch_all("""
        SELECT id, name, course, department_id 
        FROM groups;
    """)
    
    schedules = fetch_all("""
        SELECT s.id, s.group_id, s.lecture_id, s.capacity
        FROM schedule s;
    """)
    
    lectures = fetch_all("""
        SELECT l.id, l.course_id, l.topic, l.tech_requirements, l.is_special,
               lc.department_id, lc.name as course_name
        FROM lectures l 
        JOIN lecture_course lc ON l.course_id = lc.id;
    """)
    
    departments = fetch_all("""
        SELECT id, name 
        FROM departments;
    """)
    
    # Получаем данные о посещаемости
    attendance = fetch_all("""
        SELECT a.schedule_id, a.student_id, a.attendance_date, a.status
        FROM attendance a;
    """)

    def run_tx(tx, cypher, params=None):
        tx.run(cypher, params or {})
    
    with neo4j_driver.session() as session:
        # Создаем узлы Student
        for s in students:
            session.execute_write(run_tx,
                """
                MERGE (st:Student {
                    id: $id, 
                    full_name: $full_name, 
                    group_id: $group_id
                })
                """,
                {"id": s["id"], "full_name": s["full_name"], "group_id": s["group_id"]}
            )

        # Создаем узлы Group
        for g in groups:
            session.execute_write(run_tx,
                """
                MERGE (gr:Group {
                    id: $id,
                    name: $name,
                    course: $course,
                    department_id: $department_id
                })
                """,
                {"id": g["id"], "name": g["name"], "course": g["course"], 
                 "department_id": g["department_id"]}
            )

        # Создаем узлы Lecture
        for l in lectures:
            session.execute_write(run_tx,
                """
                MERGE (lec:Lecture {
                    id: $id,
                    course_id: $course_id,
                    topic: $topic,
                    tech_requirements: $tech_requirements,
                    is_special: $is_special,
                    department_id: $department_id,
                    course_name: $course_name
                })
                """,
                {"id": l["id"], "course_id": l["course_id"], "topic": l["topic"],
                 "tech_requirements": l["tech_requirements"], "is_special": l["is_special"],
                 "department_id": l["department_id"], "course_name": l["course_name"]}
            )

        # Создаем узлы Department
        for d in departments:
            session.execute_write(run_tx,
                """
                MERGE (dep:Department {
                    id: $id,
                    name: $name
                })
                """,
                {"id": d["id"], "name": d["name"]}
            )

        # Создаем связи (Student)-[:BELONGS_TO]->(Group)
        for s in students:
            session.execute_write(run_tx,
                """
                MATCH (st:Student {id: $student_id})
                MATCH (gr:Group {id: $group_id})
                MERGE (st)-[:BELONGS_TO]->(gr)
                """,
                {"student_id": s["id"], "group_id": s["group_id"]}
            )
        
        # Создаем связи (Group)-[:HAS_SCHEDULE]->(Lecture) с данными из attendance
        for sch in schedules:
            # Находим все записи посещаемости для данного расписания
            schedule_attendance = [a for a in attendance if a["schedule_id"] == sch["id"]]
            
            for att in schedule_attendance:
                session.execute_write(run_tx,
                    """
                    MATCH (gr:Group {id: $group_id})
                    MATCH (lec:Lecture {id: $lecture_id})
                    MERGE (gr)-[h:HAS_SCHEDULE]->(lec)
                    SET h.schedule_id = $schedule_id,
                        h.attendance_date = $attendance_date,
                        h.status = $status,
                        h.capacity = $capacity
                    """,
                    {
                        "group_id": sch["group_id"],
                        "lecture_id": sch["lecture_id"],
                        "schedule_id": sch["id"],
                        "attendance_date": att["attendance_date"],
                        "status": att["status"],
                        "capacity": sch["capacity"]
                    }
                )
        
        # Создаем связи (Lecture)-[:ORIGINATES_FROM]->(Department)
        for l in lectures:
            session.execute_write(run_tx,
                """
                MATCH (lec:Lecture {id: $lecture_id})
                MATCH (dep:Department {id: $department_id})
                MERGE (lec)-[:ORIGINATES_FROM]->(dep)
                """,
                {"lecture_id": l["id"], "department_id": l["department_id"]}
            )
    
    print("Добавление связей и узлов выполнено в Neo4j.")
def add_all():
    add_students_to_redis()
    add_lecture_materials_to_es()
    add_universities_to_mongo()
    add_relationships_to_neo4j()


add_all()
pg_conn.close()







