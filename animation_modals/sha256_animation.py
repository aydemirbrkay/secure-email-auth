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
# Mesaj Genişletme (Message Schedule) animasyonu
# ---------------------------------------------------------------------------

class _WExpansionWidget(QWidget):
    """
    SHA-256 mesaj genişletme animasyonu.

    sha256_pure.sha256_steps()'ın döndürdüğü w_expansion listesi (16 entry,
    i=16..31) üzerinde gezinir. Her i için 4 girdi kutusu (W[i-16], σ0(W[i-15]),
    W[i-7], σ1(W[i-2])) sırayla doğar, ardından oklar `+` düğümüne akar ve
    sonuç W[i] kutusu yeşil pulse ile belirir.

    ◀ / ▶ butonları ile i = 16..31 arasında gezinilir.
    """

    _TICK_MS = 50
    _T_INPUTS_END = 24    # 1200 ms
    _T_ARROWS_END = 36    # +600 ms
    _T_RESULT_END = 44    # +400 ms
    _NAV_HEIGHT = 0       # Navigasyon kaldırıldı — tek örnek gösterilir

    def __init__(
        self, expansion: list[dict] | None, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._exp: list[dict] = expansion or []
        # Tek örnek — kullanıcı isteğine göre 16 i-navigasyonu yerine
        # W[16] için tek detaylı animasyon. W[17..63] aynı formülle hesaplanır.
        self._cur = 0
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        # 400→340 / 460→400: QStackedWidget'ın max sizeHint'i en uzun
        # sayfaya bağlı; SHA modalı alice panelinde QScrollArea içinde
        # gömülü çalıştığı için yüksek minimum, Adım 1/2'de bile butonları
        # ekrandan dışarı itiyordu. Mesaj genişletme widget'ı daha kompakt
        # render edilebildiğinden 60 px düşürüldü.
        self.setMinimumHeight(340)
        self.setMaximumHeight(400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._tick = 0
        self.update()
        if self._exp:
            self._timer.start(self._TICK_MS)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self) -> None:
        if self._tick < self._T_RESULT_END:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        y0 = 0  # paint alanı widget'ın en üstünden başlar (nav yok)

        if not self._exp:
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.setFont(QFont("Georgia", 11))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "w_expansion verisi yok")
            p.end()
            return

        entry = self._exp[self._cur]
        i_val = entry["i"]

        # Tek-örnek bilgi satırı + kaynak açıklaması (iki satır)
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, y0 + 4, W, 16), Qt.AlignmentFlag.AlignCenter,
                   f"Örnek: W[{i_val}] hesaplanışı   "
                   f"·   W[{i_val+1}..63] aynı formülle türetilir")
        p.setFont(QFont("Georgia", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, y0 + 22, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "W[0..15]: mesaj bloğunun 16 × 32-bit kelimesidir (ilk 64 baytı). "
                   "W[16..63]: aşağıdaki σ fonksiyonlarıyla türetilir.")

        # σ formülleri sabit referans (tek-örnek banner'ı altına kayar)
        p.setFont(QFont("Courier New", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, y0 + 40, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "σ0(x) = ROTR(x,7) ⊕ ROTR(x,18) ⊕ SHR(x,3)")
        p.drawText(QRect(0, y0 + 58, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "σ1(x) = ROTR(x,17) ⊕ ROTR(x,19) ⊕ SHR(x,10)")

        # Başlık formülü
        p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, y0 + 82, W, 22), Qt.AlignmentFlag.AlignCenter,
                   f"W[{i_val}] = σ1(W[{i_val-2}]) + W[{i_val-7}] + "
                   f"σ0(W[{i_val-15}]) + W[{i_val-16}]   (mod 2³²)")

        # 4 girdi kutusu (yan yana 2x2 grid)
        box_w, box_h = 200, 56
        gap_x, gap_y = 30, 24
        total_w = 2 * box_w + gap_x
        ox = (W - total_w) // 2
        oy = y0 + 116

        inputs = [
            (ox, oy,
             f"W[{i_val-16}]",
             entry["w_i16"],
             None,
             ANIM_COLORS["accent_blue"]),
            (ox + box_w + gap_x, oy,
             f"σ0(W[{i_val-15}])",
             entry["w_i15"],
             entry["s0"],
             ANIM_COLORS["accent_mauve"]),
            (ox, oy + box_h + gap_y,
             f"W[{i_val-7}]",
             entry["w_i7"],
             None,
             ANIM_COLORS["accent_peach"]),
            (ox + box_w + gap_x, oy + box_h + gap_y,
             f"σ1(W[{i_val-2}])",
             entry["w_i2"],
             entry["s1"],
             ANIM_COLORS["accent_yellow"]),
        ]

        # Hangileri görünür?
        # 0..6 → kutu 0; 6..12 → kutu 0+1; 12..18 → +2; 18..24 → +3
        visible_count = min(4, max(0, (self._tick + 5) // 6))

        for idx, (bx, by, label, operand, result, color) in enumerate(inputs):
            if idx >= visible_count:
                continue
            opacity = 1.0
            if idx == visible_count - 1:
                progress = (self._tick - idx * 6) / 6.0
                opacity = max(0.0, min(1.0, progress))
            self._draw_input_box(p, bx, by, box_w, box_h,
                                 label, operand, result, color, opacity)

        # `+` düğümü merkezde
        node_x = W // 2 - 22
        node_y = oy + box_h + gap_y // 2 - 22
        if self._tick >= self._T_INPUTS_END:
            self._draw_plus_node(p, node_x, node_y)

        # 4 ok girdi → düğüm
        if self._tick > self._T_INPUTS_END:
            arrow_progress = min(1.0,
                (self._tick - self._T_INPUTS_END) /
                (self._T_ARROWS_END - self._T_INPUTS_END))
            # Üst satır kutuları (idx 0,1): okun ALT kenarından başla (aşağı düğüme git)
            # Alt satır kutuları (idx 2,3): okun ÜST kenarından başla (yukarı düğüme git)
            # Bu sayede oklar kutuların içinden geçmez.
            for idx, (bx, by, _, _, _, color) in enumerate(inputs):
                src_y = (by + box_h) if idx < 2 else by
                self._draw_arrow_to_node(p, bx + box_w // 2, src_y,
                                          node_x + 22, node_y + 22, 22,
                                          QColor(color), arrow_progress)

        # Sonuç kutusu altta
        result_y = oy + 2 * box_h + gap_y + 60
        if self._tick >= self._T_ARROWS_END:
            opacity = min(1.0,
                (self._tick - self._T_ARROWS_END) /
                (self._T_RESULT_END - self._T_ARROWS_END))
            pulse = self._tick >= self._T_RESULT_END
            self._draw_result_box(p, W // 2 - box_w // 2, result_y, box_w, box_h,
                                  i_val, entry["result"], opacity, pulse)
            # düğüm → sonuç oku
            self._draw_arrow_simple(p, node_x + 22, node_y + 44,
                                    W // 2, result_y, QColor(ANIM_COLORS["accent_green"]))

        # Alt sayaç burada DEĞİL — üstteki QLabel'da gösteriliyor

        p.end()

    def _draw_input_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        label: str, operand: str, result: str | None, color: str,
        opacity: float,
    ) -> None:
        col = QColor(color)
        col.setAlphaF(opacity)
        fill = QColor(color)
        fill.setAlphaF(opacity * 0.18)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)
        p.setPen(text_col)
        p.drawText(QRect(x + 4, y + 2, w - 8, 18),
                   Qt.AlignmentFlag.AlignCenter, label)

        p.setFont(QFont("Courier New", 10))
        if result is None:
            p.drawText(QRect(x + 4, y + 22, w - 8, 28),
                       Qt.AlignmentFlag.AlignCenter, operand)
        else:
            p.drawText(QRect(x + 4, y + 22, w - 8, 16),
                       Qt.AlignmentFlag.AlignCenter, operand)
            p.setPen(QColor(ANIM_COLORS["accent_green"]))
            p.drawText(QRect(x + 4, y + 38, w - 8, 16),
                       Qt.AlignmentFlag.AlignCenter, f"→ {result}")

    def _draw_plus_node(self, p: QPainter, x: int, y: int) -> None:
        p.setBrush(QBrush(QColor(ANIM_COLORS["bg_input"])))
        p.setPen(QPen(QColor(ANIM_COLORS["accent_green"]), 2))
        p.drawEllipse(x, y, 44, 44)
        p.setFont(QFont("Courier New", 18, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(x, y, 44, 44), Qt.AlignmentFlag.AlignCenter, "+")

    def _draw_arrow_to_node(
        self, p: QPainter, x1: int, y1: int, node_cx: int, node_cy: int,
        node_r: int, color: QColor, progress: float,
    ) -> None:
        """(x1,y1)'den düğüm dairesinin KENARINA (merkezine değil) giden okun
        progress kadarını çiz. Düğümün merkezindeki '+' işareti üstüne
        bindirilmez."""
        dx = node_cx - x1
        dy = node_cy - y1
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
        # Hedef nokta: düğüm dairesinin kenarı, kaynak yönüne bakan
        end_x = x1 + dx * (dist - node_r) / dist
        end_y = y1 + dy * (dist - node_r) / dist
        col = QColor(color)
        col.setAlphaF(progress)
        p.setPen(QPen(col, 2))
        cx = int(x1 + (end_x - x1) * progress)
        cy = int(y1 + (end_y - y1) * progress)
        p.drawLine(int(x1), int(y1), cx, cy)

    def _draw_arrow_simple(
        self, p: QPainter, x1: int, y1: int, x2: int, y2: int,
        color: QColor,
    ) -> None:
        p.setPen(QPen(color, 2))
        p.drawLine(x1, y1, x2, y2)
        # ok ucu
        size = 6
        pts = QPolygon([
            QPoint(x2, y2),
            QPoint(x2 - size, y2 - size * 2),
            QPoint(x2 + size, y2 - size * 2),
        ])
        p.setBrush(QBrush(color))
        p.drawPolygon(pts)

    def _draw_result_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        i: int, value: str, opacity: float, pulse: bool,
    ) -> None:
        col = QColor(ANIM_COLORS["accent_green"])
        col.setAlphaF(opacity)
        fill = QColor(ANIM_COLORS["accent_green"])
        if pulse:
            phase = (self._tick % 8) / 8.0
            fill.setAlphaF(opacity * (0.18 + 0.20 * abs(0.5 - phase) * 2))
        else:
            fill.setAlphaF(opacity * 0.20)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)

        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)
        p.setPen(text_col)
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter,
                   f"W[{i}] = {value}")


