import psycopg2
import random
from faker import Faker
from datetime import date, timedelta
import redis
from pymongo import MongoClient
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
import json
import time

# Инициализация Faker
fake = Faker('ru_RU')

# Подключение к PostgreSQL
conn = psycopg2.connect(
    dbname="university_db",
    user="user",
    password="password",
    host="postgres",
    port="5432"
)
cursor = conn.cursor()

# Подключение к Redis
r = redis.Redis(host='redis', port=6379, db=0)

# Подключение к MongoDB
mongo_client = MongoClient('mongodb://mongo:27017/')
mongo_db = mongo_client['university_db']

es = Elasticsearch('http://elasticsearch:9200', verify_certs=False)

# Подключение к Neo4j
neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687")

def create_tables():
    """Создание таблиц в PostgreSQL"""
    with open('init_db.sql', 'r') as f:
        sql_script = f.read()
    cursor.execute(sql_script)
    conn.commit()
    print("Таблицы созданы успешно")

def generate_universities():
    """Генерация университетов"""
    universities = [
        ("РТУ МИРЭА", "Москва, пр-т Вернадского, 78"),
        ("МГУ", "Москва, Ленинские горы, 1"),
        ("МФТИ", "Московская обл., г. Долгопрудный, Институтский пер., 9"),
        ("ВШЭ", "Москва, ул. Мясницкая, 20"),
        ("МГТУ им. Баумана", "Москва, 2-я Бауманская ул., 5, стр. 1")
    ]
    
    for uni in universities:
        cursor.execute("INSERT INTO universities (name, address) VALUES (%s, %s) RETURNING id", uni)
        uni_id = cursor.fetchone()[0]
        
        # Добавляем в MongoDB
        mongo_db.universities.insert_one({
            "id": uni_id,
            "name": uni[0],
            "address": uni[1],
            "institutes": []
        })
    
    conn.commit()
    return len(universities)

def generate_institutes(uni_count):
    """Генерация институтов"""
    institutes = [
        "Институт кибербезопасности и цифровых технологий",
        "Институт информационных технологий",
        "Институт искусственного интеллекта",
        "Институт радиотехники и электроники",
        "Институт экономики и управления",
        "Институт тонких химических технологий",
        "Физико-технический институт",
        "Институт международных отношений"
    ]
    
    institute_data = []
    for uni_id in range(1, uni_count + 1):
        for i in range(random.randint(2, 4)):
            name = f"{random.choice(institutes)} №{i+1}"
            cursor.execute("INSERT INTO institutes (name, university_id) VALUES (%s, %s) RETURNING id", 
                          (name, uni_id))
            inst_id = cursor.fetchone()[0]
            institute_data.append((inst_id, name, uni_id))
            
            # Обновляем MongoDB
            mongo_db.universities.update_one(
                {"id": uni_id},
                {"$push": {"institutes": {"id": inst_id, "name": name, "departments": []}}}
            )
    
    conn.commit()
    return institute_data

def generate_kafedras(institute_data):
    """Генерация кафедр"""
    kafedra_names = [
        "Кибербезопасности",
        "Информационных систем",
        "Искусственного интеллекта",
        "Радиотехники",
        "Электроники",
        "Экономики",
        "Управления",
        "Программной инженерии",
        "Математики",
        "Физики",
        "Химии",
        "Иностранных языков"
    ]
    
    kafedra_data = []
    for inst_id, inst_name, uni_id in institute_data:
        for i in range(random.randint(3, 6)):
            name = f"Кафедра {random.choice(kafedra_names)} №{i+1}"
            cursor.execute("INSERT INTO kafedra (name, institute_id) VALUES (%s, %s) RETURNING id", 
                          (name, inst_id))
            kaf_id = cursor.fetchone()[0]
            kafedra_data.append((kaf_id, name, inst_id))
            
            # Обновляем MongoDB
            mongo_db.universities.update_one(
                {"institutes.id": inst_id},
                {"$push": {"institutes.$.departments": {"id": kaf_id, "name": name}}}
            )
            
            # Добавляем в Neo4j
            with neo4j_driver.session() as session:
                session.run("CREATE (k:Kafedra {id: $id, name: $name})", 
                          id=kaf_id, name=name)
    
    conn.commit()
    return kafedra_data

