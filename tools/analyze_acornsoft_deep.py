#!/usr/bin/env python3
"""
Deep P-code analysis for Acornsoft Chess.
Focus on:
1. Extracting all P-code strings and their positions
2. Identifying data regions between strings
3. Mapping GOSUB targets to find move generation routines
4. Analyzing P-code opcodes to understand algorithm structure
"""

import struct
from typing import List, Dict, Tuple, Any, Optional

class AcornsoftPCodeAnalyzer:
    def __init__(self, pcode_data: bytes):
        self.data = pcode_data
        self.offset = 0
        
    def extract_all_strings(self) -> List[Dict]:
        """Extract all string constants with their positions."""
        strings = []
        i = 0
        
        while i < len(self.data):
            if self.data[i] == 0x22:  # String start
                # Find string end (0x0D)
                end = self.data.find(0x0D, i + 1)
                if end != -1:
                    raw_string = self.data[i + 1:end]
                    # Decode BBC character set
                    decoded = self._decode_bbc_text(raw_string)
                    
                    strings.append({
                        'offset': i,
                        'length': end - i,
                        'raw': raw_string,
                        'decoded': decoded,
                        'clean': decoded.strip()
                    })
                    i = end + 1
                else:
                    i += 1
            else:
                i += 1
        
        return strings
    
    def _decode_bbc_text(self, data: bytes) -> str:
        """Decode BBC BASIC text with special characters."""
        result = []
        for b in data:
            # BBC character set translations
            translations = {
                0x83: ' ', 0x84: '.', 0x85: '`', 0x86: "'",
                0x87: '"', 0x88: '(', 0x89: ')', 0x8A: '[',
                0x8B: ']', 0x8C: '<', 0x8D: '>', 0x8E: '!',
                0x8F: '?', 0x90: '@', 0x91: '&', 0x92: '#',
                0x93: "'", 0x94: "'", 0x95: '$', 0x96: '%',
                0x97: '^', 0x98: '*', 0x99: '\\', 0x9A: '|',
                0x9B: '~', 0x9C: '-', 0x9D: '_', 0x9E: '+',
                0x9F: '='
            }
            result.append(translations.get(b, chr(b)))
        return ''.join(result)
    
    def map_gosub_routines(self) -> List[Dict]:
        """Map all GOSUB calls and their destinations."""
        routines = []
        i = 0
        
        while i < len(self.data):
            opcode = self.data[i]
            
            if opcode == 0x62 and i + 2 < len(self.data):  # GOSUB
                dest = struct.unpack('<H', self.data[i + 1:i + 3])[0]
                routines.append({
                    'offset': i,
                    'destination': dest,
                    'type': 'gosub'
                })
                i += 3
            elif opcode == 0x95 and i + 2 < len(self.data):  # Function call
                target = struct.unpack('<H', self.data[i + 1:i + 3])[0]
                routines.append({
                    'offset': i,
                    'target': target,
                    'type': 'function'
                })
                i += 3
            else:
                i += 1
        
        return routines
    
    def find_data_gaps(self) -> List[Dict]:
        """Find regions between strings that might contain data."""
        gaps = []
        strings = self.extract_all_strings()
        
        # Sort strings by offset
        strings.sort(key=lambda x: x['offset'])
        
        # Find gaps between strings
        for i in range(len(strings) - 1):
            start = strings[i]['offset'] + strings[i]['length']
            end = strings[i + 1]['offset']
            
            if end - start > 16:  # Only consider gaps > 16 bytes
                gap_data = self.data[start:end]
                gaps.append({
                    'start': start,
                    'end': end,
                    'size': end - start,
                    'data': gap_data,
                    'unique_bytes': len(set(gap_data)),
                    'e5_count': gap_data.count(0xE5),
                    'zero_count': gap_data.count(0x00)
                })
        
        return gaps
    
    def analyze_move_generation_candidates(self) -> List[Dict]:
        """Identify potential move generation code regions."""
        candidates = []
        
        # Look for patterns typical of move generation:
        # - Piece move tables (64 entries x offsets)
        # - Bitboard masks
        # - Direction vectors
        
        i = 0
        while i < len(self.data) - 64:
            segment = self.data[i:i+64]
            
            # Check for move offset patterns
            # Look for sequences like 0x00-0x7F (move offsets)
            valid_offsets = sum(1 for b in segment if 0x00 <= b <= 0x7F)
            
            if valid_offsets > 40:
                candidates.append({
                    'offset': i,
                    'size': 64,
                    'valid_offsets': valid_offsets,
                    'pattern': 'move_offset_table'
                })
            
            i += 8
        
        return candidates
    
    def analyze_piece_tables(self) -> List[Dict]:
        """Identify potential piece tables."""
        tables = []
        
        i = 0
        while i < len(self.data) - 64:
            segment = self.data[i:i+64]
            
            # Count piece-like values
            piece_values = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF, 0xFE]
            piece_count = sum(1 for b in segment if b in piece_values)
            
            if piece_count > 20:
                tables.append({
                    'offset': i,
                    'size': 64,
                    'piece_count': piece_count,
                    'data': segment,
                    'hex': ' '.join(f'{b:02X}' for b in segment)
                })
            
            i += 8
        
        return tables
    
    def full_analysis(self) -> Dict[str, Any]:
        """Run full analysis and return structured results."""
        return {
            'total_size': len(self.data),
            'strings': self.extract_all_strings(),
            'routines': self.map_gosub_routines(),
            'data_gaps': self.find_data_gaps(),
            'move_candidates': self.analyze_move_generation_candidates(),
            'piece_tables': self.analyze_piece_tables()
        }


