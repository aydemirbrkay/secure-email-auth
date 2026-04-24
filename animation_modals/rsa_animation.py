# animation_modals/rsa_animation.py
"""
RSAAnimationWindow — RSA-2048 anahtar üretimini 7 adımda görselleştirir.
Kullanıcı ◀ Geri / İleri ▶ butonlarıyla ilerler (manual_mode=True).
Demo için küçük değerler kullanılır; son adımda gerçek Base64 eşleşmesi yapılır.
"""
from __future__ import annotations
import base64
from collections.abc import Callable
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from .base import CryptoAnimationWindow, ANIM_COLORS

# Eğitim amaçlı küçük demo değerler
_P, _Q = 61, 53
_N = _P * _Q            # 3233
_PHI = (_P - 1) * (_Q - 1)  # 3120
_E = 17
_D = pow(_E, -1, _PHI)  # 2753

# Demo değerlerin gerçek DER → Base64 dönüşümü
def _der_int(v: int) -> bytes:
    """Bir tam sayıyı DER INTEGER olarak kodlar."""
    b = v.to_bytes((v.bit_length() + 8) // 8, "big")
    if b[0] >= 0x80:          # işaret biti sıfır olmalı → 0x00 öneki ekle
        b = b"\x00" + b
    return bytes([0x02, len(b)]) + b

_DER_N   = _der_int(_N)
_DER_E   = _der_int(_E)
_DER_SEQ = bytes([0x30, len(_DER_N) + len(_DER_E)]) + _DER_N + _DER_E
_B64_DEMO = base64.b64encode(_DER_SEQ).decode()

# DER byte'larının hex gösterimi (adım 5 için)
_DER_HEX = " ".join(f"{x:02X}" for x in _DER_SEQ)

# Extended Euclidean gösterimi için adımlar (elle hesaplanmış)
_EEA_STEPS = [
    ("3120 = 183 × 17 + 9",   "3120 mod 17 = 9"),
    ("17   =   1 × 9  + 8",   "17   mod  9 = 8"),
    ("9    =   1 × 8  + 1",   "9    mod  8 = 1"),
    ("8    =   8 × 1  + 0",   "← GCD = 1, geri iz başlıyor"),
    ("1 = 9 − 1×8",
     "← satır 3'ten: 9 = 1×8 + 1 → 1 = 9 − 8"),
    ("1 = 9 − 1×(17 − 1×9)  =  2×9 − 17",
     "← satır 2'den 8'i yerine koy: 8 = 17 − 1×9"),
    ("1 = 2×(3120 − 183×17) − 17  =  2×3120 − 367×17",
     "← satır 1'den 9'u yerine koy: 9 = 3120 − 183×17"),
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
        # Kalıcı uyarı kartı — tüm adımlar boyunca görünür.
        # Animasyonda gösterilen m^e mod n / m^d mod n "ham RSA"
        # (textbook RSA) şemasıdır; pedagojik olarak doğrudur ancak
        # gerçek projede kullanılan semantikle birebir aynı değildir.
        # Projede:
        #   - İmza için: RSA-2048 + PSS (rastgele tuzlu dolgu, MGF1-SHA256)
        #   - Anahtar sarmalama için: RSA-2048 + OAEP (MGF1-SHA256)
        # uygulanır. Bu kart, öğrencinin animasyon ile crypto_core.py
        # arasındaki farkı yanlış anlamamasını sağlar.
        self._banner = self._make_textbook_vs_production_banner()
        self.content_layout.addWidget(self._banner)

        self._step_lbl = QLabel()
        self._step_lbl.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        self._step_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._step_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._step_lbl)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 10px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)

        self._body = QLabel()
        self._body.setFont(QFont("Courier New", 10))
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
    # Kalıcı uyarı kartı
    # ------------------------------------------------------------------

    def _make_textbook_vs_production_banner(self) -> QFrame:
        """Textbook RSA vs projedeki üretim modları uyarı kartını üretir.

        Kart sade, kompakt ve tüm adımlar boyunca görünür kalır.
        Öğrencinin animasyondaki ``m^e mod n`` formülünü projede
        kullanılan şema sanmasını engeller.
        """
        banner = QFrame()
        yellow = ANIM_COLORS["accent_yellow"]
        banner.setStyleSheet(
            f"QFrame {{ background: rgba(184, 134, 11, 0.10); "
            f"border: 1px solid {yellow}; border-radius: 8px; }}"
        )
        lay = QHBoxLayout(banner)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        icon = QLabel("⚠")
        icon.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        icon.setStyleSheet(f"color: {yellow};")
        icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.addWidget(icon)

        text = QLabel(
            "<b>Pedagojik Not — Textbook RSA ≠ Projedeki RSA</b><br>"
            "Bu animasyon eğitim amaçlı <b>ham (textbook) RSA</b> "
            "şemasını gösterir: <i>c = m<sup>e</sup> mod n</i> / "
            "<i>m = c<sup>d</sup> mod n</i>. Projede "
            "<code>crypto_core.py</code> içinde kullanılan şema "
            "farklıdır:<br>"
            "&nbsp;&nbsp;• <b>İmza:</b> RSA-2048 + <b>PSS</b> "
            "(rastgele tuzlu dolgu, MGF1-SHA256)<br>"
            "&nbsp;&nbsp;• <b>Oturum anahtarı sarma:</b> RSA-2048 + "
            "<b>OAEP</b> (MGF1-SHA256)<br>"
            "Ham RSA deterministik ve seçili-şifreli-metin (CCA) "
            "saldırılarına açıktır; üretimde <b>asla doğrudan</b> "
            "kullanılmaz. Burada gösterilen matematik (modüler üs "
            "alma) hâlâ PSS/OAEP'in altında çalışır, ama üzerine "
            "dolgu katmanı eklenir."
        )
        text.setFont(QFont("Segoe UI", 9))
        text.setStyleSheet(f"color: {ANIM_COLORS['text_primary']};")
        text.setWordWrap(True)
        text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        lay.addWidget(text, stretch=1)
        return banner

    # ------------------------------------------------------------------
    # Adım render'ları
    # ------------------------------------------------------------------

    def _render_step(self, idx: int) -> None:
        self._step_lbl.setText(self._TITLES[idx])
        self._body.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._body.setText(_STEP_BODIES[idx])

    def _show_match_result(self) -> None:
        self._step_lbl.setText(self._TITLES[6])
        self._body.setTextFormat(Qt.TextFormat.RichText)
        self._body.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        green = ANIM_COLORS['accent_green']
        self._body.setText(
            f"Demo Açık Anahtar:   (e={_E},  n={_N})<br>"
            f"Demo Gizli Anahtar:  (d={_D},  n={_N})<br><br>"
            f"{'─' * 60}<br><br>"
            f"Bu projede kullanılan gerçek RSA-2048 anahtarları:<br><br>"
            f"Alice Açık Anahtarı (Base64):<br>"
            f"&nbsp;&nbsp;{self._alice_b64}<br><br>"
            f"Bob Açık Anahtarı (Base64):<br>"
            f"&nbsp;&nbsp;{self._bob_b64}<br><br>"
            f"<span style='color: {ANIM_COLORS['accent_yellow']}; font-weight:bold;'>"
            f"⚠ Demo değerler (p=61, q=53) eğitim içindir; gerçek anahtarlar farklı (p,q ≈ 1024-bit).</span><br><br>"
            f"<span style='color: {green}; font-weight:bold;'>✅&nbsp;&nbsp;Aynı Matematik, Farklı Boyut</span><br><br>"
            f"Demo'da gösterilen (e,n) → ASN.1 DER → Base64 adımlarının aynısı,<br>"
            f"gerçek 2048-bit p ve q ile uygulanarak yukarıdaki anahtarları üretir."
        )


