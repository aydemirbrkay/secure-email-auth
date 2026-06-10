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

    def test_has_close_only_window_controls(self):
        dialog = _SBoxReferenceDialog([("cb", "1f")])
        flags = dialog.windowFlags()

        self.assertTrue(flags & Qt.WindowType.WindowCloseButtonHint)
        self.assertFalse(flags & Qt.WindowType.WindowMinimizeButtonHint)
        self.assertFalse(flags & Qt.WindowType.WindowMaximizeButtonHint)
        self.assertEqual(dialog.windowModality(), Qt.WindowModality.NonModal)

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


if __name__ == "__main__":
    unittest.main()
