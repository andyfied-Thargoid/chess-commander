# Visual reference-oracle test — requirements

**Status:** requirements, ready for execution.
**Owner:** operator on the t14 (has a display + keyboard; runs the emulators
interactively).
**Date:** 2026-11-27.
**Related:** `PLAN.md` (Phase 3 fidelity gates), `SOURCE_HASHES.md`,
`POSITION_CORPUS.json`, `GAME_METADATA.md`.

## Purpose and audience

The Phase 3 fidelity gates compare each **native Python backend** against the
**real emulated reference program** on the same position.

**compute01 CAN see and drive the emulated screen** — verified 2026-11-27. It
runs the emulators headlessly under **Xvfb** (a virtual framebuffer, no physical
display needed) and captures the screen with **mss** (X11 `XGetImage`), injecting
keys with **xdotool**. A FUSE + Spectrum Chess I boot frame and a keyboard-injection
frame are saved in this directory as proof. So the "a human must sit at a
display" assumption that originally motivated this document is **no longer
required**: the oracle can be driven from compute01 directly.

**What this means for the work.** The visual test can now be run **on compute01**
as an automated (or semi-automated) oracle driver: boot each program under Xvfb,
inject the keys to reach the position, capture the screen, and read the move the
program plays. The remaining human effort is *decoding the screen* — the
emulated programs use 1980s graphical move-entry (arrows, on-screen cursors,
non-standard notation) that is not always trivially machine-readable, so some
frames still benefit from a human reading them. The t14 remains a valid
**fallback** for any program whose I/O is too hard to automate, but it is no
longer the *only* path.

This document is the full spec: what to run, how to set up each program, exactly
which positions to test, and the deliverable format. It is self-contained — the
operator (human on t14, or an automated driver on compute01) does not need any
prior context.

## The core constraint (read this first)

**None of these seven programs can load an arbitrary FEN position.** They are
1982–1983 home-computer games with their own screen layout and keyboard
move-entry. So there are **two distinct tasks**, and they have different value:

- **Task A — boot & I/O characterization** (high value, always possible): for
  each program, confirm it boots, capture the title/menu screen, and document
  *how it accepts a move* (keyboard layout, move notation, "thinking" indicator,
  how it reports mate/check, and — critically — **whether it can be told an
  arbitrary starting position at all**).
- **Task B — per-position move capture** (the actual gate data): for positions
  the program *can* be set to, record the move it plays. This may be limited to
  startpos and a few reachable positions for some programs. Record *what is
  reachable*, not just the moves.

Task A is required for all seven. Task B is required for as many positions as
each program actually allows. Where a program cannot be set to a position, that
is a **finding to record**, not a failure.

## Environment

### compute01 (verified headless capture + drive toolchain — 2026-11-27)

This is the **primary** path. All components are present and working on
compute01:

| Item | Value |
|------|-------|
| Emulators | **FUSE** `/home/andyfied/src/fuse-emulator/fuse` (ZX Spectrum); **b2** `/home/andyfied/src/b2/` (BBC Micro — rebuild if no binary). |
| Virtual display | **Xvfb** (`/usr/bin/Xvfb`) at 24-bit depth — required, 16-bit fails with mss. |
| Screen capture | **mss** (X11 `XGetImage`) in the repo venv, frames saved as PNG via PIL. |
| Keyboard input | **xdotool** (`/usr/bin/xdotool`). |
| Sources | The seven files listed below (hashes in `SOURCE_HASHES.md`). |
| Not needed | Network, GPU, audio (`--no-sound` — no useful sound). |

Verified: FUSE + Spectrum Chess I boots under Xvfb and renders a non-blank
screen (grey board + blue Spectrum region, ~4.5k blue px); a `Return` keypress
via xdotool produced a visible screen change (cursor-cell update at
(400,129)–(424,137)). Boot + injection frames:
[`fuse-screen-capture-proof.png`](fuse-screen-capture-proof.png) in this
directory.

