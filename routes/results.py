from functools import wraps

from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user

from models import Student, Result

results_bp = Blueprint("results_view", __name__, url_prefix="/results")


def staff_required(view_func):
    """Search is for the Exam Officer and lecturers; students use their own page."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.is_student():
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


def build_transcript(student):
    """Group a student's released results by session/semester and compute GPA/CGPA."""
    released_results = (
        Result.query.filter_by(student_id=student.id, status=Result.STATUS_RELEASED)
        .join(Result.course)
        .order_by(Result.academic_session_id, Result.semester_id)
        .all()
    )

    grouped = {}
    for r in released_results:
        key = (r.academic_session.name, r.semester.name)
        grouped.setdefault(key, []).append(r)

    semesters_summary = []
    cumulative_units = 0
    cumulative_quality_points = 0

    for (session_name, semester_name), rows in grouped.items():
        units = sum(r.course.credit_unit for r in rows)
        quality_points = sum(r.quality_point or 0 for r in rows)
        gpa = round(quality_points / units, 2) if units else 0

        cumulative_units += units
        cumulative_quality_points += quality_points

        semesters_summary.append({
            "session": session_name,
            "semester": semester_name,
            "rows": rows,
            "total_units": units,
            "total_quality_points": round(quality_points, 2),
            "gpa": gpa,
        })

    cgpa = round(cumulative_quality_points / cumulative_units, 2) if cumulative_units else 0

    return semesters_summary, cgpa


@results_bp.route("/search", methods=["GET", "POST"])
@login_required
@staff_required
def search():
    student = None
    semesters_summary = []
    cgpa = 0
    searched = False

    if request.method == "POST":
        reg_number = request.form.get("reg_number", "").strip()
        searched = True
        student = Student.query.filter_by(reg_number=reg_number).first()
        if student:
            semesters_summary, cgpa = build_transcript(student)

    return render_template(
        "result_search.html",
        student=student,
        semesters_summary=semesters_summary,
        cgpa=cgpa,
        searched=searched,
    )


@results_bp.route("/transcript/<int:student_id>")
@login_required
def transcript(student_id):
    student = Student.query.get_or_404(student_id)

    # A student may only ever open their own transcript.
    if current_user.is_student():
        own = current_user.student
        if own is None or own.id != student.id:
            abort(403)

    semesters_summary, cgpa = build_transcript(student)
    return render_template(
        "transcript.html",
        student=student,
        semesters_summary=semesters_summary,
        cgpa=cgpa,
    )
