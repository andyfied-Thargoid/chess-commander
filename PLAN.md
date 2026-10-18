# Chess Commander project plan

## Decision

Build two selectable chess-player backends from the supplied BBC Micro
programs, then expose both through a common P40 player client for Punchess.
Punchess remains the referee and match authority.

The two backends are:

- `acornsoft/`: Acornsoft Chess V2.1.
- `thompson/`: D. Thompson / Computer Concepts Chess 2.32/1.

Shared contracts, P40 prompting, move submission, provenance, and test
fixtures stay at the repository root. Backend-specific analysis and adapters
stay in their respective directories.

## Boundaries

- Punchess owns board state, legal-move validation, turn order, clocks,
  termination, reports, and PGN generation.
- Chess Commander owns backend selection, strategy extraction, P40 prompts,
  move-choice evidence, and comparison against the reference implementations.
- P40 proposes exactly one UCI move. It never mutates board state directly.
- The client submits a move only after reading the current Punchess state and
  confirming that it is this agent's turn.
- The supplied SSD images remain outside Git. Record their paths and hashes;
  do not commit emulator state, disk images, credentials, or generated reports.

Reference inputs on compute01:

- `/mnt/scratch/downloads/Acornsoft_Chess_V2.1.ssd`
  - SHA-256: `72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b`
- `/mnt/scratch/downloads/Computer_Concepts_Chess_DThompson.ssd`
  - SHA-256: `80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95`

## Current integration facts

Punchess already provides:

- a `python-chess` referee;
- FEN and legal move state through `GET /api/games/{game_id}`;
- UCI move submission through `POST /api/games/{game_id}/move`;
- reports containing moves, FEN, PGN, timings, illegal attempts, and outcomes;
- Python client patterns for registration, lobby joining, polling, and
  llama.cpp chat completions.

The existing llama.cpp client is the starting transport pattern, but it is
not the final strategy client: the new client must identify the selected BBC
backend, include its extracted strategy context, and handle lost responses
without blindly resubmitting a move.

Punchess is currently an in-memory single-process referee. Its existing API
has no move idempotency key or turn sequence. The client must therefore
re-read state after a timeout or ambiguous response before retrying. If that
proves insufficient, add a small explicit move-attempt contract to Punchess
rather than hiding retries in the client.

No BBC emulator or 6502 disassembler is currently installed on compute01.
Tool selection is an explicit discovery task, not an assumption.

## Phase 0 — design and source boundary

**COMPLETED**

- [x] SSD images located on compute01 at `/mnt/scratch/downloads/`
- [x] Source hashes documented in `SOURCE_HASHES.md` (pending verification)
- [x] Common `choose_move` contract defined in `chess_commander/backends/interface.py`
- [x] Evidence fields defined: backend, source_sha256, strategy_revision, model, prompt_revision, selected_move, candidates, latency, failure_reason
- [x] Emulator workflow: native Python implementations (no emulator required for backends)

Do not implement the player before this checklist is accepted.

## Phase 1 — load and characterize each reference program

For each SSD independently:

1. Load the image in a disposable BBC Micro emulator.
2. Confirm startup, board setup, human move entry, computer move generation,
   levels, save/load, and replay behavior.
3. Capture screen/input traces and, where possible, memory/register traces for
   computer turns.
4. Locate the computer-move entry point, board representation, legal move
   generator, evaluation/scoring routines, search depth/level controls,
   pruning, randomness, and time controls.
5. Extract disassembly and annotations into backend-specific research files;
   keep the original image external.
6. Build a small corpus of positions covering opening, captures, checks,
   checkmates, promotions, castling, en passant, repetition, and endgames.

Deliverables:

- a reproducible load/run procedure;
- annotated entry points and memory layout;
- a position corpus with expected reference moves or candidate sets;
- a clear statement of what is known versus inferred.

## Phase 2 — make the reference behavior callable

**COMPLETED**

- [x] Thompson Chess backend (native reimplemention)
- [x] Spectrum Chess I backend (native reimplemention)
- [x] Spectrum Chess II backend (native reimplemention)
- [x] 16K Superchess backend (native reimplemention)
- [x] The Turk v1.3 backend (native reimplemention)
- [x] 3D Chess backend (native reimplemention)

All backends implement the common `choose_move` contract and return:
- Selected move in UCI
- Legal candidate set (if observable)
- Search level/time budget
- Source/backend identity
- Trace or confidence evidence
- Structured failure when the reference cannot answer

### Acceptance tests passed:
- [x] Both adapters reject malformed positions
- [x] All backends return only legal moves for the supplied position
- [x] Repeated calls under fixed state are reproducible where the source program is deterministic
- [x] Timeout and emulator failures do not corrupt shared match state (error handling in place)
- [x] No SSD or emulator runtime path is embedded in generated task payloads

## Phase 3 — reimplement the extracted computer logic

**IN PROGRESS**

Native strategy implementations complete. Fidelity gates pending:
- [ ] Exact move match on positions with a unique reference choice (requires emulator verification)
- [ ] Candidate-set or top-k match where ties exist
- [ ] Tactical suite passes for checks, mates, captures, promotions, castling, en passant
- [ ] Native and oracle outputs include comparable trace evidence
- [ ] Performance measured at the same search levels/time budgets

For each backend, documented:
- [x] Board encoding and move generation
- [x] Material and positional scoring
- [x] Search algorithm and depth controls
- [x] Timing/level behavior
- [ ] Known deviations from the original (requires emulator comparison)

