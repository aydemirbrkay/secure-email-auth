"""SHA-256 bit düzeyi drill-down'ları için paylaşılan çizim yardımcıları.

Hem round (Σ1/Ch/Σ0/Maj) hem de mesaj genişletme (σ0/σ1) sihirbazları aynı
"32 bitlik hizalı satır" dilini kullanır: etiket + hex + nibble gruplu 32 bit
hücresi. Satırlar AYNI sütun konumlarında çizildiği için kullanıcı XOR/AND/ROTR
sonucunu dikey olarak doğrulayabilir (eğitsel kazanç buradadır).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen

from ..base import ANIM_COLORS, cached_font


def bits(hexstr: str) -> str:
    """8-hane hex → 32 karakterlik ikili dize."""
    return format(int(hexstr, 16), "032b")


def bit_grid_metrics(width: int, bits_x0: int = 220) -> tuple[int, int, int]:
    """Pencere genişliğine göre (bits_x0, cell_w, nibble_gap) döndürür.

    Bit hücreleri her boyutta hizalı kalsın diye tek noktadan hesaplanır."""
    region = width - bits_x0 - 14
    cell_w = max(9, min(20, region // 36))
    nibble_gap = max(3, cell_w // 2)
    return bits_x0, cell_w, nibble_gap


def draw_bit_row(
    p: QPainter, *,
    y: int, label: str, hexstr: str, color_hex: str,
    bits_x0: int, cell_w: int, nibble_gap: int,
    emphasize: bool = False,
) -> int:
    """Etiket + hex + 32 hizalı bit hücresi çizer; satır yüksekliğini döndürür.

    1-bitler renkli (emphasize ise daha parlak), 0-bitler soluk; nibble (4 bit)
    grupları arasına küçük boşluk konur. Dönen yükseklik çağıranın bir sonraki
    satırı yerleştirmesi içindir."""
    color = QColor(color_hex)
    h = cell_w + 6
    p.setFont(cached_font("Courier New", 9, QFont.Weight.Bold))
    p.setPen(color if emphasize else QColor(ANIM_COLORS["text_secondary"]))
    p.drawText(QRect(8, y, 130, h),
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)
    p.setPen(QColor(ANIM_COLORS["text_primary"]))
    p.drawText(QRect(140, y, 74, h),
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, hexstr)
    x = bits_x0
    p.setFont(cached_font("Courier New", max(7, cell_w - 3), QFont.Weight.Bold))
    for i, ch in enumerate(bits(hexstr)):
        on = ch == "1"
        bg = QColor(color)
        bg.setAlphaF(0.85 if (on and emphasize) else (0.30 if on else 0.05))
        p.setBrush(QBrush(bg))
        p.setPen(QPen(color if on else QColor(ANIM_COLORS["border"]), 1))
        p.drawRoundedRect(x, y, cell_w, cell_w, 2, 2)
        p.setPen(QColor(ANIM_COLORS["text_primary"] if on
                        else ANIM_COLORS["text_muted"]))
        p.drawText(QRect(x, y, cell_w, cell_w), Qt.AlignmentFlag.AlignCenter, ch)
        x += cell_w
        if (i + 1) % 4 == 0 and i != 31:
            x += nibble_gap
    return h
