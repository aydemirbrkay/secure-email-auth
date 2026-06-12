"""SHA-256 mesaj genişletme (W[16]) bit-düzeyi drill-down sihirbazı testleri.

Test türü: BİRİM + SMOKE (PyQt widget davranışı + çizim güvenliği).
"""
from __future__ import annotations

import unittest

from animation_modals.sha256.w_detail_dialog import (
    _WDetailDialog,
    _SCENE_COUNT,
)
from animation_modals.sha256_pure import sha256_steps
from arayuz.theme import MANAGER


class TestSHAWDetailDialog(unittest.TestCase):

    def setUp(self):
        self._original_theme = MANAGER.mode
        self._data = sha256_steps(b"Hello World")
        self._detail = self._data["w_detail"]

    def tearDown(self):
        MANAGER.set_mode(self._original_theme)

    def test_dialog_carries_real_w_detail(self):
        dialog = _WDetailDialog(self._detail)
        self.assertEqual(dialog.wizard.detail["result"], self._detail["result"])
        self.assertEqual(dialog.wizard.detail["i"], 16)

    def test_wizard_is_manual_and_advances_on_click(self):
        dialog = _WDetailDialog(self._detail)
        wizard = dialog.wizard
        wizard.start()
        self.assertEqual(wizard._scene(), 0)
        self.assertFalse(hasattr(wizard, "_timer"))
        for _ in range(_SCENE_COUNT + 3):
            wizard._advance_scene()
        self.assertEqual(wizard._scene(), _SCENE_COUNT - 1)

    def test_all_scenes_paint_without_error(self):
        dialog = _WDetailDialog(self._detail)
        wizard = dialog.wizard
        wizard.resize(900, 440)
        for scene in range(_SCENE_COUNT):
            wizard.jump_to_scene(scene)
            self.assertEqual(wizard._scene(), scene)
            wizard.grab()

    def test_dialog_restyles_on_theme_change(self):
        from animation_modals.base import ANIM_COLORS
        MANAGER.set_mode("dark")
        dialog = _WDetailDialog(self._detail)
        dark = dialog.styleSheet()
        MANAGER.set_mode("light")
        self.assertNotEqual(dialog.styleSheet(), dark)
        self.assertIn(ANIM_COLORS["bg_panel"], dialog.styleSheet())


class TestSHAWDetailButton(unittest.TestCase):

    def test_wexpand_button_opens_dialog_with_real_detail(self):
        from animation_modals.sha256.window import SHA256AnimationWindow
        import hashlib

        msg = "Hello World"
        window = SHA256AnimationWindow(
            message=msg,
            expected_hash=hashlib.sha256(msg.encode()).hexdigest(),
        )
        self.assertTrue(window._w_detail_btn.isEnabled())
        window._w_detail_btn.click()
        self.assertEqual(
            window._w_detail_dialog.wizard.detail["result"],
            window._data["w_detail"]["result"],
        )


if __name__ == "__main__":
    unittest.main()
