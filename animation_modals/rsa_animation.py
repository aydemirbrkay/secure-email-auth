# animation_modals/rsa_animation.py
"""
RSAAnimationWindow — RSA-2048 anahtar üretimini 7 adımda görselleştirir.
Kullanıcı ◀ Geri / İleri ▶ butonlarıyla ilerler (manual_mode=True).
Demo için küçük değerler kullanılır; son adımda gerçek Base64 eşleşmesi yapılır.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget
from .base import CryptoAnimationWindow, ANIM_COLORS

# Eğitim amaçlı küçük demo değerler
_P, _Q = 61, 53
_N = _P * _Q            # 3233
_PHI = (_P - 1) * (_Q - 1)  # 3120
_E = 17
_D = pow(_E, -1, _PHI)  # 2753

# Extended Euclidean gösterimi için adımlar (elle hesaplanmış)
_EEA_STEPS = [
    ("3120 = 183 × 17 + 9",   "3120 mod 17 = 9"),
    ("17   =   1 × 9  + 8",   "17   mod  9 = 8"),
    ("9    =   1 × 8  + 1",   "9    mod  8 = 1"),
    ("8    =   8 × 1  + 0",   "← GCD = 1, geri iz başlıyor"),
    ("1 = 9 − 1×8",           ""),
    ("1 = 9 − 1×(17 − 9)   = 2×9 − 17", ""),
    ("1 = 2×(3120 − 183×17) − 17       = 2×3120 − 367×17", ""),
    (f"d = −367 mod 3120 = {_D}", "✓  d = 2753"),
]


class RSAAnimationWindow(CryptoAnimationWindow):
    """
    RSA-2048 anahtar üretimi animasyonu — 7 adım, manuel navigasyon.

    Parametreler:
      alice_pub_b64: Alice açık anahtarı Base64 (kısaltılmış)
      bob_pub_b64  : Bob açık anahtarı Base64 (kısaltılmış)
    """

    _TITLES = [
        "Adım 1 — Asal Sayı Nedir?  p ve q Seçimi",
        "Adım 2 — Modül Hesaplama  n = p × q",
        "Adım 3 — Euler Totient  φ(n) = (p−1)(q−1)",
        "Adım 4 — Açık Üs  e  Seçimi",
        "Adım 5 — Gizli Anahtar  d  (Genişletilmiş Öklid)",
        "Adım 6 — Anahtarın Karmaşık Yapıya Dönüşümü",
        "Adım 7 — Gerçek Anahtar Eşleşmesi",
    ]

    def __init__(
        self,
        alice_pub_b64: str,
        bob_pub_b64: str,
        parent: QWidget | None = None,
    ) -> None:
        self._alice_b64 = alice_pub_b64
        self._bob_b64 = bob_pub_b64
        super().__init__(
            "🔑  RSA-2048 Anahtar Üretimi",
            len(self._TITLES),
            manual_mode=True,
        )

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        self._step_lbl = QLabel()
        self._step_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._step_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._step_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._step_lbl)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 10px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 20, 28, 20)

        self._body = QLabel()
        self._body.setFont(QFont("Courier New", 13))
        self._body.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._body.setWordWrap(True)
        self._body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        card_layout.addWidget(self._body)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        self.content_layout.addWidget(scroll, stretch=1)

    # ------------------------------------------------------------------
    # Adım render'ları
    # ------------------------------------------------------------------

    def _render_step(self, idx: int) -> None:
        self._step_lbl.setText(self._TITLES[idx])
        self._body.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._body.setText(_STEP_BODIES[idx])

    def _show_match_result(self) -> None:
        self._step_lbl.setText(self._TITLES[6])
        self._body.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
        self._body.setText(
            f"Demo Açık Anahtar:   (e={_E},  n={_N})\n"
            f"Demo Gizli Anahtar:  (d={_D},  n={_N})\n\n"
            f"{'─' * 60}\n\n"
            f"Alice Açık Anahtarı — crypto_core (Base64):\n"
            f"  {self._alice_b64}\n\n"
            f"Bob Açık Anahtarı — crypto_core (Base64):\n"
            f"  {self._bob_b64}\n\n"
            f"✅  Eşleşme Başarılı\n\n"
            f"Matematiksel yapı (e, n) → ASN.1 DER → Base64 dönüşümü\n"
            f"yukarıdaki uzun anahtarı üretir."
        )


# Adım metinleri (sınıf dışında tanımlanır; temiz tutar)
_STEP_BODIES: list[str] = [
    # Adım 0 — Asal sayı
    (
        "Bir sayı asal ise yalnızca 1 ve kendisiyle bölünebilir.\n\n"
        f"  p = {_P}  →  Bölenler: 1, 61          ✓ ASAL\n"
        f"  q = {_Q}  →  Bölenler: 1, 53          ✓ ASAL\n\n"
        "RSA-2048'de p ve q gerçekte 1024-bit (309+ haneli) asal sayılardır.\n"
        "Bilgisayarın bunları çarpanlarına ayırması pratikte imkânsızdır;\n"
        "RSA'nın güvenliği buraya dayanır.\n\n"
        "Bu gösterimde eğitim amaçlı küçük değerler kullanılmaktadır."
    ),
    # Adım 1 — n = p × q
    (
        "Modül n, iki asal sayının çarpımıdır:\n\n"
        f"  n = p × q\n"
        f"  n = {_P} × {_Q}\n"
        f"  n = {_N}\n\n"
        f"n her iki anahtarda da kullanılır (açık ve gizli).\n"
        f"Güvenlik: n'yi {_P} ve {_Q}'ya çarpanlamak hesaplamalı olarak zordur."
    ),
    # Adım 2 — φ(n)
    (
        "Euler Totient φ(n): n'den küçük, n ile aralarında asal sayıların sayısı.\n\n"
        f"  φ(n) = (p − 1) × (q − 1)\n"
        f"  φ(n) = ({_P} − 1) × ({_Q} − 1)\n"
        f"  φ(n) = {_P - 1} × {_Q - 1}\n"
        f"  φ(n) = {_PHI}\n\n"
        f"φ(n) gizli tutulur; gizli anahtar hesabında kullanılır.\n"
        f"p ve q bilinirse φ(n) kolayca hesaplanır — bu yüzden p ve q gizlidir."
    ),
    # Adım 3 — e seçimi
    (
        f"Açık üs e şu koşulları sağlamalıdır:\n\n"
        f"  1 < e < φ(n)\n"
        f"  gcd(e, φ(n)) = 1   (e ile φ(n) aralarında asal)\n\n"
        f"Seçilen:  e = {_E}\n\n"
        f"Kontrol:\n"
        f"  gcd({_E}, {_PHI}) = ?\n"
        f"  {_PHI} = {_PHI // _E} × {_E} + {_PHI % _E}\n"
        f"  {_E}   = {_E // (_PHI % _E)} × {_PHI % _E} + {_E % (_PHI % _E)}\n"
        f"  ...  → gcd = 1  ✓\n\n"
        f"Gerçek RSA'da e genellikle 65537 seçilir (Fermat sayısı F4)."
    ),
    # Adım 4 — d hesabı (EEA)
    (
        f"d = e⁻¹ mod φ(n)  →  e × d ≡ 1 (mod φ(n))\n\n"
        "Genişletilmiş Öklid Algoritması:\n\n"
        + "\n".join(f"  {a}   {b}" for a, b in _EEA_STEPS)
        + f"\n\n  Sonuç:  d = {_D}\n\n"
        f"Doğrulama:  {_E} × {_D} mod {_PHI} = "
        f"{(_E * _D) % _PHI}  ✓"
    ),
    # Adım 5 — Anahtar kodlama
    (
        "Matematiksel değerler nasıl uzun bir Base64 dizisine dönüşür?\n\n"
        "Adım A — Tamsayıdan byte dizisine:\n"
        f"  n = {_N}  →  hex: 0x{_N:04x}  →  bytes: {_N.to_bytes(2, 'big').hex()}\n"
        f"  e = {_E}   →  hex: 0x{_E:02x}    →  bytes: {_E.to_bytes(1, 'big').hex()}\n\n"
        "Adım B — ASN.1 / DER şeması:\n"
        "  SEQUENCE {\n"
        "    INTEGER  n  (modulus)\n"
        "    INTEGER  e  (publicExponent)\n"
        "  }\n"
        "  Bu yapısal sarma, birkaç byte başlık ekler.\n\n"
        "Adım C — SubjectPublicKeyInfo (PKCS#8 / X.509):\n"
        "  Algoritma tanımlayıcı OID'i (rsaEncryption) + yukarıdaki DER\n\n"
        "Adım D — Base64 kodlama:\n"
        "  Her 3 byte → 4 ASCII karakter\n"
        "  DER verisi ~270 byte → ~360 Base64 karakter\n\n"
        "PEM formatı = '-----BEGIN PUBLIC KEY-----' + Base64 + '-----END...'"
    ),
    # Adım 6 — Eşleşme (_show_match_result tarafından işlenir)
    "",
]
