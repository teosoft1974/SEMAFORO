"""Breadth S&P 500: % di titoli sopra la propria MA200 e MA50.

Calcolata sui costituenti attuali (da Wikipedia) scaricati in batch da Yahoo.
Nota: usare i costituenti di oggi sul passato introduce survivorship bias, quindi
la storia serve come contesto, non per backtest rigorosi (vedi BRIEF §5).
"""
import io

import pandas as pd
import requests
import yfinance as yf

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
DEFAULT_START = "2022-01-01"  # ~1 anno di warmup MA200, breadth utile da ~2023
MIN_COVERAGE = 350  # minimo di titoli con dato valido perché il giorno conti


def fetch_constituents() -> list[str]:
    resp = requests.get(WIKI_URL, headers={"User-Agent": "semaforo/0.1"}, timeout=30)
    resp.raise_for_status()
    table = pd.read_html(io.StringIO(resp.text))[0]
    # Yahoo usa il trattino al posto del punto (BRK.B -> BRK-B)
    return sorted(table["Symbol"].str.replace(".", "-", regex=False))


def fetch_breadth(start: str = DEFAULT_START, chunk_size: int = 100) -> pd.DataFrame:
    tickers = fetch_constituents()
    closes = []
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        data = yf.download(chunk, start=start, auto_adjust=True, progress=False, threads=True)
        closes.append(data["Close"])
    prices = pd.concat(closes, axis=1).sort_index()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)

    ma200 = prices.rolling(200, min_periods=200).mean()
    ma50 = prices.rolling(50, min_periods=50).mean()
    valid = prices.notna() & ma200.notna()
    coverage = valid.sum(axis=1)
    pct200 = (prices > ma200)[valid].sum(axis=1) / coverage * 100
    pct50 = ((prices > ma50) & prices.notna() & ma50.notna()).sum(axis=1) / (
        (prices.notna() & ma50.notna()).sum(axis=1)) * 100

    out = pd.DataFrame({"pct_above_ma200": pct200, "pct_above_ma50": pct50,
                        "coverage": coverage})
    return out[out["coverage"] >= MIN_COVERAGE].drop(columns="coverage")
