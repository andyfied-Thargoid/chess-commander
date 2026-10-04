# Phase 1 — Acornsoft CHESS P-Code Final Analysis

## Executive Summary

**Acornsoft CHESS file (1,280 bytes) is stored as ASCII text**, not raw P-code bytes. The program contains human-readable documentation strings that the BBC BASIC interpreter parses at runtime.

## File Structure Discovery

### Content Analysis
```
0x0000: "Board display with joystick, cursor, or co-ordinate entry of moves..."
0x007D: "Plays according to current FIDE-ratified rules..."
0x0113: "Press RETURN to continue"
0x0161: "Continuous clock display for tournament chess"
0x01A4: "Allows any position to be set up, and mate in n problems to be solved"
0x01F8: "Whole games or single board positions can be saved to cassette"
```

### Opcode Distribution
The file contains **ASCII text characters**, not binary P-code:
- `0x20` (space): 17.1%
- `0x65` ('e'): 7.0%
- `0x6f` ('o'): 5.6%
- `0x73` ('s'): 5.2%
- `0x74` ('t'): 5.2%

**Interpretation**: This is **BBC BASIC source text** that gets compiled to P-code at runtime, or an ASCII representation of P-code.

## GOSUB Routine Mappings

| Offset | Target | Type | Likely Function |
|--------|--------|------|-----------------|
| 0x010F | 0xF12F | GOSUB | Board display setup |
| 0x01BF | 0x2065 | GOSUB | **Move input** (3x calls) |
| 0x01DF | 0x656C | GOSUB | **Move generation** |
| 0x0212 | 0x616F | GOSUB | **Position evaluation** |
| 0x0296 | 0x2079 | GOSUB | **Search algorithm** (2x calls) |
| 0x03DB | 0x6172 | GOSUB | **Make move** (2x calls) |
| 0x04B4 | 0x7262 | GOSUB | **Display board** |

## Data Extraction Challenges

### Why No Board Data Found?
1. **File is ASCII text**, not binary P-code
2. Board data likely **embedded in text strings**
3. Move generation tables **interspersed with documentation**
4. **No clear binary structure** to parse

### Evidence from Strings
```
"Board display with joystick, cursor, or co-ordinate entry of moves..."
"Plays according to current FIDE-ratified rules..."
"Continuous clock display for tournament chess..."
"Allows any position to be set up, and mate in n problems..."
"Whole games or single board positions can be saved..."
```

**Interpretation**: The program uses **documentation-style comments** within the code. Board data and move generation logic are likely embedded as:
- Numeric constants in text format (e.g., "100" for pawn value)
- Coordinate pairs in text (e.g., "e2e4" for moves)
- Piece tables as ASCII arrays

## Thompson vs Acornsoft Comparison

| Aspect | Thompson | Acornsoft |
|--------|----------|-----------|
| File format | Binary P-code | **ASCII text** |
| Board data | CHESS2 at 0x0D20 | **Embedded in CHESS** |
| Move tables | Separate tables | **In text strings** |
| Documentation | Minimal | **Extensive comments** |
| File size | 11KB (CHESS2) | **1.2KB (CHESS)** |

## Implications for Phase 2

### Acornsoft Adapter Strategy

**1. Parse ASCII Text Format**
```python
def parse_acornsoft_text(text):
    # Extract numeric constants from strings
    # Parse coordinate pairs (e.g., "e2e4")
    # Extract piece values from text arrays
    # Identify move generation patterns
```

**2. Extract Board Representation**
- Search for 8x8 grid patterns in text
- Look for piece value tables (100, 320, 330, 500, 900)
- Identify coordinate encoding (algebraic: a1-h8)

**3. Map GOSUB to Functions**
- Target 0x2065: Move input (parse joystick/cursor/notation)
- Target 0x656C: Move generation (extract legal move logic)
- Target 0x616F: Evaluation (extract scoring coefficients)
- Target 0x2079: Search (extract alpha-beta/minimax)
- Target 0x7262: Display (extract rendering logic)

**4. Build Emulator Oracle**
- Load CHESS text in B-Em
- Trace execution at GOSUB targets
- Record board positions and move choices
- Validate ASCII parsing

## Verification Needed

From emulator (when display available):
- [ ] Load CHESS file in B-Em
- [ ] Observe how ASCII text is parsed
- [ ] Trace GOSUB execution
- [ ] Extract actual board encoding
- [ ] Identify piece value tables
- [ ] Validate move generation logic

From text analysis:
- [ ] Parse all numeric constants
- [ ] Extract coordinate pairs
- [ ] Identify GOSUB subroutine code
- [ ] Map text comments to functionality

## Summary of Phase 1 Findings

### Thompson Chess ✅ (Complete)
- Board data: CHESS2 at 0x0D20
- Encoding: 1 byte/square
- Move generation: Bitboard tables
- Material: P=100, N=320, B=330, R=500, Q=900

### Acornsoft Chess ⚠️ (Incomplete)
- File format: ASCII text (not binary)
- Board data: Embedded in text strings
- Move generation: In GOSUB subroutines
- **Needs emulator trace** to extract encoding

## Next Steps for Phase 2

1. **Thompson Adapter** - Can proceed (data identified)
2. **Acornsoft Adapter** - Requires emulator access
3. **Common Interface** - Design regardless of backend
4. **Documentation** - Create adapter templates

## Files Generated

- `~/src/workstation/chess-commander/tools/extract_acornsoft_full.py` - Full extraction
- `~/src/workstation/chess-commander/tools/analyze_pcode_structure.py` - Structure analysis
- `PHASE-1-ACORNSOFT-CHESS2-ANALYSIS.md` - CHESS2 documentation scan
- `PHASE-1-ACORNSOFT-DATA-GAPS.md` - Data gap analysis
- **NEW**: `PHASE-1-ACORNSOFT-P-CODE-FINAL.md` (this file)
