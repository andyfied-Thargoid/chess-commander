"""Acornsoft Chess V2.1 backend.

Native strategy adapter for the BBC Micro Acornsoft Chess reference program.
The emulator remains the behavioural oracle; this module provides the common
Chess Commander contract without embedding the copyrighted SSD image.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import ClassVar

import chess

from .interface import BackendType, ChessBackend, MoveEvidence, MoveResult


class AcornsoftChessBackend(ChessBackend):
    """A bounded native approximation of Acornsoft Chess V2.1.

    Acornsoft exposes ten skill levels.  Levels 0 and 1 are shallow play;
    levels 2-5 are documented whole-move searches, while levels 6-9 are
    progressively harder settings.  ``max_depth`` is an explicit safety cap
    for service use and can be raised for offline qualification.
    """

    backend_type = BackendType.ACORNSOFT
    SOURCE_SHA256 = "72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b"
    SOURCE_FILE = "Acornsoft_Chess_V2.1.ssd"

    PIECE_VALUES: ClassVar[dict[int, int]] = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 10_000,
    }
    CENTER: ClassVar[set[int]] = {chess.D4, chess.E4, chess.D5, chess.E5}

    def __init__(
        self,
        source_path: str | None = None,
        skill_level: int = 2,
        max_depth: int | None = None,
        strategy_revision: str = "acornsoft-v1",
    ) -> None:
        super().__init__(self.SOURCE_SHA256, strategy_revision, source_path)
        if not 0 <= skill_level <= 9:
            raise ValueError("skill_level must be between 0 and 9")
        self.skill_level = skill_level
        documented_depth = 1 if skill_level <= 1 else min(skill_level, 5)
        self.search_depth = max(
            1, max_depth if max_depth is not None else documented_depth
        )

    def choose_move(
        self,
        position: str,
        legal_moves: list[str],
        clock: dict,
        request_id: str,
    ) -> MoveResult:
        started = time.monotonic()
        try:
            board = chess.Board(position)
            allowed = self._allowed_moves(board, legal_moves)
            if not allowed:
                raise ValueError("no legal moves supplied for the position")
            best_move, _ = self._search_root(board, allowed, self.search_depth)
            if best_move is None:
                raise ValueError("search produced no move")
            selected = best_move.uci()
            return MoveResult(
                request_id=request_id,
                status="ok",
                move_uci=selected,
                evidence=MoveEvidence(
                    backend=self.backend_type,
                    source_sha256=self.source_sha256,
                    strategy_revision=self.strategy_revision,
                    selected_move_uci=selected,
                    candidates_uci=[move.uci() for move in allowed[:10]],
                    latency_ms=int((time.monotonic() - started) * 1000),
                ),
            )
        except ValueError as exc:
            return MoveResult(
                request_id=request_id,
                status="error",
                evidence=MoveEvidence(
                    backend=self.backend_type,
                    source_sha256=self.source_sha256,
                    strategy_revision=self.strategy_revision,
                    failure_reason=f"Move selection failed: {exc}",
                ),
            )

    @staticmethod
    def _allowed_moves(
        board: chess.Board, legal_moves: Iterable[str]
    ) -> list[chess.Move]:
        legal = {move.uci(): move for move in board.legal_moves}
        return [legal[uci] for uci in legal_moves if uci in legal]

    def _search_root(
        self, board: chess.Board, moves: list[chess.Move], depth: int
    ) -> tuple[chess.Move | None, float]:
        maximizing = board.turn == chess.WHITE
        best_move: chess.Move | None = None
        best_score = float("-inf") if maximizing else float("inf")
        ordered = self._order_moves(board, moves)
        for move in ordered:
            board.push(move)
            score = self._minimax(board, depth - 1, float("-inf"), float("inf"))
            board.pop()
            if (maximizing and score > best_score) or (
                not maximizing and score < best_score
            ):
                best_move, best_score = move, score
        return best_move, best_score

    def _minimax(
        self, board: chess.Board, depth: int, alpha: float, beta: float
    ) -> float:
        if board.is_checkmate():
            return -100_000.0 if board.turn == chess.WHITE else 100_000.0
        if (
            board.is_stalemate()
            or board.is_insufficient_material()
            or board.is_fifty_moves()
        ):
            return 0.0
        if depth <= 0:
            return self._evaluate(board)

        maximizing = board.turn == chess.WHITE
        moves = self._order_moves(board, list(board.legal_moves))
        if maximizing:
            value = float("-inf")
            for move in moves:
                board.push(move)
                value = max(value, self._minimax(board, depth - 1, alpha, beta))
                board.pop()
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return value
        value = float("inf")
        for move in moves:
            board.push(move)
            value = min(value, self._minimax(board, depth - 1, alpha, beta))
            board.pop()
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value

    @staticmethod
    def _order_moves(board: chess.Board, moves: list[chess.Move]) -> list[chess.Move]:
        return sorted(
            moves,
            key=lambda move: (
                board.is_capture(move),
                board.gives_check(move),
                board.is_castling(move),
            ),
            reverse=True,
        )

    def _evaluate(self, board: chess.Board) -> float:
        score = 0.0
        for square, piece in board.piece_map().items():
            value = self.PIECE_VALUES[piece.piece_type]
            positional = 20 if square in self.CENTER else 0
            signed = value + positional
            score += signed if piece.color == chess.WHITE else -signed
        mobility = len(list(board.legal_moves)) * 0.5
        return score + mobility if board.turn == chess.WHITE else score - mobility

    def get_candidates(self, position: str, n: int = 3) -> list[str]:
        board = chess.Board(position)
        moves = list(board.legal_moves)
        scored = []
        for move in moves:
            board.push(move)
            scored.append((self._evaluate(board), move.uci()))
            board.pop()
        scored.sort(reverse=board.turn == chess.WHITE)
        return [move for _, move in scored[:n]]


def create_acornsoft_backend(
    source_path: str | None = None,
    skill_level: int = 2,
    max_depth: int | None = None,
    strategy_revision: str = "acornsoft-v1",
) -> AcornsoftChessBackend:
    """Create an Acornsoft Chess backend."""
    return AcornsoftChessBackend(source_path, skill_level, max_depth, strategy_revision)
