"""
Pytest configuration — makes `src/` importable in tests.
"""
import sys
from pathlib import Path

# Add project root to sys.path so tests can do `from src.frequentist import ...`
sys.path.insert(0, str(Path(__file__).resolve().parent))