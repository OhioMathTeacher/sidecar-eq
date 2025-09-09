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
    """Return tracks for a playlist given its ratingKey."""
    playlist = plex.playlist(rating_key)
    tracks = playlist.items()
    return [{
        "title": t.title,
        "artist": t.artist().title if t.artist() else "",
        "album": t.album().title if t.album() else "",
        "file": t.media[0].parts[0].file if t.media and t.media[0].parts else "",
    } for t in tracks]
