"""Small, non-destructive upgrades for databases created by an older version.

- Adds students.user_id if it is missing (SQLite does not add new columns to
  existing tables on its own).
- Gives every student without a login one (username = registration number).

Both steps are safe to run on every start-up.
"""

from sqlalchemy import inspect, text

from models import db, Student, User, create_student_account


def add_missing_columns():
    columns = {c["name"] for c in inspect(db.engine).get_columns("students")}
    if "user_id" not in columns:
        db.session.execute(text("ALTER TABLE students ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        db.session.commit()


def ensure_student_accounts():
    students = Student.query.filter(Student.user_id.is_(None)).all()
    created = 0
    for student in students:
        if User.query.filter_by(username=student.reg_number).first():
            # Username already used by someone else; leave the student without
            # a login rather than guessing. The Exam Officer can resolve it.
            continue
        create_student_account(student, is_demo=True)
        created += 1
    if students:
        db.session.commit()
    return created
