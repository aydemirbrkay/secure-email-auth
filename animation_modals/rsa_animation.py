# animation_modals/rsa_animation.py
"""
RSAAnimationWindow v2 — RSA-2048 anahtar üretimini görsel olarak animasyonla anlatır.

Yedi adım:
  1) p ve q seçimi (asal eleği)
  2) n = p × q
  3) φ(n) = (p−1)(q−1)
  4) Açık üs e seçimi (gcd doğrulaması)
  5) Gizli üs d (Genişletilmiş Öklid Algoritması)
  6) DER ve Base64 kodlaması
  7) Demo ↔ gerçek 2048-bit anahtar eşleşmesi

Kalıcı sol panel "Anahtar İnşa Paneli" her adımda otomatik olarak dolar.
"""
from __future__ import annotations

import base64
from collections.abc import Callable
from math import gcd

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint,
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget,
    QGraphicsOpacityEffect, QSizePolicy, QGridLayout,
)

from .base import CryptoAnimationWindow, ANIM_COLORS


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def _der_int(v: int) -> bytes:
    """Bir tam sayıyı DER INTEGER olarak kodlar."""
    b = v.to_bytes((v.bit_length() + 8) // 8, "big")
    if b[0] >= 0x80:
        b = b"\x00" + b
    return bytes([0x02, len(b)]) + b


def _eea_steps(a: int, b: int) -> list[tuple[int, int, int, int, int]]:
    """
    Genişletilmiş Öklid: a·s + b·t = gcd(a, b)
    Returns: list of (i, q_i, r_i, s_i, t_i)
    """
    r0, r1 = a, b
    s0, s1 = 1, 0
    t0, t1 = 0, 1
    rows = [(0, 0, r0, s0, t0), (1, 0, r1, s1, t1)]
    i = 2
    while r1 != 0:
        q = r0 // r1
        r0, r1 = r1, r0 - q * r1
        s0, s1 = s1, s0 - q * s1
        t0, t1 = t1, t0 - q * t1
        rows.append((i, q, r1, s1, t1))
        i += 1
    return rows


# ---------------------------------------------------------------------------
# Tez değerleri — tab:RSAExample ile birebir uyumlu (chapter1.tex)
# Tüm widget'lar bu sabitleri __init__'lerinde okur.
# ---------------------------------------------------------------------------

_P:   int = 61
_Q:   int = 53
_N:   int = _P * _Q          # 3233
_PHI: int = (_P - 1) * (_Q - 1)  # 3120
_E:   int = 17
_D:   int = pow(_E, -1, _PHI)    # 2753

assert (_E * _D) % _PHI == 1, "RSA invariant ihlal edildi: e · d ≢ 1 (mod φ)"

_DER_N:   bytes = _der_int(_N)
_DER_E:   bytes = _der_int(_E)
_DER_SEQ: bytes = bytes([0x30, len(_DER_N) + len(_DER_E)]) + _DER_N + _DER_E
_B64_DEMO: str  = base64.b64encode(_DER_SEQ).decode()


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
            ("p",   0, "p",     str(_P),    "accent_blue"),
            ("q",   0, "q",     str(_Q),    "accent_mauve"),
            ("n",   1, "n",     str(_N),    "accent_yellow"),
            ("phi", 2, "φ(n)",  str(_PHI),  "accent_yellow"),
            ("e",   3, "e",     str(_E),    "accent_peach"),
            ("d",   4, "d",     str(_D),    "accent_green"),
        ]
        self._cells: dict[str, tuple[QLabel, QLabel, QFrame]] = {}
        self._public_card: QLabel | None = None
        self._private_card: QLabel | None = None
        self._last_step = -1
        self._animations: list[QPropertyAnimation] = []
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(4)

        title = QLabel("ANAHTAR İNŞA PANELİ")
        title.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title)

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
        lay.setContentsMargins(8, 3, 8, 3)
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
            f"<span style='font-size:18pt; font-weight:bold; color:{color}; "
            f"font-family: Georgia, serif;'>K<sup>{icon_sign}</sup></span>"
            f"&nbsp;&nbsp;<span style='font-size:9pt;'>{title}</span><br>"
            f"<span style='font-family: Courier New, monospace; font-size:9pt;'>{value}</span>"
            f"</div>"
        )
        lbl.setStyleSheet(
            f"QLabel {{ background: {ANIM_COLORS['bg_input']}; "
            f"border: 2px dashed {ANIM_COLORS['border']}; border-radius: 6px; "
            f"padding: 6px; }}"
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
            value=f"(e, n) = ({e_val}, {n_val})" if step_idx >= 3 else "(?, ?)",
        )
        if step_idx >= 3 and self._last_step < 3:
            self._pulse(self._public_card, "accent_blue")

        # Gizli anahtar — Adım 5 sonrası (d ve n biliniyor)
        self._set_key_card(
            self._private_card, icon_sign="−", title="Gizli Anahtar",
            color=ANIM_COLORS["accent_green"],
            filled=(step_idx >= 4),
            value=f"(d, n) = ({d_val}, {n_val})" if step_idx >= 4 else "(?, ?)",
        )
        if step_idx >= 4 and self._last_step < 4:
            self._pulse(self._private_card, "accent_green")

        self._last_step = step_idx

    @staticmethod
    def _set_key_card(
        lbl: QLabel, icon_sign: str, title: str, color: str,
        filled: bool, value: str,
    ) -> None:
        """Kart içeriğini ve çerçeve stilini günceller."""
        text_color = ANIM_COLORS["text_primary"] if filled else ANIM_COLORS["text_muted"]
        lbl.setText(
            f"<div style='text-align:center; color:{text_color};'>"
            f"<span style='font-size:18pt; font-weight:bold; color:{color}; "
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
                f"padding: 6px; }}"
            )
        else:
            lbl.setStyleSheet(
                f"QLabel {{ background: {ANIM_COLORS['bg_input']}; "
                f"border: 2px dashed {ANIM_COLORS['border']}; border-radius: 6px; "
                f"padding: 6px; }}"
            )

    def _pulse(self, target: QWidget, color_key: str) -> None:
        """600 ms opacity pulse: 0.4 → 1.0 ile yumuşak parıltı."""
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


