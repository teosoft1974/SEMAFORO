"""Backtest Fase 2.6: glidepath sul capitale e valvola difensiva, sul dossier
a 5 blocchi con matrice+serbatoio. Estende scripts/backtest_pac.py.

Glidepath: quota azionaria obiettivo in funzione del capitale accumulato,
espresso in anni di versamenti (52*F): <5 anni 80%, poi -5 punti ogni 5 anni
fino al 60%. Dentro il blocco azionario e difensivo i pesi relativi del
dossier base restano invariati.

Valvola difensiva: al rosso confermato (2 settimane consecutive) vende il 25%
di ogni posizione azionaria (tasse 26% sulla plusvalenza, prezzo medio di
carico) e parcheggia in IEF; rientra in azionario alla finestra di ingresso
o al ritorno del verde.
"""
import pandas as pd

from backtest_pac import (DOSSIER, F, MATRIX, TAX, desired_amount, max_dd,
                          multiplier, weekly_data)

EQUITY = ["ACWI", "RSP", "IWM"]
DEFENSIVE = ["GLD", "IEF"]
VALVE_FRACTION = 0.25


def glide_equity_share(capital: float) -> float:
    years = capital / (52 * F)
    for limit, share in [(5, 0.80), (10, 0.75), (15, 0.70), (20, 0.65)]:
        if years < limit:
            return share
    return 0.60


def targets(capital: float, glidepath: bool) -> dict[str, float]:
    if not glidepath:
        return DOSSIER
    eq = glide_equity_share(capital)
    base_eq = sum(DOSSIER[t] for t in EQUITY)
    base_def = sum(DOSSIER[t] for t in DEFENSIVE)
    out = {t: DOSSIER[t] / base_eq * eq for t in EQUITY}
    out |= {t: DOSSIER[t] / base_def * (1 - eq) for t in DEFENSIVE}
    return out


def run(df, glidepath=False, valve=False, matrix=MATRIX, carry=0.02):
    d = df.dropna(subset=list(DOSSIER))
    shares = {t: 0.0 for t in DOSSIER}
    cost = {t: 0.0 for t in DOSSIER}
    reservoir, taxes, sells = 0.0, 0.0, 0
    valve_on, valve_parked = False, 0.0  # valore IEF parcheggiato dalla valvola
    prev_rosso = False
    wealth = []

    for _, row in d.iterrows():
        px = {t: row[t] for t in DOSSIER}
        reservoir *= 1 + carry / 52

        if valve:
            rosso = row.risk_label == "rosso"
            if not valve_on and rosso and prev_rosso:
                moved = 0.0
                for t in EQUITY:
                    if shares[t] <= 0:
                        continue
                    qty = shares[t] * VALVE_FRACTION
                    proceeds = qty * px[t]
                    basis = cost[t] * VALVE_FRACTION
                    tax = max(proceeds - basis, 0.0) * TAX
                    shares[t] -= qty
                    cost[t] -= basis
                    moved += proceeds - tax
                    taxes += tax
                if moved > 0:
                    shares["IEF"] += moved / px["IEF"]
                    cost["IEF"] += moved
                    valve_parked = moved
                    valve_on = True
                    sells += 1
            elif valve_on and (row.entry_window or row.risk_label == "verde"):
                back = min(valve_parked, shares["IEF"] * px["IEF"])
                qty = back / px["IEF"]
                basis = cost["IEF"] * (qty / shares["IEF"])
                tax = max(back - basis, 0.0) * TAX
                shares["IEF"] -= qty
                cost["IEF"] -= basis
                taxes += tax
                # rientro sull'azionario più sottopeso
                values = {t: shares[t] * px[t] for t in EQUITY}
                tgt = targets(sum(shares[t] * px[t] for t in DOSSIER), glidepath)
                buy = max(EQUITY, key=lambda t: tgt[t] - values[t])
                shares[buy] += (back - tax) / px[buy]
                cost[buy] += back - tax
                valve_on, valve_parked = False, 0.0
                sells += 1
            prev_rosso = rosso

        amount, reservoir = desired_amount(multiplier(row, matrix), reservoir)
        capital = sum(shares[t] * px[t] for t in DOSSIER)
        tgt = targets(capital, glidepath)
        total = capital + amount
        gaps = {t: tgt[t] - shares[t] * px[t] / total for t in DOSSIER}
        buy = max(gaps, key=gaps.get)
        shares[buy] += amount / px[buy]
        cost[buy] += amount
        wealth.append(sum(shares[t] * px[t] for t in DOSSIER) + reservoir)

    w = pd.Series(wealth, index=d.index)
    final = w.iloc[-1]
    return {"finale": final, "vendite": sells, "tasse": taxes}, w, d


def episode_losses(wealth):
    peak = wealth.cummax()
    dd_abs = peak - wealth
    out = {}
    for name, s, e in [("COVID 2020", "2020-01", "2020-12"), ("2022", "2022-01", "2023-06")]:
        i = dd_abs.loc[s:e].idxmax()
        out[name] = (dd_abs[i], dd_abs[i] / peak[i])
    return out


def main():
    df = weekly_data()
    variants = [
        ("Dossier base (matrice)", dict()),
        ("+ glidepath", dict(glidepath=True)),
        ("+ valvola", dict(valve=True)),
        ("+ glidepath + valvola", dict(glidepath=True, valve=True)),
    ]
    header = (f"{'Variante':<24}{'finale':>10}{'multiplo':>9}{'maxDD':>8}"
              f"{'2020':>16}{'2022':>16}{'vendite':>8}{'tasse':>8}")
    print(header)
    for name, kw in variants:
        res, w, d = run(df, **kw)
        inv = len(d) * F
        ep = episode_losses(w)
        e20 = f"-{ep['COVID 2020'][0]:,.0f} ({ep['COVID 2020'][1]:.0%})"
        e22 = f"-{ep['2022'][0]:,.0f} ({ep['2022'][1]:.0%})"
        print(f"{name:<24}{res['finale']:>10,.0f}{res['finale'] / inv:>8.2f}x"
              f"{max_dd(w):>8.1%}{e20:>16}{e22:>16}{res['vendite']:>8}{res['tasse']:>8,.0f}")


if __name__ == "__main__":
    main()
