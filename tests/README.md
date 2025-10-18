# Tests

This directory contains all test files for Sidecar EQ.

## Test Categories

### Unit Tests
- `test_eq_7_band.py` - 7-band EQ tests
- `test_eq_analysis.py` - EQ analysis tests
- `test_eq_interface.py` - EQ interface tests
- `test_file_validation.py` - File validation tests
- `test_source_default.py` - Default source tests

### Integration Tests
- `test_integration.py` - Main integration tests
- `test_integration_root.py` - Root-level integration tests
- `test_url_integration.py` - URL integration tests

### Feature Tests
- `test_analysis.py` - Audio analysis tests
- `test_background_analysis.py` - Background analysis tests
- `test_library.py` - Library system tests
- `test_online_metadata.py` - Online metadata fetching tests
- `test_play_count_eq.py` - Play count and EQ tests
- `test_queue_persistence.py` - Queue persistence tests
- `test_url_handling.py` - URL handling tests
- `test_video_extraction.py` - Video extraction tests

### Plex Tests
- `test_plex_playback.py` - Plex playback tests
- `test_plex_simple.py` - Simple Plex tests

### UI Tests
- `test_ui.py` - UI component tests
- `test_workers.py` - Worker thread tests

### Other
- `smoke_test.py` - Quick smoke test
- `conftest.py` - Pytest configuration

## Running Tests

Run all tests:
```bash
python -m pytest tests/ -v
```

Run specific test file:
```bash
python -m pytest tests/test_library.py -v
```

Run smoke test:
```bash
python tests/smoke_test.py
```
