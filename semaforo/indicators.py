"""Indicatori e punteggi dei componenti (formule: docs/BRIEF_v0.1.md §2-3).

Ogni funzione riceve serie giornaliere già allineate al calendario di borsa
e restituisce serie di punteggi 0-100 (alto = sano per il rischio,
alto = conveniente per l'opportunità).
"""
import numpy as np
import pandas as pd


def clip(s, lo=0, hi=100):
    return s.clip(lower=lo, upper=hi)


def combine(parts: dict[str, tuple[pd.Series, float]]) -> pd.Series:
    """Media pesata di serie 0-100, rinormalizzando i pesi dove qualche
    componente è NaN (es. breadth prima del 2022, VIX3M prima del 2010)."""
    df = pd.DataFrame({k: s for k, (s, _) in parts.items()})
    w = pd.Series({k: w for k, (_, w) in parts.items()})
    weights = df.notna() * w
    return (df * w).sum(axis=1, min_count=1) / weights.sum(axis=1)


def rolling_percentile(s: pd.Series, window: int, min_periods: int) -> pd.Series:
    return s.rolling(window, min_periods=min_periods).rank(pct=True) * 100


# ---------------------------------------------------------------- A. Trend

TREND_SUBWEIGHTS = {"state": 0.5, "momentum": 0.3, "distance": 0.2}


def trend_asset(close: pd.Series) -> pd.DataFrame:
    ma200 = close.rolling(200, min_periods=200).mean()
    slope = ma200 / ma200.shift(20) - 1
    mom_12m = close / close.shift(252) - 1
    dist_52w = close / close.rolling(252, min_periods=100).max() - 1

    above, rising = close > ma200, slope > 0
    state_score = pd.Series(
        np.select(
            [above & rising, ~above & rising, above & ~rising, ~above & ~rising],
            [100, 55, 50, 10], default=np.nan),
        index=close.index)
    state_score[ma200.isna()] = np.nan

    score = combine({
        "state": (state_score, TREND_SUBWEIGHTS["state"]),
        "momentum": (clip(50 + mom_12m * 250), TREND_SUBWEIGHTS["momentum"]),
        "distance": (clip(100 + dist_52w * 500), TREND_SUBWEIGHTS["distance"]),
    })
    return pd.DataFrame({"ma200": ma200, "ma200_slope_20d": slope, "mom_12m": mom_12m,
                         "dist_52w_high": dist_52w, "state_score": state_score,
                         "score": score})


def trend_component(closes: pd.DataFrame, asset_weights: dict[str, float]) -> pd.Series:
    return combine({t: (trend_asset(closes[t])["score"], w)
                    for t, w in asset_weights.items() if t in closes})


# ------------------------------------------------------------- B. Ampiezza

def breadth_component(pct200: pd.Series, rsp_spy: pd.Series, iwm_spy: pd.Series) -> pd.Series:
    ratio_score = lambda r: clip(50 + (r / r.shift(60) - 1) * 800)  # noqa: E731
    return combine({
        "pct200": (clip((pct200 - 20) / 60 * 100), 0.50),
        "rsp_spy": (ratio_score(rsp_spy), 0.25),
        "iwm_spy": (ratio_score(iwm_spy), 0.25),
    })


# ------------------------------------------------- C. Volatilità e sentiment

def vix_term_structure_score(ratio: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [ratio < 0.9, ratio <= 1.0, ratio > 1.0],
            [100, 100 - (ratio - 0.9) * 600, np.maximum(40 - (ratio - 1) * 400, 0)],
            default=np.nan),
        index=ratio.index)


def _velocity_score(s: pd.Series, horizon: int, scale: float) -> pd.Series:
    d = s.diff(horizon)
    z = (d - d.rolling(504, min_periods=252).mean()) / d.rolling(504, min_periods=252).std()
    return clip(50 - z * scale)


def vol_component(vix: pd.Series, vix3m: pd.Series) -> pd.Series:
    pctile = rolling_percentile(vix, 1260, 756)
    velocity = combine({"d5": (_velocity_score(vix, 5, 25), 0.5),
                        "d20": (_velocity_score(vix, 20, 25), 0.5)})
    return combine({
        "pctile": (100 - pctile, 0.40),
        "term": (vix_term_structure_score(vix / vix3m), 0.35),
        "velocity": (velocity, 0.25),
    })


# ------------------------------------------------------------------ D. Credito

