"""
test_presentation_notes.py – C6 sunum/metin köprü notlarının testleri.

Doğrulanan (yalnızca metin; kripto davranışına dokunulmaz):
  * AES intro'sunda kaldırılması istenen uzun köprü notu görünmez.
  * RSA demo↔gerçek kartında demo anahtarın "temsilî" olduğu belirtilir.
"""
from __future__ import annotations

import unittest

# Headless QApplication conftest.py'deki autouse qapp fixture'ı ile sağlanır.


class TestAESBridgeNote(unittest.TestCase):
    def test_intro_bridge_note_is_removed(self) -> None:
        from animation_modals.aes.intro_widget import _AESIntroWidget

        w = _AESIntroWidget(lambda: None)
        self.assertFalse(hasattr(w, "_bridge_note"))
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
