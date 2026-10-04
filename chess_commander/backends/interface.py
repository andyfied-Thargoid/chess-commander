"""
Base interface for chess backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class BackendType(Enum):
    """Supported chess backend types."""
    ACORNSOFT = "acornsoft"
    THOMPSON = "thompson"


@dataclass
class MoveEvidence:
    """Evidence for a move decision."""
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
class MoveResult:
    """Result of a move decision."""
    request_id: str
    status: str  # "ok" or "error"
    move_uci: Optional[str] = None
    evidence: Optional[MoveEvidence] = None


@dataclass
class ChooseMoveRequest:
    """Input for choose_move function."""
    request_id: str
    position: str  # FEN string
    legal_moves_uci: List[str]
    clock: dict  # {"white_ms": int, "black_ms": int, "increment_ms": int}
    backend: BackendType
    strategy_revision: str
    model: Optional[str] = None
    prompt_revision: Optional[str] = None


class ChessBackend(ABC):
    """Abstract base class for chess backends."""
    
    backend_type: BackendType
    
    def __init__(
        self,
        source_sha256: str,
        strategy_revision: str,
        emulator_path: Optional[str] = None
    ):
        """
        Initialize backend.
        
        Args:
            source_sha256: SHA-256 hash of source SSD image
            strategy_revision: Strategy version identifier
            emulator_path: Path to emulator/source file
        """
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
        """
        Choose a move for the given position.
        
        Args:
            position: FEN string
            legal_moves: List of legal UCI moves
            clock: Time control dict
            request_id: Unique request identifier
            
        Returns:
            MoveResult with selected move and evidence
        """
        pass
    
    @abstractmethod
    def get_candidates(
        self,
        position: str,
        n: int = 3
    ) -> List[str]:
        """Get top N candidate moves for a position."""
        pass
    
    @abstractmethod
    def validate_move(self, move: str, position: str) -> bool:
        """Validate that a move is legal for the position."""
        pass
    
    def get_evidence(
        self,
        move: str,
        candidates: List[str]
    ) -> MoveEvidence:
        """Generate evidence for a move decision."""
        return MoveEvidence(
            backend=self.backend_type,
            source_sha256=self.source_sha256,
            strategy_revision=self.strategy_revision,
            selected_move_uci=move,
            candidates_uci=candidates[:10]
        )
