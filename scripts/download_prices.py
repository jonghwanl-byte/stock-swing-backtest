from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swing_backtest.universe import load_membership_intervals, mark_point_in_time_membership


def _extract_symbol(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    frame = raw
    if isinstance(raw.columns, pd.MultiIndex):
        if ticker in raw.columns.get_level_values(0):
            frame = raw[ticker]
        elif ticker in raw.columns.get_level_values(1):
            frame = raw.xs(ticker, axis=1, level=1)
        else:
            return pd.DataFrame()
    frame = frame.rename(columns={str(c): str(c).lower().replace(" ", "_") for c in frame.columns})
    needed = ["open", "high", "low", "close", "volume"]
    if not set(needed).issubset(frame.columns):
        return pd.DataFrame()
    frame = frame[needed].dropna(subset=["close"]).reset_index()
    frame = frame.rename(columns={frame.columns[0]: "date"})
    frame["ticker"] = ticker
    return frame[["date", "ticker", *needed]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="data/sp500_membership.csv")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--warmup-days", type=int, default=420)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--output", default="data/prices.csv")
    parser.add_argument("--report", default="outputs/download_report.json")
    args = parser.parse_args()

    intervals = load_membership_intervals(args.universe)
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end) if args.end else pd.Timestamp.utcnow().tz_localize(None).normalize()
    relevant = intervals.loc[
        (intervals["start_date"] <= end)
        & (intervals["end_date"].isna() | (intervals["end_date"] >= start))
    ]
    tickers = sorted(relevant["ticker"].unique())
    download_start = start - pd.Timedelta(days=args.warmup_days)
    frames: list[pd.DataFrame] = []
    missing: list[str] = []

    for offset in range(0, len(tickers), args.batch_size):
        batch = tickers[offset:offset + args.batch_size]
        raw = yf.download(
            batch,
            start=download_start.strftime("%Y-%m-%d"),
            end=(end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            auto_adjust=True,
            actions=False,
            group_by="ticker",
            threads=True,
            progress=False,
        )
        for ticker in batch:
            frame = _extract_symbol(raw, ticker)
            if frame.empty:
                missing.append(ticker)
            else:
                frames.append(frame)

    if not frames:
        raise RuntimeError("No price data downloaded")
    prices = pd.concat(frames, ignore_index=True)
    prices = mark_point_in_time_membership(prices, intervals)
    prices = prices.sort_values(["ticker", "date"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(output, index=False, date_format="%Y-%m-%d")

    report = {
        "requested_tickers": len(tickers),
        "downloaded_tickers": int(prices["ticker"].nunique()),
        "missing_tickers": missing,
        "first_date": str(prices["date"].min().date()),
        "last_date": str(prices["date"].max().date()),
        "rows": len(prices),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
