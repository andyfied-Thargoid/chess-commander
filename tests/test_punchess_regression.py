"""Regression test for PR #3: strategy_revision TypeError fix."""
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_commander.backends.punchess_client import PunchessChessClient


class TestPunchessStrategyRevisionRegression:
    """Test that play_game() no longer passes strategy_revision to backend.choose_move()."""
    
    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend with the correct interface."""
        backend = MagicMock()
        backend.backend_type = MagicMock()
        backend.backend_type.value = "test-backend"
        
        # Mock choose_move to return a valid result
        mock_result = MagicMock()
        mock_result.status = "ok"
        mock_result.move_uci = "e2e4"
        mock_result.evidence = MagicMock()
        mock_result.evidence.selected_move_uci = "e2e4"
        
        backend.choose_move = MagicMock(return_value=mock_result)
        return backend
    
    @pytest.fixture
    def client(self, mock_backend):
        """Create a PunchessChessClient with mocked client."""
        client = PunchessChessClient(
            punchess_url="http://test-server:8000",
            backend=mock_backend
        )
        
        # Mock the inner client
        client.client = MagicMock()
        client.client.join_game = AsyncMock(return_value=True)
        client.client.get_game_report = AsyncMock(return_value=None)
        client.client.submit_move = AsyncMock(return_value=True)
        
        return client
    
    @pytest.mark.asyncio
    async def test_no_strategy_revision_passed(self, client, mock_backend):
        """
        Test that play_game() does not pass strategy_revision to backend.choose_move().
        
        This is a regression test for the issue where play_game() incorrectly passed
        the unsupported strategy_revision parameter, causing a TypeError.
        """
        # Create a status that is NOT terminal (all 5 conditions False)
        # Also include black_increment to test correct increment selection
        play_status = Mock(
            game_id="test-game-123",
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            white_fide_rating=1000,
            black_fide_rating=1000,
            move_number=1,
            last_move=None,
            checkmate=False,
            stalemate=False,
            insufficient_material=False,
            fifty_move_rule=False,  # NEW: Was missing, causing early exit
            threefold_repetition=False,  # NEW: Was missing, causing early exit
            white_time_left=300000,
            black_time_left=300000,
            white_increment=1000,
            black_increment=1000  # NEW: Added to test increment selection
        )
        
        # Mock get_game_status to return non-terminal status, then terminal
        call_count = [0]
        
        def status_side_effect(game_id):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: non-terminal (our turn)
                return play_status
            else:
                # Second call: terminal (game over after our move)
                return Mock(
                    game_id="test-game-123",
                    fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                    white_fide_rating=1000,
                    black_fide_rating=1000,
                    move_number=2,
                    last_move="e2e4",
                    checkmate=True,  # Terminal condition
                    stalemate=False,
                    insufficient_material=False,
                    fifty_move_rule=False,
                    threefold_repetition=False,
                    white_time_left=299000,
                    black_time_left=300000,
                    white_increment=1000,
                    black_increment=1000
                )
        
        client.client.get_game_status = AsyncMock(side_effect=status_side_effect)
        
        # Play the game
        result = await client.play_game("test-game-123")
        
        # Verify backend.choose_move was called (the test would pass vacuously without this)
        assert mock_backend.choose_move.called, "Backend choose_move should have been called"
        
        # Get the received kwargs
        call_args = mock_backend.choose_move.call_args
        received_kwargs = dict(call_args.kwargs) if call_args.kwargs else {}
        
        # Verify strategy_revision is NOT in the kwargs
        assert "strategy_revision" not in received_kwargs, \
            "strategy_revision should NOT be passed to backend.choose_move()"
        
        # Verify the correct parameters WERE passed
        assert "request_id" in received_kwargs, "request_id should be passed"
        assert received_kwargs["request_id"] == "test-game-123", "request_id should be the game_id"
        assert "position" in received_kwargs, "position should be passed"
        assert "legal_moves" in received_kwargs, "legal_moves should be passed"
        assert "clock" in received_kwargs, "clock should be passed"
        
        # Verify clock has the correct increment (white's increment when white to move)
        assert "increment_ms" in received_kwargs["clock"], "increment_ms should be in clock"
        assert received_kwargs["clock"]["increment_ms"] == 1000, \
            "Should use white_increment (1000) when white is to move"
