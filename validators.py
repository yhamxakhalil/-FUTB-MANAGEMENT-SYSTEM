"""Score validation for result entry.

Kept free of Flask/SQLAlchemy imports so it can be tested on its own.
"""

import math

MAX_CA_SCORE = 30
MAX_EXAM_SCORE = 70


def parse_score(raw, label, max_value):
    """Validate one score.

    Returns (value, error_message). Exactly one of the two is None.
    Rejects blanks, non-numbers, NaN/inf, negatives and anything above max_value.
    """
    text = (raw or "").strip()
    if text == "":
        return None, f"Invalid {label}: a score is required."

    try:
        value = float(text)
    except ValueError:
        return None, f"Invalid {label}: '{text}' is not a number."

    # float() happily accepts "nan" and "inf"; comparisons with NaN are always
    # False, so it would slip past the range check below without this.
    if not math.isfinite(value):
        return None, f"Invalid {label}: '{text}' is not a valid number."

    if value < 0:
        return None, f"Invalid {label}: it cannot be negative."

    if value > max_value:
        return None, f"Invalid {label}: {value:g} is more than the maximum of {max_value:g}."

    return value, None


def validate_scores(ca_raw, exam_raw):
    """Validate CA (max 30) and exam (max 70) together.

    Returns (ca_score, exam_score, errors) where errors maps the field name
    ('ca_score' / 'exam_score') to its message. Scores are only usable when
    errors is empty.
    """
    errors = {}

    ca, ca_error = parse_score(ca_raw, "CA score", MAX_CA_SCORE)
    if ca_error:
        errors["ca_score"] = ca_error

    exam, exam_error = parse_score(exam_raw, "exam score", MAX_EXAM_SCORE)
    if exam_error:
        errors["exam_score"] = exam_error

    return ca, exam, errors
