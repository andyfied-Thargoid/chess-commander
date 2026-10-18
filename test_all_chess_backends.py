#!/usr/bin/env python3
"""
Test script for all ZX Spectrum chess backends.
Tests Superchess, 3D Chess, and The Turk backends.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_commander.backends.superchess import create_superchess_backend
from chess_commander.backends.three_d_chess import create_3dchess_backend
from chess_commander.backends.the_turk import create_turk_backend


def test_backend(name, backend, position="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"):
    """Test a chess backend."""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print('='*60)
    
    print(f"Backend type: {backend.backend_type}")
    
    # Test a simple position
    print(f"\nTesting with starting position...")
    legal_moves = ["e2e4", "e2e3", "g1f3", "g1h3", "b1c3", "b1a3"]
    
    try:
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id=f"test-{name.lower()}-001"
        )
        
        print(f"Result status: {result.status}")
        print(f"Selected move: {result.move_uci}")
        print(f"Latency: {result.evidence.latency_ms}ms")
        
        if result.status == "ok":
            print(f"✅ {name} backend working correctly!")
            return True
        else:
            print(f"❌ Backend error: {result.evidence.failure_reason}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_candidates(name, backend):
    """Test candidate move generation."""
    print(f"\n--- Testing candidate generation for {name} ---")
    
    # Test position
    position = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    candidates = backend.get_candidates(position, n=3)
    
    print(f"Position: {position}")
    print(f"Top 3 candidates: {candidates}")


def main():
    """Run all tests."""
    print("="*60)
    print("ZX SPECTRUM CHESS BACKENDS TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 16K Superchess
    backend1 = create_superchess_backend(search_depth=2)
    results["Superchess"] = test_backend("16K Superchess (Chris Whittington, 1983)", backend1)
    test_candidates("Superchess", backend1)
    
    # Test 3D Chess
    backend2 = create_3dchess_backend(difficulty=5)
    results["3D Chess"] = test_backend("3D Chess (Bill Bennett, 1983)", backend2)
    test_candidates("3D Chess", backend2)
    
    # Test The Turk
    backend3 = create_turk_backend(search_depth=3, timeout_ms=60000)
    results["The Turk"] = test_backend("The Turk v1.3 (James Hutchby, 1982)", backend3)
    test_candidates("The Turk", backend3)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    if all_passed:
        print("✅ ALL BACKENDS WORKING CORRECTLY!")
        print("="*60)
        return 0
    else:
        print("❌ SOME BACKENDS FAILED")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
