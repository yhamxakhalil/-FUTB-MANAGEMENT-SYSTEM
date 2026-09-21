import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "result_checker.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            matric_no TEXT UNIQUE NOT NULL,
            level INTEGER NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            units INTEGER NOT NULL,
            level INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            semester TEXT NOT NULL,
            ca_score REAL NOT NULL,
            exam_score REAL NOT NULL,
            total_score REAL NOT NULL,
            grade TEXT NOT NULL,
            grade_point REAL NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
            UNIQUE (student_id, course_id, semester)
        )
    """)

    conn.commit()
    conn.close()


def grade_from_total(total):
    if total >= 70:
        return "A", 5.0
    elif total >= 60:
        return "B", 4.0
    elif total >= 50:
        return "C", 3.0
    elif total >= 45:
        return "D", 2.0
    elif total >= 40:
        return "E", 1.0
    else:
        return "F", 0.0
