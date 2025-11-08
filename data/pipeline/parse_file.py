from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List

NormalizedRow = Dict[str, str | float]

DEFAULT_FIELDS = {
    "cpt_field": "cpt_code",
    "payer_field": "payer_name",
    "price_field": "negotiated_rate",
    "provider_field": "provider_name",
}


def parse_transparency_file(path: Path, field_map: Dict[str, str] | None = None) -> List[NormalizedRow]:
    """Parse a machine-readable transparency file into normalized rows."""

    field_map = field_map or DEFAULT_FIELDS
    if path.suffix.lower() == ".csv":
        return _parse_csv(path, field_map)
    if path.suffix.lower() == ".json":
        return _parse_json(path, field_map)
    raise ValueError(f"Unsupported file format: {path}")


def _parse_csv(path: Path, field_map: Dict[str, str]) -> List[NormalizedRow]:
    rows: List[NormalizedRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            rows.append(_normalize_record(record, field_map))
    return rows


def _parse_json(path: Path, field_map: Dict[str, str]) -> List[NormalizedRow]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        iterable: Iterable[Dict[str, str]] = payload.get("data", [])
    else:
        iterable = payload
    return [_normalize_record(record, field_map) for record in iterable]


def _normalize_record(record: Dict[str, str], field_map: Dict[str, str]) -> NormalizedRow:
    return {
        "cpt_code": record.get(field_map["cpt_field"], ""),
        "payer_name": record.get(field_map["payer_field"], ""),
        "negotiated_rate": float(record.get(field_map["price_field"], 0) or 0),
        "provider_name": record.get(field_map["provider_field"], ""),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Normalize transparency file")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    rows = parse_transparency_file(args.path)
    print(json.dumps(rows[:5], indent=2))
