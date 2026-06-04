"""
theme.py – Renk Paleti, Tema Motoru ve Stil Sabitleri
=====================================================
Tek renk kaynağı. İki palet (_DARK / _LIGHT). Aktif palet COLORS / ANIM_COLORS /
STEP_COLORS_* içine YERİNDE yazılır; böylece projedeki tüm referanslar aynı nesneyi
tutmaya devam eder. Tema değişimi MANAGER.set_mode/toggle ile yapılır ve themeChanged
sinyali yayılır.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, QSettings, pyqtSignal

_DARK: dict[str, str] = {
    "bg_main":          "#0B0F17",
    "bg_panel":         "#141A24",
    "bg_card":          "#1C2330",
    "bg_input":         "#232C3C",
    "text_primary":     "#E6EAF2",
    "text_secondary":   "#B8C0CE",
    "text_muted":       "#9AA4B2",
    "accent_blue":      "#7C9CFF",
    "accent_green":     "#7EE2B8",
    "accent_red":       "#EF4444",
    "accent_yellow":    "#F4C95D",
    "accent_mauve":     "#C4A7FF",
    "accent_teal":      "#5FE3CE",
    "accent_peach":     "#F0A26B",
    "border":           "#2A3340",
    "border_highlight": "#7C9CFF",
    "hl_mauve":         "#3D2F56",
    "hl_yellow":        "#3D3119",
}

_LIGHT: dict[str, str] = {
    "bg_main":          "#F5F7FA",
    "bg_panel":         "#FFFFFF",
    "bg_card":          "#F0F3F8",
    "bg_input":         "#E7ECF3",
    "text_primary":     "#0F172A",
    "text_secondary":   "#334155",
    "text_muted":       "#475569",
    "accent_blue":      "#2563EB",
    "accent_green":     "#059669",
    "accent_red":       "#DC2626",
    "accent_yellow":    "#B7791F",
    "accent_mauve":     "#6D28D9",
    "accent_teal":      "#0D9488",
    "accent_peach":     "#C2630F",
    "border":           "#D9DFE8",
    "border_highlight": "#2563EB",
    "hl_mauve":         "#EADDF7",
    "hl_yellow":        "#F6ECC9",
}

_PALETTES = {"dark": _DARK, "light": _LIGHT}

_ALICE_KEYS = ["accent_mauve", "accent_blue", "accent_yellow",
               "accent_green", "accent_peach", "accent_teal"]
_BOB_KEYS   = ["accent_peach", "accent_green", "accent_yellow",
               "accent_blue", "accent_mauve"]

COLORS: dict[str, str] = {}
ANIM_COLORS: dict[str, str] = {}
STEP_COLORS_ALICE: list[str] = []
STEP_COLORS_BOB: list[str] = []


def _load_palette(mode: str) -> None:
    """Aktif paleti global nesnelere YERİNDE yazar (nesne kimliği korunur)."""
    pal = _PALETTES[mode]
    COLORS.clear()
    COLORS.update(pal)
    ANIM_COLORS.clear()
    ANIM_COLORS.update(pal)
    STEP_COLORS_ALICE.clear()
    STEP_COLORS_ALICE.extend(pal[k] for k in _ALICE_KEYS)
    STEP_COLORS_BOB.clear()
    STEP_COLORS_BOB.extend(pal[k] for k in _BOB_KEYS)


def build_global_stylesheet() -> str:
    """Aktif COLORS'tan QApplication geneli stylesheet üretir."""
    c = COLORS
    return f"""
QMainWindow {{ background-color: {c["bg_main"]}; }}
QWidget {{
    color: {c["text_primary"]};
    font-family: "IBM Plex Sans", "Inter", "Segoe UI", sans-serif;
}}
QLabel {{ color: {c["text_primary"]}; }}
QLineEdit, QTextEdit {{
    background-color: {c["bg_input"]};
    border: 1px solid {c["border"]};
    border-radius: 6px;
    padding: 8px;
    color: {c["text_primary"]};
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus {{ border-color: {c["border_highlight"]}; }}
QPushButton {{
    background-color: {c["accent_blue"]};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: bold;
    font-size: 14px;
}}
QPushButton:hover {{ background-color: {c["accent_mauve"]}; }}
QPushButton:disabled {{ background-color: {c["bg_card"]}; color: {c["text_muted"]}; }}
QGroupBox {{
    border: 2px solid {c["border"]};
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
    color: {c["accent_blue"]};
    font-family: "Georgia", "Palatino Linotype", serif;
}}
QScrollArea {{ border: none; background-color: transparent; }}
QSplitter::handle {{ background-color: {c["border"]}; width: 2px; }}
QComboBox {{
    background-color: {c["bg_input"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border"]};
    border-radius: 4px;
    padding: 4px 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {c["bg_card"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border"]};
    selection-background-color: {c["accent_blue"]};
    selection-color: #FFFFFF;
}}
"""


GLOBAL_STYLESHEET: str = ""


class ThemeManager(QObject):
    """Aktif temayı tutar, geçişte global nesneleri günceller ve sinyal yayar."""

    themeChanged = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings("ErciyesBM", "SecureEmail")
        self.mode: str = self._settings.value("theme_mode", "dark", type=str)
        if self.mode not in _PALETTES:
            self.mode = "dark"
        _load_palette(self.mode)
        global GLOBAL_STYLESHEET
        GLOBAL_STYLESHEET = build_global_stylesheet()

    def set_mode(self, mode: str) -> None:
        if mode not in _PALETTES:
            raise ValueError(f"Geçersiz tema: {mode}")
        self.mode = mode
        _load_palette(mode)
        global GLOBAL_STYLESHEET
        GLOBAL_STYLESHEET = build_global_stylesheet()
        self._settings.setValue("theme_mode", mode)
        self.themeChanged.emit(mode)

    def toggle(self) -> None:
        self.set_mode("light" if self.mode == "dark" else "dark")


MANAGER = ThemeManager()
