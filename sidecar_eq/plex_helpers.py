import os
from dotenv import load_dotenv
from plexapi.server import PlexServer

# Load env variables from .env at project root
load_dotenv()

PLEX_BASEURL = os.getenv("PLEX_BASEURL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")

plex = PlexServer(PLEX_BASEURL, PLEX_TOKEN)

def get_all_playlists():
    """Return a list of all playlist objects (music only)."""
    return [p for p in plex.playlists() if p.type == 'playlist']

def get_playlist_titles():
    """Return a list of (title, id) for all music playlists."""
    return [(p.title, p.ratingKey) for p in get_all_playlists()]

def get_tracks_for_playlist(rating_key):
    """
    Return track info for a playlist given its ratingKey (ID).
    Uses PlexAPI fetchItem to ensure it's not searching by name.
    """
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

