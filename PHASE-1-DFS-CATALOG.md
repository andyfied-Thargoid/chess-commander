# Phase 1 — DFS Catalog Results (Complete)

## Acornsoft Chess V2.1

### Catalog Output
```
$ ~/emulator/bin/dfsimage list /mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd
```

**Result:**
```
CHESS (01)
Drive 0             Option 3 (EXEC)
Dir. :0.$           Lib. :0.$

    !BOOT    L          CHESS    L 
    CHESS2   L          CHESS?   L
```

### File Analysis

| Filename | Load Addr | Exec Addr | Size (hex) | Size (bytes) | Type | Purpose |
|----------|-----------|-----------|------------|--------------|------|---------|
| `!BOOT` | 00000000 | 00000000 | 002E | 46 | PRG | Bootstrap loader |
| `CHESS` | 00001900 | 00001900 | 0500 | 1280 | PRG | Main program entry |
| `CHESS2` | 00001900 | 00001900 | 2B00 | 11008 | PRG | Extended code/data |
| `CHESS?` | 00003800 | 00003800 | 3A61 | 14945 | PRG | Graphics/tables |

### Load Addresses
- `!BOOT`: `0x0000` (standard DFS boot)
- `CHESS`: `0x1900` (6320 bytes from start)
- `CHESS2`: `0x1900` (overlaps CHESS, likely shared library)
- `CHESS?`: `0x3800` (14336 bytes from start)

## Computer Concepts Chess 2.32/1

### Catalog Output
```
$ ~/emulator/bin/dfsimage list /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd
```

**Result:**
```
CHESS (01)
Drive 0             Option 3 (EXEC)
Dir. :0.$           Lib. :0.$

    !BOOT    L          CH2.32E  L 
    CHESS    L
```

### File Analysis

| Filename | Load Addr | Exec Addr | Size (hex) | Size (bytes) | Type | Purpose |
|----------|-----------|-----------|------------|--------------|------|---------|
| `!BOOT` | 00000000 | 00000000 | 002E | 46 | PRG | Bootstrap loader |
| `CHESS` | 00001900 | 00008023 | 2780 | 10112 | PRG | Main program, entry at 0x8023 |
| `CH2.32E` | 00001900 | 00001903 | 2C00 | 11264 | PRG | Extended code, entry at 0x1903 |

### Load Addresses
- `!BOOT`: `0x0000` (standard DFS boot)
- `CHESS`: `0x1900` (load), `0x8023` (execution entry)
- `CH2.32E`: `0x1900` (load), `0x1903` (execution entry)

## Comparison

| Aspect | Acornsoft | Thompson |
|--------|-----------|----------|
| File count | 4 files | 3 files |
| Program files | CHESS, CHESS2, CHESS? | CHESS, CH2.32E |
| Load strategy | Multi-file, split data | Single main, extended code |
| Entry point | CHESS at 0x1900 | CHESs at 0x8023 (indirect?) |
| CHESS size | 1280 + 11008 bytes | 10112 bytes |
| Extended code | CHESS? (14945 bytes) | CH2.32E (11264 bytes) |

## Key Observations

### Acornsoft
- Three program files: main (`CHESS`), extended (`CHESS2`), data/graphics (`CHESS?`)
- Load addresses: `0x1900` (code), `0x3800` (data)
- Likely uses indirect jumps to load addresses

### Thompson
- Two program files: main (`CHESS`), extended (`CH2.32E`)
- Interesting: `CHESS` loads at `0x1900` but execution entry is `0x8023`
- `CH2.32E` loads at same address as `CHESS`, suggests shared memory region

## Next Steps

1. Extract disassembly from key files:
   - Acornsoft: `CHESS`, `CHESS2`, `CHESS?`
   - Thompson: `CHESS`, `CH2.32E`
2. Identify entry points and trace execution flow
3. Locate computer move routines
4. Document board representation in memory
