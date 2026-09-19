"""Rule-based swing backtest package."""

from .strategy import add_features, rank_candidates
from .backtest import run_backtest

__all__ = ["add_features", "rank_candidates", "run_backtest"]
