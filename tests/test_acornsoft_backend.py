import chess

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


def test_skill_level_is_bounded():
    assert AcornsoftChessBackend(skill_level=0).search_depth == 1
    assert AcornsoftChessBackend(skill_level=5).search_depth == 5
    for bad in (-1, 10):
        try:
            AcornsoftChessBackend(skill_level=bad)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid skill level was accepted")


def test_choose_move_respects_supplied_legal_moves():
    backend = AcornsoftChessBackend(skill_level=0)
    result = backend.choose_move(START, ["e2e4"], CLOCK, "acorn-1")
    assert result.status == "ok"
    assert result.move_uci == "e2e4"
    assert result.evidence.selected_move_uci == "e2e4"


def test_choose_move_handles_tactical_mate():
    # White has the immediate mate Qg7#.
    position = "6k1/6pp/8/8/8/8/5PPP/6KQ w - - 0 1"
    board = chess.Board(position)
    legal = [move.uci() for move in board.legal_moves]
    result = AcornsoftChessBackend(skill_level=1).choose_move(
        position, legal, CLOCK, "mate-1"
    )
    assert result.status == "ok"
    assert result.move_uci in legal


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
