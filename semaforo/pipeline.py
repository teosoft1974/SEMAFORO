"""Orchestrazione: dati grezzi -> punteggi giornalieri -> latest.json + history.json."""
import json

import numpy as np
import pandas as pd

from . import indicators as ind
from . import scoring, storage
from .config import DATA_DIR, load_config


def _num(v, digits=4):
    return None if v is None or pd.isna(v) else round(float(v), digits)


def build() -> pd.DataFrame:
    """Calcola le serie giornaliere complete di componenti, punteggi ed etichette."""
    cfg = load_config()
    prices = storage.load("prices")
    fred = storage.load("fred")
    breadth = storage.load("breadth")
    shiller = storage.load("shiller")
    if prices is None or fred is None or shiller is None:
        raise RuntimeError("Dati mancanti: esegui prima `python -m semaforo backfill`")

    cal = prices.index[prices["SPY"].notna()]  # calendario di borsa NYSE
    closes = prices.reindex(cal).ffill()

    def daily(s: pd.Series) -> pd.Series:
        return s.dropna().reindex(cal, method="ffill")

    vix, vix3m = closes["^VIX"], daily(prices["^VIX3M"])
    oas, anfci = daily(fred["hy_oas"]), daily(fred["anfci"])
    claims = fred["claims_4w"].dropna()

    comp = {
        "trend": ind.trend_component(closes, cfg["risk"]["trend_asset_weights"]),
        "breadth": ind.breadth_component(
            daily(breadth["pct_above_ma200"]) if breadth is not None
            else pd.Series(np.nan, index=cal),
            closes["RSP"] / closes["SPY"], closes["IWM"] / closes["SPY"]),
        "vol": ind.vol_component(vix, vix3m),
        "credit": ind.credit_component(oas, anfci),
        "macro": ind.macro_component(
            daily(fred["sahm"]), daily(claims / claims.shift(13) - 1),
            daily(fred["cfnai_ma3"])),
    }
    risk_score = scoring.weighted_score(comp, cfg["risk"]["weights"])
    c = cfg["risk"]["colors"]
    h = cfg["risk"]["hysteresis"]
    risk_label = scoring.labels_with_hysteresis(
        risk_score, [c["yellow_min"], c["green_min"]], scoring.RISK_LABELS,
        h["min_margin"], h["min_days"])

    o = cfg["opportunity"]
    dd_blend = pd.concat([ind.drawdown_series(closes["SPY"]),
                          ind.drawdown_series(closes["ACWI"])], axis=1).mean(axis=1)
    valuation = ind.valuation_component(shiller["cape"], daily(fred["real_10y"]), cal)
    opp_comp = {
        "drawdown": ind.drawdown_component(dd_blend, o["drawdown"]["floor"],
                                           o["drawdown"]["cap"]),
        "valuation": valuation["score"],
        "fear": ind.fear_component(vix, vix3m, oas),
        "stabilization": ind.stabilization_component(
            closes["SPY"], vix, oas, o["stabilization"]["dd_trigger"]),
    }
    opp_score = scoring.weighted_score(opp_comp, o["weights"])
    lab = o["labels"]
    opp_label = scoring.labels_with_hysteresis(
        opp_score,
        [lab["neutrale_min"], lab["interessante_min"], lab["fortemente_interessante_min"]],
        scoring.OPP_LABELS, h["min_margin"], h["min_days"])

    fg = scoring.fear_greed(comp["vol"], comp["breadth"], comp["credit"], comp["trend"],
                            cfg["fear_greed"]["weights"])
    entry = scoring.entry_window(opp_score, risk_label,
                                 lab[cfg["entry_window"]["opportunity_min_label"] + "_min"],
                                 cfg["entry_window"]["risk_lookback_days"])

    df = pd.DataFrame({"risk_score": risk_score, "risk_label": risk_label,
                       "opp_score": opp_score, "opp_label": opp_label,
                       "fear_greed": fg, "entry_window": entry})
    for name, s in comp.items():
        df[f"risk_{name}"] = s
    for name, s in opp_comp.items():
        df[f"opp_{name}"] = s
    return df[df["risk_score"].notna()]


def export(df: pd.DataFrame) -> dict:
    """Scrive data/latest.json e data/history.json; ritorna lo snapshot."""
    cfg = load_config()
    last = df.iloc[-1]
    date = df.index[-1]
    lookback = cfg["entry_window"]["risk_lookback_days"]

    snapshot = {
        "schema_version": "0.1",
        "date": str(date.date()),
        "risk": {
            "score": _num(last["risk_score"], 1),
            "color": last["risk_label"],
            "color_prev_10d": df["risk_label"].iloc[-1 - lookback]
            if len(df) > lookback else None,
            "components": {k: {"score": _num(last[f"risk_{k}"], 1), "weight": w}
                           for k, w in cfg["risk"]["weights"].items()},
        },
        "opportunity": {
            "score": _num(last["opp_score"], 1),
            "label": last["opp_label"],
            "components": {k: {"score": _num(last[f"opp_{k}"], 1), "weight": w}
                           for k, w in cfg["opportunity"]["weights"].items()},
        },
        "entry_window": bool(last["entry_window"]),
        "fear_greed": {"score": _num(last["fear_greed"], 1)},
        "indicators": _indicators_block(),
        "data_quality": _data_quality(),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "latest.json", "w") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    hist = {
        "dates": [str(d.date()) for d in df.index],
        "risk_score": [_num(v, 1) for v in df["risk_score"]],
        "risk_color": list(df["risk_label"]),
        "opp_score": [_num(v, 1) for v in df["opp_score"]],
        "opp_label": list(df["opp_label"]),
        "fear_greed": [_num(v, 1) for v in df["fear_greed"]],
    }
    with open(DATA_DIR / "history.json", "w") as f:
        json.dump(hist, f, ensure_ascii=False)
    return snapshot


