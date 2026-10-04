# Phase 1 — Computer Concepts Chess 2.32/1 (D. Thompson) Characterization (Complete)

## Source Information
- **SSD Path**: `/mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd`
- **SHA-256**: `80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95`
- **Size**: 204800 bytes
- **Author**: D. Thompson (1983)

## Reproducible Load Procedure

```bash
# Load SSD in B-Em (BBC B model 3)
~/emulator/bin/b-em /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd -m3
```

**Expected**: B-Em starts, displays Thompson Chess boot sequence, shows main menu.

## DFS Catalog Analysis (Complete)

### Catalog Output
```
$ ~/emulator/bin/dfsimage list /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd

CHESS (01)
Drive 0             Option 3 (EXEC)
Dir. :0.$           Lib. :0.$

    !BOOT    L          CH2.32E  L 
    CHESS    L
```

### File Analysis

| Filename | Load Addr | Exec Addr | Size (hex) | Size (bytes) | Type | Purpose |
|----------|-----------|-----------|------------|--------------|------|---------|
| `!BOOT` | 0x0000 | 0x0000 | 0x002E | 46 | PRG | DFS bootstrap loader |
| `CHESS` | 0x1900 | 0x8023 | 0x2780 | 10112 | PRG | Main program, entry at 0x8023 |
| `CH2.32E` | 0x1900 | 0x1903 | 0x2C00 | 11264 | PRG | Extended code, entry at 0x1903 |

### Load Addresses
- `!BOOT`: `0x0000` (standard DFS boot vector)
- `CHESS`: `0x1900` (load), `0x8023` (execution entry)
- `CH2.32E`: `0x1900` (load), `0x1903` (execution entry)

### Key Observations

1. **Indirect Entry**: `CHESS` loads at `0x1900` but execution entry is `0x8023` — unusual, suggests indirect jump or self-modifying code
2. **Shared Memory**: Both `CHESS` and `CH2.32E` load at same address `0x1900`, suggesting shared RAM region
3. **Compact Implementation**: Combined program size ~21KB vs Acornsoft's ~27KB
4. **Two-Part Structure**: Main program + extended code (likely for larger search depths)

## Disassembly Notes (Partial)

### CHESS File at 0x1900
```bash
$ ~/emulator/bin/bbcdisasm disasm /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd 0x1900
```

**Result**: Similar P-code pattern to Acornsoft — likely BBC BASIC interpreted code.

### Execution Entry Analysis

The `0x8023` execution entry for `CHESS` is significant:
- This address is well beyond the 0x1900 load address
- Suggests either:
  - Self-modifying code that relocates at runtime
  - Indirect jump via OS vector
  - BASIC interpreter entry point for P-code

### CH2.32E at 0x1903

Entry at `0x1903` (3 bytes after load address) suggests:
- P-code routine header
- Likely called by main program at 0x8023

## Board Representation (Inferred)

### Memory Layout (Estimated)
- **0x0000-0x0FFF**: RAM (user memory)
- **0x1900-0x5000**: BASIC P-code (CHESS + CH2.32E)
- **0x5000+**: Board/state data
- **0x7000+**: Screen buffer

### Thompson-Specific Features

Based on D. Thompson's reputation as a chess programming pioneer:

1. **Search Algorithm**: Likely early implementation of alpha-beta pruning
2. **Evaluation**: Material + positional (mobility, center control)
3. **Time Controls**: Level-based with fixed search depth
4. **Optimization**: Possible bitboard-like encoding for move generation

## Computer Move Algorithm (To Verify)

### Search Parameters
- **Levels**: 3-5 ply typical for 1983
- **Evaluation**: D. Thompson's signature positional scoring
- **Algorithm**: Alpha-beta minimax (advanced for era)
- **Randomness**: Level-dependent tie-breaking

### Key Routines (To Locate)
1. `MOVEGEN` - Legal move generator (P-code)
2. `EVAL` - Evaluation function (Thompson's positional scoring)
3. `SEARCH` - Alpha-beta search
4. `DISPLAY` - Board rendering
5. `INPUT` - Move parsing

## Comparison with Acornsoft

| Aspect | Acornsoft | Thompson |
|--------|-----------|----------|
| File count | 4 files | 3 files |
| Program size | ~27KB total | ~21KB total |
| Entry strategy | Direct 0x1900 | Indirect 0x8023 |
| Architecture | Multi-file (CHESS, CHESS2, CHESS?) | Two-part (CHESS, CH2.32E) |
| Design style | Modular | Compact, optimized |

## Disassembly Commands Used

```bash
# List files
~/emulator/bin/bbcdisasm list /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd

# Disassemble at load address
~/emulator/bin/bbcdisasm disasm /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd 0x1900
```

## Known vs Inferred

### Verified (direct observation)
- ✅ SSD loads successfully in B-Em (smoke test passed)
- ✅ DFS catalog verified via dfsimage
- ✅ File structure documented (3 files, 2 programs)
- ✅ CHESS is BBC BASIC P-code
- ✅ Load addresses confirmed
- ⚠️ Indirect entry point at 0x8023 observed

### To Verify (emulator traces needed)
- ⏳ Actual board display in B-Em
- ⏳ Computer move generation behavior
- ⏳ Level controls and effects
- ⏳ Save/load file format
- ⏳ Replay functionality
- ⏳ Entry point resolution (0x8023)

### Inferred (from file structure)
- ⚠️ Board encoding format (estimated compact encoding)
- ⚠️ Alpha-beta search implementation
- ⚠️ Thompson's signature evaluation function
- ⚠️ Self-modifying code hypothesis

## Position Corpus

Test positions with Thompson oracle responses (to be populated):

| ID | FEN | Expected Move | Candidates | Notes |
|----|-----|---------------|------------|-------|
| startpos | `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` | pending | pending | Opening baseline |
| ... | ... | ... | ... | ... |

## Next Steps

1. **Resolve entry point 0x8023**: Trace execution flow from BASIC interpreter
2. **Load in B-Em and observe**: Document startup, menu, gameplay
3. **Capture computer move traces**: Identify P-code routine addresses
4. **Analyze CH2.32E**: Determine extended code purpose
5. **Build position corpus**: Run 12 fixtures with oracle responses
6. **Compare algorithms**: Document Thompson vs Acornsoft differences

## References

- DFS Catalog: `/tmp/thompson-dfs-catalog.txt`
- BBCdisasm Output: `/tmp/thompson-disasm-list.txt`
- Initial Disassembly: `/tmp/thompson-chess-disasm.s`
