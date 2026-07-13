# Semaforo — Brief funzionale e tecnico v0.1

> Rilevatore di regime finanziario: misura se il mercato è **sano**, **fragile**, **sotto stress** o **in stabilizzazione** dopo una discesa.
> Derivato dal documento "Semaforo Brief.docx" (2026-07). Questo file è la specifica operativa: formule, soglie iniziali, schema JSON, architettura.

---

## 1. Output del sistema

Due misuratori indipendenti, aggiornati una volta al giorno dopo la chiusura USA:

| Misuratore | Scala | Output |
|---|---|---|
| **Semaforo del rischio** | 0–100 (alto = sano) | verde / giallo / rosso |
| **Indicatore di opportunità** | 0–100 (alto = conveniente) | caro / neutrale / interessante / fortemente interessante |

**Segnale combinato "finestra di ingresso"**: opportunità ≥ *interessante* **e** rischio in miglioramento (colore migliore rispetto a 10 sedute prima, tipicamente rosso→giallo). Non è "rischio rosso = comprare": è *prezzi depressi + primi segnali di stabilizzazione*.

### Colori e isteresi

- **Rischio**: verde se score ≥ 65, giallo se 40–64, rosso se < 40.
- **Opportunità**: caro < 25, neutrale 25–49, interessante 50–74, fortemente interessante ≥ 75.
- **Isteresi anti-sfarfallio**: il colore cambia solo se la soglia è superata di almeno 3 punti **oppure** per 3 sedute consecutive. Le soglie sono parametri in `config.yaml`, da tarare in fase di backtest (Fase 4).

---

## 2. Semaforo del rischio — componenti e formule

Score = Σ (peso × score componente), ogni componente normalizzato 0–100.

| Componente | Peso |
|---|---|
| A. Trend | 30% |
| B. Ampiezza | 20% |
| C. Volatilità e sentiment | 15% |
| D. Credito e condizioni finanziarie | 20% |
| E. Macro e lavoro | 15% |

### A. Trend (30%)

Asset e pesi interni: SPY 30%, ACWI 30%, QQQ 15%, IWM 15%, GLD 5%, BTC-USD 5% (oro e Bitcoin visibili in dashboard ma con peso ridotto, come da brief).

Per ogni asset (prezzi di chiusura giornalieri):

- `MA200 = SMA(close, 200)`
- `pendenza_MA200 = MA200 / MA200[20 sedute fa] − 1` (crescente se > 0)
- `mom_12m = close / close[252] − 1`
- `dist_52w = close / max(close, 252) − 1` (≤ 0, è il drawdown dal massimo 52 settimane)
- `vol_20`, `vol_60` = deviazione std dei rendimenti log × √252 (informativa, non pesata nel v0.1)

**Stato del trend** (la combinazione conta più del singolo "sopra/sotto"):

| Condizione | Stato | Score |
|---|---|---|
| close > MA200 e pendenza > 0 | trend sano | 100 |
| close < MA200 ma pendenza > 0 | deterioramento iniziale | 55 |
| close > MA200 e pendenza < 0 | recupero / possibile stabilizzazione | 50 |
| close < MA200 e pendenza < 0 | ribasso consolidato | 10 |

**Score asset** = 50% stato + 30% momentum + 20% distanza dal massimo, dove:

- momentum: `clip(50 + mom_12m × 250, 0, 100)` (−20% → 0; 0% → 50; +20% → 100)
- distanza: `clip(100 + dist_52w × 500, 0, 100)` (0% → 100; −20% → 0)

### B. Ampiezza (20%)

Il brief avverte: breadth, RSP/SPY e IWM/SPY descrivono in parte lo stesso fenomeno → un solo sotto-punteggio, non tre segnali indipendenti.

- **% titoli S&P 500 sopra MA200** (peso interno 50%): score = `clip((pct − 20) / (80 − 20), 0, 1) × 100` (20% → 0; 80% → 100). La % sopra MA50 è mostrata ma non pesata nel v0.1.
- **RSP/SPY** (25%): variazione del rapporto a 60 sedute → `clip(50 + Δ60 × 800, 0, 100)`
- **IWM/SPY** (25%): stessa formula.

Lettura: SPY su + RSP/SPY su = rialzo ampio; SPY su + RSP/SPY giù = concentrazione mega-cap; breadth e small cap in peggioramento con indice forte = fragilità nascosta.

