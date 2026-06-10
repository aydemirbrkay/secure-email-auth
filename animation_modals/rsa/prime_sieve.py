# animation_modals/rsa/prime_sieve.py
"""Adım 1 — Asal eleği widget'ı."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint,
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget,
    QGraphicsOpacityEffect, QSizePolicy,
)
from ..base import (
    CryptoAnimationWindow, ANIM_COLORS, get_animation_tick_ms,
    motion_effects_enabled,
)
from . import helpers as H

# ---------------------------------------------------------------------------
# 2) Adım 1 — Asal Eleği
# ---------------------------------------------------------------------------

class _PrimeSieveWidget(QWidget):
    """2..100 arası sayılar 10×10 grid; asallar yeşil; p=61, q=53 yanıp söner."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._blink = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._timer.stop()
        self._blink = False
        if motion_effects_enabled():
            self._timer.start(get_animation_tick_ms(700))

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        self._blink = not self._blink
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # NOT: 'H' modül takma adıdır (helpers); widget yüksekliği için
        # ayrı bir isim kullanılmalı, aksi halde H gölgelenir ve
        # H._is_prime / H._P / H._Q çağrıları AttributeError ile çöker.
        width_px, height_px = self.width(), self.height()
        margin = 8
        cols = 10
        rows = 10
        header_h = 22
        footer_h = 22
        avail_w = width_px - 2 * margin
        avail_h = height_px - 2 * margin - header_h - footer_h
        cell = max(20, min(42, min(avail_w // cols, avail_h // rows)))
        grid_w = cell * cols
        grid_h = cell * rows
        ox = (width_px - grid_w) // 2
        oy = margin + header_h

        # Üst başlık
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(
            QRect(0, 2, width_px, header_h),
            Qt.AlignmentFlag.AlignCenter,
            "1–100 arası sayılar  •  asallar yeşil  •  p ve q seçili",
        )

        for n in range(1, 101):
            i = n - 1
            r, c = divmod(i, cols)
            x = ox + c * cell
            y = oy + r * cell

            is_prime = H._is_prime(n)
            is_pq = (n == H._P or n == H._Q)

            if is_pq:
                # Yanıp sönen sarı çerçeve
                border_col = (
                    QColor(ANIM_COLORS["accent_yellow"])
                    if self._blink
                    else QColor(ANIM_COLORS["accent_peach"])
                )
                fill = QColor(ANIM_COLORS["accent_yellow"])
                fill.setAlpha(80 if self._blink else 140)
                p.setBrush(QBrush(fill))
                p.setPen(QPen(border_col, 2))
            elif is_prime:
                p.setBrush(QBrush(QColor(ANIM_COLORS["accent_green"] + "33")))
                p.setPen(QPen(QColor(ANIM_COLORS["accent_green"]), 1))
            else:
                p.setBrush(QBrush(QColor(ANIM_COLORS["bg_card"])))
                p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))

            p.drawRoundedRect(x + 2, y + 2, cell - 4, cell - 4, 4, 4)

            if is_pq:
                p.setPen(QColor(ANIM_COLORS["text_primary"]))
                p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            elif is_prime:
                p.setPen(QColor(ANIM_COLORS["accent_green"]))
                p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            else:
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                p.setFont(QFont("Courier New", 9))
            p.drawText(
                QRect(x, y, cell, cell),
                Qt.AlignmentFlag.AlignCenter,
                str(n),
            )

        # Açıklama
        p.setFont(QFont("Georgia", 10))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        legend_y = oy + grid_h + 10
        p.drawText(
            QRect(margin, legend_y, width_px - 2 * margin, 24),
            Qt.AlignmentFlag.AlignCenter,
            f"Seçilenler:  p = {H._P}    q = {H._Q}",
        )
        p.end()


