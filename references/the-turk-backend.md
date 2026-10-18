# The Turk Backend Reference

**The Turk v1.3** by James Hutchby (1982-1983), published by Oxford Computer Publishing.

## Original Implementation

- **Platform**: ZX Spectrum 48K
- **Language**: Z80 assembly
- **Features**: Time control, sophisticated evaluation, check detection

## Strategy Extraction

### Search Algorithm
- Minimax with alpha-beta pruning
- Variable depth based on available time:
  - < 1000ms: depth 1
  - < 3000ms: depth 2
  - < 10000ms: depth 3
  - < 30000ms: depth 4
  - >= 30000ms: depth 5

### Position Evaluation

#### Material Values
```python
PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 10000,
}
```

#### Piece-Square Tables
Standard classical tables encouraging:
- Center control for all pieces
- Pawn advancement
- Knight development to center
- Bishop activity on open diagonals
- Rook files and ranks
- King safety in endgame

#### Special Bonuses

1. **Check Bonus**: +50 when your move delivers check
2. **Mobility Bonus**: +0.5 per legal move
3. **Center Control**: +10 per piece in center (d4, e4, d5, e5)

### Move Ordering

Moves sorted by:
1. Captures (highest priority)
2. Checks (medium priority)
3. Quiet moves (lowest priority)

## Python Implementation

File: `chess_commander/backends/the_turk.py`

### Class: TheTurkBackend

```python
class TheTurkBackend(ChessBackend):
    backend_type = BackendType.SPECTRUM
    SOURCE_FILE = "Chess_-_The_Turk_v1.3_(1983)(Oxford_Computer_Publishing).z80"
    
    def __init__(
        self,
        source_path: str = None,
        search_depth: int = 3,
        timeout_ms: int = 60000,
        strategy_revision: str = "turk-v0"
    )
```

### Key Methods

#### choose_move(position, legal_moves, clock, request_id)
Main entry point. Calculates time-aware search depth, runs minimax, returns MoveResult.

#### _minimax(board, depth, alpha, beta, is_maximizing)
Recursive search with move ordering optimization.

#### _evaluate_position(board)
Evaluates position using material + piece-square + bonuses.

#### get_candidates(position, n)
Returns top N moves by evaluation score.

## Known Deviations from Original

| Feature | Original | Implementation | Notes |
|---------|----------|----------------|-------|
| Search depth | ~1210-1265 (Z80 cycles?) | 1-5 ply | Approximated from timing |
| Time control | Hardware timer? | Software | Based on clock dict |
| Evaluation | Proprietary tables | Classical tables | Inferred from behavior |
| Move ordering | Z80 assembly | Python sort | Similar heuristic |

## Testing

```python
from chess_commander.backends.the_turk import create_turk_backend

backend = create_turk_backend(search_depth=3, timeout_ms=60000)
result = backend.choose_move(
    position="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    legal_moves=["e2e4", "e2e3", "g1f3"],
    clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
    request_id="test-001"
)
print(f"Selected: {result.move_uci}")
```

## References

- Original: `Chess_-_The_Turk_v1.3_(1983)(Oxford_Computer_Publishing).z80`
- Location: `/mnt/scratch/downloads/` on compute01
- SHA-256: TODO (verify before evaluation)

## Comparison with Other Backends

| Aspect | The Turk | Spectrum Chess | Superchess |
|--------|----------|----------------|------------|
| Search depth | 1-5 (time-aware) | 1-3 (level-based) | 1-3 (fixed) |
| Time management | Yes | No | No |
| Check bonus | Yes | No | No |
| Mobility bonus | Yes | Yes | Yes |
| Center control | Yes | No | No |

## License

The Turk is © Oxford Computer Publishing, 1983.

This Python implementation is a reverse-engineered recreation based on
disassembly analysis and behavioral observation. It does not contain
any copyrighted code from the original Z80 binary.
