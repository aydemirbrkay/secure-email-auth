"""
test_theme_styles.py – arayuz.theme stil helper'larının birim testleri.

Doğrulanan davranışlar:
  * Her helper aktif paletten (COLORS) renk çeker — hardcoded hex sızdırmaz.
  * Tema değişiminde (dark→light) üretilen stil dizgisi yeni paleti yansıtır.
  * toast_style geçersiz seviyede ValueError atar (negatif durum).
  * step_box_style aktif/tamamlandı/nötr durumlarında farklı kenarlık verir.
"""
from __future__ import annotations

import re
import unittest

from arayuz import theme
from arayuz.theme import (
    MANAGER,
    button_primary_style,
    button_secondary_style,
    card_style,
    label_title_style,
    progress_bar_style,
    step_box_style,
    toast_style,
)

# Helper çıktısında izin verilen tek sabit hex: beyaz (palet anahtarı
# text_on_accent zaten "#FFFFFF" olduğundan dizgide görünmesi normaldir).
_HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}")


def _foreign_hex(style: str) -> list[str]:
    """Aktif palette KARŞILIĞI OLMAYAN hex değerlerini döndürür (sızıntı tespiti)."""
    palette = set(v.upper() for v in theme.COLORS.values())
    return [h for h in _HEX_RE.findall(style) if h.upper() not in palette]


class TestThemeStyleHelpers(unittest.TestCase):
    def setUp(self) -> None:
        MANAGER.set_mode("dark")

    def tearDown(self) -> None:
        MANAGER.set_mode("dark")

    # --- Pozitif: tüm renkler aktif paletten gelir (sızıntı yok) ----------
    def test_helpers_use_only_palette_colors(self) -> None:
        styles = [
            card_style(),
            card_style("#toastCard", background_key="bg_panel", radius=10),
            step_box_style(),
            step_box_style(active=True),
            step_box_style(completed=True),
            button_primary_style(),
            button_secondary_style(),
            label_title_style(),
            label_title_style("accent_mauve"),
            progress_bar_style(),
            toast_style("success"),
            toast_style("error"),
        ]
        for s in styles:
            self.assertEqual(_foreign_hex(s), [], f"Palet dışı hex sızdı: {s}")

    # --- Pozitif: tema değişimi stil dizgisine yansır ---------------------
    def test_style_reflects_active_theme(self) -> None:
        dark = button_primary_style()
        self.assertIn(theme._DARK["accent_blue"], dark)

        MANAGER.set_mode("light")
        light = button_primary_style()
        self.assertIn(theme._LIGHT["accent_blue"], light)
        self.assertNotEqual(dark, light)

    # --- Pozitif: step_box durumları farklı kenarlık verir ----------------
    def test_step_box_states_differ(self) -> None:
        neutral = step_box_style()
        active = step_box_style(active=True)
        completed = step_box_style(completed=True)
        self.assertIn(theme.COLORS["border"], neutral)
        self.assertIn(theme.COLORS["border_highlight"], active)
        self.assertIn(theme.COLORS["accent_green"], completed)
        # border_color override durumu yok sayar (panel adım renkleri için)
        forced = step_box_style(active=True, border_color=theme.COLORS["accent_yellow"])
        self.assertIn(theme.COLORS["accent_yellow"], forced)

    # --- Pozitif: toast_style seviye→renk eşlemesi ------------------------
    def test_toast_style_levels(self) -> None:
        self.assertIn(theme.COLORS["accent_green"], toast_style("success"))
        self.assertIn(theme.COLORS["accent_red"], toast_style("error"))
        self.assertIn(theme.COLORS["accent_yellow"], toast_style("warning"))
        self.assertIn(theme.COLORS["accent_blue"], toast_style("info"))

    # --- Negatif: geçersiz toast seviyesi hata atar -----------------------
    def test_toast_style_invalid_level_raises(self) -> None:
        with self.assertRaises(ValueError):
            toast_style("kritik")

    # --- Negatif: label_title_style bilinmeyen palet anahtarında KeyError -
    def test_label_title_unknown_key_raises(self) -> None:
        with self.assertRaises(KeyError):
            label_title_style("accent_yok")


if __name__ == "__main__":
    unittest.main()
