Changelog - Sidecar EQ

2025-09-14 — Cleanup & UI polish

- Fixed structural corruption in `sidecar_eq/app.py` where toolbar code was accidentally inserted inside `KnobWidget.mousePressEvent`.
- Restored `MainWindow` class scope and added a safe `__init__` to initialize `model`, `table`, and `player`.
- Moved source toggles into the toolbar and implemented a single Add button driven by the Source selector.
- Converted Add to an `IconButton` using `icons/addsongs.svg` and its hover/pressed variants when available.
- Swapped toolbar semantics: Download now invokes Add (adds into queue); Upload performs Save Playlist.
- Implemented right-side dock controls: woodgrain knob (volume), EQ faders with animated glow and blurred backdrop, Save EQ per-track, and Recently Played.
- Replaced non-draggable progress bar with a draggable time slider wired to player position/duration.
- Removed temporary placeholder "curtain" and set `QTableView` as the central widget.
- Implemented dock sizing helper to give the right dock a minimum width (~35% or min 320px).
- Added `tests/smoke_test.py` and ran smoke tests to verify initialization paths.
- Tuned EQ slider glow for better visibility.

Notes / Next steps

- Finish polishing `MainWindow.__init__`: fully wire persisted state (window/dock sizes), splitter locking (if desired), and save/restore preferences.
- Consider converting other toolbar items (Download/Upload/Remove) to `IconButton` for consistent hover/pressed UX.
- Unit tests: add tests for toolbar action wiring and EQ persistence.
- UX polish: tweak icon spacing, knob styling, and recently-played presentation.
- Security: if the repo ever contained secrets, rotate tokens and add `.env` to `.gitignore` (already discussed earlier).

How to run locally

1. Activate the project's virtualenv: `/Users/todd/sidecar-eq/.venv/bin/python -m venv` (or your preferred activation).
2. Run the app:

   /Users/todd/sidecar-eq/.venv/bin/python -m sidecar_eq.app

3. Run smoke tests:

   /Users/todd/sidecar-eq/.venv/bin/python tests/smoke_test.py