# ---------------------------------------------------------------------------
# 2) Adım 1 — Asal Eleği
# ---------------------------------------------------------------------------

class _PrimeSieveWidget(QWidget):
    """2..100 arası sayılar 10×10 grid; asallar yeşil; p=61, q=53 yanıp söner."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._blink = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._timer.start(700)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        self._blink = not self._blink
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        margin = 8
        cols = 10
        rows = 10
        header_h = 22
        footer_h = 22
        avail_w = W - 2 * margin
        avail_h = H - 2 * margin - header_h - footer_h
        cell = max(20, min(42, min(avail_w // cols, avail_h // rows)))
        grid_w = cell * cols
        grid_h = cell * rows
        ox = (W - grid_w) // 2
        oy = margin + header_h

        # Üst başlık
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(
            QRect(0, 2, W, header_h),
            Qt.AlignmentFlag.AlignCenter,
            "1–100 arası sayılar  •  asallar yeşil  •  p ve q seçili",
        )

        for n in range(1, 101):
            i = n - 1
            r, c = divmod(i, cols)
            x = ox + c * cell
            y = oy + r * cell

            is_prime = _is_prime(n)
            is_pq = (n == _P or n == _Q)

            if is_pq:
                # Yanıp sönen sarı çerçeve
                border_col = (
                    QColor(ANIM_COLORS["accent_yellow"])
                    if self._blink
                    else QColor(ANIM_COLORS["accent_peach"])
                )
                fill = QColor(ANIM_COLORS["accent_yellow"])
                fill.setAlpha(80 if self._blink else 140)
                p.setBrush(QBrush(fill))
                p.setPen(QPen(border_col, 2))
            elif is_prime:
                p.setBrush(QBrush(QColor(ANIM_COLORS["accent_green"] + "33")))
                p.setPen(QPen(QColor(ANIM_COLORS["accent_green"]), 1))
            else:
                p.setBrush(QBrush(QColor(ANIM_COLORS["bg_card"])))
                p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))

            p.drawRoundedRect(x + 2, y + 2, cell - 4, cell - 4, 4, 4)

            if is_pq:
                p.setPen(QColor(ANIM_COLORS["text_primary"]))
                p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            elif is_prime:
                p.setPen(QColor(ANIM_COLORS["accent_green"]))
                p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            else:
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                p.setFont(QFont("Courier New", 9))
            p.drawText(
                QRect(x, y, cell, cell),
                Qt.AlignmentFlag.AlignCenter,
                str(n),
            )

        # Açıklama
        p.setFont(QFont("Georgia", 10))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        legend_y = oy + grid_h + 10
        p.drawText(
            QRect(margin, legend_y, W - 2 * margin, 24),
            Qt.AlignmentFlag.AlignCenter,
            f"Seçilenler:  p = {_P}    q = {_Q}",
        )
        p.end()


# ---------------------------------------------------------------------------
# 3) Adım 2 — Çarpma  n = p × q
# ---------------------------------------------------------------------------

class _MultiplicationWidget(QWidget):
    """p × q animasyonu — q'nun her basamağı için ayrı satır + toplam."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Çarpma satırlarını cari _P, _Q'ya göre dinamik üret
        self._ROWS = self._compute_rows(_P, _Q)
        self._reveal = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    @staticmethod
    def _compute_rows(p: int, q: int) -> list[tuple[str, str, int]]:
        """q'nun her basamağı için 'p × <basamak değeri>' satırı + toplam."""
        rows: list[tuple[str, str, int]] = []
        for i, ch in enumerate(reversed(str(q))):
            digit = int(ch)
            if digit == 0:
                continue
            place = digit * (10 ** i)
            rows.append((f"{p} × {place}", f"= {p * place}", 0))
        rows.append(("─" * 18, "", 1))
        rows.append(("Toplam", f"= {p * q}", 2))
        return rows

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._reveal = 0
        self.update()
        self._timer.start(700)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if self._reveal < len(self._ROWS) + 1:
            self._reveal += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        cx = W // 2
        top_y = 8

        # Başlık formülü
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(
            QRect(0, top_y, W, 26),
            Qt.AlignmentFlag.AlignCenter,
            "n = p × q",
        )

        # p ve q kutuları
        box_w, box_h = 70, 42
        gap = 22
        boxes_y = top_y + 36
        p_x = cx - box_w - gap
        q_x = cx + gap

        self._draw_boxed(p, p_x, boxes_y, box_w, box_h, str(_P),
                         ANIM_COLORS["accent_blue"], font_size=14)
        # × sembolü
        p.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(
            QRect(p_x + box_w, boxes_y, gap * 2, box_h),
            Qt.AlignmentFlag.AlignCenter,
            "×",
        )
        self._draw_boxed(p, q_x, boxes_y, box_w, box_h, str(_Q),
                         ANIM_COLORS["accent_mauve"], font_size=14)

        # Çarpma satırları (kademeli açılır)
        rows_y = boxes_y + box_h + 14
        line_h = 22
        p.setFont(QFont("Courier New", 11))
        for i, (left, right, kind) in enumerate(self._ROWS):
            if i >= self._reveal:
                break
            y = rows_y + i * line_h
            if kind == 2:
                p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
                p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
            elif kind == 1:
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
            else:
                p.setPen(QColor(ANIM_COLORS["text_secondary"]))
                p.setFont(QFont("Courier New", 11))
            p.drawText(
                QRect(cx - 180, y, 180, line_h),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                left + "  ",
            )
            p.drawText(
                QRect(cx, y, 180, line_h),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                right,
            )

        # Sonuç kutusu (tüm satırlar açıldıktan sonra)
        if self._reveal >= len(self._ROWS) + 1:
            result_y = rows_y + (len(self._ROWS) + 1) * line_h
            self._draw_boxed(
                p, cx - 70, result_y, 140, 38, f"n = {_N}",
                ANIM_COLORS["accent_yellow"], font_size=12,
            )

        p.end()

    @staticmethod
    def _draw_boxed(
        p: QPainter, x: int, y: int, w: int, h: int, text: str,
        color: str, font_size: int = 16,
    ) -> None:
        fill = QColor(color)
        fill.setAlpha(60)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(color), 2))
        p.drawRoundedRect(x, y, w, h, 8, 8)
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.setFont(QFont("Georgia", font_size, QFont.Weight.Bold))
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)


