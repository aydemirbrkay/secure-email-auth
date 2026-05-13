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
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

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
        # AddRoundKey overlay için round_key (yarı-boyutlu 4×4 grid) sağda
        # gösterilir: 4*28 + 3*2 = 118 + 14 gap + 12 right margin = 144 px ek alan
        rk_extra = 4 * (self._CELL_W // 2) + 3 * 2 + 14 + 12  # 144
        total_w = (
            self._LABEL_W + 4 * self._CELL_W + 3 * self._CELL_GAP + 12 + rk_extra
        )
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
        """AddRoundKey koreografisi — round_key sağdan kayarak gelir,
        16 hücreye sırayla ⊕ sembolü ve sonuç değeri yerleşir.

        Faz haritası (toplam 60 tick):
          0–15 : KEY_REVEAL    — round_key sağdan kayarak gelir
          16–55: XOR_PER_ROW   — 4 satır × 10 tick, her satırda 4 hücre yanar
          56–59: FADEOUT       — round_key fade-out

        round_key, yan widget'a sığması için yarı boyutlu hücrelerle
        gösterilir (28×22 yerine main matrix'in 56×44'üne).
        """
        if self._round_key is None:
            return

        t = self._tick
        accent = QColor(ANIM_COLORS["accent_peach"])

        # round_key hücre boyutu — main matrix'in YARISI
        rk_cw = self._CELL_W // 2     # 28
        rk_ch = self._CELL_H // 2     # 22
        rk_gap = 2
        rk_w = 4 * rk_cw + 3 * rk_gap  # 118

        # round_key overlay'in başlangıç ve son x pozisyonu
        # Hedef: main matrix'in sağında, 14 px boşlukla
        matrix_right = ox + 4 * self._CELL_W + 3 * self._CELL_GAP
        rk_target_x = matrix_right + 14
        rk_start_x = self.width() + 10
        if t <= 15:
            progress = t / 15.0
            rk_x = int(rk_start_x + (rk_target_x - rk_start_x) * progress)
            rk_alpha = progress
        elif t < 56:
            rk_x = rk_target_x
            rk_alpha = 1.0
        else:
            # Fadeout
            progress = (t - 55) / 5.0
            rk_x = rk_target_x
            rk_alpha = max(0.0, 1.0 - progress)

        # "rk" başlığı
        title_col = QColor(ANIM_COLORS["accent_peach"])
        title_col.setAlphaF(rk_alpha)
        p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
        p.setPen(title_col)
        p.drawText(QRect(rk_x, oy - 14, rk_w, 12),
                   Qt.AlignmentFlag.AlignCenter, "round_key")

        # round_key 4×4 grid çiz (yarı boyutta)
        for r in range(4):
            for c in range(4):
                cx = rk_x + c * (rk_cw + rk_gap)
                cy = oy + r * (rk_ch + rk_gap)
                # Yarı-boyutlu hücre — _draw_cell kullanma, inline çiz
                bg_color = QColor(ANIM_COLORS["accent_peach"])
                bg_color.setAlphaF(rk_alpha * 0.35)
                border_color = QColor(ANIM_COLORS["accent_peach"])
                border_color.setAlphaF(rk_alpha)
                p.setBrush(QBrush(bg_color))
                p.setPen(QPen(border_color, 1))
                p.drawRoundedRect(cx, cy, rk_cw, rk_ch, 3, 3)
                text_col = QColor(ANIM_COLORS["text_primary"])
                text_col.setAlphaF(rk_alpha)
                p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
                p.setPen(text_col)
                p.drawText(QRect(cx, cy, rk_cw, rk_ch),
                           Qt.AlignmentFlag.AlignCenter, self._round_key[r][c])

        # Faz 2: sırayla hücreleri XOR (main matrix'te)
        if 16 <= t < 56:
            phase_t = t - 16  # 0..39
            cells_active = min(16, phase_t // 2 + 1)  # her 2 tick'te 1 yeni hücre
            for idx in range(cells_active):
                r = idx // 4
                c = idx % 4
                cx, cy = self._cell_xy(ox, oy, r, c)
                # Vurgu çerçevesi
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(accent, 2))
                p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)
                # Mini ⊕ rozeti
                p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
                p.setPen(accent)
                p.drawText(QRect(cx + self._CELL_W - 14, cy + 2, 12, 12),
                           Qt.AlignmentFlag.AlignCenter, "⊕")
                # _state'i bu hücre için after değerine yükselt
                if (self._state[r][c] != self._after[r][c]):
                    self._state[r][c] = self._after[r][c]

    def _draw_overlay_subbytes(self, p: QPainter, ox: int, oy: int) -> None:
        """SubBytes koreografisi — 16 hücre row-major sırayla S-Box dönüşümü.

        Hücre başına 4 tick (toplam 64):
          tick 0 : mavi çerçeve (aktif vurgu)
          tick 1 : 'S[xy]=zz' rozeti hücrenin üstünde
          tick 2 : hücre değeri eski → yeni (color flash turuncu→yeşil)
          tick 3 : rozet söner, vurgu kalır
        """
        t = self._tick
        cells_total = 16
        ticks_per_cell = 4

        cell_idx = min(cells_total - 1, t // ticks_per_cell)
        phase_t = t % ticks_per_cell

        accent_blue = QColor(ANIM_COLORS["accent_blue"])
        accent_peach = QColor(ANIM_COLORS["accent_peach"])
        accent_green = QColor(ANIM_COLORS["accent_green"])

        # Tamamlanmış önceki hücreleri yeni değerle güncelle
        for idx in range(cell_idx):
            r = idx // 4
            c = idx % 4
            self._state[r][c] = self._after[r][c]

        # Aktif hücre — vurgu + rozet
        ar = cell_idx // 4
        ac = cell_idx % 4
        cx, cy = self._cell_xy(ox, oy, ar, ac)

        # Vurgu çerçevesi (her zaman aktif hücrede)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(accent_blue, 2))
        p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

        # Hücre değeri color flash:
        # phase 0-1: turuncu (eski) → phase 2: yeşil (yeni)
        if phase_t >= 2:
            self._state[ar][ac] = self._after[ar][ac]
            flash_color = accent_green
        else:
            flash_color = accent_peach
        flash = QColor(flash_color)
        flash.setAlphaF(0.30)
        p.setBrush(QBrush(flash))
        p.setPen(QPen(flash_color, 1))
        p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

        # Rozet (phase 1-2): "S[xy]=zz"
        if 1 <= phase_t <= 2:
            before_val = self._before[ar][ac]
            after_val = self._after[ar][ac]
            p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
            p.setPen(accent_blue)
            badge_text = f"S[{before_val}]={after_val}"
            badge_y = cy - 14 if cy > 18 else cy + self._CELL_H + 2
            p.drawText(QRect(cx - 10, badge_y, self._CELL_W + 20, 14),
                       Qt.AlignmentFlag.AlignCenter, badge_text)

    def _draw_overlay_shiftrows(self, p: QPainter, ox: int, oy: int) -> None:
        pass

    def _draw_overlay_mixcolumns(self, p: QPainter, ox: int, oy: int) -> None:
        pass


class _AESStateCompareWidget(QWidget):
    """Yan yana iki _AESMatrixView + Yeniden Oynat butonu.

    Sol: önceki state (donmuş, set_state ile)
    Orta: aktif operasyon etiketi (renkli ok)
    Sağ: şimdiki state (canlı, play_animation ile)
    Üst sağ: Yeniden Oynat butonu
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        # Üst sağ: Yeniden Oynat butonu
        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self._replay_btn = QPushButton("⟲  Yeniden Oynat")
        self._replay_btn.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; border-radius: 6px; "
            f"padding: 4px 14px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        self._replay_btn.setFixedHeight(28)
        self._replay_btn.clicked.connect(self._on_replay)
        top_row.addWidget(self._replay_btn)
        outer.addLayout(top_row)

        # Orta: önceki view → ok → şimdiki view
        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)
        mid_row.addStretch(1)

        self._prev_view = _AESMatrixView(
            label_title="ÖNCEKİ",
            label_color=ANIM_COLORS["text_muted"],
        )
        mid_row.addWidget(self._prev_view)

        self._arrow_label = QLabel("→")
        self._arrow_label.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        self._arrow_label.setStyleSheet(
            f"color: {ANIM_COLORS['text_muted']};"
        )
        self._arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow_label.setMinimumWidth(120)
        mid_row.addWidget(self._arrow_label)

        self._curr_view = _AESMatrixView(
            label_title="ŞİMDİKİ (canlı)",
            label_color=ANIM_COLORS["accent_blue"],
        )
        mid_row.addWidget(self._curr_view)

        mid_row.addStretch(1)
        outer.addLayout(mid_row)
        outer.addStretch(1)

    def start_step(
        self,
        operation: str,
        before: list[list[str]],
        after: list[list[str]],
        op_color: str,
        *,
        round_key: list[list[str]] | None = None,
    ) -> None:
        """Adımı başlat: önceki donmuş, şimdiki animasyonlu."""
        # Önceki çalışan animasyonu durdur
        self._curr_view.stop_animation()
        # Önceki view'a donmuş before state
        self._prev_view.set_state(before)
        # Ok etiketini güncelle
        self._arrow_label.setText(f"→  {operation}  →")
        self._arrow_label.setStyleSheet(
            f"color: {op_color}; font-weight: bold;"
        )
        # Şimdiki view'a animasyon
        self._curr_view.play_animation(
            operation, before, after, round_key=round_key,
        )

    def show_final(self, final_state: list[list[str]]) -> None:
        """Round 14 sonrası: iki matris de final state, animasyon yok."""
        self._curr_view.stop_animation()
        self._prev_view.set_state(final_state)
        self._curr_view.set_state(final_state)
        self._arrow_label.setText("=  FINAL  =")
        self._arrow_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']}; font-weight: bold;"
        )

    def _on_replay(self) -> None:
        self._curr_view.replay()
