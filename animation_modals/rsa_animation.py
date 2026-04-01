# animation_modals/rsa_animation.py
"""
RSAAnimationWindow — RSA-2048 anahtar üretimini adım adım görselleştirir.
Demo olarak küçük asal sayılar (p=61, q=53) kullanılır.
Son adımda gerçek Base64 anahtar ile eşleşme gösterilir.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from .base import CryptoAnimationWindow, ANIM_COLORS

_P = 61
_Q = 53
_N = _P * _Q
_PHI = (_P - 1) * (_Q - 1)
_E = 17
_D = pow(_E, -1, _PHI)


class RSAAnimationWindow(CryptoAnimationWindow):
    """
    RSA-2048 anahtar üretimi animasyonu (4 adım).

    Parametreler:
      alice_pub_b64: Alice'in açık anahtarının Base64 gösterimi (kısaltılmış)
      bob_pub_b64  : Bob'un açık anahtarının Base64 gösterimi (kısaltılmış)
    """

    _STEP_TITLES = [
        "Adım 1 — Asal Sayı Seçimi",
        "Adım 2 — Modül Hesaplama  n = p × q",
        "Adım 3 — Totient Fonksiyonu  φ(n) ve Açık Üs e",
        "Adım 4 — Gizli Anahtar d ve Anahtar Eşleşmesi",
    ]

    def __init__(
        self,
        alice_pub_b64: str,
        bob_pub_b64: str,
        parent: QWidget | None = None,
    ) -> None:
        self._alice_b64 = alice_pub_b64
        self._bob_b64 = bob_pub_b64
        super().__init__("🔑 RSA-2048 Anahtar Üretimi", len(self._STEP_TITLES))

    def _init_content(self) -> None:
        self._step_title = QLabel()
        self._step_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._step_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._step_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._step_title)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)

        self._content_lbl = QLabel()
        self._content_lbl.setFont(QFont("Courier New", 12))
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._content_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._content_lbl.setWordWrap(True)
        self._content_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card_layout.addWidget(self._content_lbl)
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()

    def _render_step(self, step_idx: int) -> None:
        self._step_title.setText(self._STEP_TITLES[step_idx])
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")

        if step_idx == 0:
            self._content_lbl.setText(
                f"İki büyük asal sayı rastgele seçildi:\n\n"
                f"  p  =  {_P}\n"
                f"  q  =  {_Q}\n\n"
                f"Gerçek RSA-2048'de p ve q 1024-bit asal sayılardır.\n"
                f"Burada eğitim amaçlı küçük değerler kullanılmaktadır."
            )
        elif step_idx == 1:
            self._content_lbl.setText(
                f"Modül (n) hesaplandı:\n\n"
                f"  n  =  p × q\n"
                f"  n  =  {_P} × {_Q}\n"
                f"  n  =  {_N}\n\n"
                f"RSA-2048'de n, 2048 bitlik bir sayıdır.\n"
                f"n'nin güvenliği p ve q'nun gizliliğine dayanır."
            )
        elif step_idx == 2:
            self._content_lbl.setText(
                f"Euler Totient fonksiyonu:\n\n"
                f"  φ(n)  =  (p-1) × (q-1)\n"
                f"  φ(n)  =  {_P - 1} × {_Q - 1}\n"
                f"  φ(n)  =  {_PHI}\n\n"
                f"Açık anahtar üssü seçildi:\n"
                f"  e  =  {_E}  (φ(n) ile ortak bölen 1 olmalı)"
            )

    def _show_match_result(self) -> None:
        self._step_title.setText(self._STEP_TITLES[3])
        self._content_lbl.setText(
            f"Gizli anahtar d hesaplandı:\n\n"
            f"  d  =  e⁻¹ mod φ(n)  =  {_D}\n\n"
            f"  Açık anahtar  →  (e = {_E},  n = {_N})\n"
            f"  Gizli anahtar →  (d = {_D},  n = {_N})\n\n"
            f"{'─' * 52}\n\n"
            f"Alice Açık Anahtarı (crypto_core):\n"
            f"  {self._alice_b64}\n\n"
            f"Bob Açık Anahtarı (crypto_core):\n"
            f"  {self._bob_b64}\n\n"
            f"✅  Eşleşme Başarılı"
        )
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
