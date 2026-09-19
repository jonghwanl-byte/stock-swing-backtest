from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swing_backtest import add_features, rank_candidates, run_backtest
from swing_backtest.analytics import performance_report


VARIANTS = {
    "A_late_trend": {
        "entry_model": "late_trend",
        "feature_weights": {
            "momentum_63": 0.30,
            "momentum_126": 0.20,
            "breakout_63": 0.20,
            "gap": 0.15,
            "abnormal_volume": 0.15,
        },
    },
    "B_no_noise": {
        "entry_model": "no_noise",
        "feature_weights": {
            "momentum_63": 0.45,
            "momentum_126": 0.30,
            "breakout_63": 0.25,
        },
    },
    "C_early": {
        "entry_model": "early",
        "feature_weights": {
            "momentum_20": 0.35,
            "acceleration": 0.35,
            "breakout_20": 0.30,
        },
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare objective entry models on the same point-in-time data")
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", default="config/strategy.yml")
    parser.add_argument("--output", default="outputs/model_comparison.csv")
    parser.add_argument("--oos-start", default="2023-01-01")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as handle:
        base = yaml.safe_load(handle)["strategy"]
    features = add_features(pd.read_csv(args.input))

    rows: list[dict] = []
    for name, override in VARIANTS.items():
      for top_n in (100, 200, 300, 400):
        settings = copy.deepcopy(base)
        settings.update(override)
        settings["top_liquidity_n"] = top_n
        ranked = rank_candidates(features, settings)
        trades, equity = run_backtest(ranked, settings)
        summary, _ = performance_report(equity)
        oos_prices = features.loc[features["date"] >= pd.Timestamp(args.oos_start)]
        oos_ranked = rank_candidates(oos_prices, settings)
        oos_trades, oos_equity = run_backtest(oos_ranked, settings)
        oos_summary, _ = performance_report(oos_equity)
        rows.append({
            "model": name,
            "top_liquidity_n": top_n,
            "entry_model": settings["entry_model"],
            "trade_count": int(len(trades)),
            "win_rate": float((trades["return_net"] > 0).mean()) if len(trades) else 0.0,
            "cagr": summary["cagr"],
            "sharpe_0rf": summary["sharpe_0rf"],
            "annualized_volatility": summary["annualized_volatility"],
            "max_drawdown": summary["max_drawdown"],
            "ending_equity": summary["ending_equity"],
            "start_date": summary["start_date"],
            "end_date": summary["end_date"],
            "oos_start": args.oos_start,
            "oos_cagr": oos_summary["cagr"],
            "oos_sharpe_0rf": oos_summary["sharpe_0rf"],
            "oos_max_drawdown": oos_summary["max_drawdown"],
            "oos_trade_count": int(len(oos_trades)),
        })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(rows).sort_values(["oos_sharpe_0rf", "sharpe_0rf"], ascending=False)
    result.to_csv(output, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
