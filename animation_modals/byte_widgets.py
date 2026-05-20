# animation_modals/byte_widgets.py
"""
Paylaşılan byte görselleştirme widget'ları.
SHA Mesaj Hazırlığı, SHA Padding ve AES Plaintext Hazırlığı sayfalarında kullanılır.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from animation_modals.base import ANIM_COLORS


# Döngüsel 6 renkli palet — ANIM_COLORS'a eklenmez, byte_widgets'a özgüdür.
_PALETTE_6 = [
    ANIM_COLORS["accent_blue"],
    ANIM_COLORS["accent_green"],
    ANIM_COLORS["accent_yellow"],
    ANIM_COLORS["accent_mauve"],
    ANIM_COLORS["accent_peach"],
    "#C26F6F",  # yerel 6. renk — ANIM_COLORS'a eklenmez
]


class _ColoredByteGridWidget(QWidget):
    """
    Byte dizisinin ilk N byte'ını "karakter / ASCII onlık / hex / binary" satırlarında
    döngüsel 6 renk paletiyle gösterir. Padding byte'ları beyaz 2px border + alpha 0.7 +
    küçük etiket ile ayırt edilir.
    """

    def __init__(
        self,
        data: bytes,
        *,
        max_cells: int = 16,
        show_rows: tuple[str, ...] = ("char", "dec", "hex", "bin"),
        cell_w: int = 56,
        cell_h: int = 22,
        padding_mask: list[bool] | None = None,
        padding_labels: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data = data
        self._max_cells = max_cells
        self._show_rows = show_rows
        self._cell_w = cell_w
        self._cell_h = cell_h
        self._padding_mask = padding_mask or []
        self._padding_labels = padding_labels or []
        self._highlighted_idx: int | None = None
        self.setMinimumHeight(len(show_rows) * (cell_h + 4) + 30)

    def set_highlighted_index(self, idx: int | None) -> None:
        self._highlighted_idx = idx
        self.update()

    def set_data(
        self,
        data: bytes,
        padding_mask: list[bool] | None = None,
        padding_labels: list[str] | None = None,
    ) -> None:
        self._data = data
        self._padding_mask = padding_mask or []
        self._padding_labels = padding_labels or []
        self.update()

    def resizeEvent(self, e) -> None:
        # Adaptive cell width — dar ekranlarda hücreler küçülür
        avail = self.width() - 40
        if self._max_cells > 0:
            self._cell_w = max(36, min(56, avail // self._max_cells))
        self.update()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        n = min(len(self._data), self._max_cells)
        if n == 0:
            # Boş mesaj: "0 byte" etiketi
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.setFont(QFont("IBM Plex Sans", 10))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "(0 byte)")
            return

        row_labels = {
            "char": "Karakter",
            "dec": "ASCII",
            "hex": "Hex",
            "bin": "Binary",
        }
        row_label_w = 80
        cw, ch = self._cell_w, self._cell_h
        gap = 3

        for ri, row_key in enumerate(self._show_rows):
            y = 4 + ri * (ch + gap)
            # Sol etiket
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.setFont(QFont("IBM Plex Sans", 8))
            p.drawText(0, y, row_label_w, ch,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                       row_labels.get(row_key, row_key))

            # Hücreler
            for i in range(n):
                byte_val = self._data[i]
                x = row_label_w + 6 + i * (cw + 2)
                color_hex = _PALETTE_6[i % 6]
                qc = QColor(color_hex)
                is_padding = i < len(self._padding_mask) and self._padding_mask[i]
                if is_padding:
                    qc.setAlpha(178)  # 0.7 alpha
                p.fillRect(x, y, cw, ch, qc)

                # Border
                if is_padding:
                    p.setPen(QPen(QColor("#FFFFFF"), 2))
                elif self._highlighted_idx == i:
                    p.setPen(QPen(QColor("#FFFFFF"), 2))
                else:
                    p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))
                p.drawRect(x, y, cw, ch)

                # Hücre içeriği
                p.setPen(QColor("#FFFFFF"))
                if row_key == "char":
                    p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
                    ch_str = chr(byte_val) if 32 <= byte_val < 127 else "·"
                    p.drawText(x, y, cw, ch,
                               Qt.AlignmentFlag.AlignCenter, ch_str)
                elif row_key == "dec":
                    p.setFont(QFont("Courier New", 9))
                    p.drawText(x, y, cw, ch,
                               Qt.AlignmentFlag.AlignCenter, str(byte_val))
                elif row_key == "hex":
                    p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
                    p.drawText(x, y, cw, ch,
                               Qt.AlignmentFlag.AlignCenter, f"{byte_val:02x}")
                elif row_key == "bin":
                    p.setFont(QFont("Courier New", 7))
                    p.drawText(x, y, cw, ch,
                               Qt.AlignmentFlag.AlignCenter, f"{byte_val:08b}")

        # En altta padding etiketleri (varsa)
        if self._padding_labels:
            label_y = 4 + len(self._show_rows) * (ch + gap) + 2
            p.setFont(QFont("IBM Plex Sans", 7, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            for i in range(n):
                if i < len(self._padding_labels) and self._padding_labels[i]:
                    x = row_label_w + 6 + i * (cw + 2)
                    p.drawText(x, label_y, cw, 12,
                               Qt.AlignmentFlag.AlignCenter,
                               f"[{self._padding_labels[i]}]")


class _ByteStripWidget(QWidget):
    """
    Tüm byte'ları tek satırda küçük (14×14 px) renkli kareler olarak gösterir.
    Padding byte'ları beyaz 1px border + alpha 0.7 ile ayırt edilir.
    32+ byte için yatay scroll (parent QScrollArea içinde kullanılır).
    """

    def __init__(
        self,
        data: bytes,
        *,
        cell_w: int = 14,
        cell_h: int = 14,
        show_label: str = "hex",
        padding_mask: list[bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data = data
        self._cell_w = cell_w
        self._cell_h = cell_h
        self._show_label = show_label
        self._padding_mask = padding_mask or []
        n = max(1, len(data))
        # Minimum width: tüm byte'lar yan yana sığsın diye sabit
        self.setMinimumWidth(n * (cell_w + 1) + 4)
        self.setMinimumHeight(cell_h + 24)  # +üst etiket + alt boşluk

    def set_data(
        self,
        data: bytes,
        padding_mask: list[bool] | None = None,
    ) -> None:
        self._data = data
        self._padding_mask = padding_mask or []
        n = max(1, len(data))
        self.setMinimumWidth(n * (self._cell_w + 1) + 4)
        self.update()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Üst etiket
        p.setFont(QFont("IBM Plex Sans", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(0, 0, self.width(), 16,
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"Toplam: {len(self._data)} byte")

        n = len(self._data)
        if n == 0:
            return

        cw, ch = self._cell_w, self._cell_h
        y = 18
        for i in range(n):
            byte_val = self._data[i]
            x = 2 + i * (cw + 1)
            color_hex = _PALETTE_6[i % 6]
            qc = QColor(color_hex)
            is_padding = i < len(self._padding_mask) and self._padding_mask[i]
            if is_padding:
                qc.setAlpha(178)
            p.fillRect(x, y, cw, ch, qc)

            if is_padding:
                p.setPen(QPen(QColor("#FFFFFF"), 1))
            else:
                p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))
            p.drawRect(x, y, cw, ch)
