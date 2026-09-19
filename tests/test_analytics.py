import pandas as pd

from swing_backtest.analytics import add_data_quality, performance_report


def test_performance_report_has_annual_and_drawdown_metrics():
    equity = pd.DataFrame({
        "date": pd.bdate_range("2020-01-01", periods=4),
        "equity": [1.0, 1.1, 1.05, 1.2],
    })
    summary, annual = performance_report(equity)
    assert summary["ending_equity"] == 1.2
    assert summary["max_drawdown"] < 0
    assert list(annual["year"]) == [2020]


def test_data_quality_warns_for_missing_symbols():
    summary = add_data_quality({}, {
        "requested_tickers": 10,
        "downloaded_tickers": 8,
        "missing_tickers": ["A", "B"],
    })
    assert summary["data_quality"]["status"] == "warning"
    assert summary["data_quality"]["coverage_ratio"] == 0.8
