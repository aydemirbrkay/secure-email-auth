# animation_modals/rsa/arithmetic.py
"""Adım 2-4 — n = p×q, ϕ(n), gcd doğrulaması widget'ları."""
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
from ..base import CryptoAnimationWindow, ANIM_COLORS
from . import helpers as H

# ---------------------------------------------------------------------------
# 3) Adım 2 — Çarpma  n = p × q
# ---------------------------------------------------------------------------

class _MultiplicationWidget(QWidget):
    """p × q animasyonu — q'nun her basamağı için ayrı satır + toplam."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Çarpma satırlarını cari H._P, H._Q'ya göre dinamik üret
        self._ROWS = self._compute_rows(H._P, H._Q)
        self._reveal = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    @staticmethod
    def _compute_rows(p: int, q: int) -> list[tuple[str, str, int]]:
        """q'nun her basamağı için 'p × <basamak değeri>' satırı + toplam."""
        rows: list[tuple[str, str, int]] = []
        for i, ch in enumerate(reversed(str(q))):
            digit = int(ch)
            if digit == 0:
                continue
            place = digit * (10 ** i)
            rows.append((f"{p} × {place}", f"= {p * place}", 0))
        rows.append(("─" * 18, "", 1))
        rows.append(("Toplam", f"= {p * q}", 2))
        return rows

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._reveal = 0
        self.update()
        self._timer.start(700)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if self._reveal < len(self._ROWS) + 1:
            self._reveal += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()  # NOT: 'H' helpers modül takma adı; gölgelememek için yalnız W
        cx = W // 2
        top_y = 8

        # Başlık formülü
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(
            QRect(0, top_y, W, 26),
            Qt.AlignmentFlag.AlignCenter,
            "n = p × q",
        )

        # p ve q kutuları
        box_w, box_h = 70, 42
        gap = 22
        boxes_y = top_y + 36
        p_x = cx - box_w - gap
        q_x = cx + gap

        self._draw_boxed(p, p_x, boxes_y, box_w, box_h, str(H._P),
                         ANIM_COLORS["accent_blue"], font_size=14)
        # × sembolü
        p.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(
            QRect(p_x + box_w, boxes_y, gap * 2, box_h),
            Qt.AlignmentFlag.AlignCenter,
            "×",
        )
        self._draw_boxed(p, q_x, boxes_y, box_w, box_h, str(H._Q),
                         ANIM_COLORS["accent_mauve"], font_size=14)

        # Çarpma satırları (kademeli açılır)
        rows_y = boxes_y + box_h + 14
        line_h = 22
        p.setFont(QFont("Courier New", 11))
        for i, (left, right, kind) in enumerate(self._ROWS):
            if i >= self._reveal:
                break
            y = rows_y + i * line_h
            if kind == 1:
                # Yatay ayırıcı çizgi — toplama altı (yarım dash dizisi yerine
                # gerçek bir tam genişlikte çizgi, satırın ortasından geçer).
                line_y = y + line_h // 2
                p.setPen(QPen(QColor(ANIM_COLORS["text_muted"]), 1))
                p.drawLine(cx - 180, line_y, cx + 180, line_y)
                continue
            if kind == 2:
                p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
                p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
            else:
                p.setPen(QColor(ANIM_COLORS["text_secondary"]))
                p.setFont(QFont("Courier New", 11))
            p.drawText(
                QRect(cx - 180, y, 180, line_h),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                left + "  ",
            )
            p.drawText(
                QRect(cx, y, 180, line_h),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                right,
            )

        # Sonuç kutusu (tüm satırlar açıldıktan sonra)
        if self._reveal >= len(self._ROWS) + 1:
            result_y = rows_y + (len(self._ROWS) + 1) * line_h
            self._draw_boxed(
                p, cx - 70, result_y, 140, 38, f"n = {H._N}",
                ANIM_COLORS["accent_yellow"], font_size=12,
            )

        p.end()

    @staticmethod
    def _draw_boxed(
        p: QPainter, x: int, y: int, w: int, h: int, text: str,
        color: str, font_size: int = 16,
    ) -> None:
        fill = QColor(color)
        fill.setAlpha(60)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(color), 2))
        p.drawRoundedRect(x, y, w, h, 8, 8)
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.setFont(QFont("Georgia", font_size, QFont.Weight.Bold))
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)


