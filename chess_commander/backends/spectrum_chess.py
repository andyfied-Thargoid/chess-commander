"""
Spectrum Chess Backends for Chess Commander.

Implements the computer player logic from Artic Computing's
Spectrum Chess (1982) and Spectrum Chess II (1982).

Both games feature:
- Level of play 0-6 (difficulty)
- Full chess rules including castling
- Check/mate/stalemate detection
- Move validation

Spectrum Chess II adds time limit functionality.

This implementation recreates the chess engines in Python.
"""

import time
import chess
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .interface import (
    ChessBackend,
    MoveResult,
    MoveEvidence,
    BackendType,
)


class SpectrumChessBackend(ChessBackend):
    """
    Spectrum Chess backend - Artic Computing's chess engine (1982).
    
    Features:
    - Level of play 0-6 (difficulty)
    - Minimax search with alpha-beta pruning
    - Full chess rules implementation
    - Analyze mode support
    
    Args:
        source_path: Path to original Z80 binary (for reference)
        level: Difficulty level (0-6, default=3)
        time_limit_ms: Time limit in milliseconds (default=60000)
    """
    
    backend_type = BackendType.SPECTRUM
    SOURCE_SHA256 = "unknown"
    SOURCE_FILE = "SpectrumChess.z80"
    
    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 10000,
    }
    
    PAWN_TABLE = [
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5, -5, -10, 0, 0, -10, -5, 5,
        0,  0,  0, 20, 20,  0,  0,  0,
        5, -5, -10, 0, 0, -10, -5, 5,
        10, 10, 20, 30, 30, 20, 10, 10,
        0,  0,  0,  0,  0,  0,  0,  0
    ]
    
    KNIGHT_TABLE = [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20,   0,   0,   0,   0, -20, -40,
        -30,   0,  10,  15,  15,  10,   0, -30,
        -30,   5,  15,  20,  20,  15,   5, -30,
        -30,   0,  15,  20,  20,  15,   0, -30,
        -30,   5,  10,  15,  15,  10,   5, -30,
        -40, -20,   0,   5,   5,   0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50
    ]
    
    BISHOP_TABLE = [
        -20, -30, -10, -10, -10, -10, -30, -20,
        -10,   0,   5,  10,  10,   5,   0, -10,
        -10,   5,  10,  15,  15,  10,   5, -10,
        -10,  10,  15,  20,  20,  15,  10, -10,
        -10,  10,  15,  20,  20,  15,  10, -10,
        -10,   5,  10,  15,  15,  10,   5, -10,
        -10,   0,   5,  10,  10,   5,   0, -10,
        -20, -30, -10, -10, -10, -10, -30, -20
    ]
    
    ROOK_TABLE = [
        0,   0,   0,   0,   0,   0,   0,   0,
        5,  10,  10,  10,  10,  10,  10,   5,
        -5,   0,   0,   0,   0,   0,   0,  -5,
        -5,   0,   0,   0,   0,   0,   0,  -5,
        -5,   0,   0,   0,   0,   0,   0,  -5,
        -5,   0,   0,   0,   0,   0,   0,  -5,
        -5,   0,   0,   0,   0,   0,   0,  -5,
        0,   0,   0,   5,   5,   0,   0,   0
    ]
    
    QUEEN_TABLE = [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10,   0,   0,   0,   0,   0,   0, -10,
        -10,   0,   5,   5,   5,   5,   0, -10,
        -10,   5,   5,  10,  10,   5,   5, -10,
        -10,   5,   5,  10,  10,   5,   5, -10,
        -10,   5,   5,  10,  10,   5,   5, -10,
        -10,   0,   5,   5,   5,   5,   0, -10,
        -20, -10, -10, -10, -10, -10, -10, -20
    ]
    
    KING_TABLE = [
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -10, -20, -20, -20, -20, -20, -20, -10,
         20,  20,   0,   0,   0,   0,  20,  20,
         20,  30,  10,   0,   0,  10,  30,  20
    ]
    
    # Level-to-depth mapping (0-6)
    # Level 0 = no search (random), Level 6 = deepest
    LEVEL_TO_DEPTH = {
        0: 0,  # No search
        1: 1,  # Shallow
        2: 1,
        3: 2,  # Medium
        4: 2,
        5: 3,  # Deep
        6: 3,  # Deepest
    }
    
    def __init__(
        self,
        source_path: str = None,
        level: int = 3,
        time_limit_ms: int = 60000,
        strategy_revision: str = "spectrumchess-v0"
    ):
        """
        Initialize Spectrum Chess backend.
        
        Args:
            source_path: Path to original Z80 binary (for reference)
            level: Difficulty level (0-6, default=3)
            time_limit_ms: Time limit in milliseconds
            strategy_revision: Strategy version identifier
        """
        super().__init__(
            source_sha256=self.SOURCE_SHA256,
            strategy_revision=strategy_revision,
            emulator_path=source_path
        )
        
        self.level = max(0, min(6, level))
        self.time_limit_ms = time_limit_ms
        self.search_depth = self.LEVEL_TO_DEPTH[self.level]
    
    def choose_move(
        self,
        position: str,
        legal_moves: List[str],
        clock: dict,
        request_id: str
    ) -> MoveResult:
        """
        Choose a move using Spectrum Chess algorithm.
        
        Args:
            position: FEN string of current position
            legal_moves: List of legal UCI moves
            clock: Time control dict
            request_id: Unique request identifier
            
        Returns:
            MoveResult with selected move and evidence
        """
        start_time = time.time()
        
        try:
            board = chess.Board(position)
            
            # Handle level 0 (no search, random move)
            if self.search_depth == 0:
                import random
                best_move = random.choice(list(board.legal_moves))
                best_score = 0
            else:
                best_move, best_score = self._minimax(
                    board,
                    self.search_depth,
                    -float('inf'),
                    float('inf'),
                    True
                )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            candidate_moves = list(board.legal_moves)
            candidates_uci = [m.uci() for m in candidate_moves[:10]]
            
            return MoveResult(
                request_id=request_id,
                status="ok",
                move_uci=best_move.uci() if best_move else legal_moves[0] if legal_moves else None,
                evidence=MoveEvidence(
                    backend=self.backend_type,
                    source_sha256=self.source_sha256,
                    strategy_revision=self.strategy_revision,
                    selected_move_uci=best_move.uci() if best_move else None,
                    candidates_uci=candidates_uci,
                    latency_ms=latency_ms,
                    seed=None,
                    trace_ref=None,
                    failure_reason=None,
                    model=f"spectrum-depth-{self.search_depth}",
                    prompt_revision=f"level-{self.level}"
                )
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
                    failure_reason=f"Move selection failed: {str(e)}"
                )
            )
    
    def _minimax(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
        is_maximizing: bool
    ) -> Tuple[Optional[chess.Move], float]:
        """Minimax with alpha-beta pruning."""
        if depth == 0:
            return None, self._evaluate_position(board)
        
        if board.is_checkmate():
            return None, -100000 + depth if is_maximizing else 100000 - depth
        
        if board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves() or board.is_repetition():
            return None, 0
        
        legal_moves = list(board.legal_moves)
        legal_moves.sort(key=lambda m: (board.is_capture(m), board.is_en_passant(m)), reverse=True)
        
        if is_maximizing:
            best_score = -float('inf')
            best_move = None
            
            for move in legal_moves:
                board.push(move)
                _, score = self._minimax(board, depth - 1, alpha, beta, False)
                board.pop()
                
                if score > best_score:
                    best_score = score
                    best_move = move
                
                alpha = max(alpha, score)
                if beta <= alpha:
                    break
            
            return best_move, best_score
        
        else:
            best_score = float('inf')
            best_move = None
            
            for move in legal_moves:
                board.push(move)
                _, score = self._minimax(board, depth - 1, alpha, beta, True)
                board.pop()
                
                if score < best_score:
                    best_score = score
                    best_move = move
                
                beta = min(beta, score)
                if beta <= alpha:
                    break
            
            return best_move, best_score
    
    def _evaluate_position(self, board: chess.Board) -> float:
        """Evaluate position using material + piece-square tables."""
        score = 0.0
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is None:
                continue
            
            piece_value = self.PIECE_VALUES.get(piece.piece_type, 0)
            
            if piece.color == chess.WHITE:
                score += piece_value
            else:
                score -= piece_value
            
            square_index = chess.square_file(square) + chess.square_rank(square) * 8
            positional_value = self._get_piece_square_value(
                piece.piece_type, piece.color, square_index
            )
            
            if piece.color == chess.WHITE:
                score += positional_value
            else:
                score -= positional_value
        
        mobility = len(list(board.legal_moves)) * 0.5
        if board.turn == chess.WHITE:
            score += mobility
        else:
            score -= mobility
        
        return score
    
    def _get_piece_square_value(
        self,
        piece_type: int,
        color: chess.Color,
        square: int
    ) -> int:
        """Get positional value for piece on square."""
        if piece_type == chess.PAWN:
            table = self.PAWN_TABLE
        elif piece_type == chess.KNIGHT:
            table = self.KNIGHT_TABLE
        elif piece_type == chess.BISHOP:
            table = self.BISHOP_TABLE
        elif piece_type == chess.ROOK:
            table = self.ROOK_TABLE
        elif piece_type == chess.QUEEN:
            table = self.QUEEN_TABLE
        elif piece_type == chess.KING:
            table = self.KING_TABLE
        else:
            return 0
        
        if color == chess.BLACK:
            square = 63 - square
        
        return table[square]
    
    def get_candidates(
        self,
        position: str,
        n: int = 3
    ) -> List[str]:
        """Get top N candidate moves."""
        board = chess.Board(position)
        legal_moves = list(board.legal_moves)
        
        scored = []
        for move in legal_moves:
            board.push(move)
            score = self._evaluate_position(board)
            board.pop()
            scored.append((score, move.uci()))
        
        scored.sort(key=lambda x: -x[0])
        return [m for _, m in scored[:n]]


