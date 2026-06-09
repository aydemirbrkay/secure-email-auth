"""
test_presentation_notes.py – C6 sunum/metin köprü notlarının testleri.

Doğrulanan (yalnızca metin; kripto davranışına dokunulmaz):
  * AES intro'sundaki köprü notu: gösterilenin ECB "iç mekanik" olduğunu ve
    gerçek iletimin AES-256-GCM (auth tag) olduğunu söyler.
  * RSA demo↔gerçek kartında demo anahtarın "temsilî" olduğu belirtilir.
"""
from __future__ import annotations

import unittest

# Headless QApplication conftest.py'deki autouse qapp fixture'ı ile sağlanır.


class TestAESBridgeNote(unittest.TestCase):
    def test_intro_bridge_note_mentions_ecb_and_gcm(self) -> None:
        from animation_modals.aes.intro_widget import _AESIntroWidget

        w = _AESIntroWidget(lambda: None)
        text = w._bridge_note.text()
        self.assertIn("ECB", text)
        self.assertIn("AES-256-GCM", text)
        self.assertIn("tag", text.lower())
        w.deleteLater()

    def test_intro_bridge_note_not_empty(self) -> None:
        # Negatif yön: not boş kalmamalı (kullanıcı uyarıyı görmeli).
        from animation_modals.aes.intro_widget import _AESIntroWidget

        w = _AESIntroWidget(lambda: None)
        self.assertTrue(w._bridge_note.text().strip())
        w.deleteLater()


class TestRSARepresentativeLabel(unittest.TestCase):
    def test_demo_card_marked_representative(self) -> None:
        from animation_modals.rsa.key_match import _KeyMatchWidget

        w = _KeyMatchWidget("QUJDRA==", "WFlaVw==")
        title = w._demo_card._title_lbl.text()  # type: ignore[attr-defined]
        self.assertIn("temsilî", title)
        self.assertNotIn("temsilî", w._real_card._title_lbl.text())  # type: ignore[attr-defined]
        w.deleteLater()


if __name__ == "__main__":
    unittest.main()
