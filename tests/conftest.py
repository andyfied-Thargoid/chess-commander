"""Configuration for pytest tests."""
import os
import pytest

# Use SSD path from environment variable, or default to compute01 path
SSD_PATH = os.environ.get(
    'THOMPSON_SSD_PATH',
    '/mnt/scratch/project-data/chess-commander/Computer_Concepts_Chess_DThompson.ssd'
)


@pytest.fixture
def backend():
    """Provide a Thompson backend instance for tests."""
    from chess_commander.backends.thompson import ThompsonChessBackend
    
    # Skip tests that require SSD file if path doesn't exist
    if not os.path.exists(SSD_PATH):
        pytest.skip(f"SSD file not found: {SSD_PATH}. Set THOMPSON_SSD_PATH environment variable.")
    
    return ThompsonChessBackend(
        source_path=SSD_PATH,
        strategy_revision='test-v0'
    )
