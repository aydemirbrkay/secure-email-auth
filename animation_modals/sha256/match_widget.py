# animation_modals/sha256/match_widget.py
"""SHA-256 final hash eşleşme animasyonu."""
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
from .constants import _REG_LABELS

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


