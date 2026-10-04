#!/usr/bin/env python3
"""Build the deterministic Phase 0 chess-position corpus."""

from __future__ import annotations

import json
from pathlib import Path

import chess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "POSITION_CORPUS.json"

POSITIONS = [
    {
        "id": "startpos",
        "fen": chess.STARTING_FEN,
        "tags": ["opening", "baseline"],
        "purpose": "Initial board and full legal move generation.",
    },
    {
        "id": "ruy_lopez_after_a6",
        "fen": "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4",
        "tags": ["opening", "developed"],
        "purpose": "Normal opening position with castling rights preserved.",
    },
    {
        "id": "castling_both_sides",
        "fen": "r3k2r/ppp2ppp/2npbn2/8/8/2NPBN2/PPP2PPP/R3K2R w KQkq - 0 1",
        "tags": ["castling", "tactical"],
        "purpose": "Both sides retain legal kingside and queenside castling rights.",
    },
    {
        "id": "en_passant_white",
        "fen": "r3k2r/ppp2ppp/8/3pP3/8/8/PPP2PPP/R3K2R w KQkq d6 0 2",
        "tags": ["en-passant", "special-move"],
        "purpose": "White has an en-passant capture on d6.",
    },
    {
        "id": "promotion_choice",
        "fen": "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "tags": ["promotion", "endgame"],
        "purpose": "White must choose a promotion piece after advancing the a-pawn.",
    },
    {
        "id": "forced_check_evasion",
        "fen": "4r1k1/8/8/8/8/8/4r3/4K3 w - - 0 1",
        "tags": ["check", "defense"],
        "purpose": "White is in check and every returned move must evade it.",
    },
    {
        "id": "mate_in_one",
        "fen": "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1",
        "tags": ["checkmate", "tactical"],
        "purpose": "White has a mate-in-one candidate.",
    },
    {
        "id": "queen_capture",
        "fen": "4k3/8/8/3q4/3R4/8/8/4K3 w - - 0 1",
        "tags": ["capture", "tactical"],
        "purpose": "White can capture an exposed queen with the rook.",
    },
    {
        "id": "king_pawn_endgame",
        "fen": "8/8/8/8/2k5/8/4K3/8 w - - 0 1",
        "tags": ["endgame", "zugzwang"],
        "purpose": "Sparse position for endgame and evaluation behavior.",
    },
    {
        "id": "fifty_move_boundary",
        "fen": "8/8/8/8/8/8/2N5/K2k4 w - - 100 51",
        "tags": ["draw-rule", "endgame"],
        "purpose": "Halfmove clock is at the fifty-move claim boundary.",
    },
    {
        "id": "black_to_move_tactical",
        "fen": "r1b1k2r/pppp1ppp/2n2n2/4p3/1b2P3/2N2N2/PPPP1PPP/R1BQKB1R b KQkq - 3 5",
        "tags": ["black-to-move", "opening", "tactical"],
        "purpose": "Black-to-move position exercises side-to-move handling.",
    },
    {
        "id": "promotion_with_capture",
        "fen": "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "tags": ["promotion", "capture", "endgame"],
        "purpose": "Promotion position with a black rook available as a tactical target.",
    },
]


def build() -> dict[str, object]:
    fixtures: list[dict[str, object]] = []
    for position in POSITIONS:
        board = chess.Board(position["fen"])
        if not board.is_valid():
            raise ValueError(f"invalid FEN for {position['id']}: {position['fen']}")
        legal_moves = sorted(move.uci() for move in board.legal_moves)
        fixtures.append(
            {
                **position,
                "side_to_move": "white" if board.turn == chess.WHITE else "black",
                "legal_moves_uci": legal_moves,
                "legal_move_count": len(legal_moves),
                "oracle": {
                    "status": "pending",
                    "acornsoft": {"move_uci": None, "candidates_uci": None},
                    "thompson": {"move_uci": None, "candidates_uci": None},
                },
            }
        )

    return {
        "schema": "chess-commander.position-corpus.v1",
        "generator": "tools/build_position_corpus.py",
        "referee": "python-chess",
        "oracle_status": "legal move baseline complete; BBC reference outputs pending Phase 1",
        "fixtures": fixtures,
    }


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(POSITIONS)} fixtures)")
