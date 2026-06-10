# animation_modals/rsa/key_match.py
"""Adım 7-8 — Demo↔gerçek anahtar eşleşmesi + şifreleme/deşifreleme turu."""
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
from ..base import CryptoAnimationWindow, ANIM_COLORS, get_animation_tick_ms
from . import helpers as H

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
        self.setMinimumHeight(210)
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
        self._demo_card = self._make_card(
            "DEMO  (temsilî · gerçek anahtar değil)",
            f"p = {H._P}\n"
            f"q = {H._Q}\n"
            f"n = {H._N}\n"
            f"ϕ(n) = {H._PHI}\n"
            f"e = {H._E}\n"
            f"d = {H._D}\n"
            f"Modülüs: 12 bit",
            "accent_blue",
        )
        cards_row.addWidget(self._demo_card, stretch=1)

        # Orta: ≈ sembolü
        self._approx = QLabel("≈")
        self._approx.setFont(QFont("Georgia", 28, QFont.Weight.Bold))
        self._approx.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._approx.setMaximumWidth(40)
        cards_row.addWidget(self._approx)

        # Sağ: gerçek
        self._real_card = self._make_card(
            "GERÇEK (RSA-2048)",
            f"p, q ≈ 1024-bit asal\n"
            f"n ≈ 617 ondalık hane\n"
            f"e = 65537\n"
            f"d ≈ 2048-bit\n"
            f"Modülüs: 2048 bit\n"
            f"Base64 ≈ 360 karakter",
            "accent_green",
        )
        cards_row.addWidget(self._real_card, stretch=1)

        outer.addLayout(cards_row)

        # Gerçek anahtar önizlemesi (alt) — kelime kaydırma ile genişlikten bağımsız
        # Font 8pt → 9pt (önceki çok küçüktü, okunaksızdı)
        self._keys_lbl = QLabel(
            f"<b>Alice açık anahtarı:</b> {self._alice_b64[:48]}…<br>"
            f"<b>Bob açık anahtarı:</b> {self._bob_b64[:48]}…"
        )
        self._keys_lbl.setFont(QFont("Courier New", 9))
        self._keys_lbl.setWordWrap(True)
        self._keys_lbl.setTextFormat(Qt.TextFormat.RichText)
        outer.addWidget(self._keys_lbl)

        # Alt: aynı matematik mesajı
        self._msg = QLabel(
            "Aynı matematik · farklı boyut: tüm adımlar gerçek 2048-bit p ve q ile aynen uygulanır."
        )
        self._msg.setFont(QFont("Georgia", 9))
        self._msg.setWordWrap(True)
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._msg)

        self.restyle()

    def restyle(self) -> None:
        """Tema değişiminde tüm etiket/kart stillerini yeniden uygular (statik içerik)."""
        for card in (self._demo_card, self._real_card):
            color = ANIM_COLORS[card._accent_key]  # type: ignore[attr-defined]
            card.setStyleSheet(
                f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
                f"border: 2px solid {color}; border-radius: 8px; }}"
            )
            card._title_lbl.setStyleSheet(f"color: {color}; border: none;")  # type: ignore[attr-defined]
            card._body_lbl.setStyleSheet(  # type: ignore[attr-defined]
                f"color: {ANIM_COLORS['text_secondary']}; border: none;"
            )
        self._approx.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._keys_lbl.setStyleSheet(
            f"QLabel {{ color: {ANIM_COLORS['text_secondary']}; "
            f"background: {ANIM_COLORS['bg_input']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 4px; padding: 4px 6px; }}"
        )
        self._msg.setStyleSheet(
            f"QLabel {{ color: {ANIM_COLORS['accent_yellow']}; "
            f"background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 5px; padding: 6px; }}"
        )

    @staticmethod
    def _make_card(title: str, body: str, color_key: str) -> QFrame:
        f = QFrame()
        f._accent_key = color_key  # type: ignore[attr-defined]
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(2)

        t = QLabel(title)
        t.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)

        b = QLabel(body)
        b.setFont(QFont("Courier New", 9))
        b.setWordWrap(True)
        b.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(b, stretch=1)

        f._title_lbl = t  # type: ignore[attr-defined]
        f._body_lbl = b   # type: ignore[attr-defined]
        return f




# ---------------------------------------------------------------------------
# 8) Adım 8 — Şifreleme/Deşifreleme Turu (Eq:RSAExample)
# ---------------------------------------------------------------------------

