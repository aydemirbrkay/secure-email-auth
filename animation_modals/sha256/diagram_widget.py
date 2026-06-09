# animation_modals/sha256/diagram_widget.py
"""SHA-256 sıkıştırma fonksiyonu diyagramı (QPainter)."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS
from .constants import _REG_COLORS, _REG_LABELS

# ---------------------------------------------------------------------------
# Sıkıştırma fonksiyonu diyagramı (QPainter tabanlı widget)
# ---------------------------------------------------------------------------

class _SHA256DiagramWidget(QWidget):
    """
    Tek bir SHA-256 round'u için A-H sıkıştırma fonksiyonu diyagramını çizer.

    Gösterim:
      Üst satır  : 8 renkli kutu (A-H giriş değerleri)
      Orta bölge : T1 ve T2 hesaplama kutuları + K/W değerleri
      Alt satır  : 8 renkli kutu (A'-H' çıkış değerleri)
      Oklar      : A→T2, E→T1, D+T1→E', T1+T2→A'
    """

    # Animasyon aşamaları:
    # 0 = giriş registerları
    # 1 = A→T2 vurgusu
    # 2 = E→T1 vurgusu
    # 3 = T2→A' vurgusu
    # 4 = T1→E' vurgusu
    # 5 = tüm çıkış registerları (tamamlandı)
    _ANIM_PHASES = 6

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Içerik ~330 px sığar; min/max sabitleyerek pencere ne kadar büyük
        # olursa olsun widget büyümez, aşağıdaki ileri/geri butonları
        # daima ekranda kalır.
        self.setMinimumHeight(340)
        self.setMaximumHeight(360)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        # Varsayılan veri
        self._regs_in: list[str] = ["--------"] * 8
        self._regs_out: list[str] = ["--------"] * 8
        self._t1 = "--------"
        self._t2 = "--------"
        self._w = "--------"
        self._k = "--------"
        self._round_no = 0
        # Animasyon
        self._phase = self._ANIM_PHASES  # başlangıçta statik
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._next_phase)

    def set_data(
        self,
        regs_in: list[str],
        regs_out: list[str],
        t1: str,
        t2: str,
        w: str,
        k: str,
        round_no: int,
    ) -> None:
        self._regs_in = regs_in
        self._regs_out = regs_out
        self._t1 = t1
        self._t2 = t2
        self._w = w
        self._k = k
        self._round_no = round_no
        # Animasyonu başlat
        self._phase = 0
        self._anim_timer.start(380)
        self.update()

    def _next_phase(self) -> None:
        self._phase += 1
        if self._phase >= self._ANIM_PHASES:
            self._phase = self._ANIM_PHASES
            self._anim_timer.stop()
        self.update()

    # --- QPainter çizimi ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ph = self._phase  # mevcut animasyon aşaması
        W = self.width()
        box_w = max(60, min(80, (W - 80) // 8))
        box_h = 44
        gap = max(3, (W - 80 - 8 * box_w) // 7)
        total = 8 * box_w + 7 * gap
        ox = (W - total) // 2

        # top_y = 24: aşama etiketi (y=0-16) ile register kutuları (y=24+)
        # arasında 8 px boşluk kalır → 'D + T1 → E' etiketi ile A register
        # kutusunun üst kenarı artık çakışmaz.
        top_y = 24
        mid_y = top_y + box_h + 36
        bot_y = mid_y + 84

        font_lbl = QFont("Georgia", 9, QFont.Weight.Bold)
        font_val = QFont("Courier New", 8)
        font_mid = QFont("Courier New", 9)

        # Aşamaya göre vurgu belirleme
        # ph 0: sadece giriş
        # ph 1: A→T2 aktif
        # ph 2: E→T1 aktif
        # ph 3: T2→A' aktif
        # ph 4: T1→E' aktif
        # ph 5+: tümü göster
        highlight_a_in   = ph >= 1  # A giriş registerı vurgusu
        highlight_e_in   = ph >= 2
        highlight_t2     = ph >= 1
        highlight_t1     = ph >= 2
        highlight_a_out  = ph >= 3
        highlight_e_out  = ph >= 4
        show_out         = ph >= 3

        # ── Üst satır: giriş registerları ──
        # A ve E aşamaya göre daha parlak gösterilir
        custom_in_colors = list(_REG_COLORS)
        if highlight_a_in:
            custom_in_colors[0] = ANIM_COLORS["accent_blue"]  # A parlar
        if highlight_e_in:
            custom_in_colors[4] = ANIM_COLORS["accent_yellow"]  # E parlar
        self._draw_register_row(
            p, self._regs_in, ox, top_y, box_w, box_h, gap,
            font_lbl, font_val, suffix="",
            custom_colors=custom_in_colors,
        )

        # ── T2 kutusu ──
        t2_x = ox
        t2_w = int(total * 0.38)
        t1_x = ox + total - int(total * 0.52)
        t1_w = int(total * 0.52)

        t2_border = QColor(ANIM_COLORS["accent_mauve"])
        t2_fill = QColor(ANIM_COLORS["hl_mauve"]) if highlight_t2 else QColor(ANIM_COLORS["bg_card"])
        self._draw_box(p, t2_x, mid_y, t2_w, 72, t2_fill, t2_border)
        p.setFont(font_mid)
        p.setPen(t2_border)
        p.drawText(QRect(t2_x + 4, mid_y + 4, t2_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, "T2 = Σ0(A) + Maj(A,B,C)")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t2_x + 4, mid_y + 26, t2_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, f"= {self._t2}" if ph >= 1 else "= ...")

        # ── T1 kutusu ──
        t1_border = QColor(ANIM_COLORS["accent_yellow"])
        t1_fill = QColor(ANIM_COLORS["hl_yellow"]) if highlight_t1 else QColor(ANIM_COLORS["bg_card"])
        self._draw_box(p, t1_x, mid_y, t1_w, 72, t1_fill, t1_border)
        p.setPen(t1_border)
        p.drawText(QRect(t1_x + 4, mid_y + 4, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   "T1 = Σ1(E) + Ch(E,F,G) + H + K + W")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t1_x + 4, mid_y + 26, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, f"= {self._t1}" if ph >= 2 else "= ...")
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(t1_x + 4, mid_y + 48, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   f"K={self._k[:6]}  W={self._w[:6]}")

        # ── Oklar ──
        a_arrow_w = 3 if highlight_a_in else 1
        e_arrow_w = 3 if highlight_e_in else 1

        # A → T2
        pen = QPen(QColor(ANIM_COLORS["accent_blue"]), a_arrow_w)
        p.setPen(pen)
        a_cx = ox + box_w // 2
        p.drawLine(a_cx, top_y + box_h, a_cx, top_y + box_h + 20)
        p.drawLine(a_cx, top_y + box_h + 20, t2_x + t2_w // 2, mid_y)
        self._arrowhead(p, t2_x + t2_w // 2, mid_y)

        # E → T1
        pen = QPen(QColor(ANIM_COLORS["accent_yellow"]), e_arrow_w)
        p.setPen(pen)
        e_cx = ox + 4 * (box_w + gap) + box_w // 2
        p.drawLine(e_cx, top_y + box_h, e_cx, top_y + box_h + 20)
        p.drawLine(e_cx, top_y + box_h + 20, t1_x + t1_w // 2, mid_y)
        self._arrowhead(p, t1_x + t1_w // 2, mid_y)

        # T2 → A'
        t2a_w = 3 if highlight_a_out else 1
        pen2 = QPen(QColor(ANIM_COLORS["accent_mauve"]), t2a_w)
        p.setPen(pen2)
        a_out_cx = ox + box_w // 2
        p.drawLine(t2_x + t2_w // 2, mid_y + 72, a_out_cx, bot_y)
        self._arrowhead(p, a_out_cx, bot_y)

        # T1 → E'
        t1e_w = 3 if highlight_e_out else 1
        pen3 = QPen(QColor(ANIM_COLORS["accent_yellow"]), t1e_w)
        p.setPen(pen3)
        e_out_cx = ox + 4 * (box_w + gap) + box_w // 2
        p.drawLine(t1_x + t1_w // 2, mid_y + 72, e_out_cx, bot_y)
        self._arrowhead(p, e_out_cx, bot_y)

        # D → E' (kesikli)
        pen4 = QPen(QColor(ANIM_COLORS["accent_green"]), 1)
        pen4.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen4)
        d_cx = ox + 3 * (box_w + gap) + box_w // 2
        p.drawLine(d_cx, top_y + box_h, d_cx, bot_y)
        p.drawLine(d_cx, bot_y, e_out_cx, bot_y)
        self._arrowhead_right(p, e_out_cx, bot_y)
        p.setFont(QFont("IBM Plex Sans", 7))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(e_out_cx - box_w // 2 - 2, bot_y, box_w // 2, box_h // 2),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "+D")

        # ── Alt satır: çıkış registerları ──
        custom_out_colors = list(_REG_COLORS)
        if highlight_a_out:
            custom_out_colors[0] = ANIM_COLORS["accent_mauve"]  # A' vurgusu
        if highlight_e_out:
            custom_out_colors[4] = ANIM_COLORS["accent_yellow"]  # E' vurgusu
        out_vals = self._regs_out if show_out else ["--------"] * 8
        self._draw_register_row(
            p, out_vals, ox, bot_y, box_w, box_h, gap,
            font_lbl, font_val, suffix="'",
            custom_colors=custom_out_colors,
        )

        # Kaydırma açıklaması (legend)
        p.setFont(QFont("IBM Plex Sans", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        legend_y = bot_y + box_h + 6
        p.drawText(QRect(ox, legend_y, total, 14),
                   Qt.AlignmentFlag.AlignCenter,
                   "B'=A  C'=B  D'=C  F'=E  G'=F  H'=G  (diğerleri kaydırılır)")

        # Aşama etiketi (sağ alt)
        phase_labels = [
            "Giriş registerları →",
            "A → T2 (Σ0 + Maj) ►",
            "E → T1 (Σ1 + Ch + H + K + W) ►",
            "T2 + T1 → A' ►",
            "D + T1 → E' ►",
            "✓ Round tamamlandı",
        ]
        p.setPen(QColor(ANIM_COLORS["accent_blue"] if ph < 5 else ANIM_COLORS["accent_green"]))
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        lbl_idx = min(ph, len(phase_labels) - 1)
        p.drawText(QRect(0, 0, W, 16), Qt.AlignmentFlag.AlignLeft,
                   f"  {phase_labels[lbl_idx]}")

        # Round numarası (sağ)
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.setFont(QFont("IBM Plex Sans", 10))
        p.drawText(QRect(0, 0, W, 14), Qt.AlignmentFlag.AlignRight,
                   f"Round {self._round_no}/64  ")

        p.end()

    # --- Yardımcılar ---

    def _draw_register_row(
        self, p: QPainter,
        values: list[str], ox: int, y: int,
        box_w: int, box_h: int, gap: int,
        font_lbl: QFont, font_val: QFont,
        suffix: str,
        custom_colors: list[str] | None = None,
    ) -> None:
        colors = custom_colors if custom_colors is not None else _REG_COLORS
        for i, (lbl, val, col) in enumerate(
            zip(_REG_LABELS, values, colors)
        ):
            x = ox + i * (box_w + gap)
            self._draw_box(p, x, y, box_w, box_h,
                           QColor(col + "33"), QColor(col))
            p.setFont(font_lbl)
            p.setPen(QColor(col))
            p.drawText(QRect(x, y + 2, box_w, 16),
                       Qt.AlignmentFlag.AlignCenter, lbl + suffix)
            p.setFont(font_val)
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x + 2, y + 20, box_w - 4, 20),
                       Qt.AlignmentFlag.AlignCenter, val[:8])

    @staticmethod
    def _draw_box(
        p: QPainter, x: int, y: int, w: int, h: int,
        fill: QColor, border: QColor,
    ) -> None:
        p.setBrush(QBrush(fill))
        pen = QPen(border, 1)
        p.setPen(pen)
        p.drawRoundedRect(x, y, w, h, 4, 4)

    @staticmethod
    def _arrowhead(p: QPainter, x: int, y: int, size: int = 6) -> None:
        """Küçük içi dolu ok ucu."""
        pts = QPolygon([
            QPoint(x, y),
            QPoint(x - size, y - size * 2),
            QPoint(x + size, y - size * 2),
        ])
        p.setBrush(QBrush(p.pen().color()))
        p.drawPolygon(pts)

    @staticmethod
    def _arrowhead_right(p: QPainter, x: int, y: int, size: int = 6) -> None:
        """Sağa bakan ok ucu."""
        pts = QPolygon([
            QPoint(x, y),
            QPoint(x - size * 2, y - size),
            QPoint(x - size * 2, y + size),
        ])
        p.setBrush(QBrush(p.pen().color()))
        p.drawPolygon(pts)


