from datetime import date


def shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    """Return the year and month shifted by the requested number of months."""
    absolute_month = year * 12 + (month - 1) + offset
    shifted_year, shifted_month_index = divmod(absolute_month, 12)
    return shifted_year, shifted_month_index + 1


def resolve_requested_month(
    year_value: str | None,
    month_value: str | None,
    today: date,
    *,
    max_future_months: int,
) -> tuple[int, int]:
    """Parse a requested calendar month and cap it at the allowed future month."""
    try:
        requested_year = int(year_value) if year_value is not None else today.year
        requested_month = int(month_value) if month_value is not None else today.month
        if not 1 <= requested_month <= 12:
            raise ValueError
        if not 1 <= requested_year <= 9999:
            raise ValueError
    except (TypeError, ValueError):
        requested_year, requested_month = today.year, today.month

    maximum_year, maximum_month = shift_month(
        today.year,
        today.month,
        max_future_months,
    )
    if (requested_year, requested_month) > (maximum_year, maximum_month):
        return maximum_year, maximum_month
    return requested_year, requested_month
