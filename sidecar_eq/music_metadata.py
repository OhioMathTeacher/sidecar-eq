"""Music metadata fetcher using free APIs (MusicBrainz, Wikipedia, Cover Art Archive).

Provides rich artist biographies, album artwork, and contextual information
for the Now Playing panel - all without requiring API keys.
"""

import requests
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime, timedelta
import time
import re


class MusicMetadataFetcher:
    """Fetch artist/album metadata from free sources (no API keys required)."""

    # MusicBrainz API (no key needed, rate-limited to 1 req/sec)
    MB_BASE = "https://musicbrainz.org/ws/2/"
    MB_USER_AGENT = "SidecarEQ/1.0 (https://github.com/OhioMathTeacher/sidecar-eq)"

    # Cover Art Archive (no key needed, part of MusicBrainz)
    CAA_BASE = "https://coverartarchive.org/"

    # Wikipedia API (no key needed)
    WIKI_BASE = "https://en.wikipedia.org/w/api.php"

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize metadata fetcher with optional cache directory.

        Args:
            cache_dir: Directory to cache responses (default: ~/.sidecar_eq/metadata_cache)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".sidecar_eq" / "metadata_cache"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.MB_USER_AGENT
        })

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a given key."""
        cache_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{cache_key}.json"

    def _get_cached(self, key: str, max_age_days: int = 30) -> Optional[Dict[str, Any]]:
        """Retrieve cached data if it exists and is fresh enough.

        Args:
            key: Cache key
            max_age_days: Maximum age in days before cache is considered stale

        Returns:
            Cached data dict or None if not found/stale
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            # Check cache age
            cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
            if cache_age > timedelta(days=max_age_days):
                return None

            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Metadata] Cache read error: {e}")
            return None

    def _set_cached(self, key: str, data: Dict[str, Any]):
        """Store data in cache.

        Args:
            key: Cache key
            data: Data to cache
        """
        try:
            cache_path = self._get_cache_path(key)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Metadata] Cache write error: {e}")

    def get_artist_info(self, artist: str, album: Optional[str] = None) -> Dict[str, Any]:
        """Fetch comprehensive artist information.

        Args:
            artist: Artist name
            album: Optional album name for more context

        Returns:
            Dict with keys: 'bio', 'image_url', 'genres', 'similar_artists', 'listeners'
        """
        cache_key = f"artist:{artist}"

        # Check cache first
        cached = self._get_cached(cache_key)
        if cached:
            print(f"[Metadata] Using cached artist info for: {artist}")
            return cached

        result = {
            'bio': None,
            'image_url': None,
            'genres': [],
            'similar_artists': [],
            'listeners': None
        }

        # Get MusicBrainz ID and tags
        mb_id = None
        try:
            mb_data = self._fetch_musicbrainz_artist(artist)
            if mb_data:
                mb_id = mb_data.get('mbid')
                result['genres'] = mb_data.get('tags', [])
                result['similar_artists'] = mb_data.get('similar_artists', [])
                print(f"[Metadata] MusicBrainz ID: {mb_id}, tags: {result['genres']}, similar: {len(result['similar_artists'])} artists")
        except Exception as e:
            print(f"[Metadata] MusicBrainz error: {e}")

        # Try to get Wikipedia bio
        try:
            bio = self._fetch_wikipedia_bio(artist)
            if bio:
                result['bio'] = bio
                print(f"[Metadata] Wikipedia bio found: {len(bio)} chars")
        except Exception as e:
            print(f"[Metadata] Wikipedia error: {e}")

        # Cache result
        self._set_cached(cache_key, result)

        return result

    def get_album_artwork(self, artist: str, album: str) -> Optional[str]:
        """Fetch album artwork URL.

        Args:
            artist: Artist name
            album: Album name

        Returns:
            URL to album artwork image or None
        """
        cache_key = f"album_art:{artist}:{album}"

        # Check cache
        cached = self._get_cached(cache_key, max_age_days=90)  # Artwork doesn't change
        if cached and cached.get('url'):
            return cached['url']

        # Try Cover Art Archive (via MusicBrainz release ID)
        try:
            url = self._fetch_cover_art_archive(artist, album)
            if url:
                self._set_cached(cache_key, {'url': url})
                return url
        except Exception as e:
            print(f"[Metadata] Cover Art Archive error: {e}")

        return None

    def get_album_tracklist(self, artist: str, album: str) -> list[dict[str, any]]:
        """Fetch album tracklist from MusicBrainz.

        Args:
            artist: Artist name
            album: Album name

        Returns:
            List of track dicts with 'number', 'title', 'length' keys
        """
        cache_key = f"tracklist:{artist}:{album}"

        # Check cache
        cached = self._get_cached(cache_key, max_age_days=90)
        if cached and cached.get('tracks'):
            print(f"[Metadata] Using cached tracklist for: {album}")
            return cached['tracks']

        # Fetch from MusicBrainz
        try:
            tracks = self._fetch_musicbrainz_tracklist(artist, album)
            if tracks:
                self._set_cached(cache_key, {'tracks': tracks})
                return tracks
        except Exception as e:
            print(f"[Metadata] Tracklist fetch error: {e}")

        return []

    def _fetch_musicbrainz_tracklist(self, artist: str, album: str) -> list[dict[str, any]]:
        """Fetch tracklist from MusicBrainz.

        Args:
            artist: Artist name
            album: Album name

        Returns:
            List of track dicts or empty list
        """
        try:
            time.sleep(1)  # Rate limit compliance

            # Search for release
            params = {
                'query': f'artist:{artist} AND release:{album}',
                'fmt': 'json',
                'limit': 1
            }

            response = self.session.get(
                f"{self.MB_BASE}release",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            if 'releases' not in data or not data['releases']:
                return []

            release_id = data['releases'][0]['id']

            # Get full release info with recordings
            time.sleep(1)  # Rate limit compliance

            response = self.session.get(
                f"{self.MB_BASE}release/{release_id}",
                params={'inc': 'recordings', 'fmt': 'json'},
                timeout=5
            )
            response.raise_for_status()
            release_data = response.json()

            # Extract tracks from media
            tracks = []
            for medium in release_data.get('media', []):
                for track_data in medium.get('tracks', []):
                    track = {
                        'number': track_data.get('position', '?'),
                        'title': track_data.get('title', 'Unknown'),
                        'length': track_data.get('length')  # in milliseconds
                    }
                    tracks.append(track)

            print(f"[Metadata] Found {len(tracks)} tracks for: {album}")
            return tracks

        except Exception as e:
            print(f"[Metadata] MusicBrainz tracklist fetch failed: {e}")
            return []

    def _fetch_wikipedia_bio(self, artist: str) -> Optional[str]:
        """Fetch artist biography from Wikipedia.

        Args:
            artist: Artist name

        Returns:
            Plain text biography summary or None
        """
        try:
            # First, search for the artist page
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{artist} band musician',
                'srlimit': 1
            }

            response = self.session.get(self.WIKI_BASE, params=search_params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if not data.get('query', {}).get('search'):
                print(f"[Metadata] No Wikipedia page found for: {artist}")
                return None

            page_title = data['query']['search'][0]['title']
            print(f"[Metadata] Found Wikipedia page: {page_title}")

            # Get the page extract (summary)
            extract_params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'extracts',
                'exintro': True,  # Only intro section
                'explaintext': True,  # Plain text, no HTML
                'exsentences': 5  # First 5 sentences
            }

            response = self.session.get(self.WIKI_BASE, params=extract_params, timeout=5)
            response.raise_for_status()
            data = response.json()

            pages = data.get('query', {}).get('pages', {})
            if pages:
                page = next(iter(pages.values()))
                extract = page.get('extract', '')
                if extract:
                    # Clean up the extract
                    extract = extract.strip()
                    # Remove pronunciation guides like "(/ˈbɜːrθdeɪ ˈpɑːrti/)"
                    extract = re.sub(r'\s*\([^)]*?[/\\][^)]*?\)\s*', ' ', extract)
                    # Clean up multiple spaces
                    extract = re.sub(r'\s+', ' ', extract)
                    return extract

            return None

        except Exception as e:
            print(f"[Metadata] Wikipedia bio fetch failed: {e}")
            return None

    def _fetch_cover_art_archive(self, artist: str, album: str) -> Optional[str]:
        """Fetch album artwork from Cover Art Archive.

        Args:
            artist: Artist name
            album: Album name

        Returns:
            URL to album artwork or None
        """
        try:
            # First, find the release MBID
            time.sleep(1)  # Rate limit compliance

            params = {
                'query': f'artist:{artist} AND release:{album}',
                'fmt': 'json',
                'limit': 1
            }

            response = self.session.get(
                f"{self.MB_BASE}release",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            if 'releases' not in data or not data['releases']:
                print(f"[Metadata] No MusicBrainz release found for: {artist} - {album}")
                return None

            release_id = data['releases'][0]['id']
            print(f"[Metadata] Found MusicBrainz release ID: {release_id}")

            # Now get the cover art
            time.sleep(1)  # Rate limit compliance

            response = self.session.get(
                f"{self.CAA_BASE}release/{release_id}",
                timeout=5
            )
            response.raise_for_status()
            art_data = response.json()

            # Get the front cover image
            for image in art_data.get('images', []):
                if image.get('front') and 'thumbnails' in image:
                    # Use large thumbnail (500px)
                    return image['thumbnails'].get('large') or image['thumbnails'].get('small')
                elif image.get('front'):
                    return image.get('image')

            # If no front cover, use first image
            if art_data.get('images'):
                first_image = art_data['images'][0]
                if 'thumbnails' in first_image:
                    return first_image['thumbnails'].get('large') or first_image['thumbnails'].get('small')
                return first_image.get('image')

            return None

        except Exception as e:
            print(f"[Metadata] Cover Art Archive fetch failed: {e}")
            return None

    def _fetch_musicbrainz_artist(self, artist: str) -> Optional[Dict[str, Any]]:
        """Fetch artist data from MusicBrainz.

        Note: MusicBrainz rate limit is 1 req/sec - respect it!

        Args:
            artist: Artist name

        Returns:
            Dict with 'mbid', 'tags', and 'similar_artists' keys or None
        """
        try:
            time.sleep(1)  # Rate limit compliance

            params = {
                'query': f'artist:{artist}',
                'fmt': 'json',
                'limit': 1
            }

            response = self.session.get(
                f"{self.MB_BASE}artist",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            if 'artists' not in data or not data['artists']:
                print(f"[Metadata] No MusicBrainz artist found for: {artist}")
                return None

            artist_data = data['artists'][0]
            artist_mbid = artist_data.get('id')

            # Extract tags (genres)
            tags = []
            if 'tags' in artist_data:
                tags = [tag['name'] for tag in artist_data['tags'][:7]]  # Top 7 tags

            # Fetch artist relations (similar artists)
            similar_artists = []
            if artist_mbid:
                try:
                    time.sleep(1)  # Rate limit compliance

                    response = self.session.get(
                        f"{self.MB_BASE}artist/{artist_mbid}",
                        params={'inc': 'artist-rels', 'fmt': 'json'},
                        timeout=5
                    )
                    response.raise_for_status()
                    artist_details = response.json()

                    # Extract related artists
                    for relation in artist_details.get('relations', []):
                        if relation.get('type') in ['member of band', 'collaboration', 'supporting musician']:
                            related = relation.get('artist', {})
                            if related.get('name'):
                                similar_artists.append(related['name'])

                    print(f"[Metadata] Found {len(similar_artists)} related artists for {artist}")
                except Exception as e:
                    print(f"[Metadata] Failed to fetch artist relations: {e}")

            return {
                'tags': tags,
                'mbid': artist_mbid,
                'similar_artists': similar_artists[:10]  # Limit to 10
            }
        except Exception as e:
            print(f"[Metadata] MusicBrainz artist fetch failed: {e}")
            return None


# Global instance
_fetcher = None

def get_metadata_fetcher() -> MusicMetadataFetcher:
    """Get singleton metadata fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = MusicMetadataFetcher()
    return _fetcher
