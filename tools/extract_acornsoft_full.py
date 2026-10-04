#!/usr/bin/env python3
"""
Extract detailed P-code structure from Acornsoft CHESS file.
Parse GOSUB subroutines to identify move generation, evaluation, and search logic.
"""

import struct
from typing import List, Dict, Tuple, Any

class AcornsoftPCodeExtractor:
    def __init__(self, pcode_data: bytes):
        self.data = pcode_data
        self.gosub_targets = {}
        self.string_offsets = []
        self.routine_blocks = []
        
    def extract_strings(self) -> List[Dict]:
        """Extract all string constants with positions."""
        strings = []
        i = 0
        while i < len(self.data):
            if self.data[i] == 0x22:  # String start
                end = self.data.find(0x0D, i + 1)
                if end != -1:
                    raw = self.data[i + 1:end]
                    decoded = self._decode_bbc(raw)
                    strings.append({
                        'offset': i,
                        'length': end - i,
                        'decoded': decoded,
                        'raw': raw
                    })
                    i = end + 1
                else:
                    i += 1
            else:
                i += 1
        return strings
    
    def _decode_bbc(self, data: bytes) -> str:
        """Decode BBC BASIC text."""
        translations = {
            0x83: ' ', 0x84: '.', 0x85: '`', 0x86: "'",
            0x87: '"', 0x88: '(', 0x89: ')', 0x8A: '[',
            0x8B: ']', 0x8C: '<', 0x8D: '>', 0x8E: '!',
            0x8F: '?', 0x90: '@', 0x91: '&', 0x92: '#',
            0x93: "'", 0x94: "'", 0x95: '$', 0x96: '%',
            0x97: '^', 0x98: '*', 0x99: '\\', 0x9A: '|',
            0x9B: '~', 0x9C: '-', 0x9D: '_', 0x9E: '+', 0x9F: '='
        }
        return ''.join(translations.get(b, chr(b)) for b in data)
    
    def extract_gosub_routines(self) -> List[Dict]:
        """Extract all GOSUB calls and their target routines."""
        routines = []
        i = 0
        
        while i < len(self.data):
            opcode = self.data[i]
            
            if opcode == 0x62 and i + 2 < len(self.data):  # GOSUB
                dest = struct.unpack('<H', self.data[i + 1:i + 3])[0]
                routines.append({
                    'offset': i,
                    'target': dest,
                    'type': 'GOSUB'
                })
                i += 3
            elif opcode == 0x95 and i + 2 < len(self.data):  # Function call
                target = struct.unpack('<H', self.data[i + 1:i + 3])[0]
                routines.append({
                    'offset': i,
                    'target': target,
                    'type': 'FUNCTION'
                })
                i += 3
            else:
                i += 1
        
        return routines
    
    def extract_routine_blocks(self, routines: List[Dict]) -> List[Dict]:
        """Extract code blocks at GOSUB target addresses."""
        blocks = []
        
        # Sort by target address
        routines.sort(key=lambda x: x['target'])
        
        # Extract blocks
        for i, routine in enumerate(routines):
            target = routine['target']
            
            # Look for next GOSUB target or end of file
            if i + 1 < len(routines):
                end = routines[i + 1]['target']
            else:
                end = len(self.data)
            
            # Extract code between targets
            block_data = self.data[target:min(end, len(self.data))]
            
            blocks.append({
                'offset': target,
                'end': end,
                'size': min(end, len(self.data)) - target,
                'data': block_data,
                'caller_offset': routine['offset']
            })
        
        return blocks
    
    def analyze_move_generation(self, routines: List[Dict]) -> Dict:
        """Identify potential move generation code."""
        move_gen = {}
        
        for routine in routines:
            if routine['type'] == 'GOSUB':
                target = routine['target']
                
                # Extract routine data
                if target < len(self.data):
                    # Look for common move generation patterns
                    block = self.data[target:target+64]
                    
                    # Check for piece move offsets
                    offsets = [b for b in block if 0x00 <= b <= 0x7F or b == 0xFF]
                    
                    if len(offsets) > 20:
                        move_gen[target] = {
                            'type': 'potential_move_generation',
                            'offset_count': len(offsets),
                            'sample': block[:32].hex(),
                            'caller': routine['caller_offset']
                        }
        
        return move_gen
    
    def extract_piece_data(self) -> List[Dict]:
        """Look for piece table data between strings."""
        strings = self.extract_strings()
        piece_tables = []
        
        # Check gaps between strings
        for i in range(len(strings) - 1):
            start = strings[i]['offset'] + strings[i]['length']
            end = strings[i + 1]['offset']
            
            if end - start >= 64:
                gap = self.data[start:start+64]
                
                # Check for piece-like values
                piece_values = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF, 0xFE]
                piece_count = sum(1 for b in gap if b in piece_values)
                
                if piece_count > 20:
                    piece_tables.append({
                        'offset': start,
                        'size': 64,
                        'piece_count': piece_count,
                        'data': gap.hex(),
                        'between_strings': f"{strings[i]['offset']:04X}-{strings[i+1]['offset']:04X}"
                    })
        
        return piece_tables
    
    def full_extraction(self) -> Dict[str, Any]:
        """Run full extraction."""
        strings = self.extract_strings()
        routines = self.extract_gosub_routines()
        blocks = self.extract_routine_blocks(routines)
        piece_tables = self.extract_piece_data()
        move_gen = self.analyze_move_generation(routines)
        
        return {
            'total_size': len(self.data),
            'strings': strings,
            'routines': routines,
            'blocks': blocks,
            'piece_tables': piece_tables,
            'move_generation_candidates': move_gen
        }


def main():
    """Extract Acornsoft CHESS P-code."""
    
    print("=" * 80)
    print("ACORNSOFT CHESS V2.1 - DETAILED P-CODE EXTRACTION")
    print("=" * 80)
    
    with open('/tmp/acornsoft-extracted/CHESS', 'rb') as f:
        pcode = f.read()
    
    extractor = AcornsoftPCodeExtractor(pcode)
    results = extractor.full_extraction()
    
    print(f"\nTotal P-code size: {results['total_size']} bytes")
    print(f"String constants: {len(results['strings'])}")
    print(f"GOSUB/Function calls: {len(results['routines'])}")
    print(f"Potential move generation routines: {len(results['move_generation_candidates'])}")
    print(f"Piece table candidates: {len(results['piece_tables'])}")
    
    print("\n--- GOSUB Routines ---")
    for i, r in enumerate(results['routines']):
        print(f"[{i:3d}] 0x{r['offset']:04X} -> 0x{r['target']:04X} ({r['type']})")
    
    print("\n--- String Constants (with decoded content) ---")
    for i, s in enumerate(results['strings']):
        if s['decoded'].strip():
            print(f"[{i:3d}] 0x{s['offset']:04X}: {s['decoded'].strip()[:60]}")
    
    print("\n--- Move Generation Candidates ---")
    for target, info in results['move_generation_candidates'].items():
        print(f"Target 0x{target:04X}: {info['offset_count']} offsets")
        print(f"  Caller: 0x{info['caller']:04X}")
        print(f"  Sample: {info['sample']}")
    
    print("\n--- Piece Table Candidates ---")
    for table in results['piece_tables']:
        print(f"Offset 0x{table['offset']:04X}: {table['piece_count']} piece-like bytes")
        print(f"  Between: {table['between_strings']}")
        print(f"  Data: {table['data'][:64]}")


if __name__ == '__main__':
    main()
