# Phase 1 — Acornsoft Chess Data Gap Analysis

## Executive Summary

Found **1 significant data gap** in Acornsoft CHESS file at offset **0x013C-0x0161** (37 bytes).
This gap contains what appears to be **board setup data** or **move configuration**.

## Data Gap at 0x013C

### Raw Bytes
```
0D 02 6C 20 F5 FD A5 3D 31 33 3A EF 32 38 2C 30 2C 32 33 2C 33 3A DB 3A 2A 46 58 31 35
```

### Byte-by-Byte Analysis

| Offset | Byte | Interpretation |
|--------|------|----------------|
| 0x013C | `0D` | String terminator / new line |
| 0x013D | `02` | Line number or value |
| 0x013E | `6C` | P-code opcode or value |
| 0x013F | `20` | Space character |
| 0x0140 | `F5` | GOTO opcode |
| 0x0141 | `FD` | GOTO target low byte |
| 0x0142 | `A5` | Variable reference |
| 0x0143 | `3D` | String start ("=") |
| 0x0144 | `31` | Character "1" |
| 0x0145 | `33` | Character "3" |
| 0x0146 | `3A` | Character ":" |
| 0x0147 | `EF` | Control character (FIDE?) |
| 0x0148 | `32` | Character "2" |
| 0x0149 | `38` | Character "8" |
| 0x014A | `2C` | Character "," |
| 0x014B | `30` | Character "0" |
| 0x014C | `2C` | Character "," |
| 0x014D | `32` | Character "2" |
| 0x014E | `33` | Character "3" |
| 0x014F | `2C` | Character "," |
| 0x0150 | `33` | Character "3" |
| 0x0151 | `3A` | Character ":" |
| 0x0152 | `DB` | Control character |
| 0x0153 | `3A` | Character ":" |
| 0x0154 | `2A` | Character "*" |
| 0x0155 | `46` | Character "F" |
| 0x0156 | `58` | Character "X" |
| 0x0157 | `31` | Character "1" |
| 0x0158 | `35` | Character "5" |

### Decoded String
```
"13:28,0,23,3:" *FX15
```

**Interpretation:**
- `13:28,0,23,3:` = Configuration parameters (likely FIDE clock/time settings)
- `*FX15` = BBC BASIC system function (disable graphics cursor)

### Hypothesis: Time Control Configuration

This appears to be **FIDE tournament time control settings**:
- `13:28` = 13 minutes, 28 seconds per player?
- `0,23,3` = Increment or additional time settings?
- Format: `main_time:increment:seconds`

This matches the earlier string mentioning "50-move rule" and FIDE compliance.

## GOSUB Routine Analysis

### Identified Routines (12 total)

| Offset | Target | Type | Likely Function |
|--------|--------|------|-----------------|
| 0x007B | 0x22F1 | function | String initialization |
| 0x010F | 0xF12F | gosub | **Board display** |
| 0x01BF | 0x2065 | gosub | **Move input** |
| 0x01DF | 0x656C | gosub | **Move generation** ("el"?) |
| 0x01E8 | 0x2065 | gosub | **Move validation** |
| 0x0212 | 0x616F | gosub | **Evaluation** ("of"?) |
| 0x0228 | 0x2065 | gosub | **Move generation** (duplicate?) |
| 0x0296 | 0x2079 | gosub | **Search algorithm** |
| 0x03DB | 0x6172 | gosub | **Make move** ("ar"?) |
| 0x0412 | 0x2079 | gosub | **Search** (duplicate) |
| 0x04B4 | 0x7262 | gosub | **Display board** |
| 0x04D0 | 0x6172 | gosub | **Make move** (duplicate) |

### Routine Mapping Hypothesis

```
0x1900: Main program
  ├─ GOSUB 0x2065 (Move input - 3x calls)
  ├─ GOSUB 0x656C (Move generation)
  ├─ GOSUB 0x616F (Position evaluation)
  ├─ GOSUB 0x2079 (Search algorithm - 2x calls)
  ├─ GOSUB 0x6172 (Make move - 2x calls)
  ├─ GOSUB 0x7262 (Display board)
  └─ GOSUB 0xF12F (Board display setup)
```

## String Analysis

### Key Feature Strings Found

1. **"Board display with joystick, cursor, or co-ordinate entry of moves"**
   - Location: 0x0008
   - Confirms 3 input methods

2. **"Plays according to current FIDE-ratified rules, and displays moves as standard FIDE notation"**
   - Location: 0x0113
   - Confirms FIDE compliance

3. **"Continuous clock display for tournament chess"**
   - Location: 0x0161
   - Confirms time control support

4. **"Allows any position to be set up, and mate in n problems to be solved"**
   - Location: 0x01A4
   - Confirms puzzle mode

5. **"Whole games or single board positions can be saved to cassette"**
   - Location: 0x01F8
   - Confirms save/load functionality

## Board Representation Hypothesis

### Where is the board data?

**Location 1: Between strings in CHESS file**
- Data gaps identified at 0x013C-0x0161 (time controls)
- No clear 64-byte board region found

**Location 2: In CHESS2 file**
- Need to scan CHESS2 for board data
- Likely contains move generation tables

**Location 3: Embedded in P-code**
- Board data interspersed with string constants
- Piece tables as P-code operands

### Encoding Scheme (Inferred)

Based on FIDE compliance and 1980s conventions:

```
Board[64] = {
  0x00: Empty
  0x01-0x06: White pieces (P,N,B,R,Q,K)
  0xFF-0xFA: Black pieces (P,N,B,R,Q,K)
}
```

Or alternative (BBC convention):
```
Square = (piece_type << 4) | (color << 3)
0x10: White pawn
0x90: Black pawn
```

## Next Steps for Phase 2

### 1. Scan CHESS2 for Acornsoft Board Data
- Look for 64-byte blocks like Thompson
- Identify move generation tables
- Extract evaluation coefficients

### 2. Map P-code to Functions
```python
def choose_move(position: str, legal_moves: List[str], backend: str) -> MoveResult:
    """
    Acornsoft backend using P-code analysis:
    1. Parse P-code to identify board state at 0x1900
    2. Extract move generation at 0x656C
    3. Call evaluation at 0x616F
    4. Execute search at 0x2079
    """
    pass
```

### 3. Build Emulator Oracle
- Load CHESS in B-Em
- Trace GOSUB calls for test positions
- Record move choices
- Validate against P-code analysis

## Files Generated

- `~/src/workstation/chess-commander/tools/analyze_acornsoft_deep.py` - Deep P-code analyzer
- Extracted data gaps and GOSUB mappings

## Verification Needed

From emulator:
- [ ] Confirm board encoding by observing initial position
- [ ] Verify move generation for each piece type
- [ ] Validate time control settings (13:28,0,23,3)
- [ ] Test mate-in-n puzzle mode
- [ ] Confirm save/load format
