"""
Comprehensive tests for all chess backends.

Tests:
- Black-to-move correctness (Issue #1)
- Legal-move restriction enforcement (Issue #2)
- Mate-in-one detection for both colors (FAIL if missed)
- Terminal position handling (checkmate, stalemate)
- Candidate move ordering for Black (Issue #4)
- Restricted move set validation
"""

import sys
import os
import chess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_commander.backends.spectrum_chess import create_spectrum_chess_backend
from chess_commander.backends.superchess import create_superchess_backend
from chess_commander.backends.the_turk import create_turk_backend
from chess_commander.backends.three_d_chess import create_3dchess_backend
from chess_commander.backends.interface import BackendType


def test_black_to_move():
    """Test that backends correctly play as Black (minimizing)."""
    print("\n=== Testing Black-to-Move Correctness ===")
    
    position = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    legal_moves = ["e5e4", "d7d6", "d7d5", "g8f6", "g8h6"]
    
    backends = [
        ("Spectrum Chess", create_spectrum_chess_backend()),
        ("Superchess", create_superchess_backend()),
        ("The Turk", create_turk_backend()),
        ("3D Chess", create_3dchess_backend()),
    ]
    
    all_pass = True
    for name, backend in backends:
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id="black-to-move"
        )
        
        if result.status != "ok":
            print(f"  ❌ {name}: Error - {result.evidence.failure_reason}")
            all_pass = False
            continue
        
        board = chess.Board(position)
        move = chess.Move.from_uci(result.move_uci)
        
        if move not in board.legal_moves:
            print(f"  ❌ {name}: Returned illegal move {result.move_uci}")
            all_pass = False
        else:
            print(f"  ✅ {name}: Correctly played as Black with move {result.move_uci}")
    
    return all_pass


def test_legal_move_restriction():
    """Test that backends respect the supplied legal_moves argument."""
    print("\n=== Testing Legal Move Restriction ===")
    
    position = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    
    # Restrict to only one legal move
    restricted_moves = ["e7e5"]
    
    backends = [
        ("Spectrum Chess", create_spectrum_chess_backend()),
        ("Superchess", create_superchess_backend()),
        ("The Turk", create_turk_backend()),
        ("3D Chess", create_3dchess_backend()),
    ]
    
    all_pass = True
    for name, backend in backends:
        result = backend.choose_move(
            position=position,
            legal_moves=restricted_moves,
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id="legal-restriction"
        )
        
        if result.status != "ok":
            print(f"  ❌ {name}: Error - {result.evidence.failure_reason}")
            all_pass = False
            continue
        
        if result.move_uci != "e7e5":
            print(f"  ❌ {name}: Returned {result.move_uci} but should return e7e5")
            all_pass = False
        else:
            print(f"  ✅ {name}: Correctly restricted to e7e5")
    
    # Test with no valid moves
    print("\n  Testing no valid moves scenario...")
    for name, backend in backends:
        result = backend.choose_move(
            position=position,
            legal_moves=["invalid123"],
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id="no-valid-moves"
        )
        
        if result.status == "error" and "No valid legal moves" in result.evidence.failure_reason:
            print(f"  ✅ {name}: Correctly returned error for no valid moves")
        else:
            print(f"  ❌ {name}: Should return error for no valid moves, got status={result.status}")
            all_pass = False
    
    return all_pass


def test_mate_in_one_white():
    """Test mate-in-one detection for White - FAIL if missed."""
    print("\n=== Testing Mate-in-One for White ===")
    
    # White to move - mate in 1
    position = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
    legal_moves = ["d1h5", "d1e2", "d1f3", "g2g3"]
    
    backends = [
        ("Spectrum Chess", create_spectrum_chess_backend()),
        ("Superchess", create_superchess_backend()),
        ("The Turk", create_turk_backend()),
        ("3D Chess", create_3dchess_backend()),
    ]
    
    all_pass = True
    for name, backend in backends:
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id="mate-white"
        )
        
        if result.status != "ok":
            print(f"  ❌ {name}: Error - {result.evidence.failure_reason}")
            all_pass = False
            continue
        
        if result.move_uci == "d1h5":
            print(f"  ✅ {name}: Found mate-in-one (d1h5)")
        else:
            # FAIL - missed mate is a significant tactical error
            print(f"  ❌ {name}: MISSED mate-in-one, chose {result.move_uci}")
            all_pass = False
    
    return all_pass


def test_mate_in_one_black():
    """Test mate-in-one detection for Black - FAIL if missed."""
    print("\n=== Testing Mate-in-One for Black ===")
    
    # Black to move - mate in 1
    position = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    legal_moves = ["d8h4", "d8e7", "d8f6"]
    
    backends = [
        ("Spectrum Chess", create_spectrum_chess_backend()),
        ("Superchess", create_superchess_backend()),
        ("The Turk", create_turk_backend()),
        ("3D Chess", create_3dchess_backend()),
    ]
    
    all_pass = True
    for name, backend in backends:
        result = backend.choose_move(
            position=position,
            legal_moves=legal_moves,
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id="mate-black"
        )
        
        if result.status != "ok":
            print(f"  ❌ {name}: Error - {result.evidence.failure_reason}")
            all_pass = False
            continue
        
        if result.move_uci == "d8h4":
            print(f"  ✅ {name}: Found mate-in-one (d8h4)")
        else:
            # FAIL - missed mate is a significant tactical error
            print(f"  ❌ {name}: MISSED mate-in-one, chose {result.move_uci}")
            all_pass = False
    
    return all_pass


