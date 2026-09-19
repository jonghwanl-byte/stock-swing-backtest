import pandas as pd

from swing_backtest.universe import mark_point_in_time_membership, reconstruct_intervals


def test_reconstructs_multiple_membership_spells():
    changes = pd.DataFrame({
        "date": ["2022-01-03", "2021-01-04", "2020-01-02"],
        "added": ["AAA", "BBB", "AAA"],
        "removed": ["BBB", "AAA", "CCC"],
    })
    result = reconstruct_intervals(["AAA"], changes, "2019-01-01")
    aaa = result.loc[result["ticker"] == "AAA"]
    assert len(aaa) == 2
    assert pd.Timestamp("2022-01-03") in set(aaa["start_date"])


def test_marks_membership_by_historical_date():
    prices = pd.DataFrame({
        "date": ["2020-01-01", "2020-01-02", "2020-01-03"],
        "ticker": ["AAA", "AAA", "AAA"],
        "close": [10, 11, 12],
    })
    intervals = pd.DataFrame({
        "ticker": ["AAA"],
        "start_date": [pd.Timestamp("2020-01-02")],
        "end_date": [pd.Timestamp("2020-01-02")],
    })
    marked = mark_point_in_time_membership(prices, intervals)
    assert marked["in_universe"].tolist() == [False, True, False]
    assert marked["universe_exit"].tolist() == [False, True, False]