# Adım metinleri (sınıf dışında tanımlanır; temiz tutar)
_STEP_BODIES: list[str] = [
    # Adım 0 — Asal sayı
    (
        "━━  ASAL SAYI NEDİR?  ━━\n\n"
        "Asal sayı: sadece 1'e ve kendisine tam bölünebilen sayıdır.\n\n"
        f"  p = {_P}  →  1 ve 61 dışında hiçbir sayıya bölünmez  ✓\n"
        f"  q = {_Q}  →  1 ve 53 dışında hiçbir sayıya bölünmez  ✓\n\n"
        "  Asal olmayan örnek:\n"
        "  15 = 3 × 5  →  1, 3, 5, 15'e bölünür  ✗ ASAL DEĞİL\n\n"
        "━━  NEDEN ÖNEMLİ?  ━━\n\n"
        "Gerçek RSA-2048'de p ve q'nun her biri yaklaşık\n"
        "309 haneli (1024-bit) kocaman asal sayılardır.\n\n"
        "Bu iki sayıyı çarpıp n'yi elde etmek:\n"
        "  → Saniyeler içinde hesaplanır  ⚡\n\n"
        "Ama n'yi görüp p ve q'yu geri bulmaya çalışmak:\n"
        "  → Dünyanın tüm bilgisayarları milyarlarca yıl\n"
        "    uğraşsa bile bulamaz  🔒\n\n"
        "İşte RSA'nın gücü bu 'tek yönlü yol'a dayanır."
    ),
    # Adım 1 — n = p × q
    (
        "━━  KİLİDİN İKİ PARÇASI BİRLEŞİYOR  ━━\n\n"
        "İki asal sayıyı çarparak herkese açık 'kilit sayısı' n'yi üretiyoruz:\n\n"
        f"  n  =  p  ×  q\n"
        f"  n  =  {_P}  ×  {_Q}\n"
        f"  n  =  {_N}\n\n"
        "━━  NE İŞE YARAR?  ━━\n\n"
        "n, hem açık anahtarın hem de gizli anahtarın içinde bulunur.\n"
        "Sana mesaj göndermek isteyen herkes n'yi kullanır.\n\n"
        "━━  GÜVENLİK?  ━━\n\n"
        f"  {_N} sayısını görüp {_P} × {_Q} diye ayrıştırmak küçük\n"
        f"  sayılarda kolaydır — ama 617 haneli bir sayı için\n"
        f"  bu işlem imkânsız hale gelir.\n\n"
        "n'yi herkes görebilir; ama n'den p ve q gizli kalır."
    ),
    # Adım 2 — φ(n)
    (
        "━━  GİZLİ FORMÜL: φ(n)  ━━\n\n"
        "φ(n) (phi), gizli anahtarı hesaplamak için kullanılan\n"
        "ara bir değerdir. Hiçbir zaman paylaşılmaz.\n\n"
        "Hesabı çok basit — sadece p ve q bilinirse:\n\n"
        f"  φ(n)  =  (p − 1)  ×  (q − 1)\n"
        f"  φ(n)  =  ({_P} − 1)  ×  ({_Q} − 1)\n"
        f"  φ(n)  =  {_P - 1}  ×  {_Q - 1}\n"
        f"  φ(n)  =  {_PHI}\n\n"
        "━━  NEDEN GİZLİ?  ━━\n\n"
        "φ(n) bilinirse gizli anahtar d kolayca hesaplanabilir.\n"
        "φ(n) bilinmezse (yani p ve q bilinmezse) d'yi bulmak\n"
        "matematiksel olarak neredeyse imkânsızdır.\n\n"
        "Kısacası:\n"
        "  p ve q  →  φ(n) kolayca bulunur\n"
        "  Ama  n  →  φ(n) bulunamaz  (çünkü p,q gizli)"
    ),
    # Adım 3 — e seçimi
    (
        "━━  HERKESİN BİLDİĞİ ŞİFRELEME GÜCÜ: e  ━━\n\n"
        "e, açık anahtarın bir parçasıdır — herkesle paylaşılır.\n"
        "Sana mesaj göndermek isteyen herkes e'yi kullanır.\n\n"
        f"  Seçilen:  e = {_E}\n\n"
        "━━  KURALI  ━━\n\n"
        f"  · e, 1 ile {_PHI} arasında olmalı\n"
        f"  · e ile {_PHI} 'aralarında asal' olmalı\n"
        f"    (başka bir deyişle, aralarındaki ortak bölen sadece 1)\n\n"
        f"  Kontrol:  OBEB({_E}, {_PHI}) = 1  ✓\n\n"
        "━━  GERÇEK HAYATTA  ━━\n\n"
        "Gerçek RSA'da e için neredeyse hep 65537 seçilir.\n"
        "Bu sayı hem küçük olduğundan şifreleme hızlıdır,\n"
        "hem de güvenlik açısından herhangi bir zayıflık içermez.\n\n"
        "Açık anahtar = (e, n) çifti\n"
        f"  →  (e={_E},  n={_N})"
    ),
    # Adım 4 — d hesabı (EEA)
    (
        "━━  SADECE SENİN ANAHTARIN: d  ━━\n\n"
        "d, gizli anahtarın çekirdeğidir. Kimseyle paylaşılmaz.\n\n"
        "d şu özelliği sağlamalı:\n\n"
        f"  e × d  ≡  1  (mod φ(n))\n\n"
        "Bu şu anlama gelir:\n"
        f"  {_E} ile şifrelediğin bir mesajı, sadece {_D} ile çözebilirsin.\n\n"
        "━━  NASIL BULUNUR?  ━━\n\n"
        "Genişletilmiş Öklid Algoritması adım adım:\n\n"
        + "\n".join(f"  {a}   {b}" for a, b in _EEA_STEPS)
        + f"\n\n  Bulunan:  d = {_D}\n\n"
        "━━  DOĞRULAMA  ━━\n\n"
        f"  {_E} × {_D}  mod  {_PHI}  =  {(_E * _D) % _PHI}  ✓\n\n"
        "Gizli anahtar = (d, n) çifti\n"
        f"  →  (d={_D},  n={_N})\n"
        f"\n━━  DOĞRULAMA — Gerçek Şifreleme/Deşifreleme  ━━\n\n"
        f"  m = 65  (örnek mesaj)\n\n"
        f"  Şifreleme:  c  =  m^e  mod  n\n"
        f"             c  =  65^{_E}  mod  {_N}\n"
        f"             c  =  {pow(65, _E, _N)}\n\n"
        f"  Deşifreleme:  m  =  c^d  mod  n\n"
        f"               m  =  {pow(65, _E, _N)}^{_D}  mod  {_N}\n"
        f"               m  =  {pow(pow(65, _E, _N), _D, _N)}  ✓  (orijinal mesaj)\n\n"
        f"Sadece d'yi bilen (yani gizli anahtarı bilen) {pow(65, _E, _N)}'i\n"
        f"tekrar {pow(pow(65, _E, _N), _D, _N)}'ye dönüştürebilir.\n"
    ),
    # Adım 5 — Anahtar kodlama (gerçek byte dönüşümü)
    (
        "━━  SAYILARDAN ANAHTAR DOSYASINA: ADIM ADIM  ━━\n\n"
        "Elimizde iki sayı var: e ve n\n"
        f"  e = {_E}   →  şifreleme gücü\n"
        f"  n = {_N}  →  kilit sayısı\n\n"
        "━━  ADIM 1 — Sayıları byte'a çevir  ━━\n\n"
        f"  n = {_N}  →  hex: {_N:04X}  →  byte: {' '.join(f'{b:02X}' for b in _N.to_bytes(2,'big'))}\n"
        f"  e = {_E}   →  hex: {_E:02X}    →  byte: {_E:02X}\n\n"
        "━━  ADIM 2 — DER etiketleri ekle (ASN.1 yapısı)  ━━\n\n"
        "  02 = INTEGER etiketi\n"
        "  30 = SEQUENCE etiketi\n\n"
        f"  DER(n) = 02 {len(_DER_N)-2:02X} {' '.join(f'{b:02X}' for b in _DER_N[2:])}\n"
        f"  DER(e) = 02 {len(_DER_E)-2:02X} {' '.join(f'{b:02X}' for b in _DER_E[2:])}\n"
        f"  SEQUENCE = 30 {len(_DER_SEQ)-2:02X} DER(n) DER(e)\n\n"
        f"  Tüm byte'lar: {_DER_HEX}\n\n"
        "━━  ADIM 3 — Base64'e çevir  ━━\n\n"
        "  Her 3 byte → 4 ASCII karakter\n\n"
        f"  Demo sonucu:  {_B64_DEMO}\n\n"
        "━━  GERÇEK ANAHTAR  ━━\n\n"
        "Gerçek RSA-2048'de n = 256 byte (2048-bit) olduğundan\n"
        "DER verisi ~270 byte → ~360 Base64 karakter olur.\n\n"
        "PEM formatı:\n"
        "  -----BEGIN PUBLIC KEY-----\n"
        "  [Base64 satırları]\n"
        "  -----END PUBLIC KEY-----\n\n"
        "→ Sonraki adımda gerçek anahtarların eşleşmesini göreceksiniz."
    ),
    # Adım 6 — Eşleşme (_show_match_result tarafından işlenir)
    "",
]
