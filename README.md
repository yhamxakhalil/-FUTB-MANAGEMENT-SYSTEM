# Student Result Management System

A Student Result Management System for the Software Engineering Department,
Federal University of Technology, Babura (FUTB).

> Note: the app comes pre-loaded with sample data (a sample course list,
> sample students, and a sample grading scale) so you can explore every
> feature immediately. All of it is fully editable, and none of it is
> presented as the department's official curriculum or grading policy until
> you replace it with real records.

## Tech Stack

- Backend: Python Flask
- Database: SQLite
- ORM: SQLAlchemy (via Flask-SQLAlchemy)
- Frontend: HTML5, CSS3, Bootstrap 5, vanilla JavaScript
- Authentication: Flask-Login
- Password security: Werkzeug password hashing

## Features

- Three roles: Examination Officer (admin), Lecturer, and Student
- Full student management: add, edit, and remove students, with search and
  level filtering
- Course and lecturer management
- Course assignment with a hard rule: a lecturer cannot be assigned more than
  4 courses per semester
- Lecturer result entry (CA score plus exam score) with automatic total,
  grade, grade point, and quality point calculation
- Score validation: CA must be 0 to 30 and exam must be 0 to 70. Anything
  outside that range (or blank, negative, or not a number) is shown as
  "Invalid" and is not saved or submitted
- Student login: students sign in with their registration number and see
  only their own released results, GPA per semester, and CGPA (printable)
- Configurable grading scale, editable by the Examination Officer
- Result workflow: Draft, then Submitted, then Approved, then Released
- Once a result is Released, lecturers can no longer edit it
- Result search by registration number for staff (Examination Officer and
  lecturers), with GPA and CGPA calculation
- Printable transcript view
- Separate dashboards for the Examination Officer and for Lecturers
- Pre-loaded sample data: 1 Examination Officer, 5 lecturers, 40 students
  (10 per level, 100 to 400), and a sample Software Engineering course list

## Project Structure

```
futb_result_management/
├── app.py                    # App factory, blueprint registration, DB init
├── config.py                 # App configuration
├── seed_data.py               # Sample data seeding (runs on first launch only)
├── db_upgrade.py              # Adds student logins to older databases
├── validators.py              # CA / exam score validation
├── requirements.txt
├── instance/
│   └── database.db           # SQLite database (created automatically)
├── models/
│   └── __init__.py            # All SQLAlchemy models
├── routes/
│   ├── auth.py                # Login / logout
│   ├── admin.py                # Examination Officer routes
│   ├── lecturer.py             # Lecturer routes
│   ├── student.py              # Student portal (own results)
│   └── results.py              # Staff result search and transcript
├── templates/                  # Jinja2 templates (Bootstrap 5)
└── static/
    ├── css/style.css
    └── js/script.js
```

## Getting Started (Running Locally in VS Code)

### 1. Requirements

- Python 3.9 or later installed
- VS Code (recommended) with the Python extension

### 2. Set up a virtual environment

Open the project folder in VS Code, open a terminal, then run:

Windows:
```
python -m venv venv
venv\Scripts\activate
```

macOS / Linux:
```
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Run the application

```
python app.py
```

The first time you run it, the SQLite database is created automatically at
`instance/database.db` and populated with sample data.

### 5. Open the app

Visit http://127.0.0.1:5000 in your browser.

## Login Credentials

| Role                 | Username        | Password       |
|----------------------|-----------------|----------------|
| Examination Officer  | `examofficer`   | `admin123`     |
| Lecturer 1 to 5       | `lecturer1` to `lecturer5` | `lecturer123` |
| Student              | registration number, e.g. `SIT/SWE/24/0003` | `student123` |

You can add real lecturers with their own usernames and passwords from the
Lecturers, then Add Lecturer page once signed in as the Examination Officer.
You can add real students the same way from Students, then Add Student. Each
student gets a login automatically: the username is their registration number
and the password is the one you set (defaults to `student123`).

Every user can change their own password from the Password button in the top
bar. If a student forgets theirs, the Examination Officer can reset it from
Students, then the edit (pencil) button.

## How Students See Their Results

A student only sees a result after it has been **Released**:

1. Lecturer enters the CA and exam scores and clicks Submit.
2. Examination Officer opens Results and clicks Approve, then Release.
3. The student logs in with their registration number and sees the released
   results under My Results, with GPA for each semester and the CGPA.

Students cannot open other students' results, the result search page, or any
admin or lecturer page.

## Upgrading an Existing Database

No action needed. On start-up the app adds the missing column and creates a
login for every existing student who does not have one, without touching your
existing data.

## Resetting the Sample Data

To start fresh, stop the app and delete `instance/database.db`, then run
`python app.py` again. It will be recreated and reseeded automatically.

## Notes on Grading

Scores are validated before anything is saved: CA 0 to 30, exam 0 to 70 (total
out of 100). The letter grade is the highest band whose minimum the total
reaches, so half marks such as 69.5 are graded correctly.

The grading scale (score ranges to letter grade to grade point) is stored in
the database and can be edited from Grading in the Examination Officer menu,
rather than being hard-coded in the application logic. Changing the scale
does not retroactively recalculate results that already exist. It only
affects new calculations going forward.

## Notes on the Course Assignment Rule

The system enforces that a lecturer cannot hold more than 4 course
assignments in the same academic session and semester. This is checked
server-side when the Examination Officer attempts to assign a course.
