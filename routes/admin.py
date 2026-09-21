from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from models import (
    db, Student, Lecturer, Course, CourseAssignment, Result,
    AcademicSession, Semester, GradeConfig, User, create_student_account,
)
from routes.auth import MIN_PASSWORD_LENGTH

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

MAX_COURSES_PER_LECTURER = 4


def exam_officer_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_exam_officer():
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


def current_session():
    return AcademicSession.query.filter_by(is_current=True).first() or AcademicSession.query.first()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_bp.route("/dashboard")
@login_required
@exam_officer_required
def dashboard():
    total_students = Student.query.count()
    students_by_level = {
        level: Student.query.filter_by(level=level).count()
        for level in (100, 200, 300, 400)
    }
    total_courses = Course.query.count()
    total_lecturers = Lecturer.query.count()
    assigned_courses = CourseAssignment.query.count()
    submitted_results = Result.query.filter_by(status=Result.STATUS_SUBMITTED).count()
    approved_results = Result.query.filter_by(status=Result.STATUS_APPROVED).count()
    released_results = Result.query.filter_by(status=Result.STATUS_RELEASED).count()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        students_by_level=students_by_level,
        total_courses=total_courses,
        total_lecturers=total_lecturers,
        assigned_courses=assigned_courses,
        submitted_results=submitted_results,
        approved_results=approved_results,
        released_results=released_results,
    )


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@admin_bp.route("/students")
@login_required
@exam_officer_required
def students():
    level_filter = request.args.get("level", type=int)
    query = Student.query
    if level_filter:
        query = query.filter_by(level=level_filter)
    all_students = query.order_by(Student.level, Student.reg_number).all()
    return render_template("students.html", students=all_students, level_filter=level_filter)


@admin_bp.route("/students/add", methods=["GET", "POST"])
@login_required
@exam_officer_required
def add_student():
    all_sessions = AcademicSession.query.order_by(AcademicSession.name).all()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        reg_number = request.form.get("reg_number", "").strip()
        level = int(request.form.get("level"))
        email = request.form.get("email", "").strip()
        academic_session_id = request.form.get("academic_session_id", type=int) or current_session().id
        password = request.form.get("password", "").strip()

        if Student.query.filter_by(reg_number=reg_number).first():
            flash("A student with that registration number already exists.", "danger")
            return redirect(url_for("admin.add_student"))
        if User.query.filter_by(username=reg_number).first():
            flash("That registration number is already used as a login username.", "danger")
            return redirect(url_for("admin.add_student"))
        if password and len(password) < MIN_PASSWORD_LENGTH:
            flash(f"The password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return redirect(url_for("admin.add_student"))

        student = Student(
            full_name=full_name,
            reg_number=reg_number,
            level=level,
            email=email or None,
            academic_session_id=academic_session_id,
            status="Active",
        )
        db.session.add(student)
        db.session.flush()
        create_student_account(student, password=password or None)
        db.session.commit()
        flash(f"Student '{full_name}' added. Login: {reg_number} with the password you set.", "success")
        return redirect(url_for("admin.students"))

    return render_template("add_student.html", sessions=all_sessions, current_session=current_session())


@admin_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@exam_officer_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        student.full_name = request.form.get("full_name", student.full_name).strip()
        student.email = request.form.get("email", student.email)
        student.level = int(request.form.get("level", student.level))
        student.status = request.form.get("status", student.status)

        new_password = request.form.get("new_password", "").strip()
        if new_password:
            if len(new_password) < MIN_PASSWORD_LENGTH:
                flash(f"The password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
                return redirect(url_for("admin.edit_student", student_id=student.id))
            if student.user is None:
                create_student_account(student, password=new_password)
            else:
                student.user.set_password(new_password)
        if student.user:
            student.user.full_name = student.full_name

        db.session.commit()
        flash("Student updated successfully.", "success")
        return redirect(url_for("admin.students"))
    return render_template("edit_student.html", student=student)


@admin_bp.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
@exam_officer_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    name = student.full_name
    login_account = student.user
    db.session.delete(student)
    if login_account:
        db.session.delete(login_account)
    db.session.commit()
    flash(f"Student '{name}' and all of their results were removed.", "info")
    return redirect(url_for("admin.students"))


# ---------------------------------------------------------------------------
# Lecturers
# ---------------------------------------------------------------------------

@admin_bp.route("/lecturers")
@login_required
@exam_officer_required
def lecturers():
    all_lecturers = Lecturer.query.order_by(Lecturer.name).all()
    return render_template("lecturers.html", lecturers=all_lecturers, max_courses=MAX_COURSES_PER_LECTURER)


@admin_bp.route("/lecturers/add", methods=["GET", "POST"])
@login_required
@exam_officer_required
def add_lecturer():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip() or "lecturer123"

        if Lecturer.query.filter_by(email=email).first():
            flash("A lecturer with that email already exists.", "danger")
            return redirect(url_for("admin.add_lecturer"))
        if User.query.filter_by(username=username).first():
            flash("That username is already taken.", "danger")
            return redirect(url_for("admin.add_lecturer"))

        user = User(username=username, role="lecturer", full_name=name, is_demo=False)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        lecturer = Lecturer(name=name, email=email, phone=phone, user_id=user.id)
        db.session.add(lecturer)
        db.session.commit()
        flash(f"Lecturer '{name}' added with login username '{username}'.", "success")
        return redirect(url_for("admin.lecturers"))

    return render_template("add_lecturer.html")


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

@admin_bp.route("/courses")
@login_required
@exam_officer_required
def courses():
    level_filter = request.args.get("level", type=int)
    query = Course.query
    if level_filter:
        query = query.filter_by(level=level_filter)
    all_courses = query.order_by(Course.level, Course.code).all()
    return render_template("courses.html", courses=all_courses, level_filter=level_filter)


@admin_bp.route("/courses/add", methods=["GET", "POST"])
@login_required
@exam_officer_required
def add_course():
    semesters = Semester.query.all()
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        if Course.query.filter_by(code=code).first():
            flash("A course with that code already exists.", "danger")
            return redirect(url_for("admin.add_course"))

        course = Course(
            code=code,
            title=request.form.get("title", "").strip(),
            level=int(request.form.get("level")),
            semester_id=int(request.form.get("semester_id")),
            credit_unit=int(request.form.get("credit_unit", 3)),
            course_type=request.form.get("course_type", "Core"),
        )
        db.session.add(course)
        db.session.commit()
        flash(f"Course {code} added successfully.", "success")
        return redirect(url_for("admin.courses"))

    return render_template("add_course.html", semesters=semesters)


@admin_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@exam_officer_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    semesters = Semester.query.all()
    if request.method == "POST":
        course.title = request.form.get("title", course.title).strip()
        course.level = int(request.form.get("level", course.level))
        course.semester_id = int(request.form.get("semester_id", course.semester_id))
        course.credit_unit = int(request.form.get("credit_unit", course.credit_unit))
        course.course_type = request.form.get("course_type", course.course_type)
        db.session.commit()
        flash("Course updated successfully.", "success")
        return redirect(url_for("admin.courses"))
    return render_template("edit_course.html", course=course, semesters=semesters)


@admin_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@exam_officer_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash(f"Course {course.code} removed.", "info")
    return redirect(url_for("admin.courses"))


# ---------------------------------------------------------------------------
# Course Assignment
# ---------------------------------------------------------------------------

@admin_bp.route("/assignments", methods=["GET", "POST"])
@login_required
@exam_officer_required
def assignments():
    session_obj = current_session()
    all_lecturers = Lecturer.query.order_by(Lecturer.name).all()
    all_courses = Course.query.order_by(Course.level, Course.code).all()
    semesters = Semester.query.all()

    if request.method == "POST":
        course_id = int(request.form.get("course_id"))
        lecturer_id = int(request.form.get("lecturer_id"))
        semester_id = int(request.form.get("semester_id"))

        lecturer = Lecturer.query.get_or_404(lecturer_id)
        count = lecturer.active_assignment_count(session_obj.id, semester_id)

        if count >= MAX_COURSES_PER_LECTURER:
            flash(
                f"{lecturer.name} already has {MAX_COURSES_PER_LECTURER} courses assigned "
                f"for this semester. A lecturer cannot be assigned more than "
                f"{MAX_COURSES_PER_LECTURER} courses.",
                "danger",
            )
            return redirect(url_for("admin.assignments"))

        existing = CourseAssignment.query.filter_by(
            course_id=course_id, lecturer_id=lecturer_id,
            academic_session_id=session_obj.id, semester_id=semester_id,
        ).first()
        if existing:
            flash("This course is already assigned to this lecturer for the selected semester.", "warning")
            return redirect(url_for("admin.assignments"))

        assignment = CourseAssignment(
            course_id=course_id, lecturer_id=lecturer_id,
            academic_session_id=session_obj.id, semester_id=semester_id,
        )
        db.session.add(assignment)
        db.session.commit()
        flash("Course assigned successfully.", "success")
        return redirect(url_for("admin.assignments"))

    all_assignments = CourseAssignment.query.filter_by(academic_session_id=session_obj.id).all()
    return render_template(
        "assignments.html",
        lecturers=all_lecturers,
        courses=all_courses,
        semesters=semesters,
        all_assignments=all_assignments,
        max_courses=MAX_COURSES_PER_LECTURER,
        session_obj=session_obj,
    )


@admin_bp.route("/assignments/<int:assignment_id>/delete", methods=["POST"])
@login_required
@exam_officer_required
def delete_assignment(assignment_id):
    assignment = CourseAssignment.query.get_or_404(assignment_id)
    db.session.delete(assignment)
    db.session.commit()
    flash("Assignment removed.", "info")
    return redirect(url_for("admin.assignments"))


# ---------------------------------------------------------------------------
# Results: review, approve, release
# ---------------------------------------------------------------------------

@admin_bp.route("/results")
@login_required
@exam_officer_required
def results():
    status_filter = request.args.get("status")
    level_filter = request.args.get("level", type=int)
    course_id_filter = request.args.get("course_id", type=int)
    lecturer_id_filter = request.args.get("lecturer_id", type=int)

    query = Result.query.join(Student).join(Course)
    if status_filter:
        query = query.filter(Result.status == status_filter)
    if level_filter:
        query = query.filter(Student.level == level_filter)
    if course_id_filter:
        query = query.filter(Result.course_id == course_id_filter)
    if lecturer_id_filter:
        query = query.filter(Result.lecturer_id == lecturer_id_filter)

    all_results = query.order_by(Course.code, Student.reg_number).all()
    all_courses = Course.query.order_by(Course.code).all()
    all_lecturers = Lecturer.query.order_by(Lecturer.name).all()

    return render_template(
        "results.html",
        results=all_results,
        courses=all_courses,
        lecturers=all_lecturers,
        status_filter=status_filter,
        level_filter=level_filter,
        course_id_filter=course_id_filter,
        lecturer_id_filter=lecturer_id_filter,
        statuses=[Result.STATUS_DRAFT, Result.STATUS_SUBMITTED, Result.STATUS_APPROVED, Result.STATUS_RELEASED],
    )


@admin_bp.route("/results/<int:result_id>/approve", methods=["POST"])
@login_required
@exam_officer_required
def approve_result(result_id):
    result = Result.query.get_or_404(result_id)
    if result.status != Result.STATUS_SUBMITTED:
        flash("Only submitted results can be approved.", "warning")
    else:
        result.status = Result.STATUS_APPROVED
        db.session.commit()
        flash("Result approved.", "success")
    return redirect(request.referrer or url_for("admin.results"))


@admin_bp.route("/results/<int:result_id>/release", methods=["POST"])
@login_required
@exam_officer_required
def release_result(result_id):
    result = Result.query.get_or_404(result_id)
    if result.status != Result.STATUS_APPROVED:
        flash("Only approved results can be released.", "warning")
    else:
        result.status = Result.STATUS_RELEASED
        db.session.commit()
        flash("Result released.", "success")
    return redirect(request.referrer or url_for("admin.results"))


@admin_bp.route("/results/release-all-approved", methods=["POST"])
@login_required
@exam_officer_required
def release_all_approved():
    approved = Result.query.filter_by(status=Result.STATUS_APPROVED).all()
    for result in approved:
        result.status = Result.STATUS_RELEASED
    db.session.commit()
    flash(f"{len(approved)} result(s) released.", "success")
    return redirect(url_for("admin.results"))


# ---------------------------------------------------------------------------
# Grading configuration
# ---------------------------------------------------------------------------

@admin_bp.route("/grading", methods=["GET", "POST"])
@login_required
@exam_officer_required
def grading():
    if request.method == "POST":
        for config in GradeConfig.query.all():
            prefix = f"grade_{config.id}"
            min_score = request.form.get(f"{prefix}_min")
            max_score = request.form.get(f"{prefix}_max")
            grade_point = request.form.get(f"{prefix}_gp")
            if min_score is not None:
                config.min_score = int(min_score)
            if max_score is not None:
                config.max_score = int(max_score)
            if grade_point is not None:
                config.grade_point = float(grade_point)
        db.session.commit()
        flash("Grading scale updated. Note: this does not retroactively recalculate already-released results.", "success")
        return redirect(url_for("admin.grading"))

    grade_configs = GradeConfig.query.order_by(GradeConfig.min_score.desc()).all()
    return render_template("grading.html", grade_configs=grade_configs)


# ---------------------------------------------------------------------------
# Student search / transcript (shared logic lives in routes/results.py)
# ---------------------------------------------------------------------------