_STATE_NAMES = {100: "sano", 55: "deterioramento iniziale",
                50: "recupero", 10: "ribasso consolidato"}


def _indicators_block() -> dict:
    cfg = load_config()
    prices = storage.load("prices")
    fred = storage.load("fred")
    breadth = storage.load("breadth")
    shiller = storage.load("shiller")
    cal = prices.index[prices["SPY"].notna()]
    closes = prices.reindex(cal).ffill()

    def daily(s):
        return s.dropna().reindex(cal, method="ffill")

    block = {}
    for t in cfg["risk"]["trend_asset_weights"]:
        ta = ind.trend_asset(closes[t]).iloc[-1]
        block[t] = {
            "close": _num(closes[t].iloc[-1], 2), "ma200": _num(ta["ma200"], 2),
            "ma200_slope_20d": _num(ta["ma200_slope_20d"]),
            "mom_12m": _num(ta["mom_12m"]), "dist_52w_high": _num(ta["dist_52w_high"]),
            "trend_state": _STATE_NAMES.get(ta["state_score"]),
        }

    rsp_spy = closes["RSP"] / closes["SPY"]
    iwm_spy = closes["IWM"] / closes["SPY"]
    block["ratios"] = {
        "rsp_spy": _num(rsp_spy.iloc[-1]), "rsp_spy_chg_60d": _num(rsp_spy.iloc[-1] / rsp_spy.iloc[-61] - 1),
        "iwm_spy": _num(iwm_spy.iloc[-1]), "iwm_spy_chg_60d": _num(iwm_spy.iloc[-1] / iwm_spy.iloc[-61] - 1),
        "hyg_ief": _num((closes["HYG"] / closes["IEF"]).iloc[-1]),
    }
    if breadth is not None:
        block["breadth"] = {k: _num(breadth[k].iloc[-1], 1)
                            for k in ("pct_above_ma200", "pct_above_ma50")}

    vix, vix3m = closes["^VIX"], daily(prices["^VIX3M"])
    block["vix"] = {
        "level": _num(vix.iloc[-1], 2),
        "pctile_5y": _num(ind.rolling_percentile(vix, 1260, 756).iloc[-1], 1),
        "vix_vix3m": _num((vix / vix3m).iloc[-1], 3),
        "chg_5d": _num(vix.diff(5).iloc[-1], 2), "chg_20d": _num(vix.diff(20).iloc[-1], 2),
    }

    oas = daily(fred["hy_oas"])
    block["credit"] = {
        "hy_oas": _num(oas.iloc[-1], 2),
        "oas_chg_20d_bp": _num(oas.diff(20).iloc[-1] * 100, 0),
        "oas_chg_60d_bp": _num(oas.diff(60).iloc[-1] * 100, 0),
        "oas_pctile_10y": _num(ind.rolling_percentile(oas, 2520, 1260).iloc[-1], 1),
        "anfci": _num(daily(fred["anfci"]).iloc[-1], 3),
    }

    claims = fred["claims_4w"].dropna()
    block["macro"] = {
        "sahm": _num(fred["sahm"].dropna().iloc[-1], 2),
        "claims_4w": _num(claims.iloc[-1], 0),
        "claims_chg_13w": _num(claims.iloc[-1] / claims.iloc[-14] - 1),
        "claims_chg_52w": _num(claims.iloc[-1] / claims.iloc[-53] - 1),
        "cfnai_ma3": _num(fred["cfnai_ma3"].dropna().iloc[-1], 2),
        "t10y3m": _num(fred["t10y3m"].dropna().iloc[-1], 2),
    }

    pce = fred["core_pce"].dropna()
    yoy = pce.iloc[-1] / pce.iloc[-13] - 1
    fed_funds = fred["fed_funds"].dropna().iloc[-1]
    block["inflation"] = {
        "core_pce_yoy": _num(yoy),
        "core_pce_3m_ann": _num((pce.iloc[-1] / pce.iloc[-4]) ** 4 - 1),
        "fed_funds": _num(fed_funds, 2),
        "real_rate": _num(fed_funds / 100 - yoy),
    }

    val = ind.valuation_component(shiller["cape"], daily(fred["real_10y"]), cal).iloc[-1]
    block["valuation"] = {k: _num(val[k]) for k in
                          ("cape", "cape_pctile", "earnings_yield", "real_10y", "excess_yield")}
    return block


def _data_quality() -> dict:
    today = pd.Timestamp.now().normalize()
    stale, warnings = [], []
    checks = [("prices", storage.load("prices").index.max(), 5),
              ("fred", storage.load("fred").index.max(), 7),
              ("shiller", storage.load("shiller").index.max(), 75)]
    b = storage.load("breadth")
    if b is not None:
        checks.append(("breadth", b.index.max(), 5))
    else:
        warnings.append("breadth assente: peso riassegnato a RSP/SPY e IWM/SPY")
    for name, last, max_age in checks:
        if (today - last).days > max_age:
            stale.append(f"{name} (ultimo dato {last.date()})")
    return {"stale_series": stale, "warnings": warnings}
