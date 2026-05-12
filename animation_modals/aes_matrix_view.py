# animation_modals/aes_matrix_view.py
"""
_AESMatrixView ve _AESStateCompareWidget — AES state matrisi için
QPainter tabanlı byte-hareket animasyon görünümü.

_AESMatrixView: tek 4×4 matris, statik veya animasyonlu mod.
_AESStateCompareWidget: yan yana iki _AESMatrixView (Önceki / Şimdiki)
                        + Yeniden Oynat butonu.

Operasyon başına koreografi `_draw_overlay_<op>` metodlarında tanımlı
(Task 4-7'de doldurulacak).
"""
from __future__ import annotations
from collections.abc import Callable

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from .base import ANIM_COLORS


class _AESMatrixView(QWidget):
    """Tek bir 4×4 AES state matrisini QPainter ile çizer.

    İki mod:
      - statik: ``set_state(matrix)`` ile dondurulmuş matris
      - animasyonlu: ``play_animation(op, before, after, ...)`` ile koreografi
    """

    # Hücre boyutları
    _CELL_W = 56
    _CELL_H = 44
    _CELL_GAP = 4
    _LABEL_W = 18      # sol r0..r3 etiket sütunu genişliği
    _LABEL_H = 16      # üst c0..c3 etiket satırı yüksekliği
    _TITLE_H = 22      # opsiyonel başlık satırı yüksekliği

    # Animasyon
    _TICK_MS = 40      # 25 fps

    # Operasyon başına toplam tick sayıları
    _TICKS_BY_OP: dict[str, int] = {
        "AddRoundKey": 60,    # ~2.4 s
        "SubBytes":    64,    # ~2.6 s
        "ShiftRows":   80,    # ~3.2 s
        "MixColumns":  80,    # ~3.2 s
    }

    def __init__(
        self,
        *,
        label_title: str = "",
        label_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label_title = label_title
        self._label_color = label_color or ANIM_COLORS["text_secondary"]

        # State
        self._state: list[list[str]] = [["00"] * 4 for _ in range(4)]
        self._before: list[list[str]] = [["00"] * 4 for _ in range(4)]
        self._after: list[list[str]] = [["00"] * 4 for _ in range(4)]
        self._round_key: list[list[str]] | None = None
        self._op: str | None = None
        self._tick: int = 0
        self._total_ticks: int = 0
        self._on_done: Callable[[], None] | None = None

        # Timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_tick)

        # Boyut
        title_h = self._TITLE_H if label_title else 0
        total_w = self._LABEL_W + 4 * self._CELL_W + 3 * self._CELL_GAP + 12
        total_h = (
            title_h + self._LABEL_H + 4 * self._CELL_H + 3 * self._CELL_GAP + 12
        )
        self.setMinimumSize(total_w, total_h)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # --- Public API ---

    def set_state(self, matrix: list[list[str]]) -> None:
        """Animasyonsuz, anlık durum atama (donmuş matris için)."""
        self._state = [row[:] for row in matrix]
        self._op = None
        self._anim_timer.stop()
        self.update()

    def play_animation(
        self,
        operation: str,
        before: list[list[str]],
        after: list[list[str]],
        *,
        round_key: list[list[str]] | None = None,
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """Operasyon koreografisini başlat."""
        if operation not in self._TICKS_BY_OP:
            raise ValueError(f"Bilinmeyen operasyon: {operation}")
        self._op = operation
        self._before = [row[:] for row in before]
        self._after = [row[:] for row in after]
        self._round_key = (
            [row[:] for row in round_key] if round_key is not None else None
        )
        self._state = [row[:] for row in self._before]
        self._tick = 0
        self._total_ticks = self._TICKS_BY_OP[operation]
        self._on_done = on_done
        self._anim_timer.start(self._TICK_MS)
        self.update()

    def replay(self) -> None:
        """En son play_animation çağrısını baştan oyna."""
        if self._op is None:
            return
        self.play_animation(
            self._op, self._before, self._after,
            round_key=self._round_key, on_done=self._on_done,
        )

    def stop_animation(self) -> None:
        """Animasyonu durdur, after state'e atla."""
        self._anim_timer.stop()
        if self._op is not None:
            self._tick = self._total_ticks
            self._state = [row[:] for row in self._after]
        self.update()

    # --- Timer ---

    def _on_tick(self) -> None:
        self._tick += 1
        if self._tick >= self._total_ticks:
            self._anim_timer.stop()
            self._state = [row[:] for row in self._after]
            cb = self._on_done
            self._on_done = None
            self.update()
            if cb is not None:
                cb()
            return
        self.update()

    # --- Çizim ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Başlık (varsa)
        title_h = self._TITLE_H if self._label_title else 0
        if self._label_title:
            p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(self._label_color))
            p.drawText(QRect(0, 4, self.width(), 18),
                       Qt.AlignmentFlag.AlignCenter, self._label_title)

        ox = 6
        oy = title_h + 4

        # Sütun etiketleri (c0..c3)
        p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        for c in range(4):
            x = ox + self._LABEL_W + c * (self._CELL_W + self._CELL_GAP)
            p.drawText(QRect(x, oy, self._CELL_W, self._LABEL_H),
                       Qt.AlignmentFlag.AlignCenter, f"c{c}")

        # Satır etiketleri + hücreler
        cell_oy = oy + self._LABEL_H
        for r in range(4):
            cy = cell_oy + r * (self._CELL_H + self._CELL_GAP)
            # Satır etiketi
            p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(ox, cy, self._LABEL_W, self._CELL_H),
                       Qt.AlignmentFlag.AlignCenter, f"r{r}")
            for c in range(4):
                cx = ox + self._LABEL_W + c * (self._CELL_W + self._CELL_GAP)
                self._draw_cell(p, cx, cy, self._state[r][c])

        # Overlay (animasyon)
        if self._op is not None and 0 <= self._tick < self._total_ticks:
            self._draw_overlay(p, ox + self._LABEL_W, cell_oy)

        p.end()

    def _draw_cell(
        self, p: QPainter, x: int, y: int, value: str,
        *, bg: str | None = None, border: str | None = None,
        alpha: float = 1.0,
    ) -> None:
        bg_color = QColor(bg or ANIM_COLORS["bg_card"])
        bg_color.setAlphaF(alpha)
        border_color = QColor(border or ANIM_COLORS["border"])
        border_color.setAlphaF(alpha)
        p.setBrush(QBrush(bg_color))
        p.setPen(QPen(border_color, 1))
        p.drawRoundedRect(x, y, self._CELL_W, self._CELL_H, 4, 4)
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(alpha)
        p.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        p.setPen(text_col)
        p.drawText(QRect(x, y, self._CELL_W, self._CELL_H),
                   Qt.AlignmentFlag.AlignCenter, value)

    def _cell_xy(self, ox: int, oy: int, r: int, c: int) -> tuple[int, int]:
        """Verilen satır/sütun için hücre sol-üst piksel koordinatı."""
        x = ox + c * (self._CELL_W + self._CELL_GAP)
        y = oy + r * (self._CELL_H + self._CELL_GAP)
        return x, y

    def _draw_overlay(self, p: QPainter, ox: int, oy: int) -> None:
        """Operasyon-özgü overlay. Task 4-7'de doldurulacak."""
        op = self._op
        if op == "AddRoundKey":
            self._draw_overlay_addroundkey(p, ox, oy)
        elif op == "SubBytes":
            self._draw_overlay_subbytes(p, ox, oy)
        elif op == "ShiftRows":
            self._draw_overlay_shiftrows(p, ox, oy)
        elif op == "MixColumns":
            self._draw_overlay_mixcolumns(p, ox, oy)

    # Koreografi hook'ları — Task 4-7'de doldurulacak.
    def _draw_overlay_addroundkey(self, p: QPainter, ox: int, oy: int) -> None:
        pass

    def _draw_overlay_subbytes(self, p: QPainter, ox: int, oy: int) -> None:
        pass

    def _draw_overlay_shiftrows(self, p: QPainter, ox: int, oy: int) -> None:
        pass

    def _draw_overlay_mixcolumns(self, p: QPainter, ox: int, oy: int) -> None:
        pass
