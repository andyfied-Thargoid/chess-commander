#!/usr/bin/env python3
"""
Test script for 16K Superchess backend.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_commander.backends.superchess import create_superchess_backend


def test_backend():
    """Test the Superchess backend."""
    print("Creating Superchess backend (depth=2)...")
    backend = create_superchess_backend(search_depth=2)
    
    print(f"Backend type: {backend.backend_type}")
    print(f"Search depth: {backend.search_depth}")
    print(f"Strategy revision: {backend.strategy_revision}")
    
    # Test a simple position
    print("\nTesting with starting position...")
    position = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    legal_moves = ["e2e4", "e2e3", "g1f3", "g1h3", "b1c3", "b1a3"]
    
    result = backend.choose_move(
        position=position,
        legal_moves=legal_moves,
        clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
        request_id="test-001"
    )
    
    print(f"Result status: {result.status}")
    print(f"Selected move: {result.move_uci}")
    print(f"Latency: {result.evidence.latency_ms}ms")
    
    if result.status == "ok":
        print("\n✅ Superchess backend working correctly!")
        return True
    else:
        print(f"\n❌ Backend error: {result.evidence.failure_reason}")
        return False


def test_candidates():
    """Test candidate move generation."""
    print("\n--- Testing candidate generation ---")
    backend = create_superchess_backend(search_depth=2)
    
    position = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    candidates = backend.get_candidates(position, n=3)
    
    print(f"Position: {position}")
    print(f"Top 3 candidates: {candidates}")


if __name__ == "__main__":
    success = test_backend()
    test_candidates()
    
    sys.exit(0 if success else 1)
