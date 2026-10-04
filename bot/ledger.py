"""Paper ledger: signal -> your manual action -> outcome -> prediction error."""
import json, os, datetime as dt

PATH = os.path.join(os.path.dirname(__file__), "..", "state", "ledger.json")


def now():
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def load(path=PATH):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"signals": [], "positions": [], "closed": [], "last_alert": {}, "tg_offset": 0}


def save(led, path=PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(led, f, indent=1)


def record_signal(led, sig):
    led["signals"].append({**sig, "ts": now()})
    led["last_alert"][sig["symbol"]] = now()


def open_position(led, symbol, price, qty=None):
    sig = next((s for s in reversed(led["signals"]) if s["symbol"] == symbol), None)
    led["positions"].append({"symbol": symbol, "price": price, "qty": qty, "ts": now(),
                             "stop": sig["stop"] if sig else None, "target": sig["target"] if sig else None,
                             "predicted_return_pct": sig["predicted_return_pct"] if sig else None})


def close_position(led, symbol, price):
    pos = next((p for p in led["positions"] if p["symbol"] == symbol), None)
    if not pos:
        return None
    led["positions"].remove(pos)
    actual = round((price - pos["price"]) / pos["price"] * 100, 2)
    pred = pos.get("predicted_return_pct")
    rec = {**pos, "exit_price": price, "exit_ts": now(), "actual_return_pct": actual,
           "error_pct": None if pred is None else round(actual - pred, 2)}
    led["closed"].append(rec)
    return rec


def accuracy(led):
    c = led["closed"]
    if not c:
        return {"closed_trades": 0}
    wins = sum(1 for x in c if x["actual_return_pct"] > 0)
    errs = [abs(x["error_pct"]) for x in c if x["error_pct"] is not None]
    return {"closed_trades": len(c), "win_rate_pct": round(wins / len(c) * 100, 1),
            "avg_actual_return_pct": round(sum(x["actual_return_pct"] for x in c) / len(c), 2),
            "mean_abs_prediction_error_pct": round(sum(errs) / len(errs), 2) if errs else None}
