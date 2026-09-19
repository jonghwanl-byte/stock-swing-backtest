from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Position:
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    peak_price: float
    holding_days: int = 0


def run_backtest(ranked: pd.DataFrame, settings: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Equal-weight, next-close approximation suitable for initial research.

    This transparent MVP intentionally avoids an optimizer. Each position return is
    recorded net of round-trip transaction costs.
    """
    if ranked.empty:
        return pd.DataFrame(), pd.DataFrame(columns=["date", "equity"])

    all_rows = ranked.sort_values(["date", "ticker"])
    dates = sorted(all_rows["date"].unique())
    positions: dict[str, Position] = {}
    trades: list[dict] = []
    daily_returns: list[dict] = []
    previous_prices: dict[str, float] = {}
    cost = float(settings["transaction_cost_bps"]) / 10000.0

    for raw_date in dates:
        date = pd.Timestamp(raw_date)
        day = all_rows.loc[all_rows["date"] == raw_date].set_index("ticker")
        portfolio_returns = []

        for ticker in list(positions):
            if ticker not in day.index:
                continue
            row = day.loc[ticker]
            price = float(row["close"])
            pos = positions[ticker]
            if ticker in previous_prices:
                portfolio_returns.append(price / previous_prices[ticker] - 1.0)
            pos.holding_days += 1
            pos.peak_price = max(pos.peak_price, price)
            reason = None
            if price <= pos.entry_price * (1.0 - settings["stop_loss"]):
                reason = "stop_loss"
            elif price <= pos.peak_price * (1.0 - settings["trailing_stop"]):
                reason = "trailing_stop"
            elif pos.holding_days >= settings["max_holding_days"]:
                reason = "max_holding"
            elif price < float(row["ma50"]):
                reason = "trend_break"
            if reason:
                trades.append({
                    "ticker": ticker,
                    "entry_date": pos.entry_date,
                    "exit_date": date,
                    "entry_price": pos.entry_price,
                    "exit_price": price,
                    "holding_days": pos.holding_days,
                    "return_net": price / pos.entry_price - 1.0 - 2.0 * cost,
                    "exit_reason": reason,
                })
                del positions[ticker]

        if date.weekday() == int(settings["rebalance_weekday"]):
            capacity = int(settings["max_positions"]) - len(positions)
            if capacity > 0:
                candidates = day.loc[
                    day["eligible"] & ~day.index.isin(positions)
                ].sort_values("score", ascending=False)
                for ticker, row in candidates.head(capacity).iterrows():
                    price = float(row["close"])
                    positions[ticker] = Position(ticker, date, price, price)

        for ticker in positions:
            if ticker in day.index:
                previous_prices[ticker] = float(day.loc[ticker, "close"])
        daily_returns.append({
            "date": date,
            "return": sum(portfolio_returns) / len(portfolio_returns) if portfolio_returns else 0.0,
        })

    returns = pd.DataFrame(daily_returns).drop_duplicates("date").sort_values("date")
    returns["equity"] = (1.0 + returns["return"]).cumprod()
    return pd.DataFrame(trades), returns[["date", "equity"]]
