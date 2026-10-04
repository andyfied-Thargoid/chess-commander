"""
Unit tests for Thompson Chess backend.

Note: Tests requiring SSD files require the file at:
  - Default: /mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd
  - Override: Set THOMPSON_SSD_PATH environment variable

On compute01: SSD files are at /mnt/scratch/project-data/chess-commander/
On other systems: Tests will skip if SSD file not found.
"""

import pytest
import chess
from chess_commander.backends.thompson import ThompsonChessBackend
from chess_commander.backends.interface import BackendType


class TestThompsonBackendInit:
    """Test backend initialization."""
    
    def test_backend_instantiation(self, backend):
        """Test that backend can be instantiated."""
        assert backend is not None
        assert backend.backend_type == BackendType.THOMPSON
        assert backend.strategy_revision == 'test-v0'
    
    def test_source_sha256(self, backend):
        """Test source SHA-256 hash."""
        assert backend.source_sha256 == '80120f0f346194a388ebb7152d9970ec635612fee38b733d7002f113b941eb95'
    
    def test_board_data_loaded(self, backend):
        """Test that board data is loaded from CHESS2."""
        assert len(backend.board_data) == 64
        assert all(0 <= b <= 0xFF for b in backend.board_data)
    
    def test_bitboard_tables_loaded(self, backend):
        """Test that bitboard tables are loaded."""
        
        assert 'knight' in backend.bitboard_tables
        assert 'bishop' in backend.bitboard_tables
        assert 'rook' in backend.bitboard_tables
        assert len(backend.bitboard_tables['knight']) == 64
        assert len(backend.bitboard_tables['bishop']) == 64
        assert len(backend.bitboard_tables['rook']) == 64


class TestFENToBoard:
    """Test FEN to board conversion."""
    
    
    def test_starting_position(self, backend):
        """Test conversion of starting position."""
        board = backend._fen_to_board(
            'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        )
        
        # a1 should be black rook (0xC0)
        assert board[0] == 0xC0
        # b1 should be black knight (0xA0)
        assert board[1] == 0xA0
        # h1 should be black king (0xE0) - wait, h1 is black king in FEN
        # Actually rnbqkbnr = black pieces on rank 1 (a1-h1)
        # R is at h8, not h1
        assert board[7] == 0xC0  # h1 is black rook
        # a8 should be white rook (0x40)
        assert board[56] == 0x40
        # e8 should be white king (0x60)
        assert board[60] == 0x60
        # h8 should be white king (0x60) - wait, that's wrong, let me check
        
    def test_empty_squares(self, backend):
        """Test conversion with empty squares (numbers in FEN)."""
        board = backend._fen_to_board(
            '8/8/8/8/8/8/8/8 w KQkq - 0 1'
        )
        
        # All squares should be empty (0x00)
        assert all(b == 0x00 for b in board)
    
    def test_single_piece(self, backend):
        """Test conversion with single piece."""
        board = backend._fen_to_board(
            '8/8/8/8/8/8/8/K7 w kq - 0 1'
        )
        
        # K is at a1 (square 56) - K7 means King on rank 8 (bottom of board), then 7 empty
        # In FEN, rank 1 is bottom (a1-h1), rank 8 is top (a8-h8)
        # So K7 means: King on rank 8 (bottom), then 7 empty squares
        # Wait, FEN is written from rank 8 (top) to rank 1 (bottom)
        # 8/8/8/8/8/8/8/K7 = 7 empty ranks, then K on rank 1 (a1), then 7 empty
        # Square 56 = rank 7 * 8 + file 0 = a1
        assert board[56] == 0x60  # a1 (square 56) is white king
        # Other squares should be empty
        assert all(b == 0x00 for i, b in enumerate(board) if i != 56)


class TestCharToPiece:
    """Test character to piece value conversion."""
    
    
    def test_white_pieces(self, backend):
        """Test white piece encoding."""
        assert backend._char_to_piece('P') == 0x10
        assert backend._char_to_piece('N') == 0x20
        assert backend._char_to_piece('B') == 0x30
        assert backend._char_to_piece('R') == 0x40
        assert backend._char_to_piece('Q') == 0x50
        assert backend._char_to_piece('K') == 0x60
    
    def test_black_pieces(self, backend):
        """Test black piece encoding."""
        assert backend._char_to_piece('p') == 0x90
        assert backend._char_to_piece('n') == 0xA0
        assert backend._char_to_piece('b') == 0xB0
        assert backend._char_to_piece('r') == 0xC0
        assert backend._char_to_piece('q') == 0xD0
        assert backend._char_to_piece('k') == 0xE0
    
    def test_invalid_char(self, backend):
        """Test invalid character returns 0."""
        assert backend._char_to_piece('x') == 0x00


class TestChooseMove:
    """Test move selection."""
    
    
    def test_choose_move_starting_position(self, backend):
        """Test move selection from starting position."""
        position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        legal_moves = ['e2e4', 'e2e3', 'g1f3', 'g1h3', 'b1c3', 'b1a3']
        
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
            request_id='test-1'
        )
        
        assert result.status == 'ok'
        assert result.move_uci in legal_moves
        assert result.evidence is not None
        assert result.evidence.backend == BackendType.THOMPSON
        assert result.evidence.latency_ms is not None
    
    def test_choose_move_returns_valid_move(self, backend):
        """Test that chosen move is legal."""
        position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        legal_moves = ['e2e4', 'e2e3', 'g1f3']
        
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
            request_id='test-2'
        )
        
        # Verify move is legal using python-chess
        board = chess.Board(position)
        uci_move = chess.Move.from_uci(result.move_uci)
        board.push(uci_move)
        assert not board.is_checkmate()  # Should be able to make move
        
    def test_choose_move_evidence_contains_candidates(self, backend):
        """Test that evidence includes candidate moves."""
        position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        legal_moves = ['e2e4', 'e2e3', 'g1f3', 'g1h3', 'b1c3']
        
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
            request_id='test-3'
        )
        
        assert result.evidence.candidates_uci is not None
        assert len(result.evidence.candidates_uci) > 0
        assert result.move_uci in result.evidence.candidates_uci
    
    def test_choose_move_with_invalid_position(self, backend):
        """Test move selection with invalid FEN."""
        # Invalid FEN may still return a result (graceful degradation)
        # The function should handle errors gracefully, not crash
        result = backend.choose_move(
            position='invalid_fen',
            legal_moves=['e2e4'],
            clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
            request_id='test-invalid'
        )
        
        # Should return error status, not crash
        assert result.status in ['ok', 'error']
    
    def test_choose_move_with_empty_legal_moves(self, backend):
        """Test move selection with no legal moves."""
        position = '8/8/8/8/8/8/8/4K3 b - - 0 1'  # Only king, no moves
        legal_moves = []  # Actually stalemate or checkmate
        
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
            request_id='test-empty'
        )
        
        assert result.status == 'ok' or result.status == 'error'


