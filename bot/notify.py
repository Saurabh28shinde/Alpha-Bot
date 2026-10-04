"""Telegram out (alerts) and in (your 'bought'/'sold' replies). Falls back to print()."""
import os, re, requests


def _tok():
    return os.environ.get("TELEGRAM_BOT_TOKEN")


def _chat():
    return os.environ.get("TELEGRAM_CHAT_ID")


def send(text: str) -> bool:
    if not (_tok() and _chat()):
        print("[telegram not configured] " + text)
        return False
    r = requests.post(f"https://api.telegram.org/bot{_tok()}/sendMessage",
                      json={"chat_id": _chat(), "text": text}, timeout=20)
    return r.ok


def parse_command(text: str):
    """'bought ITC.NS 412.5 10' | 'sold ITC.NS 430' -> dict, else None"""
    m = re.match(r"^\s*/?(bought|sold)\s+(\S+)\s+([\d.]+)(?:\s+([\d.]+))?\s*$", text, re.I)
    if not m:
        return None
    return {"action": m.group(1).lower(), "symbol": m.group(2).upper(), "price": float(m.group(3)),
            "qty": float(m.group(4)) if m.group(4) else None}


def fetch_commands(offset: int):
    if not (_tok() and _chat()):
        return [], offset
    r = requests.get(f"https://api.telegram.org/bot{_tok()}/getUpdates",
                     params={"offset": offset + 1, "timeout": 0}, timeout=20)
    cmds, new_off = [], offset
    for u in r.json().get("result", []):
        new_off = max(new_off, u["update_id"])
        msg = u.get("message") or {}
        if str(msg.get("chat", {}).get("id")) != str(_chat()):   # ignore strangers
            continue
        c = parse_command(msg.get("text", ""))
        if c:
            cmds.append(c)
    return cmds, new_off
