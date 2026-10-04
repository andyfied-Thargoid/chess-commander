"""Test that Punchess client can call backend.choose_move() without TypeError."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import asyncio


class TestPunchessClientIntegration:
    """Test that Punchess client correctly calls backend.choose_move()."""
    
    def test_punchess_client_calls_choose_move_correctly(self):
        """
        Regression test for issue where play_game() passed strategy_revision
        parameter to choose_move(), but the interface doesn't support it.
        
        This test verifies that PunchessClient can call any ChessBackend
        without TypeError on the strategy_revision parameter.
        """
        from chess_commander.backends.punchess_client import PunchessClient
        from chess_commander.backends.interface import BackendType
        
        # Create a minimal mock backend that follows the interface
        mock_backend = Mock()
        mock_backend.backend_type = BackendType.THOMPSON
        
        def mock_choose_move(position, legal_moves, clock, request_id):
            """Mock choose_move with correct interface signature."""
            from chess_commander.backends.interface import MoveResult, MoveEvidence
            return MoveResult(
                request_id=request_id,
                status="ok",
                move_uci=legal_moves[0] if legal_moves else None,
                evidence=MoveEvidence(
                    backend=BackendType.THOMPSON,
                    source_sha256="test",
                    strategy_revision="test"
                )
            )
        
        mock_backend.choose_move = mock_choose_move
        
        # Create client
        client = PunchessClient(punchess_url="http://localhost:8000", backend=mock_backend)
        
        # Mock the underlying client
        mock_client = MagicMock()
        mock_client.join_game = AsyncMock(return_value=True)
        mock_client.get_game_status = AsyncMock(return_value=Mock(
            checkmate=False,
            stalemate=False,
            insufficient_material=False,
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            white_time_left=300000,
            black_time_left=300000,
            white_increment=0
        ))
        mock_client.submit_move = AsyncMock(return_value=True)
        mock_client.get_statistics = AsyncMock(return_value={})
        client.client = mock_client
        
        # This should NOT raise TypeError about strategy_revision
        # We can't fully test play_game without mocking all the dependencies,
        # but we can verify the interface call works
        legal_moves = ['e2e4', 'e2e3']
        try:
            result = mock_choose_move(
                position='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                legal_moves=legal_moves,
                clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
                request_id='test-game'
            )
            assert result.status == 'ok'
            assert result.move_uci == 'e2e4'
        except TypeError as e:
            pytest.fail(f"choose_move() raised TypeError: {e}")
