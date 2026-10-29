"""Generation of Shikaku rectangle partitions.

Unlike Kakuro's layout generation, this always produces a valid result on
the first try: recursively splitting a rectangle into two smaller
rectangles can never create overlaps or gaps by construction, so there's
no generate-and-check retry loop needed here (contrast with
``modules.kakuro.grid.generate_layout``, which does need one).
"""

from __future__ import annotations

import random

from .rules import Rect


MIN_RECT_AREA = 2  # a 1-cell block is a degenerate "clue == 1" that carries no
# deduction (a rectangle of area 1 can only ever be itself) -- real Shikaku
# puzzles never use it, so no split may ever produce one.


def _can_split_horizontally(width: int, height: int) -> bool:
    """Whether a cut through the columns (into a ``w1 x height`` and a
    ``w2 x height`` piece) can be placed such that both pieces still have
    area >= ``MIN_RECT_AREA``. If ``height`` alone already covers the
    minimum (height >= 2), any width split of 1 or more works, so only
    ``width >= 2`` is required; if ``height == 1``, each piece needs
    ``width >= 2`` on its own, so the whole region needs ``width >= 4``."""
    if height >= MIN_RECT_AREA:
        return width >= 2
    return width >= 2 * MIN_RECT_AREA


def _can_split_vertically(width: int, height: int) -> bool:
    if width >= MIN_RECT_AREA:
        return height >= 2
    return height >= 2 * MIN_RECT_AREA


# Probability that a region *not* otherwise forced to split still splits
# further, purely for size variety. Kept low deliberately: every extra
# split adds two new regions that can *each* split again, so this
# compounds fast -- raising it back to 0.5 turned the same 20x20/
# min_blocks=60 case from ~67 blocks (this value) back up over 100.
VARIETY_SPLIT_PROBABILITY = 0.2


def generate_partition(size: int, rng: random.Random, min_blocks: int, max_block_area: int) -> list[Rect]:
    """Recursively split the size x size grid into at least ``min_blocks``
    rectangles, none smaller than ``MIN_RECT_AREA`` cells and none larger
    than ``max_block_area`` cells.

    Starting from the whole grid as one region, each region is either kept
    as a final rectangle or split (random axis, random position) into two
    sub-regions, which get the same treatment. A region is *forced* to
    split further whenever either:

    - the partition doesn't have enough rectangles yet -- ``len(finished)
      + len(regions) + 1`` (every still-pending region counted as at
      least one eventual block, plus this one) is a lower bound on the
      final count if this region were kept as-is; forcing a split
      whenever that bound is still under ``min_blocks`` guarantees the
      final partition has at least that many rectangles, however the
      remaining regions end up splitting -- or
    - this region alone is already larger than ``max_block_area`` --
      needed because meeting ``min_blocks`` alone doesn't prevent *one*
      region from staying huge while the rest split down small; both
      conditions are needed to fix the actual complaint (large blocks
      specifically, not just too few of them).

    A region small enough to satisfy both still splits further with
    probability ``VARIETY_SPLIT_PROBABILITY``, for size variety. An
    earlier version had neither of these forcing conditions (just a flat
    per-region stop probability), which had a large enough chance of never
    splitting the top-level region at all that many generated puzzles
    came out as a single giant rectangle covering the entire grid.

    Every cut is placed so that *both* resulting pieces stay at or above
    ``MIN_RECT_AREA`` (see ``_can_split_horizontally``/``_can_split_vertically``
    and the cut-range bounds below) -- by induction from the size x size
    root region, no region with area 1 can ever be produced, so none is
    ever finalized as a rectangle either.

    Raises ``ValueError`` if ``min_blocks`` or ``max_block_area`` is
    mathematically unreachable (every block needs at least
    ``MIN_RECT_AREA`` cells, so no more than ``size * size //
    MIN_RECT_AREA`` blocks can ever fit, and no cap below ``MIN_RECT_AREA``
    can ever be satisfied) -- caught early here rather than looping
    forever trying to satisfy an impossible target.

    A *tight* ``max_block_area`` sounds like it should produce a partition
    close to ``min_blocks``, but it can do the opposite: cuts are placed
    at a uniform random position, so splits are usually uneven, and
    reliably keeping *every* resulting piece under a tight cap takes many
    more forced splits than the "perfect packing" math suggests (measured:
    a cap of 2x the grid's fair share per block, on a 20x20 grid targeting
    min_blocks=60, actually produced ~90 blocks on average -- a looser cap
    of 6x the fair share produced only ~67). A tighter cap than the
    difficulty preset's default may need a correspondingly patient
    ``MAX_PARTITION_ATTEMPTS``/generation time budget in ``puzzle.py``.
    """
    max_possible_blocks = (size * size) // MIN_RECT_AREA
    if min_blocks > max_possible_blocks:
        raise ValueError(
            f"min_blocks={min_blocks} ist fuer ein {size}x{size}-Raster nicht erreichbar "
            f"(jeder Block braucht mindestens {MIN_RECT_AREA} Felder, maximal moeglich: {max_possible_blocks})"
        )
    if max_block_area < MIN_RECT_AREA:
        raise ValueError(
            f"max_block_area={max_block_area} ist nicht erreichbar "
            f"(jeder Block braucht mindestens {MIN_RECT_AREA} Felder)"
        )
    regions = [Rect(top=0, left=0, bottom=size, right=size)]
    finished: list[Rect] = []

    while regions:
        # Picking a *uniformly random* pending region here (rather than
        # always the most recently pushed one) matters: a plain
        # last-in-first-out stack, combined with always pushing the
        # left/top half before the right/bottom half below, would always
        # process the right/bottom half immediately and recursively --
        # systematically drilling into the bottom-right corner first,
        # while earlier siblings (e.g. the left/top half) sit untouched
        # until "not enough blocks yet" is already satisfied elsewhere,
        # leaving them coarse. Measured with the old LIFO order on a
        # 20x20/min_blocks=20/max_block_area=36 grid: bottom-right
        # quadrant averaged area 7.5 across 12 blocks, top-left averaged
        # area 24.5 across only 4 -- a bug reported as "bottom-right looks
        # much more finely divided than the rest".
        region = regions.pop(rng.randrange(len(regions)))
        width = region.right - region.left
        height = region.bottom - region.top

        can_split_horizontally = _can_split_horizontally(width, height)
        can_split_vertically = _can_split_vertically(width, height)
        if not can_split_horizontally and not can_split_vertically:
            finished.append(region)
            continue

        not_enough_blocks_yet = len(finished) + len(regions) + 1 < min_blocks
        must_split = not_enough_blocks_yet or region.area > max_block_area
        if not must_split and rng.random() >= VARIETY_SPLIT_PROBABILITY:
            finished.append(region)
            continue

        axes = [axis for axis, ok in (("h", can_split_horizontally), ("v", can_split_vertically)) if ok]
        axis = rng.choice(axes)

        if axis == "h":
            min_w = 1 if height >= MIN_RECT_AREA else MIN_RECT_AREA
            cut = rng.randint(region.left + min_w, region.right - min_w)
            regions.append(Rect(region.top, region.left, region.bottom, cut))
            regions.append(Rect(region.top, cut, region.bottom, region.right))
        else:
            min_h = 1 if width >= MIN_RECT_AREA else MIN_RECT_AREA
            cut = rng.randint(region.top + min_h, region.bottom - min_h)
            regions.append(Rect(region.top, region.left, cut, region.right))
            regions.append(Rect(cut, region.left, region.bottom, region.right))

    return finished
