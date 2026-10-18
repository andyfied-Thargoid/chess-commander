#!/usr/bin/env python3
import traceback
from chess_commander.backends.superchess import create_superchess_backend

backend = create_superchess_backend(search_depth=2)
try:
    result = backend.choose_move(
        position='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        legal_moves=['e2e4', 'e2e3', 'g1f3'],
        clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
        request_id='test-001'
    )
    print(f'Result status: {result.status}')
    print(f'Move: {result.move_uci}')
    print(f'Evidence: {result.evidence}')
    print(f'Failure reason: {result.evidence.failure_reason}')
except Exception as e:
    print(f'Exception: {e}')
    traceback.print_exc()