### C. Volatilità e sentiment (15%)

- **Percentile VIX 5 anni** (40%): score = `100 − percentile`. Niente regola rigida "VIX>30 = rosso".
- **Struttura a termine VIX/VIX3M** (35%): ratio < 0.9 → 100 (contango sano); 0.9–1.0 → lineare 100→40; > 1.0 (backwardation, panico) → `max(40 − (ratio−1)×400, 0)`
- **Velocità** (25%): ΔVIX a 5 e 20 sedute, z-score sugli ultimi 2 anni; score = `clip(50 − z×25, 0, 100)`

Nota dal brief: il VIX alto alimenta il rischio in negativo **e contemporaneamente** l'opportunità in positivo (panico già nei prezzi) — vedi §3.C.

### D. Credito e condizioni finanziarie (20%)

Componente con più peso di RSI/MACD (che infatti non usiamo).

- **HY OAS, FRED `BAMLH0A0HYM2`** (50%): percentile 10 anni → score = `100 − percentile`
- **Velocità dello spread** (25%): Δ a 20 e 60 giorni; allargamento rapido penalizza: z-score, score = `clip(50 − z×30, 0, 100)`
- **ANFCI, FRED `ANFCI`** (25%): score = `clip(50 − ANFCI×50, 0, 100)` (0 = media storica → 50; positivo = restrittivo → sotto 50). Rapporto HYG/IEF mostrato in dashboard, non pesato nel v0.1.

### E. Macro e lavoro (15%)

- **Sahm Rule, FRED `SAHMREALTIME`** (40%): < 0.30 → 100; 0.30–0.49 → lineare 100→30; ≥ 0.50 → 0 (recessione segnalata)
- **Claims, FRED `IC4WSA`** (30%): crescita vs 13 settimane prima: ≤ 0% → 100; 0–15% → lineare 100→30; > 15% → 10. Crescita vs 52 settimane mostrata come contesto.
- **CFNAI-MA3, FRED `CFNAIMA3`** (30%): ≥ 0 → 100; −0.7–0 → lineare 100→30; < −0.7 → 0 (soglia recessiva storica)

Payroll e tasso di disoccupazione: solo informativi in dashboard. Curva T10Y3M e inflazione (Core PCE, Fed Funds, tasso reale): informativi nel v0.1, candidati a entrare nei pesi in v0.2 — il brief chiede di leggerli come *sequenza* (inversione → permanenza → irripidimento rapido), che richiede logica di stato da progettare con calma.

---

## 3. Indicatore di opportunità — componenti e formule

| Componente | Peso |
|---|---|
| A. Drawdown | 30% |
| B. Valutazioni | 25% |
| C. Paura e capitolazione | 20% |
| D. Stabilizzazione del trend | 25% |

### A. Drawdown (30%)

`dd = 1 − close / max(close, 252)`, media 50/50 di SPY e ACWI.
Score = `clip((dd − 0.05) / (0.30 − 0.05), 0, 1) × 100` → dd ≤ 5% → 0; 30%+ → 100.

### B. Valutazioni (25%)

- **Percentile storico del CAPE Shiller** (60%, storia dal 1950): score = `100 − percentile`
- **Earnings yield (1/CAPE) − rendimento reale Treasury 10y** (40%, ~excess CAPE yield): score = `clip(ecy × 2500, 0, 100)` (0% → 0; ≥ 4% → 100)

Il CAPE è un indicatore di rendimenti attesi di lungo periodo, non un timer: per questo pesa sull'opportunità e **non** sul semaforo del rischio.

### C. Paura e capitolazione (20%)

Qui gli stessi dati di stress del rischio giocano al contrario:

- Percentile VIX 5y (35%): score = percentile
- Backwardation VIX/VIX3M (25%): ratio ≥ 1.05 → 100; 1.0–1.05 → 60; < 1.0 → 0
- Put/call CBOE (20%): percentile 1 anno della media 10 sedute → score = percentile
- Spike HY OAS (20%): Δ60g > +150 bp → 100; +50–150 bp → lineare; < +50 bp → 0

### D. Stabilizzazione del trend (25%)

Attiva solo se c'è stato drawdown ≥ 15% negli ultimi 12 mesi (altrimenti score 0 — non c'è niente da stabilizzare). Checklist su SPY, 25 punti ciascuna:

