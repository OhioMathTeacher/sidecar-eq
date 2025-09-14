# Sidecar EQ (working title)

A minimalist, Finder-style player. On first play it analyzes the track, generates a 10-band EQ, blends it with your 7-band preference, and remembers it—so playback matches the music, not the other way around.

## Run (dev)
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python -m sidecar_eq.app
```

## Optional YouTube support (yt-dlp)

Sidecar EQ can optionally accept YouTube page URLs in the UI. This uses the external tool `yt-dlp` to resolve direct stream URLs or download audio to a temporary file. This feature is opt-in and requires `yt-dlp` to be installed in the same Python environment.

Install the optional dependency into the venv:

```bash
/Users/todd/sidecar-eq/.venv/bin/python -m pip install -e .[yt]
# or separately:
/Users/todd/sidecar-eq/.venv/bin/python -m pip install yt-dlp
```

Notes:
- Some videos may require signing-in or browser cookies (yt-dlp will print a message like "Sign in to confirm you’re not a bot"). In those cases you can provide a cookies file to yt-dlp with `--cookies PATH`.
- Downloading or programmatic access to third-party content may be subject to that site's Terms of Service. This feature is optional; we recommend users only play content they have rights to use.

