# test_rsa_animation.py
"""
RSA animasyon modülünün matematiksel invariantlarını doğrular.
Demo değerleri her RSAAnimationWindow açılışında _reseed_demo() ile
rastgele yenilenir, bu yüzden testler SPESİFİK SAYI değil INVARIANT
tabanlı yazılmıştır.

PyQt UI bileşenleri çalışma zamanında test edilemez (QApplication gerekir);
bu yüzden burada modül seviyesindeki invariantları kontrol ederiz.
"""
import unittest


class TestRSAAnimationConstants(unittest.TestCase):

    def test_demo_values_are_internally_consistent(self):
        """Modül seviyesi RSA sabitleri kendi içinde tutarlı:
           n = p·q,  φ = (p-1)(q-1),  e·d ≡ 1 (mod φ)."""
        from animation_modals import rsa_animation as rsa
        self.assertEqual(rsa._N, rsa._P * rsa._Q)
        self.assertEqual(rsa._PHI, (rsa._P - 1) * (rsa._Q - 1))
        self.assertEqual((rsa._E * rsa._D) % rsa._PHI, 1)

    def test_demo_primes_in_pool(self):
        """p ve q, _PRIME_POOL'dan iki farklı asal olmalı."""
        from animation_modals import rsa_animation as rsa
        self.assertIn(rsa._P, rsa._PRIME_POOL)
        self.assertIn(rsa._Q, rsa._PRIME_POOL)
        self.assertNotEqual(rsa._P, rsa._Q)

    def test_reseed_demo_preserves_invariants(self):
        """_reseed_demo() çağrılarından sonra invariantlar hâlâ tutmalı."""
        from animation_modals import rsa_animation as rsa
        for _ in range(5):
            rsa._reseed_demo()
            self.assertEqual(rsa._N, rsa._P * rsa._Q)
            self.assertEqual(rsa._PHI, (rsa._P - 1) * (rsa._Q - 1))
            self.assertEqual((rsa._E * rsa._D) % rsa._PHI, 1)
            # m = 65 her zaman < n olmalı (encryption tour için)
            self.assertGreater(rsa._N, 65)

    def test_reseed_demo_function_exists(self):
        """_reseed_demo ve _PRIME_POOL modülde bulunmalı — kullanıcı her
        demo açılışında farklı (p, q) görmek için."""
        from animation_modals import rsa_animation as rsa
        self.assertTrue(hasattr(rsa, "_reseed_demo"))
        self.assertTrue(hasattr(rsa, "_PRIME_POOL"))
        self.assertGreater(len(rsa._PRIME_POOL), 10)  # yeterli çeşitlilik

    def test_eea_steps_invariant_holds(self):
        """_eea_steps cari (_PHI, _E) için EEA invariantını sağlamalı:
        GCD=1 satırının t değeri mod φ alınınca _D'ye eşit olur."""
        from animation_modals.rsa_animation import _eea_steps, _PHI, _E, _D
        rows = _eea_steps(_PHI, _E)
        # Seed satırları (her zaman aynı yapıda)
        self.assertEqual(rows[0], (0, 0, _PHI, 1, 0))
        self.assertEqual(rows[1], (1, 0, _E, 0, 1))
        # GCD = 1 satırından (terminatörden bir önceki) t alınır → d
        gcd_row = next(row for row in rows if row[2] == 1)
        t = gcd_row[4]
        self.assertEqual(t % _PHI, _D)


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
