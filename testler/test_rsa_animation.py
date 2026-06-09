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
        """Alt tür: INVARIANT (3 RSA matematik bağıtı tek testte).
        Modül seviyesi demo sabitleri ŞU AN itibariyle tutarlı:
          1. n = p · q                    (modülüs tanımı)
          2. ϕ(n) = (p-1)(q-1)            (Euler totient)
          3. e · d ≡ 1 (mod ϕ)            (RSA anahtar bağıtı)
        Modül import edildiği anda _reseed_demo() çağrılır; bu test
        ilk çağrının çıktısının doğru olduğunu garanti eder."""
        import animation_modals.rsa.helpers as rsa
        self.assertEqual(rsa._N, rsa._P * rsa._Q)
        self.assertEqual(rsa._PHI, (rsa._P - 1) * (rsa._Q - 1))
        self.assertEqual((rsa._E * rsa._D) % rsa._PHI, 1)

    def test_demo_primes_in_pool(self):
        """Alt tür: INVARIANT (asal seçim havuzu).
        Seçilen p ve q değerleri _PRIME_POOL listesinde bulunmalı VE
        birbirinden farklı olmalı. Aynı asal seçilirse RSA çökecek
        (ϕ = (p-1)² olur, güvenlik bozulur)."""
        import animation_modals.rsa.helpers as rsa
        self.assertIn(rsa._P, rsa._PRIME_POOL)
        self.assertIn(rsa._Q, rsa._PRIME_POOL)
        self.assertNotEqual(rsa._P, rsa._Q)

    def test_reseed_demo_preserves_invariants(self):
        """Alt tür: INVARIANT (idempotency / tekrar tutarlılığı).
        _reseed_demo() 5 ardışık çağrı yapılınca her seferinde:
          1. RSA matematik bağıtları (üst test'teki 3 invariant) korunur
          2. n > 65 (animasyon mesajı m=65 < n garantisi — şifreleme turu
             için gerekli; aksi halde 65^e mod n çalışmaz)
        Kullanıcı pencereyi defalarca açtığında her seferde MATEMATIK
        doğru kalır."""
        import animation_modals.rsa.helpers as rsa
        for _ in range(5):
            rsa._reseed_demo()
            self.assertEqual(rsa._N, rsa._P * rsa._Q)
            self.assertEqual(rsa._PHI, (rsa._P - 1) * (rsa._Q - 1))
            self.assertEqual((rsa._E * rsa._D) % rsa._PHI, 1)
            # m = 65 her zaman < n olmalı (encryption tour için)
            self.assertGreater(rsa._N, 65)

    def test_reseed_demo_function_exists(self):
        """Alt tür: SMOKE (API varlığı + çeşitlilik kontrolü).
        _reseed_demo ve _PRIME_POOL modülde tanımlı. _PRIME_POOL >10
        eleman içermeli — yetersiz çeşitlilikte aynı (p,q) çiftleri
        sık tekrarlanır ve kullanıcı 'rastgele' deneyimi yaşamaz."""
        import animation_modals.rsa.helpers as rsa
        self.assertTrue(hasattr(rsa, "_reseed_demo"))
        self.assertTrue(hasattr(rsa, "_PRIME_POOL"))
        self.assertGreater(len(rsa._PRIME_POOL), 10)  # yeterli çeşitlilik

    def test_eea_steps_invariant_holds(self):
        """Alt tür: BİRİM (Extended Euclidean Algorithm doğruluğu).
        _eea_steps(ϕ, e) fonksiyonu EEA tablosunu üretir:
          - Satır 0: seed (0, 0, ϕ, 1, 0)
          - Satır 1: seed (1, 0, e, 0, 1)
          - Sonraki satırlar: standart EEA iterasyonu
          - GCD=1 olduğu satırda t değeri: t mod ϕ = d (RSA özel üs)
        Bu test EEA fonksiyonunun gerçekten doğru RSA d'sini ürettiğini
        cebirsel olarak kanıtlar."""
        from animation_modals.rsa.helpers import _eea_steps, _PHI, _E, _D
        rows = _eea_steps(_PHI, _E)
        # Seed satırları (her zaman aynı yapıda)
        self.assertEqual(rows[0], (0, 0, _PHI, 1, 0))
        self.assertEqual(rows[1], (1, 0, _E, 0, 1))
        # GCD = 1 satırından (terminatörden bir önceki) t alınır → d
        gcd_row = next(row for row in rows if row[2] == 1)
        t = gcd_row[4]
        self.assertEqual(t % _PHI, _D)


class TestRSAAnimationStructure(unittest.TestCase):
    """RSAAnimationWindow'un 8 adımlı yapısını doğrular (UI başlatmadan)
    (Alt kategori: SMOKE — sınıf attribute yapısı)."""

    def test_titles_have_eight_entries(self):
        """Alt tür: SMOKE (yapısal sözleşme).
        _TITLES sınıf niteliği tam 8 girdi. Adım sayısı değişirse
        progress bar veya _render_step kayar."""
        from animation_modals import RSAAnimationWindow
        self.assertEqual(len(RSAAnimationWindow._TITLES), 8)

    def test_captions_have_eight_entries(self):
        """Alt tür: SMOKE (eşleşen alt başlık).
        _CAPTIONS (her adımın açıklayıcı alt başlığı) da 8 girdi —
        _TITLES'la eşleşmeli. Eşleşmezse zip(titles, captions) kayar."""
        from animation_modals import RSAAnimationWindow
        self.assertEqual(len(RSAAnimationWindow._CAPTIONS), 8)

    def test_titles_use_eight_format(self):
        """Alt tür: SMOKE (format tutarlılığı).
        Her başlıkta 'Adım N / 8' (N: 1..8) ifadesi geçmeli. Format
        yanlış olursa kullanıcı yanlış toplam görür."""
        from animation_modals import RSAAnimationWindow
        for i, title in enumerate(RSAAnimationWindow._TITLES):
            self.assertIn(f"Adım {i+1} / 8", title,
                          f"index {i}: '{title}'")

    def test_eighth_title_is_encryption_tour(self):
        """Alt tür: SMOKE (sıralama doğrulaması).
        Son adım (index 7) 'Şifreleme' içerir — m → c → m' turu sayfası.
        Bu sıra docstring + tez içeriğiyle eşleşmek zorunda."""
        from animation_modals import RSAAnimationWindow
        self.assertIn("Şifreleme", RSAAnimationWindow._TITLES[7])

    def test_encrypt_decrypt_widget_exists(self):
        """Alt tür: SMOKE (sınıf varlığı).
        _RSAEncryptDecryptWidget — Adım 8 sayfasının ana widget'ı —
        modülde tanımlı. Yeniden adlandırılırsa Adım 8 boş çıkar."""
        import animation_modals.rsa.key_match as rsa
        self.assertTrue(hasattr(rsa, "_RSAEncryptDecryptWidget"))


if __name__ == "__main__":
    unittest.main()
