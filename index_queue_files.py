#!/usr/bin/env python3
"""Quick script to index music from current queue for testing."""

import json
from pathlib import Path
import sys

# Add sidecar_eq to path
sys.path.insert(0, str(Path(__file__).parent))

from sidecar_eq.indexer import LibraryIndexer

def main():
    """Index files from saved queue state."""
    queue_state = Path.home() / ".sidecar_eq" / "queue_state.json"
    
    if not queue_state.exists():
        print("No saved queue found. Please add some music to the app first!")
        return
        
    # Load queue
    with open(queue_state, 'r') as f:
        queue_data = json.load(f)
        
    paths = queue_data.get('paths', [])
    if not paths:
        print("Queue is empty. Add some music files first!")
        return
        
    print(f"Found {len(paths)} tracks in queue. Indexing...")
    
    # Create indexer
    indexer = LibraryIndexer()
    
    # Index each file
    indexed = 0
    for path in paths:
        file_path = Path(path)
        if file_path.exists():
            metadata = indexer._extract_metadata(file_path)
            if metadata:
                indexer.index[str(file_path.absolute())] = metadata
                indexed += 1
                print(f"✓ {file_path.name}")
        else:
            print(f"✗ File not found: {path}")
            
    # Save index
    indexer.save_index()
    
    print(f"\n✅ Indexed {indexed} tracks!")
    print("Now restart the app and try searching!")

if __name__ == "__main__":
    main()
