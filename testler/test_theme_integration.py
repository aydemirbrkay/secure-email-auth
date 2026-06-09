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

# Headless/offscreen ortam ve tek QApplication örneği conftest.py'deki
# session kapsamlı autouse `qapp` fixture'ı tarafından sağlanır.


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

    def test_main_window_accessibility(self) -> None:
        """C8: interaktif butonlar Türkçe accessibleName taşır; "Hareketi
        Azalt" menü eylemi tercihi kalıcılaştırır. (MainWindow burada güvenle
        kurulur; bkz. test_accessibility.py notu.)"""
        from arayuz.accessibility import REDUCE_MOTION, ReduceMotionSettings
        from main_gui import MainWindow

        win = MainWindow()
        for btn in (win._btn_keygen, win._btn_start, win._btn_next,
                    win._btn_reset):
            self.assertTrue(btn.accessibleName().strip())
        self.assertTrue(win._alice_panel.accessibleName().strip())

        win._reduce_motion_action.setChecked(True)
        self.assertTrue(ReduceMotionSettings().load())
        win._reduce_motion_action.setChecked(False)
        self.assertFalse(ReduceMotionSettings().load())
        REDUCE_MOTION.set_enabled(False)

        win.deleteLater()

    def test_animation_window_builds_in_both_themes(self) -> None:
        from arayuz import theme
        from animation_modals import SHA256AnimationWindow

        for mode in ("dark", "light"):
            theme.MANAGER.set_mode(mode)
            w = SHA256AnimationWindow("merhaba", "ab" * 32, on_close=lambda: None)
            self.assertIsNotNone(w)
            w.deleteLater()

    def test_open_animations_refresh_theme(self) -> None:
        """Açık animasyon, tema değişiminde içerik+chrome yeniden temalanır;
        görünür adım korunur ve istisna atılmaz (RSA/SHA/AES)."""
        import os
        from arayuz import theme
        from animation_modals import (
            RSAAnimationWindow,
            SHA256AnimationWindow,
            AESAnimationWindow,
        )

        theme.MANAGER.set_mode("light")
        builders = [
            lambda: RSAAnimationWindow("QUJDRA==", "WFlaVw==", on_close=lambda: None),
            lambda: SHA256AnimationWindow("merhaba dünya", "ab" * 32, on_close=lambda: None),
            lambda: AESAnimationWindow(os.urandom(32), b"merhaba dunya", "", on_close=lambda: None),
        ]
        for build in builders:
            w = build()
            for _ in range(min(2, max(1, w.total_steps - 1))):
                w._advance_step()
            before = w.current_step

            theme.MANAGER.set_mode("dark")
            w.refresh_theme()
            self.assertEqual(w.current_step, before)

            theme.MANAGER.set_mode("light")
            w.refresh_theme()
            self.assertEqual(w.current_step, before)

            w._stop_timers()
            w.deleteLater()

        theme.MANAGER.set_mode("dark")


if __name__ == "__main__":
    unittest.main()
