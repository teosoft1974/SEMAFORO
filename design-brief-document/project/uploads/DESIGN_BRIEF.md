# Design Brief — Dashboard SEMAFORO

> Documento autosufficiente per Claude Design. Chi legge NON ha accesso al codebase.
> Tutto ciò che serve per progettare deve essere esplicito qui.

## 1. Contesto del prodotto
- **Software:** SEMAFORO, un rilevatore di regime finanziario per investitori privati che seguono un piano di accumulo (PAC) settimanale in ETF. Ogni sera calcola due indicatori sullo stato dei mercati — un **semaforo del rischio** (verde/giallo/rosso: il mercato è sano, fragile o sotto stress) e un **indicatore di opportunità** (caro / neutrale / interessante / fortemente interessante: quanto conviene comprare adesso) — e li traduce in un suggerimento concreto: *quanto versare questa settimana e su quale ETF*.
- **Utente tipo:** investitore privato non professionale (35–65 anni). Apre la pagina **una volta a settimana** per la decisione di versamento (~2 minuti, spesso da telefono) e occasionalmente nei giorni turbolenti per capire "quanto è grave". Possibili più profili sullo stesso dispositivo (es. il proprio piano e quello del figlio). Non è un trader: niente candele, niente order book.
- **Piattaforma:** web responsive. Uso primario **mobile** (390px) e desktop (1440px). Pagina statica servita da GitHub Pages.

## 2. Obiettivo di questa UI
- **Cosa deve permettere di fare:** rispondere in 10 secondi a "**quanto verso questa settimana, su cosa, e perché**" — e in 2 minuti a "in che stato è il mercato e cosa è cambiato".
- **Schermata/componente in oggetto:** l'intera dashboard, a pagina singola (unica schermata del prodotto).
- **Problema attuale / motivo del redesign:** la UI non esiste ancora — oggi l'output è un file JSON e una riga di terminale. Questo è il primo design.

## 3. Vincoli rigidi (NON negoziabili)
- **Stack / rendering:** HTML + CSS + JavaScript vanilla, **senza framework e senza build step**. Tutto inline o in file statici. Nessun backend: i dati arrivano da 2 fetch di file JSON statici (`latest.json`, `history.json`) e, per il piano personale, da 2 CSV pubblicati da Google Sheets.
- **Libreria componenti:** nessuna. Grafici in SVG inline o canvas, niente librerie esterne pesanti (budget totale pagina < 200 KB).
- **Layout:** colonna singola su mobile; su desktop max-width 1100px.
- **Semantica dei colori (cuore del prodotto):** i tre stati del rischio DEVONO essere verde/giallo/rosso; l'opportunità ha 4 livelli su scala propria (da "caro" a "fortemente interessante"). **Il colore non può mai essere l'unico portatore d'informazione**: sempre accompagnato da etichetta testuale e/o icona (utenti daltonici: un semaforo rosso/verde indistinguibile è un fallimento del prodotto).
- **Accessibilità:** contrasto AA, target touch ≥ 44px, leggibile in luce solare (uso da telefono).
- **Tema:** light e dark, seguendo la preferenza di sistema.

