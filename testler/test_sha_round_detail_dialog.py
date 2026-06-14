"""SHA-256 round bit-düzeyi drill-down sihirbazı testleri.

Test türü: BİRİM + SMOKE (PyQt widget davranışı + çizim güvenliği).

Amaç: Drill-down'ın gerçek round_detail değerlerini taşıdığını, manuel
(tıkla-ilerle, otomatik oynatma yok) gezindiğini, tüm sahnelerin hatasız
çizildiğini ve diyagram düğmesinin diyaloğu gerçek veriyle açtığını doğrular.
"""
from __future__ import annotations

import unittest

from animation_modals.sha256.round_detail_dialog import (
    _SHARoundDetailDialog,
    _SHARoundDetailWidget,
    _SCENE_COUNT,
    _bits,
)
from animation_modals.sha256_pure import sha256_steps
from arayuz.theme import MANAGER


class TestSHARoundDetailDialog(unittest.TestCase):

    def setUp(self):
        self._original_theme = MANAGER.mode
        self._data = sha256_steps(b"Hello World")
        self._detail = self._data["round_detail"]

    def tearDown(self):
        MANAGER.set_mode(self._original_theme)

    def _make_dialog(self) -> _SHARoundDetailDialog:
        return _SHARoundDetailDialog(
            self._detail,
            h0_init=self._data["pre_final_h"][0],
            final_word=self._data["final_h_parts"][0],
            final_hash=self._data["final_hash"],
        )

    def test_dialog_has_minimize_button(self):
        """Harici round drill-down diyaloğu görev çubuğuna küçültülebilmeli."""
        from PyQt6.QtCore import Qt

        dialog = self._make_dialog()
        flags = dialog.windowFlags()

        self.assertTrue(flags & Qt.WindowType.WindowMinimizeButtonHint)
        self.assertTrue(flags & Qt.WindowType.WindowCloseButtonHint)
        self.assertEqual(dialog.windowType(), Qt.WindowType.Window)

    def test_bits_helper_is_32_chars(self):
        """_bits, 8-hane hex'i 32 karakter ikiliye çevirmeli."""
        self.assertEqual(len(_bits("00000000")), 32)
        self.assertEqual(_bits("0000000f"), "0" * 28 + "1111")
        self.assertEqual(_bits("ffffffff"), "1" * 32)

    def test_dialog_carries_real_round_detail(self):
        """Diyalog gerçek round_detail + köprü değerlerini taşımalı."""
        dialog = self._make_dialog()
        self.assertEqual(dialog.wizard.detail["new_a"],
                         self._data["final_working"][0])
        self.assertEqual(dialog.wizard.final_word,
                         self._data["final_h_parts"][0])
        self.assertEqual(dialog.wizard.final_hash[:8],
                         self._data["final_h_parts"][0])

    def test_wizard_is_manual_and_advances_on_click(self):
        """Otomatik oynatma yok: start() sahne 0; tıkla-ilerle son sahnede durur."""
        dialog = self._make_dialog()
        wizard = dialog.wizard
        wizard.start()
        self.assertEqual(wizard._scene(), 0)
        self.assertFalse(hasattr(wizard, "_timer"))
        for _ in range(_SCENE_COUNT + 3):
            wizard._advance_scene()
        self.assertEqual(wizard._scene(), _SCENE_COUNT - 1)

    def test_all_scenes_paint_without_error(self):
        """6 sahnenin tümü hatasız çizilmeli (bit satırları dâhil) — paint smoke."""
        dialog = self._make_dialog()
        wizard = dialog.wizard
        wizard.resize(900, 460)
        for scene in range(_SCENE_COUNT):
            wizard.jump_to_scene(scene)
            self.assertEqual(wizard._scene(), scene)
            wizard.grab()

    def test_clicking_strip_jumps_to_scene(self):
        dialog = self._make_dialog()
        wizard = dialog.wizard
        wizard.resize(900, 460)
        wizard.jump_to_scene(4)
        self.assertEqual(wizard._scene(), 4)
        wizard.jump_to_scene(0)
        self.assertEqual(wizard._scene(), 0)

    def test_body_click_does_not_advance(self):
        """Gövdeye (şerit dışına) tıklamak sahneyi DEĞİŞTİRMEMELİ (kazara atlama)."""
        from PyQt6.QtCore import QPointF, Qt as _Qt
        from PyQt6.QtGui import QMouseEvent
        dialog = self._make_dialog()
        wizard = dialog.wizard
        wizard.resize(900, 460)
        wizard.jump_to_scene(0)
        # Şeridin ALTINDA (gövde) bir nokta — _strip_box_at None döndürür.
        pos = QPointF(400, 300)
        ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, pos,
                         _Qt.MouseButton.LeftButton, _Qt.MouseButton.LeftButton,
                         _Qt.KeyboardModifier.NoModifier)
        wizard.mousePressEvent(ev)
        self.assertEqual(wizard._scene(), 0)

    def test_nav_buttons_change_scene(self):
        """◀ Geri / İleri ▶ düğmeleri sahneyi değiştirmeli."""
        dialog = self._make_dialog()
        self.assertEqual(dialog.wizard._scene(), 0)
        dialog._go_next()
        self.assertEqual(dialog.wizard._scene(), 1)
        dialog._go_prev()
        self.assertEqual(dialog.wizard._scene(), 0)
        dialog._go_prev()  # 0'da kalmalı (alt sınır)
        self.assertEqual(dialog.wizard._scene(), 0)

    def test_dialog_restyles_on_theme_change(self):
        from animation_modals.base import ANIM_COLORS
        MANAGER.set_mode("dark")
        dialog = self._make_dialog()
        dark = dialog.styleSheet()
        MANAGER.set_mode("light")
        self.assertNotEqual(dialog.styleSheet(), dark)
        self.assertIn(ANIM_COLORS["bg_panel"], dialog.styleSheet())


