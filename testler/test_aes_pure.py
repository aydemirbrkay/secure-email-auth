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
from animation_modals.aes_pure import (
    SBOX,
    _mix_columns,
    _shift_rows,
    aes256_encrypt_with_rounds,
)

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

    def test_short_plaintext_round_state_matches_displayed_first_block(self):
        """Kısa plaintext için round hesabı ve hazırlık sayfası aynı PKCS#7 bloğunu kullanır."""
        result = aes256_encrypt_with_rounds(self.KEY, b"abc")
        first_block = result["first_block"]
        expected_state = [
            [f"{first_block[c * 4 + r]:02x}" for c in range(4)]
            for r in range(4)
        ]
        self.assertEqual(result["initial_state_hex"], expected_state)

    def test_every_displayed_operation_matches_its_aes_transformation(self):
        """Animasyonda gösterilen tüm ara matrisler, önceki state'ten doğru üretilir."""
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        previous = result["initial_state_hex"]

        for round_data in result["rounds_data"]:
            round_no = round_data["round"]
            if round_no > 0:
                expected_sub = [
                    [f"{SBOX[int(value, 16)]:02x}" for value in row]
                    for row in previous
                ]
                self.assertEqual(round_data["after_sub_bytes"], expected_sub)

                shifted_ints = _shift_rows(
                    [[int(value, 16) for value in row] for row in expected_sub]
                )
                expected_shift = [
                    [f"{value:02x}" for value in row] for row in shifted_ints
                ]
                self.assertEqual(round_data["after_shift_rows"], expected_shift)

                before_add = expected_shift
                if round_no < 14:
                    mixed_ints = _mix_columns(shifted_ints)
                    before_add = [
                        [f"{value:02x}" for value in row] for row in mixed_ints
                    ]
                    self.assertEqual(round_data["after_mix_columns"], before_add)

            else:
                before_add = previous

            round_key = result["round_keys_hex"][round_no]
            expected_add = [
                [
                    f"{int(before_add[row][col], 16) ^ int(round_key[row][col], 16):02x}"
                    for col in range(4)
                ]
                for row in range(4)
            ]
            self.assertEqual(round_data["after_add_round_key"], expected_add)
            previous = expected_add

class TestSBoxDerivation(unittest.TestCase):
    """S-Box türetiminin (GF(2⁸) ters + affine) doğruluğunu sınar."""

    def test_derivation_reproduces_every_sbox_entry(self):
        """Türetim, 256 byte'ın tamamında resmi SBOX ile birebir eşleşmeli."""
        from animation_modals.aes_pure import derive_sbox_value

        for byte in range(256):
            self.assertEqual(derive_sbox_value(byte).result, SBOX[byte])

    def test_zero_has_no_inverse_and_maps_to_0x63(self):
        """0x00'ın çarpımsal tersi yoktur (0 alınır) ve sonucu 0x63'tür."""
        from animation_modals.aes_pure import derive_sbox_value

        step = derive_sbox_value(0x00)
        self.assertEqual(step.inverse, 0x00)
        self.assertEqual(step.result, 0x63)

    def test_inverse_is_true_multiplicative_inverse(self):
        """Sıfırdan farklı girdi için GF(2⁸)'de girdi · ters = 1 olmalı."""
        from animation_modals.aes_pure import derive_sbox_value, _gf_mul

        step = derive_sbox_value(0x53)
        self.assertEqual(_gf_mul(0x53, step.inverse), 1)

    def test_rejects_out_of_range_byte(self):
        """0-255 dışındaki değer ValueError ile reddedilmeli."""
        from animation_modals.aes_pure import derive_sbox_value

        with self.assertRaises(ValueError):
            derive_sbox_value(256)


class TestGFInverseExponentiation(unittest.TestCase):
    """GF(2⁸) tersinin üs alma (a²⁵⁴) yöntemi ve animasyon adımlarını sınar."""

    def test_inverse_via_exponentiation_for_all_nonzero(self):
        """Üs alma yöntemi tüm sıfırdan farklı byte'lar için a·a⁻¹ = 1 vermeli."""
        from animation_modals.aes_pure import _gf_inverse, _gf_mul

        for a in range(1, 256):
            self.assertEqual(_gf_mul(a, _gf_inverse(a)), 1)

    def test_zero_inverse_is_zero(self):
        """0'ın tersi tanımsızdır; AES sözleşmesi gereği 0 döner."""
        from animation_modals.aes_pure import _gf_inverse

        self.assertEqual(_gf_inverse(0), 0)

    def test_exponent_steps_chain_and_product(self):
        """Adımlar: 8 ardışık kare, a hariç çarpılan 7 kare, son çarpım = ters."""
        from animation_modals.aes_pure import (
            gf_inverse_exponent_steps, _gf_mul, _gf_inverse,
        )

        s = gf_inverse_exponent_steps(0x8e)
        self.assertEqual(len(s["squares"]), 8)
        self.assertEqual(s["squares"][0], 0x8e)          # a^(2⁰) = a
        # Her kare, bir öncekinin GF karesi olmalı.
        for i in range(1, 8):
            self.assertEqual(s["squares"][i], _gf_mul(s["squares"][i - 1],
                                                      s["squares"][i - 1]))
        self.assertEqual(s["bits"], [0, 1, 1, 1, 1, 1, 1, 1])  # 254 = 11111110
        self.assertEqual(s["multiplied"], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(s["products"][-1], s["inverse"])
        self.assertEqual(s["inverse"], _gf_inverse(0x8e))

    def test_exponent_steps_zero_is_empty(self):
        """0 için tersi tanımsız: kareler/çarpımlar boş, ters 0 döner."""
        from animation_modals.aes_pure import gf_inverse_exponent_steps

        s = gf_inverse_exponent_steps(0)
        self.assertEqual(s["squares"], [])
        self.assertEqual(s["products"], [])
        self.assertEqual(s["inverse"], 0)


if __name__ == "__main__":
    unittest.main()
