
"""
Simple file-based storage for extractions.
Stores each extraction as a JSON file in ./data/ directory.
In production, replace with a database (PostgreSQL, MongoDB, etc.)
"""
import json
import os
from pathlib import Path
from models import ExtractionRecord
 
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
 
 
def save_extraction(record: ExtractionRecord, overwrite: bool = False):
    """Save an extraction record to disk."""
    file_path = DATA_DIR / f"{record.id}.json"
    if file_path.exists() and not overwrite:
        return  # Don't overwrite unless explicitly told to
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record.dict(), f, indent=2, ensure_ascii=False)
 
 
def get_all_extractions() -> list:
    """Return all extractions sorted by timestamp (newest first)."""
    records = []
    for file_path in DATA_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        except Exception:
            continue
    # Sort by timestamp descending
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records
 
 
def get_extraction_by_id(extraction_id: str) -> dict | None:
    """Retrieve a single extraction by ID."""
    file_path = DATA_DIR / f"{extraction_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)