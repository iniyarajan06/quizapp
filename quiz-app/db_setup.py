import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    db_url = os.getenv('DB_URL')
    conn = psycopg2.connect(db_url)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            regno TEXT NOT NULL,
            correct INTEGER,
            points INTEGER,
            avg_time REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER REFERENCES participants(id),
            question_id INTEGER,
            answer INTEGER,
            time_taken REAL
        )
    ''')
    
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("PostgreSQL database initialized.")
