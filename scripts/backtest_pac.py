"""Backtest Fase 2.5: strategie PAC settimanali guidate dal semaforo, 2005-2026.

Reddito identico per tutte le strategie: F=100 EUR/settimana. Ciò che non viene
investito resta in un serbatoio di liquidità (rendimento 0, semplificazione
conservativa verso le strategie che tengono cassa). Acquisti al close del venerdì.
Vendite (solo strategia "originale") tassate al 26% sulla plusvalenza (prezzo
medio di carico). Risultati per 100 EUR/settimana: scalano linearmente.
"""
import numpy as np
import pandas as pd

from semaforo import pipeline, storage

F = 100.0
TAX = 0.26

# Matrice moltiplicatori (rischio x opportunità) proposta in discussione
MATRIX = {
    "verde":  {"caro": 0.75, "neutrale": 1.0, "interessante": 1.5, "fortemente interessante": 2.0},
    "giallo": {"caro": 0.50, "neutrale": 1.0, "interessante": 1.5, "fortemente interessante": 2.5},
    "rosso":  {"caro": 0.50, "neutrale": 0.5, "interessante": 1.0, "fortemente interessante": 1.5},
}
ENTRY_MULT = {"interessante": 3.0, "fortemente interessante": 4.0}

# Variante: mai sotto 1x (nessuna frenata sul "caro"), stessi boost
MATRIX_B = {r: {o: max(m, 1.0) for o, m in row.items()} for r, row in MATRIX.items()}

DOSSIER = {  # proxy USA dei 5 blocchi del dossier modello
    "ACWI": 0.45, "RSP": 0.15, "IWM": 0.10, "GLD": 0.10, "IEF": 0.20,
}


def weekly_data():
    sig = pipeline.build()
    prices = storage.load("prices").reindex(sig.index).ffill()
    df = pd.concat([sig[["risk_label", "opp_label", "entry_window"]],
                    prices[["SPY", *DOSSIER]]], axis=1)
    return df.resample("W-FRI").last().dropna(subset=["SPY", "risk_label"])


def multiplier(row, matrix):
    if matrix is None:  # PAC fisso
        return 1.0
    if row.entry_window and row.opp_label in ENTRY_MULT:
        return ENTRY_MULT[row.opp_label]
    return matrix[row.risk_label][row.opp_label]


def desired_amount(mult, reservoir):
    """Reddito F a settimana; sopra 1x si attinge solo dal serbatoio."""
    if mult <= 1:
        return mult * F, reservoir + (1 - mult) * F
    extra = min((mult - 1) * F, reservoir)
    return F + extra, reservoir - extra


def run_fixed(df, asset="SPY"):
    shares = 0.0
    for _, row in df.iterrows():
        shares += F / row[asset]
    return {"finale": shares * df[asset].iloc[-1], "serbatoio": 0.0,
            "vendite": 0, "tasse": 0.0}, _wealth_series(df, asset, lambda row: F)


def run_matrix(df, matrix, asset="SPY", carry=0.0):
    shares, reservoir = 0.0, 0.0

    def step(row):
        nonlocal shares, reservoir
        reservoir *= 1 + carry / 52
        amount, reservoir = desired_amount(multiplier(row, matrix), reservoir)
        shares += amount / row[asset]
        return shares * row[asset] + reservoir

    wealth = df.apply(step, axis=1)
    return {"finale": shares * df[asset].iloc[-1] + reservoir, "serbatoio": reservoir,
            "vendite": 0, "tasse": 0.0}, wealth


def run_original(df, asset="SPY", carry=0.0):
    """Strategia descritta dall'utente: fee ridotta col mercato caro, uscita
    totale al rosso, rientro su finestra di ingresso o ritorno al verde,
    poi redeploy della liquidità a 4F a settimana."""
    shares, cost, reservoir, taxes, sells = 0.0, 0.0, 0.0, 0.0, 0
    out = False
    wealth = []
    for _, row in df.iterrows():
        px = row[asset]
        reservoir *= 1 + carry / 52
        if not out and row.risk_label == "rosso" and shares > 0:
            proceeds = shares * px
            gain = max(proceeds - cost, 0.0)
            taxes += gain * TAX
            reservoir += proceeds - gain * TAX
            shares, cost = 0.0, 0.0
            sells += 1
            out = True
        if out and (row.entry_window or row.risk_label == "verde"):
            out = False
        if out:
            reservoir += F
        else:
            base = 0.5 * F if row.opp_label == "caro" else F
            reservoir += F - base
            deploy = min(3 * F, reservoir) if reservoir > 0 and base == F else 0.0
            amount = base + deploy
            reservoir -= deploy
            shares += amount / px
            cost += amount
        wealth.append(shares * px + reservoir)
    return {"finale": shares * df[asset].iloc[-1] + reservoir, "serbatoio": reservoir,
            "vendite": sells, "tasse": taxes}, pd.Series(wealth, index=df.index)


