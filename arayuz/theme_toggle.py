"""
theme_toggle.py – Karanlık/Aydınlık tema geçiş butonu (ay / güneş).
"""
from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QPushButton

from arayuz.theme import COLORS, MANAGER


class ThemeToggle(QPushButton):
    """Yuvarlak, düz buton. Karanlıkta ay, aydınlıkta güneş çizer."""

    SIZE = 38

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self.clicked.connect(MANAGER.toggle)
        MANAGER.themeChanged.connect(lambda _m: self.update())

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.SIZE
        cx, cy = s / 2, s / 2

        bg = QColor(COLORS["bg_card"])
        border = QColor(COLORS["border_highlight"]) if self.underMouse() \
            else QColor(COLORS["border"])
        p.setBrush(bg)
        p.setPen(QPen(border, 2))
        p.drawEllipse(2, 2, s - 4, s - 4)

        icon = QColor(COLORS["accent_blue"])
        if MANAGER.mode == "dark":
            r = s * 0.26
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(icon)
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.setBrush(bg)
            off = r * 0.6
            p.drawEllipse(QPointF(cx + off, cy - off * 0.25), r, r)
        else:
            r = s * 0.16
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(icon)
            p.drawEllipse(QPointF(cx, cy), r, r)
            pen = QPen(icon, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            ri, ro = r * 1.7, r * 2.5
            for i in range(8):
                a = i * (math.pi / 4)
                p.drawLine(
                    QPointF(cx + math.cos(a) * ri, cy + math.sin(a) * ri),
                    QPointF(cx + math.cos(a) * ro, cy + math.sin(a) * ro),
                )
        p.end()

    def enterEvent(self, event):  # type: ignore[override]
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # type: ignore[override]
        self.update()
        super().leaveEvent(event)
