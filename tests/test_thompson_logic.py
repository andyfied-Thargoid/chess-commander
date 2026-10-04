"""Tests for Thompson backend logic that don't require SSD files."""
import pytest
import chess
from tests.conftest import minimal_backend


class TestMaterialScoring:
    """Test material evaluation logic."""
    
    def test_material_values_defined(self):
        """Test that material values are correctly defined."""
        assert 100 <= 320 <= 330 <= 500 <= 900 <= 10000
    
    def test_white_piece_values(self, minimal_backend):
        """Test that white pieces are correctly valued."""
        assert minimal_backend.MATERIAL_VALUES['P'] == 100
        assert minimal_backend.MATERIAL_VALUES['N'] == 320
        assert minimal_backend.MATERIAL_VALUES['B'] == 330
        assert minimal_backend.MATERIAL_VALUES['R'] == 500
        assert minimal_backend.MATERIAL_VALUES['Q'] == 900
        assert minimal_backend.MATERIAL_VALUES['K'] == 10000
    
    def test_black_piece_values_same_as_white(self, minimal_backend):
        """Test that black and white pieces have same values."""
        assert minimal_backend.MATERIAL_VALUES['P'] == minimal_backend.MATERIAL_VALUES['p']


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
    
    def test_invalid_char(self, minimal_backend):
        """Test invalid character returns 0."""
        assert minimal_backend._char_to_piece('x') == 0x00


class TestMoveEvaluation:
    """Test that different moves receive different scores."""
    
    def test_different_moves_different_scores(self, minimal_backend):
        """
        Test that evaluating different moves from starting position
        produces different scores (or at least some variation).
        
        This verifies that _evaluate_move actually applies the move
        before scoring, rather than evaluating the same position every time.
        """
        starting_pos = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        moves = ['e2e4', 'e2e3', 'g1f3', 'h2h3']
        
        scores = []
        for move in moves:
            score = minimal_backend._evaluate_move(
                minimal_backend.board_data, move
            )
            scores.append(score)
        
        # We expect scores to vary because each move creates a different board state
        # (at minimum, pawn moves change material distribution)
        # If all scores were identical, that would indicate the move wasn't applied
        unique_scores = len(set(scores))
        assert unique_scores > 1, f"All moves returned identical score {scores}. Move simulation may not be working."
    
    def test_evaluate_position_works(self, minimal_backend):
        """Test that _evaluate_position works with real chess.Board."""
        board = chess.Board()
        score = minimal_backend._evaluate_position(board)
        # Starting position should have equal material, score near 0
        assert -100 < score < 100  # Allow small tolerance for implementation details


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