> **b2 note:** the BBC `.ssd` pair (Acornsoft, Thompson) needs b2. The b2
> source tree is at `/home/andyfied/src/b2/`; if `bin/` has no built binary,
> build it (see the `chess-fidelity-emulators` skill) before running those two.

### t14 (human fallback)

If a program's graphical I/O is too hard to automate from compute01, the same
test can be run on the **t14** with a human watching the screen and typing.
Same emulators/sources; the t14 just adds a physical display + keyboard. The
t14 is no longer the *only* path.

## Verified findings — Spectrum Chess I (2026-11-28)

The oracle driver (`tools/emu_oracle_driver.py`) was driven against Spectrum
Chess I on compute01. What is confirmed vs. what is still open:

**Confirmed (deterministic, verified across repeated runs):**
- Boot: `fuse ... SpectrumChess_I.tzx` under Xvfb reaches the `PLAY / ANALYSE
  / OR LOAD?` menu in ~10s.
- **Menu navigation is reliable** (3/3 runs): `P\r` → `YOUR COLOUR?`, `W\r`
  → `LEVEL OF PLAY?`, `{level}\r` → the board. Each answer is one `xdotool
  type` call with a carriage return appended (one input *unit* per call, fresh
  window focus per call). Levels 0–6 are accepted; level 0 = weakest/fastest.
- The board renders in the standard starting position; the left status panel
  shows the move number, `SPECTRUM` / `PLAYER` (the two sides), and the current
  move entry.
- **The loop works end-to-end** when the move commit lands: playing `e4` and
  committing it makes the computer (Black, level 0) reply `e7→e5` (1...e5),
  detectable as a board frame change.

**Open / flaky (blocks reliable gate execution):**
- **Reading the *computer's* reply is the real blocker** (not move entry).
  Verified: menu navigation is deterministic, and the player move commits
  reliably via `xdotool keydown/keyup` (e.g. `e4` → the white pawn moves to e4
  and the turn passes to Black). But after the player's move commits, **the
  emulated game sits idle and the computer (Black) does not produce an
  observable reply**: the captured frame stays byte-identical (no cursor blink,
  no piece move) for 40–90s, regardless of level (tested 0), trigger key
  (Enter/space/letter), or window activation. So the driver can *play* a move
  but currently *cannot read what the reference program plays back*. This is a
  property of the FUSE 1.10.1 + Spectrum Chess I interaction under Xvfb (the
  game's "computer" turn is not being computed/rendered), **not** a driver bug.
- **RZX recording does not work here**: FUSE `--record <file>` accepts the
  option but produces no `.rzx` file (even on a clean SIGINT exit), so the
  "capture machine state and parse the move" path is not available with this
  FUSE build.

**What IS reliable (use these):**
- Menu navigation + player move entry/commit (as above).
- **Frame difference** (`_frame_diff`) to detect that a move *changed* the
  board — reliable when a move is actually applied.

**Next step to unblock the gate (recommended):** find a way to make the
reference program actually render its move — candidates: (a) a different FUSE
build/config where `--record`/`--playback` works, so the session can be
deterministically replayed and the move parsed from the RZX; (b) confirm whether
the "SPECTRUM" computer needs a specific in-game command (e.g. a "run"/"think"
key) to compute its move; (c) fall back to the t14 (human at a display) for
Spectrum Chess I specifically, since its computer-turn behaviour under headless
Xvfb is not reliable.

**Read-the-move approach that works:** OCR the emulated frame with the local
vision model (Spectrum Chess I's notation is short algebraic, e.g. `E4`), and
detect the computer's reply by **frame difference** between the frame before
and after the player's move — far more reliable than asking an OCR model "did a
piece move?" on every poll.

## t14 procedure — Spectrum Chess I (the unblock path)

Because the emulated computer's reply is not observable headlessly (above), the
**t14 (a display + keyboard)** is the reliable path for reading Spectrum Chess
I's moves. This is a self-contained run sheet — the operator needs no other
context.

**Prep (once, on the t14):**
1. Confirm the exact source: `sha256sum` of `SpectrumChess_I.tzx` matches the
   hash in `SOURCE_HASHES.md`.
2. Launch FUSE: `fuse --machine=48 --no-sound SpectrumChess_I.tzx`. Press
   **Enter** if it waits after the tape load. The `PLAY / ANALYSE / OR LOAD?`
   menu appears.

**Reach a playable game:**
1. `P` (Play) → **Enter**.
2. `YOUR COLOUR?(B,W):` → type `W` (you play White; the computer is Black) →
   **Enter**. (Use `B` to flip which side the computer plays — record it.)
3. `LEVEL OF PLAY? (0-6):` → type a level → **Enter**. Use **`0`** (weakest,
   fastest) for a quick check; use the level you intend to compare against for
   real captures. **Record the level.**

**Play a move and read the computer's reply (the part that does NOT work
headless — on a real display it is visible):**
1. The board is in the standard starting position; it is White's (your) move.
2. Enter your move in the program's notation — Spectrum Chess I takes the move
   as text (short algebraic, e.g. type `e4`) then **Enter** to commit.
3. **Watch the screen:** the computer (Black) will now move a black piece on
   its own. Wait for it — at level 0 it is near-instant; at higher levels it
   may take a few seconds. **This is the move to record.**
4. Read the computer's move from the **screen**: the left status panel lists
   the moves in the program's own notation (e.g. `E4` / `E5`), and the board
   shows which black piece moved. Record it **verbatim**, then convert to UCI
   (e.g. `e7e5`).

**Repeat for each position you need** (see Task B). Spectrum Chess I cannot be
set to an arbitrary FEN, so the only position you can reach is **`startpos`**
(standard start). Record the computer's opening reply there, 3 times (to check
determinism), at a fixed level. For any other corpus position, record
`not_reachable` — do not approximate.

