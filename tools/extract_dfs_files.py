#!/usr/bin/env python3
"""
Extract DFS files from BBC Micro SSD image.
DFS format: 256-byte sector headers + 1024-byte data sectors
"""

import struct
import os
import sys

def read_dfs_catalog(ssd_path):
    """Read DFS catalog from SSD image."""
    catalog_entries = []
    
    with open(ssd_path, 'rb') as f:
        # DFS uses 1024-byte sectors
        sector_size = 1024
        
        # Read catalog sector (sector 0)
        catalog_data = f.read(sector_size)
        
        # Parse catalog entries
        offset = 0
        while offset < sector_size - 4:
            # Each entry starts with 4-byte marker
            marker = struct.unpack('<I', catalog_data[offset:offset+4])[0]
            
            # DFS entry marker
            if marker == 0x0A1A:  # End of catalog
                break
            elif marker & 0xFF000000 == 0x01000000:  # File entry
                length = struct.unpack('<I', catalog_data[offset:offset+4])[0]
                load_addr = struct.unpack('<H', catalog_data[offset+4:offset+6])[0]
                exec_addr = struct.unpack('<H', catalog_data[offset+6:offset+8])[0]
                
                # Filename is at offset+8, null-terminated
                filename = catalog_data[offset+8:offset+24].decode('ascii', errors='replace').rstrip('\x00')
                
                catalog_entries.append({
                    'name': filename,
                    'load_addr': load_addr,
                    'exec_addr': exec_addr,
                    'length': length
                })
                
                offset += 24
            else:
                offset += 4
    
    return catalog_entries

def extract_files(ssd_path, output_dir):
    """Extract all files from SSD image."""
    catalog = read_dfs_catalog(ssd_path)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(ssd_path, 'rb') as f:
        sector_size = 1024
        
        for entry in catalog:
            # Convert BASIC filename (6 chars, bit 5 determines case)
            # Extract safe name by taking first 6 chars
            safe_name = ''.join(c for c in entry['name'][:6] if c.isalnum() or c in '_.-')
            if not safe_name:
                safe_name = f"file_{entry['load_addr']:04X}"
            
            if safe_name in ['[FILLER]', '', ' ']:
                continue
            
            # Calculate sector positions
            start_sector = entry['load_addr'] // sector_size
            num_sectors = (entry['length'] + sector_size - 1) // sector_size
            
            # Read file data
            f.seek(start_sector * sector_size)
            file_data = f.read(num_sectors * sector_size)
            
            # Write to output
            output_path = os.path.join(output_dir, safe_name)
            with open(output_path, 'wb') as out:
                out.write(file_data[:entry['length']])
            
            print(f"Extracted: {safe_name} ({entry['length']} bytes at 0x{entry['load_addr']:04X})")
    
    file_count = len([e for e in catalog if e['name'] not in ['[FILLER]', '', ' ']])
    print(f"Extracted {file_count} files")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <ssd_path> <output_dir>")
        sys.exit(1)
    
    extract_files(sys.argv[1], sys.argv[2])
