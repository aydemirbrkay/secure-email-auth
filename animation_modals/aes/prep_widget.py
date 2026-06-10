# animation_modals/aes/prep_widget.py
"""AES plaintext hazırlığı sayfası (metin -> 4x4 state matrix)."""
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

        self._pp_title = QLabel("Plaintext Hazırlığı — Metin → 4×4 State Matrix")
        self._pp_title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        self._pp_title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        self._pp_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._pp_title)

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
        self._detail_lbl = QLabel("İlk blok (16 byte) — PKCS#7 padding dahil:")
        self._detail_lbl.setFont(QFont("IBM Plex Sans", 9))
        self._detail_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(self._detail_lbl)
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
        # Grid'i yatay QScrollArea'ya sar: 16 hücre dar pencerede sığmayıp
        # son hücre(ler) kesiliyordu (Görsel 4). Bu instance'a TAM boyut
        # min-width verilir (hücreler okunur kalsın); scroll alanı bunu kendi
        # içinde yatay kaydırır — min-width AES stack'ine SIZMAZ (scroll alanı
        # kendi küçük min-width'ini bildirir). byte strip ile aynı desen.
        self._grid.setMinimumWidth(80 + 6 + 16 * (66 + 3))  # tam 16 hücre
        grid_scroll = QScrollArea()
        grid_scroll.setWidget(self._grid)
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        grid_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        grid_scroll.setStyleSheet("background: transparent; border: none;")
        # 4 satır (char/ASCII/hex/binary) + padding etiket satırı sığsın.
        grid_scroll.setMinimumHeight(self._grid.minimumHeight() + 18)
        lay.addWidget(grid_scroll)

        # Byte strip (tüm padded plaintext) — scroll
        self._strip_lbl = QLabel(
            f"Tüm byte'lar (toplam {len(padded_plaintext)} byte, "
            f"blok sayısı: {blocks_total}):"
        )
        self._strip_lbl.setFont(QFont("IBM Plex Sans", 9))
        self._strip_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(self._strip_lbl)
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
        self._matrix_lbl = QLabel("4×4 State Matrix (column-major):")
        self._matrix_lbl.setFont(QFont("IBM Plex Sans", 9))
        self._matrix_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(self._matrix_lbl)
        self._matrix_widget = self._build_state_matrix_widget()
        lay.addWidget(self._matrix_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Devam butonu
        self._btn_continue = QPushButton("Devam ▶")
        self._btn_continue.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
        self._btn_continue.setStyleSheet(self._continue_btn_style())
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
                cell.setStyleSheet(self._cell_style(False))
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(cell, r, c)
                row_lbls.append(cell)
            self._cell_lbls.append(row_lbls)
        return w

    @staticmethod
    def _cell_style(filled: bool) -> str:
        if filled:
            return (
                f"background: {ANIM_COLORS['accent_blue']}; "
                f"color: #FFFFFF; border: 1px solid {ANIM_COLORS['accent_blue']}; "
                f"border-radius: 3px; padding: 6px 10px; min-width: 28px;"
            )
        return (
            f"background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_muted']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 3px; padding: 6px 10px; min-width: 28px;"
        )

    @staticmethod
    def _continue_btn_style() -> str:
        return (
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; border-radius: 6px; "
            f"padding: 6px 18px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
            f"QPushButton:disabled {{ background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_muted']}; }}"
        )

    def restyle(self) -> None:
        """Tema değişiminde QLabel/QFrame içeriğini durum bozmadan yeniden boyar.
        Byte ızgaraları (_ColoredByteGridWidget/_ByteStripWidget) QPainter'dır →
        update() ile yenilenir."""
        self._pp_title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        label_color = (
            ANIM_COLORS["text_muted"] if self._is_empty
            else ANIM_COLORS["text_secondary"]
        )
        self._txt_lbl.setStyleSheet(f"color: {label_color};")
        for lbl in (self._detail_lbl, self._strip_lbl, self._matrix_lbl):
            lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._matrix_widget.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {ANIM_COLORS['border']}; "
            f"border-radius: 6px; padding: 4px; }}"
        )
        for r in range(4):
            for c in range(4):
                self._cell_lbls[r][c].setStyleSheet(
                    self._cell_style(self._matrix_filled[r][c])
                )
        self._btn_continue.setStyleSheet(self._continue_btn_style())

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
                        self._cell_lbls[r][col].setStyleSheet(self._cell_style(True))
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

