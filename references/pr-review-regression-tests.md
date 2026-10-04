# Regression Test Patterns for PR Fixes

## Pattern: Interface-Level TypeError Fix

**Scenario:** Caller passes parameter that base interface doesn't support

**Example:** `PunchessChessClient.play_game()` calls `backend.choose_move(..., strategy_revision=...)`
- But `ChessBackend.choose_move(position, legal_moves, clock, request_id)` has no `strategy_revision`
- Backend already has `strategy_revision` via `__init__`

**Test:**
```python
def test_play_game_does_not_pass_strategy_revision(self):
    """Verify play_game() doesn't pass unsupported strategy_revision param."""
    from chess_commander.backends.punchess_client import PunchessChessClient
    from chess_commander.backends.interface import BackendType, MoveResult, MoveEvidence
    
    # Create mock backend following CORRECT interface signature
    mock_backend = Mock()
    mock_backend.backend_type = BackendType.THOMPSON
    received_kwargs = {}
    
    def choose_move(position, legal_moves, clock, request_id):
        """Mock with correct signature - NO strategy_revision param."""
        nonlocal received_kwargs
        received_kwargs = locals()
        return MoveResult(...)
    
    mock_backend.choose_move = choose_move
    client = PunchessChessClient(punchess_url="http://localhost:8000", backend=mock_backend)
    
    # Mock HTTP client with proper lifecycle
    mock_join = AsyncMock(return_value=True)
    play_status = Mock(checkmate=False, ...)
    checkmate_status = Mock(checkmate=True, ...)
    
    call_count = [0]
    def get_game_status_side_effect(game_id):
        call_count[0] += 1
        return play_status if call_count[0] == 1 else checkmate_status
    
    mock_get_status = AsyncMock(side_effect=get_game_status_side_effect)
    mock_submit = AsyncMock(return_value=True)
    
    client.client = MagicMock()
    client.client.join_game = mock_join
    client.client.get_game_status = mock_get_status
    client.client.submit_move = mock_submit
    
    # Should NOT raise TypeError
    asyncio.run(client.play_game("test-game"))
    
    # Verify strategy_revision was NOT passed
    assert 'strategy_revision' not in received_kwargs
```

**Key points:**
- Mock backend follows base interface signature (no extra params)
- Test has proper exit path (terminal state via side_effect)
- Track what kwargs were actually passed to choose_move
- Assert that unsupported params are NOT in received_kwargs

## Pattern: While Loop with Async Mocks

**Scenario:** `play_game()` uses `while True` loop that needs termination

**WRONG test (infinite loop):**
```python
client.client.get_game_status = AsyncMock(return_value=Mock(
    checkmate=False, stalemate=False, ...  # Always playing
))
asyncio.run(client.play_game("test"))  # Never exits
```

**RIGHT test (proper exit):**
```python
call_count = [0]
def get_status_side_effect(game_id):
    call_count[0] += 1
    if call_count[0] == 1:
        return Mock(checkmate=False, ...)  # First call: playing
    else:
        return Mock(checkmate=True, ...)   # Second call: terminal

mock_get_status = AsyncMock(side_effect=get_status_side_effect)
client.client.get_game_status = mock_get_status
asyncio.run(client.play_game("test"))  # Exits after checkmate
```

**Key points:**
- Use `side_effect` list or callable to return different states
- Track call count to transition from "playing" to "terminal"
- Always mock `get_game_report()` if play_game() calls it after terminal state
- Test should complete in <5 mock calls to avoid CI timeouts

## Pattern: Verify All Imports in requirements.txt

**Scenario:** Code imports modules not in requirements.txt

