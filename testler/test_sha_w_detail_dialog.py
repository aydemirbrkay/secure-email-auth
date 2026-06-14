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
        # Öğretici (dinamik) indeks: gerçek veriyle aynı + operandları dolu.
        self.assertEqual(dialog.wizard.detail["i"], self._detail["i"])
        self.assertNotEqual(self._detail["w_i15"], "00000000")
        self.assertNotEqual(self._detail["w_i2"], "00000000")

    def test_dialog_has_minimize_button(self):
        """Harici W drill-down diyaloğu görev çubuğuna küçültülebilmeli."""
        from PyQt6.QtCore import Qt

        dialog = _WDetailDialog(self._detail)
        flags = dialog.windowFlags()

        self.assertTrue(flags & Qt.WindowType.WindowMinimizeButtonHint)
        self.assertTrue(flags & Qt.WindowType.WindowCloseButtonHint)

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

    def test_body_click_does_not_advance(self):
        from PyQt6.QtCore import QPointF, Qt as _Qt
        from PyQt6.QtGui import QMouseEvent
        dialog = _WDetailDialog(self._detail)
        wizard = dialog.wizard
        wizard.resize(900, 440)
        wizard.jump_to_scene(0)
        ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(400, 300),
                         _Qt.MouseButton.LeftButton, _Qt.MouseButton.LeftButton,
                         _Qt.KeyboardModifier.NoModifier)
        wizard.mousePressEvent(ev)
        self.assertEqual(wizard._scene(), 0)

    def test_nav_buttons_change_scene(self):
        dialog = _WDetailDialog(self._detail)
        self.assertEqual(dialog.wizard._scene(), 0)
        dialog._go_next()
        self.assertEqual(dialog.wizard._scene(), 1)
        dialog._go_prev()
        self.assertEqual(dialog.wizard._scene(), 0)

    def test_scene_titles_are_dynamic_to_index(self):
        """Strip başlıkları drilled W indeksinden türemeli (σ0(W[i-15]) vb.)."""
        dialog = _WDetailDialog(self._detail)
        i = self._detail["i"]
        self.assertIn(f"W[{i-15}]", dialog.wizard._titles[1])
        self.assertIn(f"W[{i-2}]", dialog.wizard._titles[2])

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