def generate_specialities(kafedra_data):
    """Генерация специальностей"""
    specialities = [
        ("09.03.01", "Информатика и вычислительная техника"),
        ("09.03.02", "Информационные системы и технологии"),
        ("09.03.03", "Прикладная информатика"),
        ("09.03.04", "Программная инженерия"),
        ("10.03.01", "Информационная безопасность"),
        ("11.03.02", "Инфокоммуникационные технологии"),
        ("27.03.04", "Управление в технических системах"),
        ("38.03.01", "Экономика"),
        ("38.03.02", "Менеджмент"),
        ("38.03.05", "Бизнес-информатика")
    ]
    
    speciality_data = []
    for kaf_id, kaf_name, inst_id in kafedra_data:
        for code, name in random.sample(specialities, random.randint(2, 4)):
            cursor.execute("INSERT INTO specialities (code, name, kafedra_id) VALUES (%s, %s, %s) RETURNING id", 
                          (code, name, kaf_id))
            spec_id = cursor.fetchone()[0]
            speciality_data.append((spec_id, code, name, kaf_id))
    
    conn.commit()
    return speciality_data

def generate_lecture_courses(kafedra_data, speciality_data):
    """Генерация курсов лекций"""
    courses = [
        "Основы программирования",
        "Базы данных",
        "Операционные системы",
        "Компьютерные сети",
        "Кибербезопасность",
        "Машинное обучение",
        "Искусственный интеллект",
        "Теория алгоритмов",
        "Дискретная математика",
        "Теория вероятностей",
        "Экономика",
        "Менеджмент",
        "Маркетинг",
        "Философия",
        "Иностранный язык",
        "Физика",
        "Химия"
    ]
    
    course_data = []
    for kaf_id, kaf_name, inst_id in kafedra_data:
        for spec_id, code, name, kaf_id_spec in [s for s in speciality_data if s[3] == kaf_id]:
            for i in range(random.randint(4, 8)):
                course_name = f"{random.choice(courses)} ({name})"
                hours = random.choice([32, 48, 64, 72, 96])
                cursor.execute("""
                    INSERT INTO lectures_course (name, kafedra_id, speciality_id, planned_hours) 
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (course_name, kaf_id, spec_id, hours))
                course_id = cursor.fetchone()[0]
                course_data.append((course_id, course_name, kaf_id, spec_id, hours))
    
    conn.commit()
    return course_data

def generate_groups(kafedra_data):
    """Генерация групп"""
    group_types = ["БСБО", "БИБО", "БПМО", "БФКО", "БИНО", "БЭКО"]
    
    group_data = []
    for kaf_id, kaf_name, inst_id in kafedra_data:
        for i in range(random.randint(3, 6)):
            year = random.randint(2019, 2023)
            group_name = f"{random.choice(group_types)}-{str(i+1).zfill(2)}-{str(year)[-2:]}"
            course = min(6, (date.today().year - year) + 1)
            cursor.execute("""
                INSERT INTO groups (name, course, kafedra_id) 
                VALUES (%s, %s, %s) RETURNING id
            """, (group_name, course, kaf_id))
            group_id = cursor.fetchone()[0]
            group_data.append((group_id, group_name, course, kaf_id))
            
            # Добавляем в Neo4j
            
            with neo4j_driver.session() as session:
                session.run("""
                    CREATE (g:Group {id: $id, name: $name, course: $course})
                """, id=group_id, name=group_name,course=course,)
            '''
            WITH g
                    MATCH (k:Kafedra {id: $kaf_id})
                    CREATE (g)-[:BELONGS_TO]->(k)

                      kaf_id=kaf_id
            '''
    conn.commit()
    return group_data

def generate_lectures(course_data):
    """Генерация лекций"""
    lecture_topics = {
        "Основы программирования": ["Введение в программирование", "Переменные и типы данных", "Условные операторы", 
                                  "Циклы", "Функции", "Массивы", "Объектно-ориентированное программирование"],
        "Базы данных": ["Введение в БД", "Реляционная модель", "SQL: SELECT", "SQL: JOIN", "Нормализация", 
                       "Транзакции", "Индексы", "NoSQL"],
        "Кибербезопасность": ["Основы кибербезопасности", "Криптография", "Сетевая безопасность", 
                             "Этичный хакинг", "Защита данных", "Правовые аспекты"],
        "Искусственный интеллект": ["История ИИ", "Машинное обучение", "Нейронные сети", "Обработка естественного языка",
                                   "Компьютерное зрение", "Экспертные системы"],
        "Философия": ["Античная философия", "Средневековая философия", "Философия Нового времени", 
                     "Немецкая классическая философия", "Современная философия", "Диалоги Сократа"]
    }
    
    lecture_data = []
    for course_id, course_name, kaf_id, spec_id, hours in course_data:
        base_topic = course_name.split(' (')[0]
        topics = lecture_topics.get(base_topic, [f"Лекция {i+1} по {base_topic}" for i in range(8)])
        
        for i, topic in enumerate(random.sample(topics, min(len(topics), random.randint(5, 10)))):
            duration = random.choice([1, 2, 3])
            is_special = random.random() < 0.2
            tech_req = "Проектор, компьютер" if not is_special else "VR оборудование, 3D очки"
            
            cursor.execute("""
                INSERT INTO lectures (topic, course_id, duration_hours, is_special, tech_requirements) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (topic, course_id, duration, is_special, tech_req))
            lecture_id = cursor.fetchone()[0]
            lecture_data.append((lecture_id, topic, course_id, duration, is_special, tech_req))
            
            # Добавляем в Elasticsearch (пример для некоторых лекций)
            
            #if random.random() < 0.3:
            desc = fake.paragraph(nb_sentences=5)
            es.index(index="lectures", id=lecture_id, body={
                #"id": lecture_id,
                "name": topic,
                "description": desc,
                #"lecture_id": lecture_id
            })
            
            # Добавляем в Neo4j
            with neo4j_driver.session() as session:
                session.run("""
                    CREATE (l:Lecture {id: $id, topic: $topic, duration_hours: $duration, 
                            is_special: $is_special, tech_requirements: $tech_req})
                    WITH l
                    MATCH (k:Kafedra {id: $kaf_id})
                    CREATE (l)-[:ORIGINATES_FROM]->(k)
                """, id=lecture_id, topic=topic, duration=duration, 
                  is_special=is_special, tech_req=tech_req, kaf_id=kaf_id)
    
    conn.commit()
    return lecture_data