# ---------------------------------------------------------------------------
# 4) Adım 3 — Euler Totient  ϕ(n) = (p−1)(q−1)
# ---------------------------------------------------------------------------

class _TotientWidget(QWidget):
    """ϕ(n) hesabı: (p−1) ve (q−1) elde edilir, sonra çarpılır."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._phase = 0
        self.update()
        self._timer.start(800)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if self._phase < 4:
            self._phase += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()  # NOT: 'H' helpers modül takma adı; gölgelememek için yalnız W
        cx = W // 2

        # Formül başlığı
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 8, W, 26), Qt.AlignmentFlag.AlignCenter,
                   "ϕ(n) = (p − 1) × (q − 1)")

        # Üst satır: p ve q kutularından (p−1) ve (q−1) türetimi
        row1_y = 44
        box_w, box_h = 84, 38     # 60 → 84: "p−1 = 60" gibi etiketler için
        gap = 18
        arrow_gap = 24
        # Sol blok: box(p) + arrow_gap + box(p-1)
        block_w = box_w + arrow_gap + box_w
        # Toplam satır genişliği: sol blok + ara boşluk + sağ blok
        total_w = block_w * 2 + 30
        left_x = cx - total_w // 2

        # p kutusu → p−1 kutusu
        self._draw_box(p, left_x, row1_y, box_w, box_h,
                       f"p = {H._P}", ANIM_COLORS["accent_blue"])
        self._draw_arrow(p, left_x + box_w, row1_y + box_h // 2,
                         left_x + box_w + 22, row1_y + box_h // 2)
        if self._phase >= 1:
            self._draw_box(p, left_x + box_w + 24, row1_y, box_w, box_h,
                           f"p−1 = {H._P-1}", ANIM_COLORS["accent_green"])

        # q kutusu → q−1 kutusu
        right_x = left_x + block_w + 30
        self._draw_box(p, right_x, row1_y, box_w, box_h,
                       f"q = {H._Q}", ANIM_COLORS["accent_mauve"])
        self._draw_arrow(p, right_x + box_w, row1_y + box_h // 2,
                         right_x + box_w + 22, row1_y + box_h // 2)
        if self._phase >= 2:
            self._draw_box(p, right_x + box_w + 24, row1_y, box_w, box_h,
                           f"q−1 = {H._Q-1}", ANIM_COLORS["accent_green"])

        # Orta satır: çarpma
        if self._phase >= 3:
            mid_y = row1_y + box_h + 18
            p.setFont(QFont("Courier New", 12))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(
                QRect(0, mid_y, W, 24),
                Qt.AlignmentFlag.AlignCenter,
                f"({H._P-1})  ×  ({H._Q-1})  =  {(H._P-1)*(H._Q-1)}",
            )

        # Alt satır: sonuç
        if self._phase >= 4:
            result_y = row1_y + box_h + 56
            self._draw_box(
                p, cx - 90, result_y, 180, 44,
                f"ϕ(n) = {H._PHI}", ANIM_COLORS["accent_yellow"],
                font_size=13,
            )
        p.end()

    @staticmethod
    def _draw_box(
        p: QPainter, x: int, y: int, w: int, h: int, text: str,
        color: str, font_size: int = 11,
    ) -> None:
        fill = QColor(color)
        fill.setAlpha(60)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(color), 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.setFont(QFont("Georgia", font_size, QFont.Weight.Bold))
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)

    @staticmethod
    def _draw_arrow(p: QPainter, x1: int, y1: int, x2: int, y2: int) -> None:
        pen = QPen(QColor(ANIM_COLORS["text_muted"]), 2)
        p.setPen(pen)
        p.drawLine(x1, y1, x2, y2)
        # Ok ucu
        p.setBrush(QBrush(QColor(ANIM_COLORS["text_muted"])))
        head = QPolygon([
            QPoint(x2, y2),
            QPoint(x2 - 8, y2 - 4),
            QPoint(x2 - 8, y2 + 4),
        ])
        p.drawPolygon(head)




# ---------------------------------------------------------------------------
# 5) Adım 4 — gcd doğrulaması
# ---------------------------------------------------------------------------

class _GCDWidget(QWidget):
    """e=17 seçimi ve gcd(e, ϕ(n))=1 doğrulaması — Öklid adımları akar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Öklid adımları: gcd(3120, 17) — büyükten küçüğe başla
        # (küçük olan zaten büyük olanda aranmaz; ilk anlamlı bölme
        # 3120 ÷ 17 olur).
        a, b = max(H._E, H._PHI), min(H._E, H._PHI)
        steps = []
        while b != 0:
            steps.append((a, b, a % b))
            a, b = b, a % b
        self._steps = steps  # son adımdaki b=0 öncesi a, gcd
        self._gcd_value = a
        self._reveal = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._reveal = 0
        self.update()
        self._timer.start(550)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if self._reveal < len(self._steps) + 1:
            self._reveal += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()  # NOT: 'H' helpers modül takma adı; gölgelememek için yalnız W
        cx = W // 2

        # Başlık
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 8, W, 26), Qt.AlignmentFlag.AlignCenter,
                   f"Aday:  e = {H._E}    Koşul:  gcd(e, ϕ(n)) = 1")

        # Öklid adımları
        rows_y = 42
        line_h = 22
        p.setFont(QFont("Courier New", 11))
        for i, (a, b, r) in enumerate(self._steps):
            if i >= self._reveal:
                break
            y = rows_y + i * line_h

            is_last = (r == 0)
            color = (ANIM_COLORS["accent_green"] if is_last
                     else ANIM_COLORS["text_secondary"])
            p.setPen(QColor(color))
            text = f"{a}  =  {a // b} × {b}  +  {r}"
            p.drawText(QRect(0, y, W, line_h),
                       Qt.AlignmentFlag.AlignCenter, text)

        # Sonuç — kullanıcı "e bulundu" mesajını net görmeli, sadece "GCD=1
        # ✓ Geçerli" yetersizdi. Başarılıysa: "e = 17 SEÇİLDİ  (gcd=1 ✓)".
        if self._reveal >= len(self._steps) + 1:
            result_y = rows_y + (len(self._steps) + 1) * line_h + 8
            success = (self._gcd_value == 1)
            color = (ANIM_COLORS["accent_green"] if success
                     else ANIM_COLORS["accent_peach"])
            fill = QColor(color)
            fill.setAlpha(60)
            box_w, box_h = 320, 48
            x = cx - box_w // 2
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor(color), 2))
            p.drawRoundedRect(x, result_y, box_w, box_h, 6, 6)

            if success:
                # Sonuç başlığı — büyük ve net: "e = 17 SEÇİLDİ"
                p.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
                p.setPen(QColor(color))
                p.drawText(
                    QRect(x, result_y + 2, box_w, 24),
                    Qt.AlignmentFlag.AlignCenter,
                    f"e = {H._E}   ✓  SEÇİLDİ",
                )
                # Alt açıklama — gerekçe
                p.setFont(QFont("Georgia", 9))
                p.setPen(QColor(ANIM_COLORS["text_secondary"]))
                p.drawText(
                    QRect(x, result_y + 26, box_w, 18),
                    Qt.AlignmentFlag.AlignCenter,
                    f"(gcd(e, ϕ(n)) = {self._gcd_value}, koşul sağlandı)",
                )
            else:
                p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["text_primary"]))
                p.drawText(
                    QRect(x, result_y, box_w, box_h),
                    Qt.AlignmentFlag.AlignCenter,
                    f"GCD = {self._gcd_value}   ✗  REDDEDİLDİ",
                )
        p.end()



