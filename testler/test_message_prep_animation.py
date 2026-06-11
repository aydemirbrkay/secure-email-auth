# test_message_prep_animation.py
"""
test_message_prep_animation.py — Mesaj/Plaintext Hazırlığı veri kontrat testleri
================================================================================

Test türü: INVARIANT TESTİ (Veri Sözleşmesi + Boş Mesaj Davranışı)

Amaç:
    SHA Mesaj Hazırlığı + AES Plaintext Hazırlığı sayfaları için
    sha256_pure ve aes_pure modüllerine eklenen yeni alanların doğru
    veriyi döndürdüğünü; PKCS#7 padding, UTF-8 kodlama ve column-major
    matris dönüşümünün matematiksel kurallara uyduğunu sınar. Bunlar
    dinamik kullanıcı girdisine bağlı (her mesajda farklı sayılar
    çıkar), bu yüzden testler değer değil **kural** doğrular.

Kapsam:
    TestSHAMessagePrepContract (7 test):
        - sha256_steps() yeni alanları döndürür: message_bytes,
          message_text, padded_bytes
        - padded_bytes uzunluğu 64 katı (512-bit blok)
        - padded_bytes mesaj byte'larıyla başlar + 0x80 ayracı içerir
        - Son 8 byte big-endian bit-length (örn. b"abc" → 24 bit)
        - UTF-8 multi-byte (Türkçe "şğü") doğru kodlanır

    TestAESPlaintextPrepContract (9 test):
        - aes256_encrypt_with_rounds() yeni alanları:
          plaintext_bytes/text, padded_plaintext, first_block,
          blocks_total, state_matrix
        - PKCS#7 kuralı: 13 byte → 3 byte 0x03 padding; 16 byte → 16
          byte 0x10 tam blok padding
        - state_matrix 4×4 column-major: state_matrix[r][c] =
          first_block[c*4 + r] (FIPS 197 byte sıralaması)
        - blocks_total = len(padded_plaintext) // 16

    TestEmptyMessageHandling (6 test — boş mesaj graceful davranışı):
        - sha256_steps(b"") → standart empty hash "e3b0c44298fc..."
        - padded_bytes = 64 byte (0x80 + 55 × 0x00 + 8 byte length 0)
        - aes_encrypt(KEY, b"") → 16 byte 0x10 PKCS#7 padding,
          state_matrix tamamı "10", blocks_total = 1

Strateji: Spesifik değer yerine matematiksel/yapısal bağıt; pure modül
düzeyi (UI gerekmez).

Hata durumunda anlamı: Mesaj Hazırlığı / Plaintext Hazırlığı
sayfasında byte/padding gösterimi yanlış veya boş mesajda crash.
"""
import unittest


class TestSHAMessagePrepContract(unittest.TestCase):
    """sha256_pure.sha256_steps() yeni alanları döndürmeli."""

    def test_message_bytes_field_exists(self):
        """Alt tür: INVARIANT (yeni alan + değer doğruluğu).
        message_bytes alanı çıktıda olmalı VE verilen mesajın aynısı.
        Mesaj Hazırlığı sayfasında kullanıcının yazdığı byte'lar bu
        alandan okunur."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"Merhaba")
        self.assertIn("message_bytes", result)
        self.assertEqual(result["message_bytes"], b"Merhaba")

    def test_message_text_field_exists(self):
        """Alt tür: INVARIANT (yeni alan varlığı).
        message_text alanı (decode edilmiş string) çıktıda olmalı —
        Mesaj Hazırlığı sayfası label'ında 'Mesaj: "..."' olarak gösterir."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"abc")
        self.assertIn("message_text", result)

    def test_padded_bytes_length_multiple_of_64(self):
        """Alt tür: INVARIANT (SHA-256 blok yapısı).
        padded_bytes uzunluğu 64'ün KATI olmalı (SHA-256 512-bit
        blok = 64 byte). Bu, padding algoritmasının temel matematik
        bağıtıdır. Aksi halde compression fonksiyonu çalışmaz."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"x")
        self.assertIn("padded_bytes", result)
        self.assertEqual(len(result["padded_bytes"]) % 64, 0)

    def test_padded_bytes_starts_with_message(self):
        """Alt tür: INVARIANT (padding tasarımı).
        Padded blok orijinal mesaj byte'larıyla BAŞLAMALI; padding
        bunların ARDINDAN gelir. Aksi halde mesaj korunmadan kayıp
        gider."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"test")
        self.assertTrue(result["padded_bytes"].startswith(b"test"))

    def test_padded_bytes_contains_0x80_separator(self):
        """Alt tür: INVARIANT (SHA padding kuralı — ayraç byte'ı).
        Mesajdan hemen sonra (index = len(message)) tam olarak 0x80
        byte'ı eklenmeli. Bu, '1 biti' + '0 dolgu'nun başlangıcını
        işaretler. FIPS 180-4'ün padding kuralı."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"abc")
        self.assertEqual(result["padded_bytes"][3], 0x80)

    def test_padded_bytes_ends_with_bit_length(self):
        """Alt tür: INVARIANT (SHA padding kuralı — uzunluk eki).
        Padded bloğun SON 8 byte'ı orijinal mesajın bit uzunluğunu
        big-endian olarak içermeli. 'abc' = 3 byte = 24 bit; son
        8 byte big-endian okunduğunda 24 çıkmalı."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"abc")
        bit_len = int.from_bytes(result["padded_bytes"][-8:], "big")
        self.assertEqual(bit_len, 24)  # 3 byte = 24 bit

    def test_unicode_message_utf8_encoded(self):
        """Alt tür: INVARIANT (UTF-8 çok-byte karakter desteği).
        Türkçe karakterler 'şğü' UTF-8'de tek karakter ≠ tek byte
        ('şğü' = 6 byte). message_bytes alanı UTF-8 byte dizisini
        olduğu gibi saklamalı — kullanıcı 'şğü' yazınca animasyon
        6 byte göstermeli."""
        from animation_modals.sha256_pure import sha256_steps
        msg = "şğü".encode("utf-8")
        result = sha256_steps(msg)
        self.assertEqual(result["message_bytes"], msg)


