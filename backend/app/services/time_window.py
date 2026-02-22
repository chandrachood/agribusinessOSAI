from datetime import date, timedelta
from typing import Optional, Tuple


def resolve_time_window(
    start_date: Optional[date] = None, end_date: Optional[date] = None
) -> Tuple[date, date]:
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=365)
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    return start_date, end_date