def credit_component(oas: pd.Series, anfci: pd.Series) -> pd.Series:
    velocity = combine({"d20": (_velocity_score(oas, 20, 30), 0.5),
                        "d60": (_velocity_score(oas, 60, 30), 0.5)})
    return combine({
        "pctile": (100 - rolling_percentile(oas, 2520, 1260), 0.50),
        "velocity": (velocity, 0.25),
        "anfci": (clip(50 - anfci * 50), 0.25),
    })


# ----------------------------------------------------------- E. Macro e lavoro

def macro_component(sahm: pd.Series, claims_chg_13w: pd.Series, cfnai_ma3: pd.Series) -> pd.Series:
    sahm_score = pd.Series(
        np.select([sahm < 0.3, sahm < 0.5, sahm >= 0.5],
                  [100, 100 - (sahm - 0.3) / 0.2 * 70, 0], default=np.nan),
        index=sahm.index)
    claims_score = pd.Series(
        np.select([claims_chg_13w <= 0, claims_chg_13w <= 0.15, claims_chg_13w > 0.15],
                  [100, 100 - claims_chg_13w / 0.15 * 70, 10], default=np.nan),
        index=claims_chg_13w.index)
    cfnai_score = pd.Series(
        np.select([cfnai_ma3 >= 0, cfnai_ma3 >= -0.7, cfnai_ma3 < -0.7],
                  [100, 100 + cfnai_ma3 / 0.7 * 70, 0], default=np.nan),
        index=cfnai_ma3.index)
    return combine({"sahm": (sahm_score, 0.40), "claims": (claims_score, 0.30),
                    "cfnai": (cfnai_score, 0.30)})


# ------------------------------------------------- Componenti dell'opportunità

def drawdown_series(close: pd.Series) -> pd.Series:
    return 1 - close / close.rolling(252, min_periods=100).max()


def drawdown_component(dd_blend: pd.Series, floor: float, cap: float) -> pd.Series:
    return clip((dd_blend - floor) / (cap - floor) * 100)


def valuation_component(cape_monthly: pd.Series, real_10y: pd.Series,
                        cal: pd.DatetimeIndex) -> pd.DataFrame:
    """Percentile del CAPE dal 1950 (espandente: ogni data è confrontata solo
    con la storia già nota, niente lookahead) + excess yield vs Treasury reale."""
    cape_m = cape_monthly.dropna()
    cape_m = cape_m[cape_m.index >= "1950-01-01"]
    pctile_m = cape_m.expanding(min_periods=120).apply(
        lambda x: (x <= x[-1]).mean() * 100, raw=True)
    cape = cape_m.reindex(cal, method="ffill")
    pctile = pctile_m.reindex(cal, method="ffill")
    ey_pct = 100 / cape  # earnings yield in %
    ecy = ey_pct - real_10y
    score = combine({"cape_pctile": (100 - pctile, 0.60),
                     "excess_yield": (clip(ecy * 25), 0.40)})
    return pd.DataFrame({"cape": cape, "cape_pctile": pctile, "earnings_yield": ey_pct,
                         "real_10y": real_10y, "excess_yield": ecy, "score": score})


def fear_component(vix: pd.Series, vix3m: pd.Series, oas: pd.Series) -> pd.Series:
    # v0.1 senza put/call (fonte CBOE rimandata): i pesi si rinormalizzano
    ratio = vix / vix3m
    backwardation = pd.Series(
        np.select([ratio >= 1.05, ratio >= 1.0, ratio < 1.0], [100, 60, 0], default=np.nan),
        index=ratio.index)
    oas_spike = clip((oas.diff(60) - 0.5) / 1.0 * 100)  # +50bp->0, +150bp->100
    return combine({
        "vix_pctile": (rolling_percentile(vix, 1260, 756), 0.35),
        "backwardation": (backwardation, 0.25),
        "oas_spike": (oas_spike, 0.20),
    })


def stabilization_component(close: pd.Series, vix: pd.Series, oas: pd.Series,
                            dd_trigger: float) -> pd.Series:
    """Checklist di stabilizzazione (BRIEF §3.D), attiva solo dopo un drawdown
    di almeno dd_trigger negli ultimi 12 mesi."""
    dd = drawdown_series(close)
    active = dd.rolling(252, min_periods=100).max() >= dd_trigger
    ma50 = close.rolling(50, min_periods=50).mean()
    ma20 = close.rolling(20, min_periods=20).mean()
    checks = (
        (close > ma50).astype(float)
        + (ma20 > ma20.shift(10)).astype(float)
        + (vix <= 0.8 * vix.rolling(63, min_periods=40).max()).astype(float)
        + (oas <= oas.rolling(63, min_periods=40).max() - 0.40).astype(float)
    )
    return (checks * 25).where(active, 0.0)
