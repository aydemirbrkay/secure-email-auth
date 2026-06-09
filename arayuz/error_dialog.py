"""
error_dialog.py – Öğretici Kripto Hata Diyaloğu
================================================

``CryptoErrorDialog``, yakalanan bir ``CryptoError`` (veya herhangi bir
istisnayı) öğrenci diliyle 3 bölümde gösterir:

  1. Özet (başlık)
  2. "Bu ne demek?" — pedagojik açıklama
  3. "Ne yapabilirim?" — somut öneri

Teknik detay (istisna adı + ham mesaj), meraklı kullanıcı için açılır bir
bölümde gizlenir. İçerik ``explain_crypto_exception`` üzerinden gelir;
renkler ``arayuz.theme`` paletinden okunur (hardcoded hex yok).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from arayuz.theme import (
    COLORS,
    button_primary_style,
    button_secondary_style,
    card_style,
    label_title_style,
)
from kriptografi.utils import CryptoExplanation, explain_crypto_exception


class CryptoErrorDialog(QDialog):
    """Kripto istisnasını 3 bölümlü, öğretici bir diyalogda gösterir."""

    def __init__(self, exc: BaseException, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._exp: CryptoExplanation = explain_crypto_exception(exc)

        self.setWindowTitle(self._exp.title)
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setStyleSheet(
            f"QDialog {{ background: {COLORS['bg_panel']}; "
            f"color: {COLORS['text_primary']}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        # 1) Özet başlığı (kırmızı vurgu)
        title = QLabel(self._exp.title)
        title.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        title.setStyleSheet(label_title_style("accent_red"))
        title.setWordWrap(True)
        root.addWidget(title)

        # 2) "Bu ne demek?" + 3) "Ne yapabilirim?"
        root.addWidget(self._section("Bu ne demek?", self._exp.meaning,
                                     "accent_blue"))
        root.addWidget(self._section("Ne yapabilirim?", self._exp.action,
                                     "accent_green"))

        # Açılır teknik detay
        self._tech_btn = QToolButton()
        self._tech_btn.setText("Teknik detay")
        self._tech_btn.setCheckable(True)
        self._tech_btn.setArrowType(Qt.ArrowType.RightArrow)
        self._tech_btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self._tech_btn.setStyleSheet(
            f"QToolButton {{ border: none; color: {COLORS['text_muted']}; "
            f"font-size: 12px; }}"
        )
        self._tech_btn.toggled.connect(self._on_tech_toggled)
        root.addWidget(self._tech_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._tech_lbl = QLabel(self._exp.technical)
        self._tech_lbl.setWordWrap(True)
        self._tech_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._tech_lbl.setFont(QFont("Courier New", 9))
        self._tech_lbl.setStyleSheet(
            f"color: {COLORS['text_secondary']}; "
            f"background: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; "
            f"border-radius: 6px; padding: 8px;"
        )
        self._tech_lbl.setVisible(False)
        root.addWidget(self._tech_lbl)

        # Kapat butonu
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._close_btn = QPushButton("Anladım")
        self._close_btn.setStyleSheet(button_primary_style())
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)
        root.addLayout(btn_row)

    def _section(self, heading: str, body: str, accent_key: str) -> QFrame:
        """Başlık + gövde içeren tek bir bilgi kartı üretir."""
        frame = QFrame()
        frame.setStyleSheet(card_style())
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(4)

        head = QLabel(heading)
        head.setFont(QFont("IBM Plex Sans", 11, QFont.Weight.Bold))
        head.setStyleSheet(f"color: {COLORS[accent_key]}; background: transparent;")
        lay.addWidget(head)

        text = QLabel(body)
        text.setWordWrap(True)
        text.setStyleSheet(
            f"color: {COLORS['text_secondary']}; background: transparent;"
        )
        lay.addWidget(text)
        return frame

    def _on_tech_toggled(self, checked: bool) -> None:
        self._tech_lbl.setVisible(checked)
        self._tech_btn.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        # Diyalog gerekiyorsa içeriğe göre küçülür/büyür.
        self.adjustSize()