# ---------------------------------------------------------------------------
# Final Hash Eşleşme Animasyonu
# ---------------------------------------------------------------------------

class _MatchAssemblyWidget(QWidget):
    """
    SHA-256 final hash eşleşme animasyonu.

    Dört faz (toplam ~4.7 sn):
      Faz 1 (1500 ms): 8 başlangıç H + 8 çalışma değişkeni kutuları parlar
      Faz 2 (1600 ms): Önceki H + Çalışma = Yeni H toplaması, 8 satır × 200 ms
      Faz 3 (800 ms):  8 yeni H yatayda birleşir → 256-bit hash şeridi
      Faz 4 (800 ms):  Şerit crypto_core ile karakter karakter eşleşir,
                        sonuç kartı (✅ / ❌)

    start_animation(pre_h, working, parts, computed, expected) ile başlatılır.
    """

    _TICK_MS = 50
    _T_F1_END = 30   # 1500 ms
    _T_F2_END = 62   # +1600 ms
    _T_F3_END = 78   # +800 ms
    _T_F4_END = 94   # +800 ms

    _REG_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H"]
    _H_LABELS   = ["H0", "H1", "H2", "H3", "H4", "H5", "H6", "H7"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Widget min 510 px — Faz 4'teki eşleşme kartı (card_y=448, card_h=36
        # → 484'te biter) tam görünsün diye. Widget artık _make_match_page
        # içinde QScrollArea ile sarıldığı için bu yükseklik QStackedWidget'in
        # stack height'ini büyütmez; scroll içinde gerekirse dikey kaydırılır.
        # (Önceki 460 değeri kartı kırpıyordu — kullanıcı en alttaki yeşil
        # 'Eşleşme: Başarılı' kutusunu göremiyordu.)
        self.setMinimumHeight(510)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pre_h: list[str] = ["--------"] * 8
        self._working: list[str] = ["--------"] * 8
        self._parts: list[str] = ["--------"] * 8
        self._computed: str = "0" * 64
        self._expected: str = "0" * 64
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def start_animation(
        self,
        pre_h: list[str],
        working: list[str],
        parts: list[str],
        computed: str,
        expected: str,
    ) -> None:
        self._pre_h = pre_h
        self._working = working
        self._parts = parts
        self._computed = computed
        self._expected = expected
        self._tick = 0
        self._timer.start(self._TICK_MS)
        self.update()

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self) -> None:
        if self._tick < self._T_F4_END:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        t = self._tick

        # Faz 1: Round özet (üstte) — her zaman görünür ama önce sönük
        self._draw_phase1(p, W, t)

        # Faz 2: Toplama tablosu (orta) — t >= T_F1_END
        if t >= self._T_F1_END:
            self._draw_phase2(p, W, t - self._T_F1_END)

        # Faz 3: Birleşim şeridi (alt) — t >= T_F2_END
        if t >= self._T_F2_END:
            self._draw_phase3(p, W, H, t - self._T_F2_END)

        # Faz 4: Eşleşme doğrulaması — t >= T_F3_END
        if t >= self._T_F3_END:
            self._draw_phase4(p, W, H, t - self._T_F3_END)

        p.end()

    def _draw_phase1(self, p: QPainter, W: int, t: int) -> None:
        """8 H başlangıç + 8 A-H çalışma değişkeni (üstte yan yana)."""
        y = 8
        gap = 4
        # Pencere genişliğine göre adaptif kutu boyutu — 8 kutu her zaman sığar
        box_w = max(60, min(96, (W - 24 - 7 * gap) // 8))
        total_w = 8 * box_w + 7 * gap
        x_start = (W - total_w) // 2
        h_lit = min(8, max(0, t // 2)) if t < self._T_F1_END else 8
        for i in range(8):
            x = x_start + i * (box_w + gap)
            opacity = 1.0 if i < h_lit else 0.3
            self._draw_small_box(
                p, x, y, box_w, 38,
                self._H_LABELS[i], self._pre_h[i],
                ANIM_COLORS["accent_blue"], opacity,
            )

        if t >= 8:
            p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(0, y + 50, W, 18),
                       Qt.AlignmentFlag.AlignCenter, "→ 64 round →")

        y2 = y + 70
        a_lit = min(8, max(0, (t - 8) // 2)) if t < self._T_F1_END else 8
        for i in range(8):
            x = x_start + i * (box_w + gap)
            opacity = 1.0 if i < a_lit else 0.3
            self._draw_small_box(
                p, x, y2, box_w, 38,
                self._REG_LABELS[i], self._working[i],
                ANIM_COLORS["accent_mauve"], opacity,
            )

    def _draw_phase2(self, p: QPainter, W: int, t: int) -> None:
        """Önceki H + Çalışma = Yeni H toplama tablosu (8 satır × 4 tick)."""
        # Faz 1 sütunlarının altında, üst üste binme olmaz
        oy = 150
        row_h = 22
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        center_x = W // 2
        p.drawText(QRect(center_x - 280, oy - 18, 200, 16),
                   Qt.AlignmentFlag.AlignLeft, "Önceki H")
        p.drawText(QRect(center_x - 60, oy - 18, 160, 16),
                   Qt.AlignmentFlag.AlignLeft, "+ Çalışma")
        p.drawText(QRect(center_x + 140, oy - 18, 160, 16),
                   Qt.AlignmentFlag.AlignLeft, "= Yeni H")

        for i in range(8):
            row_t = t - i * 4
            if row_t < 0:
                continue
            row_y = oy + i * row_h
            p.setFont(QFont("Courier New", 10))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(center_x - 280, row_y, 200, row_h),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"{self._H_LABELS[i]} = {self._pre_h[i]}")
            if row_t >= 1:
                p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
                p.drawText(QRect(center_x - 60, row_y, 200, row_h),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           f"+ {self._REG_LABELS[i]} = {self._working[i]}")
            if row_t >= 2:
                pulse = (row_t < 8)
                col = QColor(ANIM_COLORS["accent_green"])
                if pulse:
                    phase = (self._tick % 6) / 6.0
                    col.setAlphaF(0.6 + 0.4 * abs(0.5 - phase) * 2)
                p.setPen(col)
                p.drawText(QRect(center_x + 140, row_y, 200, row_h),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           f"= {self._parts[i]}")

    def _draw_phase3(self, p: QPainter, W: int, H_total: int, t: int) -> None:
        """8 yeni H'nin tek bir 256-bit şeride birleşmesi."""
        # Faz 2'nin altında (faz 2: 150 + 8*22 = 326)
        y = 340
        max_t = self._T_F3_END - self._T_F2_END
        progress = min(1.0, t / max_t)
        full_hash = "".join(self._parts)
        strip_w = min(W - 40, 720)
        strip_h = 40
        strip_x = (W - strip_w) // 2
        col = QColor(ANIM_COLORS["accent_green"])
        col.setAlphaF(progress)
        fill = QColor(ANIM_COLORS["accent_green"])
        fill.setAlphaF(progress * 0.20)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(strip_x, y, strip_w, strip_h, 6, 6)
        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(progress)
        p.setPen(text_col)
        if strip_w > 600:
            p.drawText(QRect(strip_x, y, strip_w, strip_h),
                       Qt.AlignmentFlag.AlignCenter, full_hash)
        else:
            p.drawText(QRect(strip_x, y, strip_w, strip_h // 2),
                       Qt.AlignmentFlag.AlignCenter, full_hash[:32])
            p.drawText(QRect(strip_x, y + strip_h // 2, strip_w, strip_h // 2),
                       Qt.AlignmentFlag.AlignCenter, full_hash[32:])

    def _draw_phase4(self, p: QPainter, W: int, H_total: int, t: int) -> None:
        """crypto_core ile karakter karakter eşleşme + sonuç kartı."""
        chars_revealed = min(64, t * 4)
        # Faz 3 şeridinin altında (faz 3: y=340, h=40, biter ~380)
        y = 400

        p.setFont(QFont("Courier New", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, y, W, 16),
                   Qt.AlignmentFlag.AlignCenter, "crypto_core çıktısı:")

        y_chars = y + 18
        # char_w pencere genişliğine adaptif — 64 hex karakter her zaman sığar
        char_w = max(7, min(11, (W - 40) // 64))
        row_w = 64 * char_w
        ox = (W - row_w) // 2
        for i in range(min(chars_revealed, 64)):
            x = ox + i * char_w
            ref_char = self._expected[i] if i < len(self._expected) else "?"
            match = (i < len(self._computed) and i < len(self._expected)
                     and self._computed[i] == self._expected[i])
            col = QColor(ANIM_COLORS["accent_green"] if match
                         else ANIM_COLORS["accent_peach"])
            p.setPen(col)
            p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            p.drawText(QRect(x, y_chars, char_w, 16),
                       Qt.AlignmentFlag.AlignCenter, ref_char)

        if chars_revealed >= 64:
            match_all = self._computed == self._expected
            card_y = y_chars + 30
            col = QColor(ANIM_COLORS["accent_green"] if match_all
                         else ANIM_COLORS["accent_peach"])
            fill = QColor(col)
            fill.setAlphaF(0.20)
            card_w = 280
            card_h = 36
            card_x = (W - card_w) // 2
            p.setBrush(QBrush(fill))
            p.setPen(QPen(col, 2))
            p.drawRoundedRect(card_x, card_y, card_w, card_h, 6, 6)
            p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
            p.setPen(col)
            text = "✅  Eşleşme: Başarılı" if match_all else "❌  Eşleşme: HATA"
            p.drawText(QRect(card_x, card_y, card_w, card_h),
                       Qt.AlignmentFlag.AlignCenter, text)

    def _draw_small_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        label: str, value: str, color: str, opacity: float,
    ) -> None:
        col = QColor(color)
        col.setAlphaF(opacity)
        fill = QColor(color)
        fill.setAlphaF(opacity * 0.18)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 1))
        p.drawRoundedRect(x, y, w, h, 4, 4)

        p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)
        p.setPen(text_col)
        p.drawText(QRect(x, y + 2, w, 14), Qt.AlignmentFlag.AlignCenter, label)
        p.setFont(QFont("Courier New", 9))
        p.drawText(QRect(x, y + 18, w, 18),
                   Qt.AlignmentFlag.AlignCenter, value)


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
# SHA Mesaj Hazırlığı (metin → UTF-8 byte) — Task 7 widget'ı
# ---------------------------------------------------------------------------

class _SHAMessagePrepWidget(QWidget):
    """
    SHA Mesaj Hazırlığı sayfası — kullanıcının metnini UTF-8 byte'lara dönüştürme
    sürecini görselleştirir.

    Fazlar (QTimer _TICK_MS=60):
      0: Mesaj label'ı fade-in
      1: İlk 16 byte char->ASCII->hex satırları kademeli
      2: Binary satırı
      3: Alt byte strip görünür
      4: Özet kartı — animasyon durur, on_finished callback çağrılır

    Boş mesaj: faz 1-2-3 atlanır, doğrudan faz 4'e geçilir.
    """

    _TICK_MS = 60

    def __init__(
        self,
        message_text: str,
        message_bytes: bytes,
        on_finished=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from animation_modals.byte_widgets import (
            _ColoredByteGridWidget,
            _ByteStripWidget,
        )

        self._message_text = message_text
        self._message_bytes = message_bytes
        self._on_finished = on_finished
        self._is_empty = len(message_bytes) == 0
        self._tick = 0
        self._phase = 0
        self._finished = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        # Üst başlık
        title = QLabel("Mesaj Hazırlığı — Metin → UTF-8 Byte Dizisi")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        # Mesaj label — TAM mesaj gösterilir (eski 60 karakter kesilmesi
        # kaldırıldı); uzun mesajlarda QLabel word-wrap ile alt satıra iner.
        if self._is_empty:
            label_text = "<i>(boş mesaj)</i>"
            label_color = ANIM_COLORS["text_muted"]
        else:
            label_text = f"Mesaj: \"{message_text}\""
            label_color = ANIM_COLORS["text_secondary"]
        self._msg_lbl = QLabel(label_text)
        self._msg_lbl.setFont(QFont("IBM Plex Sans", 11))
        self._msg_lbl.setStyleSheet(f"color: {label_color};")
        self._msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._msg_lbl.setWordWrap(True)
        lay.addWidget(self._msg_lbl)

        # Detail grid — TÜM mesaj byte'ları gösterilir (16 cap KALDIRILDI):
        # Kutu boyutu sabit (66 px), kutu SAYISI mesaj uzunluğuyla artar.
        # 71-byte mesaj → 71 kutu, ~5000 px genişlikte widget; QScrollArea
        # yatay scroll ile kullanıcı tüm byte'ları (e-mail boyu kadar uzun
        # mesajı dahi) baştan sona gezebilir. Kutu boyutu küçülmez —
        # binary, hex, decimal her durumda okunaklı kalır.
        detail_lbl = QLabel("Byte detayı (yatay kaydırarak tüm byte'ları gör):")
        detail_lbl.setFont(QFont("IBM Plex Sans", 9))
        detail_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(detail_lbl)

        # max_cells = len(data): cap yok, tüm byte'lar gösterilir.
        # Boş mesaj için fallback 1 (görsel olarak hiçbir kutu çizmez).
        n_cells = max(1, len(message_bytes))
        self._grid = _ColoredByteGridWidget(message_bytes, max_cells=n_cells)
        cell_w_fixed = 66
        cell_h_fixed = 36
        grid_w = 86 + n_cells * (cell_w_fixed + 3)
        grid_h = 4 * (cell_h_fixed + 4) + 30
        self._grid.setFixedSize(grid_w, grid_h)

        grid_scroll = QScrollArea()
        grid_scroll.setWidget(self._grid)
        grid_scroll.setWidgetResizable(False)  # sabit boyut → yatay scroll
        grid_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        grid_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        grid_scroll.setStyleSheet("background: transparent; border: none;")
        grid_scroll.setFixedHeight(grid_h + 18)  # +18 yatay scrollbar payı
        lay.addWidget(grid_scroll)

        # Byte strip (tüm byte'lar) — scroll içinde
        strip_lbl = QLabel("Tüm byte'lar:")
        strip_lbl.setFont(QFont("IBM Plex Sans", 9))
        strip_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(strip_lbl)
        self._strip = _ByteStripWidget(message_bytes)
        strip_scroll = QScrollArea()
        strip_scroll.setWidget(self._strip)
        strip_scroll.setWidgetResizable(True)
        strip_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        strip_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        strip_scroll.setStyleSheet("background: transparent; border: none;")
        # 22 (cell_h) + 24 (üst etiket alanı) ≈ 46, buffer ile 56
        strip_scroll.setFixedHeight(56)
        self._strip.setVisible(False)
        lay.addWidget(strip_scroll)

        # Özet kartı
        if self._is_empty:
            summary_text = "Mesaj boş — yalnızca padding işlemi yapılacak"
        else:
            summary_text = (
                f"{len(message_text)} karakter → {len(message_bytes)} byte"
            )
        self._summary = QLabel(summary_text)
        self._summary.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        self._summary.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']}; "
            f"padding: 8px; background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px;"
        )
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary.setVisible(False)
        lay.addWidget(self._summary)

        # NOT: addStretch() çıkarıldı — pencere büyük olsa bile widget kompakt
        # kalsın, alt taraf scrollu/boş alanlı görünmesin. Üst hizalama parent
        # tarafından (_make_msgprep_page) AlignTop ile sağlanır.

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def start(self) -> None:
        self._timer.start(self._TICK_MS)

    def _on_tick(self) -> None:
        self._tick += 1
        if self._is_empty:
            # Boş mesaj: faz 0 (~1.2s) sonra doğrudan faz 4'e
            if self._tick >= 25:
                self._jump_to_final()
            return

        # Normal akış — fazlar
        if self._tick == 21:
            self._phase = 1
        elif self._tick == 61:
            self._phase = 2
        elif self._tick == 96:
            self._phase = 3
            self._strip.setVisible(True)
        elif self._tick >= 116:
            self._jump_to_final()

    def _jump_to_final(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        self._strip.setVisible(not self._is_empty)
        self._summary.setVisible(True)
        if self._on_finished:
            self._on_finished()

    def closeEvent(self, e) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(e)


class _SHA256PaddingWidget(QWidget):
    """
    SHA-256 Padding sayfası — görsel byte stripi üzerinde padding sürecini gösterir.

    Strip her zaman TÜM 64 byte'ı (tam padded blok) gösterir. Kullanıcının
    mesaj byte'ları normal renkli kareler, padding byte'ları (0x80 + 0x00
    dolgu + 8 byte length) beyaz 1px border + alpha 0.7 ile ayrışır.
    Fazlar yalnızca açıklayıcı etiketi günceller; veri başından sonuna
    aynı görünür ki kullanıcı "yazdığım yazı şurada, padding şurada başlıyor"
    ilişkisini anında görsün.

    Fazlar (etiket güncellemeleri):
      0: "Kullanıcının metni soldaki renkli kareler; geri kalan padding"
      1: "0x80 ayracı — padding başlangıç byte'ı"
      2: "0x00 dolgusu — 56 byte'a tamamlanır"
      3: "Son 8 byte — mesaj uzunluğu (big-endian)"
      4: "Padding tamamlandı — N byte / K blok"
    """

    _TICK_MS = 60

    def __init__(
        self,
        message_bytes: bytes,
        padded_bytes: bytes,
        blocks_count: int,
        message_text: str = "",
        on_finished=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from animation_modals.byte_widgets import _ByteStripWidget

        self._message_text = message_text
        self._message_bytes = message_bytes
        self._padded_bytes = padded_bytes
        self._blocks_count = blocks_count
        self._on_finished = on_finished
        self._current_block = 0
        self._tick = 0
        self._phase = 0
        self._finished = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        # Başlık
        title = QLabel("Adım 2 / 5 — Padding ve Blok Yapısı")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        # Mesaj label — Adım 1 ile simetri; kullanıcının yazdığı metin tam
        # haliyle görünür (word-wrap ile uzun mesajlar alt satıra iner).
        if len(message_bytes) == 0:
            msg_label_text = "<i>(boş mesaj)</i>"
            msg_color = ANIM_COLORS["text_muted"]
        else:
            msg_label_text = f"Mesaj: \"{message_text}\""
            msg_color = ANIM_COLORS["text_secondary"]
        self._msg_lbl = QLabel(msg_label_text)
        self._msg_lbl.setFont(QFont("IBM Plex Sans", 11))
        self._msg_lbl.setStyleSheet(f"color: {msg_color};")
        self._msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._msg_lbl.setWordWrap(True)
        lay.addWidget(self._msg_lbl)

        # Info etiketi — boş mesaj durumunda özel mesaj
        if len(message_bytes) == 0:
            info_text = "Boş mesaj — padding tek 64 byte blok oluşturur"
        else:
            info_text = (
                f"Padding: {len(message_bytes)} byte mesaj + 0x80 + "
                f"0x00 dolgu + 64-bit uzunluk = "
                f"{len(padded_bytes)} byte ({blocks_count} blok)"
            )
        self._info_lbl = QLabel(info_text)
        self._info_lbl.setFont(QFont("IBM Plex Sans", 10))
        self._info_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_lbl.setWordWrap(True)
        lay.addWidget(self._info_lbl)

        # Blok navigasyon butonları — eskiden burada başlıkla grid arasındaydı;
        # kullanıcı geri bildirimi: yatay scrollbar'ın hemen ÜSTÜNDE, sol-alt
        # köşede küçük butonlar olsun. Buton oluşturuluyor ama lay'e burada
        # eklenmiyor — grid'den sonra eklenecek (aşağı bak).
        self._block_lbl = None
        self._btn_prev_block = None
        self._btn_next_block = None
        if blocks_count > 1:
            self._btn_prev_block = QPushButton("◀ Önceki")
            self._btn_prev_block.setFont(QFont("IBM Plex Sans", 8))
            self._btn_prev_block.setFixedHeight(22)
            self._btn_prev_block.setMaximumWidth(82)
            self._btn_prev_block.clicked.connect(self._prev_block)
            self._btn_prev_block.setEnabled(False)

            self._block_lbl = QLabel(f"Blok 1 / {blocks_count}")
            self._block_lbl.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            self._block_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
            self._block_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._block_lbl.setFixedHeight(22)

            self._btn_next_block = QPushButton("Sonraki ▶")
            self._btn_next_block.setFont(QFont("IBM Plex Sans", 8))
            self._btn_next_block.setFixedHeight(22)
            self._btn_next_block.setMaximumWidth(82)
            self._btn_next_block.clicked.connect(self._next_block)
            self._btn_next_block.setEnabled(blocks_count > 1)

        # Faz etiketi — kullanıcıya hangi padding bileşeninin vurgulandığını söyler
        self._phase_lbl = QLabel(self._phase_label_text(0))
        self._phase_lbl.setFont(QFont("IBM Plex Sans", 9, QFont.Weight.Bold))
        self._phase_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
        self._phase_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._phase_lbl.setWordWrap(True)
        lay.addWidget(self._phase_lbl)

        # 64 byte detay grid'i — TÜM padded blok karakter/ASCII/hex/binary
        # satırları halinde gösterilir. Mesaj byte'ları normal renkli; padding
        # byte'ları (0x80 + 0x00 dolgu + 8 byte length) beyaz 2px border +
        # alpha 0.7 + [80]/[00]/[len] etiketleriyle ayrışır. Yatay scroll
        # ile tüm 64 byte erişilebilir (sığmadığında).
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        initial_mask = self._full_padding_mask()
        initial_labels = self._full_padding_labels()
        # Hücre boyutu: 66×36 — binary satırı (Courier 9pt "01100101"
        # ≈ 56 px) için 10 px padding'le rahat sığacak taban. Tüm satırlar
        # (Karakter / ASCII / Hex / Binary) aynı 66 px genişliği kullanır;
        # böylece satırlar bütünsel görünür ve binary kesilmez.
        # (Önceki 54×34 + 9pt zaman zaman 1-2 px taşıyabiliyordu.)
        self._grid = _ColoredByteGridWidget(
            self._current_block_bytes(),
            max_cells=64,
            cell_w=66,
            cell_h=36,
            padding_mask=initial_mask,
            padding_labels=initial_labels,
        )
        # 64 hücre × (66+3) + label (80) + sol kenar (6) ≈ 4502 px sabit
        # (yatay scroll mevcut, görsel etki yok — kullanıcı scroll'la
        # 64 baytı tek tek gezebilir).
        grid_width = 80 + 6 + 64 * (66 + 3)
        grid_height = 4 * (36 + 4) + 30 + 16  # 4 satır + padding etiket alanı
        self._grid.setFixedSize(grid_width, grid_height)

        grid_scroll = QScrollArea()
        grid_scroll.setWidget(self._grid)
        grid_scroll.setWidgetResizable(False)  # sabit boyut + yatay scroll
        grid_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        grid_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        grid_scroll.setStyleSheet("background: transparent; border: none;")
        grid_scroll.setFixedHeight(grid_height + 24)
        lay.addWidget(grid_scroll)
        self._grid_scroll = grid_scroll

        # Blok navigasyon satırı — grid scroll'un HEMEN ALTINA, sol-alta küçük
        # butonlar olarak yerleştirilir (kullanıcı isteği). Sağ tarafta esnek
        # boşluk → tek mesajda nav row dahil edilmez.
        if blocks_count > 1:
            nav_row = QHBoxLayout()
            nav_row.setContentsMargins(0, 0, 0, 0)
            nav_row.setSpacing(6)
            nav_row.addWidget(self._btn_prev_block)
            nav_row.addWidget(self._block_lbl)
            nav_row.addWidget(self._btn_next_block)
            nav_row.addStretch(1)   # geri kalan boşluğu sağa it
            lay.addLayout(nav_row)

        # Bit length etiketi
        bit_len = len(message_bytes) * 8
        self._bitlen_lbl = QLabel(f"Mesaj uzunluğu: {bit_len} bit (son 8 byte)")
        self._bitlen_lbl.setFont(QFont("Courier New", 9))
        self._bitlen_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._bitlen_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bitlen_lbl.setVisible(False)
        lay.addWidget(self._bitlen_lbl)

        # NOT: addStretch() çıkarıldı — sayfada gereksiz dikey boşluk yaratıyordu.

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def _full_padding_mask(self) -> list[bool]:
        """Tam padding mask — mesaj byte'ları False, geri kalan tüm
        padding bileşenleri (0x80, 0x00 dolgu, length) True. İlk blok için
        mesaj uzunluğuna göre hesaplanır; sonraki bloklar tamamen padding."""
        n_msg = len(self._message_bytes)
        if self._current_block == 0:
            # İlk 64 byte içinde mesaj byte'larından sonraki her şey padding
            cutoff = min(n_msg, 64)
            return [False] * cutoff + [True] * (64 - cutoff)
        # Sonraki bloklar: tamamen padding (mesaj zaten önceki bloklarda)
        return [True] * 64

    def _full_padding_labels(self) -> list[str]:
        """Her byte için padding türü etiketi: mesaj byte'larında '' (etiket
        yok), 0x80 → '80', 0x00 → '00', son 8 byte → 'len'. Kullanıcı her
        kutucuğun hangi padding bileşenine ait olduğunu okuyarak görür."""
        block_data = self._current_block_bytes()
        block_start = self._current_block * 64
        total_padded = len(self._padded_bytes)
        n_msg_total = len(self._message_bytes)
        last8_start = total_padded - 8  # mesaj uzunluğu byte'larının başlangıcı
        labels: list[str] = []
        for i, byte_val in enumerate(block_data):
            absolute = block_start + i
            if absolute < n_msg_total:
                labels.append("")  # mesaj byte'ı — etiket yok
            elif absolute >= last8_start:
                labels.append("len")  # son 8 byte: mesaj uzunluğu
            elif byte_val == 0x80:
                labels.append("80")  # padding ayracı
            else:
                labels.append("00")  # sıfır dolgu
        # 64'e tamamla (eksikse boş etiket)
        while len(labels) < 64:
            labels.append("")
        return labels[:64]

    def _phase_label_text(self, phase: int) -> str:
        """Aktif faza göre kullanıcıya ne vurgulandığını anlatan etiket."""
        n_msg = len(self._message_bytes)
        if phase == 0:
            if n_msg == 0:
                return "Boş mesaj — tüm 64 byte padding (0x80 + 0x00 dolgu + uzunluk)"
            return (
                f"Soldaki {n_msg} renkli kare = kullanıcının metni; "
                f"geri kalan {64 - min(n_msg, 64)} kare = padding"
            )
        if phase == 1:
            return "0x80 ayracı — padding'in ilk byte'ı (mesajdan hemen sonra)"
        if phase == 2:
            return "0x00 dolgusu — blok 56 byte'a tamamlanır"
        if phase == 3:
            return "Son 8 byte — mesaj uzunluğu (big-endian, bit cinsinden)"
        return (
            f"Padding tamamlandı — {len(self._padded_bytes)} byte / "
            f"{self._blocks_count} blok"
        )

    def _current_block_bytes(self) -> bytes:
        start = self._current_block * 64
        return self._padded_bytes[start:start + 64]

    def start(self) -> None:
        self._timer.start(self._TICK_MS)

    def _on_tick(self) -> None:
        # Veri görseli baştan tam — fazlar sadece açıklama etiketini günceller.
        # Bu sayede kullanıcı "yazdığım yazı / padding" ayrımını anında görür,
        # fazlar her bir padding bileşenini sırayla vurgular.
        self._tick += 1
        if self._tick == 26:
            self._phase = 1
            self._phase_lbl.setText(self._phase_label_text(1))
        elif self._tick == 46:
            self._phase = 2
            self._phase_lbl.setText(self._phase_label_text(2))
        elif self._tick == 96:
            self._phase = 3
            self._phase_lbl.setText(self._phase_label_text(3))
            self._bitlen_lbl.setVisible(True)
        elif self._tick >= 126:
            self._phase = 4
            self._phase_lbl.setText(self._phase_label_text(4))
            self._jump_to_final()

    def _jump_to_final(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        if self._on_finished:
            self._on_finished()

    def _prev_block(self) -> None:
        if self._current_block > 0:
            self._current_block -= 1
            self._update_block_view()

    def _next_block(self) -> None:
        if self._current_block < self._blocks_count - 1:
            self._current_block += 1
            self._update_block_view()

    def _update_block_view(self) -> None:
        if self._block_lbl is not None:
            self._block_lbl.setText(f"Blok {self._current_block + 1} / {self._blocks_count}")
        if self._btn_prev_block is not None:
            self._btn_prev_block.setEnabled(self._current_block > 0)
        if self._btn_next_block is not None:
            self._btn_next_block.setEnabled(self._current_block < self._blocks_count - 1)
        # Blok değişiminde tam mask + etiket uygulanır — mesaj/padding ayrımı
        # her blokta baştan görünür (sonraki bloklar tamamen padding).
        self._grid.set_data(
            self._current_block_bytes(),
            padding_mask=self._full_padding_mask(),
            padding_labels=self._full_padding_labels(),
        )

    def closeEvent(self, e) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(e)


# ---------------------------------------------------------------------------
# SHA-256 Animasyon Penceresi
# ---------------------------------------------------------------------------

class SHA256AnimationWindow(CryptoAnimationWindow):
    """
    SHA-256 animasyon penceresi.

    Mantıksal adımlar (kullanıcı görünümü):
      Adım 1 / 5 : Mesaj Hazırlığı (UTF-8 byte dönüşümü)
      Adım 2 / 5 : Padding ve Blok Yapısı
      Adım 3 / 5 : Mesaj Genişletme (W_i)
      Adım 4 / 5 : Sıkıştırma Round Diyagramı (her snapshot bir alt adım)
      Adım 5 / 5 : Hash Eşleşmesi

    Underlying step_idx (progress bar):
      0         : Mesaj Hazırlığı
      1         : Padding
      2         : W expansion
      3..N+2    : Round snapshot'ları
      N+3       : Match (otomatik _show_match_result tetiklenir)

    Parametreler:
      message      : kullanıcının orijinal mesaj metni
      expected_hash: crypto_core'un ürettiği hex hash
    """

    _TITLES = [
        "Adım 1 / 5 — Mesaj Hazırlığı",
        "Adım 2 / 5 — Padding ve Blok Yapısı",
        "Adım 3 / 5 — Mesaj Genişletme (W_i)",
        "Adım 4 / 5 — Sıkıştırma Round Diyagramı",
        "Adım 5 / 5 — Hash Eşleşmesi",
    ]
    _CAPTIONS = [
        "Metnin UTF-8 byte dizisine dönüşümü",
        "0x80 ayracı, 0x00 dolgu, 64-bit uzunluk eki",
        "İlk 16 word'den W[16..63] türetilir",
        "64 round, A..H register güncellemesi",
        "Final H[0..7] birleştirme + beklenen hash karşılaştırması",
    ]

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

        # Adım 0: mesaj hazırlığı (UTF-8 byte dönüşümü)
        # Adım 1: padding
        # Adım 2: W_i mesaj genişletme
        # Adım 3..len(snaps)+2: her blok için 9 snapshot (round 1,9,17,25,33,41,49,57,64)
        # Son adım: eşleşme (_show_match_result)
        snaps = self._data["round_snapshots"]
        total = 3 + len(snaps)   # message_prep + padding + W_i genişletme + all snapshots
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

        # Sayfa 0 — Ön tanıtma (intro). Akış şeması adım adım açıldığında
        # widget'ın sizeHint'i ~480 px'e ulaşıyor → QStackedWidget tüm
        # sayfalara bu yüksekliği dayatıyordu (Adım 2'de bile butonlar
        # ekrandan dışarı itiliyordu). Intro'yu kendi vertical scroll'una
        # sarıyoruz; sayfa intrinsic yüksekliği 290 px'te kalır, intro
        # içeriği gerekirse kullanıcı sayfada dikey scroll yapar.
        self._page_intro = _SHA256IntroWidget(on_start=self._switch_to_content)
        intro_scroll = QScrollArea()
        intro_scroll.setWidget(self._page_intro)
        intro_scroll.setWidgetResizable(True)
        intro_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        intro_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        intro_scroll.setStyleSheet("background: transparent; border: none;")
        intro_scroll.setMinimumHeight(260)
        self._stack.addWidget(intro_scroll)

        # Sayfa 1 — Mesaj Hazırlığı (yeni, Adım 1/5)
        self._page_msgprep = self._make_msgprep_page()
        self._stack.addWidget(self._page_msgprep)

        # Sayfa 2 — Padding (Adım 2/5)
        self._page_padding = self._make_padding_page()
        self._stack.addWidget(self._page_padding)

        # Sayfa 3 — Mesaj Genişletme (W_i) (Adım 3/5)
        self._page_wexpand = self._make_wexpand_page()
        self._stack.addWidget(self._page_wexpand)

        # Sayfa 4 — Kompresyon diyagramı (Adım 4/5, tüm snapshot'lar için tek sayfa, veri güncellenir)
        self._page_diagram = self._make_diagram_page()
        self._stack.addWidget(self._page_diagram)

        # Sayfa 5 — Eşleşme (Adım 5/5)
        self._page_match = self._make_match_page()
        self._stack.addWidget(self._page_match)

        # Intro animasyonunu başlat
        self._page_intro.start()

    def _make_msgprep_page(self) -> QWidget:
        """Yeni Mesaj Hazırlığı sayfası — _SHAMessagePrepWidget içerir.
        Widget üste hizalanır ki büyük pencerelerde alt boşluk olmasın."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)
        self._msgprep_widget = _SHAMessagePrepWidget(
            message_text=self._data["message_text"],
            message_bytes=self._data["message_bytes"],
            on_finished=self._on_msgprep_finished,
        )
        lay.addWidget(self._msgprep_widget, alignment=Qt.AlignmentFlag.AlignTop)
        return w

    def _on_msgprep_finished(self) -> None:
        """Mesaj Hazırlığı animasyonu bittiğinde — İleri butonu zaten manuel."""
        # Manuel modda buton zaten enabled, ek aksiyon gerekmez.
        # Bu callback, gelecekte buton durum yönetimi gerekirse genişler.
        pass

    def _make_padding_page(self) -> QWidget:
        """Yeni padding sayfası — _SHA256PaddingWidget içerir.
        Outer QScrollArea kaldırıldı: widget zaten kompakt, scroll gerekmez."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        self._padding_widget = _SHA256PaddingWidget(
            message_bytes=self._data["message_bytes"],
            padded_bytes=self._data["padded_bytes"],
            blocks_count=self._data["blocks_count"],
            message_text=self._data["message_text"],
        )
        lay.addWidget(self._padding_widget, alignment=Qt.AlignmentFlag.AlignTop)
        return w

    def _make_wexpand_page(self) -> QWidget:
        """Mesaj genişletme sayfası — _WExpansionWidget içerir.
        Widget min 340 px; içerik kompakt sayfalarda bile stack'in tercih
        yüksekliğini büyütüyordu. Scroll'a sararak sayfanın doğal yüksekliği
        ~290 px'te kalır, alt navigasyon butonları daima görünür."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Adım 2 — Mesaj Genişletme (Message Schedule)")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_mauve']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        widget = _WExpansionWidget(self._data.get("w_expansion") or [])
        wexp_scroll = QScrollArea()
        wexp_scroll.setWidget(widget)
        wexp_scroll.setWidgetResizable(True)
        wexp_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        wexp_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        wexp_scroll.setStyleSheet("background: transparent; border: none;")
        wexp_scroll.setMinimumHeight(260)
        lay.addWidget(wexp_scroll, stretch=1)
        return w

    def _make_diagram_page(self) -> QWidget:
        # Sayfa düzeni:
        #   - Başlık (Blok N / Sıkıştırma Round M)
        #   - Round bar (tıklanabilir 9 buton: R1, R9, R17, ..., R64)
        #     + çok blok varsa solda blok seçici (◀ Blok N/M Blok ▶)
        #   - Diyagram widget'ı QScrollArea'da (stack height kontrolü)
        #   - Hash zinciri göstergesi
        #
        # Round bar AES'in tıklanabilir round bar deseninden esinleniyor;
        # kullanıcı bottom-bar ◀/▶ butonlarına gitmeden diyagramda
        # roundlar arası gezebilir.
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(4)

        self._diag_title = QLabel()
        self._diag_title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        self._diag_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._diag_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._diag_title)

        # Round bar (tıklanabilir 9 buton — her snapshot için). Çok blok
        # varsa solda blok navigasyonu.
        rb_frame = QFrame()
        rb_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px; }}"
        )
        rb_lay = QHBoxLayout(rb_frame)
        rb_lay.setContentsMargins(6, 4, 6, 4)
        rb_lay.setSpacing(4)

        # Blok navigasyonu — yalnızca >1 blok varsa
        self._diag_blk_prev: QPushButton | None = None
        self._diag_blk_next: QPushButton | None = None
        self._diag_blk_lbl: QLabel | None = None
        if self._data["blocks_count"] > 1:
            self._diag_blk_prev = QPushButton("◀ Blok")
            self._diag_blk_prev.setFixedHeight(28)
            self._diag_blk_prev.setFont(QFont("IBM Plex Sans", 9))
            self._diag_blk_prev.clicked.connect(
                lambda: self._diag_jump_block(-1))
            rb_lay.addWidget(self._diag_blk_prev)

            self._diag_blk_lbl = QLabel(f"Blok 1 / {self._data['blocks_count']}")
            self._diag_blk_lbl.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            self._diag_blk_lbl.setStyleSheet(
                f"color: {ANIM_COLORS['accent_yellow']};")
            self._diag_blk_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._diag_blk_lbl.setMinimumWidth(80)
            rb_lay.addWidget(self._diag_blk_lbl)

            self._diag_blk_next = QPushButton("Blok ▶")
            self._diag_blk_next.setFixedHeight(28)
            self._diag_blk_next.setFont(QFont("IBM Plex Sans", 9))
            self._diag_blk_next.clicked.connect(
                lambda: self._diag_jump_block(+1))
            rb_lay.addWidget(self._diag_blk_next)

            sep = QLabel("│")
            sep.setStyleSheet(f"color: {ANIM_COLORS['border']};")
            rb_lay.addWidget(sep)

        # Round buton dizisi — 9 buton (snapshot başına bir tane)
        self._diag_round_btns: list[QPushButton] = []
        round_labels = ["R1", "R9", "R17", "R25", "R33", "R41", "R49", "R57", "R64"]
        for idx, lbl in enumerate(round_labels):
            btn = QPushButton(lbl)
            btn.setFixedWidth(40)
            btn.setFixedHeight(28)
            btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            btn.setStyleSheet(self._diag_round_btn_style(False))
            btn.clicked.connect(lambda checked=False, i=idx: self._diag_jump_round(i))
            rb_lay.addWidget(btn)
            self._diag_round_btns.append(btn)

        rb_lay.addStretch()
        lay.addWidget(rb_frame)

        # Diyagramı dikey scroll içine al — sayfa intrinsic yüksekliği 300 px
        # civarında kalır; diyagramın 460 px min height'i stack'i büyütmez.
        self._diag_widget = _SHA256DiagramWidget()
        diag_scroll = QScrollArea()
        diag_scroll.setWidget(self._diag_widget)
        diag_scroll.setWidgetResizable(True)
        diag_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        diag_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        diag_scroll.setStyleSheet("background: transparent; border: none;")
        diag_scroll.setMinimumHeight(230)
        lay.addWidget(diag_scroll, stretch=1)

        # Hash zinciri göstergesi (alt)
        self._chain_lbl = QLabel()
        self._chain_lbl.setFont(QFont("Courier New", 10))
        self._chain_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._chain_lbl.setWordWrap(True)
        self._chain_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._chain_lbl)
        return w

    @staticmethod
    def _diag_round_btn_style(active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
                f"color: {ANIM_COLORS['bg_main']}; border: none; "
                f"border-radius: 4px; font-weight: bold; }}"
            )
        return (
            f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_muted']}; border: none; "
            f"border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['border']}; "
            f"color: {ANIM_COLORS['text_primary']}; }}"
        )

    def _diag_jump_round(self, round_idx_in_block: int) -> None:
        """Round bar'daki butonla aynı blok içinde başka bir snapshot'a atla.
        round_idx_in_block: 0..8 (R1, R9, R17, ..., R64'e karşılık gelir)."""
        # Mevcut blok numarasını current_step'ten çıkar
        cur_snap_idx = self.current_step - 3
        if cur_snap_idx < 0 or cur_snap_idx >= len(self._snaps):
            cur_block = 0
        else:
            cur_block = cur_snap_idx // _SNAPS_PER_BLOCK
        target_snap_idx = cur_block * _SNAPS_PER_BLOCK + round_idx_in_block
        if target_snap_idx >= len(self._snaps):
            return
        self._diag_jump_to_step(3 + target_snap_idx)

    def _diag_jump_block(self, delta: int) -> None:
        """◀ Blok / Blok ▶ butonu — aynı round (snapshot in-block index)
        konumunu koruyarak farklı bloka atla."""
        cur_snap_idx = self.current_step - 3
        if cur_snap_idx < 0 or cur_snap_idx >= len(self._snaps):
            return
        cur_block = cur_snap_idx // _SNAPS_PER_BLOCK
        in_block_idx = cur_snap_idx % _SNAPS_PER_BLOCK
        new_block = cur_block + delta
        if new_block < 0 or new_block >= self._data["blocks_count"]:
            return
        target_snap_idx = new_block * _SNAPS_PER_BLOCK + in_block_idx
        if target_snap_idx >= len(self._snaps):
            return
        self._diag_jump_to_step(3 + target_snap_idx)

    def _diag_jump_to_step(self, target_step: int) -> None:
        """Diyagram sayfasındaki butonlardan birine basıldığında modal'ın
        current_step / progress / bottom button state'ini güncelleyerek
        hedef adıma atla (AES'in _jump_to_round desenine paralel)."""
        self.current_step = target_step
        self._render_step(target_step)
        self._progress.setValue(target_step + 1)
        if hasattr(self, "_btn_prev"):
            self._btn_prev.setEnabled(target_step > 0)
        if hasattr(self, "_btn_next"):
            self._btn_next.setEnabled(True)
            self._btn_next.setText("İleri  ▶")

    def _diag_update_round_bar(self, in_block_idx: int) -> None:
        for i, btn in enumerate(self._diag_round_btns):
            btn.setStyleSheet(self._diag_round_btn_style(i == in_block_idx))

    def _make_match_page(self) -> QWidget:
        """Final eşleşme sayfası — _MatchAssemblyWidget içerir.
        Widget setMinimumHeight(460) ile QStackedWidget'ın max sizeHint'ini
        domine ediyordu → diğer kompakt sayfalarda bile modal'ın tercih
        yüksekliği 460+ olunca alice panelindeki viewport'a sığmıyor,
        kullanıcı butonları görmek için dikey scroll yapmak zorunda kalıyordu.
        Match widget'ı kendi dikey QScrollArea'sına sararak bu 460 px talebi
        sayfanın doğal yüksekliğine yansımıyor (sayfa ~290 px'te kalıyor)."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Final Hash Eşleşmesi")
        title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        self._match_widget = _MatchAssemblyWidget()
        match_scroll = QScrollArea()
        match_scroll.setWidget(self._match_widget)
        match_scroll.setWidgetResizable(True)
        match_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        match_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        match_scroll.setStyleSheet("background: transparent; border: none;")
        match_scroll.setMinimumHeight(260)
        lay.addWidget(match_scroll, stretch=1)
        return w

    # ------------------------------------------------------------------
    # Adım render'ı
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if step_idx == 0:
            self._stack.setCurrentWidget(self._page_msgprep)
            self._msgprep_widget.start()
            return
        if step_idx == 1:
            self._stack.setCurrentWidget(self._page_padding)
            self._padding_widget.start()
            return
        if step_idx == 2:
            self._stack.setCurrentWidget(self._page_wexpand)
            return

        # step_idx 3..len(snaps)+2 → snapshot[step_idx - 3]
        snap_idx = step_idx - 3
        if snap_idx >= len(self._snaps):
            return

        snap = self._snaps[snap_idx]
        self._stack.setCurrentWidget(self._page_diagram)

        # Hangi blok, hangi round?
        snap_round = snap["round"]
        block_no = snap_idx // _SNAPS_PER_BLOCK + 1
        in_block_idx = snap_idx % _SNAPS_PER_BLOCK
        self._diag_title.setText(
            f"Blok {block_no} / {self._data['blocks_count']}  —  "
            f"Sıkıştırma Round {snap_round} / 64"
        )
        # Round bar ve blok etiketi senkronize
        self._diag_update_round_bar(in_block_idx)
        if self._diag_blk_lbl is not None:
            self._diag_blk_lbl.setText(
                f"Blok {block_no} / {self._data['blocks_count']}")
        if self._diag_blk_prev is not None:
            self._diag_blk_prev.setEnabled(block_no > 1)
        if self._diag_blk_next is not None:
            self._diag_blk_next.setEnabled(
                block_no < self._data["blocks_count"])

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
        """Final eşleşme sayfasını göster, animasyonu başlat."""
        self._stack.setCurrentWidget(self._page_match)
        self._match_widget.start_animation(
            pre_h=self._data["pre_final_h"],
            working=self._data["final_working"],
            parts=self._data["final_h_parts"],
            computed=self._data["final_hash"],
            expected=self._expected_hash,
        )

    # ------------------------------------------------------------------
    # Navigasyon yardımcıları
    # ------------------------------------------------------------------

    def _switch_to_content(self) -> None:
        """Intro'dan Mesaj Hazırlığı sayfasına geç ve step 0'ı render et."""
        self._render_step(0)
        self._progress.setValue(1)

    # showEvent override — intro kendi timer'ını yönetiyor, base class'ı atla
    def showEvent(self, event) -> None:  # type: ignore[override]
        QWidget.showEvent(self, event)
