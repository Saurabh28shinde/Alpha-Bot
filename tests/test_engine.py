import os
os.environ["BOT_SYNTHETIC"] = "1"
import pandas as pd
from bot import data, backtest, ledger, notify
from bot.indicators import add_all, rsi

RULE = {"atr_stop_mult": 2.0, "atr_target_mult": 3.0, "max_hold_days": 30, "rsi_entry_max": 45, "rsi_exit_min": 75}


def test_rsi_bounds():
    r = rsi(data.get_history("X")["Close"]).dropna()
    assert r.between(0, 100).all()


def test_indicators_no_lookahead():
    df = data.get_history("ITC.NS")
    full = add_all(df)
    part = add_all(df.iloc[:-50])
    assert abs(full["rsi"].iloc[-51] - part["rsi"].iloc[-1]) < 1e-9


def test_backtest_runs():
    out = backtest.run(data.get_history("BTC-USD", 2500), RULE)
    assert "trades" in out


def test_ledger_roundtrip(tmp_path):
    led = ledger.load(str(tmp_path / "l.json"))
    ledger.record_signal(led, {"symbol": "ITC.NS", "decision_id": "D-1", "stop": 90, "target": 110, "predicted_return_pct": 5.0})
    ledger.open_position(led, "ITC.NS", 100.0, 10, "india_long_term", 1.0)
    rec = ledger.close_position(led, "ITC.NS", 103.0)
    assert rec["pnl_inr"] == 30 and rec["actual_return_pct"] == 3.0 and rec["error_pct"] == -2.0
    assert ledger.accuracy(led)["closed_trades"] == 1


def test_command_parser():
    assert notify.parse_command("bought itc.ns 412.5 10") == {"action": "bought", "symbol": "ITC.NS", "price": 412.5, "qty": 10.0}
    assert notify.parse_command("/sold BTC-USD 60000")["action"] == "sold"
    assert notify.parse_command("hello") is None
