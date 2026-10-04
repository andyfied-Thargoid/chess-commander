#!/usr/bin/env python3
"""
Enhanced BBC BASIC P-code parser with better string handling.
"""

import struct
import os
import sys
from typing import List, Dict, Tuple, Any

def decode_bbc_string(data: bytes, start: int) -> Tuple[str, int]:
    """
    Decode BBC BASIC string (starts with ", ends with 0x0D).
    Handles BBC character set encoding.
    """
    end = data.find(0x0D, start)
    if end == -1:
        return "", start + 1
    
    raw_string = data[start + 1:end]
    
    # Try ASCII first
    try:
        string = raw_string.decode('ascii')
        return string, end + 1
    except:
        # Fallback: decode with errors replaced
        string = raw_string.decode('latin-1', errors='replace')
        return string, end + 1

def decode_bbc_text(data: bytes) -> str:
    """Decode BBC P-code text with embedded control characters."""
    result = []
    i = 0
    while i < len(data):
        byte = data[i]
        
        # BBC character set (higher codes are special characters)
        if byte == 0x83:
            result.append(' ')  # Space
            i += 1
        elif byte == 0x84:
            result.append('.')  # Full stop
            i += 1
        elif byte == 0x85:
            result.append('`')  # Back quote
            i += 1
        elif byte == 0x86:
            result.append("'")  # Quote
            i += 1
        elif byte == 0x87:
            result.append('"')  # Double quote
            i += 1
        elif byte == 0x88:
            result.append('(')  # Open bracket
            i += 1
        elif byte == 0x89:
            result.append(')')  # Close bracket
            i += 1
        elif byte == 0x8A:
            result.append('[')  # Square bracket
            i += 1
        elif byte == 0x8B:
            result.append(']')  # Square bracket
            i += 1
        elif byte == 0x8C:
            result.append('<')  # Less than
            i += 1
        elif byte == 0x8D:
            result.append('>')  # Greater than
            i += 1
        elif byte == 0x8E:
            result.append('!')  # Exclamation
            i += 1
        elif byte == 0x8F:
            result.append('?')  # Question mark
            i += 1
        elif byte == 0x90:
            result.append('@')  # At sign
            i += 1
        elif byte == 0x91:
            result.append('&')  # Ampersand
            i += 1
        elif byte == 0x92:
            result.append('#')  # Hash
            i += 1
        elif byte == 0x93:
            result.append('\'')  # Single quote
            i += 1
        elif byte == 0x94:
            result.append('\'')  # Single quote variant
            i += 1
        elif byte == 0x95:
            result.append('$')  # Dollar sign
            i += 1
        elif byte == 0x96:
            result.append('%')  # Percent
            i += 1
        elif byte == 0x97:
            result.append('^')  # Caret
            i += 1
        elif byte == 0x98:
            result.append('*')  # Asterisk
            i += 1
        elif byte == 0x99:
            result.append('\\')  # Backslash
            i += 1
        elif byte == 0x9A:
            result.append('|')  # Pipe
            i += 1
        elif byte == 0x9B:
            result.append('~')  # Tilde
            i += 1
        elif byte == 0x9C:
            result.append('-')  # Hyphen
            i += 1
        elif byte == 0x9D:
            result.append('_')  # Underscore
            i += 1
        elif byte == 0x9E:
            result.append('+')  # Plus
            i += 1
        elif byte == 0x9F:
            result.append('=')  # Equals
            i += 1
        else:
            result.append(chr(byte))
            i += 1
    
    return ''.join(result)

def parse_pcode_file(filepath: str) -> Dict[str, Any]:
    """Parse P-code file and extract all elements."""
    with open(filepath, 'rb') as f:
        pcode_data = f.read()
    
    strings = []
    routines = []
    line_numbers = []
    constants = []
    board_data_regions = []
    
    offset = 0
    while offset < len(pcode_data):
        opcode = pcode_data[offset]
        
        # String constant (0x22 = ")
        if opcode == 0x22:
            string, new_offset = decode_bbc_string(pcode_data, offset)
            if string.strip():  # Only store non-empty strings
                strings.append({
                    'offset': offset,
                    'content': string
                })
            offset = new_offset
            continue
        
        # Numeric constant (0x84)
        elif opcode == 0x84 and offset + 1 < len(pcode_data):
            value = pcode_data[offset + 1]
            constants.append({
                'offset': offset,
                'value': value
            })
            offset += 2
            continue
        
        # Line number (0xF1)
        elif opcode == 0xF1 and offset + 2 < len(pcode_data):
            line_num = struct.unpack('<H', pcode_data[offset + 1:offset + 3])[0]
            line_numbers.append({
                'offset': offset,
                'line_number': line_num
            })
            offset += 3
            continue
        
        # Function call (0x95)
        elif opcode == 0x95 and offset + 2 < len(pcode_data):
            func_offset = struct.unpack('<H', pcode_data[offset + 1:offset + 3])[0]
            routines.append({
                'offset': offset,
                'type': 'function_call',
                'target': func_offset
            })
            offset += 3
            continue
        
        # GOSUB (0x62)
        elif opcode == 0x62 and offset + 2 < len(pcode_data):
            dest = struct.unpack('<H', pcode_data[offset + 1:offset + 3])[0]
            routines.append({
                'offset': offset,
                'type': 'gosub',
                'destination': dest
            })
            offset += 3
            continue
        
        # GOTO/Jump (0xF5 or 0x70)
        elif opcode in [0xF5, 0x70] and offset + 2 < len(pcode_data):
            dest = struct.unpack('<H', pcode_data[offset + 1:offset + 3])[0]
            routines.append({
                'offset': offset,
                'type': 'goto',
                'destination': dest
            })
            offset += 3
            continue
        
        # Unknown opcode - skip 1 byte
        else:
            offset += 1
            continue
    
    # Find potential board data regions (64-byte blocks with specific patterns)
    for i in range(0, len(pcode_data) - 64, 16):
        segment = pcode_data[i:i+64]
        
        # Count byte entropy
        unique = len(set(segment))
        e5_count = segment.count(0xE5)
        
        # Heuristic: Low entropy + specific patterns = potential data
        if unique < 10 or e5_count > 40:
            board_data_regions.append({
                'offset': i,
                'size': 64,
                'unique_bytes': unique,
                'e5_count': e5_count
            })
    
    return {
        'total_size': len(pcode_data),
        'strings': strings,
        'routines': routines,
        'line_numbers': line_numbers,
        'constants': constants,
        'board_regions': board_data_regions
    }

