"""
widget_utils.py – Qt'ye Bağımlı Arayüz Yardımcıları
====================================================

Bu modül, eskiden ``kriptografi/utils.py`` içinde bulunan ve PyQt6'ya
bağımlı olan tüm GUI yardımcılarını barındırır. Böylece ``kriptografi/``
paketi Qt yüklü olmayan saf Python ortamında da içe aktarılabilir.

İçerik:
  - ``svg_pixmap`` / ``png_icon_pixmap``: ikon/pixmap üretimi.
  - ``make_step_box`` / ``style_step_box``: adım kutusu kurma ve temalandırma.
  - ``build_step_content`` / ``truncate_hex``: adım sonuçlarını okunaklı
    Türkçe metne çevirme.
"""
from __future__ import annotations

import logging
import os

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from kriptografi.crypto_core import StepResult
from kriptografi.utils import FRIENDLY_NAMES
from arayuz.theme import COLORS, step_box_style

logger = logging.getLogger(__name__)

# Görseller (SVG ikonlar + PNG akış diyagramları) — tek klasörde toplu erişim.
# Eski 'icons/' klasörü 'görseller/' olarak yeniden adlandırıldı; alice/bob
# akış PNG'leri de buraya taşındı. Bu dosya 'arayuz/' alt-paketinde olduğu
# için path bir üst dizine (proje köküne) çıkar.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GORSELLER_DIR = os.path.join(_PROJECT_ROOT, "görseller")


def svg_pixmap(filename: str, color: str, size: int = 20) -> QPixmap:
    """SVG simge dosyasını verilen renk ve boyutta QPixmap'e dönüştürür.
    SVG içindeki 'currentColor' değeri çalışma zamanında verilen renge çevrilir.
    """
    path = os.path.join(_GORSELLER_DIR, filename)
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read().replace("currentColor", color)
        renderer = QSvgRenderer(QByteArray(data.encode()))
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
    except Exception as exc:
        logger.warning("Simge yüklenemedi: %s — %s", filename, exc)
    return pix


def png_icon_pixmap(filename: str, color: str, size: int, thickness: float = 1.0) -> QPixmap:
    """PNG dosyasını yükler; beyaz/açık pikselleri şeffafa, koyu pikselleri
    verilen renge dönüştürerek QPixmap döndürür.
    thickness > 1.0 → çizgiler daha kalın görünür (kenar pikselleri daha opak).
    """
    path = os.path.join(_GORSELLER_DIR, filename)
    img = QImage(path)
    if img.isNull():
        logger.warning("Simge yüklenemedi: %s", filename)
        return QPixmap(size, size)

    img = img.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    ).convertToFormat(QImage.Format.Format_ARGB32)

    icon_c = QColor(color)
    ir, ig, ib = icon_c.red(), icon_c.green(), icon_c.blue()

    for y in range(img.height()):
        for x in range(img.width()):
            px = img.pixel(x, y)
            r = (px >> 16) & 0xFF
            g = (px >> 8) & 0xFF
            b = px & 0xFF
            brightness = (r + g + b) / 3
            # thickness ile alpha'yı güçlendirerek çizgileri kalınlaştır
            alpha = max(0, min(255, int((255 - brightness) * thickness)))
            img.setPixel(x, y, (alpha << 24) | (ir << 16) | (ig << 8) | ib)

    return QPixmap.fromImage(img)


def style_step_box(box: QGroupBox, border_color: str) -> None:
    """Adım kutusunun kenarlık/başlık ve içerik metni rengini aktif palete göre
    (yeniden) uygular. Tema değişiminde panellerden tekrar çağrılır."""
    box.setStyleSheet(step_box_style(border_color=border_color))
    lbl = getattr(box, "_content_lbl", None)
    if lbl is not None:
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")


def make_step_box(title: str, content: str, border_color: str) -> QGroupBox:
    """Kümülatif görselleştirme için renkli çerçeveli kutucuk oluşturur."""
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(8, 18, 8, 8)

    lbl = QLabel(content)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(lbl)

    # Tema değişiminde yeniden stillendirilebilmesi için içerik etiketini sakla.
    box._content_lbl = lbl  # type: ignore[attr-defined]
    style_step_box(box, border_color)

    return box


def truncate_hex(hex_str: str, max_len: int = 48) -> str:
    """Uzun hex değerlerini görüntüleme için kısaltır."""
    if len(hex_str) > max_len:
        return hex_str[:max_len] + "…"
    return hex_str


def build_step_content(step: StepResult) -> str:
    """Adım verilerini kullanıcı dostu Türkçe etiketlerle formatlar."""
    lines = [step.description, ""]
    for key, value in step.data.items():
        if key.endswith("_bytes"):
            continue
        display_key = FRIENDLY_NAMES.get(key, key)
        if key == "verification_result":
            display_val = "✅ DOĞRULANDI" if value else "❌ DOĞRULANAMADI"
        elif isinstance(value, str) and len(value) > 64:
            display_val = truncate_hex(value)
        else:
            display_val = value
        lines.append(f"  • {display_key}: {display_val}")
    return "\n".join(lines)
