"""Video audio extraction utilities using FFmpeg"""

import os
import subprocess
import tempfile
from pathlib import Path
import hashlib

class VideoAudioExtractor:
    """Extract audio from video files using FFmpeg"""
    
    # Common video file extensions
    VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.m4v', '.webm', '.wmv', '.3gp'}
    
    def __init__(self, cache_dir=None):
        """Initialize with optional cache directory for extracted audio"""
        if cache_dir is None:
            cache_dir = Path.home() / '.sidecar_eq_video_cache'
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
    def is_video_file(self, file_path):
        """Check if file is a video file based on extension"""
        return Path(file_path).suffix.lower() in self.VIDEO_EXTS
    
    def get_cached_audio_path(self, video_path):
        """Get the cached audio file path for a video file"""
        # Create a hash of the video file path and modification time
        video_file = Path(video_path)
        if not video_file.exists():
            return None
            
        # Use file path + size + mtime as cache key
        cache_key = f"{video_path}_{video_file.stat().st_size}_{video_file.stat().st_mtime}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        
        # Use .m4a extension for compatibility
        cached_file = self.cache_dir / f"{cache_hash}.m4a"
        return cached_file
    
    def extract_audio(self, video_path, output_path=None, force_extract=False):
        """
        Extract audio from video file using FFmpeg
        
        Args:
            video_path: Path to video file
            output_path: Optional output path (defaults to cache)
            force_extract: Force re-extraction even if cached version exists
            
        Returns:
            Path to extracted audio file, or None if extraction failed
        """
        video_path = Path(video_path)
        if not video_path.exists():
            print(f"[VideoExtractor] Video file not found: {video_path}")
            return None
            
        if not self.is_video_file(video_path):
            print(f"[VideoExtractor] Not a video file: {video_path}")
            return None
            
        # Determine output path
        if output_path is None:
            output_path = self.get_cached_audio_path(video_path)
            
        if output_path is None:
            print(f"[VideoExtractor] Could not determine cache path for: {video_path}")
            return None
            
        output_path = Path(output_path)
        
        # Check if cached version exists and is newer than source
        if not force_extract and output_path.exists():
            try:
                if output_path.stat().st_mtime >= video_path.stat().st_mtime:
                    print(f"[VideoExtractor] Using cached audio: {output_path.name}")
                    return output_path
            except Exception:
                pass  # Fall through to re-extract
        
        print(f"[VideoExtractor] Extracting audio from: {video_path.name}")
        
        try:
            # FFmpeg command to extract audio
            # -i: input file
            # -vn: no video 
            # -acodec: audio codec (aac for .m4a compatibility)
            # -ab: audio bitrate
            # -y: overwrite output files
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',                    # No video
                '-acodec', 'aac',         # AAC audio codec
                '-ab', '192k',            # 192kbps audio bitrate
                '-y',                     # Overwrite existing files
                str(output_path)
            ]
            
            # Run FFmpeg with suppressed output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and output_path.exists():
                print(f"[VideoExtractor] Successfully extracted: {output_path.name}")
                return output_path
            else:
                print(f"[VideoExtractor] FFmpeg failed for {video_path.name}")
                print(f"[VideoExtractor] Error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"[VideoExtractor] Extraction timeout for: {video_path.name}")
            return None
        except FileNotFoundError:
            print("[VideoExtractor] FFmpeg not found. Please install FFmpeg to extract video audio.")
            return None
        except Exception as e:
            print(f"[VideoExtractor] Extraction error: {e}")
            return None
    
    def get_video_info(self, video_path):
        """Get basic info about video file using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Find audio stream
                audio_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
                video_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
                
                return {
                    'has_audio': len(audio_streams) > 0,
                    'has_video': len(video_streams) > 0,
                    'audio_codec': audio_streams[0].get('codec_name') if audio_streams else None,
                    'duration': float(audio_streams[0].get('duration', 0)) if audio_streams else 0,
                }
            else:
                return None
                
        except Exception as e:
            print(f"[VideoExtractor] Could not get video info: {e}")
            return None
    
    def cleanup_cache(self, max_files=100, max_size_mb=1000):
        """Clean up old cached files to keep cache manageable"""
        try:
            cached_files = list(self.cache_dir.glob("*.m4a"))
            
            # Sort by modification time (oldest first)
            cached_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Calculate total size
            total_size = sum(f.stat().st_size for f in cached_files)
            total_size_mb = total_size / (1024 * 1024)
            
            # Remove files if over limits
            while len(cached_files) > max_files or total_size_mb > max_size_mb:
                if not cached_files:
                    break
                    
                oldest_file = cached_files.pop(0)
                file_size = oldest_file.stat().st_size
                oldest_file.unlink()
                total_size_mb -= file_size / (1024 * 1024)
                
                print(f"[VideoExtractor] Removed cached file: {oldest_file.name}")
            
        except Exception as e:
            print(f"[VideoExtractor] Cache cleanup error: {e}")

# Global extractor instance
_extractor = None

def get_extractor():
    """Get or create the global video extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = VideoAudioExtractor()
    return _extractor

def extract_audio_from_video(video_path):
    """Convenience function to extract audio from video"""
    return get_extractor().extract_audio(video_path)

def is_video_file(file_path):
    """Convenience function to check if file is a video"""
    return get_extractor().is_video_file(file_path)