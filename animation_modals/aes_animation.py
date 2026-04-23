# animation_modals/aes_animation.py
"""
AESAnimationWindow — AES-256-GCM şifreleme sürecini görselleştirir.

Yapı:
  1. Giriş animasyonu: AES-256 round yapısı adım adım belirir (otomatik, QTimer)
  2. Round görünümü: 14 round, tıklanabilir round bar, manuel navigasyon
     - SubBytes: hücre-hücre highlight (MatrixWidget.highlight_cells_sequential)
     - ShiftRows: satır kaydırma okları + animate_row_shift
     - MixColumns: sütun karıştırma görsel açıklaması
     - AddRoundKey: XOR highlight
"""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from .base import CryptoAnimationWindow, ANIM_COLORS
from .matrix_widget import MatrixWidget
from .aes_pure import aes256_encrypt_with_rounds

_COLORS_OP = {
    "SubBytes":    ANIM_COLORS["accent_yellow"],
    "ShiftRows":   ANIM_COLORS["accent_blue"],
    "MixColumns":  ANIM_COLORS["accent_mauve"],
    "AddRoundKey": ANIM_COLORS["accent_peach"],
}


# ---------------------------------------------------------------------------
# Canlı matris demo widget'ı — intro için AES operasyonlarını simüle eder
# ---------------------------------------------------------------------------

