"""
Punchess Client for Chess Commander.
Integrates chess backends with Punchess game server.
"""

import json
import aiohttp
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from .interface import BackendType, MoveResult


@dataclass
class GameStatus:
    """Status of a Punchess game."""
    game_id: str
    fen: str
    white_fide_rating: int
    black_fide_rating: int
    move_number: int
    last_move: str
    checkmate: bool
    stalemate: bool
    insufficient_material: bool
    fifty_move_rule: bool
    threefold_repetition: bool
    white_time_left: Optional[int] = None
    black_time_left: Optional[int] = None
    white_increment: Optional[int] = None
    black_increment: Optional[int] = None


@dataclass
class GameReport:
    """Game report from Punchess."""
    game_id: str
    white_fide_rating: int
    black_fide_rating: int
    fen: str
    pgns: list
    moves: list
    evaluation: Optional[Dict[str, Any]] = None
    time_analysis: Optional[Dict[str, Any]] = None
    backend: str = None


class PunchessClient:
    """Client for interacting with Punchess game server."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize Punchess client.
        
        Args:
            base_url: Base URL of Punchess server
        """
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def join_game(self, game_id: str, backend: str) -> bool:
        """
        Join a Punchess game.
        
        Args:
            game_id: Game identifier
            backend: Backend type ("acornsoft", "thompson", etc.)
            
        Returns:
            True if joined successfully
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/join"
            data = {
                "game_id": game_id,
                "backend": backend
            }
            
            try:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    return result.get("success", False)
            except aiohttp.ClientError as e:
                print(f"Failed to join game {game_id}: {e}")
                return False
    
    async def get_game_status(self, game_id: str) -> Optional[GameStatus]:
        """
        Get current game status.
        
        Args:
            game_id: Game identifier
            
        Returns:
            GameStatus or None if not found
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/status/{game_id}"
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    return GameStatus(
                        game_id=data["game_id"],
                        fen=data["fen"],
                        white_fide_rating=data["white_fide_rating"],
                        black_fide_rating=data["black_fide_rating"],
                        move_number=data["move_number"],
                        last_move=data.get("last_move"),
                        checkmate=data.get("checkmate", False),
                        stalemate=data.get("stalemate", False),
                        insufficient_material=data.get("insufficient_material", False),
                        fifty_move_rule=data.get("fifty_move_rule", False),
                        threefold_repetition=data.get("threefold_repetition", False),
                        white_time_left=data.get("white_time_left"),
                        black_time_left=data.get("black_time_left"),
                        white_increment=data.get("white_increment"),
                        black_increment=data.get("black_increment")
                    )
            except aiohttp.ClientError as e:
                print(f"Failed to get status for game {game_id}: {e}")
                return None
    
    async def submit_move(self, game_id: str, move_uci: str) -> bool:
        """
        Submit a move to the game.
        
        Args:
            game_id: Game identifier
            move_uci: Move in UCI format (e.g., "e2e4")
            
        Returns:
            True if move submitted successfully
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/move"
            data = {
                "game_id": game_id,
                "move_uci": move_uci
            }
            
            try:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    return result.get("success", False)
            except aiohttp.ClientError as e:
                print(f"Failed to submit move {move_uci} for game {game_id}: {e}")
                return False
    
    async def get_game_report(self, game_id: str) -> Optional[GameReport]:
        """
        Get game report after game ends.
        
        Args:
            game_id: Game identifier
            
        Returns:
            GameReport or None if not found
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/report/{game_id}"
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    return GameReport(
                        game_id=data["game_id"],
                        white_fide_rating=data["white_fide_rating"],
                        black_fide_rating=data["black_fide_rating"],
                        fen=data["fen"],
                        pgns=data.get("pgns", []),
                        moves=data.get("moves", []),
                        evaluation=data.get("evaluation"),
                        time_analysis=data.get("time_analysis"),
                        backend=data.get("backend")
                    )
            except aiohttp.ClientError as e:
                print(f"Failed to get report for game {game_id}: {e}")
                return None
    
    async def list_available_games(self) -> list:
        """
        List all available games in the lobby.
        
        Returns:
            List of game IDs
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/games"
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    return data.get("game_ids", [])
            except aiohttp.ClientError as e:
                print(f"Failed to list games: {e}")
                return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get server statistics.
        
        Returns:
            Server statistics dict
        """
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/stats"
            
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {}
                    
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Failed to get statistics: {e}")
                return {}