## 4. Spazio creativo (libera scelta)
- Gerarchia visiva e ordine delle sezioni (proposta indicativa in §6, ma riorganizzabile).
- Palette completa oltre ai semantici, tipografia, iconografia, stile dei grafici.
- Come rendere convivialmente la coppia di indicatori "in tensione" (oggi: rischio VERDE ma opportunità CARO — situazioni opposte devono leggersi a colpo d'occhio senza confondersi).
- Micro-interazioni (espansione dettagli componenti, tooltip sul grafico storico).
- Come dare risalto **eccezionale** allo stato "finestra di ingresso" (evento raro, ~22 giorni in 21 anni: quando accade deve essere impossibile non notarlo, senza essere allarmistico — è una buona notizia).

## 5. Design token / convenzioni già presenti
- **Colori:** nessuna palette esistente. Da proporre, con vincolo dei semantici (verde/giallo/rosso rischio; scala a 4 livelli per l'opportunità, es. dal freddo al caldo). Evitare l'estetica "app di trading" (nero + neon).
- **Tipografia:** da proporre; font di sistema o un solo webfont. I numeri grandi (punteggi 0–100, importi €) sono protagonisti: servono cifre tabulari leggibili.
- **Spaziature:** da proporre (suggerito sistema a multipli di 4px).
- **Stile generale:** sobrio, affidabile, "strumento" più che "app" — l'utente prende decisioni di soldi veri. Calmo anche quando il mercato non lo è. No gamification, no rosso ansiogeno gratuito.

## 6. Contenuti e stati da coprire
Testi e numeri reali del 13 luglio 2026 (usarli nei mockup):

**A. Card decisione della settimana** (l'elemento più importante, primo in pagina quando c'è un profilo attivo)
- Selettore profilo: "Matteo" (altri: "Figlio")
- Suggerimento: "**Questa settimana: €75 su VWCE**" (fee base €100 × moltiplicatore 0,75)
- Motivazione in una riga: "Rischio verde, ma mercato caro: versamento ridotto, la differenza va al serbatoio"
- Stato del piano: serbatoio €1.250 · piano investito al 42% (barra di avanzamento) · fase: accumulo
- Cosa è cambiato: "= invariato rispetto a settimana scorsa"
- Azione: bottone "Registra versamento" (apre il foglio Google del registro)

**B. I due indicatori** (affiancati su desktop, impilati su mobile)
- RISCHIO: **VERDE**, punteggio 79,9/100. Componenti espandibili: Trend 91,6 · Ampiezza 70,1 · Volatilità 75,8 · Credito 65,5 · Macro 92,7 (ciascuna con peso: 30/20/15/20/15%)
- OPPORTUNITÀ: **CARO**, punteggio 3,4/100. Componenti: Drawdown 0,0 · Valutazioni 2,1 · Paura 14,2 · Stabilizzazione 0,0 (pesi: 30/25/20/25%)
- Badge "Finestra di ingresso: no" (vedi stato dedicato sotto)
- Fear & Greed proprietario: 73/100 ("avidità")

**C. Grafico storico** (2005→oggi, ~5.400 sedute)
- Serie del punteggio rischio con fascia colorata verde/giallo/rosso + punteggio opportunità; marcatori sugli episodi: 2008, 2020, 2022; possibilità di vedere le finestre di ingresso passate (22 giorni totali, cluster nel 2009/2011/2020/2022)
- Selettore intervallo: 1A / 5A / Tutto

**D. Tabella indicatori di dettaglio** (per l'utente curioso, in fondo, eventualmente ripiegata)
- VIX 16,29 (32° percentile 5 anni) · VIX/VIX3M 0,85 · Spread High Yield 2,70% (percentile 24) · ANFCI -0,51 · Sahm Rule 0,07 · CFNAI-MA3 -0,03 · CAPE 41,4 (98° percentile storico) · % S&P 500 sopra MA200: 69% · SPY vs media 200gg: sopra, media crescente ("trend sano") — e simili per ACWI, QQQ, IWM, GLD, BTC
- Nota di qualità dati: "Dati aggiornati al 13/07/2026, tutte le fonti fresche"

**E. Impostazioni profilo** (pannello/pagina secondaria)
- Campi: nome profilo, fee base settimanale (€), capitale totale del piano (€), data inizio, link CSV del Registro versamenti, link CSV del Profilo, fase (accumulo/mantenimento/decumulo)
- Bottoni: "Scarica template registro" · "Esporta/Importa profilo"

**Stati da coprire:**
1. **Default** (dati e profilo presenti — i valori sopra)
2. **Prima visita** (nessun profilo): si vedono solo semafori+grafico, con invito non invadente a configurare il piano ("Configura il tuo PAC per ricevere il suggerimento settimanale")
3. **Finestra di ingresso attiva** (variante rara e importante: es. "RISCHIO GIALLO 43 in miglioramento + OPPORTUNITÀ INTERESSANTE 67 → Questa settimana: €400 su VWCE, attinge al serbatoio")
4. **Dati non freschi** (es. "Ultimo calcolo: 4 giorni fa — mostro l'ultimo disponibile" — banner di avviso, non bloccante)
5. **Errore lettura foglio Google** (il registro non risponde o è malformato: la card decisione degrada con messaggio chiaro, i semafori restano visibili)
6. **Loading** (skeleton leggero)

## 7. Fuori scope — NON toccare
- La logica dei punteggi, i pesi, le soglie dei colori: già definiti e verificati, non proporre indicatori nuovi.
- Il tracciato dei CSV (colonne del registro e del profilo): è un contratto fissato.
- Niente login/account, niente notifiche in-page, niente onboarding multi-step.
- Nessuna funzione di vendita/trading: il prodotto suggerisce solo versamenti.

## 8. Output atteso
- **Formato:** mockup visivi.
- **Deliverable:** dashboard mobile (390px) e desktop (1440px) nello stato default; più le varianti: prima visita, finestra di ingresso attiva, dati non freschi.
- **Cosa mi serve per implementare dopo:** spaziature, dimensioni e colori annotati o misurabili dai mockup (verranno tradotti in CSS vanilla a mano); palette con valori hex espliciti per light e dark, inclusi i 3+4 colori semantici dei due indicatori.