# ---------------------------------------------------------------------------
# 4) Adım 3 — Euler Totient  φ(n) = (p−1)(q−1)
# ---------------------------------------------------------------------------

class _TotientWidget(QWidget):
    """φ(n) hesabı: (p−1) ve (q−1) elde edilir, sonra çarpılır."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._phase = 0
        self.update()
        self._timer.start(800)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if self._phase < 4:
            self._phase += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        cx = W // 2

        # Formül başlığı
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 8, W, 26), Qt.AlignmentFlag.AlignCenter,
                   "φ(n) = (p − 1) × (q − 1)")

        # Üst satır: p ve q kutularından (p−1) ve (q−1) türetimi
        row1_y = 44
        box_w, box_h = 60, 38
        gap = 18
        # Toplam satır genişliği: 2*box_w + gap (arrow) + box_w   (sol blok) + space + sağ blok
        # Sol blok: box(p) + arrow + box(p-1) = 60 + 24 + 60 = 144
        # Sağ blok: aynı = 144
        # Aralık: 30
        total_w = 144 * 2 + 30
        left_x = cx - total_w // 2

        # p kutusu → p−1 kutusu
        self._draw_box(p, left_x, row1_y, box_w, box_h,
                       f"p = {_P}", ANIM_COLORS["accent_blue"])
        self._draw_arrow(p, left_x + box_w, row1_y + box_h // 2,
                         left_x + box_w + 22, row1_y + box_h // 2)
        if self._phase >= 1:
            self._draw_box(p, left_x + box_w + 24, row1_y, box_w, box_h,
                           f"p−1 = {_P-1}", ANIM_COLORS["accent_green"])

        # q kutusu → q−1 kutusu
        right_x = left_x + 144 + 30
        self._draw_box(p, right_x, row1_y, box_w, box_h,
                       f"q = {_Q}", ANIM_COLORS["accent_mauve"])
        self._draw_arrow(p, right_x + box_w, row1_y + box_h // 2,
                         right_x + box_w + 22, row1_y + box_h // 2)
        if self._phase >= 2:
            self._draw_box(p, right_x + box_w + 24, row1_y, box_w, box_h,
                           f"q−1 = {_Q-1}", ANIM_COLORS["accent_green"])

        # Orta satır: çarpma
        if self._phase >= 3:
            mid_y = row1_y + box_h + 18
            p.setFont(QFont("Courier New", 12))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(
                QRect(0, mid_y, W, 24),
                Qt.AlignmentFlag.AlignCenter,
                f"({_P-1})  ×  ({_Q-1})  =  {(_P-1)*(_Q-1)}",
            )

        # Alt satır: sonuç
        if self._phase >= 4:
            result_y = row1_y + box_h + 56
            self._draw_box(
                p, cx - 90, result_y, 180, 44,
                f"φ(n) = {_PHI}", ANIM_COLORS["accent_yellow"],
                font_size=13,
            )
        p.end()

    @staticmethod
    def _draw_box(
        p: QPainter, x: int, y: int, w: int, h: int, text: str,
        color: str, font_size: int = 11,
    ) -> None:
        fill = QColor(color)
        fill.setAlpha(60)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(color), 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.setFont(QFont("Georgia", font_size, QFont.Weight.Bold))
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)

    @staticmethod
    def _draw_arrow(p: QPainter, x1: int, y1: int, x2: int, y2: int) -> None:
        pen = QPen(QColor(ANIM_COLORS["text_muted"]), 2)
        p.setPen(pen)
        p.drawLine(x1, y1, x2, y2)
        # Ok ucu
        p.setBrush(QBrush(QColor(ANIM_COLORS["text_muted"])))
        head = QPolygon([
            QPoint(x2, y2),
            QPoint(x2 - 8, y2 - 4),
            QPoint(x2 - 8, y2 + 4),
        ])
        p.drawPolygon(head)


# ---------------------------------------------------------------------------
# 5) Adım 4 — gcd doğrulaması
# ---------------------------------------------------------------------------

class _GCDWidget(QWidget):
    """e=17 seçimi ve gcd(e, φ(n))=1 doğrulaması — Öklid adımları akar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Öklid adımları: gcd(17, 3120)
        a, b = _E, _PHI
        steps = []
        while b != 0:
            steps.append((a, b, a % b))
            a, b = b, a % b
        self._steps = steps  # son adımdaki b=0 öncesi a, gcd
        self._gcd_value = a
        self._reveal = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._reveal = 0
        self.update()
        self._timer.start(550)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if self._reveal < len(self._steps) + 1:
            self._reveal += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx = W // 2

        # Başlık
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 8, W, 26), Qt.AlignmentFlag.AlignCenter,
                   f"Aday:  e = {_E}    Koşul:  gcd(e, φ(n)) = 1")

        # Öklid adımları
        rows_y = 42
        line_h = 22
        p.setFont(QFont("Courier New", 11))
        for i, (a, b, r) in enumerate(self._steps):
            if i >= self._reveal:
                break
            y = rows_y + i * line_h

            is_last = (r == 0)
            color = (ANIM_COLORS["accent_green"] if is_last
                     else ANIM_COLORS["text_secondary"])
            p.setPen(QColor(color))
            text = f"{a}  =  {a // b} × {b}  +  {r}"
            p.drawText(QRect(0, y, W, line_h),
                       Qt.AlignmentFlag.AlignCenter, text)

        # Sonuç
        if self._reveal >= len(self._steps) + 1:
            result_y = rows_y + (len(self._steps) + 1) * line_h + 8
            success = (self._gcd_value == 1)
            color = (ANIM_COLORS["accent_green"] if success
                     else ANIM_COLORS["accent_peach"])
            fill = QColor(color)
            fill.setAlpha(60)
            box_w, box_h = 280, 44
            x = cx - box_w // 2
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor(color), 2))
            p.drawRoundedRect(x, result_y, box_w, box_h, 6, 6)

            p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            mark = "✓ Geçerli" if success else "✗ Reddedildi"
            p.drawText(
                QRect(x, result_y, box_w, box_h),
                Qt.AlignmentFlag.AlignCenter,
                f"GCD = {self._gcd_value}    {mark}",
            )
        p.end()


