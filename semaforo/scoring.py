"""Aggregazione dei componenti in punteggi e colori (docs/BRIEF_v0.1.md §1-3)."""
import pandas as pd

from .indicators import combine

RISK_LABELS = ["rosso", "giallo", "verde"]
OPP_LABELS = ["caro", "neutrale", "interessante", "fortemente interessante"]


def weighted_score(components: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    return combine({k: (components[k], weights[k]) for k in weights})


def labels_with_hysteresis(score: pd.Series, thresholds: list[float], labels: list[str],
                           min_margin: float, min_days: int) -> pd.Series:
    """Assegna etichette ordinate (labels[i] vale da thresholds[i-1] in su) con
    anti-sfarfallio: si cambia etichetta solo superando la soglia di almeno
    min_margin punti, oppure dopo min_days sedute consecutive oltre soglia."""

    def raw_rank(v: float) -> int:
        rank = 0
        for t in thresholds:
            if v >= t:
                rank += 1
        return rank

    out, current, streak = [], None, 0
    for v in score:
        if pd.isna(v):
            out.append(None if current is None else labels[current])
            continue
        cand = raw_rank(v)
        if current is None:
            current = cand
        elif cand != current:
            # soglia rilevante: quella appena sopra il punteggio di partenza
            # (salendo) o appena sotto (scendendo)
            boundary = thresholds[current] if cand > current else thresholds[current - 1]
            streak += 1
            if abs(v - boundary) >= min_margin or streak >= min_days:
                current, streak = cand, 0
        else:
            streak = 0
        out.append(labels[current])
    return pd.Series(out, index=score.index, dtype="object")


def fear_greed(vol: pd.Series, breadth: pd.Series, credit: pd.Series,
               momentum: pd.Series, weights: dict[str, float]) -> pd.Series:
    """Fear&Greed proprietario (BRIEF §3): 0 = paura, 100 = avidità.
    v0.1 senza put/call; i pesi si rinormalizzano automaticamente."""
    return combine({
        "vix": (vol, weights["vix"]),
        "breadth": (breadth, weights["breadth"]),
        "credit": (credit, weights["credit"]),
        "momentum": (momentum, weights["momentum"]),
    })


def entry_window(opp_score: pd.Series, risk_labels: pd.Series,
                 opp_min: float, lookback: int) -> pd.Series:
    """Finestra di ingresso: opportunità almeno 'interessante' e colore del
    rischio migliore di quello di `lookback` sedute fa (es. rosso -> giallo)."""
    rank = risk_labels.map({lab: i for i, lab in enumerate(RISK_LABELS)})
    return (opp_score >= opp_min) & (rank > rank.shift(lookback))