def run_dossier(df, matrix, carry=0.0):
    """Matrice + serbatoio sul dossier a 5 blocchi (matrix=None: PAC fisso),
    ribilanciamento tramite versamenti: si compra il blocco più sottopeso."""
    d = df.dropna(subset=list(DOSSIER))
    shares = {t: 0.0 for t in DOSSIER}
    reservoir = 0.0
    wealth = []
    for _, row in d.iterrows():
        reservoir *= 1 + carry / 52
        amount, reservoir = desired_amount(multiplier(row, matrix), reservoir)
        values = {t: shares[t] * row[t] for t in DOSSIER}
        total = sum(values.values()) + amount
        gaps = {t: DOSSIER[t] - values[t] / total for t in DOSSIER}
        buy = max(gaps, key=gaps.get)
        shares[buy] += amount / row[buy]
        wealth.append(sum(shares[t] * row[t] for t in DOSSIER) + reservoir)
    final = sum(shares[t] * d[t].iloc[-1] for t in DOSSIER) + reservoir
    return ({"finale": final, "serbatoio": reservoir, "vendite": 0, "tasse": 0.0},
            pd.Series(wealth, index=d.index), d)


def _wealth_series(df, asset, amount_fn):
    shares = 0.0
    out = []
    for _, row in df.iterrows():
        shares += amount_fn(row) / row[asset]
        out.append(shares * row[asset])
    return pd.Series(out, index=df.index)


def max_dd(wealth):
    return (1 - wealth / wealth.cummax()).max()


def report(name, res, wealth, invested):
    print(f"{name:<26}{res['finale']:>12,.0f}{res['finale'] / invested:>8.2f}x"
          f"{max_dd(wealth):>9.1%}{res['vendite']:>9}{res['tasse']:>10,.0f}"
          f"{res['serbatoio']:>12,.0f}")


def main():
    df = weekly_data()
    invested = len(df) * F
    print(f"Periodo: {df.index[0].date()} -> {df.index[-1].date()} "
          f"({len(df)} settimane, versati {invested:,.0f})\n")
    print(f"{'Strategia (su SPY)':<26}{'finale':>12}{'multiplo':>9}{'max DD':>9}"
          f"{'vendite':>9}{'tasse':>10}{'serbatoio':>12}")

    res, w = run_fixed(df)
    report("PAC fisso", res, w, invested)
    res, w = run_original(df, carry=0.02)
    report("Originale (esce al rosso)", res, w, invested)
    res, w = run_matrix(df, MATRIX, carry=0.02)
    report("Matrice + serbatoio", res, w, invested)
    res, w = run_matrix(df, MATRIX_B, carry=0.02)
    report("Matrice B (mai sotto 1x)", res, w, invested)
    # la cassa rende il 2% annuo in tutte le strategie che ne tengono

    print(f"\n{'Dossier 5 blocchi':<26}{'finale':>12}{'multiplo':>9}{'max DD':>9}")
    resd, wd, dd_df = run_dossier(df, None)
    inv_d = len(dd_df) * F
    print(f"(dal {dd_df.index[0].date()}, versati {inv_d:,.0f})")
    resf, wf = run_fixed(dd_df)
    print(f"{'  PAC fisso su SPY':<26}{resf['finale']:>12,.0f}"
          f"{resf['finale'] / inv_d:>8.2f}x{max_dd(wf):>9.1%}")
    print(f"{'  PAC fisso su dossier':<26}{resd['finale']:>12,.0f}"
          f"{resd['finale'] / inv_d:>8.2f}x{max_dd(wd):>9.1%}")
    resm, wm, _ = run_dossier(df, MATRIX, carry=0.02)
    print(f"{'  Matrice su dossier':<26}{resm['finale']:>12,.0f}"
          f"{resm['finale'] / inv_d:>8.2f}x{max_dd(wm):>9.1%}")


if __name__ == "__main__":
    main()
