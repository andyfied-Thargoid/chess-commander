# README — Chess Commander

> Chess orchestration and agent match control plane

## Overview

Chess Commander implements a framework for running chess backends against the Punchess referee system. This repository contains:

- **Chess backends**: Native reimplementations of classic chess programs
- **Punchess integration**: Client for game server interaction
- **Test suite**: Unit tests for backend validation
- **Documentation**: Phase completion reports and API reference

## Project Structure

```
chess-commander/
├── chess_commander/           # Python package
│   ├── __init__.py
│   ├── server.py             # Entry point
│   └── backends/
│       ├── interface.py      # Abstract base class
│       ├── thompson.py       # Thompson Chess 2.32/1
│       └── punchess_client.py # Punchess integration
├── tests/                    # Unit tests
│   └── test_thompson_backend.py
├── config/                   # Configuration
│   └── backends.yaml
├── references/               # Reference documentation
│   └── chess-commander-2026-10-04.md
└── tools/                    # P-code analysis tools
```

## Installation

```bash
cd ~/src/workstation/chess-commander
pip install -r requirements.txt
```

## Usage

### Run Server

```bash
python3 -m chess_commander.server
```

### Use Backend Programmatically

```python
from chess_commander.backends.thompson import ThompsonChessBackend

backend = ThompsonChessBackend(
    source_path='/mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd',
    strategy_revision='oracle-v0'
)

result = backend.choose_move(
    position='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    legal_moves=['e2e4', 'e2e3', 'g1f3'],
    clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
    request_id='game-1'
)

print(f"Selected: {result.move_uci}")  # e2e4
```

### Play on Punchess

```python
from chess_commander.backends.thompson import ThompsonChessBackend
from chess_commander.backends.punchess_client import PunchessChessClient

backend = ThompsonChessBackend(...)
client = PunchessChessClient(punchess_url="http://localhost:8000", backend=backend)

move = await client.play_game("game-123")
```

## Testing

```bash
python3 -m pytest tests/ -v
```

## Documentation

- [chess-commander-2026-10-04](references/chess-commander-2026-10-04.md) — Project reference
- [PHASE-0-COMPLETION.md](PHASE-0-COMPLETION.md) — Phase 0 summary
- [PHASE-1-SMOKE-TESTS.md](PHASE-1-SMOKE-TESTS.md) — Initial test results
- [PHASE-2-COMPLETION.md](PHASE-2-COMPLETION.md) — Phase 2 summary

## Next Steps

- [ ] Acornsoft backend (requires emulator trace)
- [ ] Deploy Punchess server
- [ ] Run live games
- [ ] Enhanced evaluation (mobility, center control)

## License

Proprietary — Chess Commander Project

## Credits

- **David Thompson** — Original Thompson Chess algorithm (1970s)
- **Punchess** — Game referee system