**Deliverable:** `spectrum_chess.oracle.json` (schema in Task B), with entries
for `startpos` (the computer's reply move, verbatim notation + UCI, the level
used, and all 3 runs). If the computer's reply differs across the 3 runs, record
every variant.

## The seven reference programs and their files

| # | Backend | Program | File | Emulator | Notes |
|---|---------|---------|------|----------|-------|
| 1 | `acornsoft` | Acornsoft Chess V2.1 | `Acornsoft_Chess_V2.1.ssd` | b2 | BBC Micro, 6502. |
| 2 | `thompson` | Computer Concepts Chess (D. Thompson) | `Computer_Concepts_Chess_DThompson.ssd` | b2 | BBC Micro, 6502. |
| 3 | `spectrum_chess` | Spectrum Chess I | `SpectrumChess_I.tzx` | FUSE | ZX Spectrum 48K. |
| 4 | `spectrum_chess_2` | Spectrum Chess II | `SpectrumChess_II.tzx` | FUSE | ZX Spectrum 48K. |
| 5 | `superchess` | 16K Superchess (C. Whittington, 1983) | `16K_Superchess.tap` | FUSE | **16K machine** (`--machine=16`). |
| 6 | `the_turk` | The Turk (Oxford Computer, 1983) | `The_Turk.tzx` | FUSE | ZX Spectrum 48K. |
| 7 | `three_d_chess` | 3D Chess (B. Bennett, 1983) | `3D_Chess.z80` | FUSE | A `.z80` **snapshot** (pre-set RAM). ZX Spectrum 48K. |

All seven SHA-256 hashes are in `SOURCE_HASHES.md`. Verify each file's hash
before starting so the operator is testing the exact same binaries the native
backends were derived from.

### How to launch

