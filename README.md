# sudoku-solver

A 9x9 sudoku solver with a desktop GUI, written in Python. Puzzles are solved
using the same logical techniques a human would use (naked singles, hidden
singles, pointing pairs/triples, claiming boxes), falling back to backtracking
search only for cells that can't be resolved by logic alone.

## How it works

The solver (`src/solver.py`) represents the puzzle as a 9x9x9 NumPy array:
one boolean-ish layer per digit (1-9), each layer a 9x9 grid marking which
cells could still hold that digit. A solved cell is marked with a sentinel
value (`10`) on its digit's layer.

Each round of `solving_loop` applies a sequence of standard sudoku
techniques, removing candidates and filling in cells until no further
progress can be made:

- **Naked singles** — a cell with only one remaining candidate must hold
  that digit.
- **Hidden singles** — if a digit only fits in one cell of a row, column, or
  3x3 box, it goes there.
- **Pointing pairs/triples** — if a digit's remaining candidates within a
  box all fall in one row or column, it can be eliminated from the rest of
  that row/column outside the box.
- **Claiming boxes (box-line reduction)** — the mirror image: if a digit's
  remaining candidates within a row or column all fall in one box, it can be
  eliminated from the rest of that box.

If these techniques stall before the puzzle is complete, `recursive_solve`
takes over: it picks the cell with the fewest remaining candidates, guesses
one, and re-runs the logical solver, backtracking whenever a guess leads to
a contradiction.

## Project layout

```
sudoku_solver.py      Entry point — launches the GUI
src/
  solver.py            Core solving logic (technique-based + backtracking)
  csv_io.py            CSV import/export for puzzle grids
  GUI.py               PySide6 desktop UI
example_sudokus/       Sample unsolved puzzles (easy to extreme)
```

## Requirements

- Python >= 3.13
- [NumPy](https://numpy.org/)
- [PySide6](https://pypi.org/project/PySide6/) (Qt for Python)

Dependencies are declared in `pyproject.toml` and locked in `uv.lock`.

## Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv sync
```

Or with plain `pip`:

```bash
pip install numpy pyside6
```

## Usage

Launch the GUI:

```bash
uv run sudoku_solver.py
# or, without uv:
python sudoku_solver.py
```

In the window that opens:

1. **Enter a puzzle** by typing digits directly into the grid, or click
   **Load CSV** to import one (see below). Cells you type into are treated
   as givens.
2. Click **Solve**. Solving runs in a background thread so the UI stays
   responsive; while backtracking is in progress, a status line below the
   grid shows each guess being tried (e.g. "trying 4 at (2,5)"). Solved
   cells are filled in and shown in a different color from the original
   givens.
3. Click **Save CSV** to export the current grid, or **Clear** to start
   over.

Conflicting entries (the same digit twice in a row, column, or box) are
highlighted in red and block solving until fixed.

### CSV format

Two formats are supported for `Load CSV` (see `example_sudokus/` for
samples):

- **Full grid**: 9 lines of 9 comma-separated values, with empty cells left
  blank, e.g.:

  ```
  ,9,,3,,,6,,
  1,2,,,5,,7,3,
  ...
  ```

- **Coordinate list**: one given cell per row as `row,col,value` triples,
  with an optional header row. Indexing is auto-detected as 0-based or
  1-based from the values present.

`Save CSV` always writes the full-grid format.

## License

MIT — see [LICENSE](LICENSE).
