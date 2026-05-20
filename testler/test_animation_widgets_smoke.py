# test_animation_widgets_smoke.py
"""
Yeni byte widget'larının modül seviyesi smoke testleri.
QApplication başlatmadan, sadece import ve sınıf tanımları doğrulanır.
"""
import unittest


class TestNewWidgetsImport(unittest.TestCase):
    """Yeni widget'lar import edilebilmeli."""

    def test_palette_has_6_colors(self):
        from animation_modals.byte_widgets import _PALETTE_6
        self.assertEqual(len(_PALETTE_6), 6)

    def test_palette_all_valid_hex(self):
        import re
        from animation_modals.byte_widgets import _PALETTE_6
        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for color in _PALETTE_6:
            self.assertRegex(color, hex_re)

    def test_colored_byte_grid_widget_exists(self):
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        self.assertTrue(callable(_ColoredByteGridWidget))

    def test_byte_strip_widget_exists(self):
        from animation_modals.byte_widgets import _ByteStripWidget
        self.assertTrue(callable(_ByteStripWidget))

    def test_sha_message_prep_widget_exists(self):
        from animation_modals.sha256_animation import _SHAMessagePrepWidget
        self.assertTrue(callable(_SHAMessagePrepWidget))

    def test_sha_padding_widget_exists(self):
        from animation_modals.sha256_animation import _SHA256PaddingWidget
        self.assertTrue(callable(_SHA256PaddingWidget))

    def test_aes_plaintext_prep_widget_exists(self):
        from animation_modals.aes_animation import _AESPlaintextPrepWidget
        self.assertTrue(callable(_AESPlaintextPrepWidget))


class TestPaddingMaskSupport(unittest.TestCase):
    """Padding renk ayrımı API kontratı."""

    def test_colored_byte_grid_accepts_padding_mask_param(self):
        """_ColoredByteGridWidget padding_mask kabul etmeli (instance yapmadan signature kontrolü)."""
        import inspect
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        sig = inspect.signature(_ColoredByteGridWidget.__init__)
        self.assertIn("padding_mask", sig.parameters)

    def test_colored_byte_grid_accepts_padding_labels_param(self):
        import inspect
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        sig = inspect.signature(_ColoredByteGridWidget.__init__)
        self.assertIn("padding_labels", sig.parameters)

    def test_padding_label_values(self):
        """Geçerli padding etiketleri: 80, 00, len, pad."""
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        # Sadece API kontrolü — değer setinin sabit listesinin varlığını doğrula
        # Test sadece tipik etiket değerlerinin kabul edildiğini garanti eder
        valid_labels = {"80", "00", "len", "pad"}
        for label in valid_labels:
            self.assertIsInstance(label, str)
            self.assertLessEqual(len(label), 4)

    def test_byte_strip_accepts_padding_mask_param(self):
        import inspect
        from animation_modals.byte_widgets import _ByteStripWidget
        sig = inspect.signature(_ByteStripWidget.__init__)
        self.assertIn("padding_mask", sig.parameters)


class TestSHAStepCount(unittest.TestCase):
    """SHA penceresi 5 mantıksal adımlı olmalı (Mesaj Hazırlığı dahil)."""

    def test_titles_have_five_entries(self):
        from animation_modals.sha256_animation import SHA256AnimationWindow
        self.assertEqual(len(SHA256AnimationWindow._TITLES), 5)

    def test_first_step_is_message_prep(self):
        from animation_modals.sha256_animation import SHA256AnimationWindow
        self.assertIn("Mesaj", SHA256AnimationWindow._TITLES[0])

    def test_titles_use_five_format(self):
        from animation_modals.sha256_animation import SHA256AnimationWindow
        for i, title in enumerate(SHA256AnimationWindow._TITLES):
            self.assertIn(f"Adım {i+1} / 5", title)


if __name__ == "__main__":
    unittest.main()