**Test script (`scripts/verify-requirements.py`):**
```python
#!/usr/bin/env python3
"""Verify all imports match requirements.txt."""
import ast
import sys
from pathlib import Path

def get_imports(file_path):
    """Extract all import statements from Python file."""
    with open(file_path) as f:
        tree = ast.parse(f.read())
    
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

def main():
    src_dir = Path('chess_commander')
    req_file = Path('requirements.txt')
    
    # Get required packages
    required = set()
    with open(req_file) as f:
        for line in f:
            if line.strip() and not line.strip().startswith('#'):
                pkg = line.strip().split('>=')[0].split('==')[0]
                required.add(pkg)
    
    # Get imports from source
    found_imports = set()
    for py_file in src_dir.rglob('*.py'):
        found_imports.update(get_imports(py_file))
    
    # Check for missing
    missing = found_imports - required - {'chess'}  # chess is optional
    
    if missing:
        print(f"ERROR: Missing imports in requirements.txt: {sorted(missing)}")
        sys.exit(1)
    
    print("✓ All imports covered by requirements.txt")
    sys.exit(0)

if __name__ == '__main__':
    main()
```

**Run before commit:**
```bash
python scripts/verify-requirements.py
```

## Pattern: Conftest Fixture for Shared Backend

**Scenario:** Tests need backend but SSD file is external-only

**File: `tests/conftest.py`:**
```python
import os
import pytest

SSD_PATH = os.environ.get(
    'THOMPSON_SSD_PATH',
    '/mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd'
)

@pytest.fixture
def backend():
    """Provide Thompson backend instance for tests."""
    from chess_commander.backends.thompson import ThompsonChessBackend
    
    # Skip tests if SSD file missing
    if not os.path.exists(SSD_PATH):
        pytest.skip(f"SSD file not found: {SSD_PATH}. Set THOMPSON_SSD_PATH env var.")
    
    return ThompsonChessBackend(
        source_path=SSD_PATH,
        strategy_revision='test-v0'
    )
```

**Usage in tests:**
```python
def test_choose_move_starting_position(self, backend):
    """Test uses shared fixture - no hardcoded path."""
    position = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    legal_moves = ['e2e4', 'e2e3']
    
    result = backend.choose_move(
        position=position,
        legal_moves=legal_moves,
        clock={'white_ms': 300000, 'black_ms': 300000, 'increment_ms': 0},
        request_id='test-1'
    )
    
    assert result.status == 'ok'
    assert result.move_uci in legal_moves
```

**Key points:**
- Environment variable with sensible default
- `pytest.skip()` if file missing (not `assert False`)
- Tests use `backend` fixture parameter (not local constructor)
- CI workflow sets `THOMPSON_SSD_PATH` env var (same name as conftest)

## Pattern: PR Branch Ancestry Check

**Scenario: Verify clean branch history before creating PR**

**Checklist:**
```bash
# 1. Verify branch is based on intended base
git log --oneline --graph --all --decorate | head -20

# 2. Check for unrelated commits
git log --oneline main..pr-branch  # Should only show intended fixes
git log --oneline feature-branch..pr-branch  # Should not show unrelated features

# 3. Verify file count matches description
git diff main HEAD --stat

# 4. Check for common ancestor
git merge-base main pr-branch
# If no common ancestor: branch has no history in common with main

# 5. Final sanity check
git status --short  # Should only show intended changes
git diff --cached --stat  # Staged changes match description
```

**Red flags:**
- PR description says "8 files changed" but diff shows 51
- `git log main..pr-branch` includes unrelated feature commits
- Branch has no common ancestor with main (GitHub won't allow PR)
- PR title says "Phase 2: Thompson Backend" but only README changed

## Pattern: CI Workflow Matching

**Scenario: CI env var names must match conftest**

**WRONG:**
```yaml
# .github/workflows/ci.yml
env:
  SSD_PATH: ${{ secrets.SSD_PATH }}  # conftest expects THOMPSON_SSD_PATH

# tests/conftest.py
SSD_PATH = os.environ.get('THOMPSON_SSD_PATH', ...)  # No match!
```

**RIGHT:**
```yaml
# .github/workflows/ci.yml
env:
  THOMPSON_SSD_PATH: ${{ secrets.THOMPSON_SSD_PATH }}

# tests/conftest.py
SSD_PATH = os.environ.get('THOMPSON_SSD_PATH', ...)  # Match!
```

**Key points:**
- Use same env var name everywhere
- CI uses `${{ secrets.NAME }}` for secure storage
- conftest uses `os.environ.get('NAME', 'default')`
- README documents the env var name consistently
