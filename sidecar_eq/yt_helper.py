import subprocess
import tempfile
import shutil
from typing import Tuple, Optional

YT_DLP = shutil.which("yt-dlp") or shutil.which("youtube-dl")


def resolve_or_download(page_url: str, download_if_needed: bool = True) -> Tuple[bool, Optional[str], Optional[str]]:
    """Try to resolve a direct playable URL for page_url using yt-dlp.

    Returns (success, source, message).
    - If success is True, source is a URL or local file path playable by QMediaPlayer.
    - If success is False, message contains an error description.
    """
    if YT_DLP is None:
        return False, None, "yt-dlp not found on PATH"

    # 1) Ask yt-dlp for a direct URL
    try:
        p = subprocess.run([YT_DLP, "-f", "bestaudio", "-g", page_url], capture_output=True, text=True, check=False)
    except Exception as e:
        return False, None, f"yt-dlp error: {e}"

    if p.returncode == 0 and p.stdout.strip():
        return True, p.stdout.strip().splitlines()[0], None

    stderr = (p.stderr or "").strip()

    # detect common sign-in/captcha message
    if "Sign in to confirm" in stderr or "captcha" in stderr.lower():
        return False, None, "Video requires sign-in or captcha; provide cookies or download manually"

    # 2) If resolution failed and we're allowed to download, download to a temp file
    if download_if_needed:
        tmp = tempfile.NamedTemporaryFile(prefix="sidecar_eq_yt_", suffix=".%(ext)s", delete=False)
        tmp.close()
        cmd = [YT_DLP, "-f", "bestaudio", "-o", tmp.name, page_url]
        p2 = subprocess.run(cmd, capture_output=True, text=True)
        if p2.returncode == 0:
            return True, tmp.name, None
        return False, None, (p2.stderr or p2.stdout or "yt-dlp download failed").strip()

    return False, None, stderr or "could not resolve URL"
