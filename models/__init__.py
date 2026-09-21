from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from validators import MAX_CA_SCORE, MAX_EXAM_SCORE

db = SQLAlchemy()

DEFAULT_STUDENT_PASSWORD = "student123"


# ---------------------------------------------------------------------------
# Academic structure
# ---------------------------------------------------------------------------

class AcademicSession(db.Model):
    """e.g. 2025/2026"""
    __tablename__ = "academic_sessions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    is_current = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return self.name


class Semester(db.Model):
    """First Semester / Second Semester"""
    __tablename__ = "semesters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)  # "First", "Second"

    def __repr__(self):
        return self.name


class GradeConfig(db.Model):
    """
    Configurable grading scale. The Examination Officer can edit these
    ranges instead of anything being hard-coded in application logic.
    """
    __tablename__ = "grade_configs"

    id = db.Column(db.Integer, primary_key=True)
    min_score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String(2), nullable=False)
    grade_point = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"{self.grade} ({self.min_score}-{self.max_score})"


# ---------------------------------------------------------------------------
# Users / Auth
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'exam_officer', 'lecturer' or 'student'
    full_name = db.Column(db.String(120), nullable=False)
    is_demo = db.Column(db.Boolean, default=True)

    lecturer = db.relationship("Lecturer", back_populates="user", uselist=False)
    student = db.relationship("Student", back_populates="user", uselist=False)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def is_exam_officer(self):
        return self.role == "exam_officer"

    def is_lecturer(self):
        return self.role == "lecturer"

    def is_student(self):
        return self.role == "student"

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

class Lecturer(db.Model):
    __tablename__ = "lecturers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)

    user = db.relationship("User", back_populates="lecturer")
    assignments = db.relationship("CourseAssignment", back_populates="lecturer", cascade="all, delete-orphan")
    results_entered = db.relationship("Result", back_populates="lecturer")

    def active_assignment_count(self, session_id=None, semester_id=None):
        q = CourseAssignment.query.filter_by(lecturer_id=self.id)
        if session_id:
            q = q.filter_by(academic_session_id=session_id)
        if semester_id:
            q = q.filter_by(semester_id=semester_id)
        return q.count()

    def __repr__(self):
        return self.name


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    reg_number = db.Column(db.String(40), unique=True, nullable=False)
    level = db.Column(db.Integer, nullable=False)  # 100, 200, 300, 400
    academic_session_id = db.Column(db.Integer, db.ForeignKey("academic_sessions.id"))
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default="Active")  # Active, Suspended, Graduated
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=True)

    academic_session = db.relationship("AcademicSession")
    user = db.relationship("User", back_populates="student")
    results = db.relationship("Result", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"{self.full_name} ({self.reg_number})"


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)
    credit_unit = db.Column(db.Integer, nullable=False, default=3)
    course_type = db.Column(db.String(20), default="Core")  # Core / Elective

    semester = db.relationship("Semester")
    assignments = db.relationship("CourseAssignment", back_populates="course", cascade="all, delete-orphan")
    results = db.relationship("Result", back_populates="course")

    def __repr__(self):
        return f"{self.code} - {self.title}"


class CourseAssignment(db.Model):
    __tablename__ = "course_assignments"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey("lecturers.id"), nullable=False)
    academic_session_id = db.Column(db.Integer, db.ForeignKey("academic_sessions.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)

    course = db.relationship("Course", back_populates="assignments")
    lecturer = db.relationship("Lecturer", back_populates="assignments")
    academic_session = db.relationship("AcademicSession")
    semester = db.relationship("Semester")

    __table_args__ = (
        db.UniqueConstraint(
            "course_id", "lecturer_id", "academic_session_id", "semester_id",
            name="uq_course_lecturer_session_semester",
        ),
    )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

class Result(db.Model):
    __tablename__ = "results"

    STATUS_DRAFT = "Draft"
    STATUS_SUBMITTED = "Submitted"
    STATUS_APPROVED = "Approved"
    STATUS_RELEASED = "Released"

    MAX_CA_SCORE = MAX_CA_SCORE
    MAX_EXAM_SCORE = MAX_EXAM_SCORE

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey("lecturers.id"), nullable=False)
    academic_session_id = db.Column(db.Integer, db.ForeignKey("academic_sessions.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)

    ca_score = db.Column(db.Float, default=0)
    exam_score = db.Column(db.Float, default=0)
    total_score = db.Column(db.Float, default=0)
    grade = db.Column(db.String(2))
    grade_point = db.Column(db.Float)
    quality_point = db.Column(db.Float)

    status = db.Column(db.String(20), default=STATUS_DRAFT)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship("Student", back_populates="results")
    course = db.relationship("Course", back_populates="results")
    lecturer = db.relationship("Lecturer", back_populates="results_entered")
    academic_session = db.relationship("AcademicSession")
    semester = db.relationship("Semester")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id", "course_id", "academic_session_id", "semester_id",
            name="uq_student_course_session_semester",
        ),
    )

    def compute_grade(self):
        """Recalculate total, grade, grade point, and quality point using GradeConfig."""
        self.total_score = (self.ca_score or 0) + (self.exam_score or 0)
        # Pick the highest band whose minimum the total reaches. Matching on
        # min AND max leaves gaps for half marks (e.g. 69.5 falls between the
        # 60-69 and 70-100 bands) and produced "N/A".
        config = (
            GradeConfig.query
            .filter(GradeConfig.min_score <= self.total_score)
            .order_by(GradeConfig.min_score.desc())
            .first()
        )
        if config:
            self.grade = config.grade
            self.grade_point = config.grade_point
        else:
            self.grade = "N/A"
            self.grade_point = 0
        self.quality_point = (self.grade_point or 0) * (self.course.credit_unit if self.course else 0)

    def __repr__(self):
        return f"<Result {self.student_id}-{self.course_id}: {self.total_score}>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_student_account(student, password=None, is_demo=False):
    """Create the login for a student. Username is the registration number.

    Adds to the session but does not commit, so callers can commit together
    with whatever else they are saving.
    """
    user = User(
        username=student.reg_number,
        role="student",
        full_name=student.full_name,
        is_demo=is_demo,
    )
    user.set_password(password or DEFAULT_STUDENT_PASSWORD)
    db.session.add(user)
    db.session.flush()
    student.user_id = user.id
    return user