class PunchessChessClient:
    """High-level client for playing chess on Punchess using a backend."""
    
    def __init__(
        self,
        punchess_url: str,
        backend
    ):
        """
        Initialize Punchess chess client.
        
        Args:
            punchess_url: Base URL of Punchess server
            backend: ChessBackend instance
        """
        self.punchess_url = punchess_url
        self.backend = backend
        self.client = PunchessClient(punchess_url)
    
    async def play_game(self, game_id: str) -> Optional[str]:
        """
        Play a game on Punchess.
        
        Args:
            game_id: Game identifier
            
        Returns:
            The last move UCI if the game completed, None otherwise (failure, early termination)
        """
        # Join the game
        joined = await self.client.join_game(
            game_id,
            self.backend.backend_type.value
        )
        
        if not joined:
            return None
        
        # Initialize move_uci before the loop to avoid UnboundLocalError
        move_uci: Optional[str] = None
        
        while True:
            # Get game status
            status = await self.client.get_game_status(game_id)
            
            if status is None:
                print(f"Failed to get status for game {game_id}")
                break
            
            # Check if game is over (all 5 terminal conditions)
            if status.checkmate or status.stalemate or status.insufficient_material or status.fifty_move_rule or status.threefold_repetition:
                report = await self.client.get_game_report(game_id)
                print(f"Game {game_id} ended: {self._get_result_string(report)}")
                break
            
            # Get current position
            position = status.fen
            
            # Get legal moves
            import chess
            board = chess.Board(position)
            legal_moves = [move.uci() for move in board.legal_moves]
            
            if not legal_moves:
                print(f"No legal moves in game {game_id}")
                break
            
            # Choose move using backend
            print(f"Game {game_id}: Position {position}")
            print(f"Legal moves: {legal_moves[:5]}...")
            
            # Fix: Use correct increment for the side to move
            increment_ms = status.white_increment if board.turn == chess.WHITE else status.black_increment
            
            move_result = self.backend.choose_move(
                request_id=game_id,
                position=position,
                legal_moves=legal_moves,
                clock={
                    "white_ms": status.white_time_left or 300000,
                    "black_ms": status.black_time_left or 300000,
                    "increment_ms": increment_ms
                }
            )
            
            if move_result.status != "ok":
                print(f"Backend error: {move_result.evidence.failure_reason}")
                break
            
            move_uci = move_result.move_uci
            print(f"Choosing: {move_uci}")
            
            # Submit move
            success = await self.client.submit_move(game_id, move_uci)
            
            if not success:
                print(f"Failed to submit move {move_uci}")
                break
            
            # Check if we won
            if move_result.evidence.selected_move_uci == move_uci:
                # This is a simplified check - in reality we'd need to check
                # if the opponent has no legal moves after our move
                pass
        
        return move_uci
    
    def _get_result_string(self, report: GameReport) -> str:
        """Get human-readable game result string."""
        if not report:
            return "Unknown"
        
        if report.backend == "thompson":
            return "Thompson won"
        elif report.backend == "acornsoft":
            return "Acornsoft won"
        else:
            return f"{report.backend} won"
    
    async def join_lobby(self) -> list:
        """
        Join the Punchess lobby and return list of available games.
        
        Returns:
            List of available game IDs
        """
        return await self.client.list_available_games()
    
    async def get_game_report(self, game_id: str) -> Optional[GameReport]:
        """
        Get game report.
        
        Args:
            game_id: Game identifier
            
        Returns:
            GameReport or None
        """
        return await self.client.get_game_report(game_id)


# Factory function
def create_punchess_client(
    punchess_url: str,
    backend
) -> PunchessChessClient:
    """Create a Punchess chess client."""
    return PunchessChessClient(
        punchess_url=punchess_url,
        backend=backend
    )