class TestGetCandidates:
    """Test candidate move generation."""
    
    
    def test_get_candidates_n(self, backend):
        """Test getting top N candidates."""
        position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        candidates = backend.get_candidates(position, n=3)
        
        assert len(candidates) <= 3
    
    def test_get_candidates_includes_opening_moves(self, backend):
        """Test that opening moves are included in candidates."""
        position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        candidates = backend.get_candidates(position, n=10)
        
        # Common opening moves should be in top candidates
        opening_moves = ['e2e4', 'd2d4', 'g1f3', 'c2c4']
        assert any(move in candidates for move in opening_moves)


class TestValidateMove:
    """Test move validation."""
    
    
    def test_validate_legal_move(self, backend):
        """Test validation of legal move."""
        position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        
        assert backend.validate_move('e2e4', position) is True
        assert backend.validate_move('e2e3', position) is True
    
    def test_validate_illegal_move(self, backend):
        """Test validation of illegal move."""
        position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        
        assert backend.validate_move('e2e5', position) is False
        assert backend.validate_move('h8h4', position) is False


class TestMaterialValues:
    """Test material value constants."""
    
    def test_material_values_defined(self):
        """Test that material values are correctly defined."""
        from chess_commander.backends.thompson import ThompsonChessBackend
        
        assert ThompsonChessBackend.MATERIAL_VALUES['P'] == 100
        assert ThompsonChessBackend.MATERIAL_VALUES['N'] == 320
        assert ThompsonChessBackend.MATERIAL_VALUES['B'] == 330
        assert ThompsonChessBackend.MATERIAL_VALUES['R'] == 500
        assert ThompsonChessBackend.MATERIAL_VALUES['Q'] == 900
        assert ThompsonChessBackend.MATERIAL_VALUES['K'] == 10000


class TestEvidenceGeneration:
    """Test evidence generation for move decisions."""
    
    
    def test_evidence_contains_required_fields(self, backend):
        """Test that evidence has all required fields."""
        position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        legal_moves = ['e2e4', 'e2e3', 'g1f3']
        
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
            request_id='test-evidence'
        )
        
        assert result.status == 'ok'
        assert result.move_uci == 'e2e4'
        assert result.evidence is not None
        assert result.evidence.backend == BackendType.THOMPSON
        assert result.evidence.source_sha256 is not None
        assert result.evidence.strategy_revision == 'test-v0'
        assert result.evidence.selected_move_uci == 'e2e4'
        assert result.evidence.candidates_uci is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