class _RSAEncryptDecryptWidget(QWidget):
    """
    RSA şifreleme/deşifreleme turu (Eq:RSAExample tarzı). Değerler her
    açılışta H._reseed_demo() ile rastgele seçilir; örnek bir tur:
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
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Mesaj ve türevleri CARİ modül değerlerinden (H._M, H._E, H._N, H._D)
        # okunur. H._reseed_demo() her RSAAnimationWindow açılışında m dahil tüm
        # değerleri yenilediği için m → c → m' döngüsü her demo'da farklı
        # sayılarla gözlemlenir (anahtarlar değişirken m'nin de değişmesi
        # 'değişen RSA' kavramını pekiştirir).
        self._M = H._M
        self._C = pow(self._M, H._E, H._N)
        self._M_PRIME = pow(self._C, H._D, H._N)
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._tick = 0
        self.update()
        self._timer.start(get_animation_tick_ms(self._TICK_MS))

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
        W = self.width()  # NOT: 'H' helpers modül takma adı; gölgelememek için yalnız W
        t = self._tick

        # m/c/m' kutu genişliği İÇERİĞE göre belirlenir. m artık rastgele
        # (4 haneye kadar) ve m' kutusunda " ✓" eklenince "m' = 1804 ✓" gibi
        # etiketler sabit 86px'e sığmıyordu (Görsel 1). QFontMetrics ile üç
        # kutunun en geniş metni ölçülüp +16 padding eklenir; 86 taban, 140
        # tavan (formül kutusuna yer kalsın).
        from PyQt6.QtGui import QFontMetrics
        box_h = 44
        margin = 14
        ox = margin
        _box_texts = [
            f"m = {self._M}",
            f"c = {self._C}",
            f"m' = {self._M_PRIME} ✓",
        ]
        _fm = QFontMetrics(QFont("Courier New", 11, QFont.Weight.Bold))
        _needed = max(_fm.horizontalAdvance(s) for s in _box_texts) + 16
        box_w = max(86, min(152, _needed))

        # Formül kutusu — m ve c/m' arasında kalan boşluğa uyarlanır
        # m' artık c ile aynı genişlikte (86 px) olduğu için ek hesaplama
        # gerekmez; "= m ✓" doğrulama etiketi kutunun altına çizilir.
        formula_x = margin + box_w + 12
        formula_right_lim = W - margin - box_w - 12
        formula_w = max(220, formula_right_lim - formula_x)
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
            # Bu özet ekran yalnızca modüler üs sonucunu gösterir; bit-bit
            # square-and-multiply tablosu pedagojik kapsamın dışında tutulur.
            opacity = min(1.0, (t - self._T_PLAIN_IN_END) / (self._T_ENC_END - self._T_PLAIN_IN_END))
            self._draw_formula_box(
                p, formula_x, enc_y - 10, formula_w, formula_h,
                "c = mᵉ mod n",
                f"= {self._M}{H._to_sup(H._E)} mod {H._N}",
                f"= {self._C}",
                ANIM_COLORS["accent_mauve"],
                lines_revealed=int(3 * opacity) + 1,
            )
            # Açık anahtar kartı — formül kutusunun altında ortalı (c kutusunun altında değil)
            if t > self._T_PLAIN_IN_END + 4:
                card_x = formula_x + (formula_w - card_w) // 2
                self._draw_key_card(
                    p, card_x, enc_y + box_h + 14,
                    "Açık Anahtar", f"(n={H._N}, e={H._E})",
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
                f"= {self._C}{H._to_sup(H._D)} mod {H._N}",
                f"= {self._M_PRIME}",
                ANIM_COLORS["accent_green"],
                lines_revealed=int(3 * opacity) + 1,
            )
            if t > self._T_CIPHER_IN_END + 4:
                card_x = formula_x + (formula_w - card_w) // 2
                self._draw_key_card(
                    p, card_x, dec_y + box_h + 14,
                    "Gizli Anahtar", f"(n={H._N}, d={H._D})",
                    ANIM_COLORS["accent_mauve"],
                    width=card_w, height=card_h,
                )
        # m' kutusu — diğer kutularla (m, c) tutarlı, ekstra efekt yok:
        # pulse, renk geçişi ve label değişimi kaldırıldı (kullanıcı geri
        # bildirimi). Sadece m ve c-üst kutularıyla aynı yumuşak fade-in
        # opasitesi korunuyor. M_PRIME == M ise ✓ ilk kareden itibaren
        # etikettedir, geçiş animasyonu yok.
        if t >= self._T_DEC_END:
            opacity = min(1.0, (t - self._T_DEC_END) / (self._T_PLAIN_OUT_END - self._T_DEC_END))
            if self._M_PRIME == self._M:
                label = f"m' = {self._M_PRIME} ✓"
            else:
                label = f"m' = {self._M_PRIME}"
            self._draw_box(
                p, W - margin - box_w, dec_y, box_w, box_h,
                label, ANIM_COLORS["accent_green"], opacity=opacity,
                pulse=False,
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
        # Adaptive font — metin kutuya KESİN sığsın diye QFontMetrics ile
        # ölçülerek 11→8pt arasında en büyük sığan punto seçilir (sabit
        # karakter eşiği yerine gerçek piksel ölçümü; "m' = 8632 ✓" gibi en
        # uzun durumda bile taşma olmaz).
        from PyQt6.QtGui import QFontMetrics
        font_size = 8
        for pt in (11, 10, 9, 8):
            if QFontMetrics(
                QFont("Courier New", pt, QFont.Weight.Bold)
            ).horizontalAdvance(text) <= w - 10:
                font_size = pt
                break
        p.setFont(QFont("Courier New", font_size, QFont.Weight.Bold))
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
        # Random RSA değerlerinde n,d 4 haneye çıkabildiği için 7pt'ye kadar
        # fallback ekledim; daha sıkı padding ile asla taşma olmasın.
        lines = [line1, line2, line3]
        avail_w = w - 12
        font_pt = 9
        for pt in (10, 9, 8, 7):
            p.setFont(QFont("Courier New", pt, QFont.Weight.Bold))
            longest = max(lines, key=lambda s: p.fontMetrics().horizontalAdvance(s))
            if p.fontMetrics().horizontalAdvance(longest) <= avail_w:
                font_pt = pt
                break
        else:
            font_pt = 7

        p.setFont(QFont("Courier New", font_pt, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        p.setPen(text_col)
        for li in range(min(lines_revealed, 3)):
            p.drawText(QRect(x + 6, y + 6 + li * 20, w - 12, 18),
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