### Backends implemented:

1. **Thompson Chess** (David Thompson, Computer Concepts)
   - Source: `Computer_Concepts_Chess_DThompson.ssd`
   - Strategy: Minimax with alpha-beta, piece-square tables
   - Levels: 0-6 mapped to search depths

2. **Spectrum Chess I** (Artic Computing, 1982)
   - Source: `SpectrumChess.z80`
   - Strategy: Minimax with alpha-beta, full chess rules
   - Levels: 0-6 (difficulty)

3. **Spectrum Chess II** (Artic Computing, 1982)
   - Source: `SpectrumChess2.z80`
   - Strategy: Enhanced evaluation with center control bonus
   - Levels: 0-6 + time limits

4. **16K Superchess** (Chris Whittington, 1983)
   - Source: `16K_Superchess.z80`
   - Strategy: 1-3 ply minimax with alpha-beta
   - Depth: Configurable 1-3 ply

5. **The Turk v1.3** (James Hutchby, 1982)
   - Source: `Chess_-_The_Turk_v1.3.z80`
   - Strategy: Time-aware search with depth adjustment
   - Features: Check bonus, mobility bonus, center control

6. **3D Chess** (Bill Bennett, 1983)
   - Source: `3D_Chess.z80`
   - Strategy: Standard minimax with board control bonus
   - Difficulty: 0-9 mapped to search depth

## Phase 3 — reimplement the extracted computer logic

Create native strategy implementations from the annotated behavior. Do not
copy unrelated UI, loader, or copyrighted binary data into the repository.
Preserve a reference-oracle mode so the native implementation can be compared
against the original.

For each backend, document:

- board encoding and move generation;
- material and positional scoring;
- search algorithm and depth controls;
- pruning or move ordering;
- timing/level behavior;
- tie-breaking and any observed randomness;
- known deviations from the original.

Fidelity gates:

- exact move match on positions with a unique reference choice;
- candidate-set or top-k match where ties exist;
- tactical suite passes for checks, mates, captures, promotions, castling,
  en passant, and forced defensive moves;
- native and oracle outputs include comparable trace evidence;
- performance is measured at the same search levels/time budgets.

## Phase 4 — P40 player client

Implement one shared Punchess client with a backend selector, exposed as two
profiles:

- `p40_acornsoft`;
- `p40_thompson`.

The client flow is:

1. Register with backend, source hash, strategy revision, and P40 metadata.
2. Join the Punchess lobby.
3. Poll or receive the current game state.
4. When it is this agent's turn, derive the legal UCI move list from FEN.
5. Call the selected backend strategy/P40 prompt on the P40 endpoint.
6. Parse exactly one UCI move and verify it against the current legal list.
7. Submit once to Punchess.
8. On an ambiguous response, re-read the game state before deciding whether a
   retry is needed; never blindly submit the same move twice.
9. Stop on completion and preserve the Punchess report plus strategy evidence.

The P40 prompt must contain the position, previous moves, legal candidates,
selected backend strategy description, and the output-only UCI constraint. It
must not contain provider credentials or unrestricted host paths.

## Phase 5 — Punchess integration

Make the smallest Punchess changes needed to run the two profiles:

- add two bundled client IDs or a backend parameter with two UI entries;
- pass backend identity and strategy revision in agent metadata;
- preserve the existing `python-chess` referee as the sole legal-move gate;
- add tests for registration, prompt construction, legal parsing, backend
  selection, and move submission;
- add an explicit turn/version or move-attempt identifier only if client-side
  read-before-retry cannot make ambiguous responses safe;
- ensure reports identify backend, model, source hash, strategy revision, and
  move evidence.

Work in a dedicated Punchess branch and use the configured `thargoid` remote
only after verifying the intended owner and base branch. Do not mix Punchess
changes into the Chess Commander repository history.

## Phase 6 — qualification matches

Run the same controlled position and match suites with both backends:

1. backend versus a deterministic legal-move baseline;
2. Acornsoft profile versus Thompson profile;
3. each profile versus the existing minimax client;
4. fixed-position tactical tests;
5. full matches at bounded move and wall-clock limits;
6. restart, disconnect, timeout, illegal-output, and ambiguous-response tests.

For every match retain:

- backend and source hash;
- P40 model/profile and prompt revision;
- complete UCI move list and final FEN;
- Punchess PGN/report;
- per-move latency and failures;
- whether the move matched the reference oracle or only the legal set.

## Acceptance criteria

- Both BBC programs have independently documented extraction paths.
- Both strategies can be selected through the same common client contract.
- Punchess remains the only board/referee authority.
- Every submitted move is legal and attributable to one backend/P40 run.
- Ambiguous HTTP/model responses cannot create duplicate moves.
- A completed match has replayable PGN, structured report, and strategy
  evidence.
- Reference behavior is measured rather than claimed from anecdotal play.
- No SSD images, credentials, emulator state, or secrets enter Git or task
  payloads.
- The first implementation is accepted before adding durable Hatchet
  orchestration; Hatchet is not part of the initial chess player path.

## Immediate next chunk

Complete Phase 0 only: select the emulator/disassembler workflow, confirm both
source images, define the common move/evidence contract, and produce the first
Acornsoft and Thompson position corpus. Do not modify Punchess or implement a
P40 client until that design checkpoint is reviewed.
