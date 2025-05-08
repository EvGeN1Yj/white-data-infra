-- 1. Университеты (верхний уровень)
CREATE TABLE universities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(200)
);

-- 2. Институты (в составе университетов)
CREATE TABLE institutes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    university_id INTEGER REFERENCES universities(id)
);

-- 3. Кафедры 
CREATE TABLE kafedra (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    institute_id INTEGER REFERENCES institutes(id)
);

-- 4. Специальности
CREATE TABLE specialities (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    kafedra_id INTEGER REFERENCES kafedra(id)
);

-- 5. Курсы лекций
CREATE TABLE lectures_course (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    kafedra_id INTEGER REFERENCES kafedra(id),  -- Исправленная связь
    speciality_id INTEGER REFERENCES specialities(id),
    planned_hours INTEGER
);

-- 6. Группы (обновленная связь)
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    course INTEGER CHECK (course BETWEEN 1 AND 6),
    kafedra_id INTEGER REFERENCES kafedra(id)  -- Исправленная связь
);

-- 7. Лекции (без изменений)
CREATE TABLE lectures (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    course_id INTEGER REFERENCES lectures_course(id),
    duration_hours INTEGER,
    is_special BOOLEAN DEFAULT FALSE,
    tech_requirements TEXT
);

-- 8. Материалы лекций (без изменений)
CREATE TABLE lecture_materials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    lecture_id INTEGER REFERENCES lectures(id)
);

-- 9. Студенты
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    student_record VARCHAR(50) UNIQUE,  
    group_id INTEGER REFERENCES groups(id)
);

-- 10. Расписание
CREATE TABLE schedule (
    id SERIAL PRIMARY KEY,
    auditorium VARCHAR(50) NOT NULL,
    group_id INTEGER REFERENCES groups(id),
    lecture_id INTEGER REFERENCES lectures(id),
    seats INTEGER
);

-- 11. Посещаемость (с ENUM типом)
CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'late');

CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id),
    schedule_id INTEGER REFERENCES schedule(id),
    week_start DATE NOT NULL,
    status attendance_status  -- Использование ENUM типа
);
