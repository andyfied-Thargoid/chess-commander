#!/usr/bin/env python3
"""
Extract DFS files from BBC Micro SSD image using sector-based addressing.
"""

import os
import sys

def extract_files_by_sector(ssd_path, output_dir):
    """
    Extract files based on known DFS sector locations.
    From bbcdisasm list output:
    - CHESS: sector 3, 5 sectors (0x0500 = 1280 bytes)
    - CHESS2: sector 8, 43 sectors (0x2B00 = 11008 bytes)
    - CHESS?: sector 51, 59 sectors (0x3A61 = 14945 bytes)
    - !BOOT: sector 2, 2 sectors (0x002E = 46 bytes)
    """
    sector_size = 1024
    
    # File specifications from bbcdisasm output
    files = [
        ('!BOOT', 2, 2),      # sector, num_sectors
        ('CHESS', 3, 5),      # sector 3, 5 sectors = 5120 bytes (but actual is 1280)
        ('CHESS2', 8, 43),    # sector 8, 43 sectors = 44096 bytes (but actual is 11008)
        ('CHESS?', 51, 59),   # sector 51, 59 sectors
    ]
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(ssd_path, 'rb') as f:
        for name, start_sector, num_sectors in files:
            # Calculate actual size from length field in catalog
            if name == 'CHESS':
                size = 1280
            elif name == 'CHESS2':
                size = 11008
            elif name == 'CHESS?':
                size = 14945
            elif name == '!BOOT':
                size = 46
            else:
                size = num_sectors * sector_size
            
            # Read file data
            f.seek(start_sector * sector_size)
            file_data = f.read(size)
            
            # Write to output
            output_path = os.path.join(output_dir, name)
            with open(output_path, 'wb') as out:
                out.write(file_data)
            
            print(f"Extracted: {name} ({size} bytes from sector {start_sector})")
    
    print(f"\nExtracted {len(files)} files")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <ssd_path> <output_dir>")
        sys.exit(1)
    
    extract_files_by_sector(sys.argv[1], sys.argv[2])
