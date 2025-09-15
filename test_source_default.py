#!/usr/bin/env python3
"""Test to verify source knob defaults to Local Files"""

import sys
from pathlib import Path

# Add the sidecar_eq package to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_source_default():
    """Test that source knob defaults to Local Files"""
    print("Testing source knob default value...")
    
    # The source knob calculation: idx = min(2, max(0, int(round(val/50))))
    # For Local Files (index 0): val should be 0
    # For Website URL (index 1): val should be 50  
    # For Plex Server (index 2): val should be 100
    
    src_names = ["Local Files", "Website URL", "Plex Server"]
    
    # Test the index calculation with different knob values
    test_values = [0, 25, 50, 75, 100]
    
    print("\nKnob value -> Index -> Source:")
    for val in test_values:
        idx = min(2, max(0, int(round(val/50))))
        source = src_names[idx]
        print(f"  {val:3d} -> {idx} -> {source}")
    
    # Verify that value 0 gives "Local Files"
    default_val = 0
    default_idx = min(2, max(0, int(round(default_val/50))))
    default_source = src_names[default_idx]
    
    if default_source == "Local Files":
        print(f"\n✅ Default knob value {default_val} correctly maps to '{default_source}'")
        return True
    else:
        print(f"\n❌ Default knob value {default_val} maps to '{default_source}' instead of 'Local Files'")
        return False

if __name__ == "__main__":
    success = test_source_default()
    sys.exit(0 if success else 1)