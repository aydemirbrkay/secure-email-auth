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
    "text_on_accent":   "#FFFFFF",  # vurgu rengi üstündeki metin (buton vb.)
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
    "text_on_accent":   "#FFFFFF",  # vurgu rengi üstündeki metin (buton vb.)
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


# ----------------------------------------------------------------------------
# Stil Helper'ları
# ----------------------------------------------------------------------------
# Tüm renkler aktif COLORS paletinden okunur (hardcoded hex yok). Her çağrıda
# yeniden üretildikleri için tema değişiminde (_apply_styles/refresh_theme tekrar
# çağrıldığında) doğru paleti verir; satır-içi setStyleSheet kopyalarını tekleştirir.


def card_style(selector: str = "QFrame",
               background_key: str = "bg_card",
               radius: int = 8) -> str:
    """Kart/çerçeve stili. ``selector`` ile QFrame veya ``#objectName`` hedeflenir."""
    c = COLORS
    return (
        f"{selector} {{ background-color: {c[background_key]}; "
        f"border: 1px solid {c['border']}; border-radius: {radius}px; }}"
    )


def step_box_style(active: bool = False,
                   completed: bool = False,
                   *,
                   border_color: str | None = None) -> str:
    """Adım kutusu (QGroupBox) stili. ``border_color`` verilirse onu kullanır
    (panellerin adım-bazlı renk şeması); yoksa duruma göre seçer:
    tamamlandı→yeşil, aktif→vurgu kenarlığı, aksi halde→nötr kenarlık."""
    c = COLORS
    if border_color is None:
        if completed:
            border_color = c["accent_green"]
        elif active:
            border_color = c["border_highlight"]
        else:
            border_color = c["border"]
    return (
        f"QGroupBox {{ border: 2px solid {border_color}; border-radius: 8px; "
        f"margin-top: 14px; padding: 14px 8px 8px 8px; }}"
        f"QGroupBox::title {{ color: {border_color}; "
        f"font-family: 'Georgia', 'Palatino Linotype', serif; "
        f"font-weight: bold; font-size: 15px; }}"
    )


def button_primary_style() -> str:
    """Birincil eylem butonu (dolu, vurgu mavisi)."""
    c = COLORS
    return (
        f"QPushButton {{ background: {c['accent_blue']}; "
        f"color: {c['text_on_accent']}; border: none; "
        f"border-radius: 6px; padding: 8px 22px; font-weight: bold; font-size: 13px; "
        f"min-height: 34px; min-width: 96px; }}"
        f"QPushButton:hover {{ background: {c['accent_mauve']}; }}"
        f"QPushButton:disabled {{ background: {c['bg_card']}; "
        f"color: {c['text_muted']}; }}"
    )


def button_secondary_style() -> str:
    """İkincil buton (içi boş, nötr; hover'da şeftali vurgu)."""
    c = COLORS
    return (
        f"QPushButton {{ background: {c['bg_card']}; "
        f"color: {c['text_secondary']}; border: 1px solid {c['border']}; "
        f"border-radius: 6px; padding: 8px 18px; font-size: 13px; "
        f"min-height: 34px; }}"
        f"QPushButton:hover {{ background: {c['accent_peach']}; "
        f"color: {c['text_on_accent']}; }}"
    )


def label_title_style(accent_key: str = "accent_blue") -> str:
    """Başlık etiketi rengi. ``accent_key`` palet vurgu anahtarıdır
    (örn. Alice=accent_mauve, Bob=accent_green)."""
    return f"color: {COLORS[accent_key]};"


def progress_bar_style() -> str:
    """İlerleme çubuğu (oluk + dolum)."""
    c = COLORS
    return (
        f"QProgressBar {{ border: 1px solid {c['border']}; "
        f"border-radius: 4px; background: {c['bg_card']}; "
        f"color: {c['text_primary']}; text-align: center; height: 18px; }}"
        f"QProgressBar::chunk {{ background-color: {c['accent_blue']}; "
        f"border-radius: 3px; }}"
    )


# Toast seviyesi → palet vurgu anahtarı.
_TOAST_LEVELS: dict[str, str] = {
    "success": "accent_green",
    "error":   "accent_red",
    "warning": "accent_yellow",
    "info":    "accent_blue",
}


def toast_style(level: str) -> str:
    """Toast üst şerit stili. ``level`` ∈ {success, error, warning, info}."""
    accent_key = _TOAST_LEVELS.get(level)
    if accent_key is None:
        raise ValueError(f"Geçersiz toast seviyesi: {level}")
    return (
        f"background: {COLORS[accent_key]}; "
        f"border-top-left-radius: 10px; "
        f"border-top-right-radius: 10px; "
        f"border: none;"
    )


def get_animation_tick_ms(base: int) -> int:
    """Animasyon timer aralığını (ms) döndürür; "Hareketi Azalt" açıksa
    tick'i 3× yavaşlatır. Fotosensitif kullanıcılar için hızlı/titreşimli
    geçişler yumuşatılır. Lazy import ile döngüsel bağımlılık önlenir."""
    from arayuz.accessibility import REDUCE_MOTION

    return base * 3 if REDUCE_MOTION.is_enabled() else base


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
