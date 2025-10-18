# Scripts

Utility scripts for building, setup, and maintenance.

## Build Scripts
- `build.sh` - Main build script for creating distributable packages
- `build_config.py` - Build configuration settings
- `setup.py` - Python package setup script
- `setup_py2app.py` - macOS app packaging with py2app

## Plex Utilities
- `get_plex_token.py` - Retrieve Plex authentication token
- `import_plex_to_library.py` - Import Plex library to local index

## Testing & Diagnostics
- `create_eq_test_files.py` - Generate test audio files with different EQ profiles
- `diagnose_jgeils.py` - Diagnostic script for J. Geils Band metadata issue
- `index_queue_files.py` - Index files in queue for testing

## Usage Examples

### Build macOS App
```bash
bash scripts/build.sh
```

### Get Plex Token
```bash
python scripts/get_plex_token.py
```

### Import Plex Library
```bash
python scripts/import_plex_to_library.py
```

### Create Test Files
```bash
python scripts/create_eq_test_files.py
```
