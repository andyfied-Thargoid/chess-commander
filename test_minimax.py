#!/usr/bin/env python3
import chess

board = chess.Board()
legal_moves = list(board.legal_moves)
print(f"Legal moves type: {type(legal_moves)}")
print(f"First move: {legal_moves[0]}")

# Test sorting
sorted_moves = sorted(legal_moves, key=lambda m: (board.is_capture(m), board.is_en_passant(m)), reverse=True)
print(f"First sorted move: {sorted_moves[0]}")

# Test push
board2 = chess.Board()
move = legal_moves[0]
print(f"About to push move: {move}")
board2.push(move)
print(f"After push: {board2}")