# ---------------------------------------------------------------------------
# 6) Adım 5 — Genişletilmiş Öklid Algoritması (EEA)  →  d
# ---------------------------------------------------------------------------

class _EEAWidget(QWidget):
    """
    Genişletilmiş Öklid Algoritması tablosu + canlı hesaplama şeridi.

    Faz makinesi (her satır için):
      STRIP_SHOW (1100 ms) — sırada yerleştirilecek satırın altında bir
        hesaplama şeridi belirir; q, r, s, t formülleri sayısal değerleriyle
        görünür. Önceki satırın r₀, r₁, s₀, s₁, t₀, t₁ hücreleri vurgulanır.
      STRIP_FADE (400 ms) — şerit söner, satır tabloya yerleşir.
      Sonraki satıra geç.

    Tüm satırlar yerleşince GCD=1 vurgusu, "(durma satırı)", d hesabı,
    doğrulama satırı sırayla görünür (mevcut hâliyle).
    """

    _COLS = ["i", "bölüm", "kalan", "s", "t"]
    _COL_WIDTHS = [32, 60, 76, 76, 76]

    # Faz tick aralığı (ms) — base interval, fazlar bunun katlarıyla biter
    _TICK_MS = 80
    _STRIP_SHOW_TICKS = 14   # 14 × 80 = 1120 ms
    _STRIP_FADE_TICKS = 5    # 5 × 80 = 400 ms

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._rows = _eea_steps(_PHI, _E)

        # Faz makinesi durumu
        self._placed_count = 0   # tabloya yerleşmiş satır sayısı
        self._phase = "DONE"     # "STRIP_SHOW" | "STRIP_FADE" | "BETWEEN" | "DONE"
        self._phase_tick = 0
        self._final_reveal = 0   # 0=hiç, 1=d kutusu, 2=doğrulama satırı

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        # Sıfırla ve baştan başlat
        # İlk iki satır seed (i=0, i=1) — bunlar şeritle gösterilmez
        # Direkt yerleşir; faz makinesi i=2'den başlar.
        self._placed_count = 2
        self._phase = "STRIP_SHOW"
        self._phase_tick = 0
        self._final_reveal = 0
        self.update()
        self._timer.start(self._TICK_MS)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        self._phase_tick += 1

        if self._phase == "STRIP_SHOW" and self._phase_tick >= self._STRIP_SHOW_TICKS:
            self._phase = "STRIP_FADE"
            self._phase_tick = 0
        elif self._phase == "STRIP_FADE" and self._phase_tick >= self._STRIP_FADE_TICKS:
            # Şerit söndü — satır artık yerleşmiş kabul edilir
            self._placed_count += 1
            self._phase_tick = 0
            if self._placed_count >= len(self._rows):
                self._phase = "DONE"
                # Final ortaya çıkma: d kutusu, sonra doğrulama
                self._final_reveal = 0
                self._final_timer = QTimer(self)
                self._final_timer.timeout.connect(self._final_tick)
                self._final_timer.start(420)
                self._timer.stop()
                self.update()
                return
            self._phase = "STRIP_SHOW"

        self.update()

    def _final_tick(self) -> None:
        self._final_reveal += 1
        if self._final_reveal >= 2:
            self._final_timer.stop()
        self.update()

    # --- Çizim ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Başlık
        p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 4, W, 22), Qt.AlignmentFlag.AlignCenter,
                   "Genişletilmiş Öklid Algoritması")
        p.setFont(QFont("Georgia", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 26, W, 18), Qt.AlignmentFlag.AlignCenter,
                   f"Amaç: e·d ≡ 1 (mod φ)   ·   φ = {_PHI},  e = {_E}")

        # Tablo merkezleme
        total_col_w = sum(self._COL_WIDTHS)
        annot_w = 130
        ox = (W - total_col_w - annot_w) // 2
        header_y = 50
        row_h = 20

        gcd_row_idx = len(self._rows) - 2

        # Başlık satırı
        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_blue"]))
        x = ox
        for col, w in zip(self._COLS, self._COL_WIDTHS):
            p.drawText(QRect(x, header_y, w, row_h),
                       Qt.AlignmentFlag.AlignCenter, col)
            x += w
        p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))
        p.drawLine(ox, header_y + row_h, ox + total_col_w, header_y + row_h)

        # Yerleşmiş satırlar
        # Aktif olan satır indeksi (şerit gösterilen) self._placed_count
        active_row_idx = (
            self._placed_count
            if self._phase in ("STRIP_SHOW", "STRIP_FADE")
            else -1
        )
        prev_row_idx = active_row_idx - 1 if active_row_idx > 1 else -1

        # Yerleşmiş satırları çiz (önceki satırın hücreleri gerekirse vurgulanır)
        for ri in range(self._placed_count):
            self._draw_row(
                p, ri, ox, header_y, row_h, total_col_w, annot_w, gcd_row_idx,
                highlight_operands=(ri == prev_row_idx and self._phase == "STRIP_SHOW"),
            )

        # Aktif şerit (varsa)
        if self._phase in ("STRIP_SHOW", "STRIP_FADE"):
            strip_y = header_y + (self._placed_count + 1) * row_h + 8
            opacity = 1.0
            if self._phase == "STRIP_FADE":
                opacity = 1.0 - (self._phase_tick / self._STRIP_FADE_TICKS)
            self._draw_strip(
                p, ox, strip_y, total_col_w + annot_w, active_row_idx, opacity,
            )

        # d hesaplama bloğu — tüm satırlar yerleşince
        last_t = self._rows[gcd_row_idx][4]
        if self._phase == "DONE" and self._final_reveal >= 1:
            calc_y = header_y + (len(self._rows) + 1) * row_h + 12
            p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_green"]))
            p.drawText(
                QRect(0, calc_y, W, 22),
                Qt.AlignmentFlag.AlignCenter,
                f"d  =  t  mod  φ  =  {last_t}  mod  {_PHI}  =  {_D}",
            )
            if last_t < 0:
                p.setFont(QFont("Georgia", 8))
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                p.drawText(
                    QRect(0, calc_y + 22, W, 16),
                    Qt.AlignmentFlag.AlignCenter,
                    "(negatif → +φ ekle)",
                )

        # Doğrulama
        if self._phase == "DONE" and self._final_reveal >= 2:
            verify_y = header_y + (len(self._rows) + 1) * row_h + 50
            p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            check = (_E * _D) % _PHI
            p.drawText(
                QRect(0, verify_y, W, 20),
                Qt.AlignmentFlag.AlignCenter,
                f"Doğrulama:  e × d  mod  φ  =  {_E} × {_D}  mod  {_PHI}  =  {check}   ✓",
            )
        p.end()

    def _draw_row(
        self, p: QPainter, ri: int, ox: int, header_y: int, row_h: int,
        total_col_w: int, annot_w: int, gcd_row_idx: int,
        highlight_operands: bool,
    ) -> None:
        i, q, r, s, t = self._rows[ri]
        y = header_y + (ri + 1) * row_h + 2

        is_gcd_row = (ri == gcd_row_idx) and self._placed_count > gcd_row_idx
        is_terminator = ri == len(self._rows) - 1 and self._placed_count == len(self._rows)

        # Vurgulama: GCD=1 satırı yeşil arka plan
        if is_gcd_row:
            fill = QColor(ANIM_COLORS["accent_green"])
            fill.setAlpha(50)
            p.setBrush(QBrush(fill))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(ox, y - 1, total_col_w, row_h)

        # "Önceki satır operand vurgusu" — şerit aktifken bu satır vurgulanırsa
        if highlight_operands:
            fill = QColor(ANIM_COLORS["accent_blue"])
            fill.setAlpha(35)
            p.setBrush(QBrush(fill))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(ox, y - 1, total_col_w, row_h)

        # Hücre değerleri
        x = ox
        values = [str(i), str(q) if ri >= 2 else "—", str(r), str(s), str(t)]
        if is_gcd_row:
            colors = [
                ANIM_COLORS["text_primary"],
                ANIM_COLORS["text_primary"],
                ANIM_COLORS["accent_yellow"],
                ANIM_COLORS["text_primary"],
                ANIM_COLORS["accent_green"],
            ]
            font_weight = QFont.Weight.Bold
        elif is_terminator:
            muted = ANIM_COLORS["text_muted"]
            colors = [muted, muted, muted, muted, muted]
            font_weight = QFont.Weight.Normal
        else:
            colors = [
                ANIM_COLORS["text_muted"],
                ANIM_COLORS["text_secondary"],
                ANIM_COLORS["text_primary"],
                ANIM_COLORS["text_secondary"],
                ANIM_COLORS["accent_peach"],
            ]
            font_weight = QFont.Weight.Normal

        font = QFont("Courier New", 10, font_weight)
        p.setFont(font)
        for val, w, col in zip(values, self._COL_WIDTHS, colors):
            p.setPen(QColor(col))
            p.drawText(QRect(x, y, w, row_h - 2),
                       Qt.AlignmentFlag.AlignCenter, val)
            x += w

        # Sağ taraf açıklamalar
        annot_x = ox + total_col_w + 8
        if is_gcd_row:
            p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_green"]))
            p.drawText(QRect(annot_x, y, annot_w, row_h - 2),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "← GCD = 1, t'yi al")
        elif is_terminator:
            p.setFont(QFont("Georgia", 9))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(annot_x, y, annot_w, row_h - 2),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "(durma satırı)")

    def _draw_strip(
        self, p: QPainter, ox: int, y: int, w: int,
        active_row_idx: int, opacity: float,
    ) -> None:
        """Aktif satır için q, r, s, t formüllerini sayısal değerleriyle çiz."""
        if active_row_idx < 2 or active_row_idx >= len(self._rows):
            return
        # Önceki satır indeks: active - 1 → r₁ ve s₁,t₁ (current); active - 2 → r₀, s₀, t₀
        i, q, r, s, t = self._rows[active_row_idx]
        _, _, r1, s1, t1 = self._rows[active_row_idx - 1]
        _, _, r0, s0, t0 = self._rows[active_row_idx - 2]

        # Şerit kutusu
        strip_h = 90
        bg = QColor(ANIM_COLORS["bg_input"])
        bg.setAlphaF(opacity * 0.9)
        border = QColor(ANIM_COLORS["accent_blue"])
        border.setAlphaF(opacity)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, 1))
        p.drawRoundedRect(ox, y, w, strip_h, 6, 6)

        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)

        p.setFont(QFont("Courier New", 10))
        p.setPen(text_col)
        lines = [
            f"q = ⌊{r0} / {r1}⌋ = {q}",
            f"r = {r0} − {q}·{r1} = {r}",
            f"s = {s0} − {q}·{s1} = {s}",
            f"t = {t0} − {q}·{t1} = {t}",
        ]
        for li, line in enumerate(lines):
            p.drawText(QRect(ox + 12, y + 6 + li * 20, w - 24, 18),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       line)


