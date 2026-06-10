# animation_modals/matrix_widget.py
"""
MatrixWidget — 4×4 QLabel grid.
AES state matrisi ve SHA-256 blok görselleştirmesi için paylaşımlı bileşen.

İsteğe bağlı r0..r3 satır etiketleri ve c0..c3 sütun etiketleri vardır
(``show_labels=True``); böylece kullanıcı matrisin hangi satır/sütununda
işlem yapıldığını net görür.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget

from arayuz.theme import COLORS, get_animation_tick_ms


# Aktif paletten canlı okunur (tema değişiminde yeni açılan matrisler doğru renkte).
def _default_bg() -> str:
    return COLORS["bg_card"]


def _default_fg() -> str:
    return COLORS["text_primary"]


def _label_fg() -> str:
    return COLORS["text_muted"]


class MatrixWidget(QWidget):
    """4×4 hücrelik görsel matris. Her hücre renkli QLabel.

    Args:
        rows: satır sayısı (varsayılan 4)
        cols: sütun sayısı (varsayılan 4)
        show_labels: True ise satır (r0..r3) ve sütun (c0..c3) etiketleri
            grid'in dış kenarında görünür — kullanıcının "hangi satırda
            işlem var" sorusunu anında yanıtlar.
        cell_size: (genişlik, yükseklik) — hücre minimum boyutu
        cell_font_pt: hücre değerlerinin font puntosu
    """

    def __init__(
        self,
        rows: int = 4,
        cols: int = 4,
        parent: QWidget | None = None,
        show_labels: bool = False,
        cell_size: tuple[int, int] = (60, 48),
        cell_font_pt: int = 11,
    ):
        super().__init__(parent)
        self._rows = rows
        self._cols = cols
        self._show_labels = show_labels
        self._cell_size = cell_size
        self._cell_font_pt = cell_font_pt
        self._cells: list[list[QLabel]] = []
        self._sub_timer: QTimer | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Sütun etiketleri (üstte) — show_labels açıksa
        if self._show_labels:
            for c in range(self._cols):
                col_lbl = QLabel(f"c{c}")
                col_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                col_lbl.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
                col_lbl.setStyleSheet(
                    f"color: {_label_fg()}; background: transparent;"
                )
                # Grid satır 0 etikete ayrılır, hücreler satır 1'den başlar
                layout.addWidget(col_lbl, 0, c + 1)

        cell_w, cell_h = self._cell_size

        row_offset = 1 if self._show_labels else 0
        col_offset = 1 if self._show_labels else 0

        for r in range(self._rows):
            # Satır etiketi (solda)
            if self._show_labels:
                row_lbl = QLabel(f"r{r}")
                row_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                row_lbl.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
                row_lbl.setStyleSheet(
                    f"color: {_label_fg()}; background: transparent;"
                )
                layout.addWidget(row_lbl, r + row_offset, 0)

            row: list[QLabel] = []
            for c in range(self._cols):
                cell = QLabel("00")
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setFont(QFont("Courier New", self._cell_font_pt, QFont.Weight.Bold))
                cell.setMinimumSize(cell_w, cell_h)
                cell.setStyleSheet(self._cell_style(_default_bg()))
                layout.addWidget(cell, r + row_offset, c + col_offset)
                row.append(cell)
            self._cells.append(row)

    @staticmethod
    def _cell_style(bg: str, fg: str | None = None) -> str:
        if fg is None:
            fg = _default_fg()
        return (
            f"background-color: {bg}; color: {fg}; "
            "border-radius: 4px; padding: 4px;"
        )

    def update_cell(self, row: int, col: int, value: str, bg: str | None = None) -> None:
        """Tek bir hücreyi günceller."""
        if bg is None:
            bg = _default_bg()
        cell = self._cells[row][col]
        cell.setText(value)
        cell.setStyleSheet(self._cell_style(bg))

    def set_matrix(self, matrix: list[list[str]], bg: str | None = None) -> None:
        """Tüm matrisi tek seferde günceller."""
        if bg is None:
            bg = _default_bg()
        for r in range(self._rows):
            for c in range(self._cols):
                self.update_cell(r, c, matrix[r][c], bg)

    def reset_colors(self) -> None:
        """Tüm hücrelerin arka plan rengini varsayılana döndürür."""
        for r in range(self._rows):
            for c in range(self._cols):
                cell = self._cells[r][c]
                cell.setStyleSheet(self._cell_style(_default_bg()))

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
        self._sub_timer.start(get_animation_tick_ms(interval_ms))

    def animate_row_shift(self, row: int, shift: int, color: str | None = None) -> None:
        """Bir satırı shift kadar sola kaydırır ve renklendirir."""
        if color is None:
            color = COLORS["accent_blue"]
        texts = [self._cells[row][c].text() for c in range(self._cols)]
        shifted = texts[shift:] + texts[:shift]
        for c in range(self._cols):
            self.update_cell(row, c, shifted[c], color)
