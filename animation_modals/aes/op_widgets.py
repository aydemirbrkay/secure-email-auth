# animation_modals/aes/op_widgets.py
"""AES operasyon detay widget'ları: SubBytes / ShiftRows / MixColumns / AddRoundKey."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS

# ---------------------------------------------------------------------------
# ShiftRows animasyonlu ok widget'ı
# ---------------------------------------------------------------------------

class _ShiftRowsAnimWidget(QWidget):
    """
    ShiftRows görselleştirmesi: her satır için 'önce → sonra' ve
    kaydırma yönünü gösteren renkli animasyonlu oklar.
    QTimer ile satırlar birer birer ortaya çıkar.
    """

    _ROW_COLORS = [
        ANIM_COLORS["text_muted"],    # Satır 0: sabit
        ANIM_COLORS["accent_blue"],   # Satır 1: ← 1
        ANIM_COLORS["accent_mauve"],  # Satır 2: ← 2
        ANIM_COLORS["accent_peach"],  # Satır 3: ← 3
    ]
    _SHIFTS = [0, 1, 2, 3]
    _SHIFT_LABELS = ["sabit", "← 1 bayt", "← 2 bayt", "← 3 bayt"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._before: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._after: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._revealed = 0   # kaç satır animasyonda gösterildi
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._advance)
        # 4 satır × 92 + header(18) + alt boşluk(8) ≈ 394
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_data(self, before: list[list[str]], after: list[list[str]]) -> None:
        self._before = before
        self._after = after
        self._revealed = 0
        self._anim_timer.start(420)
        self.update()

    def _advance(self) -> None:
        self._revealed += 1
        if self._revealed >= 4:
            self._revealed = 4
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        cell_w = max(38, min(52, (W - 24) // 4 - 4))
        cell_h = 28
        gap = 4
        grid_w = 4 * cell_w + 3 * gap
        x0 = max(4, (W - grid_w) // 2)
        # Yeni layout: before(28) + label(14) + arrow(12) + after(28) + boşluk(8) = 90
        row_section = 92

        font_val = QFont("Courier New", 8, QFont.Weight.Bold)
        font_lbl = QFont("IBM Plex Sans", 8, QFont.Weight.Bold)

        # Header
        p.setFont(QFont("IBM Plex Sans", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(x0, 0, grid_w, 14), Qt.AlignmentFlag.AlignCenter,
                   "ÖNCEKİ  →  SONRAKI")

        for row in range(4):
            y_top = 18 + row * row_section
            color = self._ROW_COLORS[row]
            shift = self._SHIFTS[row]
            revealed = row < self._revealed

            # ── Önce (before) hücreleri ──
            for c in range(4):
                x = x0 + c * (cell_w + gap)
                bg = QColor(color + ("55" if revealed else "22"))
                border = QColor(color if revealed else ANIM_COLORS["border"])
                p.setBrush(QBrush(bg))
                p.setPen(QPen(border, 1))
                p.drawRoundedRect(x, y_top, cell_w, cell_h, 3, 3)
                p.setFont(font_val)
                p.setPen(QColor(ANIM_COLORS["text_primary"] if revealed else ANIM_COLORS["text_muted"]))
                p.drawText(QRect(x, y_top, cell_w, cell_h),
                           Qt.AlignmentFlag.AlignCenter, self._before[row][c])

            # ── Ok ve shift etiketi (BAĞIMSIZ alanlar — üst üste binmiyor) ──
            # Layout (y_top + cell_h sonrası):
            #   +2  : etiket başlangıcı (h=14)
            #   +18 : ok çizgisi (1 piksel)
            #   +28 : after hücreleri başlangıcı
            label_y = y_top + cell_h + 2     # etiket alanı: 14 piksel
            arrow_y = y_top + cell_h + 20    # ok çizgisi: 1 piksel
            y_bot   = y_top + cell_h + 28    # sonra hücreleri

            if revealed:
                if shift == 0:
                    # Önce etiket (üstte, çizgiyle çakışmıyor)
                    p.setFont(font_lbl)
                    p.setPen(QColor(ANIM_COLORS["text_muted"]))
                    p.drawText(QRect(x0, label_y, grid_w, 14),
                               Qt.AlignmentFlag.AlignCenter, "sabit")
                    # Sonra kesikli çizgi (etiketin ALTI, ayrı satır)
                    pen_d = QPen(QColor(ANIM_COLORS["text_muted"]), 1, Qt.PenStyle.DashLine)
                    p.setPen(pen_d)
                    p.drawLine(x0, arrow_y, x0 + grid_w, arrow_y)
                else:
                    # Önce etiket
                    p.setFont(font_lbl)
                    p.setPen(QColor(color))
                    p.drawText(QRect(x0, label_y, grid_w, 14),
                               Qt.AlignmentFlag.AlignCenter,
                               self._SHIFT_LABELS[row])
                    # Sonra ok çizgisi (etiketin ALTI, ayrı satır)
                    ax_end = x0
                    ax_start = x0 + grid_w
                    pen_a = QPen(QColor(color), 2)
                    p.setPen(pen_a)
                    p.drawLine(ax_start, arrow_y, ax_end + 8, arrow_y)
                    pts = QPolygon([
                        QPoint(ax_end, arrow_y),
                        QPoint(ax_end + 9, arrow_y - 5),
                        QPoint(ax_end + 9, arrow_y + 5),
                    ])
                    p.setBrush(QBrush(QColor(color)))
                    p.drawPolygon(pts)

            # ── Sonra (after) hücreleri ──
            for c in range(4):
                x = x0 + c * (cell_w + gap)
                if revealed:
                    bg = QColor(color + "33")
                    border = QColor(color)
                    txt_color = QColor(ANIM_COLORS["text_primary"])
                    val = self._after[row][c]
                else:
                    bg = QColor(ANIM_COLORS["bg_input"])
                    border = QColor(ANIM_COLORS["border"])
                    txt_color = QColor(ANIM_COLORS["text_muted"])
                    val = "--"
                p.setBrush(QBrush(bg))
                p.setPen(QPen(border, 1))
                p.drawRoundedRect(x, y_bot, cell_w, cell_h, 3, 3)
                p.setFont(font_val)
                p.setPen(txt_color)
                p.drawText(QRect(x, y_bot, cell_w, cell_h),
                           Qt.AlignmentFlag.AlignCenter, val)

        p.end()


# ---------------------------------------------------------------------------
# MixColumns animasyonlu sütun widget'ı
# ---------------------------------------------------------------------------

class _MixColumnsAnimWidget(QWidget):
    """
    MixColumns görselleştirmesi: dört sütun sırayla vurgulanır.
    Her sütunun 4 baytı ⊕ sembolleriyle birleştirildiği gösterilir.
    QTimer ile sütunlar sırayla canlanır.
    """

    _COL_COLORS = [
        ANIM_COLORS["accent_blue"],
        ANIM_COLORS["accent_mauve"],
        ANIM_COLORS["accent_yellow"],
        ANIM_COLORS["accent_peach"],
    ]

    # GF(2⁸) MixColumns output formulas — one per output byte row
    _FORMULAS = [
        "02·s₀⊕03·s₁⊕s₂⊕s₃",
        "s₀⊕02·s₁⊕03·s₂⊕s₃",
        "s₀⊕s₁⊕02·s₂⊕03·s₃",
        "03·s₀⊕s₁⊕s₂⊕02·s₃",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._before: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._after: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._active_col = -1   # -1 = başlamadı, 0-3 = aktif sütun, 4 = hepsi tamam
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._advance)
        # Output hücreleri (4×27=108) + giriş + matris + formüller + başlık ≈ 380
        self.setMinimumHeight(380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_data(self, before: list[list[str]], after: list[list[str]]) -> None:
        self._before = before
        self._after = after
        self._active_col = 1  # ilk sütunu hemen göster
        self._anim_timer.start(600)
        self.update()

    def _advance(self) -> None:
        self._active_col += 1
        if self._active_col >= 4:
            self._active_col = 4
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()

        font_val  = QFont("Courier New", 8, QFont.Weight.Bold)
        font_lbl  = QFont("IBM Plex Sans", 8, QFont.Weight.Bold)
        # font_mat and font_fml are both Courier New 7 — kept separate for
        # readability so either can be independently tuned later.
        font_mat  = QFont("Courier New", 7)
        font_fml  = QFont("Courier New", 7)

        # ── Başlık ──────────────────────────────────────────────────────
        p.setFont(font_lbl)
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 2, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "GF(2⁸)  Matris Çarpımı  —  Sütun Karıştırma")

        # ── MixColumns matrisi (sol panel) ──────────────────────────────
        # Matrix box width and position
        mat_box_w = 88
        mat_box_h = 72
        mat_box_x = 4
        mat_box_y = 22  # 16px title + 6px gap

        mat_bg   = QColor(ANIM_COLORS["bg_card"])
        mat_brd  = QColor(ANIM_COLORS["accent_mauve"])
        p.setBrush(QBrush(mat_bg))
        p.setPen(QPen(mat_brd, 1))
        p.drawRoundedRect(mat_box_x, mat_box_y, mat_box_w, mat_box_h, 4, 4)

        # Matrix label
        p.setFont(font_lbl)
        p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
        p.drawText(QRect(mat_box_x, mat_box_y + 2, mat_box_w, 12),
                   Qt.AlignmentFlag.AlignCenter, "MixCol Matrisi")

        mc_rows = [
            "02  03  01  01",
            "01  02  03  01",
            "01  01  02  03",
            "03  01  01  02",
        ]
        p.setFont(font_mat)
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        for i, row_txt in enumerate(mc_rows):
            row_y = mat_box_y + 16 + i * 13
            p.drawText(QRect(mat_box_x + 4, row_y, mat_box_w - 8, 13),
                       Qt.AlignmentFlag.AlignCenter, row_txt)

        # "×" symbol to the right of the matrix box
        p.setFont(QFont("IBM Plex Sans", 13))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        times_x = mat_box_x + mat_box_w + 1
        times_y = mat_box_y + mat_box_h // 2 - 10
        p.drawText(QRect(times_x, times_y, 12, 20), Qt.AlignmentFlag.AlignCenter, "×")

        # ── Column sections ─────────────────────────────────────────────
        # Available width after the matrix box + "×" symbol
        cols_x_start = mat_box_x + mat_box_w + 14   # start of column area
        cols_avail_w = W - cols_x_start - 4
        col_section_w = max(1, cols_avail_w // 4)
        cell_w = max(1, col_section_w - 6)
        cell_h = 24
        gap_y  = 3

        for col in range(4):
            x_col = cols_x_start + col * col_section_w
            color  = self._COL_COLORS[col]
            is_done   = col < self._active_col
            is_active = col == self._active_col - 1
            alpha  = "88" if is_done else ("55" if is_active else "22")
            border_w = 2 if is_active else 1

            # Column label
            p.setFont(font_lbl)
            lbl_color = QColor(color) if (is_active or is_done) else QColor(ANIM_COLORS["text_muted"])
            p.setPen(lbl_color)
            p.drawText(QRect(x_col, mat_box_y, col_section_w, 14),
                       Qt.AlignmentFlag.AlignCenter, f"S{col+1}")

            # "Giriş" sub-label
            p.setFont(font_mat)
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x_col, mat_box_y + 13, col_section_w, 10),
                       Qt.AlignmentFlag.AlignCenter, "giriş")

            y_start = mat_box_y + 24
            # Before (input) cells — 4 rows
            for row in range(4):
                y = y_start + row * (cell_h + gap_y)
                bg     = QColor(color + alpha)
                border = QColor(color)
                p.setBrush(QBrush(bg))
                p.setPen(QPen(border, border_w))
                p.drawRoundedRect(x_col + 2, y, cell_w, cell_h, 3, 3)
                p.setFont(font_val)
                p.setPen(QColor(ANIM_COLORS["text_primary"] if (is_active or is_done) else ANIM_COLORS["text_muted"]))
                p.drawText(QRect(x_col + 2, y, cell_w, cell_h),
                           Qt.AlignmentFlag.AlignCenter, self._before[row][col])

            # Down arrow
            arr_top = y_start + 4 * (cell_h + gap_y) + 3
            arr_bot = arr_top + 14
            if is_active or is_done:
                p.setPen(QPen(QColor(color), 2))
                mid_x = x_col + col_section_w // 2
                p.drawLine(mid_x, arr_top, mid_x, arr_bot - 5)
                pts = QPolygon([
                    QPoint(mid_x, arr_bot),
                    QPoint(mid_x - 4, arr_bot - 7),
                    QPoint(mid_x + 4, arr_bot - 7),
                ])
                p.setBrush(QBrush(QColor(color)))
                p.drawPolygon(pts)

            # "Çıkış" sub-label
            y2_label = arr_bot + 1
            p.setFont(font_mat)
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x_col, y2_label, col_section_w, 10),
                       Qt.AlignmentFlag.AlignCenter, "çıkış")

            # After (output) cells
            y2_start = y2_label + 10
            for row in range(4):
                y = y2_start + row * (cell_h + gap_y)
                if is_active or is_done:
                    bg     = QColor(color + "33")
                    border = QColor(color)
                    val    = self._after[row][col]
                    txt    = QColor(ANIM_COLORS["text_primary"])
                else:
                    bg     = QColor(ANIM_COLORS["bg_input"])
                    border = QColor(ANIM_COLORS["border"])
                    val    = "--"
                    txt    = QColor(ANIM_COLORS["text_muted"])
                p.setBrush(QBrush(bg))
                p.setPen(QPen(border, 1))
                p.drawRoundedRect(x_col + 2, y, cell_w, cell_h, 3, 3)
                p.setFont(font_val)
                p.setPen(txt)
                p.drawText(QRect(x_col + 2, y, cell_w, cell_h),
                           Qt.AlignmentFlag.AlignCenter, val)

        # Aktif sütunun formüllerini en altta tek blok olarak göster
        active_idx = self._active_col - 1
        if 0 <= active_idx < 4:
            color = self._COL_COLORS[active_idx]
            fml_y = y2_start + 4 * (cell_h + gap_y) + 8

            # Başlık satırı: hangi sütun için
            p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            p.setPen(QColor(color))
            p.drawText(QRect(0, fml_y, W, 14),
                       Qt.AlignmentFlag.AlignCenter,
                       f"S{active_idx + 1} sütununun GF(2⁸) çıkış formülleri:")
            fml_y += 16

            # 4 formül — Courier 9pt, satırlar açık aralıklı (h=14)
            p.setFont(QFont("Courier New", 9))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            line_h = 14
            for fi, fml in enumerate(self._FORMULAS):
                p.drawText(QRect(8, fml_y + fi * line_h, W - 16, line_h),
                           Qt.AlignmentFlag.AlignCenter,
                           f"out[{fi}] = {fml}")

        p.end()


# ---------------------------------------------------------------------------
# SubBytes animasyonlu S-Box arama widget'ı
# ---------------------------------------------------------------------------

class _SubBytesAnimWidget(QWidget):
    """
    SubBytes operasyonunun byte-bazlı S-Box dönüşümünü gösterir.
    16 byte için 'giriş → çıkış' şekilde 4×4 düzende listelenir;
    her satır 700ms aralıkla canlanır.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._before: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._after: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._revealed = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._advance)
        self.setMinimumHeight(330)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_data(self, before: list[list[str]], after: list[list[str]]) -> None:
        self._before = before
        self._after = after
        self._revealed = 0
        self._anim_timer.start(420)
        self.update()

    def _advance(self) -> None:
        self._revealed += 1
        if self._revealed >= 4:
            self._revealed = 4
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()
        color = ANIM_COLORS["accent_yellow"]

        # Başlık
        p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        p.setPen(QColor(color))
        p.drawText(QRect(0, 6, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "SubBytes — S-Box ile byte değiştirme")

        # Açıklama
        p.setFont(QFont("Georgia", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 26, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "her byte:  giriş  →  S-Box[giriş]  =  çıkış")

        # 4 satır × 4 dönüşüm (4×4=16 byte)
        # Her satır: "R0:  49→3b   7e→f3   15→59   16→47"
        y_top = 50
        row_h = 30
        cell_box_w = 28
        cell_box_h = 22
        sep = 8           # giriş ↔ çıkış arası ok
        pair_w = cell_box_w * 2 + sep   # ~64
        pair_gap = 6
        total_pair_w = 4 * pair_w + 3 * pair_gap
        ox = max(8, (W - 24 - total_pair_w) // 2 + 24)

        for r in range(4):
            y = y_top + r * row_h
            revealed_row = r < self._revealed

            # Satır etiketi
            p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"] if revealed_row
                            else ANIM_COLORS["text_muted"]))
            p.drawText(QRect(2, y, 22, cell_box_h),
                       Qt.AlignmentFlag.AlignCenter, f"r{r}")

            for c in range(4):
                gx = ox + c * (pair_w + pair_gap)
                in_byte = self._before[r][c]
                out_byte = self._after[r][c]

                if revealed_row:
                    # Giriş kutusu
                    in_bg = QColor(ANIM_COLORS["bg_input"])
                    p.setBrush(QBrush(in_bg))
                    p.setPen(QPen(QColor(ANIM_COLORS["text_muted"]), 1))
                    p.drawRoundedRect(gx, y, cell_box_w, cell_box_h, 3, 3)
                    p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
                    p.setPen(QColor(ANIM_COLORS["text_primary"]))
                    p.drawText(QRect(gx, y, cell_box_w, cell_box_h),
                               Qt.AlignmentFlag.AlignCenter, in_byte)

                    # Ok
                    arr_x = gx + cell_box_w
                    arr_mid = y + cell_box_h // 2
                    p.setPen(QPen(QColor(color), 2))
                    p.drawLine(arr_x + 1, arr_mid, arr_x + sep - 3, arr_mid)
                    pts = QPolygon([
                        QPoint(arr_x + sep - 1, arr_mid),
                        QPoint(arr_x + sep - 5, arr_mid - 3),
                        QPoint(arr_x + sep - 5, arr_mid + 3),
                    ])
                    p.setBrush(QBrush(QColor(color)))
                    p.drawPolygon(pts)

                    # Çıkış kutusu
                    out_bg = QColor(color)
                    out_bg.setAlpha(80)
                    p.setBrush(QBrush(out_bg))
                    p.setPen(QPen(QColor(color), 1))
                    p.drawRoundedRect(gx + cell_box_w + sep, y,
                                      cell_box_w, cell_box_h, 3, 3)
                    p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
                    p.setPen(QColor(ANIM_COLORS["text_primary"]))
                    p.drawText(QRect(gx + cell_box_w + sep, y,
                                     cell_box_w, cell_box_h),
                               Qt.AlignmentFlag.AlignCenter, out_byte)
                else:
                    # Soluk yer-tutucu
                    p.setBrush(QBrush(QColor(ANIM_COLORS["bg_input"])))
                    p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1, Qt.PenStyle.DashLine))
                    p.drawRoundedRect(gx, y, pair_w, cell_box_h, 3, 3)

        # Alt notu
        note_y = y_top + 4 * row_h + 8
        p.setFont(QFont("Georgia", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(8, note_y, W - 16, 14),
                   Qt.AlignmentFlag.AlignCenter,
                   "S-Box: 256 girişli, FIPS 197'de tanımlı sabit tablo.")
        p.end()


# ---------------------------------------------------------------------------
# AddRoundKey animasyonlu XOR widget'ı
# ---------------------------------------------------------------------------

class _AddRoundKeyAnimWidget(QWidget):
    """
    AddRoundKey operasyonunun byte-bazlı XOR hesabını gösterir.
    16 byte için 'state ⊕ key = sonuç' şekilde 4×4 düzende listelenir;
    her satır 420ms aralıkla canlanır.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._before: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._after: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._round_key: list[list[str]] = [["--"] * 4 for _ in range(4)]
        self._round_no: int = 0
        self._revealed = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._advance)
        self.setMinimumHeight(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_data(
        self, before: list[list[str]], after: list[list[str]],
        round_key: list[list[str]], round_no: int,
    ) -> None:
        self._before = before
        self._after = after
        self._round_key = round_key
        self._round_no = round_no
        self._revealed = 0
        self._anim_timer.start(420)
        self.update()

    def _advance(self) -> None:
        self._revealed += 1
        if self._revealed >= 4:
            self._revealed = 4
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()
        color = ANIM_COLORS["accent_peach"]

        # Başlık
        p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        p.setPen(QColor(color))
        p.drawText(QRect(0, 6, W, 18), Qt.AlignmentFlag.AlignCenter,
                   f"AddRoundKey — Round {self._round_no} anahtarı ile XOR")

        # Açıklama
        p.setFont(QFont("Georgia", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 26, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "her byte:  state  ⊕  round_key  =  yeni state")

        # round_key kaynak açıklaması — kullanıcı "bu anahtar bayt'ları nereden geldi" sorduğunda anlasın
        p.setFont(QFont("Georgia", 8))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(0, 42, W, 14), Qt.AlignmentFlag.AlignCenter,
                   f"(round_key: 256-bit ana anahtardan AES anahtar genişletme algoritmasıyla "
                   f"türetilen Round {self._round_no} alt anahtarı — 16 bayt)")

        # 4 satır × 4 sütun XOR hesabı — pencere genişliğine adaptif
        y_top = 64
        row_h = 32
        cell_h = 22
        sym_w = 11    # ⊕ ve = sembol genişliği
        slot_gap = 4
        # Kullanılabilir genişlik: pencere - sol etiket alanı (24) - kenar boşluğu (8)
        avail_w = max(280, W - 32)
        # Her slot: 3 kutu + 2 sembol. 4 slot + 3 boşluk toplam:
        # 4*(3*cell_w + 2*sym_w) + 3*slot_gap ≤ avail_w
        # 12*cell_w + 8*sym_w + 12 ≤ avail_w
        cell_w = max(18, (avail_w - 8 * sym_w - 12) // 12)
        cell_w = min(cell_w, 30)
        slot_w = cell_w * 3 + 2 * sym_w
        total_w = 4 * slot_w + 3 * slot_gap
        # İçerik uzun olabilir, ortala
        ox = max(24, (W - total_w) // 2)

        for r in range(4):
            y = y_top + r * row_h
            revealed_row = r < self._revealed

            # Satır etiketi
            p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"] if revealed_row
                            else ANIM_COLORS["text_muted"]))
            p.drawText(QRect(2, y, 22, cell_h),
                       Qt.AlignmentFlag.AlignCenter, f"r{r}")

            for c in range(4):
                sx = ox + c * (slot_w + slot_gap)
                state_byte = self._before[r][c]
                key_byte = self._round_key[r][c]
                out_byte = self._after[r][c]

                if revealed_row:
                    # state hücresi (mavi-soluk)
                    p.setBrush(QBrush(QColor(ANIM_COLORS["accent_blue"] + "55")))
                    p.setPen(QPen(QColor(ANIM_COLORS["accent_blue"]), 1))
                    p.drawRoundedRect(sx, y, cell_w, cell_h, 3, 3)
                    p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
                    p.setPen(QColor(ANIM_COLORS["text_primary"]))
                    p.drawText(QRect(sx, y, cell_w, cell_h),
                               Qt.AlignmentFlag.AlignCenter, state_byte)

                    # ⊕ sembolü
                    p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
                    p.setPen(QColor(color))
                    p.drawText(QRect(sx + cell_w, y, sym_w, cell_h),
                               Qt.AlignmentFlag.AlignCenter, "⊕")

                    # key hücresi (şeftali-soluk)
                    kx = sx + cell_w + sym_w
                    p.setBrush(QBrush(QColor(color + "55")))
                    p.setPen(QPen(QColor(color), 1))
                    p.drawRoundedRect(kx, y, cell_w, cell_h, 3, 3)
                    p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
                    p.setPen(QColor(ANIM_COLORS["text_primary"]))
                    p.drawText(QRect(kx, y, cell_w, cell_h),
                               Qt.AlignmentFlag.AlignCenter, key_byte)

                    # = sembolü
                    p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
                    p.setPen(QColor(ANIM_COLORS["text_secondary"]))
                    p.drawText(QRect(kx + cell_w, y, sym_w, cell_h),
                               Qt.AlignmentFlag.AlignCenter, "=")

                    # result hücresi (yeşil-canlı)
                    rx = kx + cell_w + sym_w
                    p.setBrush(QBrush(QColor(ANIM_COLORS["accent_green"] + "55")))
                    p.setPen(QPen(QColor(ANIM_COLORS["accent_green"]), 1))
                    p.drawRoundedRect(rx, y, cell_w, cell_h, 3, 3)
                    p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
                    p.setPen(QColor(ANIM_COLORS["text_primary"]))
                    p.drawText(QRect(rx, y, cell_w, cell_h),
                               Qt.AlignmentFlag.AlignCenter, out_byte)
                else:
                    # Soluk yer-tutucu
                    p.setBrush(QBrush(QColor(ANIM_COLORS["bg_input"])))
                    p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1, Qt.PenStyle.DashLine))
                    p.drawRoundedRect(sx, y, slot_w, cell_h, 3, 3)

        # Alt notu — XOR'un nasıl çalıştığı
        note_y = y_top + 4 * row_h + 8
        p.setFont(QFont("Georgia", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(8, note_y, W - 16, 14),
                   Qt.AlignmentFlag.AlignCenter,
                   "XOR: bit-bazında karşılaştırma; aynı → 0, farklı → 1.")
        p.end()

