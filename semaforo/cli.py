"""CLI: python -m semaforo backfill | status"""
import argparse
import sys
import traceback

from . import storage
from .config import DATA_DIR, load_config
from .fetch import fred, yahoo


def cmd_backfill(args: argparse.Namespace) -> int:
    cfg = load_config()
    failures = []

    def step(name, fn):
        print(f"→ {name}...", flush=True)
        try:
            df = fn()
            storage.save(name, df)
            print(f"  ok: {len(df)} righe, {df.index.min().date()} → {df.index.max().date()}")
        except Exception:
            failures.append(name)
            print(f"  ERRORE in {name}:", file=sys.stderr)
            traceback.print_exc()

    y = cfg["tickers"]["yahoo"]
    all_tickers = y["equity"] + y["other"] + y["vol"]
    step("prices", lambda: yahoo.fetch_closes(all_tickers, start=args.start))

    if fred.api_key_available():
        step("fred", lambda: fred.fetch_series(cfg["fred"]["series"]))
    else:
        print("→ fred: SALTATO — FRED_API_KEY mancante (mettila in .env)")
        failures.append("fred (chiave mancante)")

    if not args.skip_shiller:
        from .fetch import shiller
        step("shiller", shiller.fetch_shiller)

    if not args.skip_breadth:
        from .fetch import breadth
        step("breadth", breadth.fetch_breadth)

    print()
    if failures:
        print(f"Backfill completato con problemi: {', '.join(failures)}")
        return 1
    print("Backfill completato senza errori.")
    return 0


def cmd_run(_args: argparse.Namespace) -> int:
    import json

    from . import pipeline
    from .config import DATA_DIR as _dd
    df = pipeline.build()
    snap = pipeline.export(df)

    # prezzi ETF del dossier per la dashboard: se il download fallisce si
    # conserva il file precedente (la dashboard ha comunque i suoi fallback)
    try:
        from .fetch.etf_prices import fetch_etf_prices
        mapping = load_config().get("etf_prices") or {}
        if mapping:
            with open(_dd / "etf_prices.json", "w") as f:
                json.dump(fetch_etf_prices(mapping), f, ensure_ascii=False, indent=1)
            print(f"Prezzi ETF aggiornati ({len(mapping)} ISIN)")
    except Exception as e:  # noqa: BLE001
        print(f"ATTENZIONE prezzi ETF non aggiornati: {e}", file=sys.stderr)
    r, o = snap["risk"], snap["opportunity"]
    print(f"Semaforo del {snap['date']}")
    print(f"  RISCHIO      {r['color'].upper()}  (score {r['score']})")
    for k, v in r["components"].items():
        print(f"    {k:<10} {v['score']}")
    print(f"  OPPORTUNITÀ  {o['label'].upper()}  (score {o['score']})")
    for k, v in o["components"].items():
        print(f"    {k:<13} {v['score']}")
    print(f"  Fear&Greed   {snap['fear_greed']['score']}")
    print(f"  Finestra di ingresso: {'SÌ' if snap['entry_window'] else 'no'}")
    if snap["data_quality"]["stale_series"]:
        print(f"  ATTENZIONE serie non aggiornate: {snap['data_quality']['stale_series']}")
    print(f"\nScritti {DATA_DIR / 'latest.json'} e history.json ({len(df)} sedute)")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    df = storage.describe()
    if df.empty:
        print("Nessun dato in data/raw/. Esegui: python -m semaforo backfill")
    else:
        print(df.to_string(index=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="semaforo")
    sub = parser.add_subparsers(dest="command", required=True)

    p_backfill = sub.add_parser("backfill", help="scarica lo storico completo")
    p_backfill.add_argument("--start", default=yahoo.DEFAULT_START)
    p_backfill.add_argument("--skip-breadth", action="store_true")
    p_backfill.add_argument("--skip-shiller", action="store_true")
    p_backfill.set_defaults(fn=cmd_backfill)

    p_run = sub.add_parser("run", help="calcola i punteggi e scrive latest.json")
    p_run.set_defaults(fn=cmd_run)

    p_status = sub.add_parser("status", help="riepilogo dei dati scaricati")
    p_status.set_defaults(fn=cmd_status)

    args = parser.parse_args()
    return args.fn(args)