- **FUSE (Spectrum):** `fuse --machine=48 --no-sound <file>` (use `--machine=16`
  for `16K_Superchess.tap`). Press **ENTER** after tape/snapshot load if it
  waits. A `.z80` loads as a snapshot — the board should appear immediately.
- **b2 (BBC):** `b2 -0 <file.ssd> -b` (auto-boot disc). May need the appropriate
  ROM/double-SID selected; the default modern BBC is fine.

## Task A — per-program boot & I/O characterization

For **each** of the seven, capture and record:

1. **Boot confirmation** — screenshot of the title/menu/first board screen.
2. **How a move is entered** — the exact key sequence or notation for one move
   (e.g. "type `e2` `e4` then ENTER", "arrow keys + ENTER", "click squares",
   "type `E2E4`"). This is the single most important field.
3. **Move notation displayed** — how the program *shows* a move (algebraic,
   long algebraic, coordinates, "1. e4 e5" vs. board-only). Needed to parse the
   move back to UCI.
4. **Thinking indicator** — what the screen shows while the engine computes
   (a spinner, a delay, a "thinking" label) and roughly how long a move takes at
   the default level.
5. **Level / strength selection** — how to pick the playing level, and the
   default. Record the level used for every move in Task B.
6. **Position-setup capability** — can the operator **set an arbitrary starting
   position** (FEN-style entry, piece placement mode, a "set board" menu)? If
   yes, document exactly how. If no, state that plainly.
7. **Special-move handling** — how the program accepts/reports castling,
   en-passant, and promotion (these appear in the corpus).
8. **Terminal states** — how it reports check, checkmate, and stalemate.

Produce one short section per program (a screenshot + 5–10 lines of notes is
enough). This section alone makes the next session's oracle-driver work
possible, even if Task B yields few positions.

## Task B — per-position move capture

The canonical position set is `POSITION_CORPUS.json` (12 positions). The
operator does **not** need to run all 12 against all 7 programs — only the
positions a program can actually be set to. For each program × position it can
handle, record the engine's chosen move.

### Priority (do these first; they exercise the fidelity gates most)

| Corpus id | FEN (copy exactly) | Why it matters |
|-----------|-------------------|----------------|
| `startpos` | `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` | Every program starts here; the baseline move. |
| `mate_in_one` | `7k/5Q2/6K1/8/8/8/8/8 w - - 0 1` | Forced mate — tests tactical detection. |
| `forced_check_evasion` | `4r1k1/8/8/8/8/8/4r3/4K3 w - - 0 1` | Only 2 legal moves — tests legality under check. |
| `queen_capture` | `4k3/8/8/3q4/3R4/8/8/4K3 w - - 0 1` | Forced best capture. |
| `promotion_choice` | `4k3/P7/8/8/8/8/8/4K3 w - - 0 1` | Promotion selection. |
| `en_passant_white` | `r3k2r/ppp2ppp/8/3pP3/8/8/PPP2PPP/R3K2R w KQkq d6 0 2` | En-passant legality. |
| `castling_both_sides` | `r3k2r/ppp2ppp/2npbn2/8/8/2NPBN2/PPP2PPP/R3K2R w KQkq - 0 1` | Castling rights. |
| `black_to_move_tactical` | `r1b1k2r/pppp1ppp/2n2n2/4p3/1b2P3/2N2N2/PPPP1PPP/R1BQKB1R b KQkq - 3 5` | Black-to-move handling. |

The remaining 4 (`ruy_lopez_after_a6`, `king_pawn_endgame`,
`fifty_move_boundary`, `promotion_with_capture`) are lower priority; capture them
only if the program's position-setup makes it easy.

### Procedure per (program, position)

