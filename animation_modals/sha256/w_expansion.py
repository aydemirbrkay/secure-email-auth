# animation_modals/sha256/w_expansion.py
"""SHA-256 mesaj genişletme (message schedule) animasyonu."""
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