def print_analysis(pcode_data: bytes, name: str):
    """Print structured P-code analysis."""
    
    # Decode full text
    decoded_text = decode_bbc_text(pcode_data)
    
    # Parse structure
    parsed = parse_pcode_file_bytes(pcode_data)
    
    print(f"\n{'='*80}")
    print(f"{name} - P-Code Analysis")
    print(f"{'='*80}")
    print(f"Total size: {parsed['total_size']} bytes")
    print(f"String constants: {len(parsed['strings'])}")
    print(f"Function calls/GOSUB: {len(parsed['routines'])}")
    print(f"Line numbers: {len(parsed['line_numbers'])}")
    print(f"Numeric constants: {len(parsed['constants'])}")
    
    print(f"\n--- Extracted Strings ---")
    for i, s in enumerate(parsed['strings']):
        content = s['content'].strip()
        if content:
            print(f"[{i:3d}] {content[:100]}")
    
    print(f"\n--- Board Data Regions ---")
    for region in parsed['board_regions'][:10]:
        print(f"Offset 0x{region['offset']:04X}: {region['unique_bytes']} unique bytes, {region['e5_count']} 0xE5 bytes")
    
    print(f"\n--- First 100 bytes decoded ---")
    sample = decoded_text[:100]
    # Show as readable text, replacing non-printables
    readable = ''.join(c if 32 <= ord(c) < 127 or c in ' \n\t' else f'[{ord(c):02X}]' for c in sample)
    print(readable)

def parse_pcode_file_bytes(pcode_data: bytes) -> Dict[str, Any]:
    """Parse raw P-code bytes (used when data already loaded)."""
    strings = []
    routines = []
    line_numbers = []
    constants = []
    board_data_regions = []
    
    offset = 0
    while offset < len(pcode_data):
        opcode = pcode_data[offset]
        
        if opcode == 0x22:
            string, new_offset = decode_bbc_string(pcode_data, offset)
            if string.strip():
                strings.append({'offset': offset, 'content': string})
            offset = new_offset
            continue
        
        elif opcode == 0x84 and offset + 1 < len(pcode_data):
            constants.append({'offset': offset, 'value': pcode_data[offset + 1]})
            offset += 2
            continue
        
        elif opcode == 0xF1 and offset + 2 < len(pcode_data):
            line_num = struct.unpack('<H', pcode_data[offset + 1:offset + 3])[0]
            line_numbers.append({'offset': offset, 'line_number': line_num})
            offset += 3
            continue
        
        elif opcode == 0x95 and offset + 2 < len(pcode_data):
            routines.append({'offset': offset, 'type': 'function_call', 'target': struct.unpack('<H', pcode_data[offset + 1:offset + 3])[0]})
            offset += 3
            continue
        
        elif opcode == 0x62 and offset + 2 < len(pcode_data):
            routines.append({'offset': offset, 'type': 'gosub', 'destination': struct.unpack('<H', pcode_data[offset + 1:offset + 3])[0]})
            offset += 3
            continue
        
        elif opcode in [0xF5, 0x70] and offset + 2 < len(pcode_data):
            routines.append({'offset': offset, 'type': 'goto', 'destination': struct.unpack('<H', pcode_data[offset + 1:offset + 3])[0]})
            offset += 3
            continue
        
        else:
            offset += 1
            continue
    
    # Find board data regions
    for i in range(0, len(pcode_data) - 64, 16):
        segment = pcode_data[i:i+64]
        unique = len(set(segment))
        e5_count = segment.count(0xE5)
        if unique < 10 or e5_count > 40:
            board_data_regions.append({'offset': i, 'size': 64, 'unique_bytes': unique, 'e5_count': e5_count})
    
    return {
        'total_size': len(pcode_data),
        'strings': strings,
        'routines': routines,
        'line_numbers': line_numbers,
        'constants': constants,
        'board_regions': board_data_regions
    }

# Main analysis
if __name__ == '__main__':
    # Load Acornsoft
    with open('/tmp/acornsoft-extracted/CHESS', 'rb') as f:
        acornsoft = f.read()
    print_analysis(acornsoft, "ACORNSOFT CHESS V2.1")
    
    # Load Thompson
    with open('/tmp/thompson-extracted/CHESS', 'rb') as f:
        thompson = f.read()
    print_analysis(thompson, "THOMPSON CHESS 2.32/1")
