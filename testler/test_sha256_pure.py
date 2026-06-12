# test_sha256_pure.py
"""
test_sha256_pure.py — animation_modals/sha256_pure modülü birim testleri
========================================================================

Test türü: BİRİM TESTİ (Unit Test)

Amaç:
    Saf-Python SHA-256 implementasyonunun standart kütüphane (hashlib.sha256)
    ile birebir aynı çıktıyı verdiğini doğrular. sha256_steps() animasyon
    için ara veri (round snapshot'ları, W expansion, padding adımları) da
    döndürür — bu testler bu verilerin yapısal bütünlüğünü de garanti eder.

Strateji:
    - Bilinen mesajlarla (örn. b"Hello World", boş mesaj) hash hesapla.
    - hashlib.sha256(msg).hexdigest() ile karşılaştır.
    - round_snapshots, w_expansion, initial_h, blocks_count gibi animasyon
      veri alanlarının varlığı ve doğru boyutlarda olduğunu kontrol et.
    - Animasyon yapı testleri (TestSHA256AnimationStructure): _MatchAssemblyWidget,
      _WExpansionWidget gibi sınıfların modülde tanımlı olduğu — refactor
      sonrası bozulma kontrolü için.

Hata durumunda anlamı: Saf SHA-256 implementasyonunda matematiksel bozukluk
veya animasyon arayüz kontratı kırılması.
"""
import hashlib
import unittest
from animation_modals.sha256_pure import sha256_steps

