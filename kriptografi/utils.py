"""
utils.py – Yardımcı Fonksiyonlar ve Sabitler
"""
from __future__ import annotations

import os

from cryptography.exceptions import InvalidSignature, InvalidTag

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from kriptografi.crypto_core import StepResult
from arayuz.theme import COLORS

# Görseller (SVG ikonlar + PNG akış diyagramları) — tek klasörde toplu erişim.
# Eski 'icons/' klasörü 'görseller/' olarak yeniden adlandırıldı; alice/bob
# akış PNG'leri de buraya taşındı. Bu dosya 'kriptografi/' alt-paketinde
# olduğu için path bir üst dizine (proje köküne) çıkar.
_PROJE_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GORSELLER_DIR = os.path.join(_PROJE_KOKU, "görseller")


def _svg_pixmap(filename: str, color: str, size: int = 20) -> QPixmap:
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
    "associated_data":        "AAD (Authenticated Metadata)",
    "associated_data_size":   "AAD Boyutu",
    "message":                "Mesaj İçeriği",
    "elapsed_ms":             "İşlem Süresi",
}


def format_crypto_exception(exc: BaseException) -> tuple[str, str]:
    """Kriptografik istisnayı kullanıcıya gösterilecek (başlık, gövde) metnine çevirir.

    UI katmanı yakaladığı her Exception'ı doğrudan `str(exc)` olarak
    göstermek yerine bu çevirmeni kullanmalıdır. Böylece:
      - Kullanıcıya anlaşılır Türkçe bir neden verilir.
      - Tekniği merak eden için orijinal istisna adı parantez içinde
        eklenir (sessiz bilgi kaybı olmaz).
      - Teknik detaylar tek bir yerden güncellenir.

    Dönüş: (başlık, gövde) — QMessageBox.critical gibi yerlerde
    doğrudan kullanılabilir.
    """
    exc_name = type(exc).__name__

    if isinstance(exc, InvalidTag):
        return (
            "Deşifreleme Başarısız — Kimlik Doğrulama Hatası",
            "AES-256-GCM kimlik doğrulama etiketi (tag) doğrulanamadı. "
            "Bu genellikle şu sebeplerden biriyle olur:\n\n"
            "  • Şifreli mesaj, nonce veya AAD (authenticated metadata) "
            "iletim sırasında değiştirilmiş olabilir.\n"
            "  • Bob'un çözdüğü oturum anahtarı ile Alice'in kullandığı "
            "anahtar uyuşmuyor olabilir.\n\n"
            "Paketin bütünlüğü bozulduğu için içerik güvenle "
            "çözülemez — bu tasarlanmış güvenlik davranışıdır.\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, InvalidSignature):
        return (
            "İmza Doğrulanamadı",
            "Dijital imza, Alice'in açık anahtarıyla doğrulanamadı. "
            "Olası nedenler:\n\n"
            "  • Mesaj imzalandıktan sonra değiştirilmiş.\n"
            "  • İmza, başka bir gizli anahtarla üretilmiş.\n"
            "  • İmzanın bağlı olduğu özet (H(m)) farklı bir mesaja ait.\n\n"
            "Kimlik veya bütünlük doğrulanamadığı için mesaj "
            "kabul edilmemelidir.\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, ValueError):
        # OAEP çözme hatası, uzunluk kontrolü, vb. — genellikle veri
        # formatı bozukluğu.
        return (
            "Paket Formatı Hatası",
            "Şifreli paketteki bir alan beklenen formatta değil. "
            "Olası nedenler:\n\n"
            "  • RSA-OAEP ile sarılmış oturum anahtarı bozulmuş ya da "
            "yanlış gizli anahtarla çözülmeye çalışılmış olabilir.\n"
            "  • Birleşik veri (mesaj ‖ imza) beklenen 256 byte'lık "
            "imza alanını taşıyamayacak kadar kısa olabilir.\n\n"
            f"Detay: {exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, RuntimeError):
        return (
            "Akış Hatası",
            f"İşlem akışı bir önkoşulu karşılamadı:\n\n{exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    # Beklenmeyen tipte istisna — yine de kullanıcıya bir şey göster.
    return (
        "Beklenmeyen Hata",
        f"İşlem sırasında ele alınmamış bir hata oluştu:\n\n{exc}\n\n"
        f"(Teknik: {exc_name})"
    )


def _png_icon_pixmap(filename: str, color: str, size: int, thickness: float = 1.0) -> QPixmap:
    """PNG dosyasını yükler; beyaz/açık pikselleri şeffafa, koyu pikselleri
    verilen renge dönüştürerek QPixmap döndürür.
    thickness > 1.0 → çizgiler daha kalın görünür (kenar pikselleri daha opak).
    """
    path = os.path.join(_GORSELLER_DIR, filename)
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
