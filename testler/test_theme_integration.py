"""
test_theme_integration.py – Canlı tema geçişinin davranışsal smoke testi.

MainWindow'u offscreen kurar, temayı değiştirir ve:
  * istisna olmadan tüm widget ağacının yeniden stillendiğini,
  * aktif paletin (COLORS) gerçekten değiştiğini,
  * COLORS/ANIM_COLORS nesne kimliğinin korunduğunu (yerinde güncelleme),
  * bir animasyon penceresinin her iki temada da hatasız kurulduğunu
doğrular.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


class TestThemeIntegration(unittest.TestCase):
    def setUp(self) -> None:
        from arayuz import theme
        theme.MANAGER.set_mode("dark")

    def tearDown(self) -> None:
        from arayuz import theme
        theme.MANAGER.set_mode("dark")

    def test_main_window_live_toggle(self) -> None:
        from arayuz import theme
        from main_gui import MainWindow

        win = MainWindow()
        colors_id = id(theme.COLORS)
        anim_id = id(theme.ANIM_COLORS)
        dark_bg = theme.COLORS["bg_main"]

        # Karanlık → Aydınlık
        theme.MANAGER.toggle()
        self.assertEqual(theme.MANAGER.mode, "light")
        self.assertEqual(theme.COLORS["bg_main"], theme._LIGHT["bg_main"])
        self.assertNotEqual(theme.COLORS["bg_main"], dark_bg)
        # Yerinde güncelleme: nesne kimliği korunmalı
        self.assertEqual(id(theme.COLORS), colors_id)
        self.assertEqual(id(theme.ANIM_COLORS), anim_id)

        # Aydınlık → Karanlık (geri)
        theme.MANAGER.toggle()
        self.assertEqual(theme.MANAGER.mode, "dark")
        self.assertEqual(theme.COLORS["bg_main"], dark_bg)

        win.deleteLater()

    def test_panels_have_apply_styles(self) -> None:
        from main_gui import MainWindow

        win = MainWindow()
        # main_gui._on_theme_changed bu metotları çağırır; var olmalılar.
        self.assertTrue(hasattr(win._alice_panel, "_apply_styles"))
        self.assertTrue(hasattr(win._bob_panel, "_apply_styles"))
        # Doğrudan çağrı istisna atmamalı
        win._alice_panel._apply_styles()
        win._bob_panel._apply_styles()
        win._apply_styles()
        win.deleteLater()

    def test_animation_window_builds_in_both_themes(self) -> None:
        from arayuz import theme
        from animation_modals import SHA256AnimationWindow

        for mode in ("dark", "light"):
            theme.MANAGER.set_mode(mode)
            w = SHA256AnimationWindow("merhaba", "ab" * 32, on_close=lambda: None)
            self.assertIsNotNone(w)
            w.deleteLater()


if __name__ == "__main__":
    unittest.main()
