"""One transparent rule: buy pullbacks inside an uptrend. Every number is explainable."""
import pandas as pd


def entry_ok(row, cfg) -> bool:
    if pd.isna(row["sma200"]) or pd.isna(row["rsi"]):
        return False
    uptrend = row["Close"] > row["sma200"] and row["sma50"] > row["sma200"]
    pullback = row["rsi"] <= cfg["rsi_entry_max"]
    return bool(uptrend and pullback)


def exit_reason(row, cfg, stop, target):
    if row["Low"] <= stop:
        return "stop", stop
    if row["High"] >= target:
        return "target", target
    if row["rsi"] >= cfg["rsi_exit_min"]:
        return "rsi_exit", row["Close"]
    if row["Close"] < row["sma50"]:
        return "trend_break", row["Close"]
    return None, None


def make_signal(symbol, df, cfg, stats):
    row = df.iloc[-1]
    if not entry_ok(row, cfg):
        return None
    entry = float(row["Close"])
    a = float(row["atr"])
    stop = entry - cfg["atr_stop_mult"] * a
    target = entry + cfg["atr_target_mult"] * a
    return {
        "symbol": symbol, "entry": round(entry, 2), "stop": round(stop, 2), "target": round(target, 2),
        "predicted_return_pct": round((target - entry) / entry * 100, 2),
        "risk_pct": round((entry - stop) / entry * 100, 2),
        "rsi": round(float(row["rsi"]), 1),
        "backtest": stats,
    }
