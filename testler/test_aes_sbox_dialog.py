"""AES S-Box referans diyaloğu regresyon testleri."""
from __future__ import annotations

import unittest

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHeaderView

from animation_modals.aes.sbox_dialog import _SBoxReferenceDialog
from animation_modals.base import ANIM_COLORS
from arayuz.theme import MANAGER


class TestSBoxReferenceDialog(unittest.TestCase):
    def setUp(self):
        self._original_theme = MANAGER.mode

    def tearDown(self):
        MANAGER.set_mode(self._original_theme)

    def test_highlights_every_unique_used_input(self):
        dialog = _SBoxReferenceDialog([("cb", "1f"), ("ec", "ce"), ("cb", "1f")])

        self.assertEqual(dialog.used_inputs, {"cb", "ec"})
        self.assertEqual(dialog.highlighted_cells(), {(0xC, 0xB), (0xE, 0xC)})
        self.assertIn("cb→1f", dialog.used_mappings_label.text())

    def test_has_close_and_minimize_window_controls(self):
        """Harici diyalog kapat + küçült (minimize) düğmelerini taşımalı.

        Kullanıcı diyaloğu görev çubuğuna küçültebilsin diye minimize aktiftir;
        büyüt (maximize) gerekli değildir, modal değildir.
        """
        dialog = _SBoxReferenceDialog([("cb", "1f")])
        flags = dialog.windowFlags()

        self.assertTrue(flags & Qt.WindowType.WindowCloseButtonHint)
        self.assertTrue(flags & Qt.WindowType.WindowMinimizeButtonHint)
        self.assertFalse(flags & Qt.WindowType.WindowMaximizeButtonHint)
        self.assertEqual(dialog.windowModality(), Qt.WindowModality.NonModal)

    def test_is_independent_top_level_window(self):
        """Parent verilse bile diyalog bağımsız üst-düzey penceredir.

        Owned pencere görev çubuğu düğmesi almaz ve minimize edilince köşede
        artık bırakır; bu yüzden diyalog Qt parent'ı almaz ve Qt.Window tipidir.
        """
        from PyQt6.QtWidgets import QWidget

        host = QWidget()
        dialog = _SBoxReferenceDialog([("cb", "1f")], host)

        self.assertIsNone(dialog.parent())
        self.assertEqual(dialog.windowType(), Qt.WindowType.Window)

    def test_has_no_redundant_close_button(self):
        """Pencerenin X düğmesi varken ayrı 'Kapat' butonu bulunmamalı."""
        dialog = _SBoxReferenceDialog([("cb", "1f")])

        self.assertFalse(hasattr(dialog, "close_btn"))

    def test_first_mapping_is_not_emphasized_differently(self):
        """İlk eşleme diğer vurgulu hücrelerle aynı görünmeli (kalın/büyük değil)."""
        dialog = _SBoxReferenceDialog([("cb", "1f"), ("ec", "ce")])
        first_item = dialog.table.item(0xC, 0xB)
        other_item = dialog.table.item(0xE, 0xC)

        self.assertFalse(first_item.font().bold())
        self.assertEqual(
            first_item.font().pointSize(), other_item.font().pointSize()
        )

    def test_table_stretches_to_available_space(self):
        dialog = _SBoxReferenceDialog([("cb", "1f")])

        self.assertEqual(dialog.table.rowCount(), 16)
        self.assertEqual(dialog.table.columnCount(), 16)
        self.assertEqual(
            dialog.table.horizontalHeader().sectionResizeMode(0),
            QHeaderView.ResizeMode.Stretch,
        )
        self.assertEqual(
            dialog.table.verticalHeader().sectionResizeMode(0),
            QHeaderView.ResizeMode.Stretch,
        )

    def test_dialog_fits_available_screen(self):
        dialog = _SBoxReferenceDialog([("cb", "1f")])
        available = dialog.screen().availableGeometry()

        self.assertLessEqual(dialog.width(), available.width())
        self.assertLessEqual(dialog.height(), available.height())
        self.assertLess(dialog.width(), available.width())
        self.assertLessEqual(dialog.width(), int(available.width() * 0.92))

    def test_table_has_breathing_room_and_readable_headers(self):
        dialog = _SBoxReferenceDialog([("cb", "1f")])
        outer_margins = dialog.layout().contentsMargins()
        table_margins = dialog.table_layout.contentsMargins()

        self.assertGreaterEqual(outer_margins.left(), 20)
        self.assertGreaterEqual(outer_margins.right(), 20)
        self.assertGreaterEqual(table_margins.left(), 10)
        self.assertGreaterEqual(table_margins.right(), 10)
        self.assertGreaterEqual(dialog.table.verticalHeader().width(), 36)
        self.assertGreaterEqual(dialog.table.horizontalHeader().height(), 28)

    def test_dialog_uses_theme_background_and_isolates_parent_styles(self):
        """Diyalog kendi tema zeminini taşımalı (parent stylesheet sızmasına karşı)."""
        MANAGER.set_mode("dark")
        dialog = _SBoxReferenceDialog([("cb", "1f")])

        self.assertIn("QDialog", dialog.styleSheet())
        self.assertIn(ANIM_COLORS["bg_panel"], dialog.styleSheet())
        # Bilgi şeritleri kasıtsız çerçeve taşımamalı (mavi yuvarlak çerçeve hatası).
        self.assertNotIn("border", dialog.rule_label.styleSheet())

    def test_dialog_background_follows_theme_change(self):
        """Tema değişiminde diyalog zemin stili güncellenmeli."""
        MANAGER.set_mode("dark")
        dialog = _SBoxReferenceDialog([("cb", "1f")])
        dark_style = dialog.styleSheet()

        MANAGER.set_mode("light")

        self.assertNotEqual(dialog.styleSheet(), dark_style)
        self.assertIn(ANIM_COLORS["bg_panel"], dialog.styleSheet())

    def test_open_dialog_restyles_when_theme_changes(self):
        MANAGER.set_mode("dark")
        dialog = _SBoxReferenceDialog([("cb", "1f")])
        dark_label_style = dialog.example_label.styleSheet()
        dark_highlight = dialog.table.item(0xC, 0xB).background().color().name()

        MANAGER.set_mode("light")

        self.assertNotEqual(dialog.example_label.styleSheet(), dark_label_style)
        self.assertNotEqual(
            dialog.table.item(0xC, 0xB).background().color().name(),
            dark_highlight,
        )
        self.assertEqual(
            dialog.table.item(0xC, 0xB).background().color().name(),
            QColor(ANIM_COLORS["accent_yellow"]).name(),
        )


