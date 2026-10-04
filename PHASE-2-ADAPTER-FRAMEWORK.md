# Phase 2 — Backend Adapter Framework

## Overview

This document defines the common interface and implementation patterns for both chess backends (Acornsoft and Thompson) to integrate with the Punchess referee system.

## Common Interface Contract

### Choose Move Interface

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class BackendType(Enum):
    ACORNSOFT = "acornsoft"
    THOMPSON = "thompson"

@dataclass
class MoveResult:
    """Result of a move decision."""
    request_id: str
    status: str  # "ok" or "error"
    move_uci: Optional[str] = None
    evidence: Optional['MoveEvidence'] = None

@dataclass
class MoveEvidence:
    """Evidence for the move decision."""
    backend: BackendType
    source_sha256: str
    strategy_revision: str
    model: Optional[str] = None
    prompt_revision: Optional[str] = None
    candidates_uci: Optional[List[str]] = None
    selected_move_uci: Optional[str] = None
    latency_ms: Optional[int] = None
    seed: Optional[int] = None
    trace_ref: Optional[str] = None
    failure_reason: Optional[str] = None

@dataclass
class ChooseMoveRequest:
    """Input for choose_move."""
    request_id: str
    position: str  # FEN
    legal_moves_uci: List[str]
    clock: dict  # {"white_ms": int, "black_ms": int, "increment_ms": int}
    backend: BackendType
    strategy_revision: str
    model: Optional[str] = None
    prompt_revision: Optional[str] = None
```

### Core Function Signature

```python
def choose_move(
    request: ChooseMoveRequest
) -> MoveResult:
    """
    Choose a move for the given position.
    
    Args:
        request: Move decision request with position, legal moves, clock
        
    Returns:
        MoveResult with selected move and evidence
        
    Raises:
        ValueError: If request is invalid
        TimeoutError: If backend times out
        RuntimeError: If backend fails
    """
    pass
```

## Backend Implementation Patterns

### Abstract Base Class

```python
from abc import ABC, abstractmethod

class ChessBackend(ABC):
    """Abstract base class for chess backends."""
    
    def __init__(
        self,
        source_sha256: str,
        strategy_revision: str,
        emulator_path: Optional[str] = None
    ):
        self.source_sha256 = source_sha256
        self.strategy_revision = strategy_revision
        self.emulator_path = emulator_path
    
    @abstractmethod
    def choose_move(
        self,
        position: str,
        legal_moves: List[str],
        clock: dict,
        request_id: str
    ) -> MoveResult:
        """Choose a move for the given position."""
        pass
    
    @abstractmethod
    def get_candidates(
        self,
        position: str,
        n: int = 3
    ) -> List[str]:
        """Get top N candidate moves."""
        pass
    
    @abstractmethod
    def validate_move(self, move: str, position: str) -> bool:
        """Validate that a move is legal for the position."""
        pass
    
    def get_evidence(self, move: str, candidates: List[str]) -> MoveEvidence:
        """Generate evidence for a move decision."""
        return MoveEvidence(
            backend=self.backend_type,
            source_sha256=self.source_sha256,
            strategy_revision=self.strategy_revision,
            selected_move_uci=move,
            candidates_uci=candidates[:10]  # Top 10 candidates
        )
```

## Thompson Backend Implementation

### Implementation Class

```python
from chess_commander.backends.thompson import ThompsonChessBackend

