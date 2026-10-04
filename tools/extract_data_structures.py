#!/usr/bin/env python3
"""
Advanced P-code extraction for board representation and move generation data.
Focus on finding:
1. Piece tables
2. Move generation tables
3. Position evaluation coefficients
4. Board encoding scheme
"""

import struct
import os
import sys
from typing import List, Dict, Tuple, Any, Optional

class PCodeDataExtractor:
    def __init__(self, pcode_data: bytes, name: str):
        self.data = pcode_data
        self.name = name
        self.offset = 0
        
    def scan_for_patterns(self) -> Dict[str, List[Dict]]:
        """
        Scan P-code for data patterns that might be:
        - Piece tables (64 bytes)
        - Move generation tables
        - Evaluation coefficients
        - Bitboard masks
        """
        results = {
            'piece_tables': [],
            'move_tables': [],
            'evaluation_data': [],
            'bitboard_patterns': [],
            'data_structures': []
        }
        
        # Scan for 64-byte blocks (board representation)
        board_regions = self._find_board_regions()
        results['piece_tables'] = board_regions
        
        # Scan for 64-byte move generation tables
        # Typical: 64 squares x move offsets
        move_regions = self._find_move_regions()
        results['move_tables'] = move_regions
        
        # Scan for evaluation coefficient blocks
        # Typically 16-32 byte blocks with signed values
        eval_regions = self._find_evaluation_regions()
        results['evaluation_data'] = eval_regions
        
        # Scan for bitboard patterns (64-bit masks)
        bitboard_regions = self._find_bitboard_patterns()
        results['bitboard_patterns'] = bitboard_regions
        
        # Find all data structures (non-P-code regions)
        structures = self._find_data_structures()
        results['data_structures'] = structures
        
        return results
    
    def _find_board_regions(self) -> List[Dict]:
        """Find 64-byte blocks that might be board representations."""
        regions = []
        
        for i in range(0, len(self.data) - 64, 16):
            segment = self.data[i:i+64]
            
            # Analyze segment
            unique = len(set(segment))
            e5_count = segment.count(0xE5)
            zero_count = segment.count(0x00)
            piece_like = sum(1 for b in segment if 0x01 <= b <= 0x06 or 0xFF <= b <= 0xFE)
            
            # Heuristic for board data
            if unique < 15 and (zero_count > 20 or piece_like > 10):
                regions.append({
                    'offset': i,
                    'size': 64,
                    'unique_bytes': unique,
                    'zero_count': zero_count,
                    'piece_like_count': piece_like,
                    'pattern': self._describe_pattern(segment)
                })
        
        return regions
    
    def _find_move_regions(self) -> List[Dict]:
        """Find move generation tables (64 squares with move offsets)."""
        regions = []
        
        for i in range(0, len(self.data) - 64, 8):
            segment = self.data[i:i+64]
            
            # Move tables might have:
            # - 8 bytes per rank (8 ranks = 64 bytes)
            # - Values in range 0x00-0x7F (move offsets)
            valid_moves = sum(1 for b in segment if 0x00 <= b <= 0x7F or b == 0xFF)
            
            if valid_moves > 40:
                regions.append({
                    'offset': i,
                    'size': 64,
                    'valid_move_bytes': valid_moves,
                    'pattern': 'potential_move_table'
                })
        
        return regions
    
    def _find_evaluation_regions(self) -> List[Dict]:
        """Find evaluation coefficient blocks."""
        regions = []
        
        # Look for signed byte patterns (material values, positional bonuses)
        for i in range(0, len(self.data) - 16, 4):
            segment = self.data[i:i+16]
            
            # Check for signed byte patterns
            signed_values = []
            for b in segment:
                if b > 127:
                    signed_values.append(b - 256)
                else:
                    signed_values.append(b)
            
            # Count unique signed values
            unique_signed = len(set(signed_values))
            
            # Evaluation tables often have:
            # - Material values (e.g., 100, 300, 300, 500, 900, 0 for pieces)
            # - Positional bonuses (-50 to +50 typically)
            if unique_signed < 10 and len(signed_values) >= 8:
                regions.append({
                    'offset': i,
                    'size': 16,
                    'values': signed_values,
                    'unique_count': unique_signed,
                    'pattern': 'potential_evaluation_coefficients'
                })
        
        return regions
    
    def _find_bitboard_patterns(self) -> List[Dict]:
        """Find 64-bit bitboard masks."""
        regions = []
        
        for i in range(0, len(self.data) - 8, 8):
            segment = self.data[i:i+8]
            
            # Bitboards are often all 0s, all 1s, or specific patterns
            # Check for byte patterns like 0x00, 0xFF, 0xAA, 0x55, 0x55, 0xAA
            
            byte_pattern = [format(b, '08b') for b in segment]
            
            # Check for common bitboard patterns
            if '00000000' in byte_pattern or '11111111' in byte_pattern or '01010101' in byte_pattern:
                regions.append({
                    'offset': i,
                    'size': 8,
                    'bytes': segment,
                    'binary': byte_pattern,
                    'pattern': 'potential_bitboard_mask'
                })
        
        return regions
    
    def _find_data_structures(self) -> List[Dict]:
        """Find all non-P-code data regions."""
        structures = []
        
        # Look for regions between P-code strings
        prev_string_end = 0
        for i in range(0, len(self.data), 16):
            segment = self.data[i:i+16]
            
            # Check if this looks like data, not P-code
            # P-code has opcodes 0x22, 0x62, 0x70, 0x84, 0x95, 0x9B, 0xF1, 0xF5
            # Data might have other patterns
            
            is_pcode_opcodes = sum(1 for b in segment if b in [0x22, 0x62, 0x70, 0x84, 0x95, 0xF1, 0xF5])
            
            # If few P-code opcodes, might be data
            if is_pcode_opcodes < 2:
                # Check for data patterns
                unique = len(set(segment))
                
                if unique < 8:  # Low entropy = likely data
                    structures.append({
                        'offset': i,
                        'size': 16,
                        'unique_bytes': unique,
                        'pattern': self._describe_pattern(segment)
                    })
        
        return structures
    
    def _describe_pattern(self, segment: bytes) -> str:
        """Describe byte pattern for debugging."""
        counts = {}
        for b in segment:
            counts[b] = counts.get(b, 0) + 1
        
        dominant = max(counts.items(), key=lambda x: x[1])
        unique = len(counts)
        
        # Check for piece-like values
        piece_values = [b for b in segment if 0x01 <= b <= 0x06]
        
        if len(piece_values) > 10:
            return f"piece-like: {len(piece_values)} bytes"
        elif dominant[1] > 40:
            return f"padding: {hex(dominant[0])} ({dominant[1]} bytes)"
        else:
            return f"mixed: {unique} unique bytes"
    
    def extract_piece_table(self, region: Dict) -> Optional[List[int]]:
        """Extract piece table from a 64-byte region."""
        start = region['offset']
        segment = self.data[start:start+64]
        
        # Validate as piece table
        valid_pieces = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF, 0xFE]
        valid_count = sum(1 for b in segment if b in valid_pieces)
        
        if valid_count > 40:
            return list(segment)
        
        return None
    
    def analyze_board_encoding(self) -> str:
        """Analyze board encoding scheme from extracted data."""
        piece_tables = self.scan_for_patterns()['piece_tables']
        
        if not piece_tables:
            return "No piece table found"
        
        # Take first candidate
        candidate = piece_tables[0]
        segment = self.data[candidate['offset']:candidate['offset']+64]
        
        # Try to decode as different schemes
        schemes = []
        
        # Scheme 1: 1 byte per square, 0-6 = pieces, 0 = empty
        scheme1 = all(b in [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF] for b in segment)
        if scheme1:
            schemes.append("1 byte per square: 1=P,2=N,3=B,4=R,5=Q,6=K,0=empty,FF=black")
        
        # Scheme 2: High nibble = piece, low nibble = color
        scheme2 = all(0x00 <= (b & 0xF0) <= 0x60 and (b & 0x0F) in [0x00, 0x80] for b in segment)
        if scheme2:
            schemes.append("Nibbles: high=piece, low=color (0=white, 8=black)")
        
        # Scheme 3: Signed bytes
        signed_values = [b if b < 128 else b-256 for b in segment]
        unique_signed = len(set(signed_values))
        if unique_signed < 8:
            schemes.append(f"Signed bytes: {unique_signed} unique values")
        
        return "\n".join(schemes) if schemes else "Unknown encoding"