def generate_lecture_materials(lecture_data):
    """Генерация материалов лекций"""
    material_types = [
        ("Презентация", "Слайды лекции в формате PowerPoint"),
        ("Конспект", "Текстовый конспект лекции"),
        ("Видеозапись", "Запись лекции"),
        ("Практическое задание", "Домашнее задание по теме лекции"),
        ("Тест", "Контрольные вопросы по теме"),
        ("Дополнительные материалы", "Рекомендуемая литература")
    ]
    
    for lecture_id, topic, course_id, duration, is_special, tech_req in lecture_data:
        for i in range(random.randint(1, 4)):
            mat_type, mat_desc = random.choice(material_types)
            mat_name = f"{mat_type} по '{topic}'"
            cursor.execute("""
                INSERT INTO lecture_materials (name, description, lecture_id) 
                VALUES (%s, %s, %s)
            """, (mat_name, mat_desc, lecture_id))
    
    conn.commit()

'''
def generate_students(group_data):
    """Генерация студентов"""
    student_data = []
    for group_id, group_name, course, kaf_id in group_data:
        for i in range(random.randint(15, 30)):
            full_name = fake.name()
            year = int(group_name.split('-')[-1])
            record = f"{year}{random.choice(['B', 'M', 'A'])}{str(random.randint(1000, 9999))}"
            
            cursor.execute("""
                INSERT INTO students (full_name, student_record, group_id) 
                VALUES (%s, %s, %s) RETURNING id
            """, (full_name, record, group_id))
            student_id = cursor.fetchone()[0]
            student_data.append((student_id, full_name, record, group_id))
'''

def generate_students(group_data):
    """Генерация студентов"""
    student_data = []
    existing_records = set()  # Множество для хранения уникальных student_record

    for group_id, group_name, course, kaf_id in group_data:
        for i in range(random.randint(15, 30)):
            full_name = fake.name()
            year = int(group_name.split('-')[-1])
            record = f"{year}{random.choice(['B', 'M', 'A'])}{str(random.randint(1000, 9999))}"

            # Генерация уникального student_record
            while record in existing_records:
                record = f"{year}{random.choice(['B', 'M', 'A'])}{str(random.randint(1000, 9999))}"

            existing_records.add(record)  # Добавляем в множество

            cursor.execute("""
                INSERT INTO students (full_name, student_record, group_id) 
                VALUES (%s, %s, %s) RETURNING id
            """, (full_name, record, group_id))
            student_id = cursor.fetchone()[0]
            student_data.append((student_id, full_name, record, group_id))
            
            # Добавляем в Redis
            r.set(f"student:{student_id}", json.dumps({
                "id": student_id,
                "full_name": full_name,
                "student_record": record,
                "group_id": group_id
            }))
            
            # Добавляем в Neo4j
            with neo4j_driver.session() as session:
                session.run("""
                    CREATE (s:Student {id: $id, full_name: $name, student_record: $record})
                    WITH s
                    MATCH (g:Group {id: $group_id})
                    CREATE (s)-[:BELONGS_TO]->(g)
                """, id=student_id, name=full_name, record=record, group_id=group_id)
    
    conn.commit()
    return student_data

