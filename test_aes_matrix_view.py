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

    def test_addroundkey_overlay_draws_without_error(self):
        """AddRoundKey overlay paint event'i hata vermeden çağrılır."""
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "AddRoundKey",
            [["00"] * 4 for _ in range(4)],
            [["FF"] * 4 for _ in range(4)],
            round_key=[["AA"] * 4 for _ in range(4)],
        )
        view._tick = 30  # XOR_PER_ROW fazı
        # Bir QPixmap'a render et — pixel doğrulamayız ama hata fırlamamalı
        pix = QPixmap(view.width(), view.height())
        p = QPainter(pix)
        view._draw_overlay(p, 24, 24)
        p.end()


class TestAESStateCompareWidget(unittest.TestCase):
    """_AESStateCompareWidget kapsayıcı widget."""

    def _make_widget(self):
        from animation_modals.aes_matrix_view import _AESStateCompareWidget
        return _AESStateCompareWidget()

    def test_class_exists(self):
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESStateCompareWidget"))

    def test_constructs_without_error(self):
        w = self._make_widget()
        self.assertIsNotNone(w)
        # Önceki ve şimdiki view'lar erişilebilir olmalı
        self.assertTrue(hasattr(w, "_prev_view"))
        self.assertTrue(hasattr(w, "_curr_view"))
        # Yeniden Oynat butonu
        self.assertTrue(hasattr(w, "_replay_btn"))

    def test_start_step_sets_prev_state_and_plays_curr(self):
        w = self._make_widget()
        before = [[f"b{r}{c}" for c in range(4)] for r in range(4)]
        after = [[f"a{r}{c}" for c in range(4)] for r in range(4)]
        w.start_step("AddRoundKey", before, after, op_color="#5B8EC2")
        # Önceki view'da before donmuş olmalı
        self.assertEqual(w._prev_view._state, before)
        # Şimdiki view animasyon başlatmış olmalı
        self.assertEqual(w._curr_view._op, "AddRoundKey")
        self.assertTrue(w._curr_view._anim_timer.isActive())

    def test_start_step_sets_arrow_label(self):
        w = self._make_widget()
        w.start_step(
            "ShiftRows",
            [["00"] * 4] * 4, [["FF"] * 4] * 4,
            op_color="#5B8EC2",
        )
        self.assertIn("ShiftRows", w._arrow_label.text())

    def test_show_final_sets_both_to_same_state(self):
        w = self._make_widget()
        final = [[f"f{r}{c}" for c in range(4)] for r in range(4)]
        w.show_final(final)
        self.assertEqual(w._prev_view._state, final)
        self.assertEqual(w._curr_view._state, final)
        # Animasyon yok
        self.assertIsNone(w._curr_view._op)

    def test_replay_button_triggers_curr_replay(self):
        w = self._make_widget()
        before = [["00"] * 4] * 4
        after = [["FF"] * 4] * 4
        w.start_step("AddRoundKey", before, after, op_color="#5B8EC2")
        # Sahte ilerleme
        w._curr_view._tick = 30
        # Butonu programatik tıkla
        w._replay_btn.click()
        # _tick sıfırlanmış olmalı
        self.assertEqual(w._curr_view._tick, 0)


if __name__ == "__main__":
    unittest.main()
