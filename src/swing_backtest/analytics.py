from __future__ import annotations

import math

import pandas as pd


def _clean_equity(equity: pd.DataFrame) -> pd.DataFrame:
    if equity.empty:
        return pd.DataFrame(columns=["date", "equity", "daily_return"])
    frame = equity.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").drop_duplicates("date")
    frame["equity"] = pd.to_numeric(frame["equity"], errors="coerce")
    frame = frame.dropna(subset=["equity"])
    frame["daily_return"] = frame["equity"].pct_change().fillna(0.0)
    return frame


def _period_stats(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {
            "start_date": None, "end_date": None, "days": 0,
            "ending_equity": 1.0, "cumulative_return": 0.0,
            "cagr": 0.0, "annualized_volatility": 0.0,
            "sharpe_0rf": 0.0, "max_drawdown": 0.0,
        }
    values = frame["equity"]
    daily = frame["daily_return"]
    days = max((frame["date"].iloc[-1] - frame["date"].iloc[0]).days, 1)
    ending = float(values.iloc[-1])
    cagr = ending ** (365.25 / days) - 1.0 if ending > 0 else -1.0
    std = daily.std(ddof=1)
    volatility = float(std * math.sqrt(252)) if pd.notna(std) else 0.0
    sharpe = float(daily.mean() / std * math.sqrt(252)) if std and pd.notna(std) else 0.0
    drawdown = values / values.cummax() - 1.0
    return {
        "start_date": str(frame["date"].iloc[0].date()),
        "end_date": str(frame["date"].iloc[-1].date()),
        "days": int(days),
        "ending_equity": ending,
        "cumulative_return": ending - 1.0,
        "cagr": float(cagr),
        "annualized_volatility": volatility,
        "sharpe_0rf": sharpe,
        "max_drawdown": float(drawdown.min()),
    }


def performance_report(
    equity: pd.DataFrame,
    benchmark: pd.DataFrame | None = None,
) -> tuple[dict, pd.DataFrame]:
    frame = _clean_equity(equity)
    summary = _period_stats(frame)
    annual_rows: list[dict] = []
    if not frame.empty:
        for year, group in frame.groupby(frame["date"].dt.year):
            annual_rows.append({"year": int(year), **_period_stats(group)})
    annual = pd.DataFrame(annual_rows)
    if benchmark is not None and not benchmark.empty:
        if not {"date", "close"}.issubset(benchmark.columns):
            raise ValueError("Benchmark must contain date and close columns")
        bench = benchmark.copy()
        bench["date"] = pd.to_datetime(bench["date"])
        bench["equity"] = bench["close"] / float(bench["close"].iloc[0])
        bench_summary = _period_stats(_clean_equity(bench))
        summary["benchmark"] = bench_summary
        summary["active_return"] = (
            summary["cumulative_return"] - bench_summary["cumulative_return"]
        )
    return summary, annual


def add_data_quality(summary: dict, report: dict | None) -> dict:
    if not report:
        return summary
    requested = int(report.get("requested_tickers", 0))
    downloaded = int(report.get("downloaded_tickers", 0))
    coverage = downloaded / requested if requested else 0.0
    summary["data_quality"] = {
        "requested_tickers": requested,
        "downloaded_tickers": downloaded,
        "missing_tickers": len(report.get("missing_tickers", [])),
        "coverage_ratio": coverage,
        "status": "ok" if coverage >= 0.95 else "warning",
    }
    return summary
