#!/usr/bin/env python3
import chess

board = chess.Board()
print(f"Board: {board}")
print(f"Legal moves type: {type(board.legal_moves)}")
print(f"Legal moves: {list(board.legal_moves)}")

# Test iteration
for move in board.legal_moves:
    print(f"Move: {move}, UCI: {move.uci()}")
    break
