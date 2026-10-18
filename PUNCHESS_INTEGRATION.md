# Punchess Integration for ZX Spectrum Backends

## Overview

This document describes how the ZX Spectrum chess backends integrate with the Punches referee system.

## Backend Selection

The Punchess client uses the `backend_type` field to identify which strategy is being used.
All ZX Spectrum backends are now correctly identified as `BackendType.SPECTRUM`:

```python
from chess_commander.backends.interface import BackendType
from chess_commander.backends.spectrum_chess import create_spectrum_chess_backend

backend = create_spectrum_chess_backend()
assert backend.backend_type == BackendType.SPECTRUM
```

## Client Integration

### Creating a Client

```python
from chess_commander.backends.punchess_client import PunchessChessClient
from chess_commander.backends.superchess import create_superchess_backend

backend = create_superchess_backend(search_depth=2)
client = PunchessChessClient(
    punchess_url="http://localhost:8000",
    backend=backend
)
```

### Playing a Game

```python
import asyncio

async def play_game():
    async with client:
        last_move = await client.play_game("game-123")
        return last_move

# Run the game
asyncio.run(play_game())
```

### Game Flow

1. **Join game**: Client registers with Punchess using `backend.backend_type.value`
2. **Poll status**: Client polls `/api/status/{game_id}` for FEN and legal moves
3. **Choose move**: Backend's `choose_move()` is called with position and legal moves
4. **Submit move**: Client submits selected UCI move via `/api/move`
5. **Repeat**: Loop until game ends (checkmate, stalemate, etc.)
6. **Get report**: Client retrieves final PGN and statistics

## Evidence Tracking

Every move includes structured evidence:

```python
from dataclasses import dataclass

@dataclass
class MoveEvidence:
    backend: BackendType              # SPECTRUM
    source_sha256: str                # TODO: verify SSD hash
    strategy_revision: str            # e.g., "spectrumchess-v0"
    selected_move_uci: Optional[str]  # The move chosen
    candidates_uci: Optional[List[str]]  # Top 10 legal moves
    latency_ms: Optional[int]         # Time to compute
    model: Optional[str]              # e.g., "spectrum-depth-2"
    prompt_revision: Optional[str]    # e.g., "level-3"
    failure_reason: Optional[str]     # Error if any
```

## Testing

Run integration tests:

```bash
python3 test_punchess_integration.py
```

Tests verify:
- Backend type is correctly set to `SPECTRUM`
- All returned moves are legal
- Evidence fields are populated
- Punchess client accepts the backend

## Punchess Server Requirements

The client expects the following endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/join` | Join a game with backend |
| GET | `/api/status/{game_id}` | Get game state |
| POST | `/api/move` | Submit a move |
| GET | `/api/report/{game_id}` | Get game report |
| GET | `/api/games` | List available games |
| GET | `/api/stats` | Server statistics |

## Profile Selection

To select a specific ZX Spectrum backend profile on the Punchess UI:

```python
# Register with Punchess
backend_type = client.backend.backend_type.value  # "spectrum"
strategy = client.backend.strategy_revision       # e.g., "spectrumchess-v0"

# Punchess should use these to:
# 1. Display correct backend name in lobby
# 2. Route to appropriate strategy module
# 3. Record in game reports
```

## Next Steps

- [ ] Verify backend selection in Punchess UI
- [ ] Add backend-specific profiles (`p40_spectrum`, `p40_superchess`, etc.)
- [ ] Test with live Punchess server
- [ ] Record full match reports with evidence
- [ ] Add comparison mode (native vs. emulator oracle)
