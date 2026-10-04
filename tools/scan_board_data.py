#!/usr/bin/env python3
"""
Targeted scan for chess board representation in P-code.
Focus on finding:
- 64-byte blocks with piece values
- Specific patterns that indicate board state
"""

import os
from typing import List, Dict

def scan_for_board_data(filepath: str, name: str) -> Dict:
    """Scan a P-code file for board representation data."""
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    findings = {
        'file': name,
        'size': len(data),
        'board_regions': [],
        'piece_tables': [],
        'move_gen_data': [],
        'evaluation_data': []
    }
    
    # Look for 64-byte blocks with specific piece-like patterns
    # Common encoding: 0=empty, 1-6=pieces (P,N,B,R,Q,K), FF=black piece
    
    for i in range(0, len(data) - 64, 16):
        segment = data[i:i+64]
        
        # Count valid piece-like values
        piece_values = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF, 0xFE, 0xFD]
        piece_count = sum(1 for b in segment if b in piece_values)
        
        # Count zeros (empty squares)
        zero_count = segment.count(0x00)
        
        # Count 0xE5 padding
        e5_count = segment.count(0xE5)
        
        # If significant piece-like content and not mostly padding
        if piece_count > 20 and e5_count < 32:
            findings['board_regions'].append({
                'offset': i,
                'piece_count': piece_count,
                'zero_count': zero_count,
                'e5_count': e5_count,
                'hex': ' '.join(f'{b:02X}' for b in segment[:32])
            })
    
    # Also scan for move generation patterns
    # Look for sequences that might represent legal move tables
    
    findings['piece_tables'] = findings['board_regions']
    
    return findings


def main():
    """Analyze all chess files for board data."""
    
    files = [
        ('/tmp/acornsoft-extracted/CHESS', 'Acornsoft CHESS'),
        ('/tmp/acornsoft-extracted/CHESS2', 'Acornsoft CHESS2'),
        ('/tmp/acornsoft-extracted/CHESS?', 'Acornsoft CHESS?'),
        ('/tmp/thompson-extracted/CHESS', 'Thompson CHESS'),
        ('/tmp/thompson-extracted/CHESS2', 'Thompson CHESS2'),
        ('/tmp/thompson-extracted/CHESS?', 'Thompson CHESS?'),
    ]
    
    all_findings = []
    
    for filepath, name in files:
        if os.path.exists(filepath):
            findings = scan_for_board_data(filepath, name)
            all_findings.append(findings)
    
    # Print results
    for findings in all_findings:
        print(f"\n{'='*80}")
        print(f"{findings['file']} ({findings['size']} bytes)")
        print(f"{'='*80}")
        
        if findings['board_regions']:
            print(f"Found {len(findings['board_regions'])} potential board regions:")
            for region in findings['board_regions'][:5]:  # Show first 5
                print(f"  Offset 0x{region['offset']:04X}:")
                print(f"    Pieces: {region['piece_count']}, Zeros: {region['zero_count']}, Padding: {region['e5_count']}")
                print(f"    Data: {region['hex']}")
        else:
            print("No clear board representation found in CHESS file")
            print("Board data may be embedded in P-code strings or in CHESS2/CHESS?")


if __name__ == '__main__':
    main()
