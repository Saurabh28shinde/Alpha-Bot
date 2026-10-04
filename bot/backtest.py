"""Honest check: how did this exact rule do on this instrument's own history?"""
import pandas as pd
from .indicators import add_all
from .signals import entry_ok, exit_reason


def run(df: pd.DataFrame, cfg: dict) -> dict:
    d = add_all(df).dropna(subset=["sma200"])
    trades, i, n = [], 0, len(d)
    while i < n - 2:
        row = d.iloc[i]
        if entry_ok(row, cfg):
            entry = float(d.iloc[i + 1]["Open"])          # enter next bar's open (no peeking)
            a = float(row["atr"])
            stop, target = entry - cfg["atr_stop_mult"] * a, entry + cfg["atr_target_mult"] * a
            last = min(i + 1 + cfg["max_hold_days"], n)
            exit_px, j = float(d.iloc[last - 1]["Close"]), last - 1
            for k in range(i + 1, last):
                why, px = exit_reason(d.iloc[k], cfg, stop, target)
                if why:
                    exit_px, j = float(px), k
                    break
            trades.append((exit_px - entry) / entry * 100)
            i = j + 1
        else:
            i += 1
    if not trades:
        return {"trades": 0}
    s = pd.Series(trades)
    return {"trades": len(s), "win_rate_pct": round(float((s > 0).mean() * 100), 1),
            "avg_return_pct": round(float(s.mean()), 2), "worst_pct": round(float(s.min()), 2)}