1. close > MA50
2. MA20 crescente da 10 sedute
3. VIX sceso di ≥ 20% dal picco degli ultimi 3 mesi
4. HY OAS sceso di ≥ 40 bp dal picco degli ultimi 3 mesi

Questo cattura il pattern chiave del brief: *prezzo che recupera la media dopo un forte drawdown = possibile stabilizzazione*.

### Fear & Greed proprietario (dashboard)

Come da brief, niente indici di terzi. Composito trasparente: 25% VIX+struttura a termine, 25% breadth, 25% credito, 15% put/call, 10% momentum — tutti sotto-punteggi già calcolati sopra, quindi gratis. Mostrato in dashboard con il breakdown, così si sa sempre *perché* è cambiato.

---

## 4. MVP — i 12 indicatori del brief

1. ACWI vs MA200 · 2. SPY vs MA200 · 3. pendenza MA200 SPY · 4. RSP/SPY · 5. IWM/SPY · 6. % S&P 500 sopra MA200 · 7. VIX e VIX/VIX3M · 8. HY OAS · 9. ANFCI · 10. Sahm Rule · 11. CFNAI-MA3 · 12. percentile CAPE.

Tutto il resto (QQQ, GLD, BTC, put/call, claims, curva, PCE…) è in dashboard come contesto o con peso ridotto.

---

## 5. Fonti dati e risposta alla domanda su TradingView

**Raccomandazione: per l'MVP niente TradingView.** Il flusso TradingView → alert → webhook richiede: 2FA attiva, un endpoint HTTP sempre acceso, gestione di alert che scadono o non scattano, e comunque non dà API di lettura. Tutti i 12 indicatori MVP sono calcolabili da fonti pull gratuite con codice Python puro:

| Dato | Fonte | Accesso |
|---|---|---|
| Prezzi ETF (ACWI, SPY, QQQ, IWM, RSP, GLD, HYG, IEF), ^VIX, ^VIX3M, BTC-USD | Yahoo Finance via `yfinance` | libero, nessuna chiave |
| HY OAS, ANFCI, Sahm, claims, CFNAI, T10Y3M, Core PCE, Fed Funds | **API FRED** | chiave gratuita ([fred.stlouisfed.org/docs/api](https://fred.stlouisfed.org/docs/api/api_key.html)) |
| % S&P 500 sopra MA200/MA50 | calcolata in casa: costituenti da Wikipedia + download batch `yfinance` (~500 ticker, 1 volta/giorno) | libero |
| Put/call ratio | CSV giornalieri CBOE | libero |
| CAPE, earnings yield | serie storica Shiller (Yale, `ie_data.xls`) | libero |

TradingView resta utile come *fase 6 opzionale*: alert intraday su soglie (es. VIX/VIX3M > 1) via webhook, quando esisterà un backend. Non serve per il calcolo giornaliero.

**Fallback breadth**: se il calcolo sui 500 costituenti si rivelasse fragile, il rapporto RSP/SPY assorbe temporaneamente il peso della breadth (già previsto che si sovrappongano).

## 6. Architettura tecnica

```
GitHub Actions (cron giornaliero, ~22:45 UTC dopo la chiusura USA)
  └─ fetch  → yfinance + FRED + CBOE + Shiller     (chiavi nei GitHub Secrets)
  └─ store  → SQLite / parquet versionati nel repo  (storico completo)
  └─ compute→ indicatori → score → colori           (pandas)
  └─ publish→ data/latest.json + data/history.json
GitHub Pages
  └─ dashboard statica (HTML+JS) che legge i JSON
```

Risolve l'obiezione del brief ("GitHub Pages da solo non può ricevere webhook, eseguire il calcolo o proteggere le chiavi"): **il calcolo lo fa GitHub Actions**, le chiavi stanno nei Secrets, e Pages serve solo file statici. Niente serverless, niente database esterno, costo zero. In locale lo stesso comando (`python -m semaforo run`) produce gli stessi JSON.

Struttura del pacchetto Python prevista:

```
semaforo/
  fetch/        # yahoo.py, fred.py, cboe.py, shiller.py, breadth.py
  indicators/   # trend.py, breadth.py, vol.py, credit.py, macro.py, valuation.py
  scoring/      # risk.py, opportunity.py, fear_greed.py, hysteresis.py
  storage.py    # SQLite + export JSON
  cli.py        # semaforo run / semaforo backfill
config/config.yaml   # ticker, serie FRED, pesi, soglie (tutto parametrico)
dashboard/           # statica, legge data/*.json
data/                # output giornalieri
```

## 7. Schema JSON dello snapshot giornaliero

```json
{
  "schema_version": "0.1",
  "date": "2026-07-13",
  "risk": {
    "score": 62.4,
    "color": "giallo",
    "color_prev_10d": "rosso",
    "components": {
      "trend":     {"score": 71.0, "weight": 0.30},
      "breadth":   {"score": 48.2, "weight": 0.20},
      "vol":       {"score": 55.0, "weight": 0.15},
      "credit":    {"score": 66.1, "weight": 0.20},
      "macro":     {"score": 58.9, "weight": 0.15}
    }
  },
  "opportunity": {
    "score": 57.5,
    "label": "interessante",
    "components": {
      "drawdown":      {"score": 40.0, "weight": 0.30},
      "valuation":     {"score": 35.2, "weight": 0.25},
      "fear":          {"score": 78.0, "weight": 0.20},
      "stabilization": {"score": 75.0, "weight": 0.25}
    }
  },
  "entry_window": true,
  "fear_greed": {"score": 44.1, "components": {"vix": 40, "breadth": 48, "credit": 66, "putcall": 30, "momentum": 55}},
  "indicators": {
    "SPY":  {"close": 0, "ma200": 0, "ma200_slope_20d": 0, "mom_12m": 0, "dist_52w_high": 0, "vol_20": 0, "vol_60": 0, "trend_state": "sano"},
    "ACWI": {},
    "QQQ": {}, "IWM": {}, "GLD": {}, "BTC-USD": {},
    "ratios":    {"rsp_spy": 0, "rsp_spy_chg_60d": 0, "iwm_spy": 0, "iwm_spy_chg_60d": 0, "hyg_ief": 0},
    "breadth":   {"pct_above_ma200": 0, "pct_above_ma50": 0},
    "vix":       {"level": 0, "pctile_5y": 0, "vix_vix3m": 0, "chg_5d": 0, "chg_20d": 0},
    "credit":    {"hy_oas": 0, "oas_chg_20d_bp": 0, "oas_chg_60d_bp": 0, "oas_pctile_10y": 0, "anfci": 0},
    "macro":     {"sahm": 0, "claims_4w": 0, "claims_chg_13w": 0, "claims_chg_52w": 0, "cfnai_ma3": 0, "t10y3m": 0},
    "inflation": {"core_pce_yoy": 0, "core_pce_3m_ann": 0, "fed_funds": 0, "real_rate": 0},
    "valuation": {"cape": 0, "cape_pctile": 0, "earnings_yield": 0, "real_10y": 0, "excess_yield": 0},
    "sentiment": {"put_call": 0, "put_call_ma10_pctile_1y": 0}
  },
  "data_quality": {"stale_series": [], "warnings": []}
}
```

`history.json` = array degli stessi oggetti in forma compatta (date, score, colori) per i grafici storici.

## 8. Roadmap

| Fase | Contenuto | Esito |
|---|---|---|
| **0** | Repo GitHub, scaffold, chiave FRED nei Secrets | `semaforo run` esegue a vuoto |
| **1** | Fetcher + storage + backfill 15 anni di storico | dati locali completi |
| **2** | Indicatori + scoring + isteresi (questo documento) | `latest.json` corretto |
| **3** | GitHub Action giornaliera + dashboard statica su Pages | semaforo consultabile via URL |
| **4** | Backtest dei colori su 2008, 2011, 2015, 2018, 2020, 2022 → taratura soglie | soglie v1.0 |
| **5** | Alert su cambio colore (email o Telegram dal workflow) | notifiche push |
| **6** *(opz.)* | Webhook TradingView per segnali intraday | richiede backend |

La Fase 4 è quella che trasforma i pesi "iniziali" del brief in pesi difendibili: i valori in questo documento sono punti di partenza dichiarati, non verità.

## 9. Decisioni aperte

1. **Repo pubblico o privato?** (Pages gratuito su repo pubblici; su privati serve piano Pro — in alternativa dashboard come artifact o Streamlit Community Cloud)
2. Storico BTC: su Yahoo parte dal 2014 — sufficiente per i percentili? (proposta: sì)
3. AAII / NAAIM: richiedono scraping o abbonamento → rimandati, il brief li dava come "eventuali"
