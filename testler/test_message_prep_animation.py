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
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"Merhaba")
        self.assertIn("message_bytes", result)
        self.assertEqual(result["message_bytes"], b"Merhaba")

    def test_message_text_field_exists(self):
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"abc")
        self.assertIn("message_text", result)

    def test_padded_bytes_length_multiple_of_64(self):
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"x")
        self.assertIn("padded_bytes", result)
        self.assertEqual(len(result["padded_bytes"]) % 64, 0)

    def test_padded_bytes_starts_with_message(self):
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"test")
        self.assertTrue(result["padded_bytes"].startswith(b"test"))

    def test_padded_bytes_contains_0x80_separator(self):
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"abc")
        self.assertEqual(result["padded_bytes"][3], 0x80)

    def test_padded_bytes_ends_with_bit_length(self):
        """Son 8 byte big-endian bit length olmalı."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"abc")
        bit_len = int.from_bytes(result["padded_bytes"][-8:], "big")
        self.assertEqual(bit_len, 24)  # 3 byte = 24 bit

    def test_unicode_message_utf8_encoded(self):
        from animation_modals.sha256_pure import sha256_steps
        msg = "şğü".encode("utf-8")
        result = sha256_steps(msg)
        self.assertEqual(result["message_bytes"], msg)


class TestAESPlaintextPrepContract(unittest.TestCase):
    """aes_pure.aes256_encrypt_with_rounds() yeni alanları döndürmeli."""

    KEY = bytes.fromhex("00" * 32)

    def test_plaintext_bytes_field_exists(self):
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"Merhaba Bob 123!")
        self.assertIn("plaintext_bytes", result)
        self.assertEqual(result["plaintext_bytes"], b"Merhaba Bob 123!")

    def test_plaintext_text_field_exists(self):
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"abc")
        self.assertIn("plaintext_text", result)

    def test_padded_plaintext_is_pkcs7(self):
        """13 byte mesaj → 16 byte (3 byte 0x03 padding)."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"hello world!!")
        self.assertEqual(len(result["padded_plaintext"]), 16)
        self.assertEqual(result["padded_plaintext"][-3:], b"\x03\x03\x03")

    def test_padded_plaintext_full_block_when_exact_16(self):
        """16 byte mesaj → 32 byte (full 16 byte 0x10 padding)."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"x" * 16)
        self.assertEqual(len(result["padded_plaintext"]), 32)
        self.assertEqual(result["padded_plaintext"][-16:], b"\x10" * 16)

    def test_first_block_is_16_bytes(self):
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"abc")
        self.assertEqual(len(result["first_block"]), 16)

    def test_first_block_equals_first_16_of_padded(self):
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"long message X")
        self.assertEqual(result["first_block"], result["padded_plaintext"][:16])

    def test_state_matrix_is_4x4(self):
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"test")
        self.assertEqual(len(result["state_matrix"]), 4)
        for row in result["state_matrix"]:
            self.assertEqual(len(row), 4)

    def test_state_matrix_is_column_major(self):
        """state_matrix[r][c] = first_block[c*4 + r] olmalı."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"0123456789ABCDEF")
        for r in range(4):
            for c in range(4):
                expected = f"{result['first_block'][c*4 + r]:02x}"
                self.assertEqual(result["state_matrix"][r][c], expected,
                                 f"r={r}, c={c}")

    def test_blocks_total_matches_padded_length(self):
        """50 byte → 64 byte padded → 4 blok."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"x" * 50)
        self.assertEqual(result["blocks_total"], 4)


class TestEmptyMessageHandling(unittest.TestCase):
    """Boş mesaj girişinde pure modüllerin davranışı."""

    KEY = bytes.fromhex("00" * 32)

    def test_sha256_steps_empty_message_returns_standard_hash(self):
        """SHA-256(b'') = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"")
        self.assertEqual(
            result["final_hash"],
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_sha256_steps_empty_message_bytes_field_is_empty(self):
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"")
        self.assertEqual(result["message_bytes"], b"")
        self.assertEqual(result["message_text"], "")

    def test_sha256_steps_empty_padded_bytes_is_64(self):
        """Boş mesaj → tek 64 byte blok (0x80 + 55 × 0x00 + 8 byte length=0)."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"")
        self.assertEqual(len(result["padded_bytes"]), 64)
        self.assertEqual(result["padded_bytes"][0], 0x80)
        self.assertEqual(result["padded_bytes"][-8:], b"\x00" * 8)

    def test_aes_empty_plaintext_padded_to_16(self):
        """Boş plaintext → 16 byte 0x10 padding."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"")
        self.assertEqual(result["padded_plaintext"], b"\x10" * 16)

    def test_aes_empty_padding_mask_all_true(self):
        """Boş plaintext → state_matrix tüm hücreler '10'."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"")
        for row in result["state_matrix"]:
            for cell in row:
                self.assertEqual(cell, "10")

    def test_aes_empty_blocks_total_is_one(self):
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, b"")
        self.assertEqual(result["blocks_total"], 1)


if __name__ == "__main__":
    unittest.main()
