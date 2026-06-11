"""AES-GCM keystream referans diyaloğu ve düğme bağlantısı testleri."""
from __future__ import annotations

import unittest

from animation_modals.aes.keystream_dialog import _KeystreamReferenceDialog
from animation_modals.base import ANIM_COLORS
from arayuz.theme import MANAGER


class TestKeystreamReferenceDialog(unittest.TestCase):
    """Keystream/GCM açıklama penceresinin gerçek değer ve tema sözleşmesini sınar."""

    def setUp(self):
        self._original_theme = MANAGER.mode
        self.keystream = bytes(range(16))
        self.nonce = bytes(range(12))

    def tearDown(self):
        MANAGER.set_mode(self._original_theme)

    def test_contains_real_keystream_and_core_gcm_explanation(self):
        """Diyalog gerçek baytları, XOR kullanımını ve AEAD/tag açıklamasını göstermeli."""
        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)
        all_text = " ".join(
            label.text()
            for label in (
                dialog.keystream_hex_label,
                dialog.generation_label,
                dialog.usage_label,
                dialog.gcm_label,
            )
        )

        self.assertIn(self.keystream.hex(" "), all_text)
        self.assertIn("nonce", all_text)
        self.assertIn("keystream ⊕ mesaj", all_text)
        self.assertIn("AEAD", all_text)
        self.assertIn("16 byte tag", all_text)
        self.assertEqual(dialog.generation_widget.counter_block, self.nonce + b"\x00\x00\x00\x02")
        self.assertEqual(dialog.generation_widget.keystream, self.keystream)

    def test_generation_widget_animates_counter_to_real_keystream(self):
        """Üretim görseli gerçek sayaç bloğunu 14 round üzerinden keystream'e bağlamalı."""
        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)
        widget = dialog.generation_widget

        widget.start()
        for _ in range(widget._TOTAL_TICKS):
            widget._advance()

        self.assertEqual(widget._phase, 2)
        self.assertFalse(widget._timer.isActive())

    def test_dialog_restyles_when_theme_changes(self):
        """Açık diyalog tema değişiminde yeni panel rengini kullanmalı."""
        MANAGER.set_mode("dark")
        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)
        dark_style = dialog.styleSheet()

        MANAGER.set_mode("light")

        self.assertNotEqual(dialog.styleSheet(), dark_style)
        self.assertIn(ANIM_COLORS["bg_panel"], dialog.styleSheet())

    def test_keystream_button_opens_dialog_with_round_result(self):
        """XOR sayfasındaki keystream düğmesi gerçek round sonucunu diyaloğa aktarmalı."""
        from animation_modals import AESAnimationWindow

        window = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"mesaj",
            expected_ct_hex="00" * 5,
            nonce=self.nonce,
        )

        window._keystream_btn.click()

        self.assertEqual(
            window._keystream_dialog.keystream,
            bytes.fromhex(window._final_block_hex),
        )
        self.assertEqual(window._keystream_dialog.nonce, self.nonce)

    def test_gcm_prep_keystream_button_opens_same_reference(self):
        """GCM hazırlık ekranındaki S-Box tarzı düğme de aynı gerçek referansı açmalı."""
        from animation_modals import AESAnimationWindow

        window = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"mesaj",
            expected_ct_hex="00" * 5,
            nonce=self.nonce,
        )

        window._gcm_prep_keystream_btn.click()

        self.assertEqual(
            window._keystream_dialog.keystream,
            bytes.fromhex(window._final_block_hex),
        )


if __name__ == "__main__":
    unittest.main()
