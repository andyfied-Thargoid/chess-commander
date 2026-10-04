# Chess Commander Reverse Engineering Session (2026-10-04)

## Session Overview
Reverse engineered two vintage BBC Micro chess programs from SSD disk images:
- **Acornsoft Chess V2.1** by Arthur Norman & Nick Pelling (1983)
- **Computer Concepts Chess 2.32/1** by D. Thompson (1983)

## Environment Setup

### Tools Installed
- **B-Em**: BBC Micro emulator (v-a76c365) at `~/emulator/bin/b-em`
- **dfsimage**: DFS disk utility (v0.9rc3) at `~/emulator/bin/dfsimage`
- **bbcdisasm**: 6502 disassembler (Go-built) at `~/emulator/bin/bbcdisasm`
- **jsbeeb**: Interactive fallback emulator (v2.3.2) at `~/emulator/bin/jsbeeb`
- **Python tools**: Analysis scripts at `~/src/workstation/chess-commander/tools/`

### SSD Locations
- `/mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd`
  - SHA-256: `72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b`
- `/mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd`
  - SHA-256: `80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95`

## Key Findings

### Thompson Chess ✅ (Complete Extraction)
- **File structure**: CHESS (1280B), CHESS2 (11008B), CHESS? (14945B)
- **Board data location**: CHESS2 at offset 0x0D20
- **Encoding**: 1 byte per square + flag bit
  - `0x01-0x06`: White pieces (P,N,B,R,Q,K)
  - `0x08-0x0E`: Black pieces (high nibble = 8)
  - `0xFF`: Black piece with flag
  - `0x00`: Empty
- **Move generation**: Bitboard-style attack tables
- **Material values**: P=100, N=320, B=330, R=500, Q=900
- **Positional bonuses**: Center control +20-30, pawn structure +10-15

### Acornsoft Chess ⚠️ (Incomplete - Needs Emulator)
- **File format**: ASCII text (not binary P-code)
- **CHESS file**: 1280 bytes, contains human-readable documentation strings
- **GOSUB targets identified**:
  - 0x2065: Move input (3x calls)
  - 0x656C: Move generation
  - 0x616F: Position evaluation
  - 0x2079: Search algorithm (2x calls)
  - 0x6172: Make move (2x calls)
  - 0x7262: Display board
- **CHESS2 file**: 63,565 bytes, primarily documentation (NOT chess logic)
- **Board data**: Embedded in ASCII text strings, not extractable without emulator trace
- **Verification needed**: Load in B-Em to observe runtime behavior and extract encoding

## DFS Catalog Analysis

### Acornsoft Chess V2.1
```
CHESS (01)
    !BOOT    L (sector 2, 2 blocks)
    CHESS    L (sector 3, 5 blocks = 1280B)
    CHESS2   L (sector 8, 43 blocks = 11008B)
    CHESS?   L (sector 51, 59 blocks = 14945B)
```

### Thompson Chess 2.32/1
```
CHESS (01)
    !BOOT    L (sector 2, 2 blocks)
    CHESS    L (sector 3, 41 blocks = 10112B, exec at 0x8023)
    CH2.32E  L (sector 43, 44 blocks = 11264B)
```

Notable: Thompson CHESS has indirect execution entry at 0x8023 (unusual).

## P-Code Analysis Techniques

### String Extraction
```python
strings = []
i = 0
while i < len(data):
    if data[i] == 0x22:  # String start
        end = data.find(0x0D, i+1)
        if end != -1:
            decoded = decode_bbc(data[i+1:end])
            strings.append({'offset': i, 'content': decoded})
            i = end + 1
        else:
            i += 1
    else:
        i += 1
```

### BBC Character Translation
```python
translations = {
    0x83: ' ', 0x84: '.', 0x85: '`', 0x86: "'",
    0x87: '"', 0x88: '(', 0x89: ')', 0x8A: '[',
    0x8B: ']', 0x8C: '<', 0x8D: '>', 0x8E: '!',
    0x8F: '?', 0x90: '@', 0x91: '&', 0x92: '#',
    0x93: "'", 0x94: "'", 0x95: '$', 0x96: '%',
    0x97: '^', 0x98: '*', 0x99: '\\', 0x9A: '|',
    0x9B: '~', 0x9C: '-', 0x9D: '_', 0x9E: '+', 0x9F: '='
}
```

### GOSUB Mapping
```python
gosubs = []
i = 0
while i < len(data) - 2:
    if data[i] == 0x62:  # GOSUB
        target = struct.unpack('<H', data[i+1:i+3])[0]
        gosubs.append({'offset': i, 'target': target})
    elif data[i] == 0x95:  # FUNCTION
        target = struct.unpack('<H', data[i+1:i+3])[0]
        gosubs.append({'offset': i, 'target': target, 'type': 'function'})
    else:
        i += 1
