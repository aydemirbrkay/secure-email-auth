# animation_modals/rsa_animation.py
"""
RSAAnimationWindow v2 — RSA-2048 anahtar üretimini görsel olarak animasyonla anlatır.

Sekiz adım:
  1) p ve q seçimi (asal eleği)
  2) n = p × q
  3) ϕ(n) = (p−1)(q−1)
  4) Açık üs e seçimi (gcd doğrulaması)
  5) Gizli üs d (Genişletilmiş Öklid Algoritması)
  6) DER ve Base64 kodlaması
  7) Demo ↔ gerçek 2048-bit anahtar eşleşmesi
  8) Şifreleme/Deşifreleme turu (m → c → m')

Kalıcı sol panel "Anahtar İnşa Paneli" her adımda otomatik olarak dolar.
"""
from __future__ import annotations

import base64
import random
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
    QGraphicsOpacityEffect, QSizePolicy,
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

# Asal havuzu — RSAAnimationWindow her açıldığında bu havuzdan rastgele
# iki asal seçer (kullanıcı her demo'da farklı sayılar görür, eğitsel
# çeşitlilik). Tezdeki textbook örneği (p=61, q=53) bu havuzun bir alt
# kümesidir; rastgele seçim onu da içerir.
_PRIME_POOL: list[int] = [
    n for n in range(11, 100)
    if all(n % d for d in range(2, int(n ** 0.5) + 1))
]

# Modül seviyesi cari demo değerleri. Başlangıç değerleri tezdeki örnek;
# RSAAnimationWindow oluşturulurken _reseed_demo() bunları değiştirir.
_P:   int = 61
_Q:   int = 53
_N:   int = _P * _Q
_PHI: int = (_P - 1) * (_Q - 1)
_E:   int = 17
_D:   int = pow(_E, -1, _PHI)

# Tam sayıyı Unicode üst-simgeye çevir (RSA formüllerinde m^e yerine mᵉ için)
_SUP_TRANS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

def _to_sup(n: int | str) -> str:
    return str(n).translate(_SUP_TRANS)

_DER_N:   bytes = _der_int(_N)
_DER_E:   bytes = _der_int(_E)
_DER_SEQ: bytes = bytes([0x30, len(_DER_N) + len(_DER_E)]) + _DER_N + _DER_E
_B64_DEMO: str  = base64.b64encode(_DER_SEQ).decode()


