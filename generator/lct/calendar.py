"""dim_date: one row per day in the 90-day window."""

from __future__ import annotations

import pandas as pd


def close_window_dates(days: pd.DatetimeIndex, n_business_days: int) -> set:
    """Last N and first N business days of every month touched by the window.

    Business day = Monday to Friday. Public holidays are ignored on purpose to
    keep the logic easy to follow.
    """
    # Look a month either side so the window edges are computed correctly
    span = pd.date_range(days.min() - pd.offsets.MonthBegin(1), days.max() + pd.offsets.MonthEnd(1), freq="D")
    biz = span[span.dayofweek < 5]
    out = set()
    for _, month_days in pd.Series(biz, index=biz).groupby([biz.year, biz.month]):
        out.update(month_days.iloc[:n_business_days])
        out.update(month_days.iloc[-n_business_days:])
    return {d.normalize() for d in out}


def build_dim_date(cfg: dict) -> pd.DataFrame:
    d = cfg["dates"]
    days = pd.date_range(d["start"], d["end"], freq="D")
    close = close_window_dates(days, d["close_window_business_days"])

    board = [pd.Timestamp(x) for x in d["board_meetings"]]
    prep = set()
    for meeting in board:
        for k in range(0, d["board_prep_days_before"] + 1):
            prep.add(meeting - pd.Timedelta(days=k))

    df = pd.DataFrame({"date": days})
    df["year"] = days.year
    df["quarter"] = days.quarter
    df["month"] = days.month
    df["month_name"] = days.strftime("%B")
    df["iso_week"] = days.isocalendar().week.to_numpy()
    df["week_start"] = days - pd.to_timedelta(days.dayofweek, unit="D")
    df["day_of_week"] = days.dayofweek + 1          # 1 = Monday
    df["day_name"] = days.strftime("%A")
    df["is_weekend"] = days.dayofweek >= 5
    df["is_month_end"] = days.is_month_end
    df["is_month_end_close_window"] = days.isin(list(close))
    df["is_board_prep_window"] = days.isin(list(prep))
    df["days_before_as_of"] = (days.max() - days).days
    return df