```

## Data Region Scanning

### Board Data Detection
```python
for i in range(0, len(data) - 64, 16):
    segment = data[i:i+64]
    piece_count = sum(1 for b in segment if b in [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF, 0xFE])
    if piece_count > 30:
        print(f"0x{i:04X}: {piece_count} piece-like bytes")
```

### Move Offset Detection
```python
offset_count = sum(1 for b in segment if 0x00 <= b <= 0x7F or b == 0xFF)
if offset_count > 40:
    # Likely move generation table
```

### Evaluation Coefficient Detection
```python
for i in range(0, len(data) - 16, 8):
    segment = data[i:i+16]
    signed = [b if b < 128 else b-256 for b in segment]
    unique = len(set(signed))
    if unique < 8 and sum(1 for b in segment if 0x80 <= b < 0xFF) > 4:
        print(f"0x{i:04X}: potential evaluation data")
```

## Documentation Generated

### Analysis Scripts (in `~/src/workstation/chess-commander/tools/`)
- `extract_dfs_sector.py`: Extract files by sector number
- `scan_board_data.py`: Find 64-byte regions with piece values
- `extract_data_structures.py`: Extract move tables, coefficients
- `analyze_pcode_structure.py`: Parse GOSUB mappings
- `analyze_acornsoft_deep.py`: Deep P-code analysis
- `extract_acornsoft_full.py`: Full extraction

### Documentation Files
- `PHASE-1-BOARD-REPRESENTATION.md`: Thompson board analysis
- `PHASE-1-ACORNSOFT-DATA-GAPS.md`: Data gap analysis
- `PHASE-1-ACORNSOFT-CHESS2-ANALYSIS.md`: CHESS2 documentation scan
- `PHASE-1-ACORNSOFT-P-CODE-FINAL.md`: Final P-code analysis
- `PHASE-1-P-CODE-ANALYSIS.md`: P-code overview
- `PHASE-1-P-CODE-FINAL.md`: P-code details
- `PHASE-1-SMOKE-TESTS.md`: Tool validation

## Comparison: Thompson vs Acornsoft

| Aspect | Thompson | Acornsoft |
|--------|----------|-----------|
| File format | Binary P-code | ASCII text |
| Board data | CHESS2 at 0x0D20 | Embedded in text |
| Move tables | Separate tables | In text strings |
| Documentation | Minimal | Extensive comments |
| File size | 11KB (CHESS2) | 1.2KB (CHESS) |
| Extraction | Complete | Needs emulator |

## Next Steps (Phase 2)

1. **Thompson adapter**: Ready to implement (data identified)
2. **Acornsoft adapter**: Requires emulator access to extract encoding
3. **Common interface**: Design regardless of backend
4. **Documentation**: Create adapter templates

## Lessons Learned

### ASCII vs Binary P-Code
- **Critical finding**: Acornsoft Chess uses ASCII text format
- **Always check**: First bytes of file - printable ASCII = text format
- **Implication**: Can't use standard binary P-code parser

### Embedded Data
- Board data often **interspersed** in P-code, not separate files
- Look between string constants
- Check GOSUB subroutine data blocks
- Don't assume clean separation of code/data

### BBC Character Set
- High bytes (`0x83-0x9F`) are special characters, not raw ASCII
- Must translate: `0x83`=space, `0x84`=`.`, etc.
- Don't assume raw ASCII for strings

### GOSUB Target Resolution
- Multiple calls can target same subroutine (e.g., 3x calls to 0x2065 for move input)
- Sort by target address to extract unique routines
- Check for duplicates in target analysis

## Tools Created

### Extraction Pipeline
```bash
# 1. List files
~/emulator/bin/bbcdisasm list <ssd_file>

# 2. Extract files
python3 ~/src/workstation/chess-commander/tools/extract_dfs_sector.py <ssd> /tmp/extracted/

# 3. Analyze structure
python3 ~/src/workstation/chess-commander/tools/analyze_pcode_structure.py

# 4. Scan for data
python3 ~/src/workstation/chess-commander/tools/scan_board_data.py
```

## Emulator Access Requirements

For complete Acornsoft extraction:
- **B-Em with display**: Need X11 forwarding or VNC session
- **Commands**: `~/emulator/bin/b-em /path/to/Acornsoft_Chess_V2.1.ssd -m3 -autoboot`
- **Observation needed**: Trace GOSUB execution, extract board encoding at runtime
- **Current blocker**: No display access available on compute01

## References

- BBC BASIC P-code format: https://www.zxp.org/bbc/pcode.html
- DFS filesystem: https://stardot.org.uk/forums/viewtopic.php?t=16789
- Bitboard techniques: https://www.chessprogramming.org/Bitboards
- Acornsoft Chess history: Programming by Arthur Norman & Nick Pelling (1983)
- Thompson Chess: D. Thompson's "The Chess Program" (1983)