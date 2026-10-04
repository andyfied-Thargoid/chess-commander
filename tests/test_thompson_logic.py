"""Tests for Thompson backend logic that don't require SSD files."""
import pytest
from tests.conftest import minimal_backend


class TestMaterialScoring:
    """Test material evaluation logic."""
    
    def test_white_piece_values(self, minimal_backend):
        """Test that white pieces are correctly valued."""
        # Create a simple board with just a white king
        board = [0x00] * 64
        board[60] = 0x60  # White king at e8
        
        score = minimal_backend._evaluate_move(board, 'e2e4')
        # Should have positive score from white king material
        assert score > 0
    
    def test_black_piece_values(self, minimal_backend):
        """Test that black pieces are correctly valued."""
        # Create a simple board with just a black king
        board = [0x00] * 64
        board[60] = 0xE0  # Black king at e8
        
        score = minimal_backend._evaluate_move(board, 'e2e4')
        # Should have negative score from black king material
        assert score < 0
    
    def test_material_balance(self, minimal_backend):
        """Test that equal material gives score near zero."""
        # Create a board with equal white and black kings
        board = [0x00] * 64
        board[60] = 0x60  # White king
        board[4] = 0xE0   # Black king (opposite color)
        
        score = minimal_backend._evaluate_move(board, 'e2e4')
        # Should be close to zero (both sides have king)
        assert -200 < score < 200  # King is 10000, but we're testing balance


class TestCharToPiece:
    """Test character to piece encoding."""
    
    def test_white_pieces(self, minimal_backend):
        """Test white piece encoding."""
        assert minimal_backend._char_to_piece('P') == 0x10
        assert minimal_backend._char_to_piece('N') == 0x20
        assert minimal_backend._char_to_piece('B') == 0x30
        assert minimal_backend._char_to_piece('R') == 0x40
        assert minimal_backend._char_to_piece('Q') == 0x50
        assert minimal_backend._char_to_piece('K') == 0x60
    
    def test_black_pieces(self, minimal_backend):
        """Test black piece encoding."""
        assert minimal_backend._char_to_piece('p') == 0x90
        assert minimal_backend._char_to_piece('n') == 0xA0
        assert minimal_backend._char_to_piece('b') == 0xB0
        assert minimal_backend._char_to_piece('r') == 0xC0
        assert minimal_backend._char_to_piece('q') == 0xD0
        assert minimal_backend._char_to_piece('k') == 0xE0


class TestInterface:
    """Test backend interface compliance."""
    
    def test_backend_type_exists(self, minimal_backend):
        """Test that backend has backend_type attribute."""
        assert hasattr(minimal_backend, 'backend_type')
    
    def test_source_sha256_exists(self, minimal_backend):
        """Test that backend has source_sha256 attribute."""
        assert hasattr(minimal_backend, 'source_sha256')
        assert minimal_backend.source_sha256 == "test-sha256"
    
    def test_strategy_revision_exists(self, minimal_backend):
        """Test that backend has strategy_revision attribute."""
        assert hasattr(minimal_backend, 'strategy_revision')
        assert minimal_backend.strategy_revision == "test-v0"
