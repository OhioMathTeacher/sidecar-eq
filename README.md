# Sidecar EQ (working title)

A minimalist, queue-first music player that **analyzes tracks on first play** and remembers a **per-track EQ**. Finder-like list view. No bloated library. Playlists are plain files.

## Why
Global EQ ≠ every track. Sidecar EQ blends **analysis** (librosa/essentia) with your **taste curve** and auto-applies it next time.

## MVP
- Queue UI (add files/folders, remove, reorder)
- Playback (pause/skip/volume)
- First-play analysis → 10-band curve + preamp
- Per-track store: path, play_count, last_played, eq_profile
- Save/load playlists (JSON, M3U)
- Simple 7-band “taste” sliders

## Build
```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -e .
python -m sidecar_eq.app
