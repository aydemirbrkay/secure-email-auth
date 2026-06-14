"""AES-GCM keystream sihirbazı diyaloğu ve düğme bağlantısı testleri."""
from __future__ import annotations

import unittest

from animation_modals.aes.keystream_dialog import (
    _KeystreamReferenceDialog,
    _SCENE_COUNT,
    _matrix_from_bytes,
)
from animation_modals.base import ANIM_COLORS
from arayuz.theme import MANAGER


class TestKeystreamWizardDialog(unittest.TestCase):
    """Keystream sihirbazının gerçek değer, sahne akışı ve tema sözleşmesini sınar."""

    def setUp(self):
        self._original_theme = MANAGER.mode
        self.keystream = bytes(range(16))
        self.nonce = bytes(range(12))

    def tearDown(self):
        MANAGER.set_mode(self._original_theme)

    def test_dialog_carries_real_keystream_counter_and_nonce(self):
        """Diyalog gerçek keystream, nonce ve türetilmiş sayaç bloğunu taşımalı."""
        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)

        self.assertEqual(dialog.keystream, self.keystream)
        self.assertEqual(dialog.nonce, self.nonce)
        self.assertEqual(dialog.counter_block, self.nonce + b"\x00\x00\x00\x02")
        self.assertEqual(dialog.wizard.counter_block, self.nonce + b"\x00\x00\x00\x02")
        self.assertEqual(dialog.wizard.keystream, self.keystream)

    def test_dialog_has_minimize_button(self):
        """Harici keystream diyaloğu görev çubuğuna küçültülebilmeli (minimize aktif)."""
        from PyQt6.QtCore import Qt

        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)
        flags = dialog.windowFlags()

        self.assertTrue(flags & Qt.WindowType.WindowMinimizeButtonHint)
        self.assertTrue(flags & Qt.WindowType.WindowCloseButtonHint)
        # Bagimsiz ust-duzey pencere: gorev cubugu dugmesi + normal minimize.
        self.assertEqual(dialog.windowType(), Qt.WindowType.Window)

    def test_matrix_from_bytes_is_column_major(self):
        """16 bayt AES column-major 4×4 matrise yerleşmeli (m[r][c] = data[c*4+r])."""
        data = bytes(range(16))
        matrix = _matrix_from_bytes(data)
        self.assertEqual(matrix[0][0], "00")
        self.assertEqual(matrix[1][0], "01")
        self.assertEqual(matrix[0][1], "04")
        self.assertEqual(matrix[3][3], "0f")

    def test_wizard_is_manual_and_advances_on_click(self):
        """Otomatik oynatma yok: start() sahne 0'da bırakır; tıkla-ilerle son sahnede durur."""
        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)
        wizard = dialog.wizard

        wizard.start()
        self.assertEqual(wizard._scene(), 0)
        self.assertFalse(hasattr(wizard, "_timer"))

        for _ in range(_SCENE_COUNT + 3):       # son sahnede satüre olmalı
            wizard._advance_scene()
        self.assertEqual(wizard._scene(), _SCENE_COUNT - 1)

    def test_all_scenes_paint_without_error(self):
        """Her sahne (üretim-önce sıra) hatasız çizilmeli — paint smoke."""
        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)
        wizard = dialog.wizard
        wizard.resize(820, 420)
        for scene in range(_SCENE_COUNT):
            wizard.jump_to_scene(scene)
            self.assertEqual(wizard._scene(), scene)
            wizard.grab()  # paintEvent'i zorla

    def test_clicking_scene_strip_jumps_to_that_scene(self):
        """Üstteki ilerleme kutularına 'tıklamak' o sahneye atlamalı (buton işlevi)."""
        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)
        wizard = dialog.wizard
        wizard.resize(800, 400)

        wizard.jump_to_scene(2)
        self.assertEqual(wizard._scene(), 2)
        wizard.jump_to_scene(0)
        self.assertEqual(wizard._scene(), 0)

    def test_dialog_restyles_when_theme_changes(self):
        """Açık diyalog tema değişiminde yeni panel rengini kullanmalı."""
        MANAGER.set_mode("dark")
        dialog = _KeystreamReferenceDialog(self.keystream, self.nonce)
        dark_style = dialog.styleSheet()

        MANAGER.set_mode("light")

        self.assertNotEqual(dialog.styleSheet(), dark_style)
        self.assertIn(ANIM_COLORS["bg_panel"], dialog.styleSheet())

    def test_keystream_button_opens_dialog_with_round_result(self):
        """XOR sayfasındaki keystream düğmesi gerçek round sonucunu diyaloğa aktarmalı."""
        from animation_modals import AESAnimationWindow

        window = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"mesaj",
            expected_ct_hex="00" * 5,
            nonce=self.nonce,
        )

        window._keystream_btn.click()

        self.assertEqual(
            window._keystream_dialog.keystream,
            bytes.fromhex(window._final_block_hex),
        )
        self.assertEqual(window._keystream_dialog.nonce, self.nonce)

    def test_gcm_prep_keystream_button_opens_same_reference(self):
        """GCM hazırlık ekranındaki S-Box tarzı düğme de aynı gerçek referansı açmalı."""
        from animation_modals import AESAnimationWindow

        window = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"mesaj",
            expected_ct_hex="00" * 5,
            nonce=self.nonce,
        )

        window._gcm_prep_keystream_btn.click()

        self.assertEqual(
            window._keystream_dialog.keystream,
            bytes.fromhex(window._final_block_hex),
        )


class TestAESFullNavigation(unittest.TestCase):
    """Sayfa-içi 'Devam ▶' kaldırıldı; tüm zincir global İleri/Geri ile gezilmeli."""

    def _gcm_window(self):
        from animation_modals import AESAnimationWindow
        return AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"mesaj",
            expected_ct_hex="00" * 5,
            nonce=bytes(range(12)),
        )

    def test_gcm_page_has_no_internal_continue_button(self):
        """GCM hazırlık sayfasında artık sayfa-içi Devam düğmesi olmamalı."""
        window = self._gcm_window()
        self.assertFalse(hasattr(window, "_gcm_prep_continue_btn"))

    def test_ileri_traverses_full_chain_to_match(self):
        """İleri ▶ tek başına intro → prep0 → prep1 → rounds → match gezmeli."""
        window = self._gcm_window()
        seen = [getattr(window, "_nav_phase", "intro")]
        for _ in range(200):
            if getattr(window, "_nav_phase", "intro") == "match":
                break
            window._advance_step()
            seen.append(window._nav_phase)
        self.assertEqual(window._nav_phase, "match")
        for phase in ("prep0", "prep1", "rounds", "match"):
            self.assertIn(phase, seen)

    def test_geri_traverses_back_to_intro(self):
        """Match'e gidildikten sonra ◀ Geri tek başına intro'ya dönebilmeli."""
        window = self._gcm_window()
        for _ in range(200):
            if getattr(window, "_nav_phase", "intro") == "match":
                break
            window._advance_step()
        for _ in range(200):
            if window._nav_phase == "intro":
                break
            window._go_back()
        self.assertEqual(window._nav_phase, "intro")


if __name__ == "__main__":
    unittest.main()
