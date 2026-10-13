from .config import DEFAULT_BOX_SIZE, DEFAULT_DIFFICULTY, DIFFICULTIES, SUPPORTED_BOX_SIZES, SYMBOL_ALPHABET
from .puzzle import Puzzle, generate_puzzle, generate_puzzles
from .rules import box_size_to_n

__all__ = [
    "DEFAULT_BOX_SIZE",
    "DEFAULT_DIFFICULTY",
    "DIFFICULTIES",
    "SUPPORTED_BOX_SIZES",
    "SYMBOL_ALPHABET",
    "Puzzle",
    "box_size_to_n",
    "generate_puzzle",
    "generate_puzzles",
]
