"""Serie storica mensile di Shiller (prezzi, utili, CAPE) da ie_data.xls.

Shiller non aggiorna più il file su econ.yale.edu (fermo a settembre 2023):
la fonte corrente è shillerdata.com, dove il link al file cambia ad ogni
aggiornamento — lo ricaviamo dalla homepage. Yale resta come fallback.
"""
import io
import re
import warnings

import pandas as pd
import requests

HOMEPAGE = "https://shillerdata.com/"
FALLBACK_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
HEADERS = {"User-Agent": "Mozilla/5.0 (semaforo/0.1)"}


def _current_url() -> str:
    resp = requests.get(HOMEPAGE, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    m = re.search(r'href="([^"]*ie_data[^"]*\.xls[^"]*)"', resp.text)
    if not m:
        raise RuntimeError("Link a ie_data.xls non trovato su shillerdata.com")
    url = m.group(1)
    return url if url.startswith("http") else "https:" + url


def fetch_shiller() -> pd.DataFrame:
    errors = []
    for get_url in (_current_url, lambda: FALLBACK_URL):
        try:
            url = get_url()
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            df = _parse(resp.content)
            age_days = (pd.Timestamp.now() - df.index.max()).days
            if age_days > 180:
                warnings.warn(f"Dati Shiller vecchi di {age_days} giorni ({url})")
            return df
        except Exception as e:  # noqa: BLE001 - proviamo la fonte successiva
            errors.append(str(e))
    raise RuntimeError(f"Download dati Shiller fallito: {errors}")


def _parse(content: bytes) -> pd.DataFrame:
    # Il foglio "Data" ha 7 righe di intestazione libera; le colonne utili sono
    # per posizione: 0=Date (es. 2020.01), 1=P, 2=D, 3=E, 4=CPI, 6=GS10, 12=CAPE
    raw = pd.read_excel(io.BytesIO(content), sheet_name="Data", skiprows=7, header=0)
    df = raw.iloc[:, [0, 1, 2, 3, 4, 6, 12]].copy()
    df.columns = ["date_frac", "price", "dividend", "earnings", "cpi", "gs10", "cape"]
    df = df.dropna(subset=["date_frac"])
    df["date_frac"] = df["date_frac"].astype(float)
    year = df["date_frac"].astype(int)
    month = ((df["date_frac"] - year) * 100).round().astype(int).clip(1, 12)
    df.index = pd.to_datetime({"year": year, "month": month, "day": 1})
    df = df.drop(columns="date_frac").apply(pd.to_numeric, errors="coerce")
    df = df[df["cape"].notna() | df["price"].notna()]
    # sanity check: il CAPE storico è sempre stato fra ~4 e ~50
    cape = df["cape"].dropna()
    if cape.empty or not (3 < cape.min() and cape.max() < 60):
        raise RuntimeError("Parsing ie_data.xls sospetto: valori CAPE fuori range")
    return df.sort_index()