class ThompsonChessBackend(ChessBackend):
    """Thompson Chess 2.32/1 backend."""
    
    backend_type = BackendType.THOMPSON
    
    def __init__(
        self,
        source_path: str,
        strategy_revision: str = "oracle-v0"
    ):
        super().__init__(
            source_sha256="80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95",
            strategy_revision=strategy_revision,
            emulator_path=source_path
        )
        
        # Load board representation from CHESS2
        self.board_data = self._load_board_data()
        self.material_values = {
            'P': 100,
            'N': 320,
            'B': 330,
            'R': 500,
            'Q': 900,
            'K': 0
        }
    
    def _load_board_data(self) -> bytes:
        """Load 64-byte board representation from CHESS2."""
        with open(self.emulator_path, 'rb') as f:
            f.seek(0x0D20)  # Board data offset
            return f.read(64)
    
    def choose_move(
        self,
        position: str,
        legal_moves: List[str],
        clock: dict,
        request_id: str
    ) -> MoveResult:
        """Choose move using Thompson's bitboard algorithm."""
        import time
        start_time = time.time()
        
        try:
            # Parse position to board state
            board = self._fen_to_board(position)
            
            # Get candidate moves from bitboard tables
            candidates = self._get_bitboard_candidates(board, legal_moves)
            
            # Evaluate candidates using material + positional scoring
            scored_moves = []
            for move in candidates:
                score = self._evaluate_move(board, move)
                scored_moves.append((score, move))
            
            # Sort by score and select best
            scored_moves.sort(key=lambda x: -x[0])
            best_move = scored_moves[0][1]
            
            latency = int((time.time() - start_time) * 1000)
            
            return MoveResult(
                request_id=request_id,
                status="ok",
                move_uci=best_move,
                evidence=self.get_evidence(best_move, [m[1] for m in scored_moves[:10]])
            )
            
        except Exception as e:
            return MoveResult(
                request_id=request_id,
                status="error",
                move_uci=None,
                evidence=MoveEvidence(
                    backend=self.backend_type,
                    source_sha256=self.source_sha256,
                    strategy_revision=self.strategy_revision,
                    failure_reason=str(e)
                )
            )
    
    def _fen_to_board(self, fen: str) -> List[int]:
        """Convert FEN to 64-byte board array."""
        # Thompson uses 1-byte per square encoding
        # 0x00-0x06: White pieces, 0x80-0x86: Black pieces
        board = [0x00] * 64
        
        rank, file = 0, 0
        for char in fen.split()[0]:
            if char == '/':
                rank += 1
                file = 0
            elif char.isdigit():
                file += int(char)
            else:
                square = rank * 8 + file
                piece_value = self._char_to_piece(char)
                board[square] = piece_value
                file += 1
        
        return board
    
    def _char_to_piece(self, char: str) -> int:
        """Convert chess piece character to byte value."""
        mapping = {
            'K': 0x06, 'Q': 0x05, 'R': 0x04,
            'B': 0x03, 'N': 0x02, 'P': 0x01,
            'k': 0x86, 'q': 0x85, 'r': 0x84,
            'b': 0x83, 'n': 0x82, 'p': 0x81
        }
        return mapping.get(char, 0x00)
    
    def _get_bitboard_candidates(
        self,
        board: List[int],
        legal_moves: List[str]
    ) -> List[str]:
        """Get candidate moves using bitboard attack tables."""
        # Use Thompson's bitboard attack tables from CHESS2
        # Return legal moves that are in candidate set
        return legal_moves
    
    def _evaluate_move(
        self,
        board: List[int],
        move: str
    ) -> float:
        """Evaluate a move using material + positional scoring."""
        # Extract from Thompson's evaluation function
        # Material score + mobility + center control
        return 0.0  # Placeholder - needs emulator trace
    
    def _validate_move(self, move: str, position: str) -> bool:
        """Validate move using python-chess."""
        import chess
        board = chess.Board(position)
        try:
            board.push_uci(move)
            return True
        except:
            return False
```

## Acornsoft Backend Implementation (Stub)

```python
from chess_commander.backends.acornsoft import AcornsoftChessBackend

class AcornsoftChessBackend(ChessBackend):
    """Acornsoft Chess V2.1 backend.
    
    TODO: Requires emulator trace to extract:
    - Board representation encoding
    - Move generation algorithm
    - Evaluation function coefficients
    """
    
    backend_type = BackendType.ACORNSOFT
    
    def __init__(
        self,
        source_path: str,
        strategy_revision: str = "oracle-v0"
    ):
        super().__init__(
            source_sha256="72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b",
            strategy_revision=strategy_revision,
            emulator_path=source_path
        )
        
        # TODO: Extract from emulator trace
        self.board_data = None
        self.move_generation_table = None
        self.evaluation_coefficients = None
    
    def choose_move(
        self,
        position: str,
        legal_moves: List[str],
        clock: dict,
        request_id: str
    ) -> MoveResult:
        """Choose move using Acornsoft's FIDE-compliant algorithm.
        
        TODO: Implement after emulator trace:
        1. Parse ASCII text P-code
        2. Extract board representation from strings
        3. Map GOSUB targets to functions
        4. Implement move generation logic
        """
        
        # Placeholder - will be replaced with extracted logic
        return MoveResult(
            request_id=request_id,
            status="error",
            move_uci=None,
            evidence=MoveEvidence(
                backend=self.backend_type,
                source_sha256=self.source_sha256,
                strategy_revision=self.strategy_revision,
                failure_reason="Requires emulator trace for extraction"
            )
        )
```

## Factory Pattern for Backend Selection

```python
from typing import Optional

class BackendFactory:
    """Factory for creating chess backends."""
    
    BACKENDS = {
        "acornsoft": AcornsoftChessBackend,
        "thompson": ThompsonChessBackend
    }
    
    @classmethod
    def create(
        cls,
        backend_type: str,
        source_path: str,
        strategy_revision: str = "oracle-v0"
    ) -> ChessBackend:
        """Create a backend instance."""
        if backend_type not in cls.BACKENDS:
            raise ValueError(f"Unknown backend: {backend_type}")
        
        return cls.BACKENDS[backend_type](
            source_path=source_path,
            strategy_revision=strategy_revision
        )
    
    @classmethod
    def get_available_backends(cls) -> List[str]:
        """List available backend types."""
        return list(cls.BACKENDS.keys())
```

## Integration with Punchess

### Punchess Client Wrapper

```python
from chess_commander.backends.punchess_client import PunchessClient

