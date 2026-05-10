# animation_modals/sha256_animation.py
"""
SHA256AnimationWindow — SHA-256 hash sürecini görselleştirir.
• Her 512-bit blok için A-H register diyagramı (QPainter)
• Blok zinciri: Blok kartları okla birbirine bağlı
• Manuel navigasyon: kullanıcı ◀ / ▶ ile ilerler
"""
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
from .base import CryptoAnimationWindow, ANIM_COLORS
from .sha256_pure import sha256_steps

_SNAPS_PER_BLOCK = 9  # rounds 1,9,17,25,33,41,49,57,64

# Renk eşlemesi — her register farklı renk
_REG_COLORS = [
    "#3B6FA0",  # A — blue
    "#7B5EA7",  # B — mauve
    "#4E8B60",  # C — green
    "#B8860B",  # D — yellow
    "#B87333",  # E — peach
    "#3D8B80",  # F — teal
    "#B94A4A",  # G — red
    "#2E86AB",  # H — sky
]
_REG_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H"]


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
        self.setMinimumHeight(360)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
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

        top_y = 12
        mid_y = top_y + box_h + 50
        bot_y = mid_y + 90

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
        t2_fill = QColor("#3D2F56") if highlight_t2 else QColor("#536070")
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
        t1_fill = QColor("#3D3119") if highlight_t1 else QColor("#536070")
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


# ---------------------------------------------------------------------------
# Register demo widget — intro için SHA-256 sıkıştırma fonksiyonunu simüle eder
# ---------------------------------------------------------------------------

