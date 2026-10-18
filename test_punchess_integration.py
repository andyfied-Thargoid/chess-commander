"""
Integration tests for ZX Spectrum backends with Punchess client.
Tests backend selection, move submission, and evidence tracking.
"""

import sys
import os
import asyncio
import chess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_commander.backends.spectrum_chess import (
    create_spectrum_chess_backend,
    create_spectrum_chess2_backend
)
from chess_commander.backends.superchess import create_superchess_backend
from chess_commander.backends.the_turk import create_turk_backend
from chess_commander.backends.three_d_chess import create_3dchess_backend
from chess_commander.backends.interface import BackendType


def test_backend_selection():
    """Test that all backends have correct BackendType.SPECTRUM."""
    print("Testing backend type selection...")
    
    backends = [
        (create_spectrum_chess_backend(), "Spectrum Chess I"),
        (create_spectrum_chess2_backend(), "Spectrum Chess II"),
        (create_superchess_backend(), "16K Superchess"),
        (create_turk_backend(), "The Turk"),
        (create_3dchess_backend(), "3D Chess"),
    ]
    
    all_pass = True
    for backend, name in backends:
        if backend.backend_type != BackendType.SPECTRUM:
            print(f"  ❌ {name}: wrong backend_type = {backend.backend_type}")
            all_pass = False
        else:
            print(f"  ✅ {name}: backend_type = SPECTRUM")
    
    return all_pass


def test_legal_moves():
    """Test that backends only return legal moves."""
    print("\nTesting legal move validation...")
    
    position = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    board = chess.Board(position)
    legal_moves = [m.uci() for m in board.legal_moves]
    
    backends = [
        (create_spectrum_chess_backend(), "Spectrum Chess"),
        (create_superchess_backend(), "Superchess"),
        (create_turk_backend(), "The Turk"),
        (create_3dchess_backend(), "3D Chess"),
    ]
    
    all_pass = True
    for backend, name in backends:
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id="test-legal"
        )
        
        if result.status != "ok":
            print(f"  ❌ {name}: status error = {result.evidence.failure_reason}")
            all_pass = False
        elif result.move_uci not in legal_moves:
            print(f"  ❌ {name}: returned illegal move = {result.move_uci}")
            all_pass = False
        else:
            print(f"  ✅ {name}: returned legal move = {result.move_uci}")
    
    return all_pass


def test_evidence_tracking():
    """Test that evidence is properly recorded."""
    print("\nTesting evidence tracking...")
    
    position = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    backend = create_spectrum_chess_backend()
    
    result = backend.choose_move(
        position=position,
        legal_moves=["e2e4", "e2e3", "g1f3"],
        clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
        request_id="test-evidence"
    )
    
    if result.status != "ok":
        print(f"  ❌ Error: {result.evidence.failure_reason}")
        return False
    
    evidence = result.evidence
    
    checks = [
        (evidence.backend == BackendType.SPECTRUM, "backend type"),
        (evidence.strategy_revision is not None, "strategy revision"),
        (evidence.selected_move_uci == result.move_uci, "selected move"),
        (evidence.latency_ms is not None, "latency"),
        (evidence.failure_reason is None, "no failure"),
    ]
    
    all_pass = True
    for check, name in checks:
        if not check:
            print(f"  ❌ Evidence missing: {name}")
            all_pass = False
        else:
            print(f"  ✅ Evidence present: {name}")
    
    return all_pass


def test_punchess_integration_stub():
    """Test Punchess client integration (stub - no server required)."""
    print("\nTesting Punchess client integration (stub)...")
    
    try:
        from chess_commander.backends.punchess_client import PunchessChessClient
        
        backends = [
            (create_spectrum_chess_backend(), "Spectrum Chess"),
            (create_superchess_backend(), "Superchess"),
            (create_turk_backend(), "The Turk"),
        ]
        
        all_pass = True
        for backend, name in backends:
            client = PunchessChessClient("http://localhost:8000", backend)
            # Verify client was created with correct backend type
            if client.backend.backend_type == BackendType.SPECTRUM:
                print(f"  ✅ {name}: client created with SPECTRUM backend")
            else:
                print(f"  ❌ {name}: wrong backend type in client")
                all_pass = False
        
        return all_pass
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("="*60)
    print("ZX SPECTRUM BACKENDS - PUNCHESS INTEGRATION TESTS")
    print("="*60)
    
    results = {}
    
    results["Backend Selection"] = test_backend_selection()
    results["Legal Moves"] = test_legal_moves()
    results["Evidence Tracking"] = test_evidence_tracking()
    results["Punchess Client"] = test_punchess_integration_stub()
    
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
        print("✅ ALL INTEGRATION TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