def generate_schedule(group_data, lecture_data):
    """Генерация расписания"""
    schedule_data = []
    auditoriums = [f"{b}-{r}{n}" for b in ["A", "B", "C"] for r in range(1, 5) for n in range(1, 21)]
    
    # Создаем расписание для каждой группы
    for group_id, group_name, course, kaf_id in group_data:
        # Берем только лекции для кафедры этой группы
        group_lectures = [l for l in lecture_data if l[2] == kaf_id]
        
        if not group_lectures:
            continue
            
        # Создаем расписание на 16 недель (семестр)
        for week in range(1, 17):
            # 2-3 пары в неделю
            for day in random.sample(range(1, 7), random.randint(2, 3)):
                lecture_id, topic, course_id, duration, is_special, tech_req = random.choice(group_lectures)
                auditorium = random.choice(auditoriums)
                seats = random.randint(20, 30)
                
                cursor.execute("""
                    INSERT INTO schedule (auditorium, group_id, lecture_id, seats) 
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (auditorium, group_id, lecture_id, seats))
                schedule_id = cursor.fetchone()[0]
                schedule_data.append((schedule_id, auditorium, group_id, lecture_id, seats))
                
                # Добавляем связь в Neo4j
                with neo4j_driver.session() as session:
                    session.run("""
                        MATCH (g:Group {id: $group_id}), (l:Lecture {id: $lecture_id})
                        CREATE (g)-[:HAS_SCHEDULE]->(l)
                    """, group_id=group_id, lecture_id=lecture_id)
    
    conn.commit()
    return schedule_data

def generate_attendance(student_data, schedule_data):
    """Генерация посещаемости"""
    # Для каждой записи в расписании создаем посещаемость для студентов группы
    for schedule_id, auditorium, group_id, lecture_id, seats in schedule_data:
        # Находим студентов группы
        group_students = [s for s in student_data if s[3] == group_id]
        
        if not group_students:
            continue
            
        # Дата начала недели (произвольная в текущем семестре)
        week_start = date(2023, 9, 1) + timedelta(weeks=random.randint(0, 15))
        
        for student_id, full_name, record, group_id in random.sample(
            group_students, random.randint(len(group_students) // 2, len(group_students))):
            
            status = random.choice(['present', 'absent', 'late'])
            cursor.execute("""
                INSERT INTO attendance (student_id, schedule_id, week_start, status) 
                VALUES (%s, %s, %s, %s::attendance_status)
            """, (student_id, schedule_id, week_start, status))
    
    conn.commit()

def main():
    print("Начало генерации данных...")
    start_time = time.time()
    
    # Создаем таблицы
    create_tables()
    
    # Генерируем данные
    uni_count = generate_universities()
    institute_data = generate_institutes(uni_count)
    kafedra_data = generate_kafedras(institute_data)
    speciality_data = generate_specialities(kafedra_data)
    course_data = generate_lecture_courses(kafedra_data, speciality_data)
    group_data = generate_groups(kafedra_data)
    lecture_data = generate_lectures(course_data)
    generate_lecture_materials(lecture_data)
    student_data = generate_students(group_data)
    schedule_data = generate_schedule(group_data, lecture_data)
    generate_attendance(student_data, schedule_data)
    
    # Общее количество записей
    total_records = sum([
        uni_count,
        len(institute_data),
        len(kafedra_data),
        len(speciality_data),
        len(course_data),
        len(group_data),
        len(lecture_data),
        len(student_data),
        len(schedule_data)
    ])
    
    print(f"Генерация данных завершена. Всего создано ~{total_records} записей.")
    print(f"Время выполнения: {time.time() - start_time:.2f} секунд")

if __name__ == "__main__":
    main()