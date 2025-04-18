import json
from flask import Blueprint, abort, jsonify, Response, request, send_file
from models import Student, StudentAnswer, TestSummary, StudentFeedback
from collections import Counter
from io import BytesIO
import pandas as pd

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/students", methods=["GET"])
def get_all_students():
    token = request.args.get("token")
    if token != "AdaptiveLearningBC":
        abort(401)

    students = Student.query.all()
    result = []

    def compute_stats(answers):
        total = len(answers)
        correct = sum(1 for a in answers if a.is_correct)
        rate = round((correct / total * 100), 1) if total > 0 else 0
        return total, correct, rate

    def category_stats(answers):
        stats = {}
        for a in answers:
            if not a.category:
                continue
            if a.category not in stats:
                stats[a.category] = {"total": 0, "correct": 0}
            stats[a.category]["total"] += 1
            if a.is_correct:
                stats[a.category]["correct"] += 1

        success = {}
        counts = {}
        weak = []

        for cat, val in stats.items():
            rate = val["correct"] / val["total"]
            success[cat] = round(rate * 100, 1)
            counts[cat] = val["total"]
            if rate < 0.6:
                weak.append(cat)

        return success, counts, weak, list(stats.keys())

    for s in students:
        predtest_answers = StudentAnswer.query.filter_by(student_id=s.id, test_type="predtest").all()
        pred_total, pred_correct, pred_rate = compute_stats(predtest_answers)
        pred_success, pred_counts, pred_weak, pred_used = category_stats(predtest_answers)

        # --- Hlavné testy (zo sumarizačnej tabuľky) ---
        summaries = TestSummary.query.filter_by(student_id=s.id, test_type="main").all()
        sessions = {}
        for summary in summaries:
            if summary.test_session not in sessions:
                sessions[summary.test_session] = {
                    "test_session": summary.test_session,
                    "total_answers": 0,
                    "correct_answers": 0,
                    "category_success": {},
                    "categories": {}
                }
            session = sessions[summary.test_session]
            session["total_answers"] += summary.total_answers
            session["correct_answers"] += summary.correct_answers
            session["category_success"][summary.category] = f"{summary.accuracy * 100:.1f}%"
            session["categories"][summary.category] = summary.total_answers

        session_results = list(sessions.values())

        result.append({
            "id": s.id,
            "name": s.name,
            "login": s.login,

            "predtest": {
                "total_answers": pred_total,
                "correct_answers": pred_correct,
                "success_rate": f"{pred_rate:.1f}%" if pred_total > 0 else "N/A",
                "category_success": pred_success,
                "weak_categories": pred_weak,
                "categories": pred_counts if pred_used else ["Žiadne odpovede"]
            },

            "main_tests": session_results 
        })

    return Response(
        json.dumps(result, ensure_ascii=False, indent=2),
        mimetype='application/json'
    )

@admin_bp.route("/feedback", methods=["GET"])
def export_feedback():
    token = request.args.get("token")
    if token != "AdaptiveLearningBC":
        abort(401)
        
    feedbacks = StudentFeedback.query.all()

    data = [{
        "student_id": f.student_id,
        "gender": f.gender,
        "age": f.age,
        "experience": f.experience,
        "field_of_study": f.field_of_study,
        "understand_questions": f.understand_questions,
        "easy_navigation": f.easy_navigation,
        "motivation_level": f.motivation_level,
        "helpful_feedback": f.helpful_feedback,
        "overall_usefulness": f.overall_usefulness,
        "difficulty_match": f.difficulty_match,
        "improved_skills": f.improved_skills,
        "time_spent": f.time_spent,
        "future_interest": f.future_interest,
        "ui_satisfaction": f.ui_satisfaction,
        "improvement_suggestion": f.improvement_suggestion
    } for f in feedbacks]

    df = pd.DataFrame(data)
    excel_stream = BytesIO()
    df.to_excel(excel_stream, index=False, sheet_name="Feedback")
    excel_stream.seek(0)

    return send_file(
        excel_stream,
        download_name="student_feedback.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@admin_bp.route("/feedback/summary", methods=["GET"])
def feedback_summary():
    token = request.args.get("token")
    if token != "AdaptiveLearningBC":
        abort(401)

    feedbacks = StudentFeedback.query.all()
    total = len(feedbacks)

    if total == 0:
        return jsonify({"error": "Žiadne odpovede ešte neboli zaznamenané."}), 404

    fields_to_summarize = [
        "gender",
        "experience",
        "understand_questions",
        "easy_navigation",
        "motivation_level",
        "helpful_feedback",
        "overall_usefulness",
        "difficulty_match",
        "improved_skills",
        "time_spent",
        "future_interest",
        "ui_satisfaction"
    ]

    summary = {}
    for field in fields_to_summarize:
        counter = Counter(getattr(f, field) for f in feedbacks)
        summary[field] = {
            k: round(v / total * 100, 1) for k, v in counter.items()
        }

    result_dict = {
        "summary": summary,
        "total_responses": total
    }

    return Response(
        json.dumps(result_dict, ensure_ascii=False, indent=2),
        mimetype="application/json"
    )