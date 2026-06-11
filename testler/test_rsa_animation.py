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
          2. Mesaj m geçerli: 2 ≤ m < n VE gcd(m, n) = 1 (doğru RSA örneği;
             m artık sabit 65 değil, her açılışta rastgele seçilir)
        Kullanıcı pencereyi defalarca açtığında her seferde MATEMATIK
        doğru kalır ve m → c → m' döngüsü doğru çalışır."""
        from math import gcd
        import animation_modals.rsa.helpers as rsa
        for _ in range(5):
            rsa._reseed_demo()
            self.assertEqual(rsa._N, rsa._P * rsa._Q)
            self.assertEqual(rsa._PHI, (rsa._P - 1) * (rsa._Q - 1))
            self.assertEqual((rsa._E * rsa._D) % rsa._PHI, 1)
            # m geçerli aralıkta ve n ile aralarında asal olmalı
            self.assertGreaterEqual(rsa._M, 2)
            self.assertLess(rsa._M, rsa._N)
            self.assertEqual(gcd(rsa._M, rsa._N), 1)

    def test_encrypt_decrypt_roundtrip_recovers_m(self):
        """Alt tür: BİRİM (RSA tur doğruluğu — pozitif).
        Rastgele m için c = m^e mod n ve m' = c^d mod n hesaplanınca
        m' == m olmalı (RSA bire-bir). gcd(m,n)=1 koşulu bunu garanti eder;
        m → c → m' döngüsünün her demo değeriyle çalıştığının kanıtı."""
        import animation_modals.rsa.helpers as rsa
        for _ in range(5):
            rsa._reseed_demo()
            c = pow(rsa._M, rsa._E, rsa._N)
            m_prime = pow(c, rsa._D, rsa._N)
            self.assertEqual(m_prime, rsa._M)

    def test_reseed_demo_varies_message(self):
        """Alt tür: BİRİM (çeşitlilik — negatif/regresyon).
        m artık sabit DEĞİL: birçok reseed sonrası en az iki farklı m
        görülmeli. Hep aynı değer çıkarsa (eski 65 sabiti gibi) kullanıcı
        'değişen RSA' deneyimi yaşamaz."""
        import animation_modals.rsa.helpers as rsa
        seen = set()
        for _ in range(20):
            rsa._reseed_demo()
            seen.add(rsa._M)
        self.assertGreater(len(seen), 1, "m her açılışta değişmeli")

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

    def test_titles_use_two_space_separator(self):
        """Alt tür: BİRİM (ayraç biçimi — pozitif).
        Adım numarasından sonra ayraç olarak '—' uzun tire DEĞİL, iki
        boşluk kullanılır: 'Adım N / 8  Başlık'. Kullanıcı isteği gereği
        tire kaldırıldı; biçim 'Adım N / 8' + iki boşluk + başlık."""
        from animation_modals import RSAAnimationWindow
        for i, title in enumerate(RSAAnimationWindow._TITLES):
            self.assertIn(f"Adım {i+1} / 8  ", title, f"index {i}: '{title}'")

    def test_titles_have_no_emdash_separator(self):
        """Alt tür: BİRİM (ayraç biçimi — negatif/regresyon).
        Adım başlıklarında uzun tire '—' artık bulunmamalı. Eski biçim
        ('Adım N / 8 — Başlık') geri sızarsa bu test kırılır."""
        from animation_modals import RSAAnimationWindow
        for title in RSAAnimationWindow._TITLES:
            self.assertNotIn("—", title, f"tire kaldırılmalı: '{title}'")

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

    def test_encrypt_decrypt_widget_renders_long_values(self):
        """Alt tür: BİRİM (kutu genişliği regresyonu — render).
        4 haneli m/c/m' değerleriyle bile widget hatasız boyanmalı. Kutu
        genişliği QFontMetrics ile içeriğe göre ayarlandığından (Y3),
        "m' = 8632 ✓" gibi uzun etiket kutuya sığar; render istisna atmaz."""
        from PyQt6.QtGui import QPixmap
        import animation_modals.rsa.key_match as rsa
        w = rsa._RSAEncryptDecryptWidget()
        w.resize(880, 260)
        w._M, w._C, w._M_PRIME = 8632, 1234, 8632  # en uzun durum
        w._tick = w._T_MATCH_END
        w.render(QPixmap(880, 260))  # istisna fırlatırsa fail

    def test_box_font_fits_worst_case_label(self):
        """Alt tür: BİRİM (sığma garantisi — pozitif).
        En uzun kutu etiketi "m' = 8632 ✓", hesaplanan box_w içine seçilen
        adaptif punto ile sığmalı (taşma yok). box_w üst sınırı 152;
        QFontMetrics ile 11→8pt arasında sığan punto bulunmalı."""
        from PyQt6.QtGui import QFont, QFontMetrics
        label = "m' = 8632 ✓"
        box_w = 152
        fits = any(
            QFontMetrics(QFont("Courier New", pt, QFont.Weight.Bold))
            .horizontalAdvance(label) <= box_w - 10
            for pt in (11, 10, 9, 8)
        )
        self.assertTrue(fits, "En uzun etiket adaptif punto ile kutuya sığmalı")


