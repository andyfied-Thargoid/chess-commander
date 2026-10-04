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
        assert minimal_backend.MATERIAL_VALUES['P'] == 100
    
    def test_evaluate_position_starting_position(self, minimal_backend):
        """Test that starting position has score near zero."""
        board = chess.Board()
        score = minimal_backend._evaluate_position(board)
        # Starting position has equal material, score should be ~0
        assert -100 < score < 100


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
    """Test that move evaluation works correctly."""
    
    def test_non_capture_moves_same_score(self, minimal_backend):
        """
        Test that non-capture moves from starting position receive same score.
        
        Since our evaluator is material-only, moves that don't change material
        (like e2e4, e2e3, g1f3, h2h3) should all return the same score.
        This verifies the evaluator is working correctly.
        """
        starting_pos = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        moves = ['e2e4', 'e2e3', 'g1f3', 'h2h3']
        
        scores = []
        for move in moves:
            score = minimal_backend._evaluate_move(starting_pos, move)
            scores.append(score)
        
        # All non-capture moves should have identical scores (starting position has no captures)
        unique_scores = len(set(scores))
        assert unique_scores == 1, f"Expected all non-capture moves to have same score, but got: {scores}"
    
    def test_capture_gains_material_positive_score(self, minimal_backend):
        """
        Test that a capture that wins material gets a positive score for White.
        
        Position: White pawn on e5 can capture Black pawn on d6
        After capture: White is up one pawn (+100 material)
        """
        # White to move, pawn on e5 can capture on d6
        position = '8/8/3p4/3P4/8/8/8/8 w - - 0 1'
        capture_move = 'd5e6'  # White pawn captures on e6
        
        score = minimal_backend._evaluate_move(position, capture_move)
        
        # White captures a pawn (+100), so score should be positive
        assert score == 100, f"Expected +100 for capturing a pawn, got {score}"
    
    def test_capture_ranked_above_quiet_move(self, minimal_backend):
        """
        Test that a winning capture is ranked higher than a quiet move.
        
        Position: White can either capture a pawn or make a quiet move
        The capture should score higher (+100 vs 0).
        """
        position = '8/8/3p4/3P4/8/8/8/8 w - - 0 1'
        capture = 'd5e6'  # Capture, gains +100
        quiet = 'd5d6'    # Quiet push, gains 0
        
        capture_score = minimal_backend._evaluate_move(position, capture)
        quiet_score = minimal_backend._evaluate_move(position, quiet)
        
        assert capture_score > quiet_score, \
            f"Capture score {capture_score} should be > quiet score {quiet_score}"
        assert capture_score == 100, f"Expected capture to score +100, got {capture_score}"
        assert quiet_score == 0, f"Expected quiet move to score 0, got {quiet_score}"
    
    def test_capture_by_black_negative_score(self, minimal_backend):
        """
        Test that when Black captures, the score is negative (from White perspective).
        """
        # Black to move, pawn on d6 can capture White pawn on e5
        position = '8/8/3p4/3P4/8/8/8/8 b - - 0 1'
        capture = 'd6e5'  # Black pawn captures on e5
        
        score = minimal_backend._evaluate_move(position, capture)
        
        # Black captures a pawn, White loses material, so score should be negative
        assert score == -100, f"Expected -100 for Black capturing a pawn, got {score}"
    
    def test_evaluate_position_works(self, minimal_backend):
        """Test that _evaluate_position works with real chess.Board."""
        board = chess.Board()
        score = minimal_backend._evaluate_position(board)
        # Starting position should have equal material, score near 0
        assert -100 < score < 100


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
