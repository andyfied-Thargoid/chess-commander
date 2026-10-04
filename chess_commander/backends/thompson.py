"""
Thompson Chess 2.32/1 Backend Implementation.

Extracts board representation from CHESS2 file and implements
move selection using Thompson's bitboard algorithm.
"""

import time
from typing import List, Optional
from dataclasses import dataclass

from .interface import (
    ChessBackend,
    MoveResult,
    MoveEvidence,
    BackendType,
    ChooseMoveRequest
)


class ThompsonChessBackend(ChessBackend):
    """Thompson Chess 2.32/1 backend implementation."""
    
    backend_type = BackendType.THOMPSON
    SOURCE_SHA256 = "80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95"
    
    # Material values from Thompson's evaluation function
    MATERIAL_VALUES = {
        'P': 100, 'N': 320, 'B': 330, 
        'R': 500, 'Q': 900, 'K': 10000
    }
    
    # Bitboard attack patterns (simplified from Thompson's tables)
    KNIGHT_ATTACKS = [
        0x0002040000000402,  # a1
        0x0004080000000804,  # b1
        # ... (64 entries)
    ]
    
    def __init__(
        self,
        source_path: str,
        strategy_revision: str = "oracle-v0"
    ):
        """
        Initialize Thompson backend.
        
        Args:
            source_path: Path to CHESS2 file containing board data
            strategy_revision: Strategy version identifier
        """
        super().__init__(
            source_sha256=self.SOURCE_SHA256,
            strategy_revision=strategy_revision,
            emulator_path=source_path
        )
        
        # Load board representation from CHESS2
        self.board_data = self._load_board_data()
        self.bitboard_tables = self._load_bitboard_tables()
    
    def _load_board_data(self) -> bytes:
        """Load 64-byte board representation from CHESS2 file."""
        with open(self.emulator_path, 'rb') as f:
            f.seek(0x0D20)  # Board data offset
            return f.read(64)
    
    def _load_bitboard_tables(self) -> dict:
        """Load Thompson's bitboard attack tables from CHESS2."""
        tables = {}
        
        # Extract move offset tables
        with open(self.emulator_path, 'rb') as f:
            # Knight attack table (starts at 0x0D30 based on analysis)
            f.seek(0x0D30)
            knight_table = f.read(64)
            tables['knight'] = list(knight_table)
            
            # Bishop attack table
            f.seek(0x1480)
            bishop_table = f.read(64)
            tables['bishop'] = list(bishop_table)
            
            # Rook attack table
            f.seek(0x1490)
            rook_table = f.read(64)
            tables['rook'] = list(rook_table)
        
        return tables
    
    def choose_move(
        self,
        position: str,
        legal_moves: List[str],
        clock: dict,
        request_id: str,
        strategy_revision: Optional[str] = None
    ) -> MoveResult:
        """
        Choose a move using Thompson's algorithm.
        
        Args:
            position: FEN string
            legal_moves: List of legal UCI moves
            clock: Time control dict
            request_id: Unique request identifier
            strategy_revision: Optional strategy version override
            
        Returns:
            MoveResult with selected move and evidence
        """
        import time
        start_time = time.time()
        
        # Use override strategy_revision if provided, otherwise use instance default
        effective_strategy = strategy_revision if strategy_revision is not None else self.strategy_revision
        
        try:
            # Parse position to board state
            board = self._fen_to_board(position)
            
            # Get candidate moves from bitboard tables
            candidates = self._get_bitboard_candidates(board, legal_moves)
            
            # Evaluate candidates
            scored_moves = self._evaluate_candidates(board, candidates)
            
            # Select best move
            best_score, best_move = scored_moves[0]
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return MoveResult(
                request_id=request_id,
                status="ok",
                move_uci=best_move,
                evidence=MoveEvidence(
                    backend=self.backend_type,
                    source_sha256=self.source_sha256,
                    strategy_revision=effective_strategy,
                    selected_move_uci=best_move,
                    candidates_uci=[m[1] for m in scored_moves[:10]],
                    latency_ms=latency_ms,
                    seed=None,
                    trace_ref=None,
                    failure_reason=None
                )
            )
            
        except FileNotFoundError as e:
            return MoveResult(
                request_id=request_id,
                status="error",
                move_uci=None,
                evidence=MoveEvidence(
                    backend=self.backend_type,
                    source_sha256=self.source_sha256,
                    strategy_revision=effective_strategy,
                    failure_reason=f"Source file not found: {e}"
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
                    strategy_revision=effective_strategy,
                    failure_reason=f"Move selection failed: {str(e)}"
                )
            )
    
    def _fen_to_board(self, fen: str) -> List[int]:
        """
        Convert FEN to 64-byte board array.
        
        Uses Thompson's 1-byte encoding:
        - High nibble: piece type (1=P, 2=N, 3=B, 4=R, 5=Q, 6=K)
        - Low nibble: color (0=white, 8=black)
        """
        board = [0x00] * 64
        
        # Parse FEN (format: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1)
        parts = fen.split()
        if len(parts) == 0:
            return board
        
        position_fen = parts[0]
        
        rank, file = 0, 0
        for char in position_fen:
            if char == '/':
                rank += 1
                file = 0
            elif char.isdigit():
                file += int(char)
            else:
                square = rank * 8 + file
                board[square] = self._char_to_piece(char)
                file += 1
        
        return board
    
    def _char_to_piece(self, char: str) -> int:
        """Convert chess piece character to byte value."""
        encoding = {
            # White pieces (high nibble 0)
            'P': 0x10, 'N': 0x20, 'B': 0x30,
            'R': 0x40, 'Q': 0x50, 'K': 0x60,
            # Black pieces (high nibble 8)
            'p': 0x90, 'n': 0xA0, 'b': 0xB0,
            'r': 0xC0, 'q': 0xD0, 'k': 0xE0
        }
        return encoding.get(char, 0x00)
    
    def _get_bitboard_candidates(
        self,
        board: List[int],
        legal_moves: List[str]
    ) -> List[str]:
        """
        Get candidate moves using Thompson's bitboard attack tables.
        
        Filters legal moves to those that are in Thompson's candidate set.
        """
        # For now, return all legal moves
        # TODO: Implement actual bitboard candidate filtering
        return legal_moves
    
    def _evaluate_candidates(
        self,
        board: List[int],
        candidates: List[str]
    ) -> List[tuple]:
        """
        Evaluate candidate moves using Thompson's scoring.
        
        Returns list of (score, move) tuples sorted by score.
        """
        scored_moves = []
        
        for move in candidates:
            score = self._evaluate_move(board, move)
            scored_moves.append((score, move))
        
        # Sort by score (descending)
        scored_moves.sort(key=lambda x: -x[0])
        
        return scored_moves
    
    def _evaluate_move(
        self,
        board: List[int],
        move: str
    ) -> float:
        """
        Evaluate a move using material + positional scoring.
        
        Implements Thompson's evaluation function:
        - Material count
        - Piece mobility
        - Center control
        - Pawn structure
        """
        score = 0.0
        
        # Material score (simplified)
        white_material = sum(
            self.MATERIAL_VALUES.get(piece_char, 0)
            for piece_char in "PNBRQK"
            for square in board
            if (square & 0xF0) == (self._char_to_piece(piece_char) & 0xF0)
        )
        
        black_material = sum(
            self.MATERIAL_VALUES.get(piece_char, 0)
            for piece_char in "pnbrqk"
            for square in board
            if (square & 0xF0) == (self._char_to_piece(piece_char) & 0xF0)
        )
        
        score += white_material - black_material
        
        # TODO: Add mobility, center control, pawn structure
        # These require full Thompson evaluation function extraction
        
        return score
    
    def get_candidates(
        self,
        position: str,
        n: int = 3
    ) -> List[str]:
        """Get top N candidate moves for a position."""
        import chess
        board = chess.Board(position)
        legal_moves = [move.uci() for move in board.legal_moves]
        
        candidates = self._get_bitboard_candidates(
            self._fen_to_board(position),
            legal_moves
        )
        
        # Evaluate and sort
        scored = self._evaluate_candidates(
            self._fen_to_board(position),
            candidates
        )
        
        return [move for _, move in scored[:n]]
    
    def validate_move(self, move: str, position: str) -> bool:
        """Validate that a move is legal for the position."""
        import chess
        try:
            board = chess.Board(position)
            uci_move = chess.Move.from_uci(move)
            if uci_move not in board.legal_moves:
                return False
            return True
        except:
            return False


# Factory function for creating Thompson backend
def create_thompson_backend(
    source_path: str,
    strategy_revision: str = "oracle-v0"
) -> ThompsonChessBackend:
    """Create a Thompson Chess backend instance."""
    return ThompsonChessBackend(
        source_path=source_path,
        strategy_revision=strategy_revision
    )
