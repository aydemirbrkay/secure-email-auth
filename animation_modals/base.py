# animation_modals/base.py
"""
CryptoAnimationWindow — Tüm animasyon pencerelerinin taban sınıfı.
QWidget subclass, show() ile bağımsız pencere olarak açılır.
QTimer animasyonu otomatik oynatır.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ANIM_COLORS = {
    "bg_main":        "#1e1e2e",
    "bg_card":        "#313150",
    "bg_input":       "#3b3b5c",
    "text_primary":   "#cdd6f4",
    "text_secondary": "#a6adc8",
    "text_muted":     "#6c7086",
    "accent_blue":    "#89b4fa",
    "accent_green":   "#a6e3a1",
    "accent_yellow":  "#f9e2af",
    "accent_mauve":   "#cba6f7",
    "accent_peach":   "#fab387",
    "border":         "#45475a",
}

_SPEED_MAP: dict[str, int] = {"Yavaş": 2000, "Normal": 1500, "Hızlı": 800}


class CryptoAnimationWindow(QWidget):
    """
    Ortak animasyon penceresi taban sınıfı.

    Alt sınıflar şunları override eder:
      _init_content()       → content_area'ya widget ekler
      _render_step(idx)     → idx numaralı adımı gösterir
      _show_match_result()  → son eşleşme ekranını gösterir
    """

    def __init__(
        self,
        title: str,
        total_steps: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 580)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet(
            f"background-color: {ANIM_COLORS['bg_main']}; "
            f"color: {ANIM_COLORS['text_primary']};"
        )

        self.current_step: int = 0
        self.total_steps: int = total_steps
        self.speed_ms: int = 1500

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)

        self._init_base_ui()
        self._init_content()

    def _init_base_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel(self.windowTitle())
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self._progress = QProgressBar()
        self._progress.setMaximum(self.total_steps)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setStyleSheet(
            f"QProgressBar {{ border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 4px; background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_primary']}; text-align: center; height: 18px; }}"
            f"QProgressBar::chunk {{ background-color: {ANIM_COLORS['accent_blue']}; "
            f"border-radius: 3px; }}"
        )
        layout.addWidget(self._progress)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_area, stretch=1)

        controls = QHBoxLayout()

        speed_lbl = QLabel("Hız:")
        speed_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        controls.addWidget(speed_lbl)

        self._speed_combo = QComboBox()
        self._speed_combo.addItems(list(_SPEED_MAP.keys()))
        self._speed_combo.setCurrentText("Normal")
        self._speed_combo.setStyleSheet(
            f"QComboBox {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_primary']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 4px; padding: 4px 8px; }}"
        )
        self._speed_combo.currentTextChanged.connect(self._on_speed_changed)
        controls.addWidget(self._speed_combo)

        controls.addStretch()

        btn_close = QPushButton("✕ Kapat")
        btn_close.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_secondary']}; border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 6px; padding: 6px 18px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_peach']}; "
            f"color: {ANIM_COLORS['bg_main']}; }}"
        )
        btn_close.clicked.connect(self.close)
        controls.addWidget(btn_close)

        layout.addLayout(controls)

    def _init_content(self) -> None:
        raise NotImplementedError

    def _render_step(self, step_idx: int) -> None:
        raise NotImplementedError

    def _show_match_result(self) -> None:
        raise NotImplementedError

    def _on_speed_changed(self, text: str) -> None:
        self.speed_ms = _SPEED_MAP[text]
        if self._timer.isActive():
            self._timer.setInterval(self.speed_ms)

    def _advance_step(self) -> None:
        self.current_step += 1
        if self.current_step >= self.total_steps:
            self._timer.stop()
            self._progress.setValue(self.total_steps)
            self._show_match_result()
            return
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self.current_step == 0:
            self._render_step(0)
            self._progress.setValue(1)
            self._timer.start(self.speed_ms)
