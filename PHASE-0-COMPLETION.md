# Chess Commander Emulator Setup - Complete

## Created Structure

```
~/emulator -> /mnt/scratch/chess-commander/emulator
├── bin/
│   ├── b-em          - BBC Micro emulator (GPL, v-a76c365) ✅
│   ├── dfsimage      - DFS catalog tool (Python, v0.9rc3) ✅
│   ├── bbcdisasm     - 6502 disassembler (Go) ✅
│   └── jsbeeb        - BBC Micro emulator (Node.js, v2.3.2) ✅
├── b-em/             - Source + build artifacts
├── dfsimage/         - Source clone
├── bbcdisasm/         - Source clone
└── jsbeeb/           - Pre-built Debian package
```

## Tool Status

| Tool | Status | Version | Purpose |
|------|--------|---------|---------|
| **B-Em** | ✅ Built | v-a76c365 | Primary emulator with debugger |
| **dfsimage** | ✅ Installed | v0.9rc3 | DFS catalog listing/file export |
| **bbcdisasm** | ✅ Built | Go | 6502 disassembly at load addresses |
| **jsbeeb** | ✅ Installed | v2.3.2 | Interactive fallback |

## B-Em Build Notes

- Installed dependencies: `autoconf`, `automake`, `libtool`, `libsdl2-dev`, `libpng-dev`, `libjpeg-dev`, `zlib1g-dev`, `liballegro5-dev`, `libgtk-3-dev`, `libasound2-dev`
- Built with SDL output (GTK disabled)
- Binary at `bin/b-em` (~8MB)

## Phase 0 Complete Checklist

✅ Both source paths, sizes, and SHA-256 values verified on compute01  
✅ Emulator, disk utility, and disassembler workflow selected  
✅ All tools installed and functional  
✅ Distribution boundary recorded  
✅ Common move/evidence contract defined  
✅ Initial position corpus generated and JSON-validated  
✅ Workspace directory created on md0 with symlink  

## Usage Examples

### B-Em (primary)
```bash
~/emulator/bin/b-em /mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd -m3
```

### dfsimage (DFS catalog)
```bash
~/emulator/bin/dfsimage list /mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd
```

### bbcdisasm (disassembly)
```bash
~/emulator/bin/bbcdisasm list /mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd
```

## Next: Phase 1

Ready for Paperclip-managed `phase1-toolchain` task:
1. Smoke-load both SSDs in B-Em
2. Capture DFS catalogs via dfsimage
3. Extract disassembly with bbcdisasm
4. Document startup behavior and memory layout
