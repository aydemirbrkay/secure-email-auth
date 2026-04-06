"""
theme.py – Renk Paleti ve Stil Sabitleri
"""
from __future__ import annotations

COLORS = {
    "bg_main": "#1e1e2e",
    "bg_panel": "#282840",
    "bg_card": "#313150",
    "bg_input": "#3b3b5c",
    "text_primary": "#cdd6f4",
    "text_secondary": "#a6adc8",
    "text_muted": "#6c7086",
    "accent_blue": "#89b4fa",
    "accent_green": "#a6e3a1",
    "accent_red": "#f38ba8",
    "accent_yellow": "#f9e2af",
    "accent_mauve": "#cba6f7",
    "accent_teal": "#94e2d5",
    "accent_peach": "#fab387",
    "border": "#45475a",
    "border_highlight": "#89b4fa",
}

GLOBAL_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["bg_main"]};
}}
QWidget {{
    color: {COLORS["text_primary"]};
    font-family: "Segoe UI", "Noto Sans", "Ubuntu", sans-serif;
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
    color: {COLORS["bg_main"]};
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
    background-color: {COLORS["text_muted"]};
    color: {COLORS["bg_panel"]};
}}
QGroupBox {{
    border: 2px solid {COLORS["border"]};
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
    color: {COLORS["accent_blue"]};
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
    COLORS["accent_blue"],     # Adım 1: SHA-256  (en içte)
    COLORS["accent_mauve"],    # Adım 2: RSA İmza
    COLORS["accent_yellow"],   # Adım 3: Birleştirme
    COLORS["accent_green"],    # Adım 4: AES-GCM
    COLORS["accent_peach"],    # Adım 5: RSA Anahtar Şifreleme
    COLORS["accent_teal"],     # Adım 6: Gönderim  (en dışta)
]

# Adım renkleri — Bob: dıştan içe (karmaşık → sade)
STEP_COLORS_BOB = [
    COLORS["accent_peach"],    # Adım 1: RSA Anahtar Çözme  (en dışta)
    COLORS["accent_green"],    # Adım 2: AES-GCM Deşifreleme
    COLORS["accent_yellow"],   # Adım 3: Ayrıştırma
    COLORS["accent_blue"],     # Adım 4: SHA-256 Yeniden Hesaplama
    COLORS["accent_mauve"],    # Adım 5: İmza Doğrulama (en içte)
]
