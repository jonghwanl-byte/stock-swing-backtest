from __future__ import annotations

import argparse
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swing_backtest.universe import normalize_ticker, reconstruct_intervals

CURRENT_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
HISTORY_URL = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"


def _flatten(column: object) -> str:
    if isinstance(column, tuple):
        return " ".join(str(part) for part in column if not str(part).startswith("Unnamed")).strip()
    return str(column).strip()


def _read_tables(url: str) -> list[pd.DataFrame]:
    response = requests.get(
        url,
        headers={"User-Agent": "stock-swing-backtest/1.0 (research project)"},
        timeout=30,
    )
    response.raise_for_status()
    return pd.read_html(StringIO(response.text))


def fetch_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    current_tables = _read_tables(CURRENT_URL)
    history_tables = _read_tables(HISTORY_URL)
    current = next(
        table for table in current_tables
        if any(_flatten(c) == "Symbol" for c in table.columns)
    )
    changes = next(
        table for table in history_tables
        if any("Added" in _flatten(c) for c in table.columns)
        and any("Removed" in _flatten(c) for c in table.columns)
    )
    changes.columns = [_flatten(column) for column in changes.columns]
    return current, changes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--output", default="data/sp500_membership.csv")
    args = parser.parse_args()

    current, raw_changes = fetch_tables()
    symbol_column = next(c for c in current.columns if _flatten(c) == "Symbol")
    current_tickers = [normalize_ticker(value) for value in current[symbol_column]]
    date_column = next(c for c in raw_changes.columns if "Date" in c)
    added_column = next(c for c in raw_changes.columns if "Added" in c and "Ticker" in c)
    removed_column = next(c for c in raw_changes.columns if "Removed" in c and "Ticker" in c)
    changes = raw_changes.rename(columns={
        date_column: "date",
        added_column: "added",
        removed_column: "removed",
    })[["date", "added", "removed"]]
    changes["date"] = pd.to_datetime(changes["date"], errors="coerce")
    changes = changes.dropna(subset=["date"])
    changes = changes.loc[changes["date"] >= pd.Timestamp(args.start)]

    intervals = reconstruct_intervals(current_tickers, changes, args.start)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    intervals.to_csv(output, index=False, date_format="%Y-%m-%d")
    print(f"Wrote {len(intervals)} membership intervals for {intervals.ticker.nunique()} tickers")


if __name__ == "__main__":
    main()
