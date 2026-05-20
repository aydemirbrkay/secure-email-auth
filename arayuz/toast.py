"""
toast.py – Doğrulama Bildirimi Widget
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from arayuz.theme import COLORS


class VerificationToast(QWidget):
    """Doğrulama sonucunu gösteren açılır bildirim kartı."""

    _LIFE_SECS = 8
    _CARD_WIDTH = 460

    def __init__(self, is_valid: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._secs = self._LIFE_SECS

        accent = COLORS["accent_green"] if is_valid else COLORS["accent_red"]
        title_text = "Doğrulama Başarılı" if is_valid else "Doğrulama Başarısız"

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 26)
        root.setSpacing(0)

        card = QFrame(self)
        card.setObjectName("toastCard")
        card.setStyleSheet(
            "#toastCard {"
            f" background: {COLORS['bg_panel']};"
            f" border: 1px solid {COLORS['border']};"
            " border-radius: 10px;"
            "}"
        )
        card.setFixedWidth(self._CARD_WIDTH)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(38)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 170))
        card.setGraphicsEffect(shadow)
        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        strip = QFrame(card)
        strip.setFixedHeight(3)
        strip.setStyleSheet(
            f"background: {accent};"
            " border-top-left-radius: 10px;"
            " border-top-right-radius: 10px;"
            " border: none;"
        )
        card_lay.addWidget(strip)

        header_w = QWidget(card)
        header = QVBoxLayout(header_w)
        header.setContentsMargins(26, 20, 26, 16)
        header.setSpacing(6)

        eyebrow_font = QFont("IBM Plex Sans", 9, QFont.Weight.Bold)
        eyebrow_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        eyebrow = QLabel("GÜVENLİ E-POSTA")
        eyebrow.setFont(eyebrow_font)
        eyebrow.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        header.addWidget(eyebrow)

        title_lbl = QLabel(title_text)
        title_lbl.setFont(QFont("Georgia", 18, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
        header.addWidget(title_lbl)
        card_lay.addWidget(header_w)

        divider = QFrame(card)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {COLORS['border']}; border: none;")
        card_lay.addWidget(divider)

        body_w = QWidget(card)
        body = QVBoxLayout(body_w)
        body.setContentsMargins(26, 18, 26, 16)
        body.setSpacing(12)

        if is_valid:
            items = [
                ("Kimlik Doğrulama", "Authentication"),
                ("Mesaj Bütünlüğü", "Integrity"),
                ("Gizlilik", "Confidentiality"),
            ]
            for tr, en in items:
                body.addLayout(self._make_row(accent, tr, en))
        else:
            err_title = QLabel("İmza doğrulanamadı")
            err_title.setFont(QFont("IBM Plex Sans", 12, QFont.Weight.DemiBold))
            err_title.setStyleSheet(f"color: {accent}; background: transparent;")
            body.addWidget(err_title)

            err_desc = QLabel(
                "Mesaj değiştirilmiş ya da gönderici kimliği sahte olabilir."
            )
            err_desc.setFont(QFont("IBM Plex Sans", 11))
            err_desc.setStyleSheet(
                f"color: {COLORS['text_secondary']}; background: transparent;"
            )
            err_desc.setWordWrap(True)
            body.addWidget(err_desc)

        card_lay.addWidget(body_w)

        footer_w = QWidget(card)
        footer = QHBoxLayout(footer_w)
        footer.setContentsMargins(26, 10, 18, 16)
        footer.setSpacing(10)

        self._countdown_lbl = QLabel(self._format_countdown())
        self._countdown_lbl.setFont(QFont("IBM Plex Sans", 10))
        self._countdown_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; background: transparent;"
        )
        footer.addWidget(self._countdown_lbl)
        footer.addStretch()

        self._close_btn = QPushButton("Kapat")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet(
            "QPushButton {"
            " background: transparent;"
            f" border: 1px solid {COLORS['border']};"
            " border-radius: 6px;"
            f" color: {COLORS['text_secondary']};"
            " font-weight: 600;"
            " font-size: 11px;"
            " padding: 7px 20px;"
            "}"
            "QPushButton:hover {"
            f" background: {COLORS['bg_card']};"
            f" border-color: {accent};"
            f" color: {accent};"
            "}"
        )
        self._close_btn.clicked.connect(self.close)
        footer.addWidget(self._close_btn)
        card_lay.addWidget(footer_w)

        self.adjustSize()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _make_row(self, accent: str, tr: str, en: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        row.setContentsMargins(0, 0, 0, 0)

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background: {accent}; border-radius: 4px; border: none;"
        )
        dot_wrap = QWidget()
        dot_lay = QVBoxLayout(dot_wrap)
        dot_lay.setContentsMargins(0, 5, 0, 0)
        dot_lay.setSpacing(0)
        dot_lay.addWidget(dot, alignment=Qt.AlignmentFlag.AlignTop)
        dot_wrap.setFixedWidth(10)
        row.addWidget(dot_wrap, alignment=Qt.AlignmentFlag.AlignTop)

        tr_lbl = QLabel(tr)
        tr_lbl.setFont(QFont("IBM Plex Sans", 12, QFont.Weight.DemiBold))
        tr_lbl.setStyleSheet(
            f"color: {COLORS['text_primary']}; background: transparent;"
        )
        row.addWidget(tr_lbl)
        row.addStretch()

        en_font = QFont("IBM Plex Sans", 10)
        en_font.setItalic(True)
        en_lbl = QLabel(en)
        en_lbl.setFont(en_font)
        en_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; background: transparent;"
        )
        row.addWidget(en_lbl)
        return row

    def _format_countdown(self) -> str:
        return f"Otomatik kapanıyor  ·  {self._secs} sn"

    def _tick(self) -> None:
        self._secs -= 1
        if self._secs <= 0:
            self.close()
        else:
            self._countdown_lbl.setText(self._format_countdown())

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        par = self.parent()
        if par:
            pg = par.geometry()
            sg = self.frameGeometry()
            self.move(
                pg.x() + (pg.width() - sg.width()) // 2,
                pg.y() + (pg.height() - sg.height()) // 2,
            )
