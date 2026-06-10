# animation_modals/aes_matrix_view.py
"""
_AESMatrixView ve _AESStateCompareWidget — AES state matrisi için
QPainter tabanlı byte-hareket animasyon görünümü.

_AESMatrixView: tek 4×4 matris, statik veya animasyonlu mod.
_AESStateCompareWidget: yan yana iki _AESMatrixView (Önceki / Şimdiki)
                        + Yeniden Oynat butonu.

Operasyon başına koreografi `_draw_overlay_<op>` metodlarında tanımlıdır:
AddRoundKey (round_key reveal + XOR per cell), SubBytes (hücre hücre
S-Box dönüşümü), ShiftRows (satır vurgusu + ok rozeti), MixColumns
(sütun sütun GF(2⁸) dönüşümü).
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
        # round_key artık ayrı, kalıcı bir matris olarak (bkz.
        # _AESStateCompareWidget._rk_view) gösterildiği için eski sağdaki
        # "round_key overlay" ölü alanı (rk_extra) kaldırıldı; matris yalnızca
        # kendi 4×4 gridini kaplar — boşa giden geniş sağ boşluk artık yok.
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
        # Varsayılan: hücre arka planı bg_input + hafif mavi tint
        # ve 2 px accent_blue çerçeve — bg_card/border gri ikilisinden
        # çok daha belirgin (kullanıcının "matrisi belirgin renge sok"
        # geri bildirimi sonrası).
        if bg is None:
            bg_color = QColor(ANIM_COLORS["accent_blue"])
            bg_color.setAlphaF(alpha * 0.18)
        else:
            bg_color = QColor(bg)
            bg_color.setAlphaF(alpha)
        if border is None:
            border_color = QColor(ANIM_COLORS["accent_blue"])
            border_color.setAlphaF(alpha)
            border_w = 2
        else:
            border_color = QColor(border)
            border_color.setAlphaF(alpha)
            border_w = 1
        p.setBrush(QBrush(bg_color))
        p.setPen(QPen(border_color, border_w))
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
        """Operasyon-özgü overlay — aktif _op'a göre koreografi seçer."""
        op = self._op
        if op == "AddRoundKey":
            self._draw_overlay_addroundkey(p, ox, oy)
        elif op == "SubBytes":
            self._draw_overlay_subbytes(p, ox, oy)
        elif op == "ShiftRows":
            self._draw_overlay_shiftrows(p, ox, oy)
        elif op == "MixColumns":
            self._draw_overlay_mixcolumns(p, ox, oy)

    # Operasyon başına koreografi metodları.
    def _draw_overlay_addroundkey(self, p: QPainter, ox: int, oy: int) -> None:
        """AddRoundKey koreografisi — sonuç hücrelerini sırayla 'state ⊕ key'
        sonucuna yükseltir.

        round_key ARTIK ayrı, kalıcı bir matris olarak (bkz.
        ``_AESStateCompareWidget._rk_view``) gösterildiğinden burada eski
        sağdan-kayan/sönen round_key grid'i çizilmez. Yalnızca aktif matriste
        16 hücre row-major sırayla ⊕ rozetiyle sonuç değerine geçer; böylece
        "ÖNCEKİ ⊕ round_key = ŞİMDİKİ" akışının sonuç tarafı canlanır.

        Faz haritası (toplam 60 tick): her 2 tick'te bir yeni hücre yanar,
        ~32 tick'te 16 hücre tamamlanır; kalan tick'lerde matris son state'te
        sabit kalır (kullanıcı değerleri rahatça okuyabilsin diye).
        """
        t = self._tick
        accent = QColor(ANIM_COLORS["accent_peach"])

        cells_active = min(16, t // 2 + 1)  # her 2 tick'te 1 yeni hücre
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
            if self._state[r][c] != self._after[r][c]:
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
        """ShiftRows koreografisi — satır vurgusu + ok rozeti.

        Faz haritası (toplam 80 tick):
          0–9  : Satır 0 vurgulanır, "sabit" rozeti
          10–29: Satır 1 — vurgu + "← 1 bayt" rozeti, ilk yarıda
                 _state row 1'i _after'a kaydır
          30–49: Satır 2 — vurgu + "← 2 bayt" rozeti
          50–69: Satır 3 — vurgu + "← 3 bayt" rozeti
          70–79: Tüm vurgu söner, matris final after state'inde
        """
        t = self._tick
        row_phases = [
            (0, 10, 0, 0),    # satır 0, sabit
            (10, 30, 1, 1),   # satır 1, shift 1
            (30, 50, 2, 2),   # satır 2, shift 2
            (50, 70, 3, 3),   # satır 3, shift 3
        ]
        accent = QColor(ANIM_COLORS["accent_blue"])

        for r_start, r_end, row, shift in row_phases:
            if r_start <= t < r_end:
                phase_t = t - r_start
                phase_len = r_end - r_start

                # Aktif satırı vurgula (4 hücre çerçevesi)
                for c in range(4):
                    cx, cy = self._cell_xy(ox, oy, row, c)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(accent, 2))
                    p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

                # Satırın sağına ok rozeti / "sabit" etiketi
                row_y = oy + row * (self._CELL_H + self._CELL_GAP)
                p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
                p.setPen(accent)
                lbl = "sabit" if shift == 0 else f"← {shift} bayt"
                p.drawText(
                    QRect(ox + 4 * (self._CELL_W + self._CELL_GAP) + 4,
                          row_y, 90, self._CELL_H),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    lbl,
                )

                # Faz ortasına geldiğimizde _state'i bu satır için _after'a kaydır
                # (görsel olarak "kayma tamamlandı" hissi)
                if phase_len > 0 and phase_t >= phase_len // 2:
                    for c in range(4):
                        self._state[row][c] = self._after[row][c]
                return  # her tick yalnızca bir satır aktif

        # 70-79: tüm satırlar tamamlandı, _state hepsi _after
        for r in range(4):
            for c in range(4):
                self._state[r][c] = self._after[r][c]

    def _draw_overlay_mixcolumns(self, p: QPainter, ox: int, oy: int) -> None:
        """MixColumns koreografisi — 4 sütun sırayla GF(2⁸) dönüşümü.

        Faz haritası (toplam 80 tick), sütun başına 20 tick:
          tick 0–4   : Sütun vurgusu (4 hücre çerçevesi sütun rengi)
          tick 5–14  : Sütun yanında formül balonu, 4 hücre tek tek güncellenir
          tick 15–19 : Balon söner
        """
        t = self._tick
        ticks_per_col = 20
        col_idx = min(3, t // ticks_per_col)
        phase_t = t % ticks_per_col

        col_colors = [
            ANIM_COLORS["accent_blue"],
            ANIM_COLORS["accent_mauve"],
            ANIM_COLORS["accent_yellow"],
            ANIM_COLORS["accent_peach"],
        ]
        col_color = QColor(col_colors[col_idx])

        # Tamamlanmış önceki sütunları kalıcı renkle çiz
        for completed_c in range(col_idx):
            cc = QColor(col_colors[completed_c])
            for r in range(4):
                cx, cy = self._cell_xy(ox, oy, r, completed_c)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(cc, 2))
                p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)
                self._state[r][completed_c] = self._after[r][completed_c]

        # Aktif sütun vurgusu
        for r in range(4):
            cx, cy = self._cell_xy(ox, oy, r, col_idx)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(col_color, 2))
            p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

        # Faz 2: 4 hücreyi sırayla yenisiyle değiştir
        if 5 <= phase_t < 15:
            rows_done = min(4, (phase_t - 5) // 2 + 1)
            for r in range(rows_done):
                self._state[r][col_idx] = self._after[r][col_idx]
                cx, cy = self._cell_xy(ox, oy, r, col_idx)
                # Color flash — yeşil
                flash = QColor(ANIM_COLORS["accent_green"])
                flash.setAlphaF(0.30)
                p.setBrush(QBrush(flash))
                p.setPen(QPen(QColor(ANIM_COLORS["accent_green"]), 1))
                p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

        # Formül balonu (sütunun sağında)
        if 4 <= phase_t < 18:
            balloon_x = ox + 4 * (self._CELL_W + self._CELL_GAP) + 4
            balloon_y = oy + 4
            p.setFont(QFont("Courier New", 8))
            p.setPen(col_color)
            p.drawText(QRect(balloon_x, balloon_y, 120, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"Sütun {col_idx}: GF(2⁸) ×")
            p.drawText(QRect(balloon_x, balloon_y + 16, 120, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "2·a₀ ⊕ 3·a₁ ⊕")
            p.drawText(QRect(balloon_x, balloon_y + 32, 120, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "a₂ ⊕ a₃  (vb.)")


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

        # Orta: önceki view → [operatör] → şimdiki view.
        # AddRoundKey adımında araya KALICI round_key matrisi ve ⊕ / =
        # operatörleri girer: "ÖNCEKİ ⊕ round_key = ŞİMDİKİ". Diğer
        # operasyonlarda round_key matrisi ve ikinci operatör gizlenir,
        # _arrow_label "→ Op →" gösterir.
        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)
        mid_row.addStretch(1)

        self._prev_view = _AESMatrixView(
            label_title="ÖNCEKİ",
            label_color=ANIM_COLORS["text_muted"],
        )
        mid_row.addWidget(self._prev_view)

        self._arrow_label = self._make_operator_label("→")
        mid_row.addWidget(self._arrow_label)

        # round_key kalıcı matrisi — yalnızca AddRoundKey adımlarında görünür.
        self._rk_view = _AESMatrixView(
            label_title="round_key",
            label_color=ANIM_COLORS["accent_peach"],
        )
        self._rk_view.setVisible(False)
        mid_row.addWidget(self._rk_view)

        self._op2_label = self._make_operator_label("=")
        self._op2_label.setVisible(False)
        mid_row.addWidget(self._op2_label)

        self._curr_view = _AESMatrixView(
            label_title="ŞİMDİKİ (canlı)",
            label_color=ANIM_COLORS["accent_blue"],
        )
        mid_row.addWidget(self._curr_view)

        mid_row.addStretch(1)
        outer.addLayout(mid_row)
        outer.addStretch(1)

    @staticmethod
    def _make_operator_label(text: str) -> QLabel:
        """İki matris arasındaki operatör etiketini (→ / ⊕ / =) oluşturur.

        Amaç: matrisler arası akışı (ör. "ÖNCEKİ ⊕ round_key = ŞİMDİKİ")
        görsel olarak bağlamak. Etiket ortalanır, kalın ve matris yüksekliğinde
        dikey ortalanır; metni/rengi ``start_step``/``show_final`` günceller.
        Genişlik içeriğe göre büyür (min 34 px), böylece "→ ShiftRows →" gibi
        uzun metinler de sığar, tek "⊕" ise dar kalır.
        """
        lbl = QLabel(text)
        lbl.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setMinimumWidth(34)
        return lbl

    def start_step(
        self,
        operation: str,
        before: list[list[str]],
        after: list[list[str]],
        op_color: str,
        *,
        round_key: list[list[str]] | None = None,
    ) -> None:
        """Adımı başlat: önceki donmuş, şimdiki animasyonlu.

        AddRoundKey ve round_key verildiğinde araya KALICI round_key matrisi
        (statik) ile ⊕ / = operatörleri yerleştirilir; böylece
        "ÖNCEKİ ⊕ round_key = ŞİMDİKİ" akışı kullanıcı tekrar oynatmaya gerek
        kalmadan ekranda sabit kalır. Diğer operasyonlarda round_key matrisi ve
        ikinci operatör gizlenir, _arrow_label "→ Op →" gösterir.
        """
        # Önceki çalışan animasyonu durdur
        self._curr_view.stop_animation()
        # Önceki view'a donmuş before state
        self._prev_view.set_state(before)

        if operation == "AddRoundKey" and round_key is not None:
            # round_key'i kalıcı matris olarak göster + ⊕ / = operatörleri
            self._rk_view.set_state(round_key)
            self._rk_view.setVisible(True)
            self._arrow_label.setText("⊕")
            self._arrow_label.setStyleSheet(
                f"color: {ANIM_COLORS['accent_peach']}; font-weight: bold;"
            )
            self._op2_label.setText("=")
            self._op2_label.setStyleSheet(f"color: {op_color}; font-weight: bold;")
            self._op2_label.setVisible(True)
        else:
            # Diğer operasyonlar (SubBytes/ShiftRows/MixColumns): round_key
            # matrisi + 2. operatör gizli. Aradaki etiket SADECE büyük bir "→"
            # oku; işlem adı zaten üstte _op_title'da ("Round N — ShiftRows")
            # yazdığından, dar kutuda dikey sıkışıp okunmayan "→ Op →" metni
            # kaldırıldı (Görsel 5-6 düzeltmesi).
            self._rk_view.setVisible(False)
            self._op2_label.setVisible(False)
            self._arrow_label.setText("→")
            self._arrow_label.setStyleSheet(f"color: {op_color}; font-weight: bold;")

        # Şimdiki view'a animasyon
        self._curr_view.play_animation(
            operation, before, after, round_key=round_key,
        )

    def show_final(self, final_state: list[list[str]]) -> None:
        """Round 14 sonrası: iki matris de final state, animasyon yok.

        round_key matrisi ve ikinci operatör gizlenir; yalnızca
        ÖNCEKİ = ŞİMDİKİ (final) gösterilir.
        """
        self._curr_view.stop_animation()
        self._rk_view.setVisible(False)
        self._op2_label.setVisible(False)
        self._prev_view.set_state(final_state)
        self._curr_view.set_state(final_state)
        self._arrow_label.setText("=  FINAL  =")
        self._arrow_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']}; font-weight: bold;"
        )

    def _on_replay(self) -> None:
        self._curr_view.replay()
