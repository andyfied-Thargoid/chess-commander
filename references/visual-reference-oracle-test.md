# Visual reference-oracle test — requirements

**Status:** requirements, ready for execution.
**Owner:** operator on the t14 (has a display + keyboard; runs the emulators
interactively).
**Date:** 2026-11-27.
**Related:** `PLAN.md` (Phase 3 fidelity gates), `SOURCE_HASHES.md`,
`POSITION_CORPUS.json`, `GAME_METADATA.md`.

## Purpose and audience

The Phase 3 fidelity gates compare each **native Python backend** against the
**real emulated reference program** on the same position. compute01 can run the
emulators headlessly but **cannot see the screen**, so it cannot drive these
1980s programs or read the moves they choose. This test is run **on the t14**,
where a human can watch the screen and type. The t14 operator's job is to
produce, for each program and each position, the program's chosen move (and its
candidate set where visible), so the gate can be scored.

This document is the full spec: what to run, how to set up each program, exactly
which positions to test, and the deliverable format. It is self-contained — the
operator does not need any prior context.

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

## Environment (what the t14 needs)

| Item | Value |
|------|-------|
| Emulators | **FUSE** (ZX Spectrum) and **b2** (BBC Micro). If the t14 lacks them, see "Build" below or use any equivalent recent build. |
| Sources | The seven files listed below. |
| Display | Any; the point is a human can see the screen and type. |
| Not needed | Network, GPU, audio (disable it — these have no useful sound). |

> **If the emulators are not on the t14:** the pre-built binaries and build
> scripts are on compute01 under `/home/andyfied/src/fuse-emulator/` and
> `/home/andyfied/src/b2/` (see the `chess-fidelity-emulators` skill for the
> exact build path). Easiest path: copy the source files below to the t14 and
> use any standard FUSE + b2 build. FUSE runs a `.tap`/`.tzx`/`.z80`; b2 runs a
> `.ssd`.

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
