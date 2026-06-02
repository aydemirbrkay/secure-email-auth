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
        cell_w: int = 66,
        cell_h: int = 36,
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
        # Binary satırı için sabit 9pt — cell_w default 66 px'te
        # "00000000" rahat sığar (~56 px metin + 10 px padding).
        self._binary_font_pt: int = 9
        # UTF-8 byte→karakter eşlemesi (önbellek) — her set_data'da yenilenir.
        self._char_map: list[str] = self._compute_char_map()
        self.setMinimumHeight(len(show_rows) * (cell_h + 4) + 30)
        # Sabit boyut — kutu BOYUTU değil, kutu SAYISI mesajla birlikte
        # değişir. Mesaj uzunluğu × (cell_w + gap) + etiket alanı kadar
        # genişlik gerekir; parent QScrollArea bunu yatay olarak kaydırır.
        n_data = max(1, min(len(data), max_cells))
        self.setMinimumWidth(80 + 6 + n_data * (cell_w + 3))

    def _compute_char_map(self) -> list[str]:
        """Her byte için 'Karakter' satırında gösterilecek karakter.
        UTF-8 çok-byte karakterler (Türkçe ş/ğ/ü/ö/ç/ı, emoji, vs.) için
        karakterin TÜM byte hücrelerinde aynı karakter gösterilir.

        Padding-aware: SHA padding byte'ları (0x80 ayraç, 0x00 dolgu, length)
        UTF-8'de geçerli değil → tüm veriyi tek seferde decode etmeye
        çalışırsak UnicodeDecodeError atar ve fallback ASCII'ye düşeriz;
        bu durumda Türkçe karakter byte'ları (0xC3, 0xBC...) printable
        range dışı olduğu için '·' basılır. ÇÖZÜM: padding_mask'i kullanarak
        mesaj/padding sınırını bul, decode'u SADECE mesaj kısmına uygula,
        padding byte'ları için sade '·' kullan.
        """
        if not self._data:
            return []

        # Padding mask varsa mesaj/padding sınırını tespit et.
        if self._padding_mask:
            try:
                first_pad = self._padding_mask.index(True)
            except ValueError:
                first_pad = len(self._data)  # mask var ama padding yok
            msg_bytes = bytes(self._data[:first_pad])
        else:
            # Mask yok → tüm veri mesaj sayılır (örn. Mesaj Hazırlığı sayfası).
            msg_bytes = bytes(self._data)

        n_padding = len(self._data) - len(msg_bytes)

        # Mesaj kısmını UTF-8 decode et — padding byte'ları (0x80 vb.) decode'u
        # kırmasın diye onları ayrı tutuyoruz.
        try:
            text = msg_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            # Bozuk mesaj — byte başına ASCII fallback (eski davranış).
            msg_chars: list[str] = [
                chr(b) if 32 <= b < 127 else "·"
                for b in msg_bytes
            ]
        else:
            # UTF-8 başarılı: her karakter kendi byte sayısı kadar replikle
            # (ü = 2 byte → iki hücrede 'ü'; emoji = 4 byte → dört hücre).
            msg_chars = []
            for ch in text:
                cp = ord(ch)
                display = ch if cp >= 32 and cp != 127 else "·"
                byte_count = len(ch.encode("utf-8"))
                msg_chars.extend([display] * byte_count)

        # Padding byte'ları için sade '·' (anlamlı karakter taşımaz).
        return msg_chars + ["·"] * n_padding

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
        self._char_map = self._compute_char_map()
        # Veri değiştiğinde min width'i de güncelle — yeni n'e göre.
        n_data = max(1, min(len(data), self._max_cells))
        self.setMinimumWidth(80 + 6 + n_data * (self._cell_w + 3))
        self.update()

    def resizeEvent(self, e) -> None:
        # Kutu BOYUTU sabit (cell_w/cell_h __init__'ten gelir, değişmez).
        # Kutu SAYISI mesaj uzunluğuyla birlikte değişir; widget toplam
        # genişliği setMinimumWidth ile veriye göre ayarlandı. Parent
        # QScrollArea bu fazla genişliği yatay olarak kaydırır.
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
        cell_gap = 3   # hücreler arası yatay boşluk (eski 2 → 3, görsel ayrım)

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
                x = row_label_w + 6 + i * (cw + cell_gap)
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
                    # UTF-8 farkındalığı: Türkçe karakter (ü/ş/ğ vs.) ve emoji
                    # gibi çok-byte karakterler her bir byte hücresinde aynı
                    # karakteri gösterir; ASCII tek byte ise kendi karakteri.
                    p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
                    ch_str = (
                        self._char_map[i]
                        if i < len(self._char_map)
                        else (chr(byte_val) if 32 <= byte_val < 127 else "·")
                    )
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
                    # Dinamik punto — resizeEvent'te cell_w'ye göre 9→6pt
                    # arasında seçildi. Monospace hint hücreler arası
                    # yatay tutarlılık sağlar.
                    bin_font = QFont("Courier New", self._binary_font_pt)
                    bin_font.setStyleHint(QFont.StyleHint.Monospace)
                    p.setFont(bin_font)
                    p.drawText(x, y, cw, ch,
                               Qt.AlignmentFlag.AlignCenter, f"{byte_val:08b}")

        # En altta padding etiketleri (varsa)
        if self._padding_labels:
            label_y = 4 + len(self._show_rows) * (ch + gap) + 2
            p.setFont(QFont("IBM Plex Sans", 7, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            for i in range(n):
                if i < len(self._padding_labels) and self._padding_labels[i]:
                    x = row_label_w + 6 + i * (cw + cell_gap)
                    p.drawText(x, label_y, cw, 12,
                               Qt.AlignmentFlag.AlignCenter,
                               f"[{self._padding_labels[i]}]")


class _ByteStripWidget(QWidget):
    """
    Tüm byte'ları tek satırda renkli kareler olarak gösterir — her karenin
    içinde 2-haneli hex değeri yazılı (kullanıcı her byte'ın değerini de
    görsün diye). Padding byte'ları beyaz 1px border + alpha 0.7 ile
    ayırt edilir. 32+ byte için yatay scroll (parent QScrollArea içinde
    kullanılır).
    """

    def __init__(
        self,
        data: bytes,
        *,
        cell_w: int = 22,
        cell_h: int = 22,
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
                   f"Toplam: {len(self._data)} byte  —  her kare 1 byte'ın hex değerini gösterir")

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

            # Hücre içinde hex değeri (kompakt görünüm için 7pt Courier)
            # 22×22 px hücrede "00".."ff" 14 px civarı yer kaplar.
            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            p.drawText(x, y, cw, ch,
                       Qt.AlignmentFlag.AlignCenter, f"{byte_val:02x}")
