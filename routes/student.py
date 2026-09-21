from functools import wraps

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from routes.results import build_transcript

student_bp = Blueprint("student", __name__, url_prefix="/student")


def student_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student():
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


@student_bp.route("/results")
@login_required
@student_required
def my_results():
    """A student's own released results, GPA per semester, and CGPA."""
    student = current_user.student
    if student is None:
        abort(404)
    semesters_summary, cgpa = build_transcript(student)
    return render_template(
        "transcript.html",
        student=student,
        semesters_summary=semesters_summary,
        cgpa=cgpa,
    )
