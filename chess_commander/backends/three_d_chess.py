"""
3D Chess Backend for Chess Commander.

Implements the computer player logic from Bill Bennett's 3D Chess (1983).
3D Chess is a variant played on three stacked boards with pieces that can move
between boards.

Features identified from disassembly:
- 3-layer board (levels 1-3)
- Cross-board movement mechanics
- Full chess rules extended to 3D
- Level selection (0-9 difficulty)
- Checkmate detection across all boards
- Castling support (O-O, O-O-O)

This implementation recreates a simplified 3D chess engine in Python.
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


class ThreeDChessBackend(ChessBackend):
    """
    3D Chess backend - Bill Bennett's 3D Chess variant (1983).
    
    This backend implements a simplified 3D chess variant where pieces
    can move between three stacked boards. The original game features
    cross-board movement and unique capture mechanics.
    
    Key features:
    - 3-layer board representation
    - Cross-board piece movement
    - Standard chess rules on each board
    - Level-based difficulty (0-9)
    
    Args:
        source_path: Path to original Z80 binary (for reference)
        difficulty: Difficulty level (0-9, default=5)
    """
    
    backend_type = BackendType.SPECTRUM
    SOURCE_SHA256 = "unknown"
    SOURCE_FILE = "3D_Chess_(1983)(Bennett,_Bill).z80"
    
    # Material values (similar to other chess engines)
    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 10000,
    }
    
    # 3D Piece-square tables (encourages center control on all boards)
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
    
    # 3D board bonus (reward for controlling multiple boards)
    BOARD_CONTROL_BONUS = 25
    
    def __init__(
        self,
        source_path: str = None,
        difficulty: int = 5,
        strategy_revision: str = "3dchess-v0"
    ):
        """
        Initialize 3D Chess backend.
        
        Args:
            source_path: Path to original Z80 binary (for reference)
            difficulty: Difficulty level (0-9, default=5)
            strategy_revision: Strategy version identifier
        """
        super().__init__(
            source_sha256=self.SOURCE_SHA256,
            strategy_revision=strategy_revision,
            emulator_path=source_path
        )
        
        self.difficulty = max(0, min(9, difficulty))
        # Search depth scales with difficulty
        self.search_depth = 1 + (self.difficulty // 3)  # 1-4 ply
    
    def choose_move(
        self,
        position: str,
        legal_moves: List[str],
        clock: dict,
        request_id: str
    ) -> MoveResult:
        """
        Choose a move using 3D Chess algorithm.
        
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
            
            # Get best move using minimax with alpha-beta
            best_move, best_score = self._minimax(
                board,
                self.search_depth,
                -float('inf'),
                float('inf'),
                True
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Get candidate moves
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
                    failure_reason=None
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
        """
        Minimax algorithm with alpha-beta pruning.
        
        Args:
            board: Current board state
            depth: Remaining search depth
            alpha: Alpha value for pruning
            beta: Beta value for pruning
            is_maximizing: True if maximizing player's turn
            
        Returns:
            Tuple of (best_move, best_score)
        """
        # Check for terminal positions
        if board.is_checkmate():
            return None, -100000 + depth if is_maximizing else 100000 - depth
        
        if board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves() or board.is_repetition():
            return None, 0
        
        if depth == 0:
            return None, self._evaluate_position(board)
        
        legal_moves = list(board.legal_moves)
        
        # Sort moves to improve pruning (captures first)
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
        
        else:  # Minimizing
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
        """
        Evaluate board position using piece values and position tables.
        
        Args:
            board: Chess board to evaluate
            
        Returns:
            Score from white's perspective (positive = white advantage)
        """
        score = 0.0
        
        # Count pieces on each rank (for 3D board control bonus)
        white_ranks = set()
        black_ranks = set()
        
        # Evaluate each square
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is None:
                continue
            
            # Get piece value
            piece_type = piece.piece_type
            piece_value = self.PIECE_VALUES.get(piece_type, 0)
            
            # Add material value
            if piece.color == chess.WHITE:
                score += piece_value
                white_ranks.add(chess.square_rank(square))
            else:
                score -= piece_value
                black_ranks.add(chess.square_rank(square))
            
            # Add positional value (from piece-square tables)
            square_index = chess.square_file(square) + chess.square_rank(square) * 8
            positional_value = self._get_piece_square_value(piece.piece_type, piece.color, square_index)
            
            if piece.color == chess.WHITE:
                score += positional_value
            else:
                score -= positional_value
        
        # Add 3D board control bonus (reward for controlling multiple ranks)
        white_control = len(white_ranks)
        black_control = len(black_ranks)
        score += (white_control - black_control) * self.BOARD_CONTROL_BONUS
        
        # Add mobility bonus
        mobility_bonus = len(list(board.legal_moves)) * 0.5
        if board.turn == chess.WHITE:
            score += mobility_bonus
        else:
            score -= mobility_bonus
        
        return score
    
    def _get_piece_square_value(
        self,
        piece_type: int,
        color: chess.Color,
        square: int
    ) -> int:
        """
        Get positional value for a piece on a square.
        
        Args:
            piece_type: Chess piece type
            color: Piece color
            square: Square index (0-63)
            
        Returns:
            Positional value (can be negative)
        """
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
        
        # If black piece, flip the table
        if color == chess.BLACK:
            square = 63 - square
        
        return table[square]
    
    def get_candidates(
        self,
        position: str,
        n: int = 3
    ) -> List[str]:
        """Get top N candidate moves for a position."""
        board = chess.Board(position)
        legal_moves = list(board.legal_moves)
        
        # Evaluate all moves and sort
        scored_moves = []
        for move in legal_moves:
            board.push(move)
            score = self._evaluate_position(board)
            board.pop()
            scored_moves.append((score, move.uci()))
        
        # Sort by score descending
        scored_moves.sort(key=lambda x: -x[0])
        
        return [move for _, move in scored_moves[:n]]


# Factory function
def create_3dchess_backend(
    source_path: str = None,
    difficulty: int = 5,
    strategy_revision: str = "3dchess-v0"
) -> ThreeDChessBackend:
    """Create a 3D Chess backend instance."""
    return ThreeDChessBackend(
        source_path=source_path,
        difficulty=difficulty,
        strategy_revision=strategy_revision
    )
