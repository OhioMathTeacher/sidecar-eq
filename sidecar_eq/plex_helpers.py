import os

# Optional imports for environments where developers don't have Plex or dotenv
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from plexapi.server import PlexServer
except Exception:
    PlexServer = None

# Load env variables if available
if load_dotenv:
    try:
        load_dotenv()
    except Exception:
        pass

PLEX_BASEURL = os.getenv("PLEX_BASEURL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")

plex = None
if PlexServer and PLEX_BASEURL and PLEX_TOKEN:
    try:
        plex = PlexServer(PLEX_BASEURL, PLEX_TOKEN)
    except Exception:
        plex = None

def get_all_playlists():
    """Return a list of all playlist objects (music only).

    If Plex is not configured/available, return an empty list.
    """
    if not plex:
        return []
    return [p for p in plex.playlists() if p.type == 'playlist']

def get_playlist_titles():
    """Return a list of (title, id) for all music playlists."""
    return [(p.title, p.ratingKey) for p in get_all_playlists()]

def get_tracks_for_playlist(rating_key):
    """
    Return track info for a playlist given its ratingKey (ID).
    If Plex is not configured, return an empty list.
    """
    if not plex:
        return []
    # Make sure rating_key is int (sometimes you get string IDs)
    playlist = plex.fetchItem(int(rating_key))
    tracks = playlist.items()
    return [{
        "title": t.title,
        "artist": t.grandparentTitle if hasattr(t, 'grandparentTitle') else "",
        "album": t.parentTitle if hasattr(t, 'parentTitle') else "",
        "stream_url": t.getStreamURL(),  # <-- this works even if file path is not local
        "source": "plex"
    } for t in tracks]

