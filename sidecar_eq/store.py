import json, os, sys
from pathlib import Path
from datetime import datetime

def _config_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "SidecarEQ"
    elif os.name == "nt":
        base = Path(os.path.expanduser(os.getenv("APPDATA", "~"))) / "SidecarEQ"
    else:
        base = Path.home() / ".config" / "sidecareq"
    base.mkdir(parents=True, exist_ok=True)
    return base

DB_PATH = _config_dir() / "db.json"

try:
    _db = json.loads(DB_PATH.read_text()) if DB_PATH.exists() else {}
except Exception:
    _db = {}

def save_db():
    try:
        DB_PATH.write_text(json.dumps(_db, indent=2))
    except Exception:
        pass

def get_record(path: str):
    return _db.get(os.path.abspath(path))

def set_record(path: str, data: dict) -> None:
    _db[os.path.abspath(path)] = data
    save_db()

def increment_play_count(path: str) -> None:
    ap = os.path.abspath(path)
    rec = _db.get(ap, {"play_count": 0})
    rec["play_count"] = rec.get("play_count", 0) + 1
    rec["last_played"] = datetime.utcnow().isoformat()
    _db[ap] = rec
    save_db()
