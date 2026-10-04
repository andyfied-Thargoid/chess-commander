#!/usr/bin/env python3
"""
Deep P-code analysis for Acornsoft CHESS.
Identify data structures embedded in P-code opcodes.
"""

import struct
from typing import List, Dict, Any

def analyze_pcode_structure(pcode: bytes) -> Dict[str, Any]:
    """Analyze P-code for data structures."""
    
    results = {
        'opcode_distribution': {},
        'potential_data_regions': [],
        'string_blocks': [],
        'numeric_constants': [],
        'jump_targets': []
    }
    
    # Analyze opcode distribution
    for i, byte in enumerate(pcode):
        results['opcode_distribution'][hex(byte)] = results['opcode_distribution'].get(hex(byte), 0) + 1
    
    # Find data regions (non-P-code opcodes)
    # BBC P-code opcodes: 0x22, 0x62, 0x70, 0x84, 0x95, 0x9B, 0xF1, 0xF5, 0xF6, 0x0D, etc.
    pcode_opcodes = set([
        0x22, 0x62, 0x70, 0x84, 0x95, 0x9B, 0xF1, 0xF5, 0xF6,  # P-code
        0x0D, 0x0A, 0x00,  # Control chars
        0x20, 0x30-0x39,  # ASCII
    ])
    
    # Scan for sequences that look like data
    i = 0
    while i < len(pcode) - 16:
        segment = pcode[i:i+16]
        
        # Check if segment looks like data (not P-code)
        non_pcode = sum(1 for b in segment if b not in pcode_opcodes and not (0x20 <= b <= 0x7E))
        
        if non_pcode > 8:  # More than half non-P-code
            results['potential_data_regions'].append({
                'offset': i,
                'size': 16,
                'hex': segment.hex(),
                'non_pcode_ratio': non_pcode / 16
            })
        
        i += 4
    
    # Find numeric constant sequences
    i = 0
    while i < len(pcode):
        if pcode[i] == 0x84:  # Numeric constant
            if i + 1 < len(pcode):
                value = pcode[i + 1]
                results['numeric_constants'].append({
                    'offset': i,
                    'value': value,
                    'hex': f'{pcode[i]:02X}{pcode[i+1]:02X}'
                })
        i += 1
    
    # Find GOSUB/Function targets
    i = 0
    while i < len(pcode) - 2:
        if pcode[i] in [0x62, 0x95]:  # GOSUB or FUNCTION
            target = struct.unpack('<H', pcode[i + 1:i + 3])[0]
            results['jump_targets'].append({
                'offset': i,
                'opcode': 'GOSUB' if pcode[i] == 0x62 else 'FUNCTION',
                'target': target,
                'hex': pcode[i:i+3].hex()
            })
        i += 1
    
    return results


def identify_move_generation_patterns(pcode: bytes) -> List[Dict]:
    """Look for move generation table patterns."""
    
    patterns = []
    
    # Search for 64-byte blocks with move offset patterns
    for i in range(0, len(pcode) - 64, 8):
        segment = pcode[i:i+64]
        
        # Look for sequences like: 00 01 02 03 04 05 (piece moves)
        # Or: FF FE FD FC FB FA (reverse)
        # Or: 00 08 10 18 20 28 30 38 (rank offsets)
        
        # Check for incremental patterns
        increments = []
        for j in range(len(segment) - 1):
            diff = segment[j + 1] - segment[j]
            if -16 <= diff <= 16 and diff != 0:
                increments.append(diff)
        
        # If many small increments, might be move table
        if len(increments) > 30:
            avg_increment = sum(abs(x) for x in increments) / len(increments)
            if avg_increment < 10:  # Small moves
                patterns.append({
                    'offset': i,
                    'type': 'incremental_pattern',
                    'avg_increment': avg_increment,
                    'sample': segment.hex()
                })
    
    return patterns


def main():
    """Analyze Acornsoft CHESS P-code structure."""
    
    print("=" * 80)
    print("ACORNSOFT CHESS V2.1 - P-CODE STRUCTURE ANALYSIS")
    print("=" * 80)
    
    with open('/tmp/acornsoft-extracted/CHESS', 'rb') as f:
        pcode = f.read()
    
    print(f"Total P-code size: {len(pcode)} bytes")
    
    results = analyze_pcode_structure(pcode)
    
    print("\n--- Opcode Distribution (most common) ---")
    sorted_opcodes = sorted(results['opcode_distribution'].items(), key=lambda x: -x[1])
    for opcode, count in sorted_opcodes[:20]:
        print(f"{opcode}: {count} occurrences ({count/len(pcode)*100:.1f}%)")
    
    print("\n--- Potential Data Regions ---")
    for region in results['potential_data_regions'][:10]:
        print(f"0x{region['offset']:04X} ({region['size']} bytes): {region['hex']}")
        print(f"  Non-P-code ratio: {region['non_pcode_ratio']*100:.1f}%")
    
    print("\n--- Numeric Constants ---")
    for const in results['numeric_constants'][:10]:
        print(f"0x{const['offset']:04X}: value={const['value']} ({hex(const['value'])})")
    
    print("\n--- GOSUB/Function Targets ---")
    for target in results['jump_targets']:
        print(f"0x{target['offset']:04X} -> 0x{target['target']:04X} ({target['opcode']})")
    
    # Look for move generation patterns
    print("\n--- Move Generation Pattern Analysis ---")
    patterns = identify_move_generation_patterns(pcode)
    print(f"Found {len(patterns)} incremental patterns")
    for pattern in patterns[:5]:
        print(f"0x{pattern['offset']:04X}: avg increment={pattern['avg_increment']:.1f}")
        print(f"  Sample: {pattern['sample']}")


if __name__ == '__main__':
    main()
