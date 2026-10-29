# A student must have at least 75% attendance.
# If a student can miss this many classes or fewer, we show a "borderline" warning.
BORDERLINE_LIMIT = 1


def _check(attended: int, conducted: int):
    if attended < 0 or conducted < 0 or attended > conducted:
        raise ValueError("Need 0 <= attended <= conducted")


def attendance_percentage(attended: int, conducted: int):
    """Percentage rounded to 2 places, or None if no classes were held."""
    _check(attended, conducted)

    if conducted == 0:
        return None

    return round(attended / conducted * 100, 2)


def classes_can_skip(attended: int, conducted: int) -> int:
    """Largest K with attended / (conducted + K) >= 0.75.
    From 4P >= 3(C + K)  =>  K = (4P - 3C) // 3.
    Returns 0 if attendance is already below 75%."""
    _check(attended, conducted)
    return max(0, (4 * attended - 3 * conducted) // 3)


def classes_to_recover(attended: int, conducted: int) -> int:
    """Smallest X with (attended + X) / (conducted + X) >= 0.75.
    From 4(P + X) >= 3(C + X)  =>  X = 3C - 4P.
    Returns 0 if attendance is already 75% or more."""
    _check(attended, conducted)
    return max(0, 3 * conducted - 4 * attended)


def summarize(attended: int, conducted: int) -> dict:
    percentage = attendance_percentage(attended, conducted)
    skip = classes_can_skip(attended, conducted)
    recover = classes_to_recover(attended, conducted)

    if conducted == 0:
        status = "no_classes"
        message = "No classes have been conducted yet"
    elif recover > 0:
        status = "short"
        message = (
            f"Short attendance: attend the next {recover} class(es) "
            f"in a row to reach 75%"
        )
    elif skip <= BORDERLINE_LIMIT:
        status = "borderline"
        message = (
            f"Careful: you can miss at most {skip} more class(es) "
            f"before dropping below 75%"
        )
    else:
        status = "safe"
        message = f"You can miss up to {skip} more classes and stay at 75% or above"

    return {
        "attended": attended,
        "conducted": conducted,
        "percentage": percentage,
        "can_skip": skip,
        "classes_to_recover": recover,
        "status": status,
        "message": message,
    }