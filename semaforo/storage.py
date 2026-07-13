"""Storage locale: un file parquet per dataset in data/raw/."""
import pandas as pd

from .config import RAW_DIR


def save(name: str, df: pd.DataFrame) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(RAW_DIR / f"{name}.parquet")


def load(name: str) -> pd.DataFrame | None:
    path = RAW_DIR / f"{name}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


def describe() -> pd.DataFrame:
    """Riepilogo dei dataset presenti: righe, colonne, intervallo date."""
    rows = []
    if RAW_DIR.exists():
        for path in sorted(RAW_DIR.glob("*.parquet")):
            df = pd.read_parquet(path)
            rows.append({
                "dataset": path.stem,
                "righe": len(df),
                "colonne": len(df.columns),
                "da": df.index.min(),
                "a": df.index.max(),
            })
    return pd.DataFrame(rows)
