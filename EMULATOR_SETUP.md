# Chess Commander Emulator Workspace

This directory holds external analysis tools and emulator binaries for BBC Micro chess program extraction.

## Structure

- `binaries/` - Emulator and analysis tool executables
- `config/` - Disposable emulator configurations, CMOS snapshots, save-state directories
- `logs/` - Tool execution logs and traces
- `workspace/` - Temporary working directories for emulator runs (cleared between campaigns)

## Tool Installation

### B-Em (primary emulator)
```bash
# From https://github.com/stardot/b-em
# Install via apt or build from source
sudo apt install b-em  # if available
# OR compile:
git clone https://github.com/stardot/b-em
cd b-em && make
```

### dfsimage (disk utility)
```bash
# From https://github.com/monkeyman79/dfsimage
# Go module or pre-built binary
go get github.com/monkeyman79/dfsimage
```

### bbcdisasm (disassembler)
```bash
# From https://github.com/chriskillpack/bbcdisasm
# Build from Go module
git clone https://github.com/chriskillpack/bbcdisasm
cd bbcdisasm && go build
```

### jsbeeb (interactive fallback)
```bash
# From https://github.com/mattgodbolt/jsbeeb
# Node.js based, install via npm or download pre-built
```

## Usage Notes

- All emulator runs must use disposable config from `config/` directory
- Do not commit binaries, config, or workspace state to Git
- Record tool versions and commit hashes in `logs/` for reproducibility
- SSD images remain external at `/mnt/scratch/project-data/chess-commander/`

## Phase 0 Checklist

Before Phase 1 execution, verify:
- [ ] B-Em installed and functional (`b-em --version`)
- [ ] dfsimage installed and working
- [ ] bbcdisasm built and functional
- [ ] jsbeeb available as fallback
- [ ] All tools listed in this directory with version records
