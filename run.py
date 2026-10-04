"""Entry point. `python run.py scan` is what the scheduler runs.  `python run.py backtest` shows the rule's history."""
import json, os, sys, datetime as dt, traceback
import yaml
from bot import data, ledger, notify, signals, backtest
from bot.indicators import add_all

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_JSON = os.path.join(ROOT, "docs", "state.json")


CFG = {}
FX = {"usd_inr": 88.0}


def fx_for(sym):
    return 1.0 if sym.endswith(".NS") else FX["usd_inr"]


def cfg():
    with open(os.path.join(ROOT, "config.yaml")) as f:
        return yaml.safe_load(f)


def utc():
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def process_inbox(led):
    cmds, led["tg_offset"] = notify.fetch_commands(led.get("tg_offset", 0))
    for c in cmds:
        if c["action"] == "bought":
            b = CFG["portfolio"]["symbol_bucket"].get(c["symbol"])
            if not b:
                notify.send(f"I don't track {c['symbol']}. Add it to config.yaml first.")
                continue
            ledger.open_position(led, c["symbol"], c["price"], c["qty"], b, fx_for(c["symbol"]))
            notify.send(f"Logged paper BUY {c['symbol']} @ {c['price']} in {CFG['portfolio']['buckets'][b]['label']}. Watching it for exits.")
        else:
            rec = ledger.close_position(led, c["symbol"], c["price"])
            if rec:
                notify.send(f"Logged SELL {c['symbol']} @ {c['price']} (P&L Rs {rec['pnl_inr']}). Actual {rec['actual_return_pct']}% vs predicted "
                            f"{rec['predicted_return_pct']}% (error {rec['error_pct']}%).")
            else:
                notify.send(f"No open paper position found for {c['symbol']}.")


def cooled_down(led, symbol, days):
    t = led["last_alert"].get(symbol)
    if not t:
        return True
    last = dt.datetime.fromisoformat(t.rstrip("Z"))
    return (dt.datetime.utcnow() - last).days >= days


def size(sig, led, c, px, latest):
    pc = c["portfolio"]
    bid = pc["symbol_bucket"].get(sig["symbol"])
    if not bid:
        return None
    b = pc["buckets"][bid]
    cash = next(x for x in ledger.portfolio(led, c, {}) if x["id"] == bid)["cash"]
    notional = min(b["capital"] * pc["risk_per_trade_pct"] / 100 / (sig["risk_pct"] / 100), b["capital"] * pc["max_position_pct"] / 100, cash)
    qty = notional / (px * fx_for(sig["symbol"]))
    qty = int(qty) if bid == "india_long_term" else round(qty, 4)
    if qty <= 0:
        return None
    sig.update(bucket=bid, bucket_label=b["label"], suggested_qty=qty, size_inr=round(qty * px * fx_for(sig["symbol"])))
    return sig


def scan():
    c = cfg()
    CFG.update(c)
    FX["usd_inr"] = data.get_usdinr(c["usd_inr_fallback"])
    rule = c["rule"]
    led = ledger.load()
    health, latest = {}, []
    try:
        process_inbox(led)
    except Exception as e:                      # inbox problems must never kill the scan
        print("inbox error:", e)

    for uid, u in c["universes"].items():
        h = {"label": u["label"], "stage": u["stage"], "last_run": utc(), "status": "not_connected", "ok": 0, "failed": []}
        if not u["enabled"] or not u["symbols"]:
            health[uid] = h
            continue
        h["status"] = "initialising"
        for sym in u["symbols"]:
            try:
                df = add_all(data.get_history(sym))
                last = df.iloc[-1]
                px = float(last["Close"])
                held = next((p for p in led["positions"] if p["symbol"] == sym), None)
                latest.append({"symbol": sym, "universe": uid, "price": round(px, 2), "rsi": round(float(last["rsi"]), 1),
                               "trend_up": bool(last["Close"] > last["sma200"]) if last["sma200"] == last["sma200"] else None,
                               "asof": str(df.index[-1].date())})
                if held:
                    why, _ = signals.exit_reason(last, rule, held["stop"] or -1e18, held["target"] or 1e18)
                    if why and cooled_down(led, "EXIT:" + sym, 1):
                        gain = (px - held["price"]) / held["price"] * 100
                        notify.send(f"EXIT {sym} ({why}). Last price {px:.2f}. Paper gain since your buy: {gain:+.2f}%. "
                                    f"Reply: sold {sym} <price>")
                        led["last_alert"]["EXIT:" + sym] = ledger.now()
                        led["exits"].append({"symbol": sym, "reason": why, "ts": ledger.now(), "decision_id": held["decision_id"]})
                else:
                    stats = backtest.run(df, rule)
                    sig = signals.make_signal(sym, df, rule, stats)
                    sig = size(sig, led, c, px, latest) if sig else None
                    if sig and cooled_down(led, sym, c["alert_cooldown_days"]):
                        ledger.record_signal(led, sig)
                        bt = (f"History of this rule on {sym}: {stats['trades']} trades, {stats['win_rate_pct']}% won, "
                              f"avg {stats['avg_return_pct']}%." if stats.get("trades") else "Not enough history to test this rule.")
                        notify.send(f"ENTER {sym} [{sig['decision_id']}] ~{sig['entry']}\nBucket: {sig['bucket_label']}. Suggested: {sig['suggested_qty']} units (about Rs {sig['size_inr']})\nStop {sig['stop']} (risk {sig['risk_pct']}%)\n"
                                    f"Target {sig['target']} (aim +{sig['predicted_return_pct']}%)\n{bt}\n"
                                    f"Reply: bought {sym} <price> <qty>")
                h["ok"] += 1
            except Exception as e:
                h["failed"].append(f"{sym}: {e}"[:120])
                traceback.print_exc()
        h["last_ok"] = utc() if h["ok"] else None
        h["status"] = "running" if h["ok"] and not h["failed"] else ("degraded" if h["ok"] else "error")
        health[uid] = h

    ledger.save(led)
    prices = {x["symbol"]: x["price"] for x in latest}
    pf = ledger.portfolio(led, c, prices)
    state = {"heartbeat": utc(), "portfolio": pf, "exits": led["exits"][-20:], "usd_inr": round(FX["usd_inr"], 2), "interval_min": c["scan_interval_minutes"], "health": health, "latest": latest,
             "signals": led["signals"][-30:], "positions": led["positions"], "accuracy": ledger.accuracy(led),
             "closed": led["closed"][-20:]}
    os.makedirs(os.path.dirname(STATE_JSON), exist_ok=True)
    with open(STATE_JSON, "w") as f:
        json.dump(state, f, indent=1)
    print("scan complete", {k: v["status"] for k, v in health.items()})


def bt():
    c = cfg()
    for u in c["universes"].values():
        for sym in (u["symbols"] if u["enabled"] else []):
            try:
                print(sym, backtest.run(data.get_history(sym, 2500), c["rule"]))
            except Exception as e:
                print(sym, "ERROR", e)


if __name__ == "__main__":
    {"scan": scan, "backtest": bt}.get(sys.argv[1] if len(sys.argv) > 1 else "scan", scan)()
