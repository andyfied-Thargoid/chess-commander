"""Configuration for pytest tests."""
import os
import pytest

# Use SSD path from environment variable, or use a minimal test path
# For CI, if THOMPSON_SSD_PATH is not set, we'll skip SSD-dependent tests
SSD_PATH = os.environ.get(
    'THOMPSON_SSD_PATH',
    None  # No default - tests will skip if not set
)


@pytest.fixture
def backend():
    """Provide a Thompson backend instance for tests."""
    from chess_commander.backends.thompson import ThompsonChessBackend
    
    if SSD_PATH is None or not os.path.exists(SSD_PATH):
        pytest.skip(f"SSD file not found at {SSD_PATH}. Set THOMPSON_SSD_PATH environment variable.")
    
    return ThompsonChessBackend(
        source_path=SSD_PATH,
        strategy_revision='test-v0'
    )


@pytest.fixture
def minimal_backend():
    """
    Provide a minimal backend for testing logic without SSD file.
    
    This creates a ThompsonChessBackend instance without loading
    the actual SSD file, allowing us to test the evaluation logic.
    """
    # Create instance without calling __init__
    backend = ThompsonChessBackend.__new__(ThompsonChessBackend)
    backend.backend_type = BackendType.THOMPSON
    backend.source_sha256 = "test-sha256"
    backend.strategy_revision = "test-v0"
    # Set up minimal board data for testing (64-byte array of zeros)
    backend.board_data = [0x00] * 64
    backend.MATERIAL_VALUES = {
        'P': 100, 'N': 320, 'B': 330,
        'R': 500, 'Q': 900, 'K': 10000
    }
    return backend
