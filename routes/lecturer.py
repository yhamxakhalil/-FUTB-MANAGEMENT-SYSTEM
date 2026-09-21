from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from models import db, Student, Course, CourseAssignment, Result, AcademicSession
from validators import validate_scores, MAX_CA_SCORE, MAX_EXAM_SCORE

lecturer_bp = Blueprint("lecturer", __name__, url_prefix="/lecturer")


def lecturer_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_lecturer():
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


def current_session():
    return AcademicSession.query.filter_by(is_current=True).first() or AcademicSession.query.first()


def get_lecturer_or_404():
    lecturer = current_user.lecturer
    if lecturer is None:
        abort(404)
    return lecturer


@lecturer_bp.route("/dashboard")
@login_required
@lecturer_required
def dashboard():
    lecturer = get_lecturer_or_404()
    session_obj = current_session()
    assignments = CourseAssignment.query.filter_by(
        lecturer_id=lecturer.id, academic_session_id=session_obj.id
    ).all()
    course_ids = [a.course_id for a in assignments]

    student_count = 0
    if course_ids:
        levels = {c.level for c in Course.query.filter(Course.id.in_(course_ids)).all()}
        student_count = Student.query.filter(Student.level.in_(levels)).count() if levels else 0

    draft_count = Result.query.filter_by(lecturer_id=lecturer.id, status=Result.STATUS_DRAFT).count()
    submitted_count = Result.query.filter_by(lecturer_id=lecturer.id, status=Result.STATUS_SUBMITTED).count()
    released_count = Result.query.filter_by(lecturer_id=lecturer.id, status=Result.STATUS_RELEASED).count()

    return render_template(
        "lecturer_dashboard.html",
        lecturer=lecturer,
        assignments=assignments,
        student_count=student_count,
        draft_count=draft_count,
        submitted_count=submitted_count,
        released_count=released_count,
    )


@lecturer_bp.route("/courses")
@login_required
@lecturer_required
def courses():
    lecturer = get_lecturer_or_404()
    session_obj = current_session()
    assignments = CourseAssignment.query.filter_by(
        lecturer_id=lecturer.id, academic_session_id=session_obj.id
    ).all()
    return render_template("lecturer_courses.html", assignments=assignments)


def _assert_course_assigned(lecturer, course_id, session_obj):
    """A lecturer must not access courses that are not assigned to them."""
    assignment = CourseAssignment.query.filter_by(
        lecturer_id=lecturer.id, course_id=course_id, academic_session_id=session_obj.id
    ).first()
    if not assignment:
        abort(403)
    return assignment


@lecturer_bp.route("/courses/<int:course_id>/students")
@login_required
@lecturer_required
def course_students(course_id):
    lecturer = get_lecturer_or_404()
    session_obj = current_session()
    assignment = _assert_course_assigned(lecturer, course_id, session_obj)
    course = assignment.course

    students = Student.query.filter_by(level=course.level).order_by(Student.reg_number).all()

    existing_results = {
        r.student_id: r
        for r in Result.query.filter_by(
            course_id=course.id, lecturer_id=lecturer.id, academic_session_id=session_obj.id
        ).all()
    }

    return render_template(
        "lecturer_course_students.html",
        course=course,
        students=students,
        existing_results=existing_results,
    )


@lecturer_bp.route("/courses/<int:course_id>/enter/<int:student_id>", methods=["GET", "POST"])
@login_required
@lecturer_required
def enter_result(course_id, student_id):
    lecturer = get_lecturer_or_404()
    session_obj = current_session()
    assignment = _assert_course_assigned(lecturer, course_id, session_obj)
    course = assignment.course
    student = Student.query.get_or_404(student_id)

    result = Result.query.filter_by(
        student_id=student.id, course_id=course.id,
        academic_session_id=session_obj.id, semester_id=course.semester_id,
    ).first()

    if result and result.status == Result.STATUS_RELEASED:
        flash("This result has been released and can no longer be modified.", "danger")
        return redirect(url_for("lecturer.course_students", course_id=course.id))

    if request.method == "POST":
        ca_raw = request.form.get("ca_score", "")
        exam_raw = request.form.get("exam_score", "")
        action = request.form.get("action", "save")

        ca_score, exam_score, errors = validate_scores(ca_raw, exam_raw)
        if errors:
            # Nothing is saved or submitted. Show what was wrong and let the
            # lecturer correct it, keeping what they typed.
            for message in errors.values():
                flash(message, "danger")
            return render_template(
                "lecturer_enter_result.html",
                course=course, student=student, result=result,
                ca_value=ca_raw, exam_value=exam_raw, errors=errors,
                max_ca=MAX_CA_SCORE, max_exam=MAX_EXAM_SCORE,
            )

        if not result:
            result = Result(
                student_id=student.id,
                course_id=course.id,
                lecturer_id=lecturer.id,
                academic_session_id=session_obj.id,
                semester_id=course.semester_id,
                status=Result.STATUS_DRAFT,
            )
            db.session.add(result)

        result.ca_score = ca_score
        result.exam_score = exam_score
        result.compute_grade()

        if action == "submit":
            result.status = Result.STATUS_SUBMITTED
            flash("Result submitted to the Examination Officer.", "success")
        else:
            # Any manual save (including edits to a previously submitted/approved
            # result) reverts it to Draft so it must be re-submitted for review.
            result.status = Result.STATUS_DRAFT
            flash("Result saved as draft.", "info")

        db.session.commit()
        return redirect(url_for("lecturer.course_students", course_id=course.id))

    return render_template(
        "lecturer_enter_result.html",
        course=course, student=student, result=result,
        ca_value=result.ca_score if result else 0,
        exam_value=result.exam_score if result else 0,
        errors={},
        max_ca=MAX_CA_SCORE, max_exam=MAX_EXAM_SCORE,
    )


@lecturer_bp.route("/courses/<int:course_id>/submit-all", methods=["POST"])
@login_required
@lecturer_required
def submit_all(course_id):
    lecturer = get_lecturer_or_404()
    session_obj = current_session()
    assignment = _assert_course_assigned(lecturer, course_id, session_obj)
    course = assignment.course

    drafts = Result.query.filter_by(
        course_id=course.id, lecturer_id=lecturer.id,
        academic_session_id=session_obj.id, status=Result.STATUS_DRAFT,
    ).all()
    for r in drafts:
        r.status = Result.STATUS_SUBMITTED
    db.session.commit()
    flash(f"{len(drafts)} result(s) submitted for {course.code}.", "success")
    return redirect(url_for("lecturer.course_students", course_id=course.id))
