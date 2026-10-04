#!/usr/bin/env python3
"""
Extract DFS files from BBC Micro SSD image.
Correct DFS format parsing.
"""

import struct
import os
import sys

def read_dfs_catalog(ssd_path):
    """Read DFS catalog from SSD image sector 0."""
    catalog_entries = []
    sector_size = 1024
    
    with open(ssd_path, 'rb') as f:
        catalog_data = f.read(sector_size)
    
    # DFS catalog entries are 16 bytes each:
    # Bytes 0-5: Filename (6 chars)
    # Byte 6: Attributes (0xA4 = PRG, 0x00 = DIR, etc.)
    # Byte 7: Length in 256-byte blocks
    # Bytes 8-9: Load address (little-endian)
    # Bytes 10-11: Execution address (little-endian)
    # Bytes 12-15: Filler/next entry pointer
    
    offset = 0
    while offset < sector_size - 16:
        filename = catalog_data[offset:offset+6].decode('ascii', errors='replace')
        attributes = catalog_data[offset+6]
        length_blocks = catalog_data[offset+7]
        load_addr = struct.unpack('<H', catalog_data[offset+8:offset+10])[0]
        exec_addr = struct.unpack('<H', catalog_data[offset+10:offset+12])[0]
        
        # Skip empty entries
        if filename.strip():
            catalog_entries.append({
                'name': filename,
                'attrs': attributes,
                'length_blocks': length_blocks,
                'load_addr': load_addr,
                'exec_addr': exec_addr
            })
        
        # Move to next entry (16 bytes)
        offset += 16
        
        # Check for end marker (0x0000 in next entry position)
        if offset < sector_size:
            next_entry = struct.unpack('<H', catalog_data[offset:offset+2])[0]
            if next_entry == 0:
                break
    
    return catalog_entries

def extract_files(ssd_path, output_dir):
    """Extract all files from SSD image."""
    catalog = read_dfs_catalog(ssd_path)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(ssd_path, 'rb') as f:
        for entry in catalog:
            # Sanitize filename
            safe_name = ''.join(c for c in entry['name'].strip() if c.isalnum() or c in '_.-')
            if not safe_name or safe_name in ['FILLER', '[FILLER]']:
                continue
            
            # Calculate sector positions
            sector_size = 1024
            start_sector = entry['load_addr'] // sector_size
            length_bytes = entry['length_blocks'] * 256
            
            # Read file data
            f.seek(start_sector * sector_size)
            file_data = f.read(length_bytes)
            
            # Write to output
            output_path = os.path.join(output_dir, safe_name)
            with open(output_path, 'wb') as out:
                out.write(file_data[:length_bytes])
            
            print(f"Extracted: {safe_name} ({length_bytes} bytes, load=0x{entry['load_addr']:04X}, exec=0x{entry['exec_addr']:04X})")
    
    file_count = len([e for e in catalog if e['name'].strip() and e['name'].strip() not in ['FILLER', '[FILLER]']])
    print(f"\nExtracted {file_count} files")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <ssd_path> <output_dir>")
        sys.exit(1)
    
    extract_files(sys.argv[1], sys.argv[2])
