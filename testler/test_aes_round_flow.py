"""AES Tüm Akış yerleşim regresyon testleri."""
from __future__ import annotations

import unittest

from PyQt6.QtGui import QFontMetrics

from animation_modals.aes.round_flow import _AESRoundFlowWidget


def _matrix(value: str) -> list[list[str]]:
    return [[value] * 4 for _ in range(4)]


def _rounds() -> list[dict]:
    return [
        {
            "after_add_round_key": _matrix(f"{index:02x}"),
            "after_sub_bytes": _matrix("11"),
            "after_shift_rows": _matrix("22"),
            "after_mix_columns": _matrix("33"),
        }
        for index in range(15)
    ]


class TestAESRoundFlowLayout(unittest.TestCase):
    def _make_widget(self) -> _AESRoundFlowWidget:
        return _AESRoundFlowWidget(
            _rounds(),
            [_matrix(f"{index:02x}") for index in range(15)],
            _matrix("00"),
        )

    def test_content_width_contains_rightmost_annotation(self):
        widget = self._make_widget()
        rightmost = (
            widget._column_positions()[-1]
            + widget._CELL_W
            + widget._NOTE_GAP
            + widget._NOTE_W
            + widget._RIGHT_MARGIN
        )

        self.assertGreaterEqual(widget.sizeHint().width(), rightmost)
        self.assertGreaterEqual(widget.minimumWidth(), rightmost)

    def test_header_cells_fit_all_titles(self):
        widget = self._make_widget()
        metrics = QFontMetrics(widget._HEADER_FONT)

        for title in widget._COL_TITLES:
            with self.subTest(title=title):
                self.assertLessEqual(metrics.horizontalAdvance(title) + 12,
                                     widget._CELL_W)


if __name__ == "__main__":
    unittest.main()
