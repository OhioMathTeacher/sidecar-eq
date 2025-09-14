# Offline-only tag reader: mutagen first, then filename/path guesses.
import os, re
try:
    from mutagen import File
except Exception:
    File = None

def _first(v):
    return (v[0] if isinstance(v, list) and v else v) or None

def _guess_from_filename(path: str) -> dict:
    base = os.path.splitext(os.path.basename(path))[0]

    # Common patterns:
    # 01 - Title, 01_Title, [01] Title
    m = re.match(r"^\s*[\[\(]?(?P<trk>\d{1,3})[\]\)]?\s*[-_ ]+\s*(?P<title>.+)$", base)
    if m:
        return {"title": m.group("title").strip(), "artist": None, "album": None}

    # Artist - Title
    if " - " in base:
        artist, title = base.split(" - ", 1)
        return {"title": title.strip(), "artist": artist.strip(), "album": None}

    # Fallback: just use the filename as title
    return {"title": base.strip(), "artist": None, "album": None}

def _guess_from_path(path: str, current: dict) -> dict:
    # Use folder names as hints: .../Artist/Album/Track.ext
    artist = current.get("artist")
    album  = current.get("album")

    parent = os.path.basename(os.path.dirname(path)) or None
    grand  = os.path.basename(os.path.dirname(os.path.dirname(path))) or None

    # If album missing but parent folder looks like an album
    if not album and parent:
        current["album"] = parent

    # If artist missing, try grandparent folder
    if not artist and grand:
        current["artist"] = grand

    return current

def read_tags(path: str) -> dict:
    tags = {"title": None, "artist": None, "album": None}

    # 1) Embedded tags (works for mp3/flac/m4a/ogg/etc.)
    if File:
        try:
            audio = File(path, easy=True)
            if audio and getattr(audio, "tags", None):
                tags["title"]  = _first(audio.tags.get("title"))
                tags["artist"] = _first(audio.tags.get("artist"))
                tags["album"]  = _first(audio.tags.get("album"))
        except Exception:
            pass

    # 2) Filename guess
    if not tags["title"]:
        tags.update({k: v for k, v in _guess_from_filename(path).items() if v and not tags.get(k)})

    # 3) Path guess (artist/album from folders)
    tags = _guess_from_path(path, tags)

    return tags
