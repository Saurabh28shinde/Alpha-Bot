"""Paper ledger + Rs 6 lakh bucket accounting. Every decision gets a unique ID."""
import json, os, datetime as dt

PATH = os.path.join(os.path.dirname(__file__), "..", "state", "ledger.json")


def now():
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def load(path=PATH):
    led = json.load(open(path)) if os.path.exists(path) else {}
    for k, v in {"signals": [], "positions": [], "closed": [], "exits": [], "last_alert": {}, "tg_offset": 0, "seq": 0}.items():
        led.setdefault(k, v)
    return led


def save(led, path=PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(led, open(path, "w"), indent=1)


def new_id(led):
    led["seq"] += 1
    return f"D-{dt.datetime.utcnow():%y%m%d}-{led['seq']:03d}"


def record_signal(led, sig):
    sig["decision_id"] = new_id(led)
    led["signals"].append({**sig, "ts": now()})
    led["last_alert"][sig["symbol"]] = now()


def open_position(led, symbol, price, qty, bucket, fx):
    sig = next((s for s in reversed(led["signals"]) if s["symbol"] == symbol), None)
    qty = qty if qty is not None else (sig or {}).get("suggested_qty")
    led["positions"].append({"symbol": symbol, "price": price, "qty": qty, "bucket": bucket, "fx": fx, "ts": now(),
                             "decision_id": sig["decision_id"] if sig else new_id(led),
                             "stop": sig["stop"] if sig else None, "target": sig["target"] if sig else None,
                             "predicted_return_pct": sig["predicted_return_pct"] if sig else None})


def close_position(led, symbol, price):
    pos = next((p for p in led["positions"] if p["symbol"] == symbol), None)
    if not pos:
        return None
    led["positions"].remove(pos)
    actual = round((price - pos["price"]) / pos["price"] * 100, 2)
    pred = pos.get("predicted_return_pct")
    pnl = round((price - pos["price"]) * (pos["qty"] or 0) * pos["fx"])
    rec = {**pos, "exit_price": price, "exit_ts": now(), "actual_return_pct": actual, "pnl_inr": pnl,
           "error_pct": None if pred is None else round(actual - pred, 2)}
    led["closed"].append(rec)
    return rec


def accuracy(led):
    c = led["closed"]
    if not c:
        return {"closed_trades": 0}
    errs = [abs(x["error_pct"]) for x in c if x["error_pct"] is not None]
    return {"closed_trades": len(c), "win_rate_pct": round(sum(x["actual_return_pct"] > 0 for x in c) / len(c) * 100, 1),
            "avg_actual_return_pct": round(sum(x["actual_return_pct"] for x in c) / len(c), 2),
            "mean_abs_prediction_error_pct": round(sum(errs) / len(errs), 2) if errs else None}


def portfolio(led, cfg, prices):
    out = []
    for bid, b in cfg["portfolio"]["buckets"].items():
        pos = [p for p in led["positions"] if p.get("bucket") == bid]
        dep = sum(p["price"] * (p["qty"] or 0) * p["fx"] for p in pos)
        real = sum(c.get("pnl_inr", 0) for c in led["closed"] if c.get("bucket") == bid)
        unreal = sum((prices.get(p["symbol"], p["price"]) - p["price"]) * (p["qty"] or 0) * p["fx"] for p in pos)
        out.append({"id": bid, "label": b["label"], "capital": b["capital"], "active": b.get("active", True),
                    "deployed": round(dep), "cash": round(b["capital"] + real - dep), "realised": round(real),
                    "unrealised": round(unreal), "positions": len(pos)})
    return out