1. Set the program to the position (per that program's setup method from Task A).
   **If it cannot be set to this position, stop and record `not_reachable`** —
   do not approximate.
2. Let the program (playing the side to move in the FEN) choose a move at the
   **default level** (record the level if you change it).
3. Record the move **in the program's own notation** (verbatim from screen) and
   convert it to **UCI** (e.g. `e2e4`, `e7e8q`).
4. If the program shows a **candidate list** or evaluation (some show a
   "best moves" panel or a numeric score), record that too — it feeds the
   top-k gate.
5. Repeat each position **3 times** to detect randomness / non-determinism. If
   the move varies across runs, record all variants.

### Deliverable format

One file per program, named `<backend>.oracle.json`, placed alongside the
sources. Schema:

```json
{
  "backend": "superchess",
  "program": "16K Superchess (1983)",
  "source_file": "16K_Superchess.tap",
  "sha256": "<paste from SOURCE_HASHES.md>",
  "emulator": "fuse",
  "level": "default (record which)",
  "captured_utc": "2026-11-27T00:00:00Z",
  "position_setup": {
    "arbitrary": true,
    "method": "exact steps to set a position, e.g. 'SET POS then type FEN'"
  },
  "io": {
    "move_entry": "how a move is typed",
    "move_notation_shown": "long-algebraic",
    "thinking_indicator": "what the screen shows",
    "special_moves": "how castling/en-passant/promotion are handled"
  },
  "positions": {
    "startpos": {
      "reachable": true,
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "runs": [
        {"raw": "e2e4", "move_uci": "e2e4", "candidates_uci": ["e2e4","d2d4"], "eval": null},
        {"raw": "e2e4", "move_uci": "e2e4", "candidates_uci": null, "eval": null},
        {"raw": "d2d4", "move_uci": "d2d4", "candidates_uci": null, "eval": null}
      ]
    },
    "mate_in_one": { "reachable": false, "reason": "no position-setup; only startpos" }
  }
}
```

Rules:
- `move_uci` must be a single legal UCI move for that FEN. Validate with
  `python-chess` (available in the repo venv) before submitting — a wrong UCI
  silently breaks the gate.
- `reachable: false` is a valid, expected outcome. Record the reason.
- Do **not** invent moves. If the program crashes or hangs on a position,
  record `status: "error"` with what happened.

## What compute01 will do with the deliverables (context)

Once the `<backend>.oracle.json` files are back, compute01 will:
1. Load the corpus, run each native backend on each position, and compare the
   native move to the oracle's `move_uci` (exact-match gate), and the native
   top-k to the oracle's `candidates_uci` (top-k gate).
2. Run the tactical suite (mate-in-one, check evasion, capture, promotion,
   castling, en-passant).
3. Score per-backend fidelity and document known deviations in `PLAN.md`.

The quality of the gate is bounded by the quality of these files. **Exact,
verbatim, hash-verified** is what makes the gate meaningful.

## Acceptance criteria (definition of done for this test)

- [ ] All 7 sources verified by SHA-256 before start.
- [ ] Task A complete for all 7 programs (boot screenshot + I/O notes each).
- [ ] At minimum, `startpos` move captured for all 7 programs (the one position
      every program can reach).
- [ ] The 8 priority positions captured for every program that can be set to
      them; `not_reachable` recorded with a reason where not.
- [ ] Each `move_uci` validated as legal for its FEN.
- [ ] 3 runs per position to capture non-determinism.
- [ ] One `<backend>.oracle.json` per program, conforming to the schema above.

## Known limitations / honest expectations

- Many of these programs will **not** allow arbitrary position setup. Expect
  Task B to be thin for several programs; that is a real finding, and it is why
  Task A (the I/O spec) is the high-value deliverable — it lets the next
  session build a proper automated oracle driver instead of guessing.
- `3D_Chess.z80` is a **snapshot**: its board state is whatever the snapshot
  holds, not the FEN start position. Capture whatever position the snapshot
  actually shows (screenshot it), and note it may not match `startpos`.
- These are 40+-year-old programs; some may be flaky, slow, or require a
  specific tape-press sequence. Prefer a screen recording (not just still
  images) for anything ambiguous, so the move sequence is recoverable later.
