from __future__ import annotations

from datetime import datetime, timedelta


CURRENT_PERIOD_LABEL = "当前"


FUTURE_PERIOD_LABEL = "尚未开始"


def build_period_display(
    start_date: datetime | None,
    end_date: datetime | None,
    now: datetime,
) -> dict[str, str]:
    # 起始日期就已经超过当前日期 —— 整个周期在未来
    if start_date is not None and start_date.date() > now.date():
        return {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": FUTURE_PERIOD_LABEL,
            "is_future": True,
        }

    display_end = ""
    if end_date is not None:
        display_end_date = end_date - timedelta(days=1)
        if display_end_date.date() > now.date():
            display_end = CURRENT_PERIOD_LABEL
        else:
            display_end = display_end_date.strftime("%Y-%m-%d")

    return {
        "start": start_date.strftime("%Y-%m-%d") if start_date else "",
        "end": display_end,
        "is_future": False,
    }
