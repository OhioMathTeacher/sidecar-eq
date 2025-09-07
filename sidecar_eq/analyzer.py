# Stub for Issue 6 — real librosa analysis will come later.

def analyze(path: str) -> dict:
    """
    Return a placeholder 10-band profile.
    """
    return {
        "bands_hz": [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000],
        "gains_db": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "preamp_db": -3.0,
    }
