"""Prezzi giornalieri da Yahoo Finance (chiusure aggiustate)."""
import time

import pandas as pd
import yfinance as yf

DEFAULT_START = "2005-01-01"


def fetch_closes(tickers: list[str], start: str = DEFAULT_START) -> pd.DataFrame:
    """DataFrame con una colonna per ticker, indice = date, valori = close aggiustati."""
    data = yf.download(tickers, start=start, auto_adjust=True, progress=False)
    closes = data["Close"]
    if isinstance(closes, pd.Series):  # ticker singolo
        closes = closes.to_frame(tickers[0])

    # yfinance a volte fallisce singoli ticker per lock transitori della sua cache:
    # riprova individualmente quelli tornati completamente vuoti
    for ticker in [t for t in tickers if t not in closes or closes[t].isna().all()]:
        for attempt in range(3):
            time.sleep(1 + attempt)
            retry = yf.download(ticker, start=start, auto_adjust=True, progress=False)
            if not retry.empty:
                closes[ticker] = retry["Close"].squeeze()
                break
        else:
            raise RuntimeError(f"Download fallito per {ticker} dopo 3 tentativi")

    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    return closes.sort_index()
