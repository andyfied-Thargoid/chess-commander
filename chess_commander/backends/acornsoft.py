"""Acornsoft Chess V2.1 backend.

This is a bounded native approximation of the BBC Micro program. The original
SSD remains an external behavioural oracle: ``source_path`` is provenance
metadata only and is deliberately not opened by this adapter.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar

import chess

from .interface import BackendType, ChessBackend, MoveEvidence, MoveResult


class _SearchTimeout(Exception):
    """Internal signal used to stop an incomplete iterative-deepening pass."""


@dataclass
class _SearchState:
    deadline: float
    node_budget: int
    nodes: int = 0

    def visit(self) -> None:
        self.nodes += 1
        if self.nodes > self.node_budget or time.monotonic() >= self.deadline:
            raise _SearchTimeout


class AcornsoftChessBackend(ChessBackend):
    """Bounded native approximation of Acornsoft Chess V2.1.

    Acornsoft exposes ten skill levels. Levels 0 and 1 are shallow play;
    levels 2-5 are documented whole-move searches, while levels 6-9 are
    progressively harder settings. Exact historical move fidelity is not
    claimed until emulator comparison is complete.
    """

    backend_type = BackendType.ACORNSOFT
    SOURCE_SHA256 = "72d14af1fced97aca88e6532fac54b213b7b81b819a5a8a435be39837afb037b"
    SOURCE_FILE = "Acornsoft_Chess_V2.1.ssd"
    MAX_SEARCH_DEPTH = 9

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
        search_time_ms: int = 1_000,
        node_budget: int = 100_000,
        strategy_revision: str = "acornsoft-approx-v2",
    ) -> None:
        super().__init__(self.SOURCE_SHA256, strategy_revision, source_path)
        if not 0 <= skill_level <= 9:
            raise ValueError("skill_level must be between 0 and 9")
        if max_depth is not None and not 1 <= max_depth <= self.MAX_SEARCH_DEPTH:
            raise ValueError(f"max_depth must be between 1 and {self.MAX_SEARCH_DEPTH}")
        if search_time_ms <= 0:
            raise ValueError("search_time_ms must be positive")
        if node_budget <= 0:
            raise ValueError("node_budget must be positive")
        self.skill_level = skill_level
        documented_depth = max(1, skill_level)
        self.search_depth = max_depth if max_depth is not None else documented_depth
        self.search_time_ms = search_time_ms
        self.node_budget = node_budget

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
            budget_ms = self._effective_budget_ms(board, clock)
            best_move, ranked, completed_depth, timed_out, nodes = self._run_search(
                board, allowed, budget_ms
            )
            selected = best_move.uci()
            scores = {move.uci(): score for move, score in ranked[:10]}
            trace = (
                f"depth={completed_depth};nodes={nodes};budget_ms={budget_ms};"
                f"timed_out={str(timed_out).lower()}"
            )
            return MoveResult(
                request_id=request_id,
                status="ok",
                move_uci=selected,
                evidence=MoveEvidence(
                    backend=self.backend_type,
                    source_sha256=self.source_sha256,
                    strategy_revision=self.strategy_revision,
                    selected_move_uci=selected,
                    candidates_uci=[move.uci() for move, _ in ranked[:10]],
                    candidate_scores=scores,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    trace_ref=trace,
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

    def _effective_budget_ms(self, board: chess.Board, clock: dict) -> int:
        remaining = clock.get("white_ms" if board.turn == chess.WHITE else "black_ms")
        if isinstance(remaining, (int, float)) and remaining > 0:
            return min(self.search_time_ms, max(1, int(remaining // 20)))
        return self.search_time_ms

    def _run_search(
        self, board: chess.Board, moves: list[chess.Move], budget_ms: int
    ) -> tuple[chess.Move, list[tuple[chess.Move, float]], int, bool, int]:
        if not moves:
            raise ValueError("no legal moves available for search")
        state = _SearchState(
            deadline=time.monotonic() + budget_ms / 1000,
            node_budget=self.node_budget,
        )
        best_move = self._order_moves(board, moves)[0]
        ranked = [(best_move, 0.0)]
        completed_depth = 0
        timed_out = False
        for depth in range(1, self.search_depth + 1):
            try:
                candidate, scores = self._search_root(board, moves, depth, state)
            except _SearchTimeout:
                timed_out = True
                break
            best_move, ranked = candidate, scores
            completed_depth = depth
        return best_move, ranked, completed_depth, timed_out, state.nodes

    @staticmethod
    def _allowed_moves(
        board: chess.Board, legal_moves: Iterable[str]
    ) -> list[chess.Move]:
        legal = {move.uci(): move for move in board.legal_moves}
        return [legal[uci] for uci in legal_moves if uci in legal]

    def _search_root(
        self,
        board: chess.Board,
        moves: list[chess.Move],
        depth: int,
        state: _SearchState,
    ) -> tuple[chess.Move, list[tuple[chess.Move, float]]]:
        maximizing = board.turn == chess.WHITE
        scores: list[tuple[chess.Move, float]] = []
        for move in self._order_moves(board, moves):
            state.visit()
            board.push(move)
            try:
                score = self._minimax(
                    board, depth - 1, float("-inf"), float("inf"), state
                )
            finally:
                board.pop()
            scores.append((move, score))
        scores.sort(key=lambda item: item[1], reverse=maximizing)
        return scores[0][0], scores

    def _minimax(
        self,
        board: chess.Board,
        depth: int,
        alpha: float,
        beta: float,
        state: _SearchState,
    ) -> float:
        state.visit()
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
                try:
                    value = max(
                        value, self._minimax(board, depth - 1, alpha, beta, state)
                    )
                finally:
                    board.pop()
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return value
        value = float("inf")
        for move in moves:
            board.push(move)
            try:
                value = min(
                    value, self._minimax(board, depth - 1, alpha, beta, state)
                )
            finally:
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
        if n <= 0:
            return []
        board = chess.Board(position)
        moves = list(board.legal_moves)
        if not moves:
            return []
        _, ranked, _, _, _ = self._run_search(board, moves, self.search_time_ms)
        return [move.uci() for move, _ in ranked[:n]]


def create_acornsoft_backend(
    source_path: str | None = None,
    skill_level: int = 2,
    max_depth: int | None = None,
    search_time_ms: int = 1_000,
    node_budget: int = 100_000,
    strategy_revision: str = "acornsoft-approx-v2",
) -> AcornsoftChessBackend:
    """Create a bounded Acornsoft Chess approximation backend."""
    return AcornsoftChessBackend(
        source_path,
        skill_level,
        max_depth,
        search_time_ms,
        node_budget,
        strategy_revision,
    )
