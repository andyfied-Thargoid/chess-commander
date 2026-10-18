#!/usr/bin/env python3
import traceback
import chess
from chess_commander.backends.superchess import SuperchessBackend

backend = SuperchessBackend(search_depth=2)
board = chess.Board()
legal_moves = list(board.legal_moves)

print(f"legal_moves type: {type(legal_moves)}")
print(f"First move: {legal_moves[0]}")

# Try the sorting step
try:
    sorted_moves = sorted(legal_moves, key=lambda m: (board.is_capture(m), board.is_en_passant(m)), reverse=True)
    print(f"Sorted first: {sorted_moves[0]}")
except Exception as e:
    print(f"Sort error: {e}")
    traceback.print_exc()