class TestSHARoundDetailButton(unittest.TestCase):

    def test_diagram_button_opens_dialog_with_current_round_detail(self):
        """Düğme, GÖSTERİLEN round'un detayını açmalı.

        Son round (64) görüntülenirken açılan detayın A çıkışı (new_a), son
        bloğun çalışma değişkeni A'ya eşittir (eski 'hep round 64' davranışı
        artık gösterilen round'a bağlı)."""
        from animation_modals.sha256.window import SHA256AnimationWindow
        import hashlib

        msg = "Hello World"
        window = SHA256AnimationWindow(
            message=msg,
            expected_hash=hashlib.sha256(msg.encode()).hexdigest(),
        )
        self.assertTrue(window._round_detail_btn.isEnabled())
        # Son round snapshot'ına (round 64) git, sonra düğmeye bas.
        last_step = 3 + len(window._snaps) - 1
        window._diag_jump_to_step(last_step)
        window._round_detail_btn.click()
        self.assertEqual(
            window._round_detail_dialog.wizard.detail["new_a"],
            window._data["final_working"][0],
        )
        self.assertTrue(window._round_detail_dialog.is_final_round)

    def test_diagram_button_first_round_shows_first_round(self):
        """İlk round (R1) görüntülenirken düğme R1'in detayını açmalı (round 64 değil)."""
        from animation_modals.sha256.window import SHA256AnimationWindow
        import hashlib

        msg = "Hello World"
        window = SHA256AnimationWindow(
            message=msg,
            expected_hash=hashlib.sha256(msg.encode()).hexdigest(),
        )
        window._diag_jump_to_step(3)  # ilk snapshot = round 1
        window._round_detail_btn.click()
        self.assertEqual(window._round_detail_dialog.wizard.detail["round_no"], 1)
        self.assertFalse(window._round_detail_dialog.is_final_round)


if __name__ == "__main__":
    unittest.main()
