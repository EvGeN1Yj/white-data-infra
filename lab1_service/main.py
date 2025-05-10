from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import logging
from datetime import date
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
import redis
import json

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


# Настройки аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # В реальном приложении здесь должна быть проверка токена
    # Для примера просто возвращаем тестового пользователя
    return User(username="testuser")


# Подключение к Elasticsearch
es = Elasticsearch('http://elasticsearch:9200')

#Postgres
pg_conn = psycopg2.connect(host="postgres", port="5432", database="university_db", user="user", password="password")

# Redis
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# NEO4j
neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))

@app.get("/reports/low_attendance/", response_model=List)
async def get_low_attendance_report(
    search_term: str,
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user)
):

    try:
        query = {
            "query": {
                "match": {
                    "description": search_term
                }
            }
        }
        # Выполнение запроса
        response = es.search(index="lecture_materials",body=query)
        # Сбор id из результатов
        ids = [int(hit["_id"]) for hit in response["hits"]["hits"]]
        #######################################################################
        query = """
            MATCH (gr:Group)-[h:HAS_SCHEDULE]->(lec:Lecture)
            WHERE date(h.attendance_date) >= date($start_date) 
              AND date(h.attendance_date) <= date($end_date)
            RETURN lec.id
            ORDER BY h.attendance_date
            """

        with neo4j_driver.session() as session:
            result = session.run(query, start_date=start_date, end_date=end_date)
            neo_ids=[int(x[0]) for x in result]
        #########################################################################
        common_elements = [value for value in ids if value in neo_ids]
        if len(common_elements)<1:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
            return 'no lections'
        # SQL-запрос для получения данных
        query = f"""
            SELECT 
                l.topic,
                s.id AS student_id,
                COUNT(CASE WHEN a.status = 'presence' THEN 1 END) * 100.0 / COUNT(a.id) AS percents
            FROM 
                lectures l
            JOIN 
                schedule sch ON l.id = sch.lecture_id
            JOIN 
                attendance a ON sch.id = a.schedule_id
            JOIN 
                students s ON a.student_id = s.id
            WHERE 
                l.id IN ({ ''.join(map(str, common_elements))})
            GROUP BY 
                l.topic, s.id
            ORDER BY 
                percents ASC
            LIMIT 10;
            """

        # Создание курсора и выполнение запроса
        cursor = pg_conn.cursor()
        cursor.execute(query)

        # Получение всех строк результата
        rows = cursor.fetchall()

        # Формирование ответа в формате JSON
        response = []
        for row in rows:
            topic = row[0]
            student_id = row[1]
            percents = row[2]

            # Получение информации о студенте из Redis
            student_info = redis_client.get(
                f'student:{student_id}')  # Предполагается, что данные хранятся по ключу 'student:{id}'

            # Если информация о студенте найдена, добавляем её в ответ
            if student_info:
                student_info = json.loads(student_info)  # Преобразуем строку JSON в словарь
                response.append({
                    'topic': topic,
                    'student_id': student_id,
                    'percents': percents,
                    'student_info': student_info,
                    'start_date': start_date,
                    'end_date': end_date,
                    'termin':search_term
                })

        return response


    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Service error")
    finally:
        cursor.close()
