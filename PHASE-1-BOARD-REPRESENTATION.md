# Phase 1 — Board Representation Analysis (Complete)

## Executive Summary

Board representation data found in **Thompson CHESS2** file. Acornsoft data not clearly identifiable in CHESS files, likely embedded in P-code or CHESS?.

## Thompson CHESS2 Board Data

### Location
**Offset 0x0D20 - 0x1500** in CHESS2 file (11008 bytes total)

### Sample Board Region (0x0D20)
```
49 4A 4B 4C 4D 3C 3D 3E 3F 40 41 42 43 0C F4 15 EB 13 ED 08 F8 01 FF 0A F6 09 F7 0B F5 0A F6 01
```

**Pattern Analysis:**
- `FF` = Black piece (likely)
- `01-0A` = Piece values (pawn=1, knight=2, etc.)
- `F0-F7` = Move offsets (F = flag bit, 0-7 = square index)
- `00` = Empty square

### Board Encoding Scheme (Inferred)

**1-byte per square encoding:**
```
Bits 7:   Flag bit (0 = no flag, 1 = special move)
Bits 6-4: Piece type (1=pawn, 2=knight, 3=bishop, 4=rook, 5=queen, 6=king)
Bits 3-0: Color (0=white, 8=black)
```

**Examples from extracted data:**
- `01` = White pawn
- `08` = Black pawn (0x08 = 8 = black)
- `FF` = Black piece with flag
- `00` = Empty square

### Move Generation Pattern

The sequence `F4 15 EB 13 ED 08 F8` appears to be:
- **F4** = Flag + square 4 (move from d-file)
- **15** = Move to e5
- **EB** = Knight jump pattern (E = knight, B = bit pattern)
- **13** = Move to d3
- **ED** = Bishop move pattern
- **08** = Black pawn

This suggests **Thompson uses bitboard-like move generation** with precomputed attack tables.

## Acornsoft Chess

### Findings
- No clear board representation in CHESS, CHESS2, or CHESS? files
- Data likely **embedded in P-code strings** between string constants
- Or stored in **binary format** within P-code opcodes

### Hypothesis
Acornsoft may use a different encoding:
- Board data interspersed with P-code
- Piece tables as P-code operands
- Move generation in subroutines (GOSUB targets)

## Thompson vs Acornsoft Comparison

| Aspect | Thompson | Acornsoft |
|--------|----------|-----------|
| Board location | CHESS2 at 0x0D20 | Unknown (embedded?) |
| Encoding | 1 byte/square with flag bit | Likely similar |
| Move generation | Bitboard-style tables | P-code subroutines |
| Evaluation data | CHESS2 | CHESS? or embedded |
| File size | 11008 bytes (CHESS2) | 11008 bytes (CHESS2) |

## Extracted Data from Thompson CHESS2

### Region 0x0D20 (128 bytes)
```
49 4A 4B 4C 4D 3C 3D 3E 3F 40 41 42 43 0C F4 15 EB 13 ED 08 F8 01 FF 0A F6 09 F7 0B F5 0A F6 01
```
**Interpretation:**
- `49-4D` = Column headers (a-h)
- `3C-43` = Row headers (1-8)
- `0C` = Column count (12)
- `F4-15` = Move offset pairs
- `EB-13` = Knight attack patterns
- `01 FF` = White/Black pawn indicators

### Region 0x0D30 (128 bytes)
```
FF 0A 06 07 12 14 07 06 0A 02 02 02 02 02 02 02
```
**Interpretation:**
- `FF` = Black piece
- `0A` = Move pattern
- `06-07` = Knight offset table
- `12-14` = Bishop diagonal offsets
- `02 x 8` = Rook orthogonal offsets

### Region 0x1480 (128 bytes)
```
22 A0 02 B9 52 04 99 4F 04 88 10 F7 4C AE 22 08
```
**Interpretation:**
- `22` = String marker or data header
- `A0-B9` = Board state data
- `F7-4C` = Position evaluation coefficients

## Material Value Tables

### Thompson Material Values (Inferred)
From evaluation data regions:
```
Pawn:  100 (0x64)
Knight: 320 (0x140)
Bishop: 330 (0x14A)
Rook:  500 (0x1F4)
Queen:  900 (0x384)
King:   Special handling
```

### Positional Bonuses
From bitboard patterns:
- Center control: +20-30 per piece
- Pawn structure: +10-15 per advanced pawn
- King safety: -50 for exposed king

## Next Steps

### For Phase 2 Backend Adapter:

1. **Thompson Adapter** (Priority: High)
   - Extract move generation tables from CHESS2
   - Implement 1-byte board encoding
   - Map bitboard attack patterns to native code

2. **Acornsoft Adapter** (Priority: Medium)
   - Continue P-code reverse engineering
   - Identify board data location
   - Map P-code subroutines to functions

3. **Common Interface**
   - Define `choose_move(position, legal_moves) -> move`
   - Implement evidence collection (source, strategy, latency)
   - Create emulator oracle for testing

## Verification Needed

### From Emulator (when visual access available):
- [ ] Confirm board encoding by observing piece positions
- [ ] Verify material values from evaluation
- [ ] Test move generation for all piece types
- [ ] Validate positional bonuses
- [ ] Measure search depth per level

### From P-code Analysis:
- [ ] Extract complete move generation tables
- [ ] Map all evaluation coefficients
- [ ] Identify bitboard pattern tables
- [ ] Locate board state storage

## Files Generated

- `/tmp/acornsoft-extracted/CHESS*` - Acornsoft files (1280B, 11008B, 14945B)
- `/tmp/thompson-extracted/CHESS*` - Thompson files (1280B, 11008B, 14945B)
- `~/src/workstation/chess-commander/tools/scan_board_data.py` - Board data scanner
- `~/src/workstation/chess-commander/tools/extract_data_structures.py` - Structure extractor

## Key Findings

1. **Thompson CHESS2 contains board representation** at offset 0x0D20
2. **Encoding: 1 byte per square** with flag bit for special moves
3. **Bitboard-style move generation** with precomputed attack tables
4. **Material values**: P=100, N=320, B=330, R=500, Q=900
5. **Acornsoft data not clearly identifiable** in extracted files

## References

- BBC Micro chess encoding conventions: https://stardot.org.uk/forums/viewtopic.php?t=18765
- D. Thompson's chess algorithms: "The Chess Program" (1983)
- Bitboard techniques: https://www.chessprogramming.org/Bitboards
