import chess
import pytest

from chess_commander.backends.acornsoft import (
    AcornsoftChessBackend,
    create_acornsoft_backend,
)
from chess_commander.backends.interface import BackendType

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
CLOCK = {"white_ms": 300000, "black_ms": 300000, "increment_ms": 0}


def test_factory_and_metadata():
    backend = create_acornsoft_backend(skill_level=2)
    assert backend.backend_type is BackendType.ACORNSOFT
    assert backend.source_sha256 == AcornsoftChessBackend.SOURCE_SHA256
    assert backend.search_depth == 2


def test_skill_level_and_depth_are_bounded():
    assert AcornsoftChessBackend(skill_level=0).search_depth == 1
    assert AcornsoftChessBackend(skill_level=5).search_depth == 5
    assert AcornsoftChessBackend(skill_level=9).search_depth == 9
    with pytest.raises(ValueError):
        AcornsoftChessBackend(skill_level=10)
    with pytest.raises(ValueError):
        AcornsoftChessBackend(max_depth=10)


def test_choose_move_respects_supplied_legal_moves():
    backend = AcornsoftChessBackend(skill_level=0)
    result = backend.choose_move(START, ["e2e4"], CLOCK, "acorn-1")
    assert result.status == "ok"
    assert result.move_uci == "e2e4"
    assert result.evidence.selected_move_uci == "e2e4"


def test_choose_move_finds_mate_in_one():
    position = "7k/8/5K2/8/8/8/8/6Q1 w - - 0 1"
    board = chess.Board(position)
    legal = [move.uci() for move in board.legal_moves]
    result = AcornsoftChessBackend(skill_level=1).choose_move(
        position, legal, CLOCK, "mate-1"
    )
    assert result.status == "ok"
    board.push_uci(result.move_uci)
    assert board.is_checkmate()


def test_black_side_captures_hanging_queen():
    position = "4k3/4q3/8/8/8/8/4Q3/4K3 b - - 0 1"
    board = chess.Board(position)
    legal = [move.uci() for move in board.legal_moves]
    result = AcornsoftChessBackend(skill_level=1).choose_move(
        position, legal, CLOCK, "black-capture"
    )
    assert result.status == "ok"
    assert result.move_uci == "e7e2"


def test_search_deadline_returns_legal_fallback():
    backend = AcornsoftChessBackend(
        skill_level=9, max_depth=9, search_time_ms=1, node_budget=1
    )
    board = chess.Board(START)
    legal = [move.uci() for move in board.legal_moves]
    result = backend.choose_move(START, legal, CLOCK, "deadline-1")
    assert result.status == "ok"
    assert result.move_uci in legal
    assert "timed_out=true" in result.evidence.trace_ref


def test_evidence_contains_ranked_search_candidates_and_scores():
    backend = AcornsoftChessBackend(skill_level=1, search_time_ms=1000)
    result = backend.choose_move(START, [move.uci() for move in chess.Board(START).legal_moves], CLOCK, "ranked-1")
    assert result.status == "ok"
    assert result.evidence.candidates_uci
    assert set(result.evidence.candidates_uci) == set(result.evidence.candidate_scores)
    assert result.evidence.candidates_uci[0] == result.move_uci


def test_get_candidates_uses_search_and_is_bounded():
    backend = AcornsoftChessBackend(skill_level=2, search_time_ms=1000)
    candidates = backend.get_candidates(START, n=5)
    assert len(candidates) == 5
    assert len(set(candidates)) == 5
    assert all(backend.validate_move(move, START) for move in candidates)
    assert backend.get_candidates(START, n=0) == []


def test_invalid_position_returns_structured_error():
    result = AcornsoftChessBackend().choose_move("not-fen", ["e2e4"], CLOCK, "bad-1")
    assert result.status == "error"
    assert result.move_uci is None
    assert result.evidence.failure_reason


def test_special_rules_are_legal_candidates():
    backend = AcornsoftChessBackend(skill_level=0)
    cases = [
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1"),
        ("7k/P7/8/8/8/8/8/7K w - - 0 1", "a7a8q"),
        ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6"),
    ]
    for position, expected in cases:
        result = backend.choose_move(position, [expected], CLOCK, expected)
        assert result.status == "ok"
        assert result.move_uci == expected
