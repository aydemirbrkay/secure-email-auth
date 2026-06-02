# animation_modals/aes_animation.py
"""
AESAnimationWindow — AES-256-GCM şifreleme sürecini görselleştirir.

Yapı:
  1. Giriş animasyonu: AES-256 round yapısı adım adım belirir (otomatik, QTimer)
  2. Round görünümü: 14 round, tıklanabilir round bar, manuel navigasyon.
     State matrisi `_AESStateCompareWidget` ile yan yana iki QPainter
     matrisi olarak gösterilir (önceki + şimdiki), her operasyon kendi
     koreografisini şimdiki matrisin üzerinde oynatır:
     SubBytes / ShiftRows / MixColumns / AddRoundKey.
     Sağ panel, operasyona göre detaylı matematik anlatımı sunan
     yardımcı widget'lara (_SubBytesAnimWidget, _ShiftRowsAnimWidget,
     _MixColumnsAnimWidget, _AddRoundKeyAnimWidget) bağlanır.
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
from .aes_matrix_view import _AESStateCompareWidget
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
        # 220×220 → 180×180: kompakt left_frame'e (max 200 px) sığacak
        # şekilde; matris hücreleri paintEvent'te adaptive cell_size ile
        # ölçeklendiği için içerik korunur (daha küçük ama yine okunaklı).
        self.setMinimumSize(180, 180)
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
        # 16 px sağ margin → kullanıcının istediği "~5% sağ boşluk"
        main.setContentsMargins(8, 4, 16, 4)
        main.setSpacing(3)

        # ── Yatay bölüm: sol=canlı matris, sağ=başlık + akış şeması ──
        # (Başlık eskiden main'de full-width centered idi → kullanıcı geri
        # bildirimi: başlık adımların üstünde, sağ kolonun başında olsun.)
        h_row = QHBoxLayout()
        h_row.setSpacing(8)
        main.addLayout(h_row)

        # Sol: canlı matris animasyonu — max width kaldırıldı, stretch ile
        # viewport'a oranlı genişler (matris paintEvent içinde cell_size'i
        # adaptive ölçeklendiriyor).
        left_frame = QFrame()
        left_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(6, 4, 6, 4)
        left_lay.setSpacing(2)
        demo_title = QLabel("Canlı Şifreleme Önizlemesi")
        demo_title.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        demo_title.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        demo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_lay.addWidget(demo_title)
        self._matrix_demo = _MatrixDemoWidget()
        left_lay.addWidget(self._matrix_demo, stretch=1)
        left_frame.setMinimumWidth(220)
        h_row.addWidget(left_frame, stretch=2)

        # Sağ: başlık + akış şeması — max width kaldırıldı, stretch ile
        # viewport'a oranlı genişler. Stretch ratio 2:3 (sol:sağ) → matris
        # ~%40, akış şeması ~%60 kapsar; sağ kenarda main margin'inden
        # gelen ~16 px (≈%5) boşluk kalır.
        right_w = QWidget()
        right_lay = QVBoxLayout(right_w)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        right_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_w.setMinimumWidth(300)
        h_row.addWidget(right_w, stretch=3)

        # ── Sağ taraf: önce BAŞLIK, sonra akış şeması widget'ları ──

        title = QLabel("AES-256  Şifreleme Süreci")
        title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_lay.addWidget(title)
        right_lay.addSpacing(4)

        # Giriş kutusu
        self._intro_plain = self._make_box(
            "Düz Metin  (Plaintext)", ANIM_COLORS["text_secondary"]
        )
        right_lay.addWidget(self._intro_plain)
        self._intro_plain.setVisible(False)
        self._widgets.append(self._intro_plain)

        arr0 = self._make_arrow()
        right_lay.addWidget(arr0)
        arr0.setVisible(False)
        self._widgets.append(arr0)

        self._box_r0 = self._make_round_box(
            "Initial Round  (Round 0)",
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
            "Ana Roundlar  (R1 – R13)",
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
            "Son Round  (R14)",
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
            "Şifreli Metin  (Ciphertext)", ANIM_COLORS["accent_green"]
        )
        right_lay.addWidget(self._intro_cipher)
        self._intro_cipher.setVisible(False)
        self._widgets.append(self._intro_cipher)

        right_lay.addSpacing(16)

        # Başla butonu
        self._btn_start = QPushButton("Görselleştirmeyi Başlat")
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
        lay.setContentsMargins(6, 3, 6, 3)  # daha kompakt
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
        lay.setContentsMargins(8, 4, 8, 4)  # daha kompakt — boş alan azaldı
        lay.setSpacing(1)
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
# Plaintext Hazırlığı widget'ı — intro ile Round 0 arasına eklenen sayfa
# ---------------------------------------------------------------------------

class _AESPlaintextPrepWidget(QWidget):
    """
    AES Plaintext Hazırlığı sayfası — intro ile Round 0 arasına eklenen tek-seferlik sayfa.

    Fazlar (QTimer _TICK_MS=60):
      0: Plaintext label fade-in
      1: İlk 16 byte UTF-8 grid kademeli
      2: PKCS#7 padding byte'ları beyaz border ile eklenir
      3: Toplam/blok bilgi şeridi
      4: 4×4 state matrix sütun sütun dolar
      5: "Devam ▶" buton enabled

    Boş mesaj: faz 1 atlanır.
    """

    _TICK_MS = 60

    def __init__(
        self,
        plaintext_text: str,
        plaintext_bytes: bytes,
        padded_plaintext: bytes,
        first_block: bytes,
        blocks_total: int,
        state_matrix: list[list[str]],
        on_continue=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from PyQt6.QtWidgets import QScrollArea
        from animation_modals.byte_widgets import (
            _ColoredByteGridWidget,
            _ByteStripWidget,
        )

        self._plaintext_text = plaintext_text
        self._plaintext_bytes = plaintext_bytes
        self._padded_plaintext = padded_plaintext
        self._first_block = first_block
        self._blocks_total = blocks_total
        self._state_matrix = state_matrix
        self._on_continue = on_continue
        self._is_empty = len(plaintext_bytes) == 0
        self._tick = 0
        self._phase = 0
        self._finished = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        title = QLabel("Plaintext Hazırlığı — Metin → 4×4 State Matrix")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        # Plaintext label
        if self._is_empty:
            label_text = "<i>(boş mesaj)</i>"
            label_color = ANIM_COLORS["text_muted"]
        else:
            preview = plaintext_text[:60] + ("…" if len(plaintext_text) > 60 else "")
            label_text = f"Plaintext: \"{preview}\""
            label_color = ANIM_COLORS["text_secondary"]
        self._txt_lbl = QLabel(label_text)
        self._txt_lbl.setFont(QFont("IBM Plex Sans", 10))
        self._txt_lbl.setStyleSheet(f"color: {label_color};")
        self._txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._txt_lbl.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self._txt_lbl)

        # Detail grid (ilk 16 byte = first_block)
        detail_lbl = QLabel("İlk blok (16 byte) — PKCS#7 padding dahil:")
        detail_lbl.setFont(QFont("IBM Plex Sans", 9))
        detail_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(detail_lbl)
        # Padding mask: orijinal plaintext byte'larından sonrası PKCS#7
        n_orig = min(len(plaintext_bytes), 16)
        padding_mask = [False] * n_orig + [True] * (16 - n_orig)
        padding_labels = [""] * n_orig + ["pad"] * (16 - n_orig)
        self._grid = _ColoredByteGridWidget(
            first_block,
            max_cells=16,
            padding_mask=padding_mask,
            padding_labels=padding_labels,
        )
        lay.addWidget(self._grid)

        # Byte strip (tüm padded plaintext) — scroll
        strip_lbl = QLabel(
            f"Tüm byte'lar (toplam {len(padded_plaintext)} byte, "
            f"blok sayısı: {blocks_total}):"
        )
        strip_lbl.setFont(QFont("IBM Plex Sans", 9))
        strip_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(strip_lbl)
        # Padding mask tüm strip için
        n_orig_all = len(plaintext_bytes)
        full_mask = [False] * n_orig_all + [True] * (len(padded_plaintext) - n_orig_all)
        self._strip = _ByteStripWidget(padded_plaintext, padding_mask=full_mask)
        strip_scroll = QScrollArea()
        strip_scroll.setWidget(self._strip)
        strip_scroll.setWidgetResizable(True)
        strip_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        strip_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        strip_scroll.setStyleSheet("background: transparent; border: none;")
        strip_scroll.setMinimumHeight(60)
        lay.addWidget(strip_scroll)

        # 4×4 state matrix gösterimi
        matrix_lbl = QLabel("4×4 State Matrix (column-major):")
        matrix_lbl.setFont(QFont("IBM Plex Sans", 9))
        matrix_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(matrix_lbl)
        self._matrix_widget = self._build_state_matrix_widget()
        lay.addWidget(self._matrix_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Devam butonu
        self._btn_continue = QPushButton("Devam ▶")
        self._btn_continue.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
        self._btn_continue.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; border-radius: 6px; "
            f"padding: 6px 18px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
            f"QPushButton:disabled {{ background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_muted']}; }}"
        )
        self._btn_continue.setEnabled(False)
        self._btn_continue.clicked.connect(self._on_continue_clicked)
        lay.addWidget(self._btn_continue, alignment=Qt.AlignmentFlag.AlignHCenter)

        lay.addStretch()

        # Matrix cell etiketleri (Fazlı dolum için)
        self._matrix_filled = [[False] * 4 for _ in range(4)]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def _build_state_matrix_widget(self) -> QWidget:
        """4 sütun × 4 satır mini tablo döndürür."""
        from PyQt6.QtWidgets import QGridLayout
        w = QFrame()
        w.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {ANIM_COLORS['border']}; "
            f"border-radius: 6px; padding: 4px; }}"
        )
        grid = QGridLayout(w)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        self._cell_lbls: list[list[QLabel]] = []
        for r in range(4):
            row_lbls = []
            for c in range(4):
                cell = QLabel("--")
                cell.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
                cell.setStyleSheet(
                    f"background: {ANIM_COLORS['bg_input']}; "
                    f"color: {ANIM_COLORS['text_muted']}; "
                    f"border: 1px solid {ANIM_COLORS['border']}; "
                    f"border-radius: 3px; padding: 6px 10px; min-width: 28px;"
                )
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(cell, r, c)
                row_lbls.append(cell)
            self._cell_lbls.append(row_lbls)
        return w

    def start(self) -> None:
        self._timer.start(self._TICK_MS)

    def _on_tick(self) -> None:
        self._tick += 1
        if self._is_empty:
            # Boş mesaj: faz 1 atlanır
            if self._tick == 21:
                self._phase = 2
            elif self._tick == 50:
                self._phase = 3
            elif self._tick >= 60:
                self._fill_matrix_immediate()
                self._jump_to_final()
            return

        if self._tick == 21:
            self._phase = 1
        elif self._tick == 56:
            self._phase = 2
        elif self._tick == 81:
            self._phase = 3
        elif self._tick >= 96 and self._tick < 150:
            # Faz 4: sütun sütun dolum
            local = self._tick - 96
            col = local // 14
            if col < 4:
                for r in range(4):
                    if not self._matrix_filled[r][col]:
                        self._cell_lbls[r][col].setText(self._state_matrix[r][col])
                        self._cell_lbls[r][col].setStyleSheet(
                            f"background: {ANIM_COLORS['accent_blue']}; "
                            f"color: #FFFFFF; border: 1px solid {ANIM_COLORS['accent_blue']}; "
                            f"border-radius: 3px; padding: 6px 10px; min-width: 28px;"
                        )
                        self._matrix_filled[r][col] = True
        elif self._tick >= 151:
            self._fill_matrix_immediate()
            self._jump_to_final()

    def _fill_matrix_immediate(self) -> None:
        for r in range(4):
            for c in range(4):
                if not self._matrix_filled[r][c]:
                    self._cell_lbls[r][c].setText(self._state_matrix[r][c])
                    self._matrix_filled[r][c] = True

    def _jump_to_final(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        self._btn_continue.setEnabled(True)

    def _on_continue_clicked(self) -> None:
        if self._on_continue:
            self._on_continue()

    def closeEvent(self, e) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(e)


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


# ---------------------------------------------------------------------------
# AES Round Flow Widget — FIPS 197 tarzı tüm round görünümü
# ---------------------------------------------------------------------------

class _AESRoundFlowWidget(QWidget):
    """
    Tüm 14 AES-256 round'unu video tarzı dikey listede gösterir.

    Her satır tek bir round'un beş aşamasını yan yana sunar:
      [Başlangıç] → [SubBytes] → [ShiftRows] → [MixColumns]  ⊕  [Round Key]

    Round 0 sadece AddRoundKey içerir; round 14'te MixColumns atlanır.
    Her satırda sağdaki 'Round Key' XOR'lanarak bir sonraki satırın
    'Başlangıç' state'i elde edilir.
    """

    # Hücre ve mizanpaj boyutları
    _CELL_W = 56
    _CELL_H = 56
    _ARROW_W = 16
    _XOR_W = 18
    _COL_GAP = 2
    _ROW_H = 70
    _HEADER_H = 28
    _LEFT_LABEL_W = 60
    _BYTE_FONT = QFont("Courier New", 7, QFont.Weight.Bold)

    _COL_TITLES = ["Başlangıç", "SubBytes", "ShiftRows", "MixColumns", "Round Key"]
    _COL_COLORS = [
        ANIM_COLORS["text_secondary"],     # Başlangıç (gri)
        ANIM_COLORS["accent_yellow"],      # SubBytes
        ANIM_COLORS["accent_blue"],        # ShiftRows
        ANIM_COLORS["accent_mauve"],       # MixColumns
        ANIM_COLORS["accent_peach"],       # Round Key
    ]

    def __init__(
        self,
        rounds_data: list[dict],
        round_keys_hex: list[list[list[str]]],
        initial_state_hex: list[list[str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rounds = rounds_data
        self._round_keys = round_keys_hex
        self._initial = initial_state_hex
        # 15 satır: Round 0..14
        rows_count = 15
        total_h = self._HEADER_H + rows_count * self._ROW_H + 16
        # 5 sütun + 3 ok + 1 ⊕
        total_w = (
            self._LEFT_LABEL_W + 12
            + 5 * self._CELL_W
            + 3 * (self._ARROW_W + 2 * self._COL_GAP)
            + (self._XOR_W + 2 * self._COL_GAP)
            + 16
        )
        self.setMinimumSize(total_w, total_h)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Sütun x koordinatları
        x = self._LEFT_LABEL_W + 8
        col_x = []
        # Sütun 0: Başlangıç
        col_x.append(x); x += self._CELL_W + self._COL_GAP
        # → SubBytes
        col_x.append(x + self._ARROW_W + self._COL_GAP)
        x = col_x[1] + self._CELL_W + self._COL_GAP
        # → ShiftRows
        col_x.append(x + self._ARROW_W + self._COL_GAP)
        x = col_x[2] + self._CELL_W + self._COL_GAP
        # → MixColumns
        col_x.append(x + self._ARROW_W + self._COL_GAP)
        x = col_x[3] + self._CELL_W + self._COL_GAP
        # ⊕ Round Key
        col_x.append(x + self._XOR_W + self._COL_GAP)

        # === Header ===
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        for i, (cx, title) in enumerate(zip(col_x, self._COL_TITLES)):
            p.setPen(QColor(self._COL_COLORS[i]))
            p.drawText(QRect(cx, 4, self._CELL_W, self._HEADER_H - 4),
                       Qt.AlignmentFlag.AlignCenter, title)

        # Header altı ayraç çizgi
        p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))
        p.drawLine(8, self._HEADER_H - 1, self.width() - 8, self._HEADER_H - 1)

        # === Satırlar (Round 0..14) ===
        for ri in range(15):
            y = self._HEADER_H + 4 + ri * self._ROW_H
            self._draw_round_row(p, ri, y, col_x)

        p.end()

    def _draw_round_row(
        self, p: QPainter, ri: int, y: int, col_x: list[int],
    ) -> None:
        """Tek bir round'un satırını çizer."""
        # Sol etiket: "Input", "Round 1", ..., "Round 14"
        label = "Input" if ri == 0 else f"Round {ri}"
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(4, y, self._LEFT_LABEL_W, self._CELL_H),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   label + "  ")

        # Bu round'un veri kaynakları
        rd = self._rounds[ri]

        # ── Sütun 0: Başlangıç state ──
        if ri == 0:
            start_state = self._initial
        else:
            # Önceki round'un sonu = bu round'un başı
            start_state = self._rounds[ri - 1]["after_add_round_key"]
        self._draw_matrix(p, col_x[0], y, start_state, self._COL_COLORS[0])

        # ── Round 0: sadece Round Key gösterilir, ortadakiler boş ──
        if ri == 0:
            # Boş orta sütunlar
            for ci in (1, 2, 3):
                self._draw_empty(p, col_x[ci], y, self._COL_COLORS[ci])
            # ⊕ ve RK
            self._draw_xor(p, col_x[4] - self._XOR_W - self._COL_GAP, y)
            self._draw_matrix(p, col_x[4], y,
                              self._round_keys[0], self._COL_COLORS[4])
            # Notu sağa
            self._draw_note(p, col_x[4] + self._CELL_W + 6, y,
                            "→ Round 1\nbaşlangıcı")
            return

        # ── Round 1..13: tüm sütunlar mevcut ──
        # → SubBytes
        self._draw_arrow(p, col_x[1] - self._ARROW_W - self._COL_GAP, y,
                         self._COL_COLORS[1])
        self._draw_matrix(p, col_x[1], y,
                          rd["after_sub_bytes"], self._COL_COLORS[1])
        # → ShiftRows
        self._draw_arrow(p, col_x[2] - self._ARROW_W - self._COL_GAP, y,
                         self._COL_COLORS[2])
        self._draw_matrix(p, col_x[2], y,
                          rd["after_shift_rows"], self._COL_COLORS[2])
        # → MixColumns (round 14'te yok)
        if ri < 14:
            self._draw_arrow(p, col_x[3] - self._ARROW_W - self._COL_GAP, y,
                             self._COL_COLORS[3])
            self._draw_matrix(p, col_x[3], y,
                              rd["after_mix_columns"], self._COL_COLORS[3])
        else:
            # MixColumns atlandı — soluk gri "yok" kutusu
            self._draw_empty(p, col_x[3], y, self._COL_COLORS[3],
                             label="MixColumns\natlandı")

        # ⊕ Round Key
        self._draw_xor(p, col_x[4] - self._XOR_W - self._COL_GAP, y)
        self._draw_matrix(p, col_x[4], y,
                          self._round_keys[ri], self._COL_COLORS[4])

        # Final round için "→ ÇIKTI" etiketi
        if ri == 14:
            p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_green"]))
            p.drawText(QRect(col_x[4] + self._CELL_W + 4, y,
                             80, self._CELL_H),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "→  Şifreli\n     blok")

    def _draw_matrix(
        self, p: QPainter, x: int, y: int,
        matrix: list[list[str]], color: str,
    ) -> None:
        """4×4 hex matrisi (x, y) konumuna çizer."""
        cell = self._CELL_W // 4
        # Çerçeve
        bg = QColor(color)
        bg.setAlpha(45)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor(color), 1))
        p.drawRoundedRect(x, y, self._CELL_W, self._CELL_H, 4, 4)

        # Hex değerler — sütun-yönlü AES gösterimi (matris[row][col])
        p.setFont(self._BYTE_FONT)
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        for r in range(4):
            for c in range(4):
                cx = x + c * cell
                cy = y + r * cell
                p.drawText(QRect(cx, cy, cell, cell),
                           Qt.AlignmentFlag.AlignCenter, matrix[r][c])

    def _draw_empty(
        self, p: QPainter, x: int, y: int, color: str,
        label: str = "",
    ) -> None:
        """Boş yer-tutucu hücre (round 0'ın orta kolonları, vs.)."""
        bg = QColor(ANIM_COLORS["bg_input"])
        p.setBrush(QBrush(bg))
        pen = QPen(QColor(ANIM_COLORS["border"]), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawRoundedRect(x, y, self._CELL_W, self._CELL_H, 4, 4)
        if label:
            p.setFont(QFont("Georgia", 7))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x + 2, y + 2, self._CELL_W - 4, self._CELL_H - 4),
                       Qt.AlignmentFlag.AlignCenter, label)

    def _draw_arrow(self, p: QPainter, x: int, y: int, color: str) -> None:
        """Yatay ok çizer."""
        mid_y = y + self._CELL_H // 2
        pen = QPen(QColor(color), 2)
        p.setPen(pen)
        p.drawLine(x + 2, mid_y, x + self._ARROW_W - 4, mid_y)
        pts = QPolygon([
            QPoint(x + self._ARROW_W - 1, mid_y),
            QPoint(x + self._ARROW_W - 7, mid_y - 4),
            QPoint(x + self._ARROW_W - 7, mid_y + 4),
        ])
        p.setBrush(QBrush(QColor(color)))
        p.drawPolygon(pts)

    def _draw_xor(self, p: QPainter, x: int, y: int) -> None:
        """⊕ sembolü."""
        mid_y = y + self._CELL_H // 2
        cx = x + self._XOR_W // 2
        # Çember
        r = 7
        p.setBrush(QBrush(QColor(ANIM_COLORS["accent_peach"] + "33")))
        p.setPen(QPen(QColor(ANIM_COLORS["accent_peach"]), 1))
        p.drawEllipse(QPoint(cx, mid_y), r, r)
        # Artı işareti
        p.setPen(QPen(QColor(ANIM_COLORS["accent_peach"]), 1))
        p.drawLine(cx - r + 2, mid_y, cx + r - 2, mid_y)
        p.drawLine(cx, mid_y - r + 2, cx, mid_y + r - 2)

    def _draw_note(self, p: QPainter, x: int, y: int, text: str) -> None:
        """Sağ tarafta kısa açıklama notu."""
        p.setFont(QFont("Georgia", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(x, y, 80, self._CELL_H),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   text)


# ---------------------------------------------------------------------------
# AES Animasyon Penceresi
# ---------------------------------------------------------------------------

class AESAnimationWindow(CryptoAnimationWindow):
    """
    AES-256-GCM animasyon penceresi.

    Parametreler:
      key             : 32 byte session key
      plaintext       : şifrelenecek veri (ilk 16 byte kullanılır)
      expected_ct_hex : crypto_core AES-GCM çıktısının (ciphertext ‖ 16 byte
                        kimlik doğrulama etiketi) ilk 32 byte'ına ait hex
                        önizlemedir. Kısa mesajlarda bu önizleme tag
                        baytlarını da içerebilir; uzun mesajlarda ise
                        yalnızca ciphertext'in başlangıcı görünür.
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
        # Round flow widget için ek veri
        self._rounds_data = aes_result["rounds_data"]
        self._round_keys_hex = aes_result["round_keys_hex"]
        self._initial_state_hex = aes_result["initial_state_hex"]

        # Plaintext Hazırlığı sayfası için yeni alanlar (aes_pure'dan gelir)
        self._plaintext_text_str = aes_result.get("plaintext_text", "")
        self._plaintext_bytes_data = aes_result.get("plaintext_bytes", b"")
        self._padded_plaintext_data = aes_result.get("padded_plaintext", b"")
        self._first_block_data = aes_result.get("first_block", b"")
        self._blocks_total_data = aes_result.get("blocks_total", 1)
        self._state_matrix_data = aes_result.get(
            "state_matrix", [["--"] * 4 for _ in range(4)]
        )

        # round → ilk step indeksini hesapla
        self._round_start: dict[int, int] = {}
        for i, s in enumerate(self._steps_data):
            r = s["round"]
            if r not in self._round_start:
                self._round_start[r] = i

        # Başlangıçta intro görünür; manual_mode round görünümü için
        super().__init__(
            "AES-256-GCM Şifreleme Animasyonu",
            len(self._steps_data),
            manual_mode=True,
            on_close=on_close,
        )

        # Intro ekranı kompakt — sadece akış şeması + Başlat butonu sığar.
        # Intro complete → _switch_to_plaintext_prep ekranı büyütür ve plaintext sayfasını gösterir.
        if on_close is None:
            self.resize(820, 620)

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Giriş animasyonu
        self._intro = _AESIntroWidget(on_complete=self._switch_to_plaintext_prep)
        self._stack.addWidget(self._intro)

        # Sayfa 1 — Plaintext Hazırlığı (yeni, tek seferlik pre-step)
        self._plaintext_page = self._make_plaintext_prep_page()
        self._stack.addWidget(self._plaintext_page)

        # Sayfa 2 — Round görünümü (tek round detayı)
        self._round_page = self._make_round_page()
        self._stack.addWidget(self._round_page)

        # Sayfa 3 — Tüm Roundlar Akışı (FIPS 197 tarzı)
        self._flow_page = self._make_flow_page()
        self._stack.addWidget(self._flow_page)

        # Sayfa 4 — Eşleşme sonucu
        self._match_page = self._make_match_page()
        self._stack.addWidget(self._match_page)

        # Intro başlat (otomatik)
        self._intro.start()

    def _make_plaintext_prep_page(self) -> QWidget:
        """Yeni Plaintext Hazırlığı sayfası — _AESPlaintextPrepWidget içerir."""
        from PyQt6.QtWidgets import QScrollArea
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        self._plaintext_widget = _AESPlaintextPrepWidget(
            plaintext_text=self._plaintext_text_str,
            plaintext_bytes=self._plaintext_bytes_data,
            padded_plaintext=self._padded_plaintext_data,
            first_block=self._first_block_data,
            blocks_total=self._blocks_total_data,
            state_matrix=self._state_matrix_data,
            on_continue=self._switch_to_rounds_only,
        )
        scroll = QScrollArea()
        scroll.setWidget(self._plaintext_widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

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

        # Tüm Roundlar Akışı butonu (FIPS 197 tarzı görünüm)
        rb_lay.addStretch()
        flow_btn = QPushButton("Tüm Akış")
        flow_btn.setFixedHeight(28)
        flow_btn.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        flow_btn.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; border-radius: 5px; "
            f"padding: 4px 12px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        flow_btn.clicked.connect(self._switch_to_flow_view)
        rb_lay.addWidget(flow_btn)
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
            f"border: 2px solid {ANIM_COLORS['accent_blue']}; border-radius: 8px; }}"
        )
        mat_lay = QVBoxLayout(mat_frame)
        mat_lay.setContentsMargins(8, 6, 8, 6)
        mat_lay.setSpacing(4)

        # Yan yana iki QPainter matris + Yeniden Oynat butonu.
        # Operasyon adı zaten _op_title (üstte) ve _arrow_label
        # (matrislerin arasında "→ OperationName →") tarafından
        # gösterildiği için ayrı bir matrix_context etiketi yok.
        self._matrix_pair = _AESStateCompareWidget(parent=self)
        mat_lay.addWidget(self._matrix_pair)

        content_row.addWidget(mat_frame)

        # Sağ panel — operasyona göre değişir. Min 280 (eski 320) ve
        # max 430: dar alice viewport'larında round sayfası yatay scroll'a
        # düşmesin; geniş viewport'larda gerektiği kadar yer alır.
        self._side_stack = QStackedWidget()
        self._side_stack.setMinimumWidth(280)
        self._side_stack.setMaximumWidth(430)

        empty = QWidget()  # boş panel (yedek)
        self._side_stack.addWidget(empty)                    # index 0

        # ShiftRows: scroll area içinde (4 satır × 92px = ~400px gerektirir)
        from PyQt6.QtWidgets import QScrollArea
        self._shift_widget = _ShiftRowsAnimWidget()
        shift_scroll = QScrollArea()
        shift_scroll.setWidget(self._shift_widget)
        shift_scroll.setWidgetResizable(True)
        shift_scroll.setStyleSheet("background: transparent; border: none;")
        self._side_stack.addWidget(shift_scroll)             # index 1

        self._mix_widget = _MixColumnsAnimWidget()           # MixColumns için
        self._side_stack.addWidget(self._mix_widget)         # index 2

        # SubBytes: byte → S-Box[byte] görselleştirmesi
        self._sub_widget = _SubBytesAnimWidget()
        sub_scroll = QScrollArea()
        sub_scroll.setWidget(self._sub_widget)
        sub_scroll.setWidgetResizable(True)
        sub_scroll.setStyleSheet("background: transparent; border: none;")
        self._side_stack.addWidget(sub_scroll)               # index 3

        # AddRoundKey: state ⊕ round_key = yeni state
        self._ark_widget = _AddRoundKeyAnimWidget()
        ark_scroll = QScrollArea()
        ark_scroll.setWidget(self._ark_widget)
        ark_scroll.setWidgetResizable(True)
        ark_scroll.setStyleSheet("background: transparent; border: none;")
        self._side_stack.addWidget(ark_scroll)               # index 4

        content_row.addWidget(self._side_stack)
        lay.addLayout(content_row, stretch=1)   # stretch=1: content_row fills remaining height
        return w

    def _make_flow_page(self) -> QWidget:
        """FIPS 197 tarzı tüm round akışı sayfası — scroll'lu liste."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        # Üst bar — geri dönüş + başlık
        top_row = QHBoxLayout()
        back_btn = QPushButton("◀  Tek Round Detayı")
        back_btn.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        back_btn.setFixedHeight(30)
        back_btn.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_secondary']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 5px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; }}"
        )
        back_btn.clicked.connect(self._back_to_round_view)
        top_row.addWidget(back_btn)

        title = QLabel("Tüm 14 Round Akışı  (FIPS 197 referans biçimi)")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(title, stretch=1)
        top_row.addStretch()
        lay.addLayout(top_row)

        # Açıklayıcı alt başlık
        legend = QLabel(
            "Her satır bir round'u gösterir. Soldan sağa: Başlangıç → SubBytes → "
            "ShiftRows → MixColumns ⊕ Round Key.   "
            "Round 0 sadece AddRoundKey içerir; Round 14'te MixColumns atlanır."
        )
        legend.setFont(QFont("IBM Plex Sans", 9))
        legend.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        legend.setWordWrap(True)
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(legend)

        # Scroll area içine yeni round flow widget'ı
        from PyQt6.QtWidgets import QScrollArea
        flow = _AESRoundFlowWidget(
            rounds_data=self._rounds_data,
            round_keys_hex=self._round_keys_hex,
            initial_state_hex=self._initial_state_hex,
        )
        scroll = QScrollArea()
        scroll.setWidget(flow)
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        lay.addWidget(scroll, stretch=1)
        return w

    def _switch_to_flow_view(self) -> None:
        """Round detay görünümünden Tüm Roundlar Akışı'na geçer."""
        self._stack.setCurrentWidget(self._flow_page)

    def _back_to_round_view(self) -> None:
        """Akış görünümünden tek-round detayına döner."""
        self._stack.setCurrentWidget(self._round_page)

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

    def _switch_to_plaintext_prep(self) -> None:
        """Intro complete: pencereyi büyüt + plaintext prep sayfasına geç + animasyon başlat."""
        # Pencere büyütülür çünkü plaintext prep page'in 16-cell grid'i
        # intro 820×620 boyutuna sığmaz.
        if self._on_close is None:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                g = screen.availableGeometry()
                self.resize(int(g.width() * 0.82), int(g.height() * 0.85))
                # Pencereyi tekrar ekranın merkezine kaydır
                self.move(
                    (g.width() - self.width()) // 2,
                    (g.height() - self.height()) // 2,
                )
        self._stack.setCurrentWidget(self._plaintext_page)
        self._plaintext_widget.start()

    def _switch_to_rounds_only(self) -> None:
        """Plaintext prep tamamlanınca: rounds sayfasına geç (pencere büyütme YOK, zaten büyük)."""
        self._stack.setCurrentWidget(self._round_page)
        self._render_step(0)
        self._progress.setValue(1)

    # Geriye dönük uyumluluk için: eski isim _switch_to_rounds_only çağırır.
    def _switch_to_rounds(self) -> None:
        """Eski isim — _switch_to_rounds_only çağırır."""
        self._switch_to_rounds_only()

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

        # Sağ panel — operasyona göre değişir (eskisi gibi)
        rnd = step["round"]
        rk: list[list[str]] | None = None
        if op == "SubBytes":
            self._side_stack.setCurrentIndex(3)
            self._sub_widget.set_data(before, after)
        elif op == "ShiftRows":
            self._side_stack.setCurrentIndex(1)
            self._shift_widget.set_data(before, after)
        elif op == "MixColumns":
            self._side_stack.setCurrentIndex(2)
            self._mix_widget.set_data(before, after)
        else:  # AddRoundKey
            self._side_stack.setCurrentIndex(4)
            if rnd < len(self._round_keys_hex):
                rk = self._round_keys_hex[rnd]
                self._ark_widget.set_data(before, after, rk, rnd)

        # State matrisi: yan yana iki matris + animasyon (tek satıra indi)
        self._matrix_pair.start_step(
            op, before, after, step["color"], round_key=rk,
        )

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._match_page)
        self._update_round_bar(14)
        last = self._steps_data[-1]
        mat = last["matrix"]   # 4×4 liste
        self._matrix_pair.show_final(mat)

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
            f"crypto_core AES-GCM çıktısı — ct(‖tag) ilk 32 byte kesiti:  {self._expected_ct_hex}",
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
            "  Animasyon: plaintext'in 14 round AES-ECB çıktısı (tek blok, tag yok)",
            "  GCM modu:  CTR sayacı şifrelenir → plaintext ⊕ keystream → ciphertext",
            "             ardından GHASH ile 16 byte kimlik doğrulama etiketi (tag)",
            "             ciphertext'in sonuna eklenir.",
            "             Aynı anahtar, farklı IV ve counter → farklı çıktı",
            "",
            "  Not: Yukarıdaki \"GCM çıktısı\" tam şifreli metin değil, yalnızca",
            "  ciphertext‖tag değerinin ilk 32 byte'ının hex ÖNİZLEMESİDİR.",
            "  Kısa mesajlarda bu önizleme tag baytlarını da içerir.",
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
