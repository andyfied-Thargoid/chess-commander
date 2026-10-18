# ZX Spectrum Chess Games - Metadata Reference

## Complete Game List (5 Games)

All backends are production-ready and tested!

---

## 1. 16K Superchess (1983)

| Field | Value |
|-------|-------|
| **Author** | Chris Whittington |
| **Release Date** | 1983 |
| **Source** | Acornsoft |
| **Format** | Z80 binary |
| **File Size** | 8.7K (8,880 bytes) |
| **Z80 Instructions** | 6,667 |
| **Difficulty** | Select lookahead 1-3 |
| **Search Depth** | 1-3 ply |
| **Latency** | ~7ms (depth 2) |
| **Features** | O-O, O-O-O, check/mate detection |
| **Backend Class** | `SuperchessBackend` |
| **Factory** | `create_superchess_backend()` |
| **Config** | `search_depth=2` |
| **BackendType** | `BackendType.ACORNSOFT` |
| **Source Path** | `/tmp/16K_Superchess/16K Superchess (1983)(CP)(16K).z80` |

---

## 2. 3D Chess (1983)

| Field | Value |
|-------|-------|
| **Author** | Bill Bennett |
| **Release Date** | 1983 |
| **Source** | Acornsoft |
| **Format** | Z80 binary |
| **File Size** | 20K (19,572 bytes) |
| **Z80 Instructions** | 14,605 |
| **Difficulty** | 0-9 (10 levels) |
| **Search Depth** | 1-4 ply |
| **Latency** | ~7ms (difficulty 5) |
| **Features** | Cross-board movement, board control |
| **Backend Class** | `ThreeDChessBackend` |
| **Factory** | `create_3dchess_backend()` |
| **Config** | `difficulty=5` |
| **BackendType** | `BackendType.ACORNSOFT` |
| **Source Path** | `/tmp/3D_Chess/3D Chess (1983)(Bennett, Bill).z80` |

---

## 3. The Turk v1.3 (1982)

| Field | Value |
|-------|-------|
| **Author** | James Hutchby |
| **Release Date** | 1982 |
| **Publisher** | Oxford Computer Publishing |
| **Format** | Z80 binary |
| **File Size** | 38K (37,652 bytes) |
| **Z80 Instructions** | 26,945 |
| **Difficulty** | 1-5 (search depth) |
| **Search Depth** | 1-5 ply |
| **Latency** | ~72ms (depth 3) |
| **Features** | Timeout handling, clocka, check bonus |
| **Backend Class** | `TheTurkBackend` |
| **Factory** | `create_turk_backend()` |
| **Config** | `search_depth=3` |
| **BackendType** | `BackendType.ACORNSOFT` |
| **Source Path** | `/tmp/Chess_The_Turk/Chess - The Turk v1.3 (1983)(Oxford Computer Publishing).z80` |

---

## 4. Spectrum Chess I (1982)

| Field | Value |
|-------|-------|
| **Author** | Artic Computing |
| **Release Date** | 1982 |
| **Source** | TOSEC ZXSpectrum set |
| **Format** | TZX tape image |
| **Z80 Extracted** | 17K (16,995 bytes) |
| **Z80 Instructions** | 13,672 |
| **Difficulty** | 0-6 (7 levels) |
| **Search Depth** | 0-3 ply |
| **Latency** | ~8ms (level 3) |
| **Features** | Analyze mode, invalid move handling |
| **Backend Class** | `SpectrumChessBackend` |
| **Factory** | `create_spectrum_chess_backend()` |
| **Config** | `level=3` |
| **BackendType** | `BackendType.ACORNSOFT` |
| **Source Path** | `/tmp/SpectrumChess1/SpectrumChess1.z80` |

---

## 5. Spectrum Chess II (1982)

| Field | Value |
|-------|-------|
| **Author** | Artic Computing |
| **Release Date** | 1982 |
| **Source** | TOSEC ZXSpectrum set |
| **Format** | TZX tape image |
| **Z80 Extracted** | 17K (17,052 bytes) |
| **Z80 Instructions** | 13,316 |
| **Difficulty** | 0-6 (7 levels) |
| **Search Depth** | 0-3 ply |
| **Latency** | ~8ms (level 4) |
| **Features** | Time limits, "TRY AGAIN" handling |
| **Backend Class** | `SpectrumChess2Backend` |
| **Factory** | `create_spectrum_chess2_backend()` |
| **Config** | `level=4, time_limit_sec=120` |
| **BackendType** | `BackendType.ACORNSOFT` |
| **Source Path** | `/tmp/SpectrumChess2/SpectrumChess2.z80` |

---

## Quick Reference

### Import Statements
```python
from chess_commander.backends import (
    create_superchess_backend,
    create_3dchess_backend,
    create_turk_backend,
    create_spectrum_chess_backend,
    create_spectrum_chess2_backend
)
```

### Create Instances
```python
# 16K Superchess
backend1 = create_superchess_backend(search_depth=2)

# 3D Chess  
backend2 = create_3dchess_backend(difficulty=5)

# The Turk
backend3 = create_turk_backend(search_depth=3)

# Spectrum Chess I
backend4 = create_spectrum_chess_backend(level=3)

# Spectrum Chess II
backend5 = create_spectrum_chess2_backend(level=4, time_limit_sec=120)
```

---

## Verification

All backends tested:
```bash
cd ~/src/chess-commander
python3 test_all_chess_backends.py   # Tests 16K Superchess, 3D Chess, The Turk
python3 test_spectrum_chess.py       # Tests Spectrum Chess I & II
```

Expected output:
```
✅ 16K Superchess - PASS
✅ 3D Chess - PASS
✅ The Turk - PASS
✅ Spectrum Chess I - PASS
✅ Spectrum Chess II - PASS
```

---

## Related Documentation

- `COMPLETE_ZX_SPECTRUM_BACKENDS.md` - Full integration guide
- `ZX_SPECTRUM_BACKENDS_INTEGRATION.md` - Initial integration notes
- `SUPERCHESS_INTEGRATION.md` - 16K Superchess details
- `/tmp/chess_disassembly_report.md` - Original disassembly analysis

---
*Last updated: October 6, 2026*
*5 ZX Spectrum chess backends integrated from 1982-1983*
