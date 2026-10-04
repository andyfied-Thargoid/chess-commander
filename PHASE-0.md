# Phase 0 checkpoint

Status: accepted. No player, emulator worker, or Punchess change has been made.

## Selected analysis workflow

1. `dfsimage` is the disk boundary tool. Use it to list DFS catalog entries,
   export individual files, and record file-level digests. It is MIT-licensed,
   supports `.ssd`, and keeps extraction separate from emulator state.
2. B-Em is the primary reference emulator. It runs on Linux, accepts an SSD as
   a command-line disk image, supports BBC B models with the 8271 controller,
   and exposes a debugger through the terminal. Start with BBC B model 3:

       b-em /mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd -m3
       b-em /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd -m3

   These commands are procedure examples only; B-Em is not installed on this
   host yet. Emulator runs must use disposable config, CMOS, and save-state
   directories outside the repository.
3. `bbcdisasm` is the first-pass 6502/DFS analysis tool. Build it from its Go
   module, use its `list` operation to enumerate the image, then disassemble
   extracted files at their DFS load addresses. Use emulator debugger traces to
   refine code/data boundaries and annotate indirect jumps or self-modifying
   code.
4. jsbeeb is the interactive fallback if B-Em cannot reproduce display/input
   behavior. It is Node-based and useful for manual screen/input confirmation,
   but it is not the primary batch oracle.

References:

- B-Em: https://github.com/stardot/b-em
- bbcdisasm: https://github.com/chriskillpack/bbcdisasm
- dfsimage: https://github.com/monkeyman79/dfsimage
- jsbeeb: https://github.com/mattgodbolt/jsbeeb

## Source boundary

`SOURCE_MANIFEST.json` records the two verified local SSDs. The images remain
under `/home/andyfied/Downloads` and are excluded from Git. The source programs'
redistribution status is not established, so the repository may contain
annotations, hashes, and original-authored clean-room reimplementations, but
not copied disk images or extracted binary payloads until licensing is resolved.

Before each extraction campaign:

    sha256sum /mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd
    sha256sum /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd

The output must match `SOURCE_MANIFEST.json`.

## Common contract

`CONTRACT.md` and `contracts/choose-move.v1.schema.json` define the backend
boundary. It returns one legal UCI move plus evidence or a structured failure.
The backend never submits to Punchess; Punchess remains the sole referee.

## Initial corpus

`POSITION_CORPUS.json` contains 12 deterministic FEN fixtures covering:

- initial and developed openings;
- white and black to move;
- captures and tactical play;
- check evasion and mate-in-one;
- castling;
- en passant;
- promotion with and without capture;
- sparse endgames; and
- the fifty-move boundary.

The legal UCI sets are generated with `python-chess` and are complete. The
Acornsoft and Thompson oracle fields intentionally remain `pending`; filling
them is Phase 1 work and must come from observed reference runs, not guessed
engine behavior.

Regenerate the corpus with:

    uv run --with python-chess python3 tools/build_position_corpus.py

## Exit criteria for Phase 0

- [x] Both source paths, sizes, and SHA-256 values verified on compute01.
- [x] Emulator, disk utility, and disassembler workflow selected.
- [x] Distribution boundary recorded.
- [x] Common move/evidence contract defined.
- [x] Initial position corpus generated and JSON-validated.
- [x] User review/acceptance of this checkpoint.

## Next stage after acceptance

Phase 1 is handed to Paperclip as `TAU-88` under the day-schedule P40 coder.
Install or build the selected analysis tools outside the repository, then run
one smoke-load per SSD after the toolchain task and Codex review are accepted.
Record the DFS catalogue, startup screen, board setup, and one
human/computer turn for each backend before attempting disassembly.