class TestSHA256Pure(unittest.TestCase):

    def test_final_hash_matches_hashlib(self):
        """Alt tür: BİRİM (kriptografik doğruluk — altın test).
        Pure-Python SHA-256 çıktısı, standart kütüphane hashlib.sha256()
        ile birebir aynı olmalı. Bu, implementasyonun matematiksel
        doğruluğunun en güçlü kanıtı."""
        msg = b"Hello World"
        result = sha256_steps(msg)
        expected = hashlib.sha256(msg).hexdigest()
        self.assertEqual(result["final_hash"], expected)

    def test_empty_message(self):
        """Alt tür: BİRİM (sınır koşulu — boş girdi).
        SHA-256(b'') = 'e3b0c4...' standardı. Boş mesajın özel bir
        çözüm yolu (özel padding) gerektirdiği için ayrı test edilir;
        bu test boş girdide crash veya yanlış sonuç olmadığını garantiler."""
        result = sha256_steps(b"")
        expected = hashlib.sha256(b"").hexdigest()
        self.assertEqual(result["final_hash"], expected)

    def test_initial_h_count(self):
        """Alt tür: BİRİM (sabitler — FIPS 180-4 H0..H7).
        Başlangıç hash değerleri (initial_h) tam 8 adet olmalı
        (H0, H1, ..., H7). Animasyondaki 8 satırlı register tablosu
        bu sözleşmeye dayanır."""
        result = sha256_steps(b"test")
        self.assertEqual(len(result["initial_h"]), 8)

    def test_round_snapshots_present(self):
        """Alt tür: BİRİM (animasyon veri varlığı).
        round_snapshots alanı dönüşte bulunmalı ve boş olmamalı.
        Animasyonun 'Sıkıştırma Round Diyagramı' sayfası bu listenin
        her elemanını ayrı bir alt-adım olarak gösterir."""
        result = sha256_steps(b"test")
        self.assertIn("round_snapshots", result)
        self.assertGreater(len(result["round_snapshots"]), 0)

    def test_blocks_count(self):
        """Alt tür: BİRİM (blok bölme).
        'Hello World' 11 byte → padding sonrası 64 byte → 1 blok.
        blocks_count alanı doğru hesaplanmalı; bu sayı padding
        sayfasındaki blok navigasyonunu (◀/▶) tetikler."""
        result = sha256_steps(b"Hello World")
        self.assertEqual(result["blocks_count"], 1)

    def test_binary_preview_present(self):
        """Alt tür: BİRİM (eski API alan varlığı).
        binary_preview alanı mevcut, boş değil. SHA Padding sayfasının
        eski metin tabanlı önizlemesi bu alanı kullanıyordu; backward
        compatibility için korunur."""
        result = sha256_steps(b"Hi")
        self.assertIn("binary_preview", result)
        self.assertGreater(len(result["binary_preview"]), 0)

    def test_round_snapshots_have_rich_data(self):
        """Alt tür: BİRİM (snapshot iç yapı sözleşmesi).
        Her round_snapshot şu alanları içermeli: w (mesaj genişlet
        ifadesi), k (round sabiti), t1+t2 (geçici hesaplar). Hepsi
        8-karakterlik 32-bit hex string. Round diyagramı sayfası bu
        4 alanı ayrı kutularda gösterir."""
        result = sha256_steps(b"Hello World")
        snap = result["round_snapshots"][0]
        self.assertIn("w", snap)
        self.assertIn("k", snap)
        self.assertIn("t1", snap)
        self.assertIn("t2", snap)
        # Her değer 8 karakterlik hex string olmalı
        self.assertEqual(len(snap["w"]), 8)
        self.assertEqual(len(snap["k"]), 8)

    def test_round_snapshots_are_at_expected_rounds(self):
        """Alt tür: BİRİM (snapshot örnekleme stratejisi).
        SHA-256 64 round; tümünü göstermek aşırı. Pedagojik olarak
        9 strategik round (1, 9, 17, 25, 33, 41, 49, 57, 64) seçilir
        — başlangıç + her 8 round + son round. Bu sıra docstring'le
        eşleşmeli, aksi halde animasyon mantığı bozulur."""
        result = sha256_steps(b"Hello World")
        rounds = [s["round"] for s in result["round_snapshots"]]
        self.assertEqual(rounds, [1, 9, 17, 25, 33, 41, 49, 57, 64])

    def test_w_expansion_exposes_operand_and_result(self):
        """Alt tür: BİRİM (mesaj genişlet veri sözleşmesi).
        W[16..31] genişletmesinde σ0/σ1 fonksiyonları için animasyon
        HEM operandı (W[i-15], W[i-2]) HEM de sonucu (s0, s1) ayrı
        alanlarda göstermeli. Aynı alanı paylaşırlarsa 'σ0(sonuç)'
        gibi yanıltıcı bir görüntü çıkar — operand→fonksiyon→sonuç
        akışı görsel olarak çözülmez.
        Ek olarak: en az 1 satırda σ0 sonucu operandtan farklı olmalı
        (her ikisi de aynıysa σ fonksiyonu hiç uygulanmamış demektir)."""
        result = sha256_steps(b"Hello World")
        exp = result["w_expansion"]
        self.assertIsNotNone(exp)
        self.assertEqual(len(exp), 16)  # 16..31 arası 16 satır
        required = {"i", "w_i16", "w_i15", "s0", "w_i7", "w_i2", "s1", "result"}
        for row in exp:
            self.assertTrue(required.issubset(row.keys()), row)
            # Hepsi 8 karakterlik hex string (32-bit) olmalı
            for k in ("w_i16", "w_i15", "s0", "w_i7", "w_i2", "s1", "result"):
                self.assertEqual(len(row[k]), 8)
                int(row[k], 16)
        # En az bir satırda σ fonksiyonunun operanddan farklı sonuç
        # üretmesi beklenir (aksi hâlde operand/sonuç ayrımı kaybolmuştur).
        self.assertTrue(any(row["w_i15"] != row["s0"] for row in exp))

    def test_w_detail_is_real_sigma_internals(self):
        """Alt tür: BİRİM (W bit düzeyi drill-down veri sözleşmesi — DOĞRULUK).
        w_detail, W[16]'nın σ0/σ1 iç işlemlerini (ROTR/SHR/XOR) ve dört
        operandını taşır; W drill-down sihirbazı bunları bit bit çizer.
        σ0(x)=ROTR7⊕ROTR18⊕SHR3, σ1(y)=ROTR17⊕ROTR19⊕SHR10 ve
        W[16]=W[0]+σ0+W[9]+σ1 gerçek hesapla tutarlı olmalı."""
        from animation_modals.sha256_pure import _rotr

        result = sha256_steps(b"Hello World")
        d = result["w_detail"]
        self.assertEqual(d["i"], 16)
        hexkeys = [
            "w_i16", "w_i15", "w_i7", "w_i2",
            "x_rotr7", "x_rotr18", "x_shr3", "sigma0",
            "y_rotr17", "y_rotr19", "y_shr10", "sigma1", "result",
        ]
        for key in hexkeys:
            self.assertEqual(len(d[key]), 8, key)
            int(d[key], 16)

        x = int(d["w_i15"], 16)  # σ0 operandı (W[1])
        y = int(d["w_i2"], 16)   # σ1 operandı (W[14])
        self.assertEqual(d["x_rotr7"], f"{_rotr(x, 7):08x}")
        self.assertEqual(d["x_rotr18"], f"{_rotr(x, 18):08x}")
        self.assertEqual(d["x_shr3"], f"{x >> 3:08x}")
        s0 = _rotr(x, 7) ^ _rotr(x, 18) ^ (x >> 3)
        self.assertEqual(d["sigma0"], f"{s0:08x}")
        self.assertEqual(d["y_rotr17"], f"{_rotr(y, 17):08x}")
        self.assertEqual(d["y_rotr19"], f"{_rotr(y, 19):08x}")
        self.assertEqual(d["y_shr10"], f"{y >> 10:08x}")
        s1 = _rotr(y, 17) ^ _rotr(y, 19) ^ (y >> 10)
        self.assertEqual(d["sigma1"], f"{s1:08x}")
        # W[16] = W[0] + σ0 + W[9] + σ1 (mod 2^32)
        total = (int(d["w_i16"], 16) + s0 + int(d["w_i7"], 16) + s1) & 0xFFFFFFFF
        self.assertEqual(d["result"], f"{total:08x}")

    def test_snapshots_are_self_consistent_single_round(self):
        """Alt tür: BİRİM (DOĞRULUK — diyagram tutarlılığı, regresyon).
        Round diyagramı tek bir round'un dönüşümünü çizer: gösterilen GİRİŞ
        register'larından (registers_in), gösterilen K/W ile, gösterilen
        T1/T2 ve ÇIKIŞ register'ları (registers) türetilebilmeli.

        Önceden diyagram giriş olarak 'bir önceki snapshot çıkışını' (8 round
        eski) gösteriyordu; R9, R17… için T1 gösterilen girişten hesaplanamıyor,
        animasyon matematiksel olarak tutarsız kalıyordu. registers_in alanı bu
        boşluğu kapatır: her snapshot KENDİ round'unun gerçek girişini taşır."""
        from animation_modals.sha256_pure import _rotr

        def sig0(a): return _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        def sig1(e): return _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        def ch(e, f, g): return ((e & f) ^ (~e & g)) & 0xFFFFFFFF
        def maj(a, b, c): return (a & b) ^ (a & c) ^ (b & c)

        # Tek + çok bloklu mesaj (chaining'i de kapsa)
        for msg in (b"asdasdasd", b"x" * 130):
            result = sha256_steps(msg)
            for snap in result["round_snapshots"]:
                self.assertIn("registers_in", snap,
                              "snapshot kendi round girişini taşımalı")
                a, b, c, d, e, f, g, h = (int(x, 16) for x in snap["registers_in"])
                w = int(snap["w"], 16)
                k = int(snap["k"], 16)
                t1 = (h + sig1(e) + ch(e, f, g) + k + w) & 0xFFFFFFFF
                t2 = (sig0(a) + maj(a, b, c)) & 0xFFFFFFFF
                self.assertEqual(f"{t1:08x}", snap["t1"],
                                 f"R{snap['round']}: T1 girişten türetilebilmeli")
                self.assertEqual(f"{t2:08x}", snap["t2"],
                                 f"R{snap['round']}: T2 girişten türetilebilmeli")
                # Çıkış: A'=T1+T2, E'=D+T1, diğerleri bir sağa kaydırılır
                out = [(t1 + t2) & 0xFFFFFFFF, a, b, c,
                       (d + t1) & 0xFFFFFFFF, e, f, g]
                self.assertEqual([f"{v:08x}" for v in out], snap["registers"],
                                 f"R{snap['round']}: çıkış girişten türetilebilmeli")


    def test_round_detail_is_real_round64_internals(self):
        """Alt tür: BİRİM (bit düzeyi drill-down veri sözleşmesi — DOĞRULUK).
        round_detail, SON bloğun 64. round'unun TÜM ara değerlerini taşır;
        bit düzeyi drill-down sihirbazı bunları çizer. Her alan gerçek SHA
        hesabıyla tutarlı olmalı: Σ1/Ch → T1, Σ0/Maj → T2, A'=T1+T2, E'=D+T1.
        Ayrıca 'ben neyi hesapladım?' köprüsü: new_a (64. round A çıkışı) son
        bloğun çalışma değişkeni A'sına eşit ve pre_final_h[0]+new_a final
        hash'in ilk word'ünü verir."""
        from animation_modals.sha256_pure import _rotr

        result = sha256_steps(b"Hello World")
        d = result["round_detail"]

        # Tüm alanlar 8-hane hex
        hexkeys = [
            "a", "b", "c", "d", "e", "f", "g", "h", "k", "w",
            "e_rotr6", "e_rotr11", "e_rotr25", "sigma1",
            "e_and_f", "not_e_and_g", "ch",
            "a_rotr2", "a_rotr13", "a_rotr22", "sigma0",
            "a_and_b", "a_and_c", "b_and_c", "maj",
            "t1", "t2", "new_a", "new_e",
        ]
        for key in hexkeys:
            self.assertIn(key, d, key)
            self.assertEqual(len(d[key]), 8, key)
            int(d[key], 16)
        self.assertEqual(d["round_no"], 64)

        a, b, c, dd, e, f, g, h = (int(d[x], 16) for x in "abcdefgh")
        k, w = int(d["k"], 16), int(d["w"], 16)

        # Σ1(E) bit işlemleri
        self.assertEqual(d["e_rotr6"], f"{_rotr(e, 6):08x}")
        self.assertEqual(d["e_rotr11"], f"{_rotr(e, 11):08x}")
        self.assertEqual(d["e_rotr25"], f"{_rotr(e, 25):08x}")
        s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        self.assertEqual(d["sigma1"], f"{s1:08x}")
        # Ch
        ch = ((e & f) ^ (~e & g)) & 0xFFFFFFFF
        self.assertEqual(d["ch"], f"{ch:08x}")
        # Σ0(A) bit işlemleri
        s0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        self.assertEqual(d["sigma0"], f"{s0:08x}")
        # Maj
        maj = (a & b) ^ (a & c) ^ (b & c)
        self.assertEqual(d["maj"], f"{maj:08x}")
        # T1 / T2 (hex toplama)
        t1 = (h + s1 + ch + k + w) & 0xFFFFFFFF
        t2 = (s0 + maj) & 0xFFFFFFFF
        self.assertEqual(d["t1"], f"{t1:08x}")
        self.assertEqual(d["t2"], f"{t2:08x}")
        self.assertEqual(d["new_a"], f"{(t1 + t2) & 0xFFFFFFFF:08x}")
        self.assertEqual(d["new_e"], f"{(dd + t1) & 0xFFFFFFFF:08x}")

        # Köprü: 64. round'un A çıkışı = son bloğun çalışma değişkeni A
        self.assertEqual(d["new_a"], result["final_working"][0])
        # pre_final_h[0] + new_a (mod 2^32) = final hash'in ilk word'ü
        bridge = (int(result["pre_final_h"][0], 16)
                  + int(d["new_a"], 16)) & 0xFFFFFFFF
        self.assertEqual(f"{bridge:08x}", result["final_h_parts"][0])
        self.assertEqual(f"{bridge:08x}", result["final_hash"][:8])

    def test_round_detail_tracks_last_block(self):
        """Alt tür: BİRİM (çok bloklu süreklilik).
        Çok bloklu mesajda round_detail SON bloğu yansıtmalı: block_no =
        blocks_count, böylece final köprü gerçek çıktıya bağlanır."""
        result = sha256_steps(b"x" * 130)  # 3 blok
        d = result["round_detail"]
        self.assertEqual(d["block_no"], result["blocks_count"])
        self.assertEqual(d["new_a"], result["final_working"][0])


class TestSHA256AnimationStructure(unittest.TestCase):
    """sha256_animation modülünün yeni widget yapısını doğrular
    (Alt kategori: SMOKE — animasyon sınıf varlığı)."""

    def test_w_expansion_widget_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        _WExpansionWidget (Adım 3 — Mesaj Genişletme sayfası ana widget'ı)
        modülde tanımlı olmalı. Yeniden adlandırma/silme bozulmasını yakalar."""
        from animation_modals.sha256 import window as sha
        self.assertTrue(hasattr(sha, "_WExpansionWidget"))

    def test_match_assembly_widget_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        _MatchAssemblyWidget (Adım 5 — Hash Eşleşmesi sayfası widget'ı)
        modülde tanımlı olmalı. Final H[0..7] birleştirme animasyonu
        bu sınıfa bağlı."""
        from animation_modals.sha256 import window as sha
        self.assertTrue(hasattr(sha, "_MatchAssemblyWidget"))

if __name__ == "__main__":
    unittest.main()
