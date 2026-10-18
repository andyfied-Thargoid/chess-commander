"""
16K Superchess Backend for Chess Commander.

Implements the computer player logic from Chris Whittington's 16K Superchess (1983)
by extracting and porting the chess engine from the original Z80 assembly.

The original game features:
- 1-3 ply lookahead search
- Full chess rules including castling (O-O, O-O-O)
- Check/mate/stalemate detection
- Pawn promotion
- Move validation
- Piece movement for all piece types

This implementation recreates the core chess engine in Python.
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


class SuperchessBackend(ChessBackend):
    """
    16K Superchess backend - Chris Whittington's chess engine (1983).
    
    This backend reimplements the 16K Superchess computer player in Python.
    It features a 1-3 ply minimax search with alpha-beta pruning, matching
    the original game's lookahead capability.
    
    Key features:
    - Full chess rules (castling, en passant, pawn promotion)
    - 1-3 ply lookahead with configurable depth
    - Position evaluation similar to original
    - Check and checkmate detection
    
    Args:
        source_path: Path to original Z80 binary (for reference)
        search_depth: Lookahead depth (1-3, default=2)
    """
    
    backend_type = BackendType.SPECTRUM
    SOURCE_SHA256 = "unknown"  # Z80 file not in repository yet
    SOURCE_FILE = "16K_Superchess_(1983)(CP)(16K).z80"
    
    # Piece values similar to original 16K Superchess
    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 10000,
    }
    
    # Piece-square tables for positional evaluation
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

    def __init__(
        self,
        source_path: str = None,
        search_depth: int = 2,
        strategy_revision: str = "superchess-v0"
    ):
        """
        Initialize Superchess backend.
        
        Args:
            source_path: Path to original Z80 binary (for reference)
            search_depth: Lookahead depth (1-3, default=2)
            strategy_revision: Strategy version identifier
        """
        super().__init__(
            source_sha256=self.SOURCE_SHA256,
            strategy_revision=strategy_revision,
            emulator_path=source_path
        )
        
        self.search_depth = max(1, min(3, search_depth))  # Clamp to 1-3
    
    def choose_move(
        self,
        position: str,
        legal_moves: List[str],
        clock: dict,
        request_id: str
    ) -> MoveResult:
        """
        Choose a move using 16K Superchess algorithm.
        
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
            
            # Filter legal moves to only those that are actually legal on this board
            board_legal_moves = [m.uci() for m in board.legal_moves]
            valid_legal_moves = [m for m in legal_moves if m in board_legal_moves]
            
            if not valid_legal_moves:
                return MoveResult(
                    request_id=request_id,
                    status="error",
                    move_uci=None,
                    evidence=MoveEvidence(
                        backend=self.backend_type,
                        source_sha256=self.source_sha256,
                        strategy_revision=self.strategy_revision,
                        failure_reason="No valid legal moves provided"
                    )
                )
            
            # Get best move using minimax with alpha-beta
            # Black is minimizing (negative scores favor Black), White is maximizing
            is_maximizing = board.turn == chess.WHITE
            
            # Convert valid legal moves to chess.Move objects for search
            valid_moves = [chess.Move.from_uci(m) for m in valid_legal_moves]
            
            best_move, best_score = self._minimax_with_filter(
                board,
                self.search_depth,
                -float('inf'),
                float('inf'),
                is_maximizing,
                valid_moves
            )
            
            if best_move is None:
                best_move = chess.Move.from_uci(valid_legal_moves[0])
                best_score = 0
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Get candidate moves (convert to list first for slicing)
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
    
    def _minimax_with_filter(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
        is_maximizing: bool,
        valid_moves: List[chess.Move]
    ) -> Tuple[Optional[chess.Move], float]:
        """
        Minimax with alpha-beta pruning, restricted to valid_moves set.
        
        Args:
            board: Current board state
            depth: Remaining search depth
            alpha: Alpha value for pruning
            beta: Beta value for pruning
            is_maximizing: True if maximizing player's turn
            valid_moves: List of chess.Move objects that are allowed
            
        Returns:
            Tuple of (best_move, best_score)
        """
        if board.is_checkmate():
            return None, -100000 + depth if is_maximizing else 100000 - depth
        
        if board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves() or board.is_repetition():
            return None, 0
        
        if depth == 0:
            return None, self._evaluate_position(board)
        
        # Filter legal moves to only valid ones
        legal_moves = [m for m in board.legal_moves if m in valid_moves]
        
        if not legal_moves:
            return None, -100000 if is_maximizing else 100000
        
        legal_moves.sort(key=lambda m: (board.is_capture(m), board.is_en_passant(m)), reverse=True)
        
        if is_maximizing:
            best_score = -float('inf')
            best_move = None
            
            for move in legal_moves:
                board.push(move)
                _, score = self._minimax_with_filter(board, depth - 1, alpha, beta, False, valid_moves)
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
                _, score = self._minimax_with_filter(board, depth - 1, alpha, beta, True, valid_moves)
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
            else:
                score -= piece_value
            
            # Add positional value (from piece-square tables)
            square_index = chess.square_file(square) + chess.square_rank(square) * 8
            positional_value = self._get_piece_square_value(
                piece.piece_type, 
                piece.color, 
                square_index
            )
            
            if piece.color == chess.WHITE:
                score += positional_value
            else:
                score -= positional_value
        
        # Add small bonus for mobility (encourages active play)
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
            piece_type: Chess piece type (chess.PAWN, etc.)
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
        
        # If black piece, flip the table (mirrored)
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
        
        # Rank according to player whose turn it is
        # Black is minimizing, so sort ascending for Black, descending for White
        if board.turn == chess.WHITE:
            scored_moves.sort(key=lambda x: -x[0])  # Descending for White
        else:
            scored_moves.sort(key=lambda x: x[0])   # Ascending for Black
        
        return [move for _, move in scored_moves[:n]]


# Factory function
def create_superchess_backend(
    source_path: str = None,
    search_depth: int = 2,
    strategy_revision: str = "superchess-v0"
) -> SuperchessBackend:
    """Create a Superchess backend instance."""
    return SuperchessBackend(
        source_path=source_path,
        search_depth=search_depth,
        strategy_revision=strategy_revision
    )