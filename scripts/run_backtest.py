from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swing_backtest import add_features, rank_candidates, run_backtest
from swing_backtest.analytics import add_data_quality, performance_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Long-format OHLCV CSV")
    parser.add_argument("--config", default="config/strategy.yml")
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--benchmark", help="Optional CSV with date,close columns")
    parser.add_argument("--download-report", default=None)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as handle:
        settings = yaml.safe_load(handle)["strategy"]
    prices = pd.read_csv(args.input)
    ranked = rank_candidates(add_features(prices), settings)
    trades, equity = run_backtest(ranked, settings)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    trades.to_csv(output / "trades.csv", index=False)
    equity.to_csv(output / "equity.csv", index=False)
    benchmark = pd.read_csv(args.benchmark) if args.benchmark else None
    summary, annual = performance_report(equity, benchmark)
    summary.update({
        "trade_count": int(len(trades)),
        "win_rate": float((trades["return_net"] > 0).mean()) if len(trades) else 0.0,
    })
    if args.download_report:
        with open(args.download_report, encoding="utf-8") as handle:
            summary = add_data_quality(summary, json.load(handle))
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    annual.to_csv(output / "annual_metrics.csv", index=False)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
