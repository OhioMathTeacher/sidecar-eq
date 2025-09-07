import json, os
from pathlib import Path

def save_json(paths, out_path):
    data = {"paths": [os.path.abspath(p) for p in paths]}
    Path(out_path).write_text(json.dumps(data, indent=2))

def load_json(in_path):
    try:
        data = json.loads(Path(in_path).read_text())
        return data.get("paths", [])
    except Exception:
        return []

def export_m3u(paths, out_path):
    lines = ["#EXTM3U"]
    lines += [str(p) for p in paths]
    Path(out_path).write_text("\n".join(lines))
