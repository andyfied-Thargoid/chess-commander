#!/usr/bin/env python3
"""
Deep analysis of Acornsoft CHESS2 for board representation data.
"""

import struct

def main():
    print("=" * 80)
    print("ACORNSOFT CHESS2 - DEEP ANALYSIS")
    print("=" * 80)
    
    # Load CHESS2
    with open('/tmp/acornsoft-extracted/CHESS2', 'rb') as f:
        data = f.read()
    
    print(f'Total size: {len(data)} bytes')
    
    # Extract strings
    strings = []
    i = 0
    while i < len(data):
        if data[i] == 0x22:  # String start
            end = data.find(0x0D, i+1)
            if end != -1:
                raw = data[i+1:end]
                # Decode BBC character set
                decoded = ''
                for b in raw:
                    translations = {
                        0x83: ' ', 0x84: '.', 0x85: '`', 0x86: "'",
                        0x87: '"', 0x88: '(', 0x89: ')', 0x8A: '[',
                        0x8B: ']', 0x8C: '<', 0x8D: '>', 0x8E: '!',
                        0x8F: '?', 0x90: '@', 0x91: '&', 0x92: '#',
                        0x93: "'", 0x94: "'", 0x95: '$', 0x96: '%',
                        0x97: '^', 0x98: '*', 0x99: '\\', 0x9A: '|',
                        0x9B: '~', 0x9C: '-', 0x9D: '_', 0x9E: '+', 0x9F: '='
                    }
                    decoded += translations.get(b, chr(b))
                
                if decoded.strip():
                    strings.append((i, decoded.strip()))
                i = end + 1
            else:
                i += 1
        else:
            i += 1
    
    print(f'\nFound {len(strings)} string constants')
    print('\n--- Key Strings (first 30) ---')
    for offset, content in strings[:30]:
        print(f'0x{offset:04X}: {content[:80]}')
    
    # Scan for board data (64-byte regions with piece-like values)
    print('\n--- Scanning for 64-byte board regions ---')
    found_regions = []
    for i in range(0, len(data)-64, 16):
        segment = data[i:i+64]
        
        # Count piece-like values
        piece_values = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF, 0xFE]
        piece_count = sum(1 for b in segment if b in piece_values)
        
        # Also check for move offset patterns
        offset_values = [b for b in segment if 0x00 <= b <= 0x7F or b == 0xFF]
        offset_count = len(offset_values)
        
        if piece_count > 30 or offset_count > 40:
            found_regions.append({
                'offset': i,
                'piece_count': piece_count,
                'offset_count': offset_count,
                'data': segment
            })
            print(f'0x{i:04X}: {piece_count} piece-like, {offset_count} offset-like bytes')
            print(f'  Data: {" ".join(f"{b:02X}" for b in segment[:32])}')
            print()
    
    print(f'Total potential board regions: {len(found_regions)}')
    
    # Also scan for evaluation coefficients
    print('\n--- Scanning for evaluation coefficient blocks ---')
    for i in range(0, len(data)-16, 8):
        segment = data[i:i+16]
        
        # Check for signed byte patterns
        signed = [b if b < 128 else b-256 for b in segment]
        unique = len(set(signed))
        
        # Evaluation tables often have few unique values
        if unique < 8 and sum(1 for b in segment if 0x80 <= b < 0xFF) > 4:
            print(f'0x{i:04X}: {unique} unique signed values')
            print(f'  Data: {" ".join(f"{b:02X}" for b in segment)}')
            print(f'  Signed: {" ".join(str(v) for v in signed)}')
            print()

if __name__ == '__main__':
    main()
