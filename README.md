# Semaforo

Rilevatore di regime finanziario al servizio di un PAC settimanale: un **semaforo del rischio** (verde/giallo/rosso) e un **indicatore di opportunità** (caro → fortemente interessante), calcolati ogni sera da trend, ampiezza, volatilità, credito, macro e valutazioni, e tradotti in un suggerimento concreto — *quanto versare questa settimana e su quali ETF*.

- **Specifica di partenza**: [docs/BRIEF_v0.1.md](docs/BRIEF_v0.1.md) — formule, soglie, schema JSON, architettura
- **Decisioni successive (strategia e prodotto)**: [docs/BRIEF_v0.2.md](docs/BRIEF_v0.2.md)
- **Design della dashboard**: [docs/DESIGN_BRIEF.md](docs/DESIGN_BRIEF.md) + mockup in `design-brief-document/`
- **Parametri**: [config/config.yaml](config/config.yaml) · **Documento di origine**: `Semaforo Brief.docx`

## Dashboard

**https://teosoft1974.github.io/SEMAFORO/** — aggiornata ogni sera di borsa da GitHub Actions.

Cosa offre oggi:
- i due indicatori con punteggi, componenti espandibili e anti-sfarfallio dei colori;
- grafico storico 2005→oggi coi 21 anni di punteggi reali e le finestre di ingresso passate;
- **card "La tua settimana"**: fee × matrice moltiplicatori, serbatoio, avanzamento del piano,
  riparto sul dossier in **quote intere** con prezzi aggiornati e alert "quota minima";
- piano personale su **fogli Google dell'utente** (registro versamenti + profilo), collegati col
  link normale del foglio; profili multipli per dispositivo (localStorage);
- guida integrata con bottoni ⓘ su ogni voce e template scaricabili ([templates/](templates/)).

I dati personali restano nel browser e nel proprio Drive — mai nel repository.
Prova in locale: `python3 -m http.server -d . 8000` → `http://localhost:8000/dashboard/`.

## Architettura

Pipeline pull-only, senza webhook né backend:

```
GitHub Actions (cron feriale 21:45 UTC)
  → fetch (yfinance, FRED, Shiller, costituenti S&P500, prezzi ETF del dossier)
  → compute (pandas): indicatori → punteggi → colori
  → data/latest.json + history.json + etf_prices.json
  → dashboard statica su GitHub Pages
```

## Setup locale

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "FRED_API_KEY=..." > .env   # chiave gratuita: https://fred.stlouisfed.org/docs/api/api_key.html
python -m semaforo backfill      # storico completo (~5 min)
python -m semaforo run           # calcola e scrive i JSON
```

Nota operativa: la Action committa `data/*.json` a ogni run — prima di pushare
da locale fare sempre `git pull --rebase` a working tree pulito.

## Stato

- [x] Fase 0 — brief v0.1, scaffold, configurazione
- [x] Fase 1 — fetcher + storico dal 2005 (prezzi, FRED, Shiller, breadth)
- [x] Fase 2 — indicatori + scoring con isteresi; test storico 2005–2026
- [x] Fase 2.5/2.6 — backtest strategia PAC: adottata matrice+serbatoio (mai vendite),
      dossier 5 blocchi con ribilanciamento tramite versamenti, glidepath; bocciate
      uscita al rosso e valvola difensiva ([scripts/](scripts/))
- [x] Fase 3 — Action giornaliera + dashboard su Pages (design Broadsheet), piano
      personale su fogli Google, quote intere con prezzi ETF, guida integrata
- [ ] Fase 4 — taratura fine delle soglie sul backtest
- [ ] Fase 5 — alert su cambio colore / finestra di ingresso (email o Telegram)
- [ ] Fase 6 (opz.) — segnali intraday via TradingView webhook
