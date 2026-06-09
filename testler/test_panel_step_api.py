"""
test_panel_step_api.py — Alice/Bob panel adım public API testleri
==================================================================

Test türü: BİRİM/ENTEGRASYON — PyQt6 widget (offscreen)

Amaç:
    AlicePanel ve BobPanel'e eklenen public adım akışı API'sini
    (``current_step`` property + ``peek_next_step()``) doğrular. Bu API,
    main_gui akışının panel iç durumuna (``_current_step`` / ``_steps``)
    sızmadan bir sonraki adımın ``step_type``'ına bakmasını sağlar.

Strateji:
    - ``current_step`` başlangıçta 0; her ``show_next_step()`` sonrası artar.
    - ``peek_next_step()`` durumu değiştirmeden sıradaki adımı döndürür.
    - Adımların sonunda ``peek_next_step()`` → None (negatif/kenar durum).
    - peek dönen adımın ``step_type``'ı beklenen değer (akış kararı için).

Hata durumunda anlamı: main_gui animasyon-açma akışı sessizce bozulabilir.
"""
from __future__ import annotations

import unittest

from arayuz.alice_panel import AlicePanel
from arayuz.bob_panel import BobPanel
from kriptografi.crypto_core import CryptoCore, StepType


class _PanelStepAPIBase:
    """Alice ve Bob panelleri için ortak adım API senaryoları."""

    panel_factory = None        # alt sınıfta atanır
    use_alice_steps = True      # True → alice_send, False → bob_receive
    expected_first_type = None  # ilk adımın beklenen StepType'ı
    expected_count = 0          # toplam adım sayısı

    def setUp(self) -> None:
        crypto = CryptoCore()
        crypto.setup_keys()
        packet, alice_steps = crypto.alice_send("Merhaba")
        if self.use_alice_steps:
            self._steps = alice_steps
        else:
            _, _, self._steps = crypto.bob_receive(packet)
        self.panel = self.panel_factory()
        self.panel.set_steps(self._steps)

    def test_current_step_starts_at_zero(self) -> None:
        """Alt tür: BİRİM — set_steps sonrası current_step == 0."""
        self.assertEqual(self.panel.current_step, 0)

    def test_peek_does_not_advance(self) -> None:
        """Alt tür: BİRİM — peek_next_step durumu değiştirmez."""
        first = self.panel.peek_next_step()
        self.assertIs(self.panel.peek_next_step(), first)
        self.assertEqual(self.panel.current_step, 0)

    def test_peek_first_step_type(self) -> None:
        """Alt tür: BİRİM — sıradaki adımın step_type'ı doğru.

        main_gui animasyon kararını bu tipe göre verir.
        """
        nxt = self.panel.peek_next_step()
        self.assertIsNotNone(nxt)
        self.assertEqual(nxt.step_type, self.expected_first_type)

    def test_current_step_advances(self) -> None:
        """Alt tür: BİRİM — her show_next_step current_step'i artırır."""
        for i in range(self.expected_count):
            self.assertEqual(self.panel.current_step, i)
            self.panel.show_next_step()
        self.assertEqual(self.panel.current_step, self.expected_count)

    def test_peek_returns_none_at_end(self) -> None:
        """Alt tür: KENAR DURUM — tüm adımlar bitince peek → None."""
        for _ in range(self.expected_count):
            self.panel.show_next_step()
        self.assertIsNone(self.panel.peek_next_step())


class TestAlicePanelStepAPI(_PanelStepAPIBase, unittest.TestCase):
    panel_factory = staticmethod(AlicePanel)
    use_alice_steps = True
    expected_first_type = StepType.HASH
    expected_count = 6


class TestBobPanelStepAPI(_PanelStepAPIBase, unittest.TestCase):
    panel_factory = staticmethod(BobPanel)
    use_alice_steps = False
    expected_first_type = StepType.KEY_UNWRAP
    expected_count = 5


if __name__ == "__main__":
    unittest.main()
