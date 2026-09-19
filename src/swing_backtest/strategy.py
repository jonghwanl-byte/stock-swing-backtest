from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"date", "ticker", "open", "high", "low", "close", "volume"}


def _cross_sectional_percentile(series: pd.Series) -> pd.Series:
    return series.rank(pct=True, method="average").fillna(0.0)


def add_features(prices: pd.DataFrame) -> pd.DataFrame:
    """Create point-in-time price/volume features without future information."""
    missing = REQUIRED_COLUMNS.difference(prices.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df = prices.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    g = df.groupby("ticker", group_keys=False)

    df["ma50"] = g["close"].transform(lambda x: x.rolling(50, min_periods=50).mean())
    df["ma200"] = g["close"].transform(lambda x: x.rolling(200, min_periods=200).mean())
    df["mom63"] = g["close"].pct_change(63)
    df["mom126"] = g["close"].pct_change(126)
    df["high63"] = g["high"].transform(lambda x: x.rolling(63, min_periods=63).max())
    df["breakout63"] = df["close"] / df["high63"] - 1.0
    previous_close = g["close"].shift(1)
    df["gap"] = df["open"] / previous_close - 1.0
    df["avg_volume20"] = g["volume"].transform(lambda x: x.rolling(20, min_periods=20).mean())
    df["abnormal_volume"] = df["volume"] / df["avg_volume20"] - 1.0
    df["avg_dollar_volume20"] = (df["close"] * df["volume"]).groupby(df["ticker"]).transform(
        lambda x: x.rolling(20, min_periods=20).mean()
    )
    return df


def rank_candidates(features: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Filter and rank each date cross-section using only objective inputs."""
    df = features.copy()
    eligible = (
        (df["close"] >= settings["min_price"])
        & (df["avg_dollar_volume20"] >= settings["min_avg_dollar_volume"])
        & (df["close"] > df["ma50"])
        & (df["ma50"] > df["ma200"])
    )
    df["eligible"] = eligible
    candidates = df.loc[eligible].copy()

    metric_map = {
        "momentum_63": "mom63",
        "momentum_126": "mom126",
        "breakout_63": "breakout63",
        "gap": "gap",
        "abnormal_volume": "abnormal_volume",
    }
    candidates["score"] = 0.0
    for weight_name, column in metric_map.items():
        percentile = candidates.groupby("date")[column].transform(_cross_sectional_percentile)
        candidates["score"] += float(settings["weights"][weight_name]) * percentile
    df["score"] = candidates["score"]
    return df.sort_values(["date", "score"], ascending=[True, False])
