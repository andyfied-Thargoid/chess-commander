# Phase 1 — Emulator Analysis Status

## Current State

### Tool Analysis ✅ COMPLETE
- ✅ DFS catalog analysis complete for both programs
- ✅ bbcdisasm successfully lists and extracts file information
- ✅ Program structure documented (P-code vs native assembly)

### Emulator Availability ❌ BLOCKED

**Issue**: Both available emulators require display environment:

#### B-Em (Primary)
- **Status**: Requires X11/display server
- **Command**: `~/emulator/bin/b-em /path/to/image.ssd -m3`
- **Error**: Cannot run in headless SSH session
- **Need**: X11 forwarding or VNC session for visual observation

#### jsbeeb (Fallback)
- **Status**: Requires Chrome sandbox (setuid helper)
- **Command**: `~/emulator/jsbeeb/opt/jsbeeb/jsbeeb`
- **Error**: SUID sandbox not configured (`/mnt/.../chrome-sandbox` not root:4755)
- **Fix needed**: `sudo chown root:root /path/to/chrome-sandbox && chmod 4755 /path/to/chrome-sandbox`
- **Complication**: No sudo available in this session

## What We Know (From File Analysis)

### Acornsoft Chess V2.1
- **Format**: BBC BASIC P-code (not native 6502 assembly)
- **Files**: 
  - `CHESS` at 0x1900 (1280 bytes) - main program
  - `CHESS2` at 0x1900 (11008 bytes) - extended code/library
  - `CHESS?` at 0x3800 (14945 bytes) - data/graphics
- **Entry**: Direct jump at 0x1900
- **Typical 1980s BBC structure**: P-code with data tables

### Thompson Chess 2.32/1
- **Format**: BBC BASIC P-code
- **Files**:
  - `CHESS` at 0x1900 (10112 bytes) - main program
  - `CH2.32E` at 0x1900 (11264 bytes) - extended code
- **Entry**: Indirect jump at 0x8023 (unusual - suggests self-modifying or relocated code)
- **More compact**: ~21KB total vs Acornsoft's ~27KB

## What We Need (But Can't Get Without Display)

### Acornsoft
- ⏳ Visual confirmation of startup sequence
- ⏳ Board display format and encoding
- ⏳ Menu options and level controls
- ⏳ Computer move generation (ply depth, levels)
- ⏳ Save/load file format
- ⏳ Replay functionality

### Thompson
- ⏳ Visual confirmation of startup sequence
- ⏳ Board display format
- ⏳ Menu options and level controls
- ⏳ Computer move generation characteristics
- ⏳ Resolution of 0x8023 indirect entry behavior
- ⏳ Save/load file format

## Alternative Approaches

### Option 1: X11 Forwarding (Recommended)
If you have a local X server:
```bash
# On local machine (before SSH):
xhost +local:

# Then SSH with X forwarding:
SSH_X11_FORWARDING=1 ssh andyfied@compute01
```

Then B-Em will display on your local machine.

### Option 2: VNC Session
Set up a VNC session on compute01:
```bash
# On compute01:
sudo apt install tightvncserver
vncserver :1 -geometry 1024x768 -depth 24
```

Then connect from local machine:
```bash
vncviewer :1
```

### Option 3: Console Mode (Limited)
Some BBC emulators support text-only output, but:
- B-Em: No documented console mode
- jsbeeb: Web-based, requires browser

### Option 4: Manual Documentation from Disk Analysis
Without emulator access, we can still:
- ✅ Document file structure (done)
- ✅ Analyze P-code byte patterns (partial - shows BASIC string patterns)
- ⏳ Extract and analyze CHESS? data section for board encoding
- ⏳ Infer algorithm characteristics from program structure
- ⏳ Compare with documented Acornsoft/Thompson chess implementations

## Next Actions

### If Display Access Available:
1. Launch B-Em with both SSDs
2. Capture screenshots of:
   - Boot sequence
   - Main menu
   - Board display
   - Computer move generation
3. Test all menu options
4. Record level behaviors
5. Document save/load format

### If Display Access Not Available:
1. Extract CHESS? data files and analyze for:
   - Board representation encoding
   - Piece tables
   - Move generation tables
2. Compare P-code patterns between backends
3. Document inferred algorithm characteristics
4. Note: Phase 1 oracle responses will remain `pending` without emulator traces

## Current Deliverables

✅ DFS catalogs (both programs)  
✅ File structure analysis  
✅ Load address documentation  
✅ P-code identification  
✅ Entry point analysis (direct vs indirect)  
⏳ Position corpus: legal moves populated, oracle fields `pending`  
⏳ Board representation: inferred but not verified  
⏳ Computer move algorithm: inferred but not traced  

## Recommendation

For complete Phase 1, **display access is required** to:
- Observe actual gameplay
- Capture computer move behavior
- Verify board encoding
- Build position corpus with oracle responses

If you cannot provide display access, we can:
1. Continue with Phase 2 using inferred characteristics
2. Mark oracle responses as "to be verified when display available"
3. Proceed with adapter framework design based on contract

What would you prefer?