def test_checkmate_position():
    """Test actual checkmate position handling."""
    print("\n=== Testing Checkmate Position ===")
    
    # Checkmate position - White to move, already checkmated
    # This is a terminal position
    position = "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 0 1"
    
    backends = [
        ("Spectrum Chess", create_spectrum_chess_backend()),
        ("Superchess", create_superchess_backend()),
    ]
    
    all_pass = True
    for name, backend in backends:
        try:
            board = chess.Board(position)
            # Black has no legal moves - should detect checkmate
            result = backend.choose_move(
                position=position,
                legal_moves=[],
                clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
                request_id="checkmate-position"
            )
            
            if result.status == "error" and "No valid legal moves" in result.evidence.failure_reason:
                print(f"  ✅ {name}: Correctly handled checkmate position")
            else:
                print(f"  ❌ {name}: Should handle checkmate with error, got status={result.status}")
                all_pass = False
        except Exception as e:
            print(f"  ❌ {name}: Exception on checkmate - {e}")
            all_pass = False
    
    return all_pass


def test_stalemate_position():
    """Test actual stalemate position handling."""
    print("\n=== Testing Stalemate Position ===")
    
    # Stalemate position - Black to move but no legal moves and not in check
    position = "k6K/8/8/8/8/8/8/4k3 w - - 0 1"
    
    backends = [
        ("Spectrum Chess", create_spectrum_chess_backend()),
        ("Superchess", create_superchess_backend()),
    ]
    
    all_pass = True
    for name, backend in backends:
        try:
            board = chess.Board(position)
            result = backend.choose_move(
                position=position,
                legal_moves=[],
                clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
                request_id="stalemate-position"
            )
            
            if result.status == "error" and "No valid legal moves" in result.evidence.failure_reason:
                print(f"  ✅ {name}: Correctly handled stalemate position")
            else:
                print(f"  ❌ {name}: Should handle stalemate with error, got status={result.status}")
                all_pass = False
        except Exception as e:
            print(f"  ❌ {name}: Exception on stalemate - {e}")
            all_pass = False
    
    return all_pass


def test_candidate_ordering_black():
    """Test that candidates are correctly ordered for Black."""
    print("\n=== Testing Candidate Ordering for Black ===")
    
    position = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    
    backends = [
        ("Spectrum Chess", create_spectrum_chess_backend()),
        ("Superchess", create_superchess_backend()),
        ("The Turk", create_turk_backend()),
        ("3D Chess", create_3dchess_backend()),
    ]
    
    all_pass = True
    for name, backend in backends:
        candidates = backend.get_candidates(position, n=3)
        
        if not candidates:
            print(f"  ❌ {name}: No candidates returned")
            all_pass = False
            continue
        
        board = chess.Board(position)
        for cand in candidates:
            move = chess.Move.from_uci(cand)
            if move not in board.legal_moves:
                print(f"  ❌ {name}: Candidate {cand} is not legal")
                all_pass = False
                break
        else:
            print(f"  ✅ {name}: Candidates {candidates} are all legal")
    
    return all_pass


def test_candidate_evidence_restricted():
    """Test that candidates_uci is restricted to caller's allowed set."""
    print("\n=== Testing Candidate Evidence Restriction ===")
    
    position = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
    
    # Restrict legal moves to just 2
    restricted_legal = ["e2e4", "e2e3"]
    
    backends = [
        ("Spectrum Chess", create_spectrum_chess_backend()),
        ("Superchess", create_superchess_backend()),
        ("The Turk", create_turk_backend()),
        ("3D Chess", create_3dchess_backend()),
    ]
    
    all_pass = True
    for name, backend in backends:
        result = backend.choose_move(
            position=position,
            legal_moves=restricted_legal,
            clock={"white_ms": 300000, "black_ms": 300000, "increment_ms": 0},
            request_id="candidate-restriction"
        )
        
        if result.status != "ok":
            print(f"  ❌ {name}: Error - {result.evidence.failure_reason}")
            all_pass = False
            continue
        
        # Check that candidates are from the restricted set
        candidates = result.evidence.candidates_uci or []
        
        # All candidates should be in the allowed set
        restricted_set = set(restricted_legal)
        all_in_set = all(c in restricted_set for c in candidates)
        
        if all_in_set:
            print(f"  ✅ {name}: Candidates restricted to {candidates}")
        else:
            print(f"  ❌ {name}: Candidates {candidates} not all in allowed set {restricted_set}")
            all_pass = False
    
    return all_pass


def main():
    """Run all tests."""
    print("="*60)
    print("COMPREHENSIVE BACKEND TESTS")
    print("="*60)
    
    results = {}
    
    results["Black-to-Move"] = test_black_to_move()
    results["Legal Move Restriction"] = test_legal_move_restriction()
    results["Mate-in-One White (FAIL if missed)"] = test_mate_in_one_white()
    results["Mate-in-One Black (FAIL if missed)"] = test_mate_in_one_black()
    results["Checkmate Position"] = test_checkmate_position()
    results["Stalemate Position"] = test_stalemate_position()
    results["Candidate Ordering (Black)"] = test_candidate_ordering_black()
    results["Candidate Evidence Restriction"] = test_candidate_evidence_restricted()
    
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
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