def _reseed_demo() -> None:
    """Modül seviyesindeki RSA demo değerlerini rastgele bir küçük asal
    çiftiyle yeniden hesaplar. RSAAnimationWindow her açıldığında çağrılır,
    böylece kullanıcı her seferinde farklı (p, q, n, ϕ, e, d) görür.

    Seçim kuralları:
      - p, q ∈ _PRIME_POOL (11..97 asalları), p ≠ q
      - n = p × q ≥ 143 (m = 65 her zaman < n olsun)
      - e: küçük ve gcd(e, ϕ) = 1 koşulunu sağlayan ilk yaygın değer
        (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
      - d = e⁻¹ mod ϕ, (e × d) mod ϕ == 1 invariantı sağlanmalı
    """
    global _P, _Q, _N, _PHI, _E, _D
    global _DER_N, _DER_E, _DER_SEQ, _B64_DEMO

    while True:
        p, q = random.sample(_PRIME_POOL, 2)
        n = p * q
        if n < 143:               # m=65 < n garantisi
            continue
        phi = (p - 1) * (q - 1)
        e = next(
            (cand for cand in (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
             if cand < phi and gcd(cand, phi) == 1),
            None,
        )
        if e is None:
            continue
        try:
            d = pow(e, -1, phi)
        except ValueError:
            continue
        if (e * d) % phi != 1:
            continue
        break

    _P, _Q = p, q
    _N = p * q
    _PHI = phi
    _E = e
    _D = d
    _DER_N = _der_int(_N)
    _DER_E = _der_int(_E)
    _DER_SEQ = bytes([0x30, len(_DER_N) + len(_DER_E)]) + _DER_N + _DER_E
    _B64_DEMO = base64.b64encode(_DER_SEQ).decode()


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
            ("phi", 2, "ϕ(n)",  str(_PHI),  "accent_yellow"),
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
            if kind == 1:
                # Yatay ayırıcı çizgi — toplama altı (yarım dash dizisi yerine
                # gerçek bir tam genişlikte çizgi, satırın ortasından geçer).
                line_y = y + line_h // 2
                p.setPen(QPen(QColor(ANIM_COLORS["text_muted"]), 1))
                p.drawLine(cx - 180, line_y, cx + 180, line_y)
                continue
            if kind == 2:
                p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
                p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
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
# 4) Adım 3 — Euler Totient  ϕ(n) = (p−1)(q−1)
# ---------------------------------------------------------------------------

class _TotientWidget(QWidget):
    """ϕ(n) hesabı: (p−1) ve (q−1) elde edilir, sonra çarpılır."""

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
                   "ϕ(n) = (p − 1) × (q − 1)")

        # Üst satır: p ve q kutularından (p−1) ve (q−1) türetimi
        row1_y = 44
        box_w, box_h = 84, 38     # 60 → 84: "p−1 = 60" gibi etiketler için
        gap = 18
        arrow_gap = 24
        # Sol blok: box(p) + arrow_gap + box(p-1)
        block_w = box_w + arrow_gap + box_w
        # Toplam satır genişliği: sol blok + ara boşluk + sağ blok
        total_w = block_w * 2 + 30
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
        right_x = left_x + block_w + 30
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
                f"ϕ(n) = {_PHI}", ANIM_COLORS["accent_yellow"],
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
    """e=17 seçimi ve gcd(e, ϕ(n))=1 doğrulaması — Öklid adımları akar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Öklid adımları: gcd(3120, 17) — büyükten küçüğe başla
        # (küçük olan zaten büyük olanda aranmaz; ilk anlamlı bölme
        # 3120 ÷ 17 olur).
        a, b = max(_E, _PHI), min(_E, _PHI)
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
                   f"Aday:  e = {_E}    Koşul:  gcd(e, ϕ(n)) = 1")

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

        # Sonuç — kullanıcı "e bulundu" mesajını net görmeli, sadece "GCD=1
        # ✓ Geçerli" yetersizdi. Başarılıysa: "e = 17 SEÇİLDİ  (gcd=1 ✓)".
        if self._reveal >= len(self._steps) + 1:
            result_y = rows_y + (len(self._steps) + 1) * line_h + 8
            success = (self._gcd_value == 1)
            color = (ANIM_COLORS["accent_green"] if success
                     else ANIM_COLORS["accent_peach"])
            fill = QColor(color)
            fill.setAlpha(60)
            box_w, box_h = 320, 48
            x = cx - box_w // 2
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor(color), 2))
            p.drawRoundedRect(x, result_y, box_w, box_h, 6, 6)

            if success:
                # Sonuç başlığı — büyük ve net: "e = 17 SEÇİLDİ"
                p.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
                p.setPen(QColor(color))
                p.drawText(
                    QRect(x, result_y + 2, box_w, 24),
                    Qt.AlignmentFlag.AlignCenter,
                    f"e = {_E}   ✓  SEÇİLDİ",
                )
                # Alt açıklama — gerekçe
                p.setFont(QFont("Georgia", 9))
                p.setPen(QColor(ANIM_COLORS["text_secondary"]))
                p.drawText(
                    QRect(x, result_y + 26, box_w, 18),
                    Qt.AlignmentFlag.AlignCenter,
                    f"(gcd(e, ϕ(n)) = {self._gcd_value}, koşul sağlandı)",
                )
            else:
                p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["text_primary"]))
                p.drawText(
                    QRect(x, result_y, box_w, box_h),
                    Qt.AlignmentFlag.AlignCenter,
                    f"GCD = {self._gcd_value}   ✗  REDDEDİLDİ",
                )
        p.end()


# ---------------------------------------------------------------------------
# 6) Adım 5 — Genişletilmiş Öklid Algoritması (EEA)  →  d
# ---------------------------------------------------------------------------

class _EEAWidget(QWidget):
    """
    Genişletilmiş Öklid Algoritması — STATİK matematik gösterimi.

    Adım 4 (Aday e seçimi, _GCDWidget) gibi animasyonsuz; satır satır
    ham matematik akışı:

      r₀ = q × r₁ + r        ⇒  s = s₀ − q·s₁,   t = t₀ − q·t₁

    Her satır bölüm denklemiyle birlikte güncellenmiş s ve t katsayılarını
    da gösterir. GCD = 1 satırından t alınır, d = t mod ϕ olarak yazılır.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._rows = _eea_steps(_PHI, _E)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx = W // 2

        # Başlık
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 8, W, 26), Qt.AlignmentFlag.AlignCenter,
                   "Genişletilmiş Öklid Algoritması")

        # Alt başlık — amaç + ϕ, e
        p.setFont(QFont("Georgia", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 34, W, 18), Qt.AlignmentFlag.AlignCenter,
                   f"Amaç: e·d ≡ 1 (mod ϕ)   ·   ϕ = {_PHI},  e = {_E}")

        # s, t katsayı kuralı
        p.setFont(QFont("Georgia", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 52, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "(Her adımda  s = s₀ − q·s₁,   t = t₀ − q·t₁  güncellenir.)")

        # Satırlar — rows[2..]: gerçek bölme adımları
        gcd_row_idx = len(self._rows) - 2
        row_y = 78
        line_h = 22
        # Pencere genişliğine göre dinamik kolon — dar pencerede de sığar
        eq_col_w = min(180, max(140, (W - 220) // 2))
        arrow_w = 22
        st_col_w = min(160, max(120, (W - 220) // 2))
        annot_x = cx + arrow_w // 2 + st_col_w + 8
        annot_w = 110

        for ri in range(2, len(self._rows)):
            i, q, r, s, t = self._rows[ri]
            _, _, r1, _, _ = self._rows[ri - 1]
            _, _, r0, _, _ = self._rows[ri - 2]

            is_gcd = (ri == gcd_row_idx)
            is_term = (r == 0)

            if is_gcd:
                color = ANIM_COLORS["accent_green"]
            elif is_term:
                color = ANIM_COLORS["text_muted"]
            else:
                color = ANIM_COLORS["text_secondary"]

            y = row_y + (ri - 2) * line_h

            # Sol: bölüm denklemi — daha küçük font, "3120 = 183 × 17 + 9" sığar
            p.setFont(QFont("Courier New", 11))
            p.setPen(QColor(color))
            text_left = f"{r0} = {q} × {r1} + {r}"
            p.drawText(
                QRect(cx - eq_col_w - arrow_w // 2, y, eq_col_w, line_h),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                text_left,
            )

            # Orta: ⇒
            p.drawText(
                QRect(cx - arrow_w // 2, y, arrow_w, line_h),
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                "⇒",
            )

            # Sağ: s, t katsayıları
            text_right = f"s={s}, t={t}"
            p.drawText(
                QRect(cx + arrow_w // 2, y, st_col_w, line_h),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text_right,
            )

            # Etiket — GCD=1 veya durma (sadece pencere genişse göster)
            if W >= 700:
                if is_gcd:
                    p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
                    p.setPen(QColor(ANIM_COLORS["accent_green"]))
                    p.drawText(
                        QRect(annot_x, y, annot_w, line_h),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        "← GCD=1, t'yi al",
                    )
                elif is_term:
                    p.setFont(QFont("Georgia", 8))
                    p.setPen(QColor(ANIM_COLORS["text_muted"]))
                    p.drawText(
                        QRect(annot_x, y, annot_w, line_h),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        "(durma)",
                    )

        # d hesaplama
        n_rows = len(self._rows) - 2
        last_t = self._rows[gcd_row_idx][4]
        calc_y = row_y + n_rows * line_h + 16

        p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(0, calc_y, W, 24), Qt.AlignmentFlag.AlignCenter,
                   f"d = t mod ϕ = {last_t} mod {_PHI} = {_D}")
        if last_t < 0:
            p.setFont(QFont("Georgia", 8))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(0, calc_y + 22, W, 14),
                       Qt.AlignmentFlag.AlignCenter,
                       "(negatif → +ϕ ekle)")

        # Doğrulama — biraz büyütüldü ama yine de pencere genişliğine sığacak boyutta
        verify_y = calc_y + 44
        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        check = (_E * _D) % _PHI
        p.drawText(QRect(4, verify_y, W - 8, 24), Qt.AlignmentFlag.AlignCenter,
                   f"Doğrulama: e×d mod ϕ = {_E}×{_D} mod {_PHI} = {check} ✓")

        p.end()


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
        self.setMinimumHeight(420)  # Base64 bit-çözümlemesi için ek alan
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
            y += 16
            p.setFont(QFont("Georgia", 8))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(0, y, W, 14), Qt.AlignmentFlag.AlignCenter,
                       "(Sayılar ağ üzerinden bayt olarak iletildiği için "
                       "big-endian bayt dizisine çevrilir; her bayt 2 hex hane.)")

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
            y += 18

            # — Bit-seviyesi açıklama — DEMO yerine ALICE'in GERÇEK
            # anahtarının ilk 4 b64 karakteri ile gösterilir. Kullanıcı
            # "alice'in açık anahtarının başını" net görür.
            alice_first4 = self._alice_b64[:4]   # ör. "MIIB"
            try:
                alice_first3 = base64.b64decode(alice_first4 + "==")[:3]
            except Exception:
                alice_first3 = b""

            if len(alice_first3) == 3:
                bits = "".join(f"{b:08b}" for b in alice_first3)     # 24 bit
                groups = [bits[i:i+6] for i in range(0, 24, 6)]      # 4 × 6-bit
                indices = [int(g, 2) for g in groups]

                p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
                p.drawText(
                    QRect(0, y, W, 14), Qt.AlignmentFlag.AlignCenter,
                    "Nasıl: 24 bit → 6-bit gruplar → A-Z a-z 0-9 + / alfabesinde indeks "
                    "(Alice'in gerçek anahtarının ilk 4 b64 karakteri):",
                )
                y += 14
                p.setFont(QFont("Courier New", 8))
                p.setPen(QColor(ANIM_COLORS["text_secondary"]))
                hex_str = " ".join(f"{b:02X}" for b in alice_first3)
                bin_str = " ".join(f"{b:08b}" for b in alice_first3)
                p.drawText(
                    QRect(0, y, W, 14), Qt.AlignmentFlag.AlignCenter,
                    f"{hex_str}  =  {bin_str}",
                )
                y += 12
                mapping = "   ".join(
                    f"{g}={idx}={ch}" for g, idx, ch in zip(groups, indices, alice_first4)
                )
                p.setPen(QColor(ANIM_COLORS["accent_green"]))
                p.drawText(
                    QRect(0, y, W, 14), Qt.AlignmentFlag.AlignCenter,
                    f"→ {mapping}",
                )
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
                value="(n, d) — yalnızca Alice'te tutulur",
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
            f"ϕ(n) = {_PHI}\n"
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
# 8) Adım 8 — Şifreleme/Deşifreleme Turu (Eq:RSAExample)
# ---------------------------------------------------------------------------

class _RSAEncryptDecryptWidget(QWidget):
    """
    Tezdeki Eq:RSAExample animasyonu:
      m = 65   →   c = m^e mod n = 65^17 mod 3233 = 2790
      c = 2790 →   m' = c^d mod n = 2790^2753 mod 3233 = 65   ✓

    Faz makinesi (toplam ~3.6 sn):
      PLAINTEXT_IN  (400 ms): m kutusu belirir
      ENC_FORMULA   (800 ms): şifreleme formülü satır satır yazılır,
                              açık anahtar kartı parlar
      CIPHER_OUT    (400 ms): c kutusu belirir
      CIPHER_IN     (200 ms): c alt yola düşer
      DEC_FORMULA   (800 ms): deşifreleme formülü, gizli anahtar kartı parlar
      PLAINTEXT_OUT (400 ms): m' kutusu belirir
      MATCH         (600 ms): m' = m ✓ yeşil pulse
    """

    _TICK_MS = 50

    # Faz tick eşikleri (kümülatif)
    _T_PLAIN_IN_END  = 8    # 400 ms
    _T_ENC_END       = 24   # +800 ms = 1200
    _T_CIPHER_END    = 32   # +400 ms = 1600
    _T_CIPHER_IN_END = 36   # +200 ms = 1800
    _T_DEC_END       = 52   # +800 ms = 2600
    _T_PLAIN_OUT_END = 60   # +400 ms = 3000
    _T_MATCH_END     = 72   # +600 ms = 3600

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Mesaj sabit (m = 65); şifreli ve çözülmüş değerler instance
        # oluşturulduğunda CARİ modül _E, _N, _D değerlerine göre hesaplanır.
        # _reseed_demo() her RSAAnimationWindow açılışında bu değerleri
        # yenilediği için widget her zaman güncel (e, n, d) ile çalışır.
        self._M = 65
        self._C = pow(self._M, _E, _N)
        self._M_PRIME = pow(self._C, _D, _N)
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._tick = 0
        self.update()
        self._timer.start(self._TICK_MS)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self) -> None:
        if self._tick < self._T_MATCH_END:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        t = self._tick

        box_w, box_h = 100, 44
        margin = 20
        ox = margin

        # Formül kutusu — m ve c arasında kalan boşluğa uyarlanır
        formula_x = margin + box_w + 16
        formula_right_lim = W - margin - box_w - 16
        formula_w = max(180, formula_right_lim - formula_x)
        formula_h = 64

        # Anahtar kartı (formül altında ortalı)
        card_w = 170
        card_h = 36

        # ── Üst yol: Şifreleme ──
        enc_y = 24
        # m kutusu
        if t >= 1:
            self._draw_box(
                p, ox, enc_y, box_w, box_h,
                f"m = {self._M}", ANIM_COLORS["accent_blue"],
                opacity=min(1.0, t / self._T_PLAIN_IN_END),
            )
        # Şifreleme formülü kutusu
        if t > self._T_PLAIN_IN_END:
            opacity = min(1.0, (t - self._T_PLAIN_IN_END) / (self._T_ENC_END - self._T_PLAIN_IN_END))
            self._draw_formula_box(
                p, formula_x, enc_y - 10, formula_w, formula_h,
                "c = mᵉ mod n",
                f"= {self._M}{_to_sup(_E)} mod {_N}",
                f"= {self._C}",
                ANIM_COLORS["accent_mauve"],
                lines_revealed=int(3 * opacity) + 1,
            )
            # Açık anahtar kartı — formül kutusunun altında ortalı (c kutusunun altında değil)
            if t > self._T_PLAIN_IN_END + 4:
                card_x = formula_x + (formula_w - card_w) // 2
                self._draw_key_card(
                    p, card_x, enc_y + box_h + 14,
                    "Açık Anahtar", f"(n={_N}, e={_E})",
                    ANIM_COLORS["accent_blue"],
                    width=card_w, height=card_h,
                )
        # c kutusu
        if t >= self._T_ENC_END:
            opacity = min(1.0, (t - self._T_ENC_END) / (self._T_CIPHER_END - self._T_ENC_END))
            self._draw_box(
                p, W - margin - box_w, enc_y, box_w, box_h,
                f"c = {self._C}", ANIM_COLORS["accent_peach"], opacity=opacity,
            )

        # ── Alt yol: Deşifreleme ──
        # enc satırı + enc kartı toplam yer: box_h + 14 + card_h + 18 boşluk
        dec_y = enc_y + box_h + 14 + card_h + 18  # 24 + 44 + 14 + 36 + 18 = 136
        # c (alt yolda sol)
        if t >= self._T_CIPHER_IN_END:
            self._draw_box(
                p, ox, dec_y, box_w, box_h,
                f"c = {self._C}", ANIM_COLORS["accent_peach"],
            )
        # Deşifreleme formülü
        if t > self._T_CIPHER_IN_END:
            opacity = min(1.0, (t - self._T_CIPHER_IN_END) / (self._T_DEC_END - self._T_CIPHER_IN_END))
            self._draw_formula_box(
                p, formula_x, dec_y - 10, formula_w, formula_h,
                "m' = cᵈ mod n",
                f"= {self._C}{_to_sup(_D)} mod {_N}",
                f"= {self._M_PRIME}",
                ANIM_COLORS["accent_green"],
                lines_revealed=int(3 * opacity) + 1,
            )
            if t > self._T_CIPHER_IN_END + 4:
                card_x = formula_x + (formula_w - card_w) // 2
                self._draw_key_card(
                    p, card_x, dec_y + box_h + 14,
                    "Gizli Anahtar", f"(n={_N}, d={_D})",
                    ANIM_COLORS["accent_mauve"],
                    width=card_w, height=card_h,
                )
        # m' kutusu — başarı etiketinde m' = 65 = m ✓ 13 karakterlik metin
        # 100 px sığmıyor; bu yüzden son fazda kutu genişletilir ve sola
        # kaydırılır ki c kutusuyla çakışmasın, içerik (özellikle "m' "
        # apostrofu) kırpılmadan görünsün.
        if t >= self._T_DEC_END:
            opacity = min(1.0, (t - self._T_DEC_END) / (self._T_PLAIN_OUT_END - self._T_DEC_END))
            if t >= self._T_PLAIN_OUT_END:
                label = f"m' = {self._M_PRIME} = m ✓"
                final_box_w = 170
            else:
                label = f"m' = {self._M_PRIME}"
                final_box_w = box_w
            color = ANIM_COLORS["accent_green"] if t >= self._T_PLAIN_OUT_END else ANIM_COLORS["accent_blue"]
            self._draw_box(
                p, W - margin - final_box_w, dec_y, final_box_w, box_h,
                label, color, opacity=opacity,
                pulse=(t >= self._T_PLAIN_OUT_END and t < self._T_MATCH_END),
            )

        p.end()

    def _draw_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        text: str, color: str, opacity: float = 1.0, pulse: bool = False,
    ) -> None:
        col = QColor(color)
        col.setAlphaF(opacity)
        fill = QColor(color)
        fill.setAlphaF(opacity * 0.18)
        if pulse:
            phase = (self._tick % 8) / 8.0
            fill.setAlphaF(opacity * (0.18 + 0.20 * abs(0.5 - phase) * 2))

        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)
        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)
        p.setPen(text_col)
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_formula_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        line1: str, line2: str, line3: str, color: str,
        lines_revealed: int,
    ) -> None:
        col = QColor(color)
        fill = QColor(color)
        fill.setAlphaF(0.15)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)

        # Font puntosu, en uzun satır kutuya sığacak şekilde dinamik seçilir.
        # Random RSA değerlerinde (özellikle d 3-4 haneye çıkınca) sabit 10pt
        # bazen taşıyordu; bu nedenle adaptif fallback eklendi.
        lines = [line1, line2, line3]
        avail_w = w - 16
        font_pt = 10
        for pt in (10, 9, 8):
            p.setFont(QFont("Courier New", pt, QFont.Weight.Bold))
            longest = max(lines, key=lambda s: p.fontMetrics().horizontalAdvance(s))
            if p.fontMetrics().horizontalAdvance(longest) <= avail_w:
                font_pt = pt
                break
        else:
            font_pt = 8

        p.setFont(QFont("Courier New", font_pt, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        p.setPen(text_col)
        for li in range(min(lines_revealed, 3)):
            p.drawText(QRect(x + 8, y + 6 + li * 20, w - 16, 18),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       lines[li])

    def _draw_key_card(
        self, p: QPainter, x: int, y: int, title: str, val: str, color: str,
        width: int = 140, height: int = 60,
    ) -> None:
        col = QColor(color)
        fill = QColor(color)
        fill.setAlphaF(0.20)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 1))
        p.drawRoundedRect(x, y, width, height, 6, 6)
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(col)
        title_h = max(14, height // 3)
        p.drawText(QRect(x, y + 2, width, title_h),
                   Qt.AlignmentFlag.AlignCenter, title)
        p.setFont(QFont("Courier New", 9))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(x, y + title_h + 2, width, height - title_h - 4),
                   Qt.AlignmentFlag.AlignCenter, val)


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
        "Adım 1 / 8 — p ve q Seçimi",
        "Adım 2 / 8 — n = p × q",
        "Adım 3 / 8 — ϕ(n) = (p − 1)(q − 1)",
        "Adım 4 / 8 — Açık Üs e Seçimi",
        "Adım 5 / 8 — Gizli Üs d  (Genişletilmiş Öklid)",
        "Adım 6 / 8 — DER ve Base64 Kodlaması",
        "Adım 7 / 8 — Gerçek Anahtarlarla Eşleşme",
        "Adım 8 / 8 — Şifreleme / Deşifreleme Turu",
    ]

    _CAPTIONS = [
        "p ve q rastgele iki büyük asaldır; n ve ϕ(n) hesabının temelini oluştururlar.",
        "n = p × q  →  modülüs; hem açık hem gizli anahtarda yer alır.",
        "ϕ(n) = (p − 1)(q − 1)  →  Euler totient fonksiyonu.",
        "gcd(e, ϕ(n)) = 1  koşulu sağlanmalı; e açık anahtarın üs bileşenidir.",
        "d, e'nin ϕ(n) modülünde tersidir:  e · d ≡ 1  (mod ϕ).",
        "Anahtar dosyada DER yapısında, satır içinde Base64 olarak kodlanır.",
        "Aynı matematik · farklı boyut: demo 12-bit n, gerçek 2048-bit n.",
        "m → c → m'  döngüsü; her iki yön de aynı m değerine ulaşır (Eq:RSAExample).",
    ]

    def __init__(
        self,
        alice_pub_b64: str,
        bob_pub_b64: str,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        # Her açılışta rastgele farklı bir (p, q, e, d) seç — kullanıcı
        # her demo'da farklı sayılar görür. Widget'lar __init__ sırasında
        # cari modül sabitlerini okuduğu için bu çağrı SUPER ÇAĞRISINDAN
        # ÖNCE yapılmalıdır (super → _init_content → widget'lar).
        _reseed_demo()
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

        # Sağ: 8 sayfalı stack
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
            _RSAEncryptDecryptWidget(),
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
        # Son adım — index 7 (Şifreleme/Deşifreleme Turu)
        self._step_lbl.setText(self._TITLES[7])
        self._stack.setCurrentIndex(7)
        self._kb.set_step(7)
        self._caption.setText(self._CAPTIONS[7])
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
