"""PySide6 GUI for the sudoku solver."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIntValidator
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import csv_io
import solver

Grid = list[list[int]]

STATUS_COLORS = {
    "neutral": "#495057",
    "info": "#0d6efd",
    "success": "#0f5132",
    "error": "#842029",
}


def find_conflicts(grid: Grid) -> set[tuple[int, int]]:
    """Return coordinates of cells that clash with another cell in their row/col/box."""
    conflicts: set[tuple[int, int]] = set()

    def check_group(cells: list[tuple[int, int]]) -> None:
        seen: dict[int, tuple[int, int]] = {}
        for r, c in cells:
            value = grid[r][c]
            if value == 0:
                continue
            if value in seen:
                conflicts.add(seen[value])
                conflicts.add((r, c))
            else:
                seen[value] = (r, c)

    for r in range(9):
        check_group([(r, c) for c in range(9)])
    for c in range(9):
        check_group([(r, c) for r in range(9)])
    for box_r in range(3):
        for box_c in range(3):
            check_group(
                [
                    (box_r * 3 + i, box_c * 3 + j)
                    for i in range(3)
                    for j in range(3)
                ]
            )
    return conflicts


class SudokuCell(QLineEdit):
    """A single editable digit cell that tracks whether it's a given or a solved value."""

    changed = Signal(int, int)

    def __init__(self, row: int, col: int):
        super().__init__()
        self.row = row
        self.col = col
        self.is_given = False
        self.is_solved = False
        self._conflict = False

        self.setAlignment(Qt.AlignCenter)
        self.setMaxLength(1)
        self.setValidator(QIntValidator(1, 9))
        self.setFixedSize(36, 36)
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)

        self.textEdited.connect(self._on_edited)
        self._update_style()

    def _on_edited(self, _text: str) -> None:
        self.is_given = bool(self.text())
        self.is_solved = False
        self._update_style()
        self.changed.emit(self.row, self.col)

    def value(self) -> int:
        text = self.text().strip()
        return int(text) if text else 0

    def set_value(self, value: int, *, given: bool = False, solved: bool = False) -> None:
        self.setText(str(value) if value else "")
        self.is_given = given
        self.is_solved = solved
        self._update_style()

    def set_conflict(self, conflict: bool) -> None:
        self._conflict = conflict
        self._update_style()

    def _update_style(self) -> None:
        if self._conflict:
            bg, color = "#f8d7da", "#842029"
        elif self.is_solved:
            bg, color = "#d1e7dd", "#0f5132"
        elif self.is_given:
            bg, color = "#e9ecef", "#000000"
        else:
            bg, color = "#ffffff", "#000000"
        weight = "normal" if (not self.is_given and not self.is_solved) else "bold"
        self.setStyleSheet(
            "QLineEdit {"
            f"background-color: {bg}; color: {color}; font-weight: {weight}; "
            "border: 1px solid #adb5bd; border-radius: 0px; }"
        )


class BoardWidget(QWidget):
    """The 9x9 board, laid out as nine 3x3 boxes so box borders stand out."""

    cell_changed = Signal()

    def __init__(self):
        super().__init__()
        self.cells: list[list[SudokuCell]] = [[None] * 9 for _ in range(9)]  # type: ignore[list-item]

        board_frame = QFrame()
        board_frame.setFrameShape(QFrame.Box)
        board_frame.setStyleSheet("QFrame { border: 3px solid #adb5bd; }")

        outer = QGridLayout(board_frame)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        for box_r in range(3):
            for box_c in range(3):
                box = QFrame()
                box.setFrameShape(QFrame.Box)
                box.setStyleSheet("QFrame { border: 2px solid #343a40; }")
                inner = QGridLayout(box)
                inner.setSpacing(1)
                inner.setContentsMargins(2, 2, 2, 2)
                for i in range(3):
                    for j in range(3):
                        r, c = box_r * 3 + i, box_c * 3 + j
                        cell = SudokuCell(r, c)
                        cell.changed.connect(lambda _r, _c: self.cell_changed.emit())
                        inner.addWidget(cell, i, j)
                        self.cells[r][c] = cell
                outer.addWidget(box, box_r, box_c)

        self_layout = QGridLayout(self)
        self_layout.setContentsMargins(0, 0, 0, 0)
        self_layout.addWidget(board_frame, 0, 0)

    def get_grid(self) -> Grid:
        return [[self.cells[r][c].value() for c in range(9)] for r in range(9)]

    def set_grid(self, grid: Grid, *, given: bool = True) -> None:
        for r in range(9):
            for c in range(9):
                self.cells[r][c].set_value(grid[r][c], given=given and grid[r][c] != 0)

    def apply_solution(self, grid: Grid) -> None:
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                if cell.value() == 0:
                    cell.set_value(grid[r][c], solved=True)

    def highlight_conflicts(self, conflicts: set[tuple[int, int]]) -> None:
        for r in range(9):
            for c in range(9):
                self.cells[r][c].set_conflict((r, c) in conflicts)

    def clear(self) -> None:
        for r in range(9):
            for c in range(9):
                self.cells[r][c].set_value(0)


