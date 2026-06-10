# animation_modals/rsa/key_builder.py
"""RSA Anahtar İnşa Paneli — kalıcı sol panel."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint,
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget,
    QGraphicsOpacityEffect, QSizePolicy,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS, motion_effects_enabled
from . import helpers as H

# ---------------------------------------------------------------------------
# 1) Anahtar İnşa Paneli — kalıcı sol panel
# ---------------------------------------------------------------------------

class _RSAKeyBuilderWidget(QWidget):
    """
    Sol panel; anahtar alanları her adımda otomatik dolar.
    Yeni dolan alanda 600 ms süreli yeşil pulse animasyonu.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Cari demo değerlerinden alanları oluştur (her instance kendi anlık snapshot'ını alır)
        # (anahtar, doldurulduğu_adim_idx, sembol, değer, renk_anahtarı)
        self._FIELDS = [
            ("p",   0, "p",     str(H._P),    "accent_blue"),
            ("q",   0, "q",     str(H._Q),    "accent_mauve"),
            ("n",   1, "n",     str(H._N),    "accent_yellow"),
            ("phi", 2, "ϕ(n)",  str(H._PHI),  "accent_yellow"),
            ("e",   3, "e",     str(H._E),    "accent_peach"),
            ("d",   4, "d",     str(H._D),    "accent_green"),
        ]
        self._cells: dict[str, tuple[QLabel, QLabel, QFrame]] = {}
        self._public_card: QLabel | None = None
        self._private_card: QLabel | None = None
        self._last_step = -1
        self._animations: list[QPropertyAnimation] = []
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        outer.setSpacing(3)

        self._title_lbl = QLabel("ANAHTAR İNŞA PANELİ")
        self._title_lbl.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(
            f"color: {ANIM_COLORS['text_muted']}; letter-spacing: 1px;"
        )
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._title_lbl)

        # Bireysel alanlar
        for key, _, sym, _val, color_key in self._FIELDS:
            row = self._make_field_row(sym, color_key)
            outer.addWidget(row["frame"])
            self._cells[key] = (row["label"], row["value"], row["frame"])

        outer.addSpacing(4)

        # Açık ve gizli anahtar kartları (K⁺ / K⁻ akademik notasyon)
        self._public_card = self._make_key_card(
            icon_sign="+",
            title="Açık Anahtar",
            value="(?, ?)",
            color=ANIM_COLORS["accent_blue"],
        )
        outer.addWidget(self._public_card)

        self._private_card = self._make_key_card(
            icon_sign="−",
            title="Gizli Anahtar",
            value="(?, ?)",
            color=ANIM_COLORS["accent_green"],
        )
        outer.addWidget(self._private_card)

        outer.addStretch()

    @staticmethod
    def _make_field_row(symbol: str, color_key: str) -> dict:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 5px; }}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(8, 2, 8, 2)
        lay.setSpacing(6)

        sym_lbl = QLabel(symbol)
        sym_lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        sym_lbl.setStyleSheet(
            f"color: {ANIM_COLORS[color_key]}; border: none;"
        )
        sym_lbl.setMinimumWidth(34)
        lay.addWidget(sym_lbl)

        eq = QLabel("=")
        eq.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; border: none;")
        lay.addWidget(eq)

        val_lbl = QLabel("?")
        val_lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        val_lbl.setStyleSheet(
            f"color: {ANIM_COLORS['text_muted']}; border: none;"
        )
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(val_lbl, stretch=1)

        return {"frame": frame, "label": sym_lbl, "value": val_lbl}

    @staticmethod
    def _make_key_card(
        icon_sign: str, title: str, value: str, color: str,
    ) -> QLabel:
        """
        Akademik notasyondaki K⁺ / K⁻ stilini taklit eden kart.
        icon_sign: '+' (açık anahtar) ya da '−' (gizli anahtar)
        """
        lbl = QLabel()
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setText(
            f"<div style='text-align:center; color:{ANIM_COLORS['text_muted']};'>"
            f"<span style='font-size:15pt; font-weight:bold; color:{color}; "
            f"font-family: Georgia, serif;'>K<sup>{icon_sign}</sup></span>"
            f"&nbsp;&nbsp;<span style='font-size:9pt;'>{title}</span><br>"
            f"<span style='font-family: Courier New, monospace; font-size:9pt;'>{value}</span>"
            f"</div>"
        )
        lbl.setStyleSheet(
            f"QLabel {{ background: {ANIM_COLORS['bg_input']}; "
            f"border: 2px dashed {ANIM_COLORS['border']}; border-radius: 6px; "
            f"padding: 3px; }}"
        )
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def set_step(self, step_idx: int) -> None:
        """Verilen adıma göre alanları doldur ve yeni dolanları pulse ile vurgula."""
        for key, fill_step, _sym, val, color_key in self._FIELDS:
            sym_lbl, val_lbl, frame = self._cells[key]
            should_be_filled = step_idx >= fill_step
            was_filled = self._last_step >= fill_step

            if should_be_filled:
                val_lbl.setText(val)
                val_lbl.setStyleSheet(
                    f"color: {ANIM_COLORS[color_key]}; border: none; "
                    f"font-weight: bold;"
                )
                frame.setStyleSheet(
                    f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
                    f"border: 2px solid {ANIM_COLORS[color_key]}; border-radius: 6px; }}"
                )
                if not was_filled:
                    self._pulse(frame, color_key)
            else:
                val_lbl.setText("?")
                val_lbl.setStyleSheet(
                    f"color: {ANIM_COLORS['text_muted']}; border: none;"
                )
                frame.setStyleSheet(
                    f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
                    f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 6px; }}"
                )

        # Açık anahtar — Adım 4 sonrası (e ve n biliniyor)
        # Cari (instance-snapshot) değerlerden oku; FIELDS aynı anda set edildi
        e_val = self._FIELDS[4][3]   # 'e' alanının str değeri
        n_val = self._FIELDS[2][3]   # 'n' alanının str değeri
        d_val = self._FIELDS[5][3]   # 'd' alanının str değeri
        self._set_key_card(
            self._public_card, icon_sign="+", title="Açık Anahtar",
            color=ANIM_COLORS["accent_blue"],
            filled=(step_idx >= 3),
            value=f"(n, e) = ({n_val}, {e_val})" if step_idx >= 3 else "(?, ?)",
        )
        if step_idx >= 3 and self._last_step < 3:
            self._pulse(self._public_card, "accent_blue")

        # Gizli anahtar — Adım 5 sonrası (d ve n biliniyor)
        self._set_key_card(
            self._private_card, icon_sign="−", title="Gizli Anahtar",
            color=ANIM_COLORS["accent_green"],
            filled=(step_idx >= 4),
            value=f"(n, d) = ({n_val}, {d_val})" if step_idx >= 4 else "(?, ?)",
        )
        if step_idx >= 4 and self._last_step < 4:
            self._pulse(self._private_card, "accent_green")

        self._last_step = step_idx

    def restyle(self) -> None:
        """Tema değişiminde alanları/kartları durum bozmadan yeniden boyar."""
        self._title_lbl.setStyleSheet(
            f"color: {ANIM_COLORS['text_muted']}; letter-spacing: 1px;"
        )
        # set_step mevcut adımı yeniden uygular; aynı adım olduğu için pulse
        # tetiklenmez (was_filled == should_be_filled) → görsel sıçrama olmaz.
        self.set_step(self._last_step if self._last_step >= 0 else 0)

    @staticmethod
    def _set_key_card(
        lbl: QLabel, icon_sign: str, title: str, color: str,
        filled: bool, value: str,
    ) -> None:
        """Kart içeriğini ve çerçeve stilini günceller."""
        text_color = ANIM_COLORS["text_primary"] if filled else ANIM_COLORS["text_muted"]
        lbl.setText(
            f"<div style='text-align:center; color:{text_color};'>"
            f"<span style='font-size:15pt; font-weight:bold; color:{color}; "
            f"font-family: Georgia, serif;'>K<sup>{icon_sign}</sup></span>"
            f"&nbsp;&nbsp;<span style='font-size:9pt;'>{title}</span><br>"
            f"<span style='font-family: Courier New, monospace; font-size:9pt; "
            f"font-weight:bold;'>{value}</span>"
            f"</div>"
        )
        if filled:
            lbl.setStyleSheet(
                f"QLabel {{ background: {ANIM_COLORS['bg_input']}; "
                f"border: 2px solid {color}; border-radius: 6px; "
                f"padding: 3px; }}"
            )
        else:
            lbl.setStyleSheet(
                f"QLabel {{ background: {ANIM_COLORS['bg_input']}; "
                f"border: 2px dashed {ANIM_COLORS['border']}; border-radius: 6px; "
                f"padding: 3px; }}"
            )

    def _pulse(self, target: QWidget, color_key: str) -> None:
        """600 ms opacity pulse: 0.4 → 1.0 ile yumuşak parıltı."""
        if not motion_effects_enabled():
            target.setGraphicsEffect(None)
            return

        effect = QGraphicsOpacityEffect(target)
        target.setGraphicsEffect(effect)
        effect.setOpacity(0.4)

        anim = QPropertyAnimation(effect, b"opacity", target)
        anim.setDuration(600)
        anim.setStartValue(0.4)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._animations.append(anim)


