"""
test_accessibility.py – C8 erişilebilirlik katmanı testleri.

Doğrulanan:
  * set_accessible ad/açıklamayı widget'a yazar.
  * build_tab_order hatasız çalışır (tek/çok widget).
  * ReduceMotionSettings tercihi kalıcı (QSettings).
  * get_animation_tick_ms hareket azaltma açıkken tick'i 3× yavaşlatır.
  * MainWindow butonları accessibleName'e sahip; menü eylemi tercihi kalıcılaştırır.
"""
from __future__ import annotations

import unittest

from PyQt6.QtWidgets import QLabel, QPushButton

from arayuz import theme
from arayuz.accessibility import (
    REDUCE_MOTION,
    ReduceMotionSettings,
    build_tab_order,
    motion_effects_enabled,
    set_accessible,
)


class TestAccessibleHelpers(unittest.TestCase):
    def test_set_accessible_sets_name_and_description(self) -> None:
        w = QPushButton()
        set_accessible(w, "Anahtar Üret", "RSA-2048 üretir.")
        self.assertEqual(w.accessibleName(), "Anahtar Üret")
        self.assertEqual(w.accessibleDescription(), "RSA-2048 üretir.")
        w.deleteLater()

    def test_set_accessible_description_optional(self) -> None:
        w = QLabel()
        set_accessible(w, "Başlık")
        self.assertEqual(w.accessibleName(), "Başlık")
        self.assertEqual(w.accessibleDescription(), "")
        w.deleteLater()

    def test_build_tab_order_runs_for_one_and_many(self) -> None:
        a, b, c = QPushButton(), QPushButton(), QPushButton()
        # Tek widget → no-op (hata atmamalı).
        build_tab_order(a)
        # Çoklu → zincir kurulur (istisna atmamalı).
        build_tab_order(a, b, c)
        for w in (a, b, c):
            w.deleteLater()


class TestReduceMotion(unittest.TestCase):
    def tearDown(self) -> None:
        REDUCE_MOTION.set_enabled(False)

    def test_setting_persists_across_instances(self) -> None:
        REDUCE_MOTION.set_enabled(True)
        fresh = ReduceMotionSettings()  # ayrı örnek, aynı QSettings
        self.assertTrue(fresh.load())

        REDUCE_MOTION.set_enabled(False)
        fresh2 = ReduceMotionSettings()
        self.assertFalse(fresh2.load())

    def test_get_animation_tick_ms_slows_when_enabled(self) -> None:
        REDUCE_MOTION.set_enabled(False)
        self.assertEqual(theme.get_animation_tick_ms(100), 100)
        self.assertTrue(motion_effects_enabled())

        REDUCE_MOTION.set_enabled(True)
        self.assertEqual(theme.get_animation_tick_ms(100), 300)
        self.assertFalse(motion_effects_enabled())


class TestReduceMotionAnimations(unittest.TestCase):
    def tearDown(self) -> None:
        REDUCE_MOTION.set_enabled(False)

    def test_base_auto_play_uses_reduced_motion_interval(self) -> None:
        from PyQt6.QtWidgets import QApplication
        from animation_modals.base import CryptoAnimationWindow

        class _Window(CryptoAnimationWindow):
            def _init_content(self) -> None:
                pass

            def _render_step(self, step_idx: int) -> None:
                pass

            def _show_match_result(self) -> None:
                pass

        REDUCE_MOTION.set_enabled(True)
        w = _Window("Test", total_steps=2)
        w.show()
        QApplication.processEvents()
        self.assertEqual(w._timer.interval(), w.speed_ms * 3)
        w.close()

    def test_prime_sieve_disables_blink_timer(self) -> None:
        from PyQt6.QtWidgets import QApplication
        from animation_modals.rsa.prime_sieve import _PrimeSieveWidget

        REDUCE_MOTION.set_enabled(True)
        w = _PrimeSieveWidget()
        w.show()
        QApplication.processEvents()
        self.assertFalse(w._timer.isActive())
        self.assertFalse(w._blink)
        w.close()

    def test_rsa_key_builder_skips_pulse(self) -> None:
        from PyQt6.QtWidgets import QFrame
        from animation_modals.rsa.key_builder import _RSAKeyBuilderWidget

        REDUCE_MOTION.set_enabled(True)
        w = _RSAKeyBuilderWidget()
        target = QFrame(w)
        w._pulse(target, "accent_blue")
        self.assertIsNone(target.graphicsEffect())
        self.assertEqual(w._animations, [])

    def test_sha_diagram_disables_pulse_timer(self) -> None:
        from animation_modals.sha256.diagram_widget import _SHA256DiagramWidget

        REDUCE_MOTION.set_enabled(True)
        w = _SHA256DiagramWidget()
        w.set_data(
            ["00"] * 8, ["11"] * 8, "1", "2", "3", "4", 1,
        )
        self.assertFalse(w._pulse_timer.isActive())
        self.assertFalse(w._pulse_on)


# Not: MainWindow tabanlı a11y doğrulaması (buton accessibleName + menü
# tercih kalıcılığı) test_theme_integration.py içinde yapılır; o dosya
# MainWindow'u suite'in geç ve güvenli bir noktasında kurup yıkar. Burada
# erken (ilk dosya) MainWindow kurmak offscreen Qt'de kümülatif çökmeyi
# tetikliyordu.


if __name__ == "__main__":
    unittest.main()
