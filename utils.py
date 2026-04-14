"""
utils.py – Yardımcı Fonksiyonlar ve Sabitler
"""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from crypto_core import StepResult
from theme import COLORS

_ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


def _svg_pixmap(filename: str, color: str, size: int = 20) -> QPixmap:
    """SVG simge dosyasını verilen renk ve boyutta QPixmap'e dönüştürür.
    SVG içindeki 'currentColor' değeri çalışma zamanında verilen renge çevrilir.
    """
    path = os.path.join(_ICONS_DIR, filename)
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
        print(f"[icon] Yüklenemedi: {filename} — {exc}")
    return pix

FRIENDLY_NAMES: dict[str, str] = {
    "nonce_hex":              "Rastgele Sayı (Nonce)",
    "session_key_hex":        "Oturum Anahtarı (K_S)",
    "hash_hex":               "SHA-256 Özet Değeri H(m)",
    "signature_hex":          "Dijital İmza",
    "encrypted_key_hex":      "RSA Şifreli Oturum Anahtarı",
    "ciphertext_hex_preview": "Şifreli Mesaj (Önizleme)",
    "verification_result":    "Doğrulama Sonucu",
    "key_info":               "Kullanılan Anahtar",
    "combined_size":          "Birleşik Veri Boyutu",
    "message_size":           "Mesaj Boyutu",
    "signature_size":         "İmza Boyutu",
    "ciphertext_size":        "Şifreli Veri Boyutu",
    "encrypted_key_size":     "RSA Şifreli Anahtar Boyutu",
    "total_packet_size":      "Toplam Paket Boyutu",
    "message":                "Mesaj İçeriği",
    "elapsed_ms":             "İşlem Süresi",
}


def _png_icon_pixmap(filename: str, color: str, size: int, thickness: float = 1.0) -> QPixmap:
    """PNG dosyasını yükler; beyaz/açık pikselleri şeffafa, koyu pikselleri
    verilen renge dönüştürerek QPixmap döndürür.
    thickness > 1.0 → çizgiler daha kalın görünür (kenar pikselleri daha opak).
    """
    path = os.path.join(_ICONS_DIR, filename)
    img = QImage(path)
    if img.isNull():
        print(f"[icon] Yüklenemedi: {filename}")
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


def _make_step_box(title: str, content: str, border_color: str) -> QGroupBox:
    """Kümülatif görselleştirme için renkli çerçeveli kutucuk oluşturur."""
    box = QGroupBox(title)
    box.setStyleSheet(
        f"QGroupBox {{ border: 2px solid {border_color}; border-radius: 8px; "
        f"margin-top: 14px; padding: 14px 8px 8px 8px; }}"
        f"QGroupBox::title {{ color: {border_color}; font-family: 'Georgia', 'Palatino Linotype', serif; "
        f"font-weight: bold; font-size: 15px; }}"
    )
    layout = QVBoxLayout(box)
    layout.setContentsMargins(8, 18, 8, 8)

    lbl = QLabel(content)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(lbl)

    return box


def _truncate_hex(hex_str: str, max_len: int = 48) -> str:
    """Uzun hex değerlerini görüntüleme için kısaltır."""
    if len(hex_str) > max_len:
        return hex_str[:max_len] + "…"
    return hex_str


def _build_step_content(step: StepResult) -> str:
    """Adım verilerini kullanıcı dostu Türkçe etiketlerle formatlar."""
    lines = [step.description, ""]
    for key, value in step.data.items():
        if key.endswith("_bytes"):
            continue
        display_key = FRIENDLY_NAMES.get(key, key)
        if key == "verification_result":
            display_val = "✅ DOĞRULANDI" if value else "❌ DOĞRULANAMADI"
        elif isinstance(value, str) and len(value) > 64:
            display_val = _truncate_hex(value)
        else:
            display_val = value
        lines.append(f"  • {display_key}: {display_val}")
    return "\n".join(lines)
