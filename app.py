import os
import json
from datetime import date
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from db.database import init_db, get_connection
from rag.pdf_reader import extract_text_from_pdf
from rag.chroma_store import index_syllabus_to_chroma, rag_search
from graph.study_graph import study_graph
from llm import get_llm
from chat_prompt import get_chat_prompt

app = Flask(__name__)
init_db()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def home():
    return render_template("index.html")


#Upload syllabus PDF and index into ChromaDB
@app.route("/upload-syllabus", methods=["POST"])
def upload_syllabus():
    if "pdf" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)

    text = extract_text_from_pdf(path)
    if not text:
        return jsonify({"error": "PDF text extraction failed"}), 400

    #save syllabus to SQLite
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO syllabus(filename, content) VALUES (?, ?)", (filename, text))
    conn.commit()
    conn.close()

    #index into Chroma
    chunks_count = index_syllabus_to_chroma(text, filename)

    return jsonify({
        "message": "✅ PDF uploaded, syllabus extracted & indexed in ChromaDB!",
        "filename": filename,
        "chunks_indexed": chunks_count
    })


#Generate plan using syllabus
@app.route("/generate-plan", methods=["POST"])
def generate_plan():
    data = request.json

    subjects = data["subjects"]
    exam_date = data["exam_date"]
    hours_per_day = float(data["hours_per_day"])

    #clear old plans before regenerating
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM plans")
    conn.commit()
    conn.close()

    state = {
        "subjects": subjects,
        "exam_date": exam_date,
        "hours_per_day": hours_per_day,
        "plan": []
    }

    result = study_graph.invoke(state)
    plan = result["plan"]

    #save in DB
    conn = get_connection()
    cur = conn.cursor()

    for item in plan:
        cur.execute("""
        INSERT INTO plans(subject, topic, study_date, hours, status)
        VALUES (?, ?, ?, ?, ?)
        """, (item["subject"], item["topic"], item["date"], item["hours"], "pending"))

    conn.commit()
    conn.close()

    return jsonify({"message": "✅ Plan generated from syllabus (RAG)!", "plan": plan})


@app.route("/plans", methods=["GET"])
def get_plans():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, subject, topic, study_date, hours, status
        FROM plans
        ORDER BY study_date ASC
    """)
    rows = cur.fetchall()
    conn.close()

    plans = [
        {"id": r[0], "subject": r[1], "topic": r[2], "date": r[3], "hours": r[4], "status": r[5]}
        for r in rows
    ]
    return jsonify(plans)


@app.route("/mark-done/<int:plan_id>", methods=["POST"])
def mark_done(plan_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE plans SET status='done' WHERE id=?", (plan_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "✅ Marked done!"})


#  DELETE SINGLE 
@app.route("/delete-plan/<int:plan_id>", methods=["POST"])
def delete_plan(plan_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM plans WHERE id=?", (plan_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "🗑️ Task deleted successfully!"})


#  DELETE ALL 
@app.route("/delete-all-plans", methods=["POST"])
def delete_all_plans():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM plans")
    conn.commit()
    conn.close()
    return jsonify({"message": "🗑️ All plans deleted successfully!"})


#  Suggest next topic to study
@app.route("/what-should-i-study", methods=["GET"])
def what_should_i_study():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, subject, topic, study_date, hours
        FROM plans
        WHERE status='pending'
        ORDER BY study_date ASC
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({
            "message": "✅ No pending tasks found! You can revise or take a mock test 😄",
            "task": None
        })

    task = {
        "id": row[0],
        "subject": row[1],
        "topic": row[2],
        "date": row[3],
        "hours": row[4]
    }

    return jsonify({
        "message": "🎯 You should work on this topic now:",
        "task": task
    })


#  Daily Goal 
@app.route("/daily-goals", methods=["GET"])
def daily_goals():
    today = date.today().isoformat()

    conn = get_connection()
    cur = conn.cursor()

    #tasks scheduled 
    cur.execute("""
        SELECT id, subject, topic, study_date, hours, status
        FROM plans
        WHERE status='pending' AND study_date=?
        ORDER BY id ASC
        LIMIT 3
    """, (today,))
    rows = cur.fetchall()

    #fill remaining from upcoming pending tasks
    if len(rows) < 3:
        remaining = 3 - len(rows)
        cur.execute("""
            SELECT id, subject, topic, study_date, hours, status
            FROM plans
            WHERE status='pending' AND study_date!=?
            ORDER BY study_date ASC
            LIMIT ?
        """, (today, remaining))
        rows += cur.fetchall()

    conn.close()

    goals = [
        {
            "id": r[0],
            "subject": r[1],
            "topic": r[2],
            "date": r[3],
            "hours": r[4],
            "status": r[5]
        }
        for r in rows
    ]

    return jsonify({
        "message": "🎯 Daily Goal Mode: Complete these 3 topics today ✅",
        "today": today,
        "goals": goals
    })


# RAG Chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_question = data.get("message", "").strip()
    if not user_question:
        return jsonify({"reply": "Please type a question ✅"})

    #  fetch plan
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT subject, topic, study_date, hours, status FROM plans ORDER BY study_date ASC LIMIT 300")
    plan_rows = cur.fetchall()

    plan_json = [
        {"subject": r[0], "topic": r[1], "date": r[2], "hours": r[3], "status": r[4]}
        for r in plan_rows
    ]

    #  RAG search
    retrieved = rag_search(user_question, top_k=5)
    rag_context = "\n\n".join(
        [f"[Chunk {i+1}] {r['text']}" for i, r in enumerate(retrieved)]
    ) if retrieved else "No syllabus context found."

    conn.close()

    llm = get_llm()
    prompt = get_chat_prompt(
        user_question=user_question,
        saved_plan_json=json.dumps(plan_json),
        rag_context=rag_context
    )

    reply = llm.invoke(prompt).content
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)
