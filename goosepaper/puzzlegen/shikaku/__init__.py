from .config import DEFAULT_DIFFICULTY, DEFAULT_SIZE, DIFFICULTIES, SUPPORTED_SIZES
from .puzzle import Puzzle, generate_puzzle, generate_puzzles
from .rules import Rect

__all__ = [
    "DEFAULT_DIFFICULTY",
    "DEFAULT_SIZE",
    "DIFFICULTIES",
    "SUPPORTED_SIZES",
    "Puzzle",
    "Rect",
    "generate_puzzle",
    "generate_puzzles",
]
