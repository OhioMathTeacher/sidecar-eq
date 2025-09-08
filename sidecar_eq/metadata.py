from mutagen import File

def read_tags(path: str) -> dict:
    """
    Returns {'title': str|None, 'artist': str|None, 'album': str|None}
    Uses mutagen's easy tags when available.
    """
    try:
        audio = File(path, easy=True)
        if not audio or not hasattr(audio, "tags") or audio.tags is None:
            return {"title": None, "artist": None, "album": None}
        def first(key):
            v = audio.tags.get(key)
            return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else None)
        return {
            "title": first("title"),
            "artist": first("artist"),
            "album": first("album"),
        }
    except Exception:
        return {"title": None, "artist": None, "album": None}
