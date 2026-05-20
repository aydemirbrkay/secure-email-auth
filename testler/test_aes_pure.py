# test_aes_pure.py
"""
test_aes_pure.py — animation_modals/aes_pure modülü birim testleri
==================================================================

Test türü: BİRİM TESTİ (Unit Test)

Amaç:
    Saf-Python AES-256 ECB implementasyonunun kriptografik doğruluğunu
    NIST FIPS-197 Appendix B referans test vektörü ile birebir karşılaştırır.
    Pure-Python kod, üretimdeki 'cryptography' kütüphanesinden bağımsız
    olarak round state matrislerini animasyon için açar; bu testler o
    çıktının doğru olduğunu garanti eder.

Strateji:
    - Standart NIST test vektörünü (key + plaintext + beklenen ciphertext)
      sabit olarak tut.
    - aes256_encrypt_with_rounds() çağrısıyla son blok hex'ini al.
    - Beklenen ciphertext ile assertEqual.

Hata durumunda anlamı: Pure AES implementasyonunda matematiksel bozukluk
var; animasyondaki tüm round state görselleri yanlış olur.
"""
import unittest
from animation_modals.aes_pure import aes256_encrypt_with_rounds

class TestAESPure(unittest.TestCase):

    # NIST FIPS-197 Appendix B test vector
    KEY = bytes.fromhex(
        "000102030405060708090a0b0c0d0e0f"
        "101112131415161718191a1b1c1d1e1f"
    )
    PLAINTEXT = bytes.fromhex("00112233445566778899aabbccddeeff")
    EXPECTED_CT = bytes.fromhex("8ea2b7ca516745bfeafc49904b496089")

    def test_final_block_matches_nist(self):
        """Alt tür: BİRİM (kriptografik doğruluk — altın test).
        Bu sınıftaki EN KRİTİK test: NIST FIPS-197 Appendix B referans
        vektörü ile final ciphertext birebir aynı olmalı. Pure-Python
        AES implementasyonunun standartla uyumlu olduğunun matematiksel
        kanıtıdır. Bu test başarısızsa hiçbir round state görseli
        güvenilir değildir."""
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        self.assertEqual(result["final_block_hex"], self.EXPECTED_CT.hex())

    def test_15_round_entries(self):
        """Alt tür: BİRİM (yapısal sözleşme).
        AES-256 için 14 ana round + 1 başlangıç round_key uygulaması =
        toplam 15 round_data entry'si döndürülmeli. Animasyon penceresi
        her round için bir sayfa açtığından bu sayı kritik."""
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        # rounds_data: round 0 through 14 = 15 entries
        self.assertEqual(len(result["rounds_data"]), 15)

    def test_round_0_has_add_round_key(self):
        """Alt tür: BİRİM (özel durum — round 0 yapısı).
        Round 0 sadece AddRoundKey içerir (SubBytes/ShiftRows/MixColumns
        yok) — FIPS 197'ye göre başlangıç anahtar XOR'u. round=0 alanı
        ve after_add_round_key matrisi mevcut olmalı."""
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r0 = result["rounds_data"][0]
        self.assertEqual(r0["round"], 0)
        self.assertIn("after_add_round_key", r0)

    def test_round_1_has_all_ops(self):
        """Alt tür: BİRİM (ara round yapısı — 4 operasyon kontratı).
        Ana round'lar (1-13) tam 4 operasyon içerir:
        SubBytes → ShiftRows → MixColumns → AddRoundKey
        Her birinin after_* matrisi animasyonda ayrı bir sayfa olarak
        görünür; eksik biri varsa o sayfa boş çıkar."""
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r1 = result["rounds_data"][1]
        self.assertIn("after_sub_bytes", r1)
        self.assertIn("after_shift_rows", r1)
        self.assertIn("after_mix_columns", r1)
        self.assertIn("after_add_round_key", r1)

    def test_round_14_no_mix_columns(self):
        """Alt tür: BİRİM (özel durum — son round istisnası).
        FIPS 197 standardı son round'da (14) MixColumns'u ATLAR — bu,
        AES'in matematiksel bir özelliğidir (decryption simetrisi için).
        after_mix_columns alanı OLMAMALI; aksi halde standartdışı çıktı."""
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r14 = result["rounds_data"][14]
        self.assertEqual(r14["round"], 14)
        self.assertNotIn("after_mix_columns", r14)

    def test_matrix_is_4x4_hex(self):
        """Alt tür: BİRİM (matris veri yapısı).
        AES state matrisi 4×4 olmalı; her hücre 2 karakterlik hex
        string ('00'..'ff'). Animasyon widget'ları her hücreyi
        font='Courier' ile çizdiği için 2-karakter sözleşmesi sabit
        genişlik için kritik."""
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        mat = result["rounds_data"][1]["after_sub_bytes"]
        self.assertEqual(len(mat), 4)
        self.assertEqual(len(mat[0]), 4)
        self.assertEqual(len(mat[0][0]), 2)

if __name__ == "__main__":
    unittest.main()
