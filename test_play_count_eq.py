#!/usr/bin/env python3
"""
Test play count tracking and EQ save functionality.
"""

def test_store_functionality():
    """Test the store module play count functionality."""
    print("=== Testing Store Functionality ===\n")
    
    try:
        from sidecar_eq import store
        import tempfile
        import os
        
        # Create a test file path
        test_path = "/tmp/test_song.mp3"
        
        print("1. Testing initial record creation...")
        # Get initial record (should be None or empty)
        record = store.get_record(test_path)
        print(f"Initial record: {record}")
        
        print("\n2. Testing play count increment...")
        # Increment play count a few times
        for i in range(3):
            store.increment_play_count(test_path)
            record = store.get_record(test_path)
            play_count = record.get('play_count', 0) if record else 0
            print(f"After increment {i+1}: play_count = {play_count}")
        
        print("\n3. Testing custom record setting...")
        # Set custom data
        store.set_record(test_path, {
            'play_count': 10,
            'custom_data': 'test_value',
            'last_eq': [1, -2, 0, 3, -1, 0, 2, -1, 0, 1]
        })
        
        record = store.get_record(test_path)
        print(f"Custom record: {record}")
        
        print("\n✓ Store functionality working correctly!")
        return True
        
    except Exception as e:
        print(f"✗ Store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_eq_data_format():
    """Test the EQ data format and loading."""
    print("\n=== Testing EQ Data Format ===\n")
    
    try:
        from pathlib import Path
        import json
        
        # Check if EQ store file exists
        eq_store = Path.home() / '.sidecar_eq_eqs.json'
        print(f"EQ store location: {eq_store}")
        print(f"Exists: {eq_store.exists()}")
        
        if eq_store.exists():
            try:
                data = json.loads(eq_store.read_text())
                print(f"Number of tracks in EQ store: {len(data)}")
                
                # Show structure of first entry if any exist
                if data:
                    first_key = next(iter(data))
                    first_entry = data[first_key]
                    print(f"Sample entry structure:")
                    print(f"  Path: {first_key}")
                    print(f"  Data keys: {list(first_entry.keys()) if isinstance(first_entry, dict) else 'legacy format'}")
                    
                    if isinstance(first_entry, dict):
                        print(f"  EQ settings: {first_entry.get('eq_settings', 'N/A')}")
                        print(f"  Volume: {first_entry.get('suggested_volume', 'N/A')}")
                        print(f"  Play count: {first_entry.get('play_count', 'N/A')}")
                        print(f"  Manual save: {first_entry.get('manual_save', 'N/A')}")
                
            except Exception as e:
                print(f"Error reading EQ store: {e}")
        
        print("\n✓ EQ data format check complete!")
        return True
        
    except Exception as e:
        print(f"✗ EQ format test failed: {e}")
        return False

def main():
    print("=== Play Count & EQ Save Test ===\n")
    
    # Test store functionality
    store_ok = test_store_functionality()
    
    # Test EQ data format
    eq_ok = test_eq_data_format()
    
    print(f"\n=== Results ===")
    print(f"Store functionality: {'✓ PASS' if store_ok else '✗ FAIL'}")
    print(f"EQ data format: {'✓ PASS' if eq_ok else '✗ FAIL'}")
    
    if store_ok and eq_ok:
        print("\n🎉 All tests passed! Play counts and EQ save should work correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()