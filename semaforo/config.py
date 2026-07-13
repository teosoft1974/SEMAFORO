"""Caricamento configurazione e percorsi del progetto."""
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

load_dotenv(PROJECT_ROOT / ".env")


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)