class _RegisterDemoWidget(QWidget):
    """
    SHA-256 intro ekranında gösterilen canlı A-H register animasyonu.
    72-tick döngü (120ms):
      0-23  : Giriş registerları sırayla parlar
      24-47 : T2 ve T1 kutuları sırayla canlanır
      48-71 : Çıkış registerları birer birer belirir
    """

    _PHASE_NAMES = [
        "Giriş Değerleri  (A–H)",
        "T1 / T2  Hesaplama",
        "Yeni Register Değerleri  (A'–H')",
    ]
    _DEMO_IN  = ["6a09e667", "bb67ae85", "3c6ef372", "a54ff53a",
                 "510e527f", "9b05688c", "1f83d9ab", "5be0cd19"]
    _DEMO_OUT = ["5d6aebb1", "9e7c3f82", "a1b4c5d6", "7f8e9a0b",
                 "4c3d2e1f", "8b7a6c5d", "2f1e0d9c", "b8a79685"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tick = 0
        self._round_no = 1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(120)
        self.setMinimumSize(160, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _step(self) -> None:
        self._tick += 1
        if (self._tick % 72) == 71:
            self._round_no = (self._round_no % 64) + 1
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        label_h = 22
        margin = 4

        phase = (self._tick // 24) % 3
        sub   = self._tick % 24

        # Boyutlar — dar alana uyum sağlar
        avail_w = W - 2 * margin
        box_w = max(18, min(56, avail_w // 8 - 2))
        gap   = max(1, (avail_w - 8 * box_w) // 7)
        box_h = max(26, min(40, H // 6))
        total_w = 8 * box_w + 7 * gap
        ox = (W - total_w) // 2

        top_y = label_h + 4
        mid_h = max(36, min(48, H // 5))
        mid_y = top_y + box_h + 10
        bot_y = mid_y + mid_h + 8

        # Dar genişlikte küçük fontlar
        compact = box_w < 34
        font_lbl   = QFont("Georgia", 6 if compact else 8, QFont.Weight.Bold)
        font_val   = QFont("Courier New", 5 if compact else 7)
        font_mid   = QFont("Courier New", 6 if compact else 8)
        font_phase = QFont("Georgia", 7 if compact else 9, QFont.Weight.Bold)

        # Phase label
        phase_color = [
            ANIM_COLORS["accent_blue"],
            ANIM_COLORS["accent_yellow"],
            ANIM_COLORS["accent_green"],
        ][phase]
        p.setFont(font_phase)
        p.setPen(QColor(phase_color))
        p.drawText(QRect(0, 2, W, label_h),
                   Qt.AlignmentFlag.AlignCenter,
                   f"Round {self._round_no}/64  —  {self._PHASE_NAMES[phase]}")

        # ── Üst satır: giriş registerları ──
        lit_in = sub // 3 if phase == 0 else 8
        for i in range(8):
            x   = ox + i * (box_w + gap)
            col = _REG_COLORS[i]
            active = (i == lit_in) if phase == 0 else False
            fill   = QColor(col + "55") if active else QColor(col + "22")
            border = QColor(col) if (phase == 0 or phase == 1) else QColor(ANIM_COLORS["border"])
            p.setBrush(QBrush(fill))
            p.setPen(QPen(border, 1))
            p.drawRoundedRect(x, top_y, box_w, box_h, 4, 4)
            p.setFont(font_lbl)
            p.setPen(QColor(col if phase <= 1 else ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x, top_y + 1, box_w, box_h // 2),
                       Qt.AlignmentFlag.AlignCenter, _REG_LABELS[i])
            p.setFont(font_val)
            p.setPen(QColor(ANIM_COLORS["text_primary"] if phase <= 1 else ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x, top_y + box_h // 2, box_w, box_h // 2),
                       Qt.AlignmentFlag.AlignCenter, self._DEMO_IN[i][:max(4, box_w // 6)])

        # ── Orta: T2 ve T1 kutuları ──
        t2_w = int(total_w * 0.36)
        t1_w = int(total_w * 0.52)
        t2_x = ox
        t1_x = ox + total_w - t1_w
        t2_lit = (phase == 1 and sub < 12)
        t1_lit = (phase == 1 and sub >= 12)

        t2_fill   = QColor("#3D2F56" if t2_lit else "#536070")
        t2_border = QColor(ANIM_COLORS["accent_mauve"] if t2_lit else ANIM_COLORS["border"])
        p.setBrush(QBrush(t2_fill))
        p.setPen(QPen(t2_border, 2 if t2_lit else 1))
        p.drawRoundedRect(t2_x, mid_y, t2_w, mid_h, 4, 4)
        p.setFont(font_mid)
        p.setPen(t2_border)
        p.drawText(QRect(t2_x + 2, mid_y + 2, t2_w - 4, mid_h // 2),
                   Qt.AlignmentFlag.AlignCenter, "Σ0(A) + Maj(A,.." if compact else "T2 = Σ0(A) + Maj(A,B,C)")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t2_x + 2, mid_y + mid_h // 2, t2_w - 4, mid_h // 2),
                   Qt.AlignmentFlag.AlignCenter, "a1b2c3d4" if t2_lit else "...")

        t1_fill   = QColor("#3D3119" if t1_lit else "#536070")
        t1_border = QColor(ANIM_COLORS["accent_yellow"] if t1_lit else ANIM_COLORS["border"])
        p.setBrush(QBrush(t1_fill))
        p.setPen(QPen(t1_border, 2 if t1_lit else 1))
        p.drawRoundedRect(t1_x, mid_y, t1_w, mid_h, 4, 4)
        p.setPen(t1_border)
        p.drawText(QRect(t1_x + 2, mid_y + 2, t1_w - 4, mid_h // 2),
                   Qt.AlignmentFlag.AlignCenter, "Σ1(E) + Ch(E,F,G) + .." if compact else "T1 = Σ1(E) + Ch(E,F,G) + H + K + W")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t1_x + 2, mid_y + mid_h // 2, t1_w - 4, mid_h // 2),
                   Qt.AlignmentFlag.AlignCenter, "e5f6a7b8" if t1_lit else "...")

        # ── Alt satır: çıkış registerları ──
        revealed = sub // 3 if phase == 2 else (-1 if phase < 2 else 8)
        for i in range(8):
            x   = ox + i * (box_w + gap)
            col = _REG_COLORS[i]
            shown = (phase == 2 and i <= revealed)
            active = (phase == 2 and i == revealed)
            fill   = QColor(col + "44") if active else (QColor(ANIM_COLORS["accent_green"] + "22") if shown else QColor(col + "0a"))
            border = QColor(ANIM_COLORS["accent_green"] if shown else ANIM_COLORS["border"])
            p.setBrush(QBrush(fill))
            p.setPen(QPen(border, 1))
            p.drawRoundedRect(x, bot_y, box_w, box_h, 4, 4)
            p.setFont(font_lbl)
            p.setPen(QColor(ANIM_COLORS["accent_green"] if shown else ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x, bot_y + 1, box_w, box_h // 2),
                       Qt.AlignmentFlag.AlignCenter, _REG_LABELS[i] + "'")
            p.setFont(font_val)
            raw_val = self._DEMO_OUT[i] if shown else "----"
            val = raw_val[:max(4, box_w // 6)]
            p.setPen(QColor(ANIM_COLORS["text_primary"] if shown else ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x, bot_y + box_h // 2, box_w, box_h // 2),
                       Qt.AlignmentFlag.AlignCenter, val)

        p.end()


# ---------------------------------------------------------------------------
# SHA-256 Ön Tanıtma Widget'ı
# ---------------------------------------------------------------------------

class _SHA256IntroWidget(QWidget):
    """
    SHA-256 ön tanıtma widget'ı.
    Sol  : canlı A-H register animasyonu (_RegisterDemoWidget)
    Sağ  : SHA-256 süreç akış şeması (kademeli görünüm, 500ms/adım)
    Alt  : "Görselleştirmeyi Başlat" butonu
    """

    def __init__(self, on_start: "callable", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_start = on_start
        self._phase = 0
        self._reveal_widgets: list[QWidget] = []
        self._reveal_timer = QTimer(self)
        self._reveal_timer.timeout.connect(self._reveal_next)
        self._init_ui()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 6, 12, 6)
        main.setSpacing(4)

        # Başlık
        title = QLabel("SHA-256  Hash Algoritması")
        title.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(title)

        # ── Yatay bölüm: sol=register demo, sağ=akış şeması ──
        h_row = QHBoxLayout()
        h_row.setSpacing(12)
        main.addLayout(h_row)

        # Sol: register animasyonu
        left_frame = QFrame()
        left_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 10px; }}"
        )
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(8, 6, 8, 6)
        left_lay.setSpacing(2)
        demo_lbl = QLabel("Sıkıştırma Fonksiyonu Önizlemesi")
        demo_lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        demo_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        demo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_lay.addWidget(demo_lbl)
        self._reg_demo = _RegisterDemoWidget()
        left_lay.addWidget(self._reg_demo, stretch=1)
        h_row.addWidget(left_frame, stretch=2)

        # Sağ: akış şeması — dış _anim_scroll zaten kaydırma sağlar, iç scroll gereksiz
        right_container = QWidget()
        right_container_lay = QVBoxLayout(right_container)
        right_container_lay.setContentsMargins(0, 0, 0, 0)
        right_container_lay.setSpacing(4)
        h_row.addWidget(right_container, stretch=3)

        right_lay = right_container_lay
        right_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Akış şeması kutular + oklar
        flow_items = [
            ("plain",  "Mesaj Girişi",                          ANIM_COLORS["text_secondary"],  None),
            ("arrow",  None, None, None),
            ("detail", "Padding  (512-bit katı)",                ANIM_COLORS["accent_peach"],
             ["→  '1' biti eklenir",
              "→  '0' bitleriyle 512-bit katına tamamlanır",
              "→  Sonuna 64-bit mesaj uzunluğu yazılır"]),
            ("arrow",  None, None, None),
            ("detail", "Blok Bölme  (N × 512-bit)",              ANIM_COLORS["accent_blue"],
             ["→  Her blok 64 bayt / 512 bit",
              "→  16 adet 32-bit kelime  (W0 – W15)"]),
            ("arrow",  None, None, None),
            ("detail", "Sıkıştırma  (64 Round / Blok)",          ANIM_COLORS["accent_mauve"],
             ["→  Çalışma değişkenleri: A, B, C, D, E, F, G, H",
              "→  T1 = Σ1(E) + Ch(E,F,G) + H + Kᵢ + Wᵢ",
              "→  T2 = Σ0(A) + Maj(A,B,C)"]),
            ("arrow",  None, None, None),
            ("plain",  "H Değerlerini Güncelle",                 ANIM_COLORS["accent_yellow"],   None),
            ("arrow",  None, None, None),
            ("plain",  "256-bit SHA-256 Hash",                   ANIM_COLORS["accent_green"],    None),
        ]

        for kind, text, color, subs in flow_items:
            if kind == "arrow":
                w = self._make_arrow()
            elif kind == "plain":
                w = self._make_box(text, color)
            else:
                w = self._make_detail_box(text, subs, color)
            right_lay.addWidget(w)
            w.setVisible(False)
            self._reveal_widgets.append(w)

        # Başla butonu — scroll area dışında, her zaman görünür konumda
        self._btn_start = QPushButton("Görselleştirmeyi Başlat")
        self._btn_start.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
        self._btn_start.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; "
            f"border-radius: 6px; padding: 6px 18px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        self._btn_start.setVisible(False)
        self._btn_start.clicked.connect(self._on_start)
        right_container_lay.addWidget(self._btn_start, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._reveal_widgets.append(self._btn_start)

    @staticmethod
    def _make_box(text: str, color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 5, 8, 5)
        lbl = QLabel(text)
        lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        return f

    @staticmethod
    def _make_detail_box(title: str, items: list[str], color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 5, 8, 5)
        lay.setSpacing(2)
        t = QLabel(title)
        t.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {color}; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setWordWrap(True)
        lay.addWidget(t)
        for item in items:
            o = QLabel(item)
            o.setFont(QFont("Segoe UI", 9))
            o.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']}; border: none;")
            o.setWordWrap(True)
            lay.addWidget(o)
        return f

    @staticmethod
    def _make_arrow() -> QLabel:
        lbl = QLabel("⬇")
        lbl.setFont(QFont("Segoe UI", 12))
        lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(16)
        return lbl

    def start(self) -> None:
        self._reveal_timer.start(500)

    def _reveal_next(self) -> None:
        if self._phase >= len(self._reveal_widgets):
            self._reveal_timer.stop()
            return
        self._reveal_widgets[self._phase].setVisible(True)
        self._phase += 1


# ---------------------------------------------------------------------------
# SHA-256 Animasyon Penceresi
# ---------------------------------------------------------------------------

class SHA256AnimationWindow(CryptoAnimationWindow):
    """
    SHA-256 animasyon penceresi.

    Adımlar:
      0        : Padding görselleştirmesi
      1        : Mesaj genişletme (W_i) sayfası
      2..9*N+1 : Her 512-bit blok için kompresyon diyagramı (9 snapshot: round 1,9,17,25,33,41,49,57,64)
      son adım : Hash eşleşmesi (_show_match_result)

    Parametreler:
      message      : kullanıcının orijinal mesaj metni
      expected_hash: crypto_core'un ürettiği hex hash
    """

    def __init__(
        self,
        message: str,
        expected_hash: str,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self._message = message
        self._expected_hash = expected_hash
        self._data = sha256_steps(message.encode("utf-8"))

        # Adım 0: padding
        # Adım 1: W_i mesaj genişletme
        # Adım 2..9*N+1: her blok için 9 snapshot (round 1,9,17,25,33,41,49,57,64)
        # Son adım: eşleşme (_show_match_result)
        snaps = self._data["round_snapshots"]
        total = 2 + len(snaps)   # padding + W_i genişletme + all snapshots
        super().__init__(
            "SHA-256 Hash Animasyonu",
            total,
            manual_mode=True,
            on_close=on_close,
        )
        self._snaps = snaps

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        from PyQt6.QtWidgets import QStackedWidget

        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Ön tanıtma
        self._page_intro = _SHA256IntroWidget(on_start=self._switch_to_content)
        self._stack.addWidget(self._page_intro)

        # Sayfa 1 — Padding
        self._page_padding = self._make_padding_page()
        self._stack.addWidget(self._page_padding)

        # Sayfa 1b — Mesaj Genişletme (W_i)
        self._page_wexpand = self._make_wexpand_page()
        self._stack.addWidget(self._page_wexpand)

        # Sayfa 2 — Kompresyon diyagramı (tüm snapshot'lar için tek sayfa, veri güncellenir)
        self._page_diagram = self._make_diagram_page()
        self._stack.addWidget(self._page_diagram)

        # Sayfa 3 — Eşleşme
        self._page_match = self._make_match_page()
        self._stack.addWidget(self._page_match)

        # Intro animasyonunu başlat
        self._page_intro.start()

    def _make_padding_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Adım 1 — Padding ve Blok Yapısı")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        d = self._data
        bc = d["blocks_count"]
        preview = d["binary_preview"]
        padded_len = d["padded_len"]

        info = QLabel(
            f"Mesaj: \"{self._message[:50]}\"\n\n"
            f"İlk 8 byte (binary):\n  {preview}\n\n"
            f"Padding işlemleri:\n"
            f"  1. '1' biti eklendi\n"
            f"  2. '0' bitleri ile 512'nin katına tamamlandı\n"
            f"  3. Sonuna 64-bit mesaj uzunluğu eklendi\n\n"
            f"Sonuç: {padded_len} byte → {bc} adet 512-bit blok\n\n"
            + "\n".join(
                f"  ▪ Blok {i+1}:  byte {i*64} – {(i+1)*64-1}"
                for i in range(bc)
            )
        )
        info.setFont(QFont("Courier New", 10))
        info.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    def _make_wexpand_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Adım 2 — Mesaj Genişletme (Message Schedule)")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_mauve']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        d = self._data
        exp = d.get("w_expansion") or []

        lines = [
            "W[0..15]:  Blok'tan doğrudan (mesajın 16 × 32-bit kelimesi)",
            "",
            "W[16..63]: σ1(W[i-2]) + W[i-7] + σ0(W[i-15]) + W[i-16]  (mod 2³²)",
            "",
            "  σ0(x) = ROTR(x,7)  ⊕  ROTR(x,18)  ⊕  SHR(x,3)",
            "  σ1(x) = ROTR(x,17) ⊕  ROTR(x,19)  ⊕  SHR(x,10)",
            "",
            "Gösterim: σ0(W[i-15]=operand) → sonuç   (σ1 için de aynı)",
            "─" * 72,
            "Örnek — İlk blok W[16..31]:",
            "",
        ]
        for entry in exp:
            i = entry["i"]
            lines.append(
                f"  W[{i:2d}] = W[{i-16:2d}]({entry['w_i16']})"
                f" + σ0(W[{i-15:2d}]={entry['w_i15']})→{entry['s0']}"
                f" + W[{i-7:2d}]({entry['w_i7']})"
                f" + σ1(W[{i-2:2d}]={entry['w_i2']})→{entry['s1']}"
                f" = {entry['result']}"
            )
        lines += [
            "",
            "Not: σ0(…) ve σ1(…) içindeki değer fonksiyonun GİRDİSİDİR;",
            "ok (→) işaretinden sonraki 32-bit kelime ise fonksiyonun ÇIKTISIDIR.",
            "",
            "64 round boyunca Compression fonksiyonu W[0..63] kullanır.",
        ]

        info = QLabel("\n".join(lines))
        info.setFont(QFont("Courier New", 9))
        info.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.addWidget(info)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    def _make_diagram_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)

        self._diag_title = QLabel()
        self._diag_title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        self._diag_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._diag_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._diag_title)

        self._diag_widget = _SHA256DiagramWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._diag_widget)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll, stretch=1)

        # Hash zinciri göstergesi (alt)
        self._chain_lbl = QLabel()
        self._chain_lbl.setFont(QFont("Courier New", 10))
        self._chain_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._chain_lbl.setWordWrap(True)
        self._chain_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._chain_lbl)
        return w

    def _make_match_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        self._match_lbl = QLabel()
        self._match_lbl.setFont(QFont("Courier New", 12))
        self._match_lbl.setWordWrap(True)
        self._match_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(self._match_lbl)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    # Adım render'ı
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if step_idx == 0:
            self._stack.setCurrentWidget(self._page_padding)
            return
        if step_idx == 1:
            self._stack.setCurrentWidget(self._page_wexpand)
            return

        # step_idx 2..len(snaps)+1 → snapshot[step_idx - 2]
        snap_idx = step_idx - 2
        if snap_idx >= len(self._snaps):
            return

        snap = self._snaps[snap_idx]
        self._stack.setCurrentWidget(self._page_diagram)

        # Hangi blok, hangi round?
        snap_round = snap["round"]
        block_no = snap_idx // _SNAPS_PER_BLOCK + 1
        self._diag_title.setText(
            f"Blok {block_no} / {self._data['blocks_count']}  —  "
            f"Sıkıştırma Round {snap_round} / 64"
        )

        # Mevcut register değerleri (bu snapshot'taki çıkış)
        regs_out = snap["registers"]

        # Bir önceki snapshot'tan giriş değerleri (veya H0 sabitleri)
        if snap_idx > 0 and snap_idx % _SNAPS_PER_BLOCK != 0:
            regs_in = self._snaps[snap_idx - 1]["registers"]
        else:
            regs_in = self._data["initial_h"]

        self._diag_widget.set_data(
            regs_in=regs_in,
            regs_out=regs_out,
            t1=snap.get("t1", "--------"),
            t2=snap.get("t2", "--------"),
            w=snap.get("w", "--------"),
            k=snap.get("k", "--------"),
            round_no=snap_round,
        )

        # Zincir göstergesi
        chain_parts = []
        for i in range(block_no):
            if i < block_no - 1:
                chain_parts.append(f"[Blok {i+1} →]")
            else:
                chain_parts.append(f"[Blok {i+1} ←burada]")
        self._chain_lbl.setText("  →  ".join(chain_parts) + "  →  [Final Hash]")

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._page_match)
        computed = self._data["final_hash"]
        match = computed == self._expected_hash
        icon = "✅" if match else "❌"
        color = ANIM_COLORS["accent_green"] if match else ANIM_COLORS["accent_peach"]

        # Son blok toplama (H_önceki + çalışma değişkenleri = H_sonraki)
        pre_h  = self._data["pre_final_h"]    # 8 değer
        work   = self._data["final_working"]  # a,b,c,d,e,f,g,h
        parts  = self._data["final_h_parts"]  # sonuç

        reg_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
        h_labels   = ["H0", "H1", "H2", "H3", "H4", "H5", "H6", "H7"]

        bc = self._data["blocks_count"]

        assembly_lines = []
        # ── A–H'nin nereden geldiğini açıkla ──
        assembly_lines.append("━━  A – H  ÇALIŞMA DEĞİŞKENLERİ NASIL OLUŞTU?  ━━")
        assembly_lines.append("")
        assembly_lines.append(
            f"Blok {bc}/{bc} işlenmeye başlamadan önce A–H,  önceki H değerleriyle başlatıldı:"
        )
        for i in range(8):
            assembly_lines.append(
                f"  {reg_labels[i]}  ←  {h_labels[i]} = {pre_h[i]}"
            )
        assembly_lines.append("")
        assembly_lines.append("Ardından 64 round boyunca her turda:")
        assembly_lines.append("  T2 = Σ0(A) + Maj(A,B,C)")
        assembly_lines.append("  T1 = Σ1(E) + Ch(E,F,G) + H + K[i] + W[i]")
        assembly_lines.append("  yeni A = T1 + T2    yeni E = D + T1")
        assembly_lines.append("  B←A, C←B, D←C, F←E, G←F, H←G")
        assembly_lines.append("")
        assembly_lines.append("64 round sonunda elde edilen çalışma değişkenleri:")
        for i in range(8):
            assembly_lines.append(f"  {reg_labels[i]} = {work[i]}")
        assembly_lines.append("")
        assembly_lines.append("─" * 60)
        assembly_lines.append("Son adım — H_yeni = H_önceki + çalışma_değişkeni:")
        assembly_lines.append("─" * 60)
        assembly_lines.append(
            f"  {'Önceki H':>10}   {'+ Çalışma':>10}   {'= Yeni H':>10}"
        )
        for i in range(8):
            assembly_lines.append(
                f"  {h_labels[i]}={pre_h[i]}  +  {reg_labels[i]}={work[i]}"
                f"  =  {parts[i]}"
            )

        assembly_lines.append("")
        assembly_lines.append("Birleştirme: H0 ‖ H1 ‖ H2 ‖ H3 ‖ H4 ‖ H5 ‖ H6 ‖ H7")
        assembly_lines.append("─" * 60)

        # 256-bit hash'i 4 satırda göster (32 char + 32 char)
        h = computed
        assembly_lines.append(f"  {h[:16]}  {h[16:32]}")
        assembly_lines.append(f"  {h[32:48]}  {h[48:64]}")
        assembly_lines.append("")
        assembly_lines.append(f"= {len(computed)*4}-bit SHA-256 hash")
        assembly_lines.append("")
        assembly_lines.append("─" * 60)
        assembly_lines.append(f"crypto_core çıktısı: {self._expected_hash[:32]}...")
        assembly_lines.append(f"{icon}  Eşleşme: {'Başarılı' if match else 'HATA'}")

        self._match_lbl.setText("\n".join(assembly_lines))
        self._match_lbl.setStyleSheet(f"color: {color};")

    # ------------------------------------------------------------------
    # Navigasyon yardımcıları
    # ------------------------------------------------------------------

    def _switch_to_content(self) -> None:
        """Intro'dan padding sayfasına geç ve step 0'ı render et."""
        self._stack.setCurrentWidget(self._page_padding)
        self._render_step(0)
        self._progress.setValue(1)

    # showEvent override — intro kendi timer'ını yönetiyor, base class'ı atla
    def showEvent(self, event) -> None:  # type: ignore[override]
        QWidget.showEvent(self, event)
