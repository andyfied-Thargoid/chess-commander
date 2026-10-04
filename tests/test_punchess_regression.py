"""Regression test for Punchess client strategy_revision TypeError."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock


class TestPunchessClientRegression:
    """Test that Punchess client no longer passes strategy_revision to backend."""
    
    def test_play_game_does_not_pass_strategy_revision(self):
        """
        Regression test for TypeError in play_game().
        
        Before fix: PunchessChessClient.play_game() called backend.choose_move()
        with strategy_revision= parameter, causing TypeError because the base
        ChessBackend interface only defines:
            choose_move(position, legal_moves, clock, request_id)
        
        After fix: strategy_revision parameter removed from the call.
        """
        from chess_commander.backends.punchess_client import PunchessChessClient
        from chess_commander.backends.interface import BackendType, MoveResult, MoveEvidence
        
        # Create a mock backend that follows the CORRECT interface signature
        mock_backend = Mock()
        mock_backend.backend_type = BackendType.THOMPSON
        
        # Track if strategy_revision was passed (it should NOT be)
        received_kwargs = {}
        
        def choose_move(position, legal_moves, clock, request_id):
            """Mock choose_move with correct interface signature."""
            nonlocal received_kwargs
            received_kwargs = {
                'position': position,
                'legal_moves': legal_moves,
                'clock': clock,
                'request_id': request_id
            }
            return MoveResult(
                request_id=request_id,
                status="ok",
                move_uci='e2e4',
                evidence=MoveEvidence(
                    backend=BackendType.THOMPSON,
                    source_sha256="test",
                    strategy_revision="test"
                )
            )
        
        mock_backend.choose_move = choose_move
        
        # Create PunchessChessClient (the HIGH-LEVEL client, not low-level PunchessClient)
        client = PunchessChessClient(punchess_url="http://localhost:8000", backend=mock_backend)
        
        # Mock the underlying HTTP client
        mock_join = AsyncMock(return_value=True)
        
        # First call returns playing status, second call returns checkmate
        play_status = Mock(
            checkmate=False,
            stalemate=False,
            insufficient_material=False,
            fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            white_time_left=300000,
            black_time_left=300000,
            white_increment=0
        )
        
        checkmate_status = Mock(
            checkmate=True,
            stalemate=False,
            insufficient_material=False,
            fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1',
            white_time_left=300000,
            black_time_left=300000,
            white_increment=0
        )
        
        call_count = [0]
        def get_game_status_side_effect(game_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return play_status
            else:
                return checkmate_status
        
        mock_get_status = AsyncMock(side_effect=get_game_status_side_effect)
        mock_submit = AsyncMock(return_value=True)
        
        client.client = MagicMock()
        client.client.join_game = mock_join
        client.client.get_game_status = mock_get_status
        client.client.submit_move = mock_submit
        
        # Call play_game - this is what was failing before
        async def run_test():
            result = await client.play_game("test-game-123")
            return result
        
        # This should NOT raise TypeError about unexpected keyword argument
        try:
            asyncio.run(run_test())
        except TypeError as e:
            if "strategy_revision" in str(e):
                pytest.fail(f"play_game() still passes strategy_revision to backend: {e}")
            raise
        
        # Verify that choose_move was called WITHOUT strategy_revision
        assert 'strategy_revision' not in received_kwargs, \
            "Backend choose_move() should not receive strategy_revision parameter"