# ---------------------------------------------------------------------------
# 7) Adım 6 — DER ve Base64 Kodlaması
# ---------------------------------------------------------------------------

class _DERByteFlowWidget(QWidget):
    """
    Sayılar → byte → DER yapısı → Base64 dönüşümü.
    Son faz: Alice'in gerçek RSA-2048 anahtarlarının oluşumunu gösterir.
    """

    def __init__(
        self, alice_b64: str, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._alice_b64 = alice_b64
        self.setMinimumHeight(360)  # Detaylı byte-grup görselleştirmesi için
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._phase = 0
        self.update()
        self._timer.start(900)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if self._phase < 4:  # 0..4 (5 phases including Alice's keys)
            self._phase += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()

        # 1) Sayılar
        y = 6
        p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "1)  Tam sayılar:")
        y += 20
        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, y, W, 20), Qt.AlignmentFlag.AlignCenter,
                   f"n = {_N}    e = {_E}")

        # 2) Byte gösterimi
        y += 26
        n_bytes = _N.to_bytes((_N.bit_length() + 7) // 8, "big")
        e_bytes = _E.to_bytes(max(1, (_E.bit_length() + 7) // 8), "big")
        if self._phase >= 1:
            p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                       "2)  Big-endian byte dizisi:")
            y += 20
            n_hex = " ".join(f"{b:02X}" for b in n_bytes)
            e_hex = " ".join(f"{b:02X}" for b in e_bytes)
            p.setFont(QFont("Courier New", 10))
            p.setPen(QColor(ANIM_COLORS["accent_blue"]))
            p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                       f"n = {_N} → {n_hex}    e = {_E} → {e_hex}")

        # 3) DER yapısı — kompakt tek-satır
        y += 24
        if self._phase >= 2:
            p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                       "3)  ASN.1 / DER paketleme:")
            y += 20
            # SEQUENCE [ 02 len(n) <n_bytes>  02 len(e) <e_bytes> ]
            der_hex = " ".join(f"{b:02X}" for b in _DER_SEQ)
            p.setFont(QFont("Courier New", 9))
            p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
            p.drawText(QRect(0, y, W, 16), Qt.AlignmentFlag.AlignCenter,
                       f"30 {len(_DER_SEQ)-2:02X}  ·  02 {len(_DER_N)-2:02X} {' '.join(f'{b:02X}' for b in _DER_N[2:])}"
                       f"  ·  02 {len(_DER_E)-2:02X} {' '.join(f'{b:02X}' for b in _DER_E[2:])}")
            y += 16
            p.setFont(QFont("Georgia", 8))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(0, y, W, 14), Qt.AlignmentFlag.AlignCenter,
                       "[SEQ] [INT n] [INT e]   →   ham byte dizisi")
            y += 14
            p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(0, y, W, 16), Qt.AlignmentFlag.AlignCenter,
                       f"DER ({len(_DER_SEQ)} bayt): {der_hex}")

        # 4) Base64 — byte gruplarını ve karakter eşleşmesini göster
        y += 22
        if self._phase >= 3:
            p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                       "4)  Base64 dönüşümü  (her 3 bayt → 4 karakter):")
            y += 20

            # 3'lü byte gruplarını ve karşılık gelen 4'lü Base64 karakter gruplarını
            # yan yana çiz
            der = _DER_SEQ
            b64 = _B64_DEMO
            # Grup sayısı: ceil(len(der) / 3), Base64 padding ile len(b64) buna karşılık gelir
            n_groups = (len(der) + 2) // 3
            group_w = 100
            total_groups_w = n_groups * group_w + (n_groups - 1) * 10
            ox = max(8, (W - total_groups_w) // 2)

            for gi in range(n_groups):
                gx = ox + gi * (group_w + 10)
                byte_chunk = der[gi * 3 : gi * 3 + 3]
                b64_chunk = b64[gi * 4 : gi * 4 + 4]

                # Üst: 3 byte'lık grup
                p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_blue"]))
                byte_hex = " ".join(f"{b:02X}" for b in byte_chunk)
                p.drawText(QRect(gx, y, group_w, 16),
                           Qt.AlignmentFlag.AlignCenter, byte_hex)

                # Ok
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                p.drawText(QRect(gx, y + 14, group_w, 12),
                           Qt.AlignmentFlag.AlignCenter, "↓")

                # Alt: 4 base64 karakteri
                p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_green"]))
                p.drawText(QRect(gx, y + 26, group_w, 18),
                           Qt.AlignmentFlag.AlignCenter, b64_chunk)

            y += 46
            # Toplam Base64
            p.setFont(QFont("Georgia", 9))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(0, y, W, 16), Qt.AlignmentFlag.AlignCenter,
                       f"= Base64 ({len(_B64_DEMO)} karakter): {_B64_DEMO}")
            y += 14

        # 5) ALICE'İN GERÇEK ANAHTARLARI — son faz
        y += 26
        if self._phase >= 4:
            # Ayraç + başlık
            p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1, Qt.PenStyle.DashLine))
            p.drawLine(40, y, W - 40, y)
            y += 6

            p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                       "↓  Aynı yöntemle Alice'in gerçek RSA-2048 anahtarları:")
            y += 22

            # Açık anahtar (K⁺)
            self._draw_real_key_box(
                p, x=12, y=y, w=W - 24, h=24,
                icon="K⁺", icon_color=ANIM_COLORS["accent_blue"],
                label="Alice Açık Anahtarı:",
                value=self._alice_b64,
            )
            y += 28

            # Gizli anahtar (K⁻) — içerik gösterilmez (güvenlik)
            self._draw_real_key_box(
                p, x=12, y=y, w=W - 24, h=24,
                icon="K⁻", icon_color=ANIM_COLORS["accent_green"],
                label="Alice Gizli Anahtarı:",
                value="(d, n) — yalnızca Alice'te tutulur",
                value_color=ANIM_COLORS["text_muted"],
                italic_value=True,
            )
        p.end()

    @staticmethod
    def _draw_real_key_box(
        p: QPainter, x: int, y: int, w: int, h: int,
        icon: str, icon_color: str,
        label: str, value: str,
        value_color: str | None = None,
        italic_value: bool = False,
    ) -> None:
        # Çerçeve
        fill = QColor(ANIM_COLORS["bg_input"])
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(icon_color), 1))
        p.drawRoundedRect(x, y, w, h, 4, 4)

        # K⁺ / K⁻ simge alanı (sol)
        icon_w = 36
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(icon_color))
        p.drawText(QRect(x + 4, y, icon_w, h),
                   Qt.AlignmentFlag.AlignCenter, icon)

        # Etiket
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        label_w = 110
        p.drawText(QRect(x + icon_w + 4, y, label_w, h),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   label)

        # Değer
        font = QFont("Courier New", 8)
        if italic_value:
            font.setItalic(True)
        p.setFont(font)
        p.setPen(QColor(value_color or ANIM_COLORS["text_primary"]))
        value_x = x + icon_w + 4 + label_w + 4
        value_w = w - (value_x - x) - 6
        # Tek satıra sığacak şekilde uzun b64'ü kırp
        max_chars = max(20, value_w // 6)
        display = value if len(value) <= max_chars else value[:max_chars - 1] + "…"
        p.drawText(QRect(value_x, y, value_w, h),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   display)


# ---------------------------------------------------------------------------
# 8) Adım 7 — Demo ↔ Gerçek Anahtar Eşleşmesi
# ---------------------------------------------------------------------------

class _KeyMatchWidget(QWidget):
    """Demo değerler ile gerçek 2048-bit anahtarın yan yana karşılaştırması."""

    def __init__(
        self,
        alice_b64: str,
        bob_b64: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._alice_b64 = alice_b64
        self._bob_b64 = bob_b64
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        # Üst: yan yana iki kart
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        # Sol: demo
        demo = self._make_card(
            "DEMO",
            f"p = {_P}\n"
            f"q = {_Q}\n"
            f"n = {_N}\n"
            f"φ(n) = {_PHI}\n"
            f"e = {_E}\n"
            f"d = {_D}\n"
            f"Modülüs: 12 bit",
            ANIM_COLORS["accent_blue"],
        )
        cards_row.addWidget(demo, stretch=1)

        # Orta: ≈ sembolü
        approx = QLabel("≈")
        approx.setFont(QFont("Georgia", 28, QFont.Weight.Bold))
        approx.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        approx.setAlignment(Qt.AlignmentFlag.AlignCenter)
        approx.setMaximumWidth(40)
        cards_row.addWidget(approx)

        # Sağ: gerçek
        real = self._make_card(
            "GERÇEK (RSA-2048)",
            f"p, q ≈ 1024-bit asal\n"
            f"n ≈ 617 ondalık hane\n"
            f"e = 65537\n"
            f"d ≈ 2048-bit\n"
            f"Modülüs: 2048 bit\n"
            f"Base64 ≈ 360 karakter",
            ANIM_COLORS["accent_green"],
        )
        cards_row.addWidget(real, stretch=1)

        outer.addLayout(cards_row)

        # Gerçek anahtar önizlemesi (alt) — kelime kaydırma ile genişlikten bağımsız
        keys_lbl = QLabel(
            f"<b>Alice açık anahtarı:</b> {self._alice_b64[:48]}…<br>"
            f"<b>Bob açık anahtarı:</b> {self._bob_b64[:48]}…"
        )
        keys_lbl.setFont(QFont("Courier New", 8))
        keys_lbl.setStyleSheet(
            f"QLabel {{ color: {ANIM_COLORS['text_secondary']}; "
            f"background: {ANIM_COLORS['bg_input']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 4px; padding: 4px 6px; }}"
        )
        keys_lbl.setWordWrap(True)
        keys_lbl.setTextFormat(Qt.TextFormat.RichText)
        outer.addWidget(keys_lbl)

        # Alt: aynı matematik mesajı
        msg = QLabel(
            "Aynı matematik · farklı boyut: tüm adımlar gerçek 2048-bit p ve q ile aynen uygulanır."
        )
        msg.setFont(QFont("Georgia", 9))
        msg.setStyleSheet(
            f"QLabel {{ color: {ANIM_COLORS['accent_yellow']}; "
            f"background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 5px; padding: 6px; }}"
        )
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(msg)

    @staticmethod
    def _make_card(title: str, body: str, color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(2)

        t = QLabel(title)
        t.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {color}; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)

        b = QLabel(body)
        b.setFont(QFont("Courier New", 9))
        b.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']}; border: none;")
        b.setWordWrap(True)
        b.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(b, stretch=1)

        return f


# ---------------------------------------------------------------------------
# 9) Ana Pencere
# ---------------------------------------------------------------------------

class RSAAnimationWindow(CryptoAnimationWindow):
    """
    RSA-2048 anahtar üretimi animasyonu — yeni görsel tasarım.

    Parametreler:
      alice_pub_b64: Alice'in açık anahtar Base64 önizlemesi
      bob_pub_b64  : Bob'un açık anahtar Base64 önizlemesi
    """

    _TITLES = [
        "Adım 1 / 7 — p ve q Seçimi",
        "Adım 2 / 7 — n = p × q",
        "Adım 3 / 7 — φ(n) = (p − 1)(q − 1)",
        "Adım 4 / 7 — Açık Üs e Seçimi",
        "Adım 5 / 7 — Gizli Üs d  (Genişletilmiş Öklid)",
        "Adım 6 / 7 — DER ve Base64 Kodlaması",
        "Adım 7 / 7 — Gerçek Anahtarlarla Eşleşme",
    ]

    _CAPTIONS = [
        "p ve q rastgele iki büyük asaldır; n ve φ(n) hesabının temelini oluştururlar.",
        "n = p × q  →  modülüs; hem açık hem gizli anahtarda yer alır.",
        "φ(n) = (p − 1)(q − 1)  →  Euler totient fonksiyonu.",
        "gcd(e, φ(n)) = 1  koşulu sağlanmalı; e açık anahtarın üs bileşenidir.",
        "d, e'nin φ(n) modülünde tersidir:  e · d ≡ 1  (mod φ).",
        "Anahtar dosyada DER yapısında, satır içinde Base64 olarak kodlanır.",
        "Aynı matematik · farklı boyut: demo 12-bit n, gerçek 2048-bit n.",
    ]

    def __init__(
        self,
        alice_pub_b64: str,
        bob_pub_b64: str,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self._alice_b64 = alice_pub_b64
        self._bob_b64 = bob_pub_b64
        super().__init__(
            "RSA-2048 Anahtar Üretimi",
            len(self._TITLES) - 1,  # Son adım _show_match_result tarafından işlenir
            manual_mode=True,
            on_close=on_close,
        )

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        # Üst: adım başlığı (kompakt)
        self._step_lbl = QLabel()
        self._step_lbl.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        self._step_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._step_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_lbl.setMaximumHeight(22)
        self.content_layout.addWidget(self._step_lbl)

        # Orta: yatay split — sol KeyBuilder, sağ Stack
        split = QHBoxLayout()
        split.setSpacing(6)
        split.setContentsMargins(0, 0, 0, 0)

        # Sol: KeyBuilder (dar)
        kb_frame = QFrame()
        kb_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        kb_layout = QVBoxLayout(kb_frame)
        kb_layout.setContentsMargins(0, 0, 0, 0)
        self._kb = _RSAKeyBuilderWidget()
        kb_layout.addWidget(self._kb)
        kb_frame.setMinimumWidth(155)
        kb_frame.setMaximumWidth(210)
        split.addWidget(kb_frame, stretch=0)

        # Sağ: 7 sayfalı stack
        stack_frame = QFrame()
        stack_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        stack_layout = QVBoxLayout(stack_frame)
        stack_layout.setContentsMargins(4, 4, 4, 4)

        self._stack = QStackedWidget()
        self._page_widgets: list[QWidget] = [
            _PrimeSieveWidget(),
            _MultiplicationWidget(),
            _TotientWidget(),
            _GCDWidget(),
            _EEAWidget(),
            _DERByteFlowWidget(self._alice_b64),
            _KeyMatchWidget(self._alice_b64, self._bob_b64),
        ]
        for w in self._page_widgets:
            self._stack.addWidget(w)
        stack_layout.addWidget(self._stack)
        split.addWidget(stack_frame, stretch=1)

        split_holder = QWidget()
        split_holder.setLayout(split)
        self.content_layout.addWidget(split_holder, stretch=1)

        # Alt: kompakt açıklama
        self._caption = QLabel()
        self._caption.setFont(QFont("Georgia", 9))
        self._caption.setStyleSheet(
            f"QLabel {{ color: {ANIM_COLORS['text_secondary']}; "
            f"background: {ANIM_COLORS['bg_input']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 5px; padding: 4px 8px; }}"
        )
        self._caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._caption.setWordWrap(True)
        self._caption.setMaximumHeight(40)
        self.content_layout.addWidget(self._caption)

    # ------------------------------------------------------------------
    # Adım render'ı
    # ------------------------------------------------------------------

    def _render_step(self, idx: int) -> None:
        self._step_lbl.setText(self._TITLES[idx])
        self._stack.setCurrentIndex(idx)
        self._kb.set_step(idx)
        self._caption.setText(self._CAPTIONS[idx])
        self._fade_in_current_page()

    def _show_match_result(self) -> None:
        # Son adım — index 6
        self._step_lbl.setText(self._TITLES[6])
        self._stack.setCurrentIndex(6)
        self._kb.set_step(6)
        self._caption.setText(self._CAPTIONS[6])
        self._fade_in_current_page()

    def _fade_in_current_page(self) -> None:
        """Aktif sayfaya 220 ms opacity 0→1 fade-in uygula."""
        page = self._stack.currentWidget()
        if page is None:
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        anim = QPropertyAnimation(effect, b"opacity", page)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