class PunchessChessClient:
    """Client for integrating chess backends with Punchess."""
    
    def __init__(
        self,
        punchess_url: str,
        backend: ChessBackend
    ):
        self.punchess_url = punchess_url
        self.backend = backend
        self.client = PunchessClient(punchess_url)
    
    async def join_lobby(self, game_id: str) -> None:
        """Join a Punchess lobby."""
        await self.client.join_game(game_id, self.backend.backend_type.value)
    
    async def make_move(self, game_id: str, position: str) -> str:
        """Make a move in a Punchess game."""
        import chess
        board = chess.Board(position)
        legal_moves = [move.uci() for move in board.legal_moves]
        
        # Choose move using backend
        move_result = self.backend.choose_move(
            request_id=game_id,
            position=position,
            legal_moves=legal_moves,
            clock={
                "white_ms": board.white_clock,
                "black_ms": board.black_clock,
                "increment_ms": 0
            },
            strategy_revision=self.backend.strategy_revision
        )
        
        if move_result.status != "ok":
            raise RuntimeError(f"Move selection failed: {move_result.evidence.failure_reason}")
        
        # Submit to Punchess
        move_uci = move_result.move_uci
        await self.client.submit_move(game_id, move_uci)
        
        return move_uci
    
    async def get_report(self, game_id: str) -> dict:
        """Get game report from Punchess."""
        return await self.client.get_game_report(game_id)
```

## Testing Strategy

### Unit Tests

```python
import pytest
from chess_commander.backends.thompson import ThompsonChessBackend

class TestThompsonBackend:
    
    @pytest.fixture
    def backend(self):
        return ThompsonChessBackend(
            source_path="/tmp/thompson-extracted/CHESS2",
            strategy_revision="test-v0"
        )
    
    def test_choose_move_valid(self, backend):
        """Test choosing a valid move."""
        position = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        legal_moves = ["e2e4", "e2e3", "d2d4", ...]
        
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id="test-1"
        )
        
        assert result.status == "ok"
        assert result.move_uci in legal_moves
        assert result.evidence.backend == BackendType.THOMPSON
    
    def test_validate_move_legal(self, backend):
        """Test move validation."""
        assert backend._validate_move("e2e4", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        assert not backend._validate_move("e2e5", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    
    def test_fen_to_board(self, backend):
        """Test FEN to board conversion."""
        board = backend._fen_to_board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        assert board[0] == 0x84  # Black rook
        assert board[1] == 0x82  # Black knight
        assert board[63] == 0x06  # White king
    
    def test_candidates_returned(self, backend):
        """Test candidate move generation."""
        position = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        candidates = backend.get_candidates(position, n=3)
        assert len(candidates) <= 3
        assert "e2e4" in candidates  # Opening move
```

### Integration Tests

```python
class TestPunchessIntegration:
    
    @pytest.fixture
    def client(self):
        return PunchessChessClient(
            punchess_url="http://localhost:8000",
            backend=ThompsonChessBackend(...)
        )
    
    @pytest.mark.asyncio
    async def test_make_move(self, client):
        """Test making a move in Punchess."""
        game_id = "test-game-1"
        position = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        move = await client.make_move(game_id, position)
        
        assert move in ["e2e4", "e2e3", "d2d4", ...]
    
    @pytest.mark.asyncio
    async def test_get_report(self, client):
        """Test getting game report."""
        game_id = "test-game-1"
        report = await client.get_report(game_id)
        
        assert "moves" in report
        assert "pgn" in report
        assert report["backend"] == "thompson"
```

## Configuration

### YAML Configuration File

```yaml
# config/backends.yaml

backends:
  acornsoft:
    enabled: false  # Requires emulator trace
    source_path: /mnt/scratch/project-data/chess-commander/Acornsoft_Chess_V2.1.ssd
    strategy_revision: oracle-v0
    timeout_ms: 30000
    
  thompson:
    enabled: true
    source_path: /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd
    strategy_revision: oracle-v0
    timeout_ms: 30000

punchess:
  url: http://localhost:8000
  timeout_ms: 60000

logging:
  level: INFO
  file: logs/chess-commander.log
```

## Deployment

### Systemd Service

```ini
# /etc/systemd/system/chess-commander.service

[Unit]
Description=Chess Commander Backend Service
After=network.target

[Service]
Type=simple
User=andyfied
WorkingDirectory=/home/andyfied/src/workstation/chess-commander
Environment="PYTHONPATH=/home/andyfied/src/workstation/chess-commander"
ExecStart=/usr/bin/python3 -m chess_commander.server
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
# Dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "chess_commander.server"]
```

## Next Steps

1. ✅ **Design common interface** (this document)
2. ⏳ **Implement Thompson backend** (data available)
3. ⏳ **Extract Acornsoft data** (requires emulator)
4. ⏳ **Write tests** (unit + integration)
5. ⏳ **Integrate with Punchess**
6. ⏳ **Deploy and test**

## References

- [CONTRACT.md](../CONTRACT.md) - Common move/evidence contract
- [PHASE-1-BOARD-REPRESENTATION.md](./PHASE-1-BOARD-REPRESENTATION.md) - Thompson board data
- [PHASE-1-ACORNSOFT-P-CODE-FINAL.md](./PHASE-1-ACORNSOFT-P-CODE-FINAL.md) - Acornsoft P-code analysis
- [contracts/choose-move.v1.schema.json](../contracts/choose-move.v1.schema.json) - JSON schema
