import os
import sqlite3
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# === Database setup ===
DB_PATH = os.path.join(os.path.dirname(__file__), "quiz.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
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

init_db()

# === Flask app ===
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  # allow cross-origin requests

# === File paths ===
DATA_DIR = Path(app.static_folder) / "data"
DATA_DIR.mkdir(exist_ok=True)

REG_FILE = DATA_DIR / "registrations.xlsx"
RESULTS_FILE = DATA_DIR / "quiz_results.xlsx"
LEADERBOARD_FILE = DATA_DIR / "leaderboard.xlsx"
QUESTIONS_FILE = Path(__file__).parent / "questions.json"

# === Initialize Excel files if missing ===
if not REG_FILE.exists():
    pd.DataFrame(columns=["timestamp", "name", "regno", "college", "department", "year"]).to_excel(REG_FILE, index=False)

if not RESULTS_FILE.exists():
    pd.DataFrame(columns=["timestamp", "name", "regno", "score", "total", "answers"]).to_excel(RESULTS_FILE, index=False)

if not LEADERBOARD_FILE.exists():
    pd.DataFrame(columns=["name", "regno", "correct_answers", "points", "avg_time_sec", "timestamp"]).to_excel(LEADERBOARD_FILE, index=False)

# === Routes ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        name = data.get("name", "").strip()
        regno = data.get("regno", "").strip()
        college = data.get("college", "").strip()
        department = data.get("department", "").strip()
        year = data.get("year", "").strip()

        if not (name and regno and college and department and year):
            return jsonify({"success": False, "message": "Missing fields"}), 400

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save to Excel
        df = pd.read_excel(REG_FILE)
        df.loc[len(df)] = [timestamp, name, regno, college, department, year]
        df.to_excel(REG_FILE, index=False)

        # Save to SQLite
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO participants (name, regno, correct, points, avg_time) VALUES (?, ?, ?, ?, ?)",
            (name, regno, 0, 0, 0.0)
        )
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Registration successful"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/questions")
def get_questions():
    if QUESTIONS_FILE.exists():
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            qs = json.load(f)
        safe = [{"id": i, "question": q["question"], "options": q["options"]} for i, q in enumerate(qs)]
        return jsonify(safe)
    return jsonify([])

@app.route("/submit-quiz", methods=["POST"])
def submit_quiz():
    payload = request.get_json()
    if not payload:
        return jsonify({"success": False, "message": "No data"}), 400

    name = payload.get("name", "")
    regno = payload.get("regno", "")
    answers = payload.get("answers", [])

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    correct = 0
    total_time = 0
    time_counts = 0

    for i, ans in enumerate(answers):
        qid = ans.get("qId", i)
        selected = ans.get("selected", None)
        time_sec = ans.get("time_sec", None)
        if time_sec is not None:
            total_time += time_sec
            time_counts += 1
        if selected is not None and qid < len(questions):
            if selected == questions[qid].get("answer"):
                correct += 1

    points = correct * 2
    avg_time = (total_time / time_counts) if time_counts else 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save to SQLite
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO participants (name, regno, correct, points, avg_time) VALUES (?, ?, ?, ?, ?)",
        (name, regno, correct, points, avg_time)
    )
    participant_id = cur.lastrowid
    for ans in answers:
        cur.execute(
            "INSERT INTO answers (participant_id, question_id, answer, time_taken) VALUES (?, ?, ?, ?)",
            (participant_id, ans.get("qId"), ans.get("selected"), ans.get("time_sec"))
        )
    conn.commit()
    conn.close()

    # After quiz submission, redirect to leaderboard page
    return jsonify({"success": True, "redirect": "/leaderboard"})

@app.route("/leaderboard")
def leaderboard():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT name, regno, correct, points, avg_time
        FROM participants
        ORDER BY points DESC, avg_time ASC
        LIMIT 20
    """)
    rows = cur.fetchall()
    leaderboard_data = [
        {
            "rank": idx + 1,
            "name": row[0],
            "regno": row[1],
            "correct": row[2],
            "points": row[3],
            "avg_time": round(row[4], 2) if row[4] is not None else ""
        }
        for idx, row in enumerate(rows)
    ]
    conn.close()
    return render_template("leaderboard.html", leaderboard=leaderboard_data)

@app.route("/download/registrations")
def download_regs():
    if REG_FILE.exists():
        return send_file(REG_FILE, as_attachment=True)
    return "No file", 404

if __name__ == "__main__":
    app.run(debug=True)