class TestDERByteFlowAnimation(unittest.TestCase):
    """Adım 6 DER/Base64 uzamsal montaj animasyonu (_DERByteFlowWidget)
    (Alt kategori: BİRİM — runtime, conftest offscreen QApplication ile).

    Bu widget tick tabanlıdır: _tick arttıkça kutular/aşamalar açılır.
    Testler hem açılış zamanlamasının tutarlılığını hem de her tikte
    hatasız çizimi doğrular."""

    @staticmethod
    def _make(alice_b64="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA"):
        from animation_modals.rsa.der_widget import _DERByteFlowWidget
        w = _DERByteFlowWidget(alice_b64)
        w.resize(640, 860)
        return w

    def test_renders_all_ticks_without_error(self):
        """Alt tür: BİRİM (pozitif — render dayanıklılığı).
        0'dan son tikin ötesine kadar her tikte widget hatasız boyanmalı;
        kutu açılış mantığı (sayı→byte, DER montajı, bit-yeniden-gruplama,
        Aşama B, anahtarlar) hiçbir ara karede istisna atmamalı."""
        from PyQt6.QtGui import QPixmap
        w = self._make()
        for t in range(0, w._t_end + 3):
            w._tick = t
            w.render(QPixmap(640, 860))  # istisna fırlatırsa fail

    def test_schedule_is_monotonic(self):
        """Alt tür: BİRİM (invariant — zamanlama sırası).
        Aşama başlangıç tikleri kesin artan olmalı: sayılar < n < e <
        DER < Base64 (bit/grup) < Aşama B < anahtarlar < son. Sıra
        bozulursa bir aşama diğerinin üstüne biner."""
        w = self._make()
        order = [
            w._t_nums, w._t_n_start, w._t_e_start, w._t_der_start,
            w._t_b64, w._t_b64_bits, w._t_b64_groups,
            w._t_asama_b, w._t_keys, w._t_end,
        ]
        for a, b in zip(order, order[1:]):
            self.assertLess(a, b, f"zamanlama artan olmalı: {order}")

    def test_revealed_helper_bounds(self):
        """Alt tür: BİRİM (pozitif+negatif — açığa çıkma sayacı).
        _revealed(start, count): start'tan önce 0; start'tan yeterince
        sonra tam count döndürür ve count'u asla aşmaz."""
        w = self._make()
        w._tick = 0
        self.assertEqual(w._revealed(5, 4), 0, "start öncesi 0 olmalı")
        w._tick = 5 + w._TICKS_PER_BOX * 4 + 10
        self.assertEqual(w._revealed(5, 4), 4, "yeterince sonra tam count")
        self.assertLessEqual(w._revealed(5, 4), 4, "count aşılmamalı")

    def test_empty_alice_b64_renders(self):
        """Alt tür: BİRİM (negatif/kenar — eksik gerçek anahtar).
        Standalone/test bağlamında Alice b64 boş gelebilir; Aşama B 3 bayt
        çözemese de widget son tikte hatasız boyanmalı (boş b64 düşüşü)."""
        from PyQt6.QtGui import QPixmap
        w = self._make(alice_b64="")
        w._tick = w._t_end
        w.render(QPixmap(640, 860))  # istisna fırlatırsa fail

    def test_base64_label_clearance_prevents_overlap(self):
        """Alt tür: BİRİM (yerleşim regresyonu — üst üste binme).
        Base64 bölümünde 'bayt N' etiketli kutu satırı, bölüm başlığıyla
        çakışmamalı. Etiket kutunun _LABEL_DY px üstüne yazıldığından, satır
        öncesi ayrılan boşluk (_LABEL_CLEARANCE) bunu KARŞILAMALI."""
        w = self._make()
        self.assertGreaterEqual(
            w._LABEL_CLEARANCE, w._LABEL_DY,
            "Etiketli satır boşluğu, etiketin kutu üstüne çıkışını örtmeli",
        )

    def test_tick_pacing_is_followable(self):
        """Alt tür: BİRİM (pozitif — temponun takip edilebilirliği).
        Kutu açılış temposu (_TICK_MS) en az 60 ms olmalı ki öğrenci her
        baytın yerleşmesini izleyebilsin; ayrıca kutu başına ≥2 tik ile
        açılış 'atlamasız' olur."""
        w = self._make()
        self.assertGreaterEqual(w._TICK_MS, 60)
        self.assertGreaterEqual(w._TICKS_PER_BOX, 2)


if __name__ == "__main__":
    unittest.main()
