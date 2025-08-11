import sqlite3

def init_db():
    conn = sqlite3.connect('quiz.db')
    c = conn.cursor()
    # Participants table
    c.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            regno TEXT NOT NULL,
            correct INTEGER,
            points INTEGER,
            avg_time REAL
        )
    ''')
    # Answers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id INTEGER,
            question_id INTEGER,
            answer INTEGER,
            time_taken REAL,
            FOREIGN KEY(participant_id) REFERENCES participants(id)
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
