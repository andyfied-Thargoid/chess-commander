#!/usr/bin/env python3
"""Test Spectrum Chess backends."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_commander.backends.spectrum_chess import (
    create_spectrum_chess_backend,
    create_spectrum_chess2_backend
)

def test_backend(name, backend):
    """Test a backend."""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print('='*60)
    
    print(f"Backend type: {backend.backend_type}")
    if hasattr(backend, 'level'):
        print(f"Level: {backend.level}")
    if hasattr(backend, 'search_depth'):
        print(f"Search depth: {backend.search_depth}")
    
    print("\nTesting with starting position...")
    legal_moves = ["e2e4", "e2e3", "g1f3", "g1h3", "b1c3"]
    
    result = backend.choose_move(
        position="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        legal_moves=legal_moves,
        clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
        request_id=f"test-{name.lower()}-001"
    )
    
    print(f"Result status: {result.status}")
    print(f"Selected move: {result.move_uci}")
    print(f"Latency: {result.evidence.latency_ms}ms")
    
    if result.status == "ok":
        print(f"✅ {name} working!")
        return True
    else:
        print(f"❌ Error: {result.evidence.failure_reason}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("SPECTRUM CHESS BACKEND TESTS")
    print("="*60)
    
    # Test Spectrum Chess I
    backend1 = create_spectrum_chess_backend(level=3)
    test1 = test_backend("Spectrum Chess I (Level 3)", backend1)
    
    # Test Spectrum Chess II
    backend2 = create_spectrum_chess2_backend(level=4)
    test2 = test_backend("Spectrum Chess II (Level 4)", backend2)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Spectrum Chess I: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Spectrum Chess II: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    sys.exit(0 if (test1 and test2) else 1)