def main():
    """Analyze Acornsoft CHESS file in detail."""
    
    with open('/tmp/acornsoft-extracted/CHESS', 'rb') as f:
        data = f.read()
    
    print("=" * 80)
    print("ACORNSOFT CHESS V2.1 - DEEP P-CODE ANALYSIS")
    print("=" * 80)
    
    analyzer = AcornsoftPCodeAnalyzer(data)
    results = analyzer.full_analysis()
    
    print(f"\nTotal P-code size: {results['total_size']} bytes")
    print(f"String constants: {len(results['strings'])}")
    print(f"GOSUB/Function calls: {len(results['routines'])}")
    print(f"Data gaps: {len(results['data_gaps'])}")
    print(f"Move generation candidates: {len(results['move_candidates'])}")
    print(f"Potential piece tables: {len(results['piece_tables'])}")
    
    print("\n--- All String Constants (with positions) ---")
    for i, s in enumerate(results['strings']):
        if s['clean']:
            print(f"[{i:3d}] 0x{s['offset']:04X}: {s['clean'][:80]}")
    
    print("\n--- GOSUB/Function Routines ---")
    for i, r in enumerate(results['routines'][:20]):  # Show first 20
        print(f"[{i:3d}] 0x{r['offset']:04X} -> 0x{r.get('destination', r.get('target', 0)):04X} ({r['type']})")
    
    print("\n--- Data Gaps (potential embedded data) ---")
    for i, gap in enumerate(results['data_gaps']):
        if gap['size'] > 32 and gap['e5_count'] < 20:  # Show meaningful gaps
            print(f"[{i:3d}] 0x{gap['start']:04X}-0x{gap['end']:04X} ({gap['size']} bytes)")
            print(f"     Unique: {gap['unique_bytes']}, Zeros: {gap['zero_count']}, E5: {gap['e5_count']}")
            # Show hex sample
            sample = gap['data'][:32]
            print(f"     Data: {' '.join(f'{b:02X}' for b in sample)}")
    
    print("\n--- Move Generation Candidates ---")
    for i, candidate in enumerate(results['move_candidates'][:5]):
        print(f"[{i:3d}] 0x{candidate['offset']:04X}: {candidate['valid_offsets']} valid offsets")
    
    print("\n--- Potential Piece Tables ---")
    for i, table in enumerate(results['piece_tables'][:5]):
        print(f"[{i:3d}] 0x{table['offset']:04X}: {table['piece_count']} piece-like bytes")
        print(f"     Data: {table['hex']}")


if __name__ == '__main__':
    main()
