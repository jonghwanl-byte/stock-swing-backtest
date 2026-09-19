from __future__ import annotations

from pathlib import Path

import pandas as pd


UNIVERSE_COLUMNS = {"ticker", "start_date", "end_date"}


def normalize_ticker(value: object) -> str:
    """Normalize symbols to Yahoo Finance's convention."""
    return str(value).strip().upper().replace(".", "-")


def load_membership_intervals(path: str | Path) -> pd.DataFrame:
    intervals = pd.read_csv(path)
    missing = UNIVERSE_COLUMNS.difference(intervals.columns)
    if missing:
        raise ValueError(f"Missing universe columns: {sorted(missing)}")
    intervals = intervals.copy()
    intervals["ticker"] = intervals["ticker"].map(normalize_ticker)
    intervals["start_date"] = pd.to_datetime(intervals["start_date"], errors="raise")
    intervals["end_date"] = pd.to_datetime(intervals["end_date"], errors="coerce")
    invalid = intervals["end_date"].notna() & (
        intervals["end_date"] < intervals["start_date"]
    )
    if invalid.any():
        raise ValueError("Universe contains end_date before start_date")
    return intervals.sort_values(["ticker", "start_date"]).reset_index(drop=True)


def mark_point_in_time_membership(
    prices: pd.DataFrame, intervals: pd.DataFrame
) -> pd.DataFrame:
    """Mark each price row using membership known for that historical date."""
    result = prices.copy()
    result["date"] = pd.to_datetime(result["date"])
    result["ticker"] = result["ticker"].map(normalize_ticker)
    result["in_universe"] = False
    result["universe_exit"] = False
    for row in intervals.itertuples(index=False):
        active = (
            (result["ticker"] == row.ticker)
            & (result["date"] >= row.start_date)
            & (pd.isna(row.end_date) | (result["date"] <= row.end_date))
        )
        result.loc[active, "in_universe"] = True
        if pd.notna(row.end_date) and active.any():
            last_active_index = result.loc[active, "date"].idxmax()
            result.loc[last_active_index, "universe_exit"] = True
    return result


def reconstruct_intervals(
    current_tickers: list[str],
    changes: pd.DataFrame,
    history_start: str | pd.Timestamp,
) -> pd.DataFrame:
    """Reconstruct index membership backwards from current members.

    Expected change columns: date, added, removed. Multiple membership spells are
    retained, which is important when a company leaves and later rejoins.
    """
    floor = pd.Timestamp(history_start).normalize()
    events = changes.copy()
    events["date"] = pd.to_datetime(events["date"]).dt.normalize()
    events = events.sort_values("date", ascending=False)
    active: dict[str, pd.Timestamp | None] = {
        normalize_ticker(ticker): None for ticker in current_tickers
    }
    records: list[dict] = []

    for event in events.itertuples(index=False):
        date = pd.Timestamp(event.date)
        added = normalize_ticker(event.added) if pd.notna(event.added) else ""
        removed = normalize_ticker(event.removed) if pd.notna(event.removed) else ""

        if added and added in active:
            records.append({
                "ticker": added,
                "start_date": date,
                "end_date": active.pop(added),
            })
        if removed and removed not in active:
            active[removed] = date - pd.Timedelta(days=1)

    for ticker, end_date in active.items():
        records.append({
            "ticker": ticker,
            "start_date": floor,
            "end_date": end_date,
        })

    result = pd.DataFrame(records)
    result = result.loc[
        result["end_date"].isna() | (result["end_date"] >= result["start_date"])
    ]
    return result.sort_values(["ticker", "start_date"]).reset_index(drop=True)
