"""Comprehensive metadata extraction for audio files."""

from pathlib import Path
try:
    from mutagen import File as MutagenFile
except Exception:
    MutagenFile = None


def extract_comprehensive_metadata(file_path):
    """
    Extract all metadata fields from an audio file.
    
    Returns a dict with keys:
        title, artist, album, year, label, producer, rating,
        bitrate, format, sample_rate, bit_depth, duration
    """
    metadata = {
        "title": None,
        "artist": None,
        "album": None,
        "year": None,
        "label": None,
        "producer": None,
        "rating": 0,  # 0-5 stars
        "bitrate": None,
        "format": None,
        "sample_rate": None,
        "bit_depth": None,
        "duration": None,
    }
    
    if not MutagenFile:
        return metadata
    
    try:
        audio = MutagenFile(file_path)
        if not audio:
            return metadata
        
        # Extract technical info from audio.info
        if hasattr(audio, 'info'):
            info = audio.info
            
            # Bitrate (in kbps)
            if hasattr(info, 'bitrate') and info.bitrate:
                metadata["bitrate"] = f"{info.bitrate // 1000}kbps"
            
            # Sample rate (in kHz)
            if hasattr(info, 'sample_rate') and info.sample_rate:
                sr = info.sample_rate / 1000.0
                metadata["sample_rate"] = f"{sr:.1f}kHz"
            
            # Bit depth (for lossless formats)
            if hasattr(info, 'bits_per_sample') and info.bits_per_sample:
                metadata["bit_depth"] = f"{info.bits_per_sample}-bit"
            
            # Duration (in seconds)
            if hasattr(info, 'length') and info.length:
                metadata["duration"] = info.length
        
        # Format (file extension)
        metadata["format"] = Path(file_path).suffix.upper()[1:]
        
        # Extract tags
        if hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            
            # Title
            for key in ['TIT2', 'title', '©nam', 'TITLE']:
                if key in tags:
                    val = tags[key]
                    metadata["title"] = str(val[0]) if isinstance(val, list) else str(val)
                    break
            
            # Artist
            for key in ['TPE1', 'artist', '©ART', 'ARTIST']:
                if key in tags:
                    val = tags[key]
                    metadata["artist"] = str(val[0]) if isinstance(val, list) else str(val)
                    break
            
            # Album
            for key in ['TALB', 'album', '©alb', 'ALBUM']:
                if key in tags:
                    val = tags[key]
                    metadata["album"] = str(val[0]) if isinstance(val, list) else str(val)
                    break
            
            # Year/Date
            for key in ['TDRC', 'date', '©day', 'DATE', 'YEAR']:
                if key in tags:
                    val = tags[key]
                    year_str = str(val[0]) if isinstance(val, list) else str(val)
                    # Extract just the year (handles "2023-01-15" format)
                    if year_str:
                        metadata["year"] = year_str[:4]
                    break
            
            # Label/Publisher
            for key in ['TPUB', 'PUBLISHER', 'publisher', 'label', 'LABEL']:
                if key in tags:
                    val = tags[key]
                    metadata["label"] = str(val[0]) if isinstance(val, list) else str(val)
                    break
            
            # Producer
            for key in ['TIPL', 'IPLS', 'producer', 'PRODUCER']:
                if key in tags:
                    val = tags[key]
                    if isinstance(val, list):
                        # TIPL/IPLS can be nested, extract producer if present
                        for item in val:
                            if 'producer' in str(item).lower():
                                metadata["producer"] = str(item)
                                break
                        if not metadata["producer"] and val:
                            metadata["producer"] = str(val[0])
                    else:
                        metadata["producer"] = str(val)
                    break
            
            # Rating (POPM for ID3, or custom rating tag)
            # POPM (Popularimeter) email:rating:playcount
            for key in ['POPM', 'rating', 'RATING']:
                if key in tags:
                    val = tags[key]
                    if key == 'POPM':
                        # Extract rating from POPM (0-255 scale, convert to 0-5)
                        try:
                            if hasattr(val, 'rating'):
                                rating_255 = val.rating
                            elif isinstance(val, (list, tuple)) and len(val) > 1:
                                rating_255 = val[1]
                            else:
                                rating_255 = 0
                            # Convert 0-255 to 0-5 stars
                            metadata["rating"] = int((rating_255 / 255.0) * 5)
                        except:
                            pass
                    else:
                        # Direct rating value
                        try:
                            rating = int(val[0]) if isinstance(val, list) else int(val)
                            metadata["rating"] = max(0, min(5, rating))
                        except:
                            pass
                    if metadata["rating"]:
                        break
        
        # Fallback: try easy tags if we didn't get basic info
        if not metadata["title"] or not metadata["artist"] or not metadata["album"]:
            try:
                easy = MutagenFile(file_path, easy=True)
                if easy:
                    if not metadata["title"]:
                        title_list = easy.get("title", [])
                        metadata["title"] = title_list[0] if title_list else None
                    if not metadata["artist"]:
                        artist_list = easy.get("artist", [])
                        metadata["artist"] = artist_list[0] if artist_list else None
                    if not metadata["album"]:
                        album_list = easy.get("album", [])
                        metadata["album"] = album_list[0] if album_list else None
            except:
                pass
        
        # Final fallback for title: use filename
        if not metadata["title"]:
            metadata["title"] = Path(file_path).stem
        
        return metadata
        
    except Exception as e:
        print(f"[MetadataExtractor] Error extracting metadata from {Path(file_path).name}: {e}")
        # Return basic metadata with filename as title
        metadata["title"] = Path(file_path).stem
        metadata["format"] = Path(file_path).suffix.upper()[1:]
        return metadata
