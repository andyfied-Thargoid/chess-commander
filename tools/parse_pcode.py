#!/usr/bin/env python3
"""
Parse BBC BASIC P-code to extract meaningful data.
BBC P-code format:
- Each opcode is 1 byte (sometimes followed by operands)
- Strings are prefixed with 0x22 (double quote) and terminated by 0x0D
- Numeric constants: 0x84 followed by encoded value
- Line numbers: 0xF1 followed by 2-byte little-endian
"""

import struct
import os
import sys
from typing import List, Dict, Tuple, Any

class BBCPCodeParser:
    def __init__(self, pcode_data: bytes):
        self.data = pcode_data
        self.offset = 0
        self.strings = []
        self.variables = []
        self.line_numbers = []
        self.constants = []
        self.routines = []
        
    def parse(self) -> Dict[str, Any]:
        """Parse P-code and extract all elements."""
        while self.offset < len(self.data):
            opcode = self.data[self.offset]
            
            # Check for string constant (starts with ")
            if opcode == 0x22:
                string_end = self.data.find(0x0D, self.offset + 1)
                if string_end != -1:
                    string_content = self.data[self.offset + 1:string_end].decode('ascii', errors='replace')
                    self.strings.append({
                        'offset': self.offset,
                        'content': string_content
                    })
                    self.offset = string_end + 1
                    continue
            
            # Check for line number (0xF1)
            elif opcode == 0xF1 and self.offset + 2 < len(self.data):
                line_num = struct.unpack('<H', self.data[self.offset + 1:self.offset + 3])[0]
                self.line_numbers.append({
                    'offset': self.offset,
                    'line_number': line_num
                })
                self.offset += 3
                continue
            
            # Check for numeric constant (0x84)
            elif opcode == 0x84 and self.offset + 1 < len(self.data):
                value = self.data[self.offset + 1]
                self.constants.append({
                    'offset': self.offset,
                    'value': value
                })
                self.offset += 2
                continue
            
            # Check for variable reference (0xA5 or similar)
            elif opcode == 0xA5 and self.offset + 1 < len(self.data):
                var_offset = struct.unpack('<H', self.data[self.offset + 1:self.offset + 3])[0]
                self.variables.append({
                    'offset': self.offset,
                    'variable_offset': var_offset
                })
                self.offset += 3
                continue
            
            # Check for function call (0x95)
            elif opcode == 0x95 and self.offset + 2 < len(self.data):
                func_offset = struct.unpack('<H', self.data[self.offset + 1:self.offset + 3])[0]
                self.routines.append({
                    'offset': self.offset,
                    'function_offset': func_offset,
                    'type': 'function_call'
                })
                self.offset += 3
                continue
            
            # Check for GOSUB (0x62)
            elif opcode == 0x62 and self.offset + 2 < len(self.data):
                dest_line = struct.unpack('<H', self.data[self.offset + 1:self.offset + 3])[0]
                self.routines.append({
                    'offset': self.offset,
                    'destination': dest_line,
                    'type': 'gosub'
                })
                self.offset += 3
                continue
            
            # Check for GOTO (0xF5 or 0x70)
            elif opcode in [0xF5, 0x70] and self.offset + 2 < len(self.data):
                dest_line = struct.unpack('<H', self.data[self.offset + 1:self.offset + 3])[0]
                self.routines.append({
                    'offset': self.offset,
                    'destination': dest_line,
                    'type': 'goto'
                })
                self.offset += 3
                continue
            
            # Skip unknown opcodes (1 byte)
            else:
                self.offset += 1
                continue
        
        return {
            'total_bytes': len(self.data),
            'strings': self.strings,
            'variables': self.variables,
            'line_numbers': self.line_numbers,
            'constants': self.constants,
            'routines': self.routines
        }
    
    def find_board_data_region(self) -> Tuple[int, int, str]:
        """
        Heuristic: Look for regions with repetitive patterns that might be board data.
        Returns (start_offset, end_offset, description)
        """
        # Look for 64-byte regions with specific patterns
        # Board data is likely between P-code routines
        
        # Search for common patterns:
        # - Piece values (0x01-0x06 for pieces, 0x00 for empty)
        # - 8x8 grid patterns
        # - Data between string constants
        
        regions = []
        i = 0
        while i < len(self.data) - 64:
            # Look for 64 consecutive bytes with limited entropy (likely data)
            segment = self.data[i:i+64]
            
            # Count unique bytes
            unique_bytes = len(set(segment))
            
            # If low entropy (< 20 unique bytes), might be board data or padding
            if unique_bytes < 20:
                # Check if it's mostly 0xE5 (padding) or has piece-like values
                e5_count = segment.count(0xE5)
                piece_like = sum(1 for b in segment if 0x00 <= b <= 0x0F)
                
                if e5_count > 50:
                    desc = "Padding region (0xE5)"
                elif piece_like > 20:
                    desc = "Potential board data (piece-like values)"
                else:
                    desc = "Low-entropy data region"
                
                regions.append((i, i+64, desc, e5_count, piece_like))
                i += 64
            else:
                i += 1
        
        return regions
    
    def extract_piece_table(self) -> List[int]:
        """
        Try to extract piece table from P-code.
        Expected: 64 bytes representing board squares.
        """
        # Look for patterns that match piece encoding
        # Common: 1=P, 2=N, 3=B, 4=R, 5=Q, 6=K (positive = white, negative = black)
        
        # Search for 64-byte sequence with piece-like values
        for i in range(len(self.data) - 64):
            segment = self.data[i:i+64]
            
            # Check for valid piece values
            valid_pieces = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
            valid_count = sum(1 for b in segment if b in valid_pieces)
            
            if valid_count > 40:  # Most bytes are piece values
                return list(segment)
        
        return []
    
    def analyze(self) -> str:
        """Generate human-readable analysis."""
        lines = []
        lines.append(f"Total P-code size: {len(self.data)} bytes")
        lines.append(f"String constants: {len(self.strings)}")
        lines.append(f"Numeric constants: {len(self.constants)}")
        lines.append(f"GOSUB/Function calls: {len(self.routines)}")
        lines.append(f"Line numbers: {len(self.line_numbers)}")
        
        lines.append("\n--- String Constants (first 20) ---")
        for i, s in enumerate(self.strings[:20]):
            lines.append(f"[{i:3d}] {s['content'][:80]}")
        
        lines.append("\n--- Data Regions ---")
        regions = self.find_board_data_region()
        for start, end, desc, e5_count, piece_like in regions[:10]:
            lines.append(f"Offset 0x{start:04X}-0x{end:04X}: {desc} (0xE5: {e5_count}, pieces: {piece_like})")
        
        return "\n".join(lines)


def parse_pcode_file(filepath: str) -> Dict[str, Any]:
    """Parse a P-code file and return structured data."""
    with open(filepath, 'rb') as f:
        pcode_data = f.read()
    
    parser = BBCPCodeParser(pcode_data)
    return parser.parse()


def analyze_chess_programs():
    """Analyze both chess programs."""
    
    # Acornsoft
    print("=" * 80)
    print("ACORNSOFT CHESS V2.1 - P-Code Analysis")
    print("=" * 80)
    
    with open('/tmp/acornsoft-extracted/CHESS', 'rb') as f:
        acornsoft_pcode = f.read()
    
    parser = BBCPCodeParser(acornsoft_pcode)
    acornsoft_result = parser.parse()
    
    print(parser.analyze())
    
    # Thompson
    print("\n" + "=" * 80)
    print("THOMPSON CHESS 2.32/1 - P-Code Analysis")
    print("=" * 80)
    
    with open('/tmp/thompson-extracted/CHESS', 'rb') as f:
        thompson_pcode = f.read()
    
    parser = BBCPCodeParser(thompson_pcode)
    thompson_result = parser.parse()
    
    print(parser.analyze())


if __name__ == '__main__':
    analyze_chess_programs()
