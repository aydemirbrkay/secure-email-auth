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

if __name__ == "__main__":
    unittest.main()