def analyze_files():
    """Analyze both chess programs."""
    
    print("=" * 80)
    print("ACORNSOFT CHESS V2.1 - P-Code Data Analysis")
    print("=" * 80)
    
    with open('/tmp/acornsoft-extracted/CHESS', 'rb') as f:
        acornsoft = f.read()
    
    extractor = PCodeDataExtractor(acornsoft, "Acornsoft")
    acornsoft_data = extractor.scan_for_patterns()
    
    print(f"Board regions: {len(acornsoft_data['piece_tables'])}")
    print(f"Move tables: {len(acornsoft_data['move_tables'])}")
    print(f"Evaluation data: {len(acornsoft_data['evaluation_data'])}")
    print(f"Bitboard patterns: {len(acornsoft_data['bitboard_patterns'])}")
    print(f"Data structures: {len(acornsoft_data['data_structures'])}")
    
    print("\n--- Board Encoding Analysis ---")
    print(extractor.analyze_board_encoding())
    
    print("\n--- Sample Board Region (if found) ---")
    if acornsoft_data['piece_tables']:
        region = acornsoft_data['piece_tables'][0]
        print(f"Offset: 0x{region['offset']:04X}")
        print(f"Pattern: {region['pattern']}")
        print(f"Unique bytes: {region['unique_bytes']}")
        
        # Show hex dump
        segment = acornsoft[region['offset']:region['offset']+64]
        hex_str = ' '.join(f'{b:02X}' for b in segment)
        print(f"Bytes: {hex_str}")
    
    print("\n" + "=" * 80)
    print("THOMPSON CHESS 2.32/1 - P-Code Data Analysis")
    print("=" * 80)
    
    with open('/tmp/thompson-extracted/CHESS', 'rb') as f:
        thompson = f.read()
    
    extractor = PCodeDataExtractor(thompson, "Thompson")
    thompson_data = extractor.scan_for_patterns()
    
    print(f"Board regions: {len(thompson_data['piece_tables'])}")
    print(f"Move tables: {len(thompson_data['move_tables'])}")
    print(f"Evaluation data: {len(thompson_data['evaluation_data'])}")
    print(f"Bitboard patterns: {len(thompson_data['bitboard_patterns'])}")
    print(f"Data structures: {len(thompson_data['data_structures'])}")
    
    print("\n--- Board Encoding Analysis ---")
    print(extractor.analyze_board_encoding())
    
    print("\n--- Sample Board Region (if found) ---")
    if thompson_data['piece_tables']:
        region = thompson_data['piece_tables'][0]
        print(f"Offset: 0x{region['offset']:04X}")
        print(f"Pattern: {region['pattern']}")
        print(f"Unique bytes: {region['unique_bytes']}")
        
        segment = thompson[region['offset']:region['offset']+64]
        hex_str = ' '.join(f'{b:02X}' for b in segment)
        print(f"Bytes: {hex_str}")


if __name__ == '__main__':
    analyze_files()
