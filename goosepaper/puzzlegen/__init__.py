"""Self-contained puzzle generation cores (no rendering, no CLI, no third-party dependencies).

Each subpackage (e.g. ``sudoku``) holds only the pure grid-generation/solver logic for one puzzle
type. Rendering lives in ``goosepaper.storyprovider.puzzle``, as HTML - not here.
"""
