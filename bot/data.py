"""Market data. yfinance (free, delayed) by default; synthetic data for tests."""
import os
import numpy as np
import pandas as pd


def _synthetic(symbol: str, days: int) -> pd.DataFrame:
    rng = np.random.default_rng(sum(map(ord, symbol)))
    n = max(days, 300)
    rets = rng.normal(0.0004, 0.015, n)
    close = 100 * np.exp(np.cumsum(rets))
    open_ = close * (1 + rng.normal(0, 0.004, n))
    high = np.maximum(open_, close) * (1 + abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * (1 - abs(rng.normal(0, 0.006, n)))
    idx = pd.bdate_range(start="2021-01-04", periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close}, index=idx)


def get_history(symbol: str, days: int = 800) -> pd.DataFrame:
    if os.environ.get("BOT_SYNTHETIC") == "1":
        return _synthetic(symbol, days)
    import yfinance as yf
    df = yf.Ticker(symbol).history(period=f"{max(days // 250 + 1, 2)}y", interval="1d", auto_adjust=True)
    if df is None or df.empty:
        raise RuntimeError(f"no data returned for {symbol}")
    df = df[["Open", "High", "Low", "Close"]].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def get_usdinr(default: float) -> float:
    if os.environ.get("BOT_SYNTHETIC") == "1":
        return default
    try:
        import yfinance as yf
        return float(yf.Ticker("INR=X").history(period="5d")["Close"].dropna().iloc[-1])
    except Exception:
        return default
