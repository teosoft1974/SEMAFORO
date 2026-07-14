# Semaforo

Rilevatore di regime finanziario: un **semaforo del rischio** (verde/giallo/rosso) e un **indicatore di opportunità** (caro → fortemente interessante), calcolati ogni giorno da trend, ampiezza, volatilità, credito, macro e valutazioni.

- **Specifica completa**: [docs/BRIEF_v0.1.md](docs/BRIEF_v0.1.md) — formule, soglie, schema JSON, architettura, roadmap
- **Documento di origine**: `Semaforo Brief.docx`
- **Parametri**: [config/config.yaml](config/config.yaml)

## Architettura (MVP)

Pipeline pull-only, senza webhook TradingView:

```
GitHub Actions (cron giornaliero)
  → fetch (yfinance, FRED, CBOE, Shiller)
  → compute (pandas)
  → data/latest.json + history.json
  → dashboard statica su GitHub Pages
```

## Setup locale

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "FRED_API_KEY=..." > .env   # chiave gratuita: https://fred.stlouisfed.org/docs/api/api_key.html
```

## Dashboard

**https://teosoft1974.github.io/SEMAFORO/** — aggiornata ogni sera di borsa da GitHub Actions.

Il design è quello del mockup Broadsheet in `design-brief-document/` (brief: [docs/DESIGN_BRIEF.md](docs/DESIGN_BRIEF.md)).
Il piano personale (fee, dossier ETF) si configura nella pagina stessa: servono i link
"pubblica sul web → CSV" dei propri fogli Google (template in [templates/](templates/)).
I dati personali restano nel browser e nel proprio Drive — mai nel repository.

Per provarla in locale: `python3 -m http.server -d . 8000` e apri
`http://localhost:8000/dashboard/` (i fetch non funzionano da `file://`).

## Stato

- [x] Fase 0 — brief v0.1, scaffold, configurazione
- [x] Fase 1 — fetcher + storico dal 2005
- [x] Fase 2 — indicatori + scoring (+ 2.5/2.6: backtest strategia PAC)
- [x] Fase 3 — Action giornaliera + dashboard su Pages
- [ ] Fase 4 — taratura fine delle soglie sul backtest
- [ ] Fase 5 — alert su cambio colore
