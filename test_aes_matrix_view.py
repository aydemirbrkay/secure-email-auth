"""
test_aes_matrix_view.py — _AESMatrixView ve _AESStateCompareWidget birim testleri
=================================================================================
QPainter çizimini test edemeyiz (pixel doğrulaması yok); state yönetimi,
animasyon timer kurulumu, callback çağrılması gibi invariant'ları test ederiz.
Görsel doğrulama manuel.
"""
import sys
import unittest

from PyQt6.QtWidgets import QApplication

# QWidget alt sınıfları için tek bir QApplication örneği gereklidir.
_app = QApplication.instance() or QApplication(sys.argv)


class TestAESMatrixViewBasics(unittest.TestCase):
    """_AESMatrixView temel state yönetimi."""

    def _make_view(self):
        from animation_modals.aes_matrix_view import _AESMatrixView
        return _AESMatrixView(label_title="Test")

    def test_class_exists(self):
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESMatrixView"))

    def test_constructs_without_error(self):
        view = self._make_view()
        self.assertIsNotNone(view)

    def test_default_state_is_4x4_zeros(self):
        view = self._make_view()
        self.assertEqual(view._state, [["00"] * 4 for _ in range(4)])

    def test_set_state_stores_matrix(self):
        view = self._make_view()
        matrix = [[f"{r}{c}" for c in range(4)] for r in range(4)]
        view.set_state(matrix)
        self.assertEqual(view._state, matrix)

    def test_set_state_stops_active_animation(self):
        view = self._make_view()
        view._anim_timer.start(40)  # sahte aktif animasyon
        self.assertTrue(view._anim_timer.isActive())
        view.set_state([["FF"] * 4 for _ in range(4)])
        self.assertFalse(view._anim_timer.isActive())


class TestAESMatrixViewAnimation(unittest.TestCase):
    """_AESMatrixView animasyon timer ve callback davranışı."""

    def _make_view(self):
        from animation_modals.aes_matrix_view import _AESMatrixView
        return _AESMatrixView()

    def test_play_animation_starts_timer(self):
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("AddRoundKey", before, after)
        self.assertTrue(view._anim_timer.isActive())
        self.assertEqual(view._op, "AddRoundKey")
        self.assertEqual(view._tick, 0)
        self.assertGreater(view._total_ticks, 0)

    def test_play_animation_unknown_op_raises(self):
        view = self._make_view()
        with self.assertRaises(ValueError):
            view.play_animation("BogusOp", [], [])

    def test_play_animation_stores_round_key(self):
        view = self._make_view()
        rk = [["AA"] * 4 for _ in range(4)]
        view.play_animation(
            "AddRoundKey",
            [["00"] * 4 for _ in range(4)],
            [["FF"] * 4 for _ in range(4)],
            round_key=rk,
        )
        self.assertEqual(view._round_key, rk)

    def test_stop_animation_advances_to_end(self):
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("AddRoundKey", before, after)
        view.stop_animation()
        self.assertFalse(view._anim_timer.isActive())
        self.assertEqual(view._tick, view._total_ticks)
        self.assertEqual(view._state, after)

    def test_on_tick_advances_and_completes(self):
        """_total_ticks tick'inden sonra timer durmalı, callback çağrılmalı."""
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        callback_calls = []
        view.play_animation(
            "AddRoundKey", before, after,
            on_done=lambda: callback_calls.append(True),
        )
        # _total_ticks kadar manuel tick at
        total = view._total_ticks
        for _ in range(total):
            view._on_tick()
        self.assertFalse(view._anim_timer.isActive())
        self.assertEqual(view._state, after)
        self.assertEqual(callback_calls, [True])

    def test_replay_reuses_last_params(self):
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("ShiftRows", before, after)
        view._tick = 50  # animasyon ortasında
        view.replay()
        self.assertEqual(view._tick, 0)
        self.assertEqual(view._op, "ShiftRows")

    def test_replay_without_prior_animation_is_noop(self):
        view = self._make_view()
        view.replay()  # hata olmamalı
        self.assertIsNone(view._op)


if __name__ == "__main__":
    unittest.main()
