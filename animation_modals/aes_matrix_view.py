# animation_modals/aes_matrix_view.py
"""
_AESMatrixView ve _AESStateCompareWidget — AES state matrisi için
QPainter tabanlı byte-hareket animasyon görünümü.

_AESMatrixView: tek 4×4 matris, statik veya animasyonlu mod.
_AESStateCompareWidget: yan yana iki _AESMatrixView (Önceki / Canlı sonuç)
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
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from .base import ANIM_COLORS, cached_font, get_animation_tick_ms
from .aes.sbox_dialog import _SBoxReferenceDialog
from .aes_pure import gcm_first_keystream_block


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
    _TICK_MS = 55      # Round içi byte/faz geçişleri rahatça takip edilsin.

    # Operasyon başına toplam tick sayıları
    _TICKS_BY_OP: dict[str, int] = {
        "AddRoundKey": 60,    # ~3.3 s
        "SubBytes":    64,    # ~3.5 s
        "ShiftRows":   80,    # ~4.4 s
        "MixColumns":  80,    # ~4.4 s
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
        self._anim_timer.start(get_animation_tick_ms(self._TICK_MS))
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
        self._state = self._state_for_tick(self._tick)
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

    def _state_for_tick(self, tick: int) -> list[list[str]]:
        """Cari operasyonun verilen tick'teki matris durumunu saf olarak üretir."""
        state = [row[:] for row in self._before]

        if self._op == "AddRoundKey":
            cells_done = min(16, tick // 2 + 1)
            for idx in range(cells_done):
                state[idx // 4][idx % 4] = self._after[idx // 4][idx % 4]

        elif self._op == "SubBytes":
            cell_idx = min(15, tick // 4)
            for idx in range(cell_idx):
                state[idx // 4][idx % 4] = self._after[idx // 4][idx % 4]
            if tick % 4 >= 2:
                state[cell_idx // 4][cell_idx % 4] = self._after[cell_idx // 4][cell_idx % 4]

        elif self._op == "ShiftRows":
            for start, end, row in ((0, 10, 0), (10, 30, 1), (30, 50, 2), (50, 70, 3)):
                if tick >= start + (end - start) // 2:
                    state[row] = self._after[row][:]
            if tick >= 70:
                state = [row[:] for row in self._after]

        elif self._op == "MixColumns":
            for col in range(4):
                phase_t = tick - col * 20
                if phase_t < 5:
                    continue
                rows_done = min(4, (phase_t - 5) // 2 + 1)
                for row in range(rows_done):
                    state[row][col] = self._after[row][col]

        return state

    # --- Çizim ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Başlık (varsa)
        title_h = self._TITLE_H if self._label_title else 0
        if self._label_title:
            p.setFont(cached_font("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(self._label_color))
            p.drawText(QRect(0, 4, self.width(), 18),
                       Qt.AlignmentFlag.AlignCenter, self._label_title)

        ox = 6
        oy = title_h + 4

        # Sütun etiketleri (c0..c3)
        p.setFont(cached_font("Georgia", 8, QFont.Weight.Bold))
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
            p.setFont(cached_font("Georgia", 8, QFont.Weight.Bold))
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
        p.setFont(cached_font("Courier New", 13, QFont.Weight.Bold))
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
            p.setFont(cached_font("Georgia", 9, QFont.Weight.Bold))
            p.setPen(accent)
            p.drawText(QRect(cx + self._CELL_W - 14, cy + 2, 12, 12),
                       Qt.AlignmentFlag.AlignCenter, "⊕")
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
            p.setFont(cached_font("Courier New", 8, QFont.Weight.Bold))
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
                # Aktif satırı vurgula (4 hücre çerçevesi)
                for c in range(4):
                    cx, cy = self._cell_xy(ox, oy, row, c)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(accent, 2))
                    p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

                # Satırın sağına ok rozeti / "sabit" etiketi
                row_y = oy + row * (self._CELL_H + self._CELL_GAP)
                p.setFont(cached_font("Georgia", 9, QFont.Weight.Bold))
                p.setPen(accent)
                lbl = "sabit" if shift == 0 else f"← {shift} bayt"
                p.drawText(
                    QRect(ox + 4 * (self._CELL_W + self._CELL_GAP) + 4,
                          row_y, 90, self._CELL_H),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    lbl,
                )

                return  # her tick yalnızca bir satır aktif

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
            p.setFont(cached_font("Courier New", 8))
            p.setPen(col_color)
            # MixColumns sabit matrisinde HER çıkış baytı FARKLI katsayı satırı
            # kullanır; tek genel formül ("2·a₀⊕3·a₁⊕a₂⊕a₃ vb.") göstermek
            # yanıltıcıdır. Dört satırın tamamı GF(2⁸) çarpımıyla gösterilir.
            p.drawText(QRect(balloon_x, balloon_y, 150, 13),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"Sütun {col_idx}:  b = M · a  (GF(2⁸))")
            mix_formulas = (
                "b₀=2a₀⊕3a₁⊕ a₂⊕ a₃",
                "b₁= a₀⊕2a₁⊕3a₂⊕ a₃",
                "b₂= a₀⊕ a₁⊕2a₂⊕3a₃",
                "b₃=3a₀⊕ a₁⊕ a₂⊕2a₃",
            )
            for i, line in enumerate(mix_formulas):
                p.drawText(QRect(balloon_x, balloon_y + 14 + i * 13, 150, 13),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           line)


class _AESStateCompareWidget(QWidget):
    """Yan yana iki _AESMatrixView + Yeniden Oynat butonu.

    Sol: önceki state (donmuş, set_state ile)
    Orta: aktif operasyon etiketi (renkli ok)
    Sağ: işlem sonucu (canlı, play_animation ile)
    Üst sağ: Yeniden Oynat butonu
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        # Üst satır: gerektiğinde S-Box referansı + replay.
        top_row = QHBoxLayout()
        top_row.addStretch(1)

        self._sbox_btn = QPushButton("S-Box Tablosu")
        self._sbox_btn.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['accent_yellow']}; "
            f"border: 1px solid {ANIM_COLORS['accent_yellow']}; "
            f"border-radius: 5px; padding: 4px 10px; font-weight: bold; }}"
        )
        self._sbox_btn.setFixedHeight(28)
        self._sbox_btn.clicked.connect(self._show_sbox_reference)
        self._sbox_btn.setVisible(False)
        top_row.addWidget(self._sbox_btn)

        self._replay_btn = QPushButton("⟲  Yeniden Oynat")
        self._replay_btn.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['text_on_accent']}; border: none; border-radius: 6px; "
            f"padding: 4px 14px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        self._replay_btn.setFixedHeight(28)
        self._replay_btn.clicked.connect(self._on_replay)
        top_row.addWidget(self._replay_btn)
        outer.addLayout(top_row)
        self._subbytes_mappings: list[tuple[str, str]] = []
        self._sbox_dialog: _SBoxReferenceDialog | None = None

        # Orta: önceki view → [operatör] → canlı sonuç view.
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
            label_title="SONUÇ",
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
        """Adımı başlat: önceki donmuş, sonuç animasyonlu.

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
        self._sbox_btn.setVisible(operation == "SubBytes")
        self._subbytes_mappings = (
            [
                (before[row][col], after[row][col])
                for row in range(4)
                for col in range(4)
            ]
            if operation == "SubBytes"
            else []
        )

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

    def _show_sbox_reference(self) -> None:
        """AES'in sabit 16×16 S-Box tablosunu ayrı bir referans penceresinde gösterir."""
        dialog = _SBoxReferenceDialog(self._subbytes_mappings, self)
        self._sbox_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def show_final(self, final_state: list[list[str]]) -> None:
        """Round 14 sonrası: iki matris de final state, animasyon yok.

        round_key matrisi ve ikinci operatör gizlenir; yalnızca
        ÖNCEKİ = SONUÇ (final) gösterilir.
        """
        self._curr_view.stop_animation()
        self._rk_view.setVisible(False)
        self._op2_label.setVisible(False)
        self._prev_view.set_state(final_state)
        self._curr_view.set_state(final_state)
        self._sbox_btn.setVisible(False)
        self._subbytes_mappings = []
        self._arrow_label.setText("=  FINAL  =")
        self._arrow_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']}; font-weight: bold;"
        )

    def _on_replay(self) -> None:
        self._curr_view.replay()


class _ColumnMajorLinearizeWidget(QWidget):
    """Final AES state matrisinin column-major (sütun-öncelikli) sıraya
    dizilişini canlandırır.

    Üstte 4×4 final matris, altında 16 hücrelik yatay "çıktı şeridi" çizilir.
    Animasyon sütun sütun (c0→c3) ilerler: aktif sütun matriste vurgulanır ve o
    sütunun byte'ları (r0..r3) tek tek, kaynak hücreden şeritteki ``c*4+r``
    konumuna uçarak yerleşir. 16 byte dizildikten sonra 32 haneli hex çıktı
    belirir. AES'in matrisi neden sütun-öncelikli okuduğunu görsel anlatır.
    """

    # Üst matris hücre boyutları (kompakt; _AESMatrixView'dan bağımsız tutuldu).
    _M_CELL = 38
    _M_GAP = 4
    # Alt şerit hücre boyutları (16 byte yatay).
    _S_CELL_W = 30
    _S_CELL_H = 30
    _S_GAP = 3

    # Tempo (tick). Timer get_animation_tick_ms ile ölçeklenir.
    _TICK_MS = 90
    _INTRO_TICKS = 14            # Matris belirip sabitlenir.
    _BYTE_TICKS = 5             # Her byte'ın uçuş süresi.
    _COL_GAP_TICKS = 3          # Sütunlar arası kısa duraklama.
    _OUTRO_TICKS = 24           # Hex çıktı + final bekleme.

    # Dikey yerleşim sabitleri (paintEvent ile birebir aynı; min yükseklik
    # bunlardan türetilir, böylece şerit + hex çıktı asla kırpılmaz).
    _TITLE_TOP = 2
    _MAT_OY = 26                 # Matrisin üst kenarı.
    _STRIP_GAP = 26              # Matris altı ile şerit arası (etiket dahil).
    _HEX_GAP = 8                 # Şerit altı ile hex çıktı arası.
    _HEX_H = 22                  # Hex çıktı satır yüksekliği.
    _BOTTOM_PAD = 10

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state: list[list[str]] = [["00"] * 4 for _ in range(4)]
        self._tick = 0
        self._total_ticks = self._compute_total()
        mat_h = 4 * self._M_CELL + 3 * self._M_GAP
        # Toplam içerik yüksekliği: matris + şerit + hex çıktı + paylar.
        content_h = (
            self._MAT_OY + mat_h + self._STRIP_GAP + self._S_CELL_H
            + self._HEX_GAP + self._HEX_H + self._BOTTOM_PAD
        )
        min_w = 16 * self._S_CELL_W + 15 * self._S_GAP + 12
        self.setMinimumSize(min_w, content_h)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------

    def set_state(self, matrix: list[list[str]]) -> None:
        """Gösterilecek 4×4 final matrisi atar ve animasyonu başa sarar."""
        self._state = [row[:] for row in matrix]
        self._tick = 0
        self.update()

    def hex_output(self) -> str:
        """Matristen column-major (c, sonra r) okunan 32 haneli hex çıktı."""
        return "".join(
            self._state[r][c] for c in range(4) for r in range(4)
        )

    def start(self) -> None:
        """Animasyonu baştan başlatır."""
        self._tick = 0
        self._timer.start(get_animation_tick_ms(self._TICK_MS))

    def stop(self) -> None:
        self._timer.stop()

    def replay(self) -> None:
        self.start()

    # ------------------------------------------------------------------
    # Zaman çizelgesi
    # ------------------------------------------------------------------

    def _compute_total(self) -> int:
        per_col = 4 * self._BYTE_TICKS + self._COL_GAP_TICKS
        return self._INTRO_TICKS + 4 * per_col + self._OUTRO_TICKS

    def _advance(self) -> None:
        self._tick += 1
        if self._tick >= self._total_ticks:
            self._tick = self._total_ticks  # Son karede sabit kal (döngü yok).
            self._timer.stop()
        self.update()

    def _placed_count(self) -> int:
        """Şu ana kadar şeride yerleşmiş (uçuşu tamamlanmış) byte sayısı (0..16)."""
        t = self._tick - self._INTRO_TICKS
        if t <= 0:
            return 0
        per_col = 4 * self._BYTE_TICKS + self._COL_GAP_TICKS
        placed = 0
        for col in range(4):
            col_start = col * per_col
            for r in range(4):
                # Bu byte'ın uçuşu col_start + r*_BYTE_TICKS'te başlar,
                # +_BYTE_TICKS'te tamamlanır.
                if t >= col_start + (r + 1) * self._BYTE_TICKS:
                    placed += 1
        return min(16, placed)

    def _flying(self) -> tuple[int, int, float] | None:
        """O an uçuşta olan byte varsa (sütun, satır, ilerleme[0,1]) döndürür."""
        t = self._tick - self._INTRO_TICKS
        if t <= 0:
            return None
        per_col = 4 * self._BYTE_TICKS + self._COL_GAP_TICKS
        for col in range(4):
            col_start = col * per_col
            for r in range(4):
                fly_start = col_start + r * self._BYTE_TICKS
                fly_end = fly_start + self._BYTE_TICKS
                if fly_start <= t < fly_end:
                    return col, r, (t - fly_start) / self._BYTE_TICKS
        return None

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()

        # Üst başlık.
        p.setFont(cached_font("IBM Plex Sans", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(0, 2, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "AES son state → sütun-öncelikli (column-major) okunur")

        # Matris yerleşimi (üstte, ortalanmış).
        mat_w = 4 * self._M_CELL + 3 * self._M_GAP
        mat_ox = (W - mat_w) // 2
        mat_oy = self._MAT_OY
        flying = self._flying()
        active_col = flying[0] if flying else self._current_active_col()

        for r in range(4):
            for c in range(4):
                x = mat_ox + c * (self._M_CELL + self._M_GAP)
                y = mat_oy + r * (self._M_CELL + self._M_GAP)
                lit = (c == active_col)
                self._draw_box(p, x, y, self._M_CELL, self._M_CELL,
                               self._state[r][c],
                               accent=lit, dim=False)

        # Alt şerit.
        strip_w = 16 * self._S_CELL_W + 15 * self._S_GAP
        strip_ox = max(6, (W - strip_w) // 2)
        strip_oy = mat_oy + 4 * (self._M_CELL + self._M_GAP) + self._STRIP_GAP

        p.setFont(cached_font("IBM Plex Sans", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, strip_oy - 18, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "Çıktı sırası (16 byte):")

        placed = self._placed_count()
        for idx in range(16):
            sx = strip_ox + idx * (self._S_CELL_W + self._S_GAP)
            if idx < placed:
                c, r = idx // 4, idx % 4
                self._draw_box(p, sx, strip_oy, self._S_CELL_W, self._S_CELL_H,
                               self._state[r][c], accent=False, dim=False)
            else:
                # Boş yer-tutucu.
                self._draw_box(p, sx, strip_oy, self._S_CELL_W, self._S_CELL_H,
                               "", accent=False, dim=True)

        # Uçuştaki byte (kaynak hücre → hedef şerit kutusu, lineer).
        if flying is not None:
            c, r, prog = flying
            src_x = mat_ox + c * (self._M_CELL + self._M_GAP)
            src_y = mat_oy + r * (self._M_CELL + self._M_GAP)
            dst_idx = c * 4 + r
            dst_x = strip_ox + dst_idx * (self._S_CELL_W + self._S_GAP)
            fx = int(src_x + (dst_x - src_x) * prog)
            fy = int(src_y + (strip_oy - src_y) * prog)
            self._draw_box(p, fx, fy, self._S_CELL_W, self._S_CELL_H,
                           self._state[r][c], accent=True, dim=False)

        # Tüm byte'lar dizildiyse 32 hane hex çıktı.
        if placed >= 16:
            hex_out = self.hex_output()
            p.setFont(cached_font("Courier New", 13, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_green"]))
            p.drawText(QRect(0, strip_oy + self._S_CELL_H + self._HEX_GAP, W, self._HEX_H),
                       Qt.AlignmentFlag.AlignCenter, hex_out)
        p.end()

    def _current_active_col(self) -> int:
        """Uçuş yokken vurgulanacak sütun: bir sonraki dolacak veya -1."""
        placed = self._placed_count()
        if placed >= 16 or self._tick <= self._INTRO_TICKS:
            return -1
        return min(3, placed // 4)

    def _draw_box(self, p: QPainter, x: int, y: int, w: int, h: int,
                  value: str, *, accent: bool, dim: bool) -> None:
        """Tek bir kutu çizer (matris hücresi veya şerit kutusu)."""
        if dim:
            bg = QColor(ANIM_COLORS["bg_input"])
            border = QColor(ANIM_COLORS["border"])
            bw = 1
        elif accent:
            bg = QColor(ANIM_COLORS["accent_blue"]); bg.setAlphaF(0.30)
            border = QColor(ANIM_COLORS["accent_blue"]); bw = 2
        else:
            bg = QColor(ANIM_COLORS["accent_blue"]); bg.setAlphaF(0.14)
            border = QColor(ANIM_COLORS["accent_blue"]); border.setAlphaF(0.6)
            bw = 1
        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, bw))
        p.drawRoundedRect(x, y, w, h, 4, 4)
        if value:
            p.setFont(cached_font("Courier New", 12, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, value)


class _GCMRealEncryptWidget(QWidget):
    """Programın GERÇEK AES-256-GCM şifrelemesinin çekirdeğini canlandırır.

    GCM, AES blok şifrelemesini düz metne değil bir SAYAÇ bloğuna uygular ve
    çıkan keystream'i veriyle XOR'lar. Bu widget, gerçek session anahtarı (K_S)
    ve nonce ile:
      1) sayaç bloğunu (nonce ‖ 0x00000002) gösterir,
      2) AES-256 ile şifreleyip gerçek keystream bloğunu üretir,
      3) keystream ⊕ mesaj = şifreli metin adımını gösterir,
      4) çıkan ilk byte'ların programın GERÇEK ciphertext'iyle eşleştiğini
         yeşil onayla kanıtlar.
    Nonce verilmezse (eğitim/test) pasif kalır.
    """

    _CW = 30           # Byte kutusu genişliği.
    _CH = 28           # Byte kutusu yüksekliği.
    _GAP = 3
    _N = 16            # Satır başına byte (sayaç/keystream/ciphertext blokları).

    _TICK_MS = 90
    _T_COUNTER = 12    # Sayaç bloğu belirir.
    _T_AES = 14        # Sayaç → AES kutusu → keystream çıkar.
    _BYTE_TICKS = 4    # XOR'da her byte için.
    _T_PROOF = 26      # Eşleşme onayı + bekleme.

    # Dikey yerleşim sabitleri (min yükseklik bunlardan türetilir).
    _TOP = 6
    _ROW_LABEL_H = 18
    _ROW_GAP = 16
    _AES_BOX_H = 30

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._key = b""
        self._nonce = b""
        self._plaintext = b""
        self._expected_ct = b""       # Gerçek ciphertext ilk byte'ları (kanıt).
        self._counter_block = b""
        self._keystream = b""
        self._cipher = b""            # keystream ⊕ plaintext (ilk 16 byte).
        self._match: bool | None = None
        self._tick = 0
        self._total_ticks = self._compute_total()
        self.setMinimumSize(self._min_w(), self._min_h())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------

    def has_inputs(self) -> bool:
        """Gerçek anahtar+nonce verilmiş mi (köprü gösterilebilir mi)?"""
        return len(self._key) == 32 and len(self._nonce) == 12

    def set_inputs(self, session_key: bytes, nonce: bytes,
                   plaintext: bytes, expected_ct_hex: str) -> None:
        """Gerçek K_S, nonce, mesaj ve beklenen ciphertext önizlemesini atar.

        Geçersiz/boş nonce'ta widget pasif kalır (has_inputs False).
        """
        self._key = session_key
        self._nonce = nonce
        self._plaintext = plaintext
        self._tick = 0
        if not self.has_inputs():
            return
        self._counter_block = nonce + (2).to_bytes(4, "big")
        self._keystream = gcm_first_keystream_block(session_key, nonce)
        n = min(self._N, len(plaintext))
        self._cipher = bytes(self._keystream[i] ^ plaintext[i] for i in range(n))
        # Beklenen ciphertext (hex önizleme "...": kuyruğu temizle).
        clean = expected_ct_hex.replace(".", "").strip()
        try:
            self._expected_ct = bytes.fromhex(clean)
        except ValueError:
            self._expected_ct = b""
        cmp_len = min(len(self._cipher), len(self._expected_ct))
        if cmp_len > 0:
            self._match = self._cipher[:cmp_len] == self._expected_ct[:cmp_len]
        else:
            self._match = None
        self.update()

    def start(self) -> None:
        if not self.has_inputs():
            return
        self._tick = 0
        self._timer.start(get_animation_tick_ms(self._TICK_MS))

    def stop(self) -> None:
        self._timer.stop()

    def replay(self) -> None:
        self.start()

    # ------------------------------------------------------------------
    # Zaman çizelgesi
    # ------------------------------------------------------------------

    def _compute_total(self) -> int:
        return (self._T_COUNTER + self._T_AES
                + self._N * self._BYTE_TICKS + self._T_PROOF)

    def _advance(self) -> None:
        self._tick += 1
        if self._tick >= self._total_ticks:
            self._tick = self._total_ticks
            self._timer.stop()
        self.update()

    def _xor_done(self) -> int:
        """XOR fazında tamamlanmış byte sayısı (0..16)."""
        t = self._tick - (self._T_COUNTER + self._T_AES)
        if t <= 0:
            return 0
        return min(self._N, t // self._BYTE_TICKS)

    # ------------------------------------------------------------------
    # Boyut
    # ------------------------------------------------------------------

    def _min_w(self) -> int:
        return self._N * self._CW + (self._N - 1) * self._GAP + 16

    def _min_h(self) -> int:
        # başlık + sayaç satırı + AES kutusu + keystream + XOR(mesaj+ciphertext)
        # + kanıt satırı; her satır etiket + kutu + boşluk.
        rows = 4  # sayaç, keystream, mesaj, ciphertext
        h = self._TOP + 20  # üst başlık
        h += self._AES_BOX_H + self._ROW_GAP
        h += rows * (self._ROW_LABEL_H + self._CH + self._ROW_GAP)
        h += 26  # kanıt satırı
        return h

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()
        if not self.has_inputs():
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.setFont(cached_font("IBM Plex Sans", 10))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Gerçek GCM verisi yok.")
            p.end()
            return

        row_w = self._N * self._CW + (self._N - 1) * self._GAP
        ox = max(8, (W - row_w) // 2)

        # Başlık.
        p.setFont(cached_font("IBM Plex Sans", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(0, self._TOP, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "Programın gerçek şifrelemesi (AES-256-GCM çekirdeği)")

        y = self._TOP + 22
        show_aes = self._tick >= self._T_COUNTER
        show_ks = self._tick >= (self._T_COUNTER + self._T_AES)

        # 1) Sayaç bloğu satırı.
        self._row(p, ox, y, "Sayaç bloğu  (nonce ‖ 00000002):",
                  self._counter_block, active=not show_aes,
                  color="accent_mauve")
        y += self._ROW_LABEL_H + self._CH + 6

        # 2) AES kutusu (sayaç → AES·K_S → keystream).
        box_w = 220
        box_x = (W - box_w) // 2
        lit = show_aes
        bg = QColor(ANIM_COLORS["accent_blue"]); bg.setAlphaF(0.22 if lit else 0.10)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor(ANIM_COLORS["accent_blue"]), 2 if lit else 1))
        p.drawRoundedRect(box_x, y, box_w, self._AES_BOX_H, 6, 6)
        p.setFont(cached_font("IBM Plex Sans", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"] if lit else ANIM_COLORS["text_muted"]))
        p.drawText(QRect(box_x, y, box_w, self._AES_BOX_H),
                   Qt.AlignmentFlag.AlignCenter, "AES-256  ·  K_S  (gerçek anahtar)")
        y += self._AES_BOX_H + self._ROW_GAP

        # 3) Keystream satırı.
        self._row(p, ox, y, "Keystream  (AES çıkışı):",
                  self._keystream if show_ks else b"",
                  active=show_ks and self._xor_done() == 0,
                  color="accent_blue", placeholder_n=self._N)
        y += self._ROW_LABEL_H + self._CH + 6

        # 4) XOR: mesaj satırı.
        done = self._xor_done()
        self._row(p, ox, y, "⊕  Mesaj (m ‖ imza, ilk 16 byte):",
                  self._plaintext[:self._N], active=False,
                  color="accent_peach", placeholder_n=self._N)
        y += self._ROW_LABEL_H + self._CH + 6

        # 5) Ciphertext satırı (XOR sonucu, byte byte dolar).
        self._row(p, ox, y, "=  Şifreli metin (keystream ⊕ mesaj):",
                  self._cipher[:done], active=True,
                  color="accent_green", placeholder_n=self._N)
        y += self._ROW_LABEL_H + self._CH + 8

        # 6) Kanıt: gerçek ciphertext ile eşleşme.
        if done >= min(self._N, len(self._cipher)) and self._match is not None:
            if self._match:
                p.setPen(QColor(ANIM_COLORS["accent_green"]))
                msg = "✓ Bu, programın gönderdiği gerçek şifreli metnin ta kendisidir."
            else:
                p.setPen(QColor(ANIM_COLORS["accent_red"]))
                msg = "Çıktı, beklenen ciphertext ile eşleşmedi."
            p.setFont(cached_font("IBM Plex Sans", 10, QFont.Weight.Bold))
            p.drawText(QRect(0, y, W, 22), Qt.AlignmentFlag.AlignCenter, msg)
        p.end()

    def _row(self, p: QPainter, ox: int, y: int, label: str, data: bytes,
             *, active: bool, color: str, placeholder_n: int = 0) -> None:
        """Etiketli bir byte satırı çizer (nonce/keystream/mesaj/ciphertext)."""
        p.setFont(cached_font("IBM Plex Sans", 9))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(ox, y, self._N * (self._CW + self._GAP), self._ROW_LABEL_H),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
        ry = y + self._ROW_LABEL_H
        n = placeholder_n if placeholder_n else len(data)
        for i in range(n):
            x = ox + i * (self._CW + self._GAP)
            if i < len(data):
                val = f"{data[i]:02x}"
                self._draw_byte(p, x, ry, val, color, active and i == len(data) - 1)
            else:
                self._draw_byte(p, x, ry, "", color, False, dim=True)

    def _draw_byte(self, p: QPainter, x: int, y: int, val: str, color_key: str,
                   accent: bool, dim: bool = False) -> None:
        if dim:
            bg = QColor(ANIM_COLORS["bg_input"])
            border = QColor(ANIM_COLORS["border"]); bw = 1
        else:
            base = QColor(ANIM_COLORS[color_key])
            bg = QColor(base); bg.setAlphaF(0.30 if accent else 0.16)
            border = QColor(base); border.setAlphaF(1.0 if accent else 0.6)
            bw = 2 if accent else 1
        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, bw))
        p.drawRoundedRect(x, y, self._CW, self._CH, 4, 4)
        if val:
            p.setFont(cached_font("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x, y, self._CW, self._CH),
                       Qt.AlignmentFlag.AlignCenter, val)