class _MatrixDemoWidget(QWidget):
    """
    AES intro ekranında gösterilen canlı 4×4 matris animasyonu.
    QTimer ile SubBytes → ShiftRows → MixColumns → AddRoundKey döngüsü yapar.
    """

    _OP_COLORS = [
        ANIM_COLORS["accent_yellow"],   # SubBytes
        ANIM_COLORS["accent_blue"],     # ShiftRows
        ANIM_COLORS["accent_mauve"],    # MixColumns
        ANIM_COLORS["accent_peach"],    # AddRoundKey
    ]
    _OP_NAMES = ["SubBytes", "ShiftRows", "MixColumns", "AddRoundKey"]

    # Başlangıç demo değerleri (görsel amaçlı)
    _INIT_VALS = [
        ["19", "a0", "9a", "e9"],
        ["3d", "f4", "c6", "f8"],
        ["e3", "e2", "8d", "48"],
        ["be", "2b", "2a", "08"],
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tick = 0
        self._cells = [row[:] for row in self._INIT_VALS]
        self._bg_colors = [[ANIM_COLORS["bg_card"]] * 4 for _ in range(4)]
        self._op_idx = 0      # hangi operasyon (0-3)
        self._op_tick = 0     # operasyon içi adım
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(110)
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _step(self) -> None:
        self._tick += 1
        t = self._tick

        # Her operasyon 24 tick sürer
        op = (t // 24) % 4
        sub = t % 24
        self._op_idx = op

        if op == 0:  # SubBytes: hücreleri sırayla highlight et
            r, c = divmod(sub % 16, 4)
            self._bg_colors = [[ANIM_COLORS["bg_card"]] * 4 for _ in range(4)]
            self._bg_colors[r][c] = self._OP_COLORS[0]
            self._cells[r][c] = f"{(self._tick * 37 + r * 4 + c) % 256:02x}"

        elif op == 1:  # ShiftRows: satır satır highlight
            row = sub // 6
            row = min(row, 3)
            self._bg_colors = [[ANIM_COLORS["bg_card"]] * 4 for _ in range(4)]
            row_colors = [
                ANIM_COLORS["text_muted"],
                ANIM_COLORS["accent_blue"],
                ANIM_COLORS["accent_mauve"],
                ANIM_COLORS["accent_peach"],
            ]
            for c in range(4):
                self._bg_colors[row][c] = row_colors[row]

        elif op == 2:  # MixColumns: sütun sütun highlight
            col = sub // 6
            col = min(col, 3)
            self._bg_colors = [[ANIM_COLORS["bg_card"]] * 4 for _ in range(4)]
            col_colors = [
                ANIM_COLORS["accent_blue"],
                ANIM_COLORS["accent_mauve"],
                ANIM_COLORS["accent_yellow"],
                ANIM_COLORS["accent_peach"],
            ]
            for r in range(4):
                self._bg_colors[r][col] = col_colors[col]

        else:  # AddRoundKey: tümü yanıp söner
            lit = (sub % 6) < 3
            color = self._OP_COLORS[3] if lit else ANIM_COLORS["bg_card"]
            self._bg_colors = [[color] * 4 for _ in range(4)]

        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        margin = 12
        label_h = 28
        avail_w = W - 2 * margin
        avail_h = H - label_h - margin
        cell_size = min(avail_w // 4, avail_h // 4) - 4
        gap = 4
        grid_w = 4 * cell_size + 3 * gap
        grid_h = 4 * cell_size + 3 * gap
        ox = (W - grid_w) // 2
        oy = label_h + (avail_h - grid_h) // 2

        # Operasyon etiketi
        op_color = self._OP_COLORS[self._op_idx]
        p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        p.setPen(QColor(op_color))
        p.drawText(QRect(0, 4, W, label_h - 4),
                   Qt.AlignmentFlag.AlignCenter,
                   self._OP_NAMES[self._op_idx])

        # Hücreler
        font_val = QFont("Courier New", max(9, cell_size // 4), QFont.Weight.Bold)
        for r in range(4):
            for c in range(4):
                x = ox + c * (cell_size + gap)
                y = oy + r * (cell_size + gap)
                bg = QColor(self._bg_colors[r][c])
                border = QColor(bg).lighter(150)
                p.setBrush(QBrush(bg))
                p.setPen(QPen(border, 1))
                p.drawRoundedRect(x, y, cell_size, cell_size, 5, 5)
                p.setFont(font_val)
                p.setPen(QColor(ANIM_COLORS["text_primary"]))
                p.drawText(QRect(x, y, cell_size, cell_size),
                           Qt.AlignmentFlag.AlignCenter, self._cells[r][c])

        p.end()


# ---------------------------------------------------------------------------
# AES Giriş Animasyonu Widget'ı
# ---------------------------------------------------------------------------

class _AESIntroWidget(QWidget):
    """
    AES-256 round yapısını aşamalı olarak gösteren giriş widget'ı.
    QTimer ile her 600ms'de bir bileşen görünür hale gelir.
    Tüm bileşenler göründükten sonra 'ready' sinyali yerine callback çağrılır.
    """

    def __init__(self, on_complete: "callable", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_complete = on_complete
        self._phase = 0
        self._widgets: list[QWidget] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._show_next_phase)
        self._init_ui()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(10, 6, 10, 6)
        main.setSpacing(4)

        title = QLabel("AES-256  Şifreleme Süreci")
        title.setFont(QFont("Georgia", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(title)

        # ── Yatay bölüm: sol=canlı matris, sağ=akış şeması ──
        h_row = QHBoxLayout()
        h_row.setSpacing(12)
        main.addLayout(h_row)

        # Sol: canlı matris animasyonu
        left_frame = QFrame()
        left_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 10px; }}"
        )
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(12, 8, 12, 8)
        left_lay.setSpacing(4)
        demo_title = QLabel("Canlı Şifreleme Önizlemesi")
        demo_title.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        demo_title.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        demo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_lay.addWidget(demo_title)
        self._matrix_demo = _MatrixDemoWidget()
        left_lay.addWidget(self._matrix_demo, stretch=1)
        h_row.addWidget(left_frame, stretch=2)

        # Sağ: akış şeması
        right_w = QWidget()
        right_lay = QVBoxLayout(right_w)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        right_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        h_row.addWidget(right_w, stretch=3)

        # ── Sağ taraf: akış şeması widget'ları ──

        # Giriş kutusu
        self._intro_plain = self._make_box(
            "📄  Düz Metin  (Plaintext)", ANIM_COLORS["text_secondary"]
        )
        right_lay.addWidget(self._intro_plain)
        self._intro_plain.setVisible(False)
        self._widgets.append(self._intro_plain)

        arr0 = self._make_arrow()
        right_lay.addWidget(arr0)
        arr0.setVisible(False)
        self._widgets.append(arr0)

        self._box_r0 = self._make_round_box(
            "🔑  Initial Round  (Round 0)",
            ["AddRoundKey"],
            ANIM_COLORS["accent_peach"],
        )
        right_lay.addWidget(self._box_r0)
        self._box_r0.setVisible(False)
        self._widgets.append(self._box_r0)

        arr1 = self._make_arrow()
        right_lay.addWidget(arr1)
        arr1.setVisible(False)
        self._widgets.append(arr1)

        self._box_main = self._make_round_box(
            "🔄  Ana Roundlar  (R1 – R13)",
            ["1-SubBytes", "2-ShiftRows", "3-MixColumns", "4-AddRoundKey"],
            ANIM_COLORS["accent_blue"],
        )
        right_lay.addWidget(self._box_main)
        self._box_main.setVisible(False)
        self._widgets.append(self._box_main)

        arr2 = self._make_arrow()
        right_lay.addWidget(arr2)
        arr2.setVisible(False)
        self._widgets.append(arr2)

        self._box_r14 = self._make_round_box(
            "🏁  Son Round  (R14)",
            ["1-SubBytes", "2-ShiftRows", "3-AddRoundKey  (MixColumns yok)"],
            ANIM_COLORS["accent_green"],
        )
        right_lay.addWidget(self._box_r14)
        self._box_r14.setVisible(False)
        self._widgets.append(self._box_r14)

        arr3 = self._make_arrow()
        right_lay.addWidget(arr3)
        arr3.setVisible(False)
        self._widgets.append(arr3)

        self._intro_cipher = self._make_box(
            "🔒  Şifreli Metin  (Ciphertext)", ANIM_COLORS["accent_green"]
        )
        right_lay.addWidget(self._intro_cipher)
        self._intro_cipher.setVisible(False)
        self._widgets.append(self._intro_cipher)

        right_lay.addSpacing(16)

        # Başla butonu
        self._btn_start = QPushButton("▶  Görselleştirmeyi Başlat")
        self._btn_start.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
        self._btn_start.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; "
            f"border-radius: 6px; padding: 6px 18px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        self._btn_start.setVisible(False)
        self._btn_start.clicked.connect(self._on_complete)
        right_lay.addWidget(self._btn_start, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._widgets.append(self._btn_start)
        right_lay.addStretch()

    @staticmethod
    def _make_box(text: str, color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 6, 8, 6)
        lbl = QLabel(text)
        lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        return f

    @staticmethod
    def _make_round_box(title: str, ops: list[str], color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(3)
        t = QLabel(title)
        t.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {color}; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setWordWrap(True)
        lay.addWidget(t)
        for op in ops:
            o = QLabel(f"  →  {op}")
            o.setFont(QFont("Segoe UI", 9))
            o.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']}; border: none;")
            o.setWordWrap(True)
            lay.addWidget(o)
        return f

    @staticmethod
    def _make_arrow() -> QLabel:
        lbl = QLabel("⬇")
        lbl.setFont(QFont("Segoe UI", 14))
        lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(20)
        return lbl

    def start(self) -> None:
        self._timer.start(600)

    def _show_next_phase(self) -> None:
        if self._phase >= len(self._widgets):
            self._timer.stop()
            return
        self._widgets[self._phase].setVisible(True)
        self._phase += 1


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
        self.setMinimumHeight(340)
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
        cell_h = 30
        gap = 4
        grid_w = 4 * cell_w + 3 * gap
        x0 = max(4, (W - grid_w) // 2)
        row_section = 84  # height per row (before + arrow area + after)

        font_val = QFont("Courier New", 8, QFont.Weight.Bold)
        font_lbl = QFont("IBM Plex Sans", 8)

        # Header
        p.setFont(font_lbl)
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

            # ── Ok ve shift etiketi ──
            arr_y = y_top + cell_h + 6
            lbl_y = arr_y + 2
            if revealed:
                if shift == 0:
                    # Kesikli çizgi: sabit
                    pen_d = QPen(QColor(ANIM_COLORS["text_muted"]), 1, Qt.PenStyle.DashLine)
                    p.setPen(pen_d)
                    p.drawLine(x0, arr_y + 8, x0 + grid_w, arr_y + 8)
                    p.setFont(font_lbl)
                    p.setPen(QColor(ANIM_COLORS["text_muted"]))
                    p.drawText(QRect(x0, lbl_y, grid_w, 14),
                               Qt.AlignmentFlag.AlignCenter, "──  sabit  ──")
                else:
                    # Sol ok: kaydırma yönü
                    ax_end = x0
                    ax_start = x0 + grid_w
                    pen_a = QPen(QColor(color), 2)
                    p.setPen(pen_a)
                    mid_arr = arr_y + 8
                    p.drawLine(ax_start, mid_arr, ax_end + 8, mid_arr)
                    # Ok ucu (sola)
                    pts = QPolygon([
                        QPoint(ax_end, mid_arr),
                        QPoint(ax_end + 9, mid_arr - 5),
                        QPoint(ax_end + 9, mid_arr + 5),
                    ])
                    p.setBrush(QBrush(QColor(color)))
                    p.drawPolygon(pts)
                    # Shift miktarı etiketi
                    p.setFont(font_lbl)
                    p.setPen(QColor(color))
                    p.drawText(QRect(x0, lbl_y, grid_w, 14),
                               Qt.AlignmentFlag.AlignCenter,
                               self._SHIFT_LABELS[row])

            # ── Sonra (after) hücreleri ──
            y_bot = arr_y + 22
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
        self.setMinimumHeight(300)
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

            # Formula labels for the active column (drawn below output cells)
            if is_active:
                fml_y = y2_start + 4 * (cell_h + gap_y) + 4
                p.setFont(font_fml)
                p.setPen(QColor(color))
                for fi, fml in enumerate(self._FORMULAS):
                    fml_x = max(0, x_col - col_section_w // 2)
                    fml_w = min(col_section_w * 2, W - fml_x)
                    p.drawText(QRect(fml_x, fml_y + fi * 11, fml_w, 11),
                               Qt.AlignmentFlag.AlignLeft, fml)

        p.end()


# ---------------------------------------------------------------------------
# Yardımcı: step listesi oluştur
# ---------------------------------------------------------------------------

def _build_steps(rounds_data: list[dict]) -> list[dict]:
    steps: list[dict] = []
    for rd in rounds_data:
        rnd = rd["round"]
        if rnd == 0:
            steps.append({
                "round": 0, "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": "Round 0 — Initial AddRoundKey\nPlaintext, ilk round anahtarı ile XOR'landı.",
            })
        elif rnd <= 13:
            for op, key, desc in [
                ("SubBytes",   "after_sub_bytes",    f"Round {rnd} — SubBytes\nHer byte S-Box'taki karşılığıyla değiştirildi."),
                ("ShiftRows",  "after_shift_rows",   f"Round {rnd} — ShiftRows\nSatır 1: sabit, 2: 1←, 3: 2←, 4: 3← kaydı."),
                ("MixColumns", "after_mix_columns",  f"Round {rnd} — MixColumns\nHer sütun GF(2⁸) matris çarpımıyla karıştırıldı."),
                ("AddRoundKey","after_add_round_key",f"Round {rnd} — AddRoundKey\nState, {rnd}. round anahtarı ile XOR'landı."),
            ]:
                steps.append({
                    "round": rnd, "operation": op,
                    "matrix": rd[key],
                    "color": _COLORS_OP[op],
                    "description": desc,
                })
        else:
            for op, key, desc in [
                ("SubBytes",   "after_sub_bytes",    "Round 14 — SubBytes  (Son round)"),
                ("ShiftRows",  "after_shift_rows",   "Round 14 — ShiftRows"),
                ("AddRoundKey","after_add_round_key","Round 14 — AddRoundKey  (MixColumns yok)"),
            ]:
                steps.append({
                    "round": rnd, "operation": op,
                    "matrix": rd[key],
                    "color": _COLORS_OP[op],
                    "description": desc,
                })
    return steps


# ---------------------------------------------------------------------------
# AES Animasyon Penceresi
# ---------------------------------------------------------------------------

class AESAnimationWindow(CryptoAnimationWindow):
    """
    AES-256-GCM animasyon penceresi.

    Parametreler:
      key             : 32 byte session key
      plaintext       : şifrelenecek veri (ilk 16 byte kullanılır)
      expected_ct_hex : crypto_core AES-GCM çıktısının hex preview'u
    """

    def __init__(
        self,
        key: bytes,
        plaintext: bytes,
        expected_ct_hex: str,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self._key = key
        self._plaintext = plaintext
        self._expected_ct_hex = expected_ct_hex

        aes_result = aes256_encrypt_with_rounds(key, plaintext)
        self._steps_data = _build_steps(aes_result["rounds_data"])
        self._final_block_hex = aes_result["final_block_hex"]

        # round → ilk step indeksini hesapla
        self._round_start: dict[int, int] = {}
        for i, s in enumerate(self._steps_data):
            r = s["round"]
            if r not in self._round_start:
                self._round_start[r] = i

        # Başlangıçta intro görünür; manual_mode round görünümü için
        super().__init__(
            "🔒  AES-256-GCM Şifreleme Animasyonu",
            len(self._steps_data),
            manual_mode=True,
            on_close=on_close,
        )

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Giriş animasyonu
        self._intro = _AESIntroWidget(on_complete=self._switch_to_rounds)
        self._stack.addWidget(self._intro)

        # Sayfa 1 — Round görünümü
        self._round_page = self._make_round_page()
        self._stack.addWidget(self._round_page)

        # Sayfa 2 — Eşleşme sonucu
        self._match_page = self._make_match_page()
        self._stack.addWidget(self._match_page)

        # Intro başlat (otomatik)
        self._intro.start()

    def _make_round_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        # Tıklanabilir round bar
        rb_frame = QFrame()
        rb_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px; }}"
        )
        rb_lay = QHBoxLayout(rb_frame)
        rb_lay.setContentsMargins(6, 4, 6, 4)
        rb_lay.setSpacing(3)
        self._round_btns: list[QPushButton] = []
        for i in range(15):
            btn = QPushButton(f"R{i}")
            btn.setFixedWidth(38)
            btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            btn.setStyleSheet(self._round_btn_style(False))
            btn.clicked.connect(lambda checked, r=i: self._jump_to_round(r))
            rb_lay.addWidget(btn)
            self._round_btns.append(btn)
        lay.addWidget(rb_frame)

        # Operasyon başlığı
        self._op_title = QLabel()
        self._op_title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._op_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._op_title)

        # Açıklama
        self._desc_lbl = QLabel()
        self._desc_lbl.setFont(QFont("IBM Plex Sans", 10))
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_lbl.setWordWrap(True)
        lay.addWidget(self._desc_lbl)

        # Matris + yardımcı widget
        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        mat_frame = QFrame()
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        mat_lay = QVBoxLayout(mat_frame)
        mat_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matrix = MatrixWidget(parent=self)
        mat_lay.addWidget(self._matrix, alignment=Qt.AlignmentFlag.AlignCenter)
        mat_lbl = QLabel("State Matrisi  (4×4 byte, hex)")
        mat_lbl.setFont(QFont("IBM Plex Sans", 9))
        mat_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        mat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mat_lay.addWidget(mat_lbl)
        content_row.addWidget(mat_frame)

        # Sağ panel — operasyona göre değişir
        self._side_stack = QStackedWidget()
        self._side_stack.setMinimumWidth(320)
        self._side_stack.setMaximumWidth(430)

        empty = QWidget()  # boş panel (AddRoundKey ve SubBytes için)
        self._side_stack.addWidget(empty)                    # index 0

        # ShiftRows: scroll area içinde (4 satır × 84px = ~360px gerektirir)
        from PyQt6.QtWidgets import QScrollArea
        self._shift_widget = _ShiftRowsAnimWidget()
        shift_scroll = QScrollArea()
        shift_scroll.setWidget(self._shift_widget)
        shift_scroll.setWidgetResizable(True)
        shift_scroll.setStyleSheet("background: transparent; border: none;")
        self._side_stack.addWidget(shift_scroll)             # index 1

        self._mix_widget = _MixColumnsAnimWidget()           # MixColumns için
        self._side_stack.addWidget(self._mix_widget)         # index 2

        content_row.addWidget(self._side_stack)
        lay.addLayout(content_row, stretch=1)   # stretch=1: content_row fills remaining height
        return w

    def _make_match_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 8, 16, 8)

        self._match_lbl = QLabel()
        self._match_lbl.setFont(QFont("Courier New", 12))
        self._match_lbl.setWordWrap(True)
        self._match_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(self._match_lbl)
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    # Navigasyon yardımcıları
    # ------------------------------------------------------------------

    def _switch_to_rounds(self) -> None:
        """Intro'dan round görünümüne geç."""
        self._stack.setCurrentWidget(self._round_page)
        self._render_step(0)
        self._progress.setValue(1)

    def _jump_to_round(self, r: int) -> None:
        """Round bar'daki butona tıklanınca o round'un ilk adımına atla."""
        if r not in self._round_start:
            return
        self.current_step = self._round_start[r]
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)
        if hasattr(self, "_btn_prev"):
            self._btn_prev.setEnabled(self.current_step > 0)
        if hasattr(self, "_btn_next"):
            self._btn_next.setEnabled(True)
            self._btn_next.setText("İleri  ▶")

    @staticmethod
    def _round_btn_style(active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
                f"color: {ANIM_COLORS['bg_main']}; border: none; "
                f"border-radius: 3px; padding: 2px; font-weight: bold; }}"
            )
        return (
            f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_muted']}; border: none; "
            f"border-radius: 3px; padding: 2px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['border']}; "
            f"color: {ANIM_COLORS['text_primary']}; }}"
        )

    def _update_round_bar(self, active: int) -> None:
        for i, btn in enumerate(self._round_btns):
            btn.setStyleSheet(self._round_btn_style(i == active))

    # ------------------------------------------------------------------
    # Adım render
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if self._stack.currentWidget() != self._round_page:
            self._stack.setCurrentWidget(self._round_page)

        step = self._steps_data[step_idx]
        self._update_round_bar(step["round"])
        self._op_title.setText(
            f"Round {step['round']} / 14   —   {step['operation']}"
        )
        self._op_title.setStyleSheet(f"color: {step['color']};")
        self._desc_lbl.setText(step["description"])

        op = step["operation"]

        # Bir önceki adımın matrisi (before state)
        before = (
            self._steps_data[step_idx - 1]["matrix"]
            if step_idx > 0
            else step["matrix"]
        )
        after = step["matrix"]

        if op == "SubBytes":
            self._side_stack.setCurrentIndex(0)
            ops = [(r, c, after[r][c]) for r in range(4) for c in range(4)]
            self._matrix.highlight_cells_sequential(
                ops, step["color"], interval_ms=60, callback=None
            )

        elif op == "ShiftRows":
            self._side_stack.setCurrentIndex(1)
            # Sağ panel: animasyonlu ok diyagramı (önce → sonra)
            self._shift_widget.set_data(before, after)
            # Ana matris: satır kaydırma animasyonu
            for row_idx, shift in enumerate([0, 1, 2, 3]):
                if shift > 0:
                    self._matrix.animate_row_shift(row_idx, shift, step["color"])
                else:
                    for c in range(4):
                        self._matrix.update_cell(row_idx, c, after[row_idx][c])

        elif op == "MixColumns":
            self._side_stack.setCurrentIndex(2)
            # Sağ panel: animasyonlu sütun karıştırma diyagramı
            self._mix_widget.set_data(before, after)
            # Ana matris: sütun renkleriyle güncelle
            col_colors = [
                ANIM_COLORS["accent_blue"],
                ANIM_COLORS["accent_mauve"],
                ANIM_COLORS["accent_yellow"],
                ANIM_COLORS["accent_peach"],
            ]
            for col in range(4):
                for row in range(4):
                    self._matrix.update_cell(row, col, after[row][col], col_colors[col])

        else:  # AddRoundKey
            self._side_stack.setCurrentIndex(0)
            self._matrix.set_matrix(after, step["color"])
            QTimer.singleShot(250, self._matrix.reset_colors)

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._match_page)
        self._update_round_bar(14)
        last = self._steps_data[-1]
        mat = last["matrix"]   # 4×4 liste
        self._matrix.set_matrix(mat, ANIM_COLORS["accent_green"])

        # ── Final state matrisi → şifreli metin byte sırası ──
        # AES, state matrisini sütun-öncelikli (column-major) okur
        col_bytes: list[list[str]] = [
            [mat[r][c] for r in range(4)] for c in range(4)
        ]
        hex_out = "".join("".join(col) for col in col_bytes)
        assert len(hex_out) == 32, f"Unexpected hex_out length: {len(hex_out)}"

        col_lines = []
        for c in range(4):
            vals = " ".join(col_bytes[c])
            col_lines.append(f"  Sütun {c+1}: [{vals}]")

        lines = [
            "━━  14 ROUND TAMAMLANDI  ━━",
            "",
            "Final State Matrisi (Round 14 çıkışı):",
            "  ┌────────────────────────┐",
        ]
        for r in range(4):
            lines.append(f"  │  {' '.join(mat[r])}  │")
        lines += [
            "  └────────────────────────┘",
            "",
            "━━  MATRİS → ŞİFRELİ ÇIKIŞ  ━━",
            "",
            "AES, matrisi sütun-öncelikli okur (Column-Major):",
            "",
        ]
        lines += col_lines
        lines += [
            "",
            "Birleştirme: Sütun1 ‖ Sütun2 ‖ Sütun3 ‖ Sütun4",
            f"  → {hex_out[:16]}",
            f"     {hex_out[16:32]}",
            "",
            "━━  GCM MODU  ━━",
            "",
            "AES-256-GCM'de bu 16-byte blok doğrudan şifreli metin değil,",
            "CTR sayacının şifrelenmiş halidir (keystream).",
            "",
            "keystream ⊕ plaintext = ciphertext",
            "",
            "GHASH fonksiyonu da ayrıca kimlik doğrulama etiketi üretir.",
            "",
            "─" * 54,
            f"Animasyon çıktısı (AES-ECB blok dönüşümü):  {self._final_block_hex}",
            f"crypto_core GCM çıktısı (gerçek şifreli metin):  {self._expected_ct_hex}",
            "",
        ]

        # Build HTML for the label so the ⚠ warning line can be colored
        # differently (yellow) from the ✅ success line (green via stylesheet).
        warning_line = (
            f'<span style="color:{ANIM_COLORS["accent_yellow"]}; font-weight:bold;">'
            "⚠  Bu iki değer farklıdır — bu beklenen bir durumdur:"
            "</span>"
        )
        plain_lines = [
            "",
            "  Animasyon: plaintext'in 14 round AES-ECB çıktısı",
            "  GCM modu:  CTR sayacı şifrelenir → plaintext ⊕ keystream → ciphertext",
            "             Aynı anahtar, farklı IV ve counter → farklı çıktı",
            "",
            "✅  AES-256-GCM Şifreleme Doğru Çalıştı",
        ]
        html_body = "<br>".join(lines) + "<br>" + warning_line + "<br>" + "<br>".join(plain_lines)
        self._match_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._match_lbl.setText(html_body)
        self._match_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")

    # showEvent override — intro başlatılmış, timer başlatma
    def showEvent(self, event) -> None:  # type: ignore[override]
        # Intro QTimer kendi içinde çalışıyor; base class showEvent'i atla
        QWidget.showEvent(self, event)
