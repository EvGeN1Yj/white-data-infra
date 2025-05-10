
CREATE TABLE IF NOT EXISTS universities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(200)
);


CREATE TABLE IF NOT EXISTS institutes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    university_id INT NOT NULL,
    FOREIGN KEY (university_id) REFERENCES universities(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    institute_id INT NOT NULL,
    FOREIGN KEY (institute_id) REFERENCES institutes(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS specialties (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS lecture_course (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    department_id INT NOT NULL,
    specialty_id INT NOT NULL,
    planned_hours INT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
    FOREIGN KEY (specialty_id) REFERENCES specialties(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS lectures (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    course_id INT NOT NULL,
    duration_hours INT NOT NULL DEFAULT 2 CHECK (duration_hours=2),
    is_special BOOLEAN NOT NULL DEFAULT TRUE,
    tech_requirements TEXT,    
    FOREIGN KEY (course_id) REFERENCES lecture_course(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lecture_materials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    lecture_id INT NOT NULL,
    FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    course INT CHECK (course BETWEEN 1 AND 6),
    department_id INT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(200) NOT NULL,
    student_record VARCHAR(50) NOT NULL,
    group_id INT NOT NULL,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS schedule (
    id SERIAL PRIMARY KEY,
    auditorium VARCHAR(50),
    group_id INT NOT NULL,
    lecture_id INT NOT NULL,
    capacity INT NOT NULL,  
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL,
    student_id INT NOT NULL,
    schedule_id INT NOT NULL,
    attendance_date TIMESTAMP NOT NULL,  
    week_start DATE NOT NULL,    
    status VARCHAR(10) CHECK (status IN ('presence','absence','late')) NOT NULL,
    PRIMARY KEY (id, week_start),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (schedule_id) REFERENCES schedule(id) ON DELETE CASCADE
)
PARTITION BY RANGE (week_start);



