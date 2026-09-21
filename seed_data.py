"""
Seeds the database with starter data on first launch:
- 1 academic session, 2 semesters
- A configurable grading scale
- 1 Examination Officer account
- 5 sample lecturers (each with a login)
- Sample Software Engineering courses across 100 to 400 level
- 40 sample students (10 per level)
- A handful of sample course assignments

This is sample data meant to be replaced with real records once the system
is in use. It is not presented as FUTB's official curriculum, grading
policy, or staff list.
"""

from models import (
    db, User, Lecturer, Student, Course, CourseAssignment,
    AcademicSession, Semester, GradeConfig,
)


SAMPLE_COURSES = [
    # (code, title, level, semester_name, credit_unit, course_type)
    ("CSC101", "Introduction to Computer Science", 100, "First", 3, "Core"),
    ("MTH101", "Elementary Mathematics I", 100, "First", 3, "Core"),
    ("GST101", "Communication in English", 100, "First", 2, "General"),
    ("CSC102", "Introduction to Programming", 100, "Second", 3, "Core"),
    ("PHY102", "General Physics II", 100, "Second", 3, "Core"),
    ("GST102", "Nigerian Peoples and Culture", 100, "Second", 2, "General"),

    ("SWE201", "Introduction to Software Engineering", 200, "First", 3, "Core"),
    ("CSC201", "Data Structures and Algorithms", 200, "First", 3, "Core"),
    ("MTH201", "Discrete Mathematics", 200, "First", 3, "Core"),
    ("SWE202", "Object-Oriented Programming", 200, "Second", 3, "Core"),
    ("CSC202", "Computer Organization and Architecture", 200, "Second", 3, "Core"),
    ("STA202", "Probability and Statistics", 200, "Second", 3, "Core"),

    ("SWE301", "Software Requirements Engineering", 300, "First", 3, "Core"),
    ("SWE302", "Database Systems", 300, "First", 3, "Core"),
    ("CSC301", "Operating Systems", 300, "First", 3, "Core"),
    ("SWE303", "Software Design and Architecture", 300, "Second", 3, "Core"),
    ("SWE304", "Web Application Development", 300, "Second", 3, "Core"),
    ("CSC302", "Computer Networks", 300, "Second", 3, "Core"),

    ("SWE401", "Software Project Management", 400, "First", 3, "Core"),
    ("SWE402", "Software Quality Assurance and Testing", 400, "First", 3, "Core"),
    ("SWE403", "Software Engineering Ethics and Professionalism", 400, "First", 2, "General"),
    ("SWE404", "Final Year Project I", 400, "Second", 6, "Core"),
    ("SWE405", "Cloud Computing and DevOps", 400, "Second", 3, "Elective"),
    ("SWE406", "Mobile Application Development", 400, "Second", 3, "Elective"),
]

# level -> registration-number year prefix, per the spec
LEVEL_REG_PREFIX = {
    100: "SIT/SWE/26",
    200: "SIT/SWE/25",
    300: "SIT/SWE/24",
    400: "SIT/SWE/23",
}

LECTURER_NAMES = [
    ("Lecturer 1", "lecturer1@futb-swe.edu.ng", "lecturer1"),
    ("Lecturer 2", "lecturer2@futb-swe.edu.ng", "lecturer2"),
    ("Lecturer 3", "lecturer3@futb-swe.edu.ng", "lecturer3"),
    ("Lecturer 4", "lecturer4@futb-swe.edu.ng", "lecturer4"),
    ("Lecturer 5", "lecturer5@futb-swe.edu.ng", "lecturer5"),
]

MAX_COURSES_PER_LECTURER = 4


def seed_all():
    """Idempotent: only seeds if the database is empty."""
    if User.query.first():
        return  # already seeded

    # --- Academic session & semesters -----------------------------------
    session_obj = AcademicSession(name="2025/2026", is_current=True)
    db.session.add(session_obj)

    first_sem = Semester(name="First")
    second_sem = Semester(name="Second")
    db.session.add_all([first_sem, second_sem])
    db.session.flush()
    semester_lookup = {"First": first_sem, "Second": second_sem}

    # --- Grading scale (configurable) ------------------------------------
    grade_scale = [
        (70, 100, "A", 5.0),
        (60, 69, "B", 4.0),
        (50, 59, "C", 3.0),
        (45, 49, "D", 2.0),
        (40, 44, "E", 1.0),
        (0, 39, "F", 0.0),
    ]
    for min_s, max_s, grade, gp in grade_scale:
        db.session.add(GradeConfig(min_score=min_s, max_score=max_s, grade=grade, grade_point=gp))

    # --- Examination Officer ---------------------------------------------
    exam_officer = User(
        username="examofficer",
        role="exam_officer",
        full_name="Demo Examination Officer",
        is_demo=True,
    )
    exam_officer.set_password(DEMO_PASSWORD_EXAM_OFFICER)
    db.session.add(exam_officer)

    # --- Lecturers ---------------------------------------------------------
    lecturers = []
    for name, email, username in LECTURER_NAMES:
        user = User(username=username, role="lecturer", full_name=name, is_demo=True)
        user.set_password(DEMO_PASSWORD_LECTURER)
        db.session.add(user)
        db.session.flush()

        lecturer = Lecturer(name=name, email=email, phone="080000000" + username[-1], user_id=user.id)
        db.session.add(lecturer)
        lecturers.append(lecturer)
    db.session.flush()

    # --- Courses -------------------------------------------------------------
    courses = []
    for code, title, level, sem_name, units, ctype in SAMPLE_COURSES:
        course = Course(
            code=code,
            title=title,
            level=level,
            semester_id=semester_lookup[sem_name].id,
            credit_unit=units,
            course_type=ctype,
        )
        db.session.add(course)
        courses.append(course)
    db.session.flush()

    # --- Students: 10 per level, 40 total ------------------------------------
    counter = 1000
    for level, prefix in LEVEL_REG_PREFIX.items():
        for i in range(1, 11):
            counter += 1
            reg_number = f"{prefix}/{i:04d}"
            student = Student(
                full_name=f"Student {counter}",
                reg_number=reg_number,
                level=level,
                academic_session_id=session_obj.id,
                email=f"student{counter}@futbabura-demo.edu.ng",
                status="Active",
            )
            db.session.add(student)
    db.session.flush()

    # --- Sample course assignments (respecting the 4-course-per-lecturer rule) ---
    lecturer_load = {lecturer.id: 0 for lecturer in lecturers}
    lecturer_cycle_index = 0

    for course in courses:
        # round-robin through lecturers, skipping anyone already at the cap
        attempts = 0
        while attempts < len(lecturers):
            lecturer = lecturers[lecturer_cycle_index % len(lecturers)]
            lecturer_cycle_index += 1
            attempts += 1
            if lecturer_load[lecturer.id] < MAX_COURSES_PER_LECTURER:
                db.session.add(CourseAssignment(
                    course_id=course.id,
                    lecturer_id=lecturer.id,
                    academic_session_id=session_obj.id,
                    semester_id=course.semester_id,
                ))
                lecturer_load[lecturer.id] += 1
                break
        # if every lecturer is at capacity, the course is simply left unassigned
        # (this is expected once 5 lecturers x 4 courses = 20 slots are filled)

    db.session.commit()
