"""Chess Commander server - Punchess integration."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from chess_commander.backends.thompson import ThompsonChessBackend
from chess_commander.backends.punchess_client import PunchessChessClient


async def main():
    """Start chess commander server."""
    
    # Load configuration
    config_path = Path("config/backends.yaml")
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return
    
    # Import YAML parser
    try:
        import yaml
    except ImportError:
        print("PyYAML not installed. Install with: pip install pyyaml")
        return
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Select backend
    backends_config = config.get("backends", {})
    
    if backends_config.get("thompson", {}).get("enabled", False):
        source_path = backends_config["thompson"]["source_path"]
        strategy_revision = backends_config["thompson"]["strategy_revision"]
        
        backend = ThompsonChessBackend(
            source_path=source_path,
            strategy_revision=strategy_revision
        )
        
        print(f"✓ Thompson backend loaded")
        print(f"  Source SHA-256: {backend.source_sha256[:16]}...")
        print(f"  Strategy revision: {strategy_revision}")
    
    else:
        print("No backends enabled in config")
        return
    
    # Initialize Punchess client
    punchess_url = config.get("punchess", {}).get("url", "http://localhost:8000")
    
    client = PunchessChessClient(
        punchess_url=punchess_url,
        backend=backend
    )
    
    print(f"✓ Punchess client connected to {punchess_url}")
    
    # List available games
    games = await client.join_lobby()
    
    if games:
        print(f"✓ Found {len(games)} available games:")
        for game_id in games[:5]:
            print(f"  - {game_id}")
        if len(games) > 5:
            print(f"  ... and {len(games) - 5} more")
    else:
        print("No games available in lobby")
    
    # Print statistics
    stats = await client.client.get_statistics()
    
    if stats:
        print(f"\n✓ Server statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    print("\n✓ Chess Commander server running")
    print("\nTo play games, use: await client.play_game('game_id')")


if __name__ == "__main__":
    asyncio.run(main())
