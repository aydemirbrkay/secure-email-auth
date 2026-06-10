"""AES SubBytes adımı için ekranı dolduran S-Box referans diyaloğu."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..aes_pure import SBOX
from ..base import ANIM_COLORS
from arayuz.theme import MANAGER


class _SBoxReferenceDialog(QDialog):
    """Sabit AES S-Box tablosunu mevcut SubBytes eşlemeleriyle açıklar."""

    def __init__(
        self,
        mappings: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mappings = [(source.lower(), result.lower()) for source, result in mappings]
        self._used_inputs = {source for source, _ in self._mappings}

        self._configure_window()
        self._build_ui()
        self._populate_table()
        self._highlight_used_cells()
        self._resize_to_available_screen()
        self.restyle()
        MANAGER.themeChanged.connect(self._on_theme_changed)
        self.finished.connect(self._disconnect_theme_signal)

    @property
    def used_inputs(self) -> set[str]:
        return set(self._used_inputs)

    def highlighted_cells(self) -> set[tuple[int, int]]:
        return {
            (int(source[0], 16), int(source[1], 16))
            for source in self._used_inputs
        }

    def _configure_window(self) -> None:
        self.setWindowTitle("AES S-Box Referans Tablosu")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        self.rule_label = QLabel(
            "S-Box kullanımı: Girdi byte'ının ilk hex hanesi satırı, "
            "ikinci hex hanesi sütunu seçer."
        )
        self.rule_label.setWordWrap(True)
        self.rule_label.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
        layout.addWidget(self.rule_label)

        self.example_label = QLabel(self._example_text())
        self.example_label.setWordWrap(True)
        layout.addWidget(self.example_label)

        self.used_mappings_label = QLabel(self._used_mappings_text())
        self.used_mappings_label.setWordWrap(True)
        layout.addWidget(self.used_mappings_label)

        self.table_frame = QFrame(self)
        self.table_layout = QVBoxLayout(self.table_frame)
        self.table_layout.setContentsMargins(12, 10, 12, 12)
        self.table_layout.setSpacing(0)

        self.table = QTableWidget(16, 16, self.table_frame)
        self._table = self.table
        headers = [f"{index:X}" for index in range(16)]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setVerticalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setFixedHeight(30)
        self.table.verticalHeader().setFixedWidth(40)
        self.table_layout.addWidget(self.table)
        layout.addWidget(self.table_frame, stretch=1)

        self.close_btn = QPushButton("Kapat")
        self.close_btn.setFixedHeight(32)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _example_text(self) -> str:
        if not self._mappings:
            return "Bu adım için gösterilecek S-Box eşlemesi yok."
        source, result = self._mappings[0]
        row, col = source[0].upper(), source[1].upper()
        return (
            f"Bu adımın ilk örneği: {source} → satır {row}, sütun {col} "
            f"→ S[{row},{col}] = {result}"
        )

    def _used_mappings_text(self) -> str:
        unique = list(dict.fromkeys(self._mappings))
        summary = ", ".join(f"{source}→{result}" for source, result in unique)
        return f"Bu adımda kullanılan eşlemeler: {summary}"

    def _populate_table(self) -> None:
        for row in range(16):
            for col in range(16):
                item = QTableWidgetItem(f"{SBOX[row * 16 + col]:02x}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

    def _highlight_used_cells(self) -> None:
        first_source = self._mappings[0][0] if self._mappings else None
        for source in self._used_inputs:
            row, col = int(source[0], 16), int(source[1], 16)
            item = self.table.item(row, col)
            item.setBackground(QBrush(QColor(ANIM_COLORS["accent_yellow"])))
            item.setForeground(QBrush(QColor(ANIM_COLORS["bg_main"])))
            if source == first_source:
                font = item.font()
                font.setBold(True)
                font.setPointSize(font.pointSize() + 1)
                item.setFont(font)

    def _resize_to_available_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(900, 700)
            return
        available = screen.availableGeometry()
        target_width = min(1180, int(available.width() * 0.90))
        target_height = min(820, int(available.height() * 0.82))
        self.resize(target_width, target_height)

    def restyle(self) -> None:
        """Açık diyaloğu aktif uygulama temasına geçirir."""
        self.rule_label.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self.example_label.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self.used_mappings_label.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self.table_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_primary']}; "
            f"gridline-color: {ANIM_COLORS['border']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; }}"
            f"QTableWidget::item {{ padding: 3px; }}"
            f"QHeaderView::section {{ background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_secondary']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; padding: 4px; }}"
            f"QTableCornerButton::section {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; }}"
        )
        self._highlight_used_cells()
        self.update()

    def _on_theme_changed(self, _mode: str) -> None:
        self.restyle()

    def _disconnect_theme_signal(self, _result: int) -> None:
        try:
            MANAGER.themeChanged.disconnect(self._on_theme_changed)
        except TypeError:
            pass
