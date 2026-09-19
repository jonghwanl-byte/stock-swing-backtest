import numpy as np
import pandas as pd

from swing_backtest.strategy import add_features, rank_candidates


def test_feature_and_ranking_pipeline():
    dates = pd.bdate_range("2024-01-01", periods=230)
    frames = []
    for number, ticker in enumerate(["AAA", "BBB"]):
        close = np.linspace(20 + number, 40 + 2 * number, len(dates))
        frames.append(pd.DataFrame({
            "date": dates,
            "ticker": ticker,
            "open": close * 1.001,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 2_000_000,
        }))
    settings = {
        "min_price": 5,
        "min_avg_dollar_volume": 1_000_000,
        "weights": {
            "momentum_63": .3, "momentum_126": .2, "breakout_63": .2,
            "gap": .15, "abnormal_volume": .15,
        },
    }
    ranked = rank_candidates(add_features(pd.concat(frames)), settings)
    assert not ranked.empty
    assert ranked["score"].between(0, 1).all()


def test_missing_column_is_rejected():
    try:
        add_features(pd.DataFrame({"date": []}))
    except ValueError as exc:
        assert "Missing columns" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_early_model_and_top_liquidity_limit():
    dates = pd.bdate_range("2024-01-01", periods=240)
    frames = []
    for number, ticker in enumerate(["AAA", "BBB", "CCC"]):
        close = np.linspace(20 + number, 45 + number, len(dates))
        frames.append(pd.DataFrame({
            "date": dates, "ticker": ticker,
            "open": close, "high": close * 1.01, "low": close * .99,
            "close": close, "volume": (3 - number) * 2_000_000,
        }))
    settings = {
        "min_price": 5, "min_avg_dollar_volume": 1_000_000,
        "top_liquidity_n": 1, "entry_model": "early",
        "feature_weights": {"momentum_20": .35, "acceleration": .35, "breakout_20": .30},
    }
    ranked = rank_candidates(add_features(pd.concat(frames)), settings)
    assert not ranked.empty
    assert ranked.loc[ranked["eligible"]].groupby("date").size().max() <= 1
