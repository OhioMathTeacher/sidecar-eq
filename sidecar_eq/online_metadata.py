"""Online metadata fetching from Wikipedia, MusicBrainz, and Last.fm.

Provides artist information, album details, and track metadata from multiple
online sources. Results are cached to minimize API calls and improve performance.

Sources:
- Wikipedia: Artist biographies, background, career info
- MusicBrainz: Structured music metadata (releases, recordings, relationships)
- Last.fm: Artist info, similar artists, album information, tags

All APIs are free to use with reasonable rate limits.
"""

import urllib.request
import urllib.parse
import json
import html
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class OnlineMetadataFetcher:
    """Fetch artist and album information from online sources.
    
    Attributes:
        cache: In-memory cache of fetched data (path -> {data, timestamp})
        cache_duration: How long to cache results (seconds)
    """
    
    def __init__(self, cache_duration: int = 3600):
        """Initialize the metadata fetcher.
        
        Args:
            cache_duration: Cache validity duration in seconds (default 1 hour)
        """
        self.cache = {}
        self.cache_duration = cache_duration
        
        # Last.fm API key (public, read-only key for educational use)
        # For production, users should get their own key from https://www.last.fm/api
        self.lastfm_api_key = "YOUR_API_KEY_HERE"  # Replace with actual key
        
        # User agent for respectful API access
        self.user_agent = "SidecarEQ/1.0 (Music Player)"
        
        # Persistent disk cache for offline access
        from .metadata_cache import get_metadata_cache
        self.disk_cache = get_metadata_cache()
    
    def fetch_artist_info(self, artist: str, track_title: str = "") -> Dict:
        """Fetch comprehensive artist information from multiple sources.
        
        Args:
            artist: Artist name
            track_title: Optional track title for better matching
            
        Returns:
            Dictionary with artist info:
            {
                'name': str,
                'bio': str (short bio/summary),
                'full_bio': str (longer biography),
                'image_url': str,
                'similar_artists': List[str],
                'tags': List[str],
                'listeners': int,
                'play_count': int,
                'url': str (link to artist page),
                'formed': str (year or date),
                'source': str (which API provided the data)
            }
        """
        # Check persistent disk cache first (for offline access)
        cached_data = self.disk_cache.get_artist(artist)
        if cached_data:
            print(f"[OnlineMetadata] Using cached data for '{artist}' (offline mode)")
            return cached_data
        
        # Check in-memory cache second (for recent fetches)
        cache_key = f"artist:{artist.lower()}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_duration):
                return cached_data
        
        # Try multiple sources in order of preference
        info = {}
        
        # 1. Try MusicBrainz first (most structured data)
        mb_info = self._fetch_musicbrainz_artist(artist)
        if mb_info:
            info.update(mb_info)
        
        # 2. Try Wikipedia for biography
        wiki_info = self._fetch_wikipedia_artist(artist)
        if wiki_info:
            info.update(wiki_info)
        
        # 3. Try Last.fm for social data and images
        if self.lastfm_api_key and self.lastfm_api_key != "YOUR_API_KEY_HERE":
            lastfm_info = self._fetch_lastfm_artist(artist)
            if lastfm_info:
                info.update(lastfm_info)
        
        # Cache the result (both in-memory and on disk)
        if info:
            self.cache[cache_key] = (info, datetime.now())
            # Save to persistent disk cache for offline access
            self.disk_cache.put_artist(artist, info)
        
        return info
    
    def _fetch_wikipedia_artist(self, artist: str) -> Optional[Dict]:
        """Fetch artist info from Wikipedia.
        
        Args:
            artist: Artist name
            
        Returns:
            Dictionary with bio, url, etc. or None if not found
        """
        try:
            # Wikipedia API endpoint
            base_url = "https://en.wikipedia.org/w/api.php"
            
            # Search for the artist page - try exact match first
            # Use intitle to prioritize pages with the artist name in the title
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'intitle:"{artist}"',
                'srlimit': 5  # Get several results to find the best match
            }
            
            search_url = f"{base_url}?{urllib.parse.urlencode(search_params)}"
            req = urllib.request.Request(search_url, headers={'User-Agent': self.user_agent})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
            if not data.get('query', {}).get('search'):
                return None
            
            # Try to find the best match (prefer shorter titles, avoid disambiguation pages)
            results = data['query']['search']
            page_title = None
            
            for result in results:
                title = result['title']
                # Skip disambiguation pages
                if '(disambiguation)' in title.lower():
                    continue
                # Prefer exact or close matches
                if artist.lower() in title.lower():
                    page_title = title
                    break
            
            # If no good match, use the first result
            if not page_title and results:
                page_title = results[0]['title']
            
            if not page_title:
                return None
            
            # Get page extract and full content
            content_params = {
                'action': 'query',
                'format': 'json',
                'prop': 'extracts|info',
                'exintro': 1,  # Just the intro
                'explaintext': 1,  # Plain text
                'inprop': 'url',
                'titles': page_title
            }
            
            content_url = f"{base_url}?{urllib.parse.urlencode(content_params)}"
            req = urllib.request.Request(content_url, headers={'User-Agent': self.user_agent})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            pages = data.get('query', {}).get('pages', {})
            if not pages:
                return None
            
            page = list(pages.values())[0]
            extract = page.get('extract', '')
            url = page.get('fullurl', '')
            
            # Clean up the extract (first paragraph is usually best)
            bio = extract.split('\n')[0] if extract else ''
            
            return {
                'bio': bio[:500] + '...' if len(bio) > 500 else bio,
                'full_bio': extract,
                'url': url,
                'source': 'Wikipedia'
            }
            
        except Exception as e:
            print(f"[OnlineMetadata] Wikipedia fetch failed for '{artist}': {e}")
            return None
    
    def _fetch_musicbrainz_artist(self, artist: str) -> Optional[Dict]:
        """Fetch artist info from MusicBrainz.
        
        Args:
            artist: Artist name
            
        Returns:
            Dictionary with structured metadata or None if not found
        """
        try:
            # MusicBrainz API endpoint
            base_url = "https://musicbrainz.org/ws/2/artist/"
            
            # Search for artist
            params = {
                'query': f'artist:"{artist}"',
                'fmt': 'json',
                'limit': 1
            }
            
            search_url = f"{base_url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(search_url, headers={'User-Agent': self.user_agent})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            if not data.get('artists'):
                return None
            
            artist_data = data['artists'][0]
            
            # Extract useful info
            info = {
                'name': artist_data.get('name', artist),
                'formed': artist_data.get('life-span', {}).get('begin', ''),
                'type': artist_data.get('type', ''),  # Person, Group, etc.
                'country': artist_data.get('country', ''),
                'source': 'MusicBrainz'
            }
            
            # Get tags/genres if available
            if 'tags' in artist_data:
                info['tags'] = [tag['name'] for tag in artist_data['tags'][:5]]
            
            return info
            
        except Exception as e:
            print(f"[OnlineMetadata] MusicBrainz fetch failed for '{artist}': {e}")
            return None
    
    def _fetch_lastfm_artist(self, artist: str) -> Optional[Dict]:
        """Fetch artist info from Last.fm.
        
        Args:
            artist: Artist name
            
        Returns:
            Dictionary with stats, images, similar artists or None if not found
        """
        try:
            base_url = "http://ws.audioscrobbler.com/2.0/"
            
            params = {
                'method': 'artist.getinfo',
                'artist': artist,
                'api_key': self.lastfm_api_key,
                'format': 'json'
            }
            
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            if 'error' in data or 'artist' not in data:
                return None
            
            artist_data = data['artist']
            
            info = {
                'listeners': int(artist_data.get('stats', {}).get('listeners', 0)),
                'play_count': int(artist_data.get('stats', {}).get('playcount', 0)),
                'url': artist_data.get('url', ''),
            }
            
            # Get artist image
            images = artist_data.get('image', [])
            for img in images:
                if img.get('size') == 'large' and img.get('#text'):
                    info['image_url'] = img['#text']
                    break
            
            # Get similar artists
            similar = artist_data.get('similar', {}).get('artist', [])
            if similar:
                info['similar_artists'] = [a['name'] for a in similar[:5]]
            
            # Get tags
            tags = artist_data.get('tags', {}).get('tag', [])
            if tags:
                info['tags'] = [t['name'] for t in tags[:5]]
            
            # Get bio summary
            bio = artist_data.get('bio', {}).get('summary', '')
            if bio:
                # Clean HTML tags
                bio = html.unescape(bio)
                bio = bio.replace('<a href', ' <a href')  # Add space before links
                # Remove HTML tags
                import re
                bio = re.sub('<[^<]+?>', '', bio)
                info['bio'] = bio[:500] + '...' if len(bio) > 500 else bio
            
            info['source'] = 'Last.fm'
            
            return info
            
        except Exception as e:
            print(f"[OnlineMetadata] Last.fm fetch failed for '{artist}': {e}")
            return None
    
    def format_artist_info_html(self, info: Dict, local_meta: Dict) -> str:
        """Format artist information as rich HTML for display.
        
        Args:
            info: Artist info from online sources
            local_meta: Local track metadata (title, artist, album, etc.)
            
        Returns:
            HTML string for display in QTextBrowser
        """
        title = local_meta.get('title', 'Unknown')
        artist = local_meta.get('artist', 'Unknown Artist')
        album = local_meta.get('album', 'Unknown Album')
        
        # Uniform font size throughout (11px), no title captions
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #e0e0e0; background: transparent; padding: 8px; font-size: 11px; line-height: 1.4; }}
                p {{ margin: 4px 0; font-size: 11px; }}
                .bio {{ color: #ccc; margin: 8px 0; font-size: 11px; }}
                .meta {{ color: #888; font-size: 11px; margin: 6px 0; }}
                .tag {{ display: inline-block; background: #2a4a6a; color: #8ab4f8; padding: 2px 5px; border-radius: 3px; margin: 2px 2px 2px 0; font-size: 10px; }}
                a {{ color: #4a9eff; text-decoration: none; font-size: 11px; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <p><b>{title}</b> by {artist}</p>
        """
        
        if not info:
            html += """
            <p class="bio">🔍 Fetching artist information...</p>
            """
        else:
            # Show MORE bio text - use full bio or at least 600 chars
            bio = info.get('bio', '') or info.get('full_bio', '')
            if bio:
                # Show up to 600 chars (about 3-4 sentences) instead of just 200
                # This gives users real Wikipedia content, not just a teaser
                if len(bio) > 600:
                    bio_text = bio[:600].rsplit('.', 1)[0] + '.'
                else:
                    bio_text = bio
                html += f'<div class="bio">{bio_text}</div>'
            
            # Genre tags - compact and uniform
            tags = info.get('tags', [])
            if tags:
                html += '<div class="meta">'
                for tag in tags[:5]:  # Show up to 5 tags
                    html += f'<span class="tag">{tag}</span>'
                html += '</div>'
            
            # Compact metadata line (uniform small font)
            meta_parts = []
            formed = info.get('formed', '')
            country = info.get('country', '')
            if formed:
                meta_parts.append(formed)
            if country:
                meta_parts.append(country)
            
            if meta_parts:
                html += f'<div class="meta">{" • ".join(meta_parts)}</div>'
            
            # Link for more info (smaller, less prominent)
            url = info.get('url', '')
            if url:
                html += f'<div style="margin-top: 8px;"><a href="{url}" target="_blank">Read more on Wikipedia →</a></div>'
        
        html += """
        </body>
        </html>
        """
        
        return html


# Singleton instance
_fetcher = None

def get_metadata_fetcher() -> OnlineMetadataFetcher:
    """Get the global metadata fetcher instance.
    
    Returns:
        OnlineMetadataFetcher singleton
    """
    global _fetcher
    if _fetcher is None:
        _fetcher = OnlineMetadataFetcher()
    return _fetcher
