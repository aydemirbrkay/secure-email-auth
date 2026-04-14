"""
toast.py – Doğrulama Bildirimi Widget
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from theme import COLORS


class VerificationToast(QWidget):
    """
    Doğrulama sonucunu gösteren açılır bildirim penceresi.
    8 saniye sonra otomatik kapanır; 'Kapat' butonu ile erken kapatılabilir.
    """

    _LIFE_SECS = 8

    def __init__(self, is_valid: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._secs = self._LIFE_SECS

        color = COLORS["accent_green"] if is_valid else COLORS["accent_red"]
        icon  = "✅" if is_valid else "❌"
        title = "DOĞRULAMA BAŞARILI" if is_valid else "DOĞRULAMA BAŞARISIZ"

        self.setStyleSheet(
            f"QWidget {{ background: {COLORS['bg_panel']}; "
            f"border: 2px solid {color}; border-radius: 12px; }}"
        )
        self.setFixedWidth(440)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {color}; border: none;")
        title_lbl.setWordWrap(True)
        hdr.addWidget(title_lbl, stretch=1)
        lay.addLayout(hdr)

        sep = QLabel()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background-color: {color}; border: none;")
        lay.addWidget(sep)

        if is_valid:
            items = [
                (COLORS["accent_green"], "✓  Kimlik Doğrulama  (Authentication)"),
                (COLORS["accent_green"], "✓  Mesaj Bütünlüğü   (Integrity)"),
                (COLORS["accent_green"], "✓  Gizlilik           (Confidentiality)"),
            ]
        else:
            items = [
                (COLORS["accent_red"],
                 "✗  İmza doğrulanamadı\n"
                 "    Mesaj değiştirilmiş veya gönderici kimliği sahte olabilir!"),
            ]
        for c, text in items:
            lbl = QLabel(text)
            lbl.setFont(QFont("IBM Plex Sans", 12))
            lbl.setStyleSheet(f"color: {c}; border: none;")
            lbl.setWordWrap(True)
            lay.addWidget(lbl)

        lay.addSpacing(4)

        self._close_btn = QPushButton(f"✕  Kapat  ({self._secs}s)")
        self._close_btn.setStyleSheet(
            f"QPushButton {{ background: {color}22; border: 2px solid {color}; "
            f"border-radius: 6px; color: {color}; font-weight: bold; "
            f"font-size: 12px; padding: 8px 24px; }}"
            f"QPushButton:hover {{ background: {color}55; }}"
        )
        self._close_btn.clicked.connect(self.close)
        lay.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.adjustSize()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self) -> None:
        self._secs -= 1
        if self._secs <= 0:
            self.close()
        else:
            self._close_btn.setText(f"✕  Kapat  ({self._secs}s)")

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        par = self.parent()
        if par:
            pg = par.geometry()
            sg = self.frameGeometry()
            self.move(
                pg.x() + (pg.width()  - sg.width())  // 2,
                pg.y() + (pg.height() - sg.height()) // 2,
            )
