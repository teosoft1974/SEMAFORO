"""Serie economiche dall'API FRED. Richiede FRED_API_KEY (in .env o nell'ambiente)."""
import os

import pandas as pd
from fredapi import Fred

DEFAULT_START = "2000-01-01"


def api_key_available() -> bool:
    return bool(os.environ.get("FRED_API_KEY"))


def fetch_series(series: dict[str, str], start: str = DEFAULT_START) -> pd.DataFrame:
    """series: {nome_logico: id_FRED}. Ritorna un DataFrame con una colonna per nome logico."""
    fred = Fred()  # legge FRED_API_KEY dall'ambiente
    out = {}
    for name, series_id in series.items():
        s = fred.get_series(series_id, observation_start=start)
        out[name] = s
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()
