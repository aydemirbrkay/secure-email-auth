"""S-Box türetim animasyon widget'ı (_SBoxDerivationWidget) testleri."""
from __future__ import annotations

import unittest

from animation_modals.aes.sbox_derivation import (
    _SBoxDerivationWidget,
    _CYCLE_TICKS,
)
from animation_modals.aes_pure import derive_sbox_value


class TestSBoxDerivationWidget(unittest.TestCase):
    def test_default_byte_has_valid_derivation(self):
        """Varsayılan byte için türetim resmi değerle tutarlı olmalı."""
        widget = _SBoxDerivationWidget()
        d = widget.current_derivation

        self.assertEqual(d.result, derive_sbox_value(widget.current_byte).result)

    def test_set_byte_locks_and_updates_value(self):
        """set_byte byte'ı günceller ve otomatik gezinmeyi kilitler."""
        widget = _SBoxDerivationWidget()
        widget.set_mappings([("8a", "7e"), ("8f", "73")])

        widget.set_byte(0x53)

        self.assertEqual(widget.current_byte, 0x53)
        self.assertTrue(widget._locked)

    def test_set_byte_rejects_out_of_range(self):
        """0-255 dışındaki byte ValueError ile reddedilmeli."""
        widget = _SBoxDerivationWidget()

        with self.assertRaises(ValueError):
            widget.set_byte(300)

    def test_mappings_take_unique_inputs_in_order(self):
        """Eşlemelerden yalnızca benzersiz girdiler, görülme sırasıyla alınır."""
        widget = _SBoxDerivationWidget()

        widget.set_mappings([("8a", "7e"), ("8f", "73"), ("8a", "7e")])

        self.assertEqual(widget._mapping_bytes, [0x8A, 0x8F])
        self.assertEqual(widget.current_byte, 0x8A)

    def test_cycle_advances_to_next_mapping_byte(self):
        """Bir döngü tamamlanınca (kilitsiz) sonraki eşleme byte'ına geçilir."""
        widget = _SBoxDerivationWidget()
        widget.set_mappings([("8a", "7e"), ("8f", "73")])

        for _ in range(_CYCLE_TICKS):
            widget._advance()

        self.assertEqual(widget.current_byte, 0x8F)

    def test_locked_byte_does_not_advance(self):
        """Kilitli byte, döngü tamamlansa da değişmemeli."""
        widget = _SBoxDerivationWidget()
        widget.set_mappings([("8a", "7e"), ("8f", "73")])
        widget.set_byte(0x53)

        for _ in range(_CYCLE_TICKS + 5):
            widget._advance()

        self.assertEqual(widget.current_byte, 0x53)

    def test_active_step_progresses_through_four_boxes(self):
        """Aktif adım 0'dan başlayıp sırayla son kutuya (3) ilerlemeli."""
        widget = _SBoxDerivationWidget()

        self.assertEqual(widget._active_step(), 0)
        for _ in range(_CYCLE_TICKS - 1):
            widget._advance()
        self.assertEqual(widget._active_step(), 3)


if __name__ == "__main__":
    unittest.main()
