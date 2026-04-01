# test_aes_pure.py
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
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        self.assertEqual(result["final_block_hex"], self.EXPECTED_CT.hex())

    def test_15_round_entries(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        # rounds_data: round 0 through 14 = 15 entries
        self.assertEqual(len(result["rounds_data"]), 15)

    def test_round_0_has_add_round_key(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r0 = result["rounds_data"][0]
        self.assertEqual(r0["round"], 0)
        self.assertIn("after_add_round_key", r0)

    def test_round_1_has_all_ops(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r1 = result["rounds_data"][1]
        self.assertIn("after_sub_bytes", r1)
        self.assertIn("after_shift_rows", r1)
        self.assertIn("after_mix_columns", r1)
        self.assertIn("after_add_round_key", r1)

    def test_round_14_no_mix_columns(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r14 = result["rounds_data"][14]
        self.assertEqual(r14["round"], 14)
        self.assertNotIn("after_mix_columns", r14)

    def test_matrix_is_4x4_hex(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        mat = result["rounds_data"][1]["after_sub_bytes"]
        self.assertEqual(len(mat), 4)
        self.assertEqual(len(mat[0]), 4)
        self.assertEqual(len(mat[0][0]), 2)

if __name__ == "__main__":
    unittest.main()
