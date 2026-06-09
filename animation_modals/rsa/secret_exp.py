# animation_modals/rsa/secret_exp.py
"""Adım 5 — Gizli üs d (e·d = 1 + k·ϕ doğrudan arama) widget'ı."""
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
# 6) Adım 5 — Gizli üs d (doğrudan arama: e·d = 1 + k·ϕ)
# ---------------------------------------------------------------------------

class _EEAWidget(QWidget):
    """
    d (gizli üs) hesaplama — DOĞRUDAN ARAMA yöntemi.

    Klasik EEA yerine kullanıcının pedagojik tercih ettiği "k bul, böl"
    yaklaşımı:

        e · d ≡ 1 (mod ϕ)   ⇒   e · d = 1 + k · ϕ
                            ⇒   d = (1 + k · ϕ) / e

    k = 1, 2, 3, ... için bölme tam sayı çıkana kadar denenir. İlk başarılı
    k'da d bulunmuştur. Sınıf adı geriye dönük uyumluluk için "_EEAWidget"
    olarak korunur.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._iterations = self._compute_iterations()

    @staticmethod
    def _compute_iterations() -> list[tuple[int, int, float, int, bool]]:
        """Her k için (k, num, q_float, q_int_or_0, success) listesi.

        Başarılıda q_int gerçek bölüm; başarısızda q_float gösterilir.
        """
        out: list[tuple[int, int, float, int, bool]] = []
        for k in range(1, H._E + 1):
            num = 1 + k * H._PHI
            q_float = num / H._E
            ok = (num % H._E == 0)
            q_int = num // H._E if ok else 0
            out.append((k, num, q_float, q_int, ok))
            if ok:
                break
        return out

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()  # NOT: 'H' helpers modül takma adı; gölgelememek için yalnız W

        # Başlık
        p.setFont(QFont("Georgia", 13, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 6, W, 26), Qt.AlignmentFlag.AlignCenter,
                   "Gizli Üs d'nin Bulunması")

        # Amaç — neden böyle yapıyoruz
        p.setFont(QFont("Georgia", 10))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(0, 34, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "Amaç:  e · d ≡ 1 (mod ϕ)   ⇒   e · d = 1 + k · ϕ   ⇒   d = (1 + k · ϕ) / e")

        # Strateji
        p.setFont(QFont("Georgia", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 54, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "k = 1, 2, 3, … için böl;  ilk tam sayı çıkan k'da  d  bulunmuştur.")

        # Bilinen değerler
        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_peach"]))
        p.drawText(QRect(0, 76, W, 20), Qt.AlignmentFlag.AlignCenter,
                   f"ϕ = {H._PHI},   e = {H._E}")

        # İterasyonlar (max 5 başarısız + 1 başarılı satır; arada ⋮)
        iters = self._iterations
        if len(iters) > 6:
            visible: list[tuple[int, int, float, int, bool] | None] = (
                list(iters[:4]) + [None] + [iters[-1]]
            )
        else:
            visible = list(iters)

        row_y = 104
        line_h = 24

        # Satırların en uzunu için adaptif font seç
        sample_lines = []
        for it in visible:
            if it is None:
                continue
            k, num, qf, qi, ok = it
            if ok:
                sample_lines.append(
                    f"k = {k}:  (1 + {k} · {H._PHI}) / {H._E}  =  {num} / {H._E}  =  {qi}   ✓ bulundu"
                )
            else:
                sample_lines.append(
                    f"k = {k}:  (1 + {k} · {H._PHI}) / {H._E}  =  {num} / {H._E}  =  {qf:.3f}…   ✗"
                )
        avail_w = W - 16
        row_pt = 11
        for pt in (11, 10, 9, 8):
            p.setFont(QFont("Courier New", pt))
            longest = max(sample_lines, key=lambda s: p.fontMetrics().horizontalAdvance(s)) if sample_lines else ""
            if not longest or p.fontMetrics().horizontalAdvance(longest) <= avail_w:
                row_pt = pt
                break
        else:
            row_pt = 8

        success_color = QColor(ANIM_COLORS["accent_green"])
        fail_color = QColor(ANIM_COLORS["text_muted"])

        for i, it in enumerate(visible):
            y = row_y + i * line_h
            if it is None:
                p.setFont(QFont("Courier New", row_pt))
                p.setPen(fail_color)
                p.drawText(QRect(0, y, W, line_h),
                           Qt.AlignmentFlag.AlignCenter, "⋮")
                continue
            k, num, qf, qi, ok = it
            color = success_color if ok else fail_color
            font = QFont("Courier New", row_pt,
                         QFont.Weight.Bold if ok else QFont.Weight.Normal)
            p.setFont(font)
            p.setPen(color)
            if ok:
                line = (
                    f"k = {k}:  (1 + {k} · {H._PHI}) / {H._E}  =  {num} / {H._E}"
                    f"  =  {qi}   ✓ bulundu"
                )
            else:
                line = (
                    f"k = {k}:  (1 + {k} · {H._PHI}) / {H._E}  =  {num} / {H._E}"
                    f"  =  {qf:.3f}…   ✗"
                )
            p.drawText(QRect(8, y, W - 16, line_h),
                       Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                       line)

        # Sonuç d
        result_y = row_y + len(visible) * line_h + 16
        p.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        p.setPen(success_color)
        p.drawText(QRect(0, result_y, W, 26),
                   Qt.AlignmentFlag.AlignCenter, f"d = {H._D}")

        # Doğrulama — kongrüans formunda (e·d ≡ 1 mod ϕ)
        verify_y = result_y + 36
        check = (H._E * H._D) % H._PHI
        symbolic = "Doğrulama:  e · d  ≡  1  (mod ϕ)"
        numeric = f"{H._E} · {H._D}  =  {H._E * H._D}  ≡  {check}  (mod {H._PHI})   ✓"

        ver_pt = 11
        for pt in (11, 10, 9, 8):
            p.setFont(QFont("Courier New", pt, QFont.Weight.Bold))
            longest = max(symbolic, numeric, key=lambda s: p.fontMetrics().horizontalAdvance(s))
            if p.fontMetrics().horizontalAdvance(longest) <= avail_w:
                ver_pt = pt
                break
        else:
            ver_pt = 8

        p.setFont(QFont("Courier New", ver_pt, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(8, verify_y, W - 16, 22),
                   Qt.AlignmentFlag.AlignCenter, symbolic)
        p.drawText(QRect(8, verify_y + 22, W - 16, 22),
                   Qt.AlignmentFlag.AlignCenter, numeric)

        p.end()



