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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Long-format OHLCV CSV")
    parser.add_argument("--config", default="config/strategy.yml")
    parser.add_argument("--output", default="outputs")
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
    summary = {
        "trade_count": int(len(trades)),
        "ending_equity": float(equity["equity"].iloc[-1]) if len(equity) else 1.0,
        "win_rate": float((trades["return_net"] > 0).mean()) if len(trades) else 0.0,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
