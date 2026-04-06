"""
utils.py – Yardımcı Fonksiyonlar ve Sabitler
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from crypto_core import StepResult
from theme import COLORS

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


def _make_step_box(title: str, content: str, border_color: str) -> QGroupBox:
    """Kümülatif görselleştirme için renkli çerçeveli kutucuk oluşturur."""
    box = QGroupBox(title)
    box.setStyleSheet(
        f"QGroupBox {{ border: 2px solid {border_color}; border-radius: 8px; "
        f"margin-top: 14px; padding: 14px 8px 8px 8px; }}"
        f"QGroupBox::title {{ color: {border_color}; font-weight: bold; }}"
    )
    layout = QVBoxLayout(box)
    layout.setContentsMargins(8, 18, 8, 8)

    lbl = QLabel(content)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
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
