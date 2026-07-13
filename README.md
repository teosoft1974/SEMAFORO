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

## Stato

- [x] Fase 0 — brief v0.1, scaffold, configurazione
- [ ] Fase 1 — fetcher + storico 15 anni
- [ ] Fase 2 — indicatori + scoring
- [ ] Fase 3 — Action giornaliera + dashboard
- [ ] Fase 4 — backtest e taratura soglie
- [ ] Fase 5 — alert su cambio colore
