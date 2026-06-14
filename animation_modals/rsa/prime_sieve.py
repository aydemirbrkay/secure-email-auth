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
    """2..100 arası sayılar 10×10 grid; asallar yeşil; p, q yanıp söner.

    Elle seçim modu (`set_custom_mode(True)`): kullanıcı ızgaradaki asallara
    (yalnız 11–97 havuzu) tıklayarak p ve q'yu kendisi seçer. Geçerli çift
    uygulanınca `on_applied` callback'i ile pencereye bildirilir.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        on_applied: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._blink = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        # Elle seçim durumu
        self._on_applied = on_applied
        self._custom_mode = False
        self._pending_p: int | None = None
        self._status_msg = ""
        self._status_error = False
        # Elle modda kullanıcı kendi p/q çiftini uygulayana dek True olmaz.
        # Devralınan rastgele p/q'nun yanıp sönmesini bastırmak için kullanılır.
        self._has_custom_selection = False

    # ------------------------------------------------------------------
    # Elle seçim modu
    # ------------------------------------------------------------------

    def set_custom_mode(self, on: bool) -> None:
        """Elle seçim modunu açar/kapatır; bekleyen seçimi ve durumu sıfırlar."""
        self._custom_mode = on
        self._pending_p = None
        self._status_msg = ""
        self._status_error = False
        self._has_custom_selection = False
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if on else Qt.CursorShape.ArrowCursor
        )
        self.update()

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

    # ------------------------------------------------------------------
    # Geometri (paintEvent ile mousePressEvent paylaşır)
    # ------------------------------------------------------------------

    def _grid_geometry(self) -> tuple[int, int, int]:
        """Izgaranın (ox, oy, cell) yerleşimini döndürür. paintEvent ve
        mousePressEvent aynı hesabı kullanır ki tıklama hücreyle birebir örtüşsün."""
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
        ox = (width_px - grid_w) // 2
        oy = margin + header_h
        return ox, oy, cell

    def _cell_at(self, pos: QPoint) -> int | None:
        """Verilen piksel konumundaki sayıyı (1..100) ya da None döndürür."""
        ox, oy, cell = self._grid_geometry()
        cols = 10
        col = (pos.x() - ox) // cell
        row = (pos.y() - oy) // cell
        if 0 <= col < cols and 0 <= row < 10:
            n = row * cols + col + 1
            if 1 <= n <= 100:
                return n
        return None

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if not self._custom_mode:
            super().mousePressEvent(event)
            return
        n = self._cell_at(event.pos())
        if n is None:
            return
        # Yalnız gerçekçi havuz (11–97 asalları) seçilebilir.
        if n not in H._PRIME_POOL:
            self._status_msg = "Yalnız 11–97 arası asallar seçilebilir."
            self._status_error = True
            self.update()
            return

        if self._pending_p is None:
            # İlk seçim → p adayı
            self._pending_p = n
            self._status_msg = "Şimdi q için bir asala tıklayın."
            self._status_error = False
            self.update()
            return

        if n == self._pending_p:
            # Aynı hücreye ikinci tık → p seçimini iptal et
            self._pending_p = None
            self._status_msg = "p seçimi iptal edildi; p için bir asala tıklayın."
            self._status_error = False
            self.update()
            return

        # İkinci geçerli asal → çifti uygula
        err = H._apply_custom_pq(self._pending_p, n)
        if err is None:
            self._pending_p = None
            self._status_msg = ""
            self._status_error = False
            self._has_custom_selection = True
            self.update()
            if self._on_applied is not None:
                self._on_applied()
        else:
            self._pending_p = None
            self._status_msg = err
            self._status_error = True
            self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # NOT: 'H' modül takma adıdır (helpers); widget yüksekliği için
        # ayrı bir isim kullanılmalı, aksi halde H gölgelenir ve
        # H._is_prime / H._P / H._Q çağrıları AttributeError ile çöker.
        width_px = self.width()
        margin = 8
        cols = 10
        ox, oy, cell = self._grid_geometry()
        grid_w = cell * cols
        grid_h = cell * 10
        header_h = 22

        # Üst başlık — moda göre değişir
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        if self._custom_mode:
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            if self._pending_p is None:
                header = "Elle seçim  •  p için bir asala (yeşil) tıklayın"
            else:
                header = f"Elle seçim  •  p = {self._pending_p}  •  şimdi q için bir asala tıklayın"
        else:
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            header = "1–100 arası sayılar  •  asallar yeşil  •  p ve q seçili"
        p.drawText(
            QRect(0, 2, width_px, header_h),
            Qt.AlignmentFlag.AlignCenter,
            header,
        )

        for n in range(1, 101):
            i = n - 1
            r, c = divmod(i, cols)
            x = ox + c * cell
            y = oy + r * cell

            is_prime = H._is_prime(n)
            is_pq = (n == H._P or n == H._Q)
            is_pending = (self._custom_mode and n == self._pending_p)
            is_selectable = (self._custom_mode and n in H._PRIME_POOL)
            # Elle modda, kullanıcı kendi çiftini uygulamadan önce devralınan
            # rastgele p/q vurgulanmaz — yanıp sönmesi kullanıcının seçimini
            # gölgeler ("artık onlar üzerinden işlem yapılmayacak").
            show_pq = is_pq and (not self._custom_mode or self._has_custom_selection)

            if is_pending:
                # Bekleyen p adayı — mavi vurgu
                p.setBrush(QBrush(QColor(ANIM_COLORS["accent_blue"] + "55")))
                p.setPen(QPen(QColor(ANIM_COLORS["accent_blue"]), 2))
            elif show_pq:
                if self._custom_mode:
                    # Kullanıcının uyguladığı çift — sabit (yanıp sönmeyen) vurgu.
                    border_col = QColor(ANIM_COLORS["accent_yellow"])
                    fill = QColor(ANIM_COLORS["accent_yellow"])
                    fill.setAlpha(120)
                else:
                    # Otomatik mod — yanıp sönen sarı çerçeve.
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
                # Elle seçim modunda seçilebilir asalları daha belirgin kenarla
                pen_w = 2 if is_selectable else 1
                p.setPen(QPen(QColor(ANIM_COLORS["accent_green"]), pen_w))
            else:
                p.setBrush(QBrush(QColor(ANIM_COLORS["bg_card"])))
                p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))

            p.drawRoundedRect(x + 2, y + 2, cell - 4, cell - 4, 4, 4)

            if is_pending or show_pq:
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

        # Açıklama / durum satırı
        legend_y = oy + grid_h + 10
        if self._custom_mode and self._status_msg:
            color = (ANIM_COLORS["accent_peach"] if self._status_error
                     else ANIM_COLORS["text_secondary"])
            p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(color))
            p.drawText(
                QRect(margin, legend_y, width_px - 2 * margin, 24),
                Qt.AlignmentFlag.AlignCenter,
                self._status_msg,
            )
        elif self._custom_mode and not self._has_custom_selection:
            # Elle modda henüz seçim yapılmadı — devralınan rastgele p/q'yu
            # "Seçilenler" diye göstermek yanıltıcı olur; üst başlık yönlendirir.
            pass
        else:
            p.setFont(QFont("Georgia", 10))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(
                QRect(margin, legend_y, width_px - 2 * margin, 24),
                Qt.AlignmentFlag.AlignCenter,
                f"Seçilenler:  p = {H._P}    q = {H._Q}",
            )
        p.end()
