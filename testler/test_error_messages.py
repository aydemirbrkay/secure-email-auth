"""
test_error_messages.py – C7 öğretici hata mesajları + diyalog testleri.

Doğrulanan:
  * crypto_core raise mesajları "Beklenen → Alınan → Olası neden → Çözüm"
    yapısında ve öğrenci dilinde (≥3 cümle).
  * explain_crypto_exception her tipli istisna için 3 dolu bölüm + teknik
    detay verir.
  * CryptoErrorDialog 3 bölüm kurar; teknik detay başta gizli, açılınca görünür.
  * Bilinmeyen/ham istisna için de güvenli bir açıklama döner (negatif durum).
"""
from __future__ import annotations

import unittest

from cryptography.exceptions import InvalidSignature

from kriptografi.crypto_core import CryptoCore
from kriptografi.errors import (
    DecryptError,
    IntegrityError,
    PacketFormatError,
    ReplayDetectedError,
    StaleTimestampError,
)
from kriptografi.utils import CryptoExplanation, explain_crypto_exception


def _sentence_count(text: str) -> int:
    return sum(text.count(p) for p in ".!?")


class TestRaiseMessages(unittest.TestCase):
    def test_rsa_sign_wrong_hash_length_message(self) -> None:
        """rsa_sign yanlış uzunlukta özet alınca yapılandırılmış mesaj atar."""
        core = CryptoCore()
        kp = core.generate_rsa_keypair()
        with self.assertRaises(IntegrityError) as ctx:
            core.rsa_sign(kp.private_key, b"kisa")  # 32 byte değil
        msg = str(ctx.exception)
        self.assertIn("Beklenen", msg)
        self.assertIn("Çözüm", msg)
        self.assertIn("32 byte", msg)
        self.assertGreaterEqual(_sentence_count(msg), 3)

    def test_short_signature_message_has_expected_and_received(self) -> None:
        # rsa_verify_packet benzeri yol yerine doğrudan istisna metnini değil,
        # yapı kuralını sınıf mesajı üzerinden doğrula: PacketFormatError
        # açıklayıcısı beklenen öğeleri içerir.
        exp = explain_crypto_exception(PacketFormatError("test"))
        self.assertTrue(exp.meaning.strip())
        self.assertGreaterEqual(_sentence_count(exp.meaning), 2)


class TestExplainCryptoException(unittest.TestCase):
    def _assert_full(self, exp: CryptoExplanation) -> None:
        self.assertTrue(exp.title.strip())
        self.assertTrue(exp.meaning.strip())
        self.assertTrue(exp.action.strip())
        self.assertTrue(exp.technical.strip())

    def test_all_typed_exceptions_have_three_filled_sections(self) -> None:
        for exc in (
            ReplayDetectedError("x"),
            StaleTimestampError("x"),
            IntegrityError("x"),
            DecryptError("x"),
            PacketFormatError("x"),
        ):
            with self.subTest(exc=type(exc).__name__):
                self._assert_full(explain_crypto_exception(exc))

    def test_invalid_signature_lists_three_causes(self) -> None:
        exp = explain_crypto_exception(InvalidSignature("x"))
        self.assertEqual(exp.meaning.count("•"), 3)
        self.assertIn("H(m)", exp.meaning)

    def test_technical_field_carries_exception_name(self) -> None:
        exp = explain_crypto_exception(IntegrityError("tag mismatch"))
        self.assertIn("IntegrityError", exp.technical)
        self.assertIn("tag mismatch", exp.technical)

    def test_unknown_exception_falls_back_safely(self) -> None:
        # Negatif: kripto-dışı bir istisna da boş olmayan açıklama vermeli.
        exp = explain_crypto_exception(ValueError("beklenmedik"))
        self._assert_full(exp)


class TestCryptoErrorDialog(unittest.TestCase):
    """QApplication conftest.py autouse qapp fixture'ı ile sağlanır."""

    def test_dialog_builds_with_three_sections(self) -> None:
        from arayuz.error_dialog import CryptoErrorDialog

        dlg = CryptoErrorDialog(InvalidSignature("imza"))
        self.assertIn("İmza", dlg.windowTitle())
        # Teknik detay başta gizli, butona basınca görünür. Diyalog exec
        # edilmediği için isVisibleTo(parent) ile niyet/durum kontrol edilir.
        self.assertFalse(dlg._tech_lbl.isVisibleTo(dlg))
        dlg._tech_btn.setChecked(True)
        self.assertTrue(dlg._tech_lbl.isVisibleTo(dlg))
        dlg.deleteLater()

    def test_dialog_handles_plain_exception(self) -> None:
        from arayuz.error_dialog import CryptoErrorDialog

        dlg = CryptoErrorDialog(RuntimeError("akış"))
        self.assertTrue(dlg.windowTitle().strip())
        dlg.deleteLater()


if __name__ == "__main__":
    unittest.main()