class TestAESPlaintextPrepContract(unittest.TestCase):
    """aes_pure.aes256_encrypt_with_rounds() yeni alanları döndürmeli."""

    KEY = bytes.fromhex("00" * 32)

    def test_plaintext_bytes_field_exists(self):
        """Alt tür: INVARIANT (yeni alan + değer doğruluğu).
        plaintext_bytes alanı, kullanıcının verdiği bytes'ı aynen
        içermeli. AES Plaintext Hazırlığı sayfası label'ında
        'Plaintext: "..."' olarak gösterir."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"Merhaba Bob 123!")
        self.assertIn("plaintext_bytes", result)
        self.assertEqual(result["plaintext_bytes"], b"Merhaba Bob 123!")

    def test_plaintext_text_field_exists(self):
        """Alt tür: INVARIANT (yeni alan varlığı).
        plaintext_text alanı UI label için decode edilmiş string."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"abc")
        self.assertIn("plaintext_text", result)

    def test_padded_plaintext_is_pkcs7(self):
        """Alt tür: INVARIANT (PKCS#7 padding kuralı — kısmi blok).
        PKCS#7 kuralı: ekstra alan kadar byte ekle, her byte'ın değeri
        = padding miktarı. 13 byte mesaj + 3 byte 0x03 padding = 16 byte
        (tek tam blok). Son 3 byte 0x03 olmalı."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"hello world!!")
        self.assertEqual(len(result["padded_plaintext"]), 16)
        self.assertEqual(result["padded_plaintext"][-3:], b"\x03\x03\x03")

    def test_padded_plaintext_full_block_when_exact_16(self):
        """Alt tür: INVARIANT (PKCS#7 — tam blok özel durumu).
        Mesaj tam 16 byte ise PKCS#7 BİR TAM EK BLOK ekler (16 × 0x10).
        Bu kuralın çiğnenmesi (örn. hiç padding eklememe) decryption
        ambiguity yaratır — alıcı sondaki padding'i ayıramaz."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"x" * 16)
        self.assertEqual(len(result["padded_plaintext"]), 32)
        self.assertEqual(result["padded_plaintext"][-16:], b"\x10" * 16)

    def test_first_block_is_16_bytes(self):
        """Alt tür: INVARIANT (blok boyutu).
        first_block alanı tam 16 byte (AES blok boyutu). Animasyonun
        4×4 matris dolumu bu uzunluğa bağlı (16 hücre)."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"abc")
        self.assertEqual(len(result["first_block"]), 16)

    def test_first_block_equals_first_16_of_padded(self):
        """Alt tür: INVARIANT (slice tutarlılığı).
        first_block = padded_plaintext[:16]. İki alan arasında
        herhangi bir kayma olmamalı; animasyon strip'i ve matrisi
        aynı veriden türüyor."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"long message X")
        self.assertEqual(result["first_block"], result["padded_plaintext"][:16])

    def test_state_matrix_is_4x4(self):
        """Alt tür: INVARIANT (matris yapısı).
        state_matrix tam 4 satır × 4 sütun. AES state'inin standart
        boyutu; widget'ın 4×4 QGridLayout'u buna bağlı."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"test")
        self.assertEqual(len(result["state_matrix"]), 4)
        for row in result["state_matrix"]:
            self.assertEqual(len(row), 4)

    def test_state_matrix_is_column_major(self):
        """Alt tür: INVARIANT (FIPS 197 byte yerleşimi — column-major).
        AES state'inin matris formu COLUMN-MAJOR: byte sırası 0..15
        sütun sütun yerleşir (b0 → s[0][0], b1 → s[1][0], b2 → s[2][0],
        b3 → s[3][0], b4 → s[0][1], ...). Formül: s[r][c] = b[c*4+r].
        Row-major kullanmak FIPS 197 ihlali olur ve şifreleme yanlış
        çıkar. 16 hücre tek tek kontrol edilir."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"0123456789ABCDEF")
        for r in range(4):
            for c in range(4):
                expected = f"{result['first_block'][c*4 + r]:02x}"
                self.assertEqual(result["state_matrix"][r][c], expected,
                                 f"r={r}, c={c}")

    def test_blocks_total_matches_padded_length(self):
        """Alt tür: INVARIANT (blok sayısı hesabı).
        50 byte mesaj → PKCS#7 padding (14 byte 0x0E) → 64 byte
        → 64/16 = 4 blok. blocks_total tam 4 olmalı; animasyon
        '4 blok' bilgisini bu alandan okur."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"x" * 50)
        self.assertEqual(result["blocks_total"], 4)


class TestEmptyMessageHandling(unittest.TestCase):
    """Boş mesaj girişinde pure modüllerin davranışı."""

    KEY = bytes.fromhex("00" * 32)

    def test_sha256_steps_empty_message_returns_standard_hash(self):
        """Alt tür: SINIR KOŞULU (RFC standart vektörü).
        SHA-256(b"") = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934
        ca495991b7852b855" — RFC 4634'te belirtilen boş giriş hash'i.
        Bu test boş input handling'in standart uyumlu olduğunun kanıtı."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"")
        self.assertEqual(
            result["final_hash"],
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_sha256_steps_empty_message_bytes_field_is_empty(self):
        """Alt tür: SINIR KOŞULU (alan tutarlılığı).
        Boş girişte message_bytes = b"", message_text = "". Animasyon
        '(boş mesaj)' italic etiketi göstermek için bu alanlara bakar."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"")
        self.assertEqual(result["message_bytes"], b"")
        self.assertEqual(result["message_text"], "")

    def test_sha256_steps_empty_padded_bytes_is_64(self):
        """Alt tür: SINIR KOŞULU (boş girişte padding yapısı).
        Boş mesaj → tek 64 byte blok, tamamı padding:
          - byte[0] = 0x80 (ayraç)
          - byte[1..55] = 0x00 (sıfır dolgu, 55 byte)
          - byte[56..63] = 8 × 0x00 (length = 0 bit)
        Bu yapı SHA padding sayfasında 'Boş mesaj — padding tek blok'
        senaryosunda gösterilir."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"")
        self.assertEqual(len(result["padded_bytes"]), 64)
        self.assertEqual(result["padded_bytes"][0], 0x80)
        self.assertEqual(result["padded_bytes"][-8:], b"\x00" * 8)

    def test_aes_empty_plaintext_padded_to_16(self):
        """Alt tür: SINIR KOŞULU (PKCS#7 boş giriş).
        Boş plaintext (0 byte) → PKCS#7 16 byte 0x10 ekler (tam blok
        padding kuralı). Animasyon 'Boş mesaj — bir tam blok PKCS#7
        padding' bilgisini bu sonuca dayanarak gösterir."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"")
        self.assertEqual(result["padded_plaintext"], b"\x10" * 16)

    def test_aes_empty_padding_mask_all_true(self):
        """Alt tür: SINIR KOŞULU (matris tamamen padding).
        Boş plaintext'in state_matrix'i tamamen '10' hex değeriyle
        dolu (16 × 0x10 padding'in matris formu). 4×4 = 16 hücre
        tek tek '10' eşitliği kontrolü."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"")
        for row in result["state_matrix"]:
            for cell in row:
                self.assertEqual(cell, "10")

    def test_aes_empty_blocks_total_is_one(self):
        """Alt tür: SINIR KOŞULU (boş plaintext blok sayısı).
        Boş plaintext → 16 byte tam blok padding → blocks_total = 1.
        AES animasyonu 'blok sayısı: 1' bilgisini gösterir."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"")
        self.assertEqual(result["blocks_total"], 1)


class TestPaddingBreakdown(unittest.TestCase):
    """_SHA256PaddingWidget._padding_breakdown padding bileşenlerini SAYILARIYLA
    doğru vermeli (Alt kategori: BİRİM — açıklama verisi doğruluğu).

    Kullanıcı geri bildirimi: padding metni '0x00 dolgu' diyordu ama kaç sıfır
    bayt eklendiği ve son 8 baytın değeri belirsizdi. breakdown bunları açar."""

    @staticmethod
    def _make(msg: bytes):
        from animation_modals.sha256_pure import sha256_steps
        from animation_modals.sha256.prep_widget import _SHA256PaddingWidget
        d = sha256_steps(msg)
        return _SHA256PaddingWidget(
            d["message_bytes"], d["padded_bytes"], d["blocks_count"],
            d["message_text"])

    def test_components_sum_to_total(self):
        """Alt tür: BİRİM (pozitif — bileşen toplamı).
        mesaj + 1 (0x80) + zeros + 8 (uzunluk) = toplam padded uzunluk;
        her mesaj boyutunda (tek/çok blok, sınır) tutmalı."""
        for msg in (b"merhab", b"", b"x" * 56, b"x" * 130):
            bd = self._make(msg)._padding_breakdown()
            self.assertEqual(bd["msg"] + 1 + bd["zeros"] + 8, bd["total"],
                             f"{len(msg)} bayt: bileşenler toplama eşit olmalı")
            self.assertGreaterEqual(bd["zeros"], 0)

    def test_six_byte_message_matches_known_values(self):
        """Alt tür: BİRİM (pozitif — bilinen değer / kullanıcı örneği).
        6 byte mesaj → 64 byte blok, 49 sıfır bayt, 48 bit uzunluk; son 8
        byte big-endian '00 00 00 00 00 00 00 30' (0x30 = 48)."""
        bd = self._make(b"abcdef")._padding_breakdown()
        self.assertEqual(bd["total"], 64)
        self.assertEqual(bd["zeros"], 49)
        self.assertEqual(bd["bit_len"], 48)
        self.assertEqual(bd["last8_hex"], "00 00 00 00 00 00 00 30")

    def test_last8_encodes_bit_length_big_endian(self):
        """Alt tür: BİRİM (negatif/kenar — uzunluk alanı kodlaması).
        Son 8 baytın big-endian tamsayı değeri = mesaj bit uzunluğu. Çok
        baytlı uzunlukta da (örn. 56 byte → 448 bit = 0x01C0) doğru olmalı."""
        bd = self._make(b"x" * 56)._padding_breakdown()
        self.assertEqual(bd["bit_len"], 448)
        last8_int = int(bd["last8_hex"].replace(" ", ""), 16)
        self.assertEqual(last8_int, bd["bit_len"])


class TestSHAPrepExplanationPacing(unittest.TestCase):
    """SHA hazırlık ekranlarının hız ve kullanıcı kontrollü açıklama sözleşmesini sınar."""

    def test_message_prep_restores_fast_byte_strip_timing(self):
        """Tüm byte'lar şeridi önceki akıştaki gibi yaklaşık iki saniyede görünmeli."""
        from animation_modals.sha256.prep_widget import _SHAMessagePrepWidget

        widget = _SHAMessagePrepWidget("asd", b"asd")
        self.assertEqual(widget._TICK_MS, 45)
        for _ in range(40):
            widget._on_tick()
        self.assertFalse(widget._strip.isHidden())
        while widget._tick < 52:
            widget._on_tick()
        self.assertTrue(widget._finished)

    def test_padding_explanations_are_click_driven_not_timed(self):
        """Padding bilgileri otomatik akmamalı; seçilen bileşenin açıklaması açılmalı."""
        widget = TestPaddingBreakdown._make(b"abcdef")

        self.assertTrue(widget._detail_explanation.isHidden())
        self.assertFalse(hasattr(widget, "_info_lbl"))
        self.assertFalse(hasattr(widget, "_phase_lbl"))
        self.assertFalse(hasattr(widget, "_bitlen_lbl"))

        widget._explanation_buttons["length"].click()

        self.assertFalse(widget._detail_explanation.isHidden())
        self.assertIn("compression", widget._detail_explanation.text())
        self.assertIn("son 8 byte", widget._detail_explanation.text())
        self.assertIn("00 00 00 00 00 00 00 30", widget._detail_explanation.text())

    def test_length_phase_explains_why_last_eight_bytes_are_at_end(self):
        """Uzunluk açıklaması son 8 baytın nerede kullanıldığını gerekçelendirmeli."""
        widget = TestPaddingBreakdown._make(b"abcdef")

        text = widget._component_explanation("length")

        self.assertIn("compression", text)
        self.assertIn("64 byte", text)
        self.assertIn("orijinal mesaj uzunluğunu", text)
        self.assertIn("00 00 00 00 00 00 00 30", text)


if __name__ == "__main__":
    unittest.main()
