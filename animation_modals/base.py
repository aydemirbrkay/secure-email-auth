# animation_modals/base.py
"""
CryptoAnimationWindow — Tüm animasyon pencerelerinin taban sınıfı.
QWidget subclass. on_close=None (varsayılan): bağımsız pencere olarak açılır, ekranın
%85'ine yeniden boyutlandırılır. on_close verilirse: gömülü widget olarak davranır
(pencere bayrağı ve boyut ayarı atlanır).
manual_mode=True: kullanıcı tıklayarak ilerler (RSA, SHA, AES roundları).
manual_mode=False: QTimer otomatik oynatır (AES intro).
"""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
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

_BTN_STYLE = (
    f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
    f"color: {ANIM_COLORS['bg_main']}; border: none; "
    f"border-radius: 6px; padding: 8px 22px; font-weight: bold; font-size: 13px; }}"
    f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
    f"QPushButton:disabled {{ background: {ANIM_COLORS['bg_card']}; "
    f"color: {ANIM_COLORS['text_muted']}; }}"
)

_CLOSE_STYLE = (
    f"QPushButton {{ background: {ANIM_COLORS['bg_card']}; "
    f"color: {ANIM_COLORS['text_secondary']}; border: 1px solid {ANIM_COLORS['border']}; "
    f"border-radius: 6px; padding: 8px 18px; font-weight: bold; }}"
    f"QPushButton:hover {{ background: {ANIM_COLORS['accent_peach']}; "
    f"color: {ANIM_COLORS['bg_main']}; }}"
)


class CryptoAnimationWindow(QWidget):
    """
    Ortak animasyon penceresi taban sınıfı.

    Alt sınıflar şunları override eder:
      _init_content()       → content_area'ya widget ekler
      _render_step(idx)     → idx numaralı adımı gösterir
      _show_match_result()  → son eşleşme ekranını gösterir

    manual_mode=True ise kullanıcı ◀ Geri / İleri ▶ butonlarıyla ilerler.
    manual_mode=False ise QTimer otomatik oynatır (hız seçici görünür).
    """

    def __init__(
        self,
        title: str,
        total_steps: int,
        manual_mode: bool = False,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_close = on_close

        # Standalone modda bağımsız pencere olarak aç
        if on_close is None:
            self.setWindowFlags(Qt.WindowType.Window)
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setWindowTitle(title)
        self.setStyleSheet(
            f"background-color: {ANIM_COLORS['bg_main']}; "
            f"color: {ANIM_COLORS['text_primary']};"
        )

        # Ekranın %85'i kadar boyutlandır — sadece standalone modda
        if on_close is None:
            screen = QApplication.primaryScreen()
            if screen:
                g = screen.availableGeometry()
                self.resize(int(g.width() * 0.82), int(g.height() * 0.85))
            else:
                self.resize(1280, 860)

        self.manual_mode: bool = manual_mode
        self.current_step: int = 0
        self.total_steps: int = total_steps
        self.speed_ms: int = 1500

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)

        self._init_base_ui()
        self._init_content()

    # ------------------------------------------------------------------
    # UI kurulumu
    # ------------------------------------------------------------------

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
        controls.setSpacing(8)

        if self.manual_mode:
            self._btn_prev = QPushButton("◀  Geri")
            self._btn_prev.setStyleSheet(_BTN_STYLE)
            self._btn_prev.setEnabled(False)
            self._btn_prev.clicked.connect(self._go_back)
            controls.addWidget(self._btn_prev)

            self._btn_next = QPushButton("İleri  ▶")
            self._btn_next.setStyleSheet(_BTN_STYLE)
            self._btn_next.clicked.connect(self._advance_step)
            controls.addWidget(self._btn_next)
        else:
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

        btn_close = QPushButton("✕  Kapat")
        btn_close.setStyleSheet(_CLOSE_STYLE)
        if self._on_close is not None:
            btn_close.clicked.connect(self._on_close)
        else:
            btn_close.clicked.connect(self.close)
        controls.addWidget(btn_close)

        layout.addLayout(controls)

    # ------------------------------------------------------------------
    # Alt sınıf arayüzü
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        raise NotImplementedError

    def _render_step(self, step_idx: int) -> None:
        raise NotImplementedError

    def _show_match_result(self) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Navigasyon
    # ------------------------------------------------------------------

    def _on_speed_changed(self, text: str) -> None:
        self.speed_ms = _SPEED_MAP[text]
        if self._timer.isActive():
            self._timer.setInterval(self.speed_ms)

    def _go_back(self) -> None:
        """Manuel mod: bir önceki adıma dön."""
        if self.current_step <= 0:
            return
        self.current_step -= 1
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)
        self._btn_prev.setEnabled(self.current_step > 0)
        self._btn_next.setEnabled(True)
        self._btn_next.setText("İleri  ▶")

    def _advance_step(self) -> None:
        """Bir sonraki adıma geç (manuel veya otomatik)."""
        if self.manual_mode:
            if self.current_step >= self.total_steps - 1:
                self._progress.setValue(self.total_steps)
                self._show_match_result()
                self._btn_next.setEnabled(False)
                self._btn_next.setText("✅  Tamamlandı")
                return
            self.current_step += 1
            self._render_step(self.current_step)
            self._progress.setValue(self.current_step + 1)
            if hasattr(self, "_btn_prev"):
                self._btn_prev.setEnabled(True)
        else:
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
            if not self.manual_mode:
                self._timer.start(self.speed_ms)
