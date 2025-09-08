import subprocess
from mutagen import File

def _first(v):
    return (v[0] if isinstance(v, list) and v else v) or None

def read_tags(path: str) -> dict:
    tags = {"title": None, "artist": None, "album": None}

    # 1) Try mutagen (works for MP3/FLAC/M4A/OGG, etc.)
    try:
        audio = File(path, easy=True)
        if audio and getattr(audio, "tags", None):
            tags["title"]  = _first(audio.tags.get("title"))
            tags["artist"] = _first(audio.tags.get("artist"))
            tags["album"]  = _first(audio.tags.get("album"))
    except Exception:
        pass

    # 2) Fallback on macOS Spotlight metadata (mdls)
    if not any(tags.values()):
        try:
            out = subprocess.check_output(
                ["mdls", "-raw",
                 "-name", "kMDItemTitle",
                 "-name", "kMDItemAuthors",
                 "-name", "kMDItemAlbum", path],
                text=True
            ).splitlines()
            title, authors, album = (out + [None, None, None])[:3]

            def clean(x):
                if not x or x in ("(null)",):
                    return None
                return x.strip('"')

            def first_author(s):
                if not s or s in ("(null)",):
                    return None
                s = s.strip()
                if s.startswith("(") and s.endswith(")"):
                    s = s[1:-1].strip()
                    if not s:
                        return None
                    # array of quoted strings -> take the first
                    return s.split(",")[0].strip().strip('"')
                return clean(s)

            tags["title"]  = tags["title"]  or clean(title)
            tags["artist"] = tags["artist"] or first_author(authors)
            tags["album"]  = tags["album"]  or clean(album)
        except Exception:
            pass

    return tags

