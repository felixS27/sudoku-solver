"""CSV import/export for 9x9 sudoku grids.

Supports two input formats:
- Full grid: 9 lines of 9 comma-separated values, blank for empty cells
  (matches the files in example_sudokus/).
- Coordinate list: rows of (row, col, value) triples, one given cell per row,
  with an optional header row. Row/col indexing is auto-detected as 0-based
  or 1-based from the observed range of values.
"""
import csv

Grid = list[list[int]]


def load_grid(path: str) -> Grid:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [row for row in csv.reader(f) if row]

    if not rows:
        raise ValueError("CSV file is empty")

    if len(rows) == 9 and all(len(row) == 9 for row in rows):
        return _parse_full_grid(rows)

    return _parse_coordinate_list(rows)


def _parse_full_grid(rows: list[list[str]]) -> Grid:
    grid = [[0] * 9 for _ in range(9)]
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            cell = cell.strip()
            if not cell:
                continue
            value = int(cell)
            if not 1 <= value <= 9:
                raise ValueError(f"Invalid value '{cell}' at row {r + 1}, col {c + 1}")
            grid[r][c] = value
    return grid


def _parse_coordinate_list(rows: list[list[str]]) -> Grid:
    data_rows = rows
    if not _is_int(rows[0][0]):
        data_rows = rows[1:]  # header row, e.g. "row,col,value"

    triples: list[tuple[int, int, int]] = []
    for row in data_rows:
        if len(row) != 3:
            raise ValueError(
                "Unrecognized CSV format: expected a 9x9 grid or (row, col, value) "
                f"triples, got a row with {len(row)} fields: {row}"
            )
        r, c, v = (cell.strip() for cell in row)
        if not (_is_int(r) and _is_int(c) and _is_int(v)):
            raise ValueError(f"Non-numeric entry in coordinate row: {row}")
        triples.append((int(r), int(c), int(v)))

    if not triples:
        raise ValueError("CSV file contains no data rows")

    rows_idx = [t[0] for t in triples]
    cols_idx = [t[1] for t in triples]
    zero_based = min(rows_idx) == 0 or min(cols_idx) == 0
    offset = 0 if zero_based else 1

    grid = [[0] * 9 for _ in range(9)]
    for r, c, v in triples:
        r -= offset
        c -= offset
        if not (0 <= r <= 8 and 0 <= c <= 8):
            raise ValueError(f"Coordinate out of range: row={r + offset}, col={c + offset}")
        if not 1 <= v <= 9:
            raise ValueError(f"Invalid value '{v}' at row={r + offset}, col={c + offset}")
        grid[r][c] = v
    return grid


def _is_int(s: str) -> bool:
    try:
        int(s.strip())
        return True
    except ValueError:
        return False


def save_grid(path: str, grid: Grid) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in grid:
            writer.writerow(value if value else "" for value in row)
