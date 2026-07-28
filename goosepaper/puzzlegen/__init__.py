"""Self-contained puzzle generation cores (no rendering, no CLI, no third-party dependencies).

Each subpackage (e.g. ``sudoku``) is a vendored-and-stripped copy of the equivalent module from
a sibling puzzle-generation project, keeping only the pure grid-generation/solver logic. Rendering
lives in ``goosepaper.storyprovider.puzzle``, as HTML - not here, and not as the reportlab-based
PDF rendering the original modules also had.
"""
