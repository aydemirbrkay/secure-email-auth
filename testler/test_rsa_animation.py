# test_rsa_animation.py
"""
test_rsa_animation.py — RSA animasyon matematiksel invariant testleri
======================================================================

Test türü: INVARIANT TESTİ (Matematiksel Sözleşme)

Amaç:
    RSA animasyon penceresinde gösterilen küçük demo değerleri
    (p, q, n, ϕ, e, d) her pencere açılışında _reseed_demo() çağrısıyla
    rastgele seçilir. Spesifik bir sayı sabit olmadığı için testler
    "şu sayı şu olmalı" değil "**her zaman şu matematiksel bağıt**
    sağlanmalı" diye yazılmıştır.

Kapsam:
    - n = p · q  (modülüs tanımı)
    - ϕ = (p-1)(q-1)  (Euler totient fonksiyonu)
    - e · d ≡ 1 (mod ϕ)  (RSA anahtar üretimi temel bağıtı)
    - p, q ∈ _PRIME_POOL ve p ≠ q
    - _reseed_demo() idempotency: 5 ardışık çağrı sonrası invariant'lar
      hâlâ tutuyor + m = 65 (animasyon mesajı) < n garantisi
    - _eea_steps doğru çalışıyor: GCD=1 satırından alınan t değeri,
      mod ϕ alınınca _D'ye eşit
    - RSAAnimationWindow 8 adımlı: _TITLES + _CAPTIONS 8'li listeler,
      her başlık "Adım N / 8" formatında, 8. adım "Şifreleme" içerir

Strateji: Modül seviyesi invariantlar — PyQt UI bileşenlerini instance
etmeden, _reseed_demo()'yu doğrudan çağırarak. QApplication gerekmez.

Hata durumunda anlamı: Reseed sonrası RSA matematiği bozuk; demo
gösteriminde m → c → m' tur'u doğru sonuç vermiyor.
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