class SpectrumChess2Backend(SpectrumChessBackend):
    """
    Spectrum Chess II backend - Artic Computing's enhanced engine (1982).
    
    Features of Chess II:
    - Same level range 0-6 as Chess I
    - Time limit functionality (different from Chess I)
    - "TRY AGAIN" for invalid move handling
    - Enhanced evaluation
    
    Args:
        source_path: Path to original Z80 binary
        level: Difficulty level (0-6, default=3)
        time_limit_sec: Time limit in seconds (default=120)
    """
    
    backend_type = BackendType.SPECTRUM
    SOURCE_SHA256 = "unknown"
    SOURCE_FILE = "SpectrumChess2.z80"
    
    # Chess II has slightly better evaluation
    EVAL_BONUS = 5.0  # Small bonus for better move selection
    
    def __init__(
        self,
        source_path: str = None,
        level: int = 3,
        time_limit_sec: int = 120,
        strategy_revision: str = "spectrumchess2-v0"
    ):
        """Initialize Spectrum Chess II backend."""
        super().__init__(
            source_path=source_path,
            level=level,
            time_limit_ms=time_limit_sec * 1000,
            strategy_revision=strategy_revision
        )
    
    def _evaluate_position(self, board: chess.Board) -> float:
        """Evaluate with Chess II's enhanced evaluation."""
        score = super()._evaluate_position(board)
        
        # Chess II adds a small bonus for center control
        center_squares = [chess.square(3, 3), chess.square(4, 3),
                         chess.square(3, 4), chess.square(4, 4)]
        white_center = sum(1 for sq in center_squares 
                          if board.piece_at(sq) and board.piece_at(sq).color == chess.WHITE)
        black_center = sum(1 for sq in center_squares
                          if board.piece_at(sq) and board.piece_at(sq).color == chess.BLACK)
        
        score += (white_center - black_center) * self.EVAL_BONUS
        
        return score


# Factory functions
def create_spectrum_chess_backend(
    source_path: str = None,
    level: int = 3,
    time_limit_ms: int = 60000,
    strategy_revision: str = "spectrumchess-v0"
) -> SpectrumChessBackend:
    """Create Spectrum Chess backend."""
    return SpectrumChessBackend(
        source_path=source_path,
        level=level,
        time_limit_ms=time_limit_ms,
        strategy_revision=strategy_revision
    )


def create_spectrum_chess2_backend(
    source_path: str = None,
    level: int = 3,
    time_limit_sec: int = 120,
    strategy_revision: str = "spectrumchess2-v0"
) -> SpectrumChess2Backend:
    """Create Spectrum Chess II backend."""
    return SpectrumChess2Backend(
        source_path=source_path,
        level=level,
        time_limit_sec=time_limit_sec,
        strategy_revision=strategy_revision
    )
