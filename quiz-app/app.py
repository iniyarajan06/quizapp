import os
import psycopg2
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    db_url = os.getenv('DB_URL')
    conn = psycopg2.connect(db_url)
    return conn


app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  

 
QUESTIONS_FILE = Path(__file__).parent / "questions.json"

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

        # Save to DB only (Excel storage removed)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO participants (name, regno, correct, points, avg_time) VALUES (%s, %s, %s, %s, %s)",
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

    # Save to SQLite
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO participants (name, regno, correct, points, avg_time) VALUES (%s, %s, %s, %s, %s)",
        (name, regno, correct, points, avg_time)
    )
    participant_id = cur.lastrowid+1
    for ans in answers:
        cur.execute(
            "INSERT INTO answers (participant_id, question_id, answer, time_taken) VALUES (%s, %s, %s, %s)",
            (participant_id, ans.get("qId"), ans.get("selected"), ans.get("time_sec"))
        )
    conn.commit()
    conn.close()


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
            "name": row[0],
            "regno": row[1],
            "correct": row[2],
            "points": row[3],
            "avg_time": round(row[4], 2) if row[4] is not None else ""
        }
        for row in rows
    ]
    print(leaderboard_data)
    conn.close()
    return render_template("leaderboard.html", board=leaderboard_data)

# New: JSON API for leaderboard, used by the SPA
@app.route("/api/leaderboard")
def leaderboard_api():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, regno, correct, points, avg_time
            FROM participants
            ORDER BY points DESC, avg_time ASC
            LIMIT 20
            """
        )
        rows = cur.fetchall()
        data = []
        for row in rows:
            avg = None
            if row[4] is not None:
                try:
                    avg = round(float(row[4]), 2)
                except Exception:
                    avg = None
            data.append({
                "name": row[0],
                "regno": row[1],
                "correct": row[2],
                "points": row[3],
                "avg_time": avg,
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    app.run(debug=True)
