# Semaforo — Brief v0.2 (delta rispetto alla v0.1)

> Registro delle decisioni prese dopo [BRIEF_v0.1.md](BRIEF_v0.1.md), in fase di
> costruzione e verifica (luglio 2026). La v0.1 resta la specifica di formule e
> soglie del *segnale*; questo documento fissa la *strategia d'uso* e il *prodotto*.

## 1. Strategia PAC adottata (verificata con backtest 2005–2026)

Backtest in [scripts/backtest_pac.py](../scripts/backtest_pac.py) e
[scripts/backtest_glidepath.py](../scripts/backtest_glidepath.py), versamenti
settimanali, tasse 26% sulle vendite, cassa al 2%.

**Adottato:**
- **Matrice moltiplicatori** (rischio × opportunità) applicata alla fee settimanale:
  da 0,5× (giallo/rosso + caro) a 1× (normale) fino a **3–4× nelle finestre di ingresso**;
- **Serbatoio**: le settimane sotto 1× accantonano la differenza; i boost sopra 1×
  attingono *solo* dal serbatoio. Mai vendite, mai debiti;
- **Finestra di ingresso** = opportunità ≥ interessante **e** colore del rischio in
  miglioramento vs 10 sedute prima. Rara per costruzione: 22 sedute su ~5.400,
  cluster 2009/2011/2020/2022;
- **Dossier a 5 blocchi** (pesi obiettivo di partenza): azionario globale 45,
  S&P 500 equal weight 15, small cap 10, oro 10, obbligazionario 20 — con
  **ribilanciamento tramite versamenti** (si compra il più sottopeso, mai vendite);
- **Glidepath sul completamento del piano**: quota azionaria obiettivo 80% → 60%
  in funzione del *versato / capitale totale dichiarato* (non del tempo).

**Bocciato dai numeri (non reintrodurre senza nuovi backtest):**
- *Uscita al rosso e rientro su segnale*: 1,5× finale contro 5× del PAC fisso —
  perde perfino nello scenario "crollo imminente" (2007→2012);
- *Valvola difensiva* (vendita parziale al rosso confermato): peggiora rendimento
  **e** drawdown, oltre alle tasse;
- *Fee decrescente col mercato caro senza serbatoio che si scarica*: accumula
  liquidità che non rientra mai.

## 2. Numeri chiave del backtest (per memoria)

| Strategia (SPY, 2005–2026, €100/sett) | Multiplo | Max DD |
|---|---|---|
| PAC fisso | 5,02× | 36% |
| Uscita al rosso | 1,53× | 17% |
| **Matrice + serbatoio** | **4,56×** | **29%** |
| Matrice su dossier 5 blocchi (dal 2008) | 2,48× | 21% |

I pesi/soglie della v0.1 hanno superato il test storico senza ritarature
(rosso su 2008/2018/2020, finestre solo sui grandi minimi): la Fase 4 resta
per la taratura fine, non per correzioni strutturali.

## 3. Il prodotto: piano personale sopra il segnale universale

- **Il semaforo è unico e pubblico** (JSON su GitHub Pages); **il piano è personale**
  e vive in **due fogli Google dell'utente**: *Registro versamenti* (una riga per
  acquisto: Data, Profilo, ETF, ISIN, Importo, Quote, Prezzo, Note) e *Profilo*
  (fee, capitale totale, data inizio, fase, ordine minimo, glidepath, etf_1..5).
  Template in [templates/](../templates/);
- collegamento col **link normale del foglio** (condivisione "chiunque abbia il
  link → visualizzatore"); la dashboard deriva da sola gli endpoint CSV;
- **multi-utente senza backend**: profili in localStorage (solo nome + link);
  ogni utente ha i suoi fogli; ricostruzione totale = reincollare due link;
- **abbinamento per ISIN** tra registro e dossier (stesso fondo, borse diverse);
- **fasi del piano**: accumulo (suggerimento settimanale) / mantenimento e
  decumulo (per ora messaggio dedicato; logica a bande: da sviluppare);
- il registro è la **fonte di verità**: serbatoio = dovuto − versato effettivo,
  completamento = versato / capitale totale. Il sistema si autocorregge se
  l'utente versa importi diversi dal suggerito o salta settimane.

## 4. Suggerimento settimanale: riparto e quote intere

1. Importo = fee × moltiplicatore (cap: serbatoio disponibile e capitale residuo);
2. riparto sul dossier **in proporzione al sottopeso** vs pesi obiettivo (glidepath);
3. ordini sotto `ordine_minimo` accorpati sul fondo più sottopeso;
4. con prezzi noti, conversione in **quote intere**: resti redistribuiti su tutto
   il dossier in ordine di sottopeso; **alert "quota minima"** per gli ETF non
   acquistabili col budget della settimana; avanzo dichiarato → serbatoio.

**Catena dei prezzi** (dal più fresco): colonna D del Profilo con `GOOGLEFINANCE`
(quasi real-time; copertura a macchia di leopardo: `BIT:` in EUR, `LON:` spesso in
USD da convertire; ETC oro e classi hedged assenti) → **`data/etf_prices.json`**
(chiusure EUR da Yahoo, pubblicate ogni sera dalla Action, chiave ISIN, mappa in
`config.yaml → etf_prices`) → ultimo prezzo del registro.

## 5. Dashboard (Fase 3, consegnata)

Design "Broadsheet" dal mockup Claude Design ([DESIGN_BRIEF.md](DESIGN_BRIEF.md),
`design-brief-document/`), implementato in `dashboard/index.html` (vanilla,
zero dipendenze): light+dark, 6 stati (default, prima visita, finestra di
ingresso, dati non freschi, errore fogli, loading), grafico storico dai dati
reali, guida integrata (`guida.html`) con bottoni ⓘ su ogni voce e sezione
per ogni indicatore con relativa fonte. Correzioni rispetto al mockup: soglia
verde 65 (non 60), importo senza effetto CMYK (scelta utente), dati veri.

## 6. Vincoli operativi appresi

- La Action committa `data/*.json` a ogni run: push locali solo dopo
  `git pull --rebase` a working tree pulito;
- fogli Google in locale italiano: separatore formule `;` — le formule
  suggerite nella guida evitano i separatori;
- costanti della matrice duplicate in `dashboard/index.html` e
  `scripts/backtest_pac.py`: tenerle allineate a mano.

## 7. Backlog (in ordine di valore)

1. **Fase 5 — alert** su cambio colore / finestra di ingresso (email o Telegram
   dal workflow): trasforma il sistema da "da consultare" a "che ti chiama";
2. logica di **mantenimento/decumulo** a bande nella card (oggi solo messaggio);
3. Fase 4 — taratura fine soglie/pesi sul backtest;
4. tooltip sul grafico storico; put/call CBOE; indicatori v0.2 del brief
   (curva dei tassi come sequenza, inflazione nei pesi);
5. Fase 6 (opz.) — TradingView webhook per segnali intraday.
