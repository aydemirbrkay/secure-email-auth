# test_sha256_pure.py
import hashlib
import unittest
from animation_modals.sha256_pure import sha256_steps

class TestSHA256Pure(unittest.TestCase):

    def test_final_hash_matches_hashlib(self):
        msg = b"Hello World"
        result = sha256_steps(msg)
        expected = hashlib.sha256(msg).hexdigest()
        self.assertEqual(result["final_hash"], expected)

    def test_empty_message(self):
        result = sha256_steps(b"")
        expected = hashlib.sha256(b"").hexdigest()
        self.assertEqual(result["final_hash"], expected)

    def test_initial_h_count(self):
        result = sha256_steps(b"test")
        self.assertEqual(len(result["initial_h"]), 8)

    def test_round_snapshots_present(self):
        result = sha256_steps(b"test")
        self.assertIn("round_snapshots", result)
        self.assertGreater(len(result["round_snapshots"]), 0)

    def test_blocks_count(self):
        result = sha256_steps(b"Hello World")
        self.assertEqual(result["blocks_count"], 1)

    def test_binary_preview_present(self):
        result = sha256_steps(b"Hi")
        self.assertIn("binary_preview", result)
        self.assertGreater(len(result["binary_preview"]), 0)

    def test_round_snapshots_have_rich_data(self):
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
        """Snapshot round numaraları kod ile docstring tutarlı olmalı."""
        result = sha256_steps(b"Hello World")
        rounds = [s["round"] for s in result["round_snapshots"]]
        self.assertEqual(rounds, [1, 9, 17, 25, 33, 41, 49, 57, 64])

    def test_w_expansion_exposes_operand_and_result(self):
        """
        W[16..31] gösteriminde σ0/σ1 için hem operand (W[i-15], W[i-2])
        hem de sonuç (s0, s1) ayrı alanlar olarak dönmeli — aksi hâlde
        animasyon 'σ0(sonuç)' gibi yanıltıcı görünüm üretir.
        """
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

class TestSHA256AnimationStructure(unittest.TestCase):
    """sha256_animation modülünün yeni widget yapısını doğrular."""

    def test_w_expansion_widget_exists(self):
        from animation_modals import sha256_animation as sha
        self.assertTrue(hasattr(sha, "_WExpansionWidget"))

    def test_match_assembly_widget_exists(self):
        from animation_modals import sha256_animation as sha
        self.assertTrue(hasattr(sha, "_MatchAssemblyWidget"))

if __name__ == "__main__":
    unittest.main()
