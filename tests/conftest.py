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
    
    This creates a backend that doesn't load actual board data,
    allowing us to test the evaluation logic and interfaces.
    """
    # Create a minimal mock-like backend for testing
    class MinimalThompsonBackend:
        backend_type = None
        source_sha256 = "test-sha256"
        strategy_revision = "test-v0"
        MATERIAL_VALUES = {
            'P': 100, 'N': 320, 'B': 330, 
            'R': 500, 'Q': 900, 'K': 10000
        }
        
        def _char_to_piece(self, char: str) -> int:
            encoding = {
                'P': 0x10, 'N': 0x20, 'B': 0x30,
                'R': 0x40, 'Q': 0x50, 'K': 0x60,
                'p': 0x90, 'n': 0xA0, 'b': 0xB0,
                'r': 0xC0, 'q': 0xD0, 'k': 0xE0
            }
            return encoding.get(char, 0x00)
    
    return MinimalThompsonBackend()
