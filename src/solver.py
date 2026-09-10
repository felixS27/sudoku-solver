
from collections import defaultdict
from collections.abc import Callable

import numpy as np

Grid = list[list[int]]  # 9x9, 0 = empty cell


def solve(grid: Grid, progress_callback: Callable[[str], None] | None = None) -> tuple[str, Grid]:
    """Solve a 9x9 sudoku. Called by the GUI's Solve button.

    Args:
        grid: 9x9 grid of ints, 0 for empty cells. Already checked by the GUI
            to contain no row/column/box conflicts.
        progress_callback: optional callback for short human-readable status
            updates (e.g. "trying 4 at (2,5)") shown live in the GUI. May be
            called from a background thread; safe to ignore or call often.

    Returns:
        (status, result_grid): status is "solved" or "unsolvable".
        result_grid is the completed grid on "solved", or a best-effort
        (possibly partial) grid otherwise.
    """
    raise NotImplementedError("TODO: implement the solving algorithm")


def grid_to_coordinate_lists(grid: Grid) -> tuple[list[int], list[int], list[int]]:
    """Parallel (rows, cols, values) — one entry per filled cell."""
    rows, cols, values = [], [], []
    for r in range(9):
        for c in range(9):
            v = grid[r][c]
            if v:
                rows.append(r)
                cols.append(c)
                values.append(v)
    return rows, cols, values

def solve(grid, progress_callback=None):
    given = grid_to_dict(grid)          # or: rows, cols, values = grid_to_coordinate_lists(grid)