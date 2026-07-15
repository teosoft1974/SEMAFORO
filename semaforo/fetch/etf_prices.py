"""Ultima chiusura degli ETF del dossier (quotazioni in EUR), per la dashboard.

Pubblicato in data/etf_prices.json e abbinato per ISIN: serve al conteggio
delle quote intere quando il foglio Profilo non fornisce un prezzo live.
"""
from datetime import date

import pandas as pd
import yfinance as yf


def fetch_etf_prices(mapping: dict[str, str]) -> dict:
    """mapping: {ISIN: ticker Yahoo}. Ritorna il dict pronto per il JSON."""
    tickers = list(mapping.values())
    data = yf.download(tickers, period="5d", auto_adjust=False, progress=False)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(tickers[0])
    prices = {}
    for isin, ticker in mapping.items():
        if ticker not in data:
            continue
        s = data[ticker].dropna()
        if s.empty:
            continue
        prices[isin] = {"ticker": ticker, "price": round(float(s.iloc[-1]), 4),
                        "date": str(s.index[-1].date())}
    return {"updated": str(date.today()), "prices": prices}
