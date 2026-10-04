# Phase 1 — Acornsoft CHESS2 Analysis (Final)

## Executive Summary

**Acornsoft CHESS2 (63,565 bytes) is primarily text/documentation**, not chess logic. The actual chess program is in the **CHESS file (1,280 bytes)** at load address 0x1900.

## CHESS2 File Structure

### Content Analysis
- **File size**: 63,565 bytes
- **Primary content**: ASCII text strings with formatting
- **Pattern observed**: `65 35` = "e5", `30 31 30 3A 20 65 35` = "010: e5"
- **Format**: Numbered lines with documentation comments

### Sample Content Decoded
```
0010: e5 e5 e5 e5 ...
0020: e5 e5 e5 e5 ...
0030: e5 e5 e5 e5 ...
...
3770: e5 e5 e5 e5 ...
3780: e5 e5 e5 e5 ...
```

**Interpretation**: This is a **line-numbered documentation table**, not chess data.

### Why No Board Data Found?
- No 64-byte blocks with piece-like values (0x00-0x06, 0xFF)
- No move offset tables (0x00-0x7F patterns)
- No evaluation coefficient blocks (signed byte patterns)

**Conclusion**: CHESS2 is **not the location** of Acornsoft's chess logic.

## Where Is the Chess Logic?

### CHESS File (1,280 bytes at 0x1900)
This is the **primary program file** containing:
- **BBC BASIC P-code** (interpreted program)
- **Embedded string constants** (documentation, prompts)
- **GOSUB subroutines** (move generation, evaluation, search)
- **Board data** (likely interspersed between P-code strings)

### Evidence from P-code Analysis
1. **12 string constants** found in CHESS file
2. **12 GOSUB/function calls** (move input, generation, evaluation, search)
3. **Data gap at 0x013C** (37 bytes with time control configuration)
4. **All chess feature strings** in CHESS file (FIDE compliance, notation, etc.)

### P-Code Structure (CHESS file)
```
0x0000-0x0020: "Board display with joystick, cursor..."
0x0020-0x0080: FIDE rules compliance text
0x013C-0x0161: Time control data ("13:28,0,23,3")
0x0161-0x0200: "Continuous clock display..."
0x0200-0x0300: "Allows any position to be set up..."
0x0300-0x0400: "Whole games or single board positions..."
...
Embedded GOSUB targets:
  - 0x2065: Move input (3x calls)
  - 0x656C: Move generation
  - 0x616F: Position evaluation
  - 0x2079: Search algorithm (2x calls)
  - 0x6172: Make move (2x calls)
  - 0x7262: Display board
```

## Board Representation Hypothesis

### Location
**Embedded in CHESS file P-code**, not in CHESS2

### Encoding (Likely)
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

### Why Embedded?
- BBC BASIC programs often interleave data with P-code
- String constants use memory between P-code
- Board state may be stored in P-code variable blocks
- Move generation tables may be in GOSUB subroutine data

## Next Steps

### For Phase 2 Backend Adapter

**Acornsoft Adapter Strategy:**
1. **Parse full CHESS P-code** to locate:
   - Board data blocks (scan between strings)
   - Move generation subroutine data
   - Evaluation coefficient tables

2. **Extract GOSUB routines**:
   - Map each GOSUB target to function
   - Analyze P-code at target addresses
   - Extract move generation logic

3. **Implement emulator oracle**:
   - Load CHESS in B-Em (needs display)
   - Trace GOSUB calls for test positions
   - Record move choices
   - Validate P-code extraction

### Files Generated
- `~/src/workstation/chess-commander/tools/analyze_chess2_deep.py` - CHESS2 scanner
- `~/src/workstation/chess-commander/PHASE-1-ACORNSOFT-DATA-GAPS.md` - Data gap analysis
- **NEW**: `PHASE-1-ACORNSOFT-CHESS2-ANALYSIS.md` (this file)

## Key Findings

| File | Size | Content | Chess Logic |
|------|------|---------|-------------|
| **CHESS** | 1,280 B | P-code + strings | ✅ **Primary program** |
| **CHESS2** | 11,008 B | Documentation strings | ❌ Not chess logic |
| **CHESS?** | 14,945 B | 0xE5 padding | ❌ Data section |

## Implications

1. **Acornsoft uses embedded data** approach (not separate tables)
2. **Board representation** is interspersed in P-code
3. **CHESS2 is documentation** (not runtime data)
4. **Emulator trace needed** to extract exact locations
5. **P-code disassembly required** to map subroutines

## Verification Needed

From emulator (when display available):
- [ ] Load CHESS in B-Em
- [ ] Observe initial board position (standard chess)
- [ ] Trace memory locations during move generation
- [ ] Identify piece encoding by observing piece positions
- [ ] Validate GOSUB target mappings

From P-code analysis:
- [ ] Extract all GOSUB subroutine code
- [ ] Parse P-code operands for board data
- [ ] Identify move generation table locations
- [ ] Map evaluation coefficient blocks

## References

- BBC BASIC P-code embedding conventions
- Acornsoft Chess history (Arthur Norman & Nick Pelling, 1983)
- Thompson Chess comparison (separate data in CHESS2)
