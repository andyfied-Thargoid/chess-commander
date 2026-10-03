# chess-commander

Chess orchestration and agent match control plane with two selectable BBC
Micro chess logic backends.

## Layout

- `acornsoft/` — Acornsoft Chess V2.1 logic and its adapter boundary.
- `thompson/` — D. Thompson / Computer Concepts Chess 2.32/1 logic and its
  adapter boundary.
- Root-level code and tests — shared game, match, transport, persistence, and
  orchestration contracts.

Both backends must expose the same common match interface so the referee and
control plane can run either implementation without backend-specific state
leaking into the shared layer.

## Source images

The reference SSD images are kept outside Git because they are source material
for the adapters, not application runtime data:

- `Acornsoft_Chess_V2.1.ssd`
- `Computer_Concepts_Chess_DThompson.ssd`

The working copies currently live under `/mnt/scratch/downloads` on compute01.
The repository must contain provenance and adapter tests, not untracked disk
images or generated emulator state.

## Project records

- `PLAN.md` — staged extraction and Punchess integration plan.
- `PHASE-0.md` — selected emulator/disassembly workflow and checkpoint status.
- `SOURCE_MANIFEST.json` — verified local source paths and hashes.
- `CONTRACT.md` — common backend move/evidence contract.
- `POSITION_CORPUS.json` — initial legal-position corpus; BBC oracle results are
  populated during Phase 1.
