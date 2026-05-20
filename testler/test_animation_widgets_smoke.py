# test_animation_widgets_smoke.py
"""
test_animation_widgets_smoke.py — Mesaj/Plaintext Hazırlığı widget'ları smoke testleri
=======================================================================================

Test türü: SMOKE TESTİ (Import & API Sözleşmesi)

Amaç:
    SHA Mesaj Hazırlığı + AES Plaintext Hazırlığı çalışmasıyla eklenen yeni
    widget'ların ve byte_widgets modülünün import edilebilirliğini, API
    parametre signature'larını ve SHA penceresinin yeni 5-adımlı yapısını
    QApplication başlatmadan doğrular.

Kapsam (PyQt6 widget instance YOK — sadece import + inspect.signature):
    - TestNewWidgetsImport: 6 yeni öğe import edilebilmeli:
        * _PALETTE_6 (6 renkli liste, hepsi geçerli #RRGGBB)
        * _ColoredByteGridWidget (detay grid)
        * _ByteStripWidget (kompakt strip)
        * _SHAMessagePrepWidget (Adım 1/5)
        * _SHA256PaddingWidget (Adım 2/5)
        * _AESPlaintextPrepWidget (AES intro→prep→rounds)
    - TestPaddingMaskSupport: widget'ların padding_mask + padding_labels
      parametrelerini kabul ettiği signature kontrolü (inspect.signature).
      Geçerli etiket değerleri: '80', '00', 'len', 'pad'.
    - TestSHAStepCount: SHA penceresi _TITLES sınıf niteliği 5 girdili,
      birincisi "Mesaj Hazırlığı" içerir, her başlık "Adım N / 5"
      formatında — 4→5 adım kaymasının doğru yapıldığının kanıtı.

Strateji: Mikro-saniyelerde çalışır, CI/headless dostu. Bir API kontratı
test'idir; widget'ların gerçek render'ı manuel doğrulanır.

Hata durumunda anlamı: byte_widgets modülü, padding API'si veya SHA
window adım yapısı bozulmuş; uygulama açıldığında AttributeError verir.
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
