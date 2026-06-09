# animation_modals/aes/round_flow.py
"""AES tüm round'ları FIPS 197 tarzı dikey listede gösteren widget."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS
from .constants import AES_FINAL_ROUND_INDEX

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
        if ri == AES_FINAL_ROUND_INDEX:
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

