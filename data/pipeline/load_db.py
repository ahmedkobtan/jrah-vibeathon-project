from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "seed"
DEFAULT_DB = ROOT / "transparentcare.db"


def init_db(path: Path = DEFAULT_DB) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS providers (
                provider_id TEXT PRIMARY KEY,
                name TEXT,
                state TEXT,
                lat REAL,
                lon REAL,
                address TEXT,
                zip TEXT
            );

            CREATE TABLE IF NOT EXISTS price_transparency (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id TEXT,
                cpt_code TEXT,
                payer_name TEXT,
                negotiated_rate REAL,
                source TEXT,
                confidence REAL,
                last_updated TEXT,
                FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
            );

            CREATE INDEX IF NOT EXISTS idx_price_cpt_payer ON price_transparency (cpt_code, payer_name);
            CREATE INDEX IF NOT EXISTS idx_price_provider ON price_transparency (provider_id);

            CREATE TABLE IF NOT EXISTS insurance_plans (
                plan_id TEXT PRIMARY KEY,
                payer_name TEXT,
                network_id TEXT,
                coverage_percent REAL,
                deductible REAL,
                aliases TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_insurance_payer ON insurance_plans (payer_name);
            """
        )
        conn.commit()


def load_csv(table: str, csv_path: Path, db_path: Path = DEFAULT_DB) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        if not rows:
            return
        columns = rows[0].keys()
        placeholders = ",".join([":" + column for column in columns])
        sql = f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
        cursor.executemany(sql, rows)
        conn.commit()


def load_seed_data(db_path: Path = DEFAULT_DB) -> None:
    init_db(db_path)
    load_csv("providers", SEED_DIR / "providers.csv", db_path)
    load_csv("price_transparency", SEED_DIR / "rates.csv", db_path)
    load_csv("insurance_plans", SEED_DIR / "insurance_plans.csv", db_path)


if __name__ == "__main__":
    load_seed_data()
    print(f"Seed data loaded into {DEFAULT_DB}")
