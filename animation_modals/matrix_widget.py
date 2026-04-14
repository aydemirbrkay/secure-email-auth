# animation_modals/matrix_widget.py
"""
MatrixWidget — 4×4 QLabel grid.
AES state matrisi ve SHA-256 blok görselleştirmesi için paylaşımlı bileşen.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget

_DEFAULT_BG = "#536070"
_DEFAULT_FG = "#F1F3F7"


class MatrixWidget(QWidget):
    """4×4 hücrelik görsel matris. Her hücre renkli QLabel."""

    def __init__(self, rows: int = 4, cols: int = 4, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows = rows
        self._cols = cols
        self._cells: list[list[QLabel]] = []
        self._sub_timer: QTimer | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        for r in range(self._rows):
            row: list[QLabel] = []
            for c in range(self._cols):
                cell = QLabel("00")
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
                cell.setMinimumSize(60, 48)
                cell.setStyleSheet(self._cell_style(_DEFAULT_BG))
                layout.addWidget(cell, r, c)
                row.append(cell)
            self._cells.append(row)

    @staticmethod
    def _cell_style(bg: str, fg: str = _DEFAULT_FG) -> str:
        return (
            f"background-color: {bg}; color: {fg}; "
            "border-radius: 4px; padding: 4px;"
        )

    def update_cell(self, row: int, col: int, value: str, bg: str = _DEFAULT_BG) -> None:
        """Tek bir hücreyi günceller."""
        cell = self._cells[row][col]
        cell.setText(value)
        cell.setStyleSheet(self._cell_style(bg))

    def set_matrix(self, matrix: list[list[str]], bg: str = _DEFAULT_BG) -> None:
        """Tüm matrisi tek seferde günceller."""
        for r in range(self._rows):
            for c in range(self._cols):
                self.update_cell(r, c, matrix[r][c], bg)

    def reset_colors(self) -> None:
        """Tüm hücrelerin arka plan rengini varsayılana döndürür."""
        for r in range(self._rows):
            for c in range(self._cols):
                cell = self._cells[r][c]
                cell.setStyleSheet(self._cell_style(_DEFAULT_BG))

    def highlight_cells_sequential(
        self,
        ops: list[tuple[int, int, str]],
        highlight_color: str,
        interval_ms: int,
        callback: "callable | None" = None,
    ) -> None:
        """
        Her hücreyi sırayla highlight_color ile boyar ve new_value ile günceller.
        ops: list of (row, col, new_value)
        Tamamlandığında callback çağrılır.
        """
        if self._sub_timer is not None:
            self._sub_timer.stop()
            self._sub_timer.deleteLater()

        index = [0]
        self._sub_timer = QTimer(self)

        def _tick() -> None:
            if index[0] >= len(ops):
                self._sub_timer.stop()
                self._sub_timer.deleteLater()
                self._sub_timer = None
                if callback:
                    callback()
                return
            r, c, val = ops[index[0]]
            self.update_cell(r, c, val, highlight_color)
            index[0] += 1

        self._sub_timer.timeout.connect(_tick)
        self._sub_timer.start(interval_ms)

    def animate_row_shift(self, row: int, shift: int, color: str = "#3B6FA0") -> None:
        """Bir satırı shift kadar sola kaydırır ve renklendirir."""
        texts = [self._cells[row][c].text() for c in range(self._cols)]
        shifted = texts[shift:] + texts[:shift]
        for c in range(self._cols):
            self.update_cell(row, c, shifted[c], color)
