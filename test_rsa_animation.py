# test_rsa_animation.py
"""
RSA animasyon modülünün tezdeki değerlerle hizalandığını doğrular.
PyQt UI bileşenleri çalışma zamanında test edilemez (QApplication gerekir);
bu yüzden burada modül seviyesindeki invariantları kontrol ederiz.
"""
import unittest


class TestRSAAnimationConstants(unittest.TestCase):

    def test_thesis_values_are_fixed(self):
        """Tezdeki Tablo tab:RSAExample değerleriyle birebir uymalı."""
        from animation_modals import rsa_animation as rsa
        self.assertEqual(rsa._P, 61)
        self.assertEqual(rsa._Q, 53)
        self.assertEqual(rsa._N, 3233)
        self.assertEqual(rsa._PHI, 3120)
        self.assertEqual(rsa._E, 17)
        self.assertEqual(rsa._D, 2753)

    def test_rsa_invariant_holds(self):
        """e · d ≡ 1 (mod φ) RSA tanımının temel invariantı."""
        from animation_modals import rsa_animation as rsa
        self.assertEqual((rsa._E * rsa._D) % rsa._PHI, 1)

    def test_random_seed_function_removed(self):
        """_reseed_demo modülde olmamalı — sabit tez değerleri var."""
        from animation_modals import rsa_animation as rsa
        self.assertFalse(hasattr(rsa, "_reseed_demo"),
                         "_reseed_demo kaldırılmış olmalı")
        self.assertFalse(hasattr(rsa, "_PRIME_POOL"),
                         "_PRIME_POOL kaldırılmış olmalı")

    def test_eea_steps_for_thesis_values(self):
        """φ=3120, e=17 için EEA çıktısının ilk satırları sabittir.

        Tezdeki Algoritma algo:EEA ile q, r, s, t kolonlarının
        deterministik olduğunu doğrular.
        """
        from animation_modals.rsa_animation import _eea_steps, _PHI, _E, _D
        rows = _eea_steps(_PHI, _E)
        # İlk iki satır seed: (0, 0, 3120, 1, 0) ve (1, 0, 17, 0, 1)
        self.assertEqual(rows[0], (0, 0, 3120, 1, 0))
        self.assertEqual(rows[1], (1, 0, 17, 0, 1))
        # i=2 için: q=⌊3120/17⌋=183, r=3120-183·17=9, s=1, t=-183
        self.assertEqual(rows[2], (2, 183, 9, 1, -183))
        # GCD=1 satırı → t değeri pozitif moda alınınca _D olmalı
        gcd_row = next(row for row in rows if row[2] == 1)
        t = gcd_row[4]
        self.assertEqual(t % _PHI, _D)  # _D = 2753


class TestRSAAnimationStructure(unittest.TestCase):
    """RSAAnimationWindow'un 8 adımlı yapısını doğrular (UI başlatmadan)."""

    def test_titles_have_eight_entries(self):
        from animation_modals.rsa_animation import RSAAnimationWindow
        self.assertEqual(len(RSAAnimationWindow._TITLES), 8)

    def test_captions_have_eight_entries(self):
        from animation_modals.rsa_animation import RSAAnimationWindow
        self.assertEqual(len(RSAAnimationWindow._CAPTIONS), 8)

    def test_titles_use_eight_format(self):
        """Her adım başlığı 'Adım N / 8' formatında olmalı."""
        from animation_modals.rsa_animation import RSAAnimationWindow
        for i, title in enumerate(RSAAnimationWindow._TITLES):
            self.assertIn(f"Adım {i+1} / 8", title,
                          f"index {i}: '{title}'")

    def test_eighth_title_is_encryption_tour(self):
        from animation_modals.rsa_animation import RSAAnimationWindow
        self.assertIn("Şifreleme", RSAAnimationWindow._TITLES[7])

    def test_encrypt_decrypt_widget_exists(self):
        from animation_modals import rsa_animation as rsa
        self.assertTrue(hasattr(rsa, "_RSAEncryptDecryptWidget"))


if __name__ == "__main__":
    unittest.main()
