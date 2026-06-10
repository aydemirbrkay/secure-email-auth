# animation_modals/sha256/register_demo.py
"""SHA-256 intro için A-H register demo widget'ı."""
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
from ..base import CryptoAnimationWindow, ANIM_COLORS, get_animation_tick_ms
from .constants import _REG_COLORS, _REG_LABELS

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
        self._timer.start(get_animation_tick_ms(120))
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

        t2_fill   = QColor(ANIM_COLORS["hl_mauve"] if t2_lit else ANIM_COLORS["bg_card"])
        t2_border = QColor(ANIM_COLORS["accent_mauve"] if t2_lit else ANIM_COLORS["border"])
        p.setBrush(QBrush(t2_fill))
        p.setPen(QPen(t2_border, 2 if t2_lit else 1))
        p.drawRoundedRect(t2_x, mid_y, t2_w, mid_h, 4, 4)
        p.setFont(font_mid)
        # Başlık metni HER ZAMAN accent rengiyle (lit/unlit fark etmez); eskiden
        # unlit iken faint 'border' rengi kullanılıyordu ve başlık hem açık hem
        # koyu temada okunmuyordu.
        p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
        p.drawText(QRect(t2_x + 2, mid_y + 2, t2_w - 4, mid_h // 2),
                   Qt.AlignmentFlag.AlignCenter, "Σ0(A) + Maj(A,.." if compact else "T2 = Σ0(A) + Maj(A,B,C)")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t2_x + 2, mid_y + mid_h // 2, t2_w - 4, mid_h // 2),
                   Qt.AlignmentFlag.AlignCenter, "a1b2c3d4" if t2_lit else "...")

        t1_fill   = QColor(ANIM_COLORS["hl_yellow"] if t1_lit else ANIM_COLORS["bg_card"])
        t1_border = QColor(ANIM_COLORS["accent_yellow"] if t1_lit else ANIM_COLORS["border"])
        p.setBrush(QBrush(t1_fill))
        p.setPen(QPen(t1_border, 2 if t1_lit else 1))
        p.drawRoundedRect(t1_x, mid_y, t1_w, mid_h, 4, 4)
        # Başlık her zaman accent rengiyle (unlit faint 'border' yerine) →
        # her iki temada okunur.
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
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