class TestSBoxDerivationPage(unittest.TestCase):
    """Diyalog içindeki 'S-Box nasıl üretildi?' türetim sayfası testleri."""

    def setUp(self):
        self._original_theme = MANAGER.mode

    def tearDown(self):
        MANAGER.set_mode(self._original_theme)

    def test_starts_on_table_page(self):
        """Diyalog açıldığında önce referans tablosu sayfası görünür."""
        dialog = _SBoxReferenceDialog([("53", "ed")])

        self.assertEqual(dialog._stack.currentIndex(), 0)

    def test_show_derivation_switches_page_and_locks_byte(self):
        """Türetim istenince sayfa değişir ve widget o byte'a kilitlenir."""
        dialog = _SBoxReferenceDialog([("53", "ed")])

        dialog.show_derivation_for(0x53)

        self.assertEqual(dialog._stack.currentIndex(), 1)
        self.assertEqual(dialog.derivation_widget.current_byte, 0x53)
        d = dialog.derivation_widget.current_derivation
        self.assertEqual(d.inverse, 0xCA)  # 0x53'ün GF(2^8) çarpımsal tersi
        self.assertEqual(d.result, 0xED)   # S[5,3] = ed

    def test_back_button_returns_to_table(self):
        """Geri dönünce tekrar tablo sayfası gösterilir."""
        dialog = _SBoxReferenceDialog([("53", "ed")])
        dialog.show_derivation_for(0x53)

        dialog.show_table_page()

        self.assertEqual(dialog._stack.currentIndex(), 0)

    def test_clicking_table_cell_opens_its_derivation(self):
        """Tablo hücresine tıklamak o byte'ın türetimini açar."""
        dialog = _SBoxReferenceDialog([("53", "ed")])

        dialog._on_cell_clicked(0xA, 0xB)  # byte 0xAB

        self.assertEqual(dialog._stack.currentIndex(), 1)
        self.assertEqual(dialog.derivation_widget.current_byte, 0xAB)


class TestSBoxInputMatrix(unittest.TestCase):
    """Türetim sayfasının solundaki tıklanabilir girdi matrisi testleri."""

    def setUp(self):
        self._original_theme = MANAGER.mode

    def tearDown(self):
        MANAGER.set_mode(self._original_theme)

    def test_input_matrix_has_unique_inputs_in_order(self):
        """Girdi matrisi yalnız benzersiz girdileri, görülme sırasıyla taşımalı."""
        dialog = _SBoxReferenceDialog([("8e", "19"), ("75", "9d"), ("8e", "19")])

        bytes_in_grid = [byte for byte, _ in dialog._input_buttons]
        self.assertEqual(bytes_in_grid, [0x8E, 0x75])

    def test_clicking_input_cell_locks_and_plays_that_byte(self):
        """Girdi hücresine tıklamak o byte'ı kilitler, türetim sayfasını açar."""
        dialog = _SBoxReferenceDialog([("8e", "19"), ("75", "9d")])

        dialog._on_input_selected(0x75)

        self.assertEqual(dialog._stack.currentIndex(), 1)
        self.assertEqual(dialog.derivation_widget.current_byte, 0x75)
        self.assertTrue(dialog.derivation_widget._locked)
        self.assertEqual(dialog._selected_input_byte, 0x75)

    def test_empty_mappings_show_hint_and_no_buttons(self):
        """Girdi yoksa matris düğmesi olmamalı; bilgilendirme etiketi gösterilmeli."""
        dialog = _SBoxReferenceDialog([])

        self.assertEqual(dialog._input_buttons, [])
        self.assertIsNotNone(dialog.input_empty_hint)


if __name__ == "__main__":
    unittest.main()
