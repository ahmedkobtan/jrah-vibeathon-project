from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

DATA_ROOT = Path(__file__).resolve().parents[1]
HOSPITAL_DIR = DATA_ROOT / "hospitals"


def discover_transparency_files() -> List[Path]:
    """Return a list of machine-readable files found in the hospitals folder."""

    if not HOSPITAL_DIR.exists():
        return []
    files: List[Path] = []
    for path in HOSPITAL_DIR.rglob("*"):
        if path.suffix.lower() in {".json", ".csv"}:
            files.append(path)
    return files


def snapshot_file_index(destination: Path) -> None:
    """Dump the list of files to JSON for inspection."""

    files = [str(path) for path in discover_transparency_files()]
    destination.write_text(json.dumps({"files": files}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    output_path = DATA_ROOT / "hospitals_index.json"
    snapshot_file_index(output_path)
    print(f"Wrote index to {output_path}")
