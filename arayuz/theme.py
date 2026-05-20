"""
theme.py – Renk Paleti ve Stil Sabitleri
"""
from __future__ import annotations

COLORS = {
    "bg_main":          "#3D4451",
    "bg_panel":         "#4A5568",
    "bg_card":          "#536070",
    "bg_input":         "#4D5769",
    "text_primary":     "#F1F3F7",
    "text_secondary":   "#CBD5E0",
    "text_muted":       "#8896A8",
    "accent_blue":      "#5B8EC2",
    "accent_green":     "#6FC28C",
    "accent_red":       "#D95555",
    "accent_yellow":    "#C99B24",
    "accent_mauve":     "#9B7EC7",
    "accent_teal":      "#4DA898",
    "accent_peach":     "#C4834A",
    "border":           "#5A6272",
    "border_highlight": "#5B8EC2",
}

GLOBAL_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["bg_main"]};
}}
QWidget {{
    color: {COLORS["text_primary"]};
    font-family: "IBM Plex Sans", "Inter", "Segoe UI", sans-serif;
}}
QLabel {{
    color: {COLORS["text_primary"]};
}}
QLineEdit, QTextEdit {{
    background-color: {COLORS["bg_input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 8px;
    color: {COLORS["text_primary"]};
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {COLORS["border_highlight"]};
}}
QPushButton {{
    background-color: {COLORS["accent_blue"]};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: bold;
    font-size: 14px;
}}
QPushButton:hover {{
    background-color: {COLORS["accent_mauve"]};
}}
QPushButton:disabled {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text_muted"]};
}}
QGroupBox {{
    border: 2px solid #7A8A9A;
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 10px 10px 10px;
    font-weight: bold;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #A8C4E0;
    font-family: "Georgia", "Palatino Linotype", serif;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QSplitter::handle {{
    background-color: {COLORS["border"]};
    width: 2px;
}}
"""

# Adım renkleri — Alice: içten dışa (sade → karmaşık)
STEP_COLORS_ALICE = [
    COLORS["accent_blue"],    # Adım 1: SHA-256  (en içte)
    COLORS["accent_mauve"],   # Adım 2: RSA İmza
    COLORS["accent_yellow"],  # Adım 3: Birleştirme
    COLORS["accent_green"],   # Adım 4: AES-GCM
    COLORS["accent_peach"],   # Adım 5: RSA Anahtar Şifreleme
    COLORS["accent_teal"],    # Adım 6: Gönderim  (en dışta)
]

# Adım renkleri — Bob: dıştan içe (karmaşık → sade)
STEP_COLORS_BOB = [
    COLORS["accent_peach"],   # Adım 1: RSA Anahtar Çözme  (en dışta)
    COLORS["accent_green"],   # Adım 2: AES-GCM Deşifreleme
    COLORS["accent_yellow"],  # Adım 3: Ayrıştırma
    COLORS["accent_blue"],    # Adım 4: SHA-256 Yeniden Hesaplama
    COLORS["accent_mauve"],   # Adım 5: İmza Doğrulama (en içte)
]
