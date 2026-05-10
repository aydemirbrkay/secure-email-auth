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


if __name__ == "__main__":
    unittest.main()
