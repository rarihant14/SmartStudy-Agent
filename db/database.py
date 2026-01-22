import sqlite3

DB_NAME = "studyplanner.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
CREATE TABLE IF NOT EXISTS syllabus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    content TEXT
)
""")


    cur.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT,
        topic TEXT,
        study_date TEXT,
        hours REAL,
        status TEXT DEFAULT 'pending'
    )
    """)

    conn.commit()
    conn.close()