class SolverThread(QThread):
    """Runs solver.solve() off the GUI thread so the window stays responsive."""

    progress = Signal(str)
    solved = Signal(str, object)
    failed = Signal(str)

    def __init__(self, grid: Grid):
        super().__init__()
        self.grid = grid

    def run(self) -> None:
        try:
            status, result = solver.solve(self.grid, progress_callback=self.progress.emit)
            self.solved.emit(status, result)
        except NotImplementedError as exc:
            self.failed.emit(f"Solver not implemented yet: {exc}")
        except Exception as exc:  # surface solver bugs instead of crashing the GUI
            self.failed.emit(f"Solver error: {exc}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sudoku Solver")
        self._solver_thread: SolverThread | None = None

        self.board = BoardWidget()
        self.board.cell_changed.connect(self._on_grid_edited)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self._set_status("Ready", "neutral")

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #6c757d; font-style: italic;")

        load_btn = QPushButton("Load CSV")
        save_btn = QPushButton("Save CSV")
        clear_btn = QPushButton("Clear")
        self.solve_btn = QPushButton("Solve")

        load_btn.clicked.connect(self._load_csv)
        save_btn.clicked.connect(self._save_csv)
        clear_btn.clicked.connect(self._clear_board)
        self.solve_btn.clicked.connect(self._solve)

        button_row = QHBoxLayout()
        for button in (load_btn, save_btn, clear_btn, self.solve_btn):
            button_row.addWidget(button)

        layout = QVBoxLayout()
        layout.addLayout(button_row)
        layout.addWidget(self.board, alignment=Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _set_status(self, text: str, kind: str = "neutral") -> None:
        self.status_label.setText(text)
        color = STATUS_COLORS.get(kind, STATUS_COLORS["neutral"])
        self.status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")

    def _on_grid_edited(self) -> None:
        conflicts = find_conflicts(self.board.get_grid())
        self.board.highlight_conflicts(conflicts)
        if conflicts:
            self._set_status("Conflicting entries — fix the highlighted cells", "error")
        else:
            self._set_status("Ready", "neutral")
        self.progress_label.setText("")

    def _load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load sudoku CSV", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            grid = csv_io.load_grid(path)
        except Exception as exc:
            QMessageBox.critical(self, "Failed to load CSV", str(exc))
            self._set_status(f"Failed to load CSV: {exc}", "error")
            return

        self.board.set_grid(grid, given=True)
        self.progress_label.setText("")
        conflicts = find_conflicts(grid)
        self.board.highlight_conflicts(conflicts)
        if conflicts:
            self._set_status("Loaded, but the puzzle has conflicting entries", "error")
        else:
            self._set_status(f"Loaded {os.path.basename(path)}", "neutral")

    def _save_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save sudoku CSV", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            csv_io.save_grid(path, self.board.get_grid())
        except Exception as exc:
            QMessageBox.critical(self, "Failed to save CSV", str(exc))
            return
        self._set_status(f"Saved to {os.path.basename(path)}", "success")

    def _clear_board(self) -> None:
        self.board.clear()
        self.board.highlight_conflicts(set())
        self.progress_label.setText("")
        self._set_status("Ready", "neutral")

    def _solve(self) -> None:
        grid = self.board.get_grid()
        conflicts = find_conflicts(grid)
        if conflicts:
            self.board.highlight_conflicts(conflicts)
            self._set_status("Cannot solve: conflicting entries", "error")
            return

        self.solve_btn.setEnabled(False)
        self._set_status("Solving…", "info")
        self.progress_label.setText("")

        self._solver_thread = SolverThread(grid)
        self._solver_thread.progress.connect(self.progress_label.setText)
        self._solver_thread.solved.connect(self._on_solve_finished)
        self._solver_thread.failed.connect(self._on_solve_failed)
        self._solver_thread.finished.connect(self._solver_thread.deleteLater)
        self._solver_thread.start()

    def _on_solve_finished(self, status: str, result_grid: Grid) -> None:
        self.solve_btn.setEnabled(True)
        self.progress_label.setText("")
        if status == "solved":
            self.board.apply_solution(result_grid)
            self.board.highlight_conflicts(set())
            self._set_status("Sudoku solved!", "success")
        elif status == "unsolvable":
            self._set_status("No solution exists for this sudoku", "error")
        else:
            self._set_status(f"Unexpected solver status: {status!r}", "error")

    def _on_solve_failed(self, message: str) -> None:
        self.solve_btn.setEnabled(True)
        self.progress_label.setText("")
        self._set_status(message, "error")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
