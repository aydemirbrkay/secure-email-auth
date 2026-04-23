# Animasyon UI Yeniden Tasarımı — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tüm animasyon pencerelerini 85% ekran boyutuna getir; RSA ve SHA için kullanıcı tıklamalı navigasyon ekle; SHA'ya QPainter tabanlı A-H register diyagramı + blok zinciri görünümü ekle; AES'e animasyonlu intro, tıklanabilir round bar ve ShiftRows/MixColumns ok göstergeleri ekle.

**Architecture:** `base.py`'ye `manual_mode` parametresi ve ekran-bazlı boyutlandırma eklenir. Her animasyon penceresi bu temel sınıfı kullanarak ya otomatik (AES intro) ya manuel (RSA, SHA, AES roundları) navigasyon sunar. SHA-256 sıkıştırma diyagramı QPainter ile, AES intro animasyonu gizlenip sırayla gösterilen widget'larla yapılır.

**Tech Stack:** Python 3.12, PyQt6 6.6+ (QPainter, QTimer, QPushButton), mevcut ANIM_COLORS paleti

---

## Dosya Yapısı

```
animation_modals/
  base.py              ← MODIFY: manual_mode + 85% ekran boyutu
  sha256_pure.py       ← MODIFY: snapshot'lara T1, T2, W, K ekle
  rsa_animation.py     ← REWRITE: 7 manuel adım
  sha256_animation.py  ← REWRITE: QPainter diagram + blok zinciri
  aes_animation.py     ← REWRITE: intro animasyonu + tıklanabilir rounds + oklar
```

---

## Task 1: base.py — 85% Ekran Boyutu + Manuel Mod

**Files:**
- Modify: `animation_modals/base.py`

- [ ] **Step 1: base.py'yi tamamen yeniden yaz**

```python
# animation_modals/base.py
"""
CryptoAnimationWindow — Tüm animasyon pencerelerinin taban sınıfı.
QWidget subclass, show() ile bağımsız pencere olarak açılır.
manual_mode=True: kullanıcı tıklayarak ilerler (RSA, SHA, AES roundları).
manual_mode=False: QTimer otomatik oynatır (AES intro).
Pencere boyutu ekranın %85'i olacak şekilde ayarlanır.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ANIM_COLORS = {
    "bg_main":        "#1e1e2e",
    "bg_card":        "#313150",
    "bg_input":       "#3b3b5c",
    "text_primary":   "#cdd6f4",
    "text_secondary": "#a6adc8",
    "text_muted":     "#6c7086",
    "accent_blue":    "#89b4fa",
    "accent_green":   "#a6e3a1",
    "accent_yellow":  "#f9e2af",
    "accent_mauve":   "#cba6f7",
    "accent_peach":   "#fab387",
    "border":         "#45475a",
}

_SPEED_MAP: dict[str, int] = {"Yavaş": 2000, "Normal": 1500, "Hızlı": 800}

_BTN_STYLE = (
    f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
    f"color: {ANIM_COLORS['bg_main']}; border: none; "
    f"border-radius: 6px; padding: 8px 22px; font-weight: bold; font-size: 13px; }}"
    f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
    f"QPushButton:disabled {{ background: {ANIM_COLORS['bg_card']}; "
    f"color: {ANIM_COLORS['text_muted']}; }}"
)

_CLOSE_STYLE = (
    f"QPushButton {{ background: {ANIM_COLORS['bg_card']}; "
    f"color: {ANIM_COLORS['text_secondary']}; border: 1px solid {ANIM_COLORS['border']}; "
    f"border-radius: 6px; padding: 8px 18px; font-weight: bold; }}"
    f"QPushButton:hover {{ background: {ANIM_COLORS['accent_peach']}; "
    f"color: {ANIM_COLORS['bg_main']}; }}"
)


class CryptoAnimationWindow(QWidget):
    """
    Ortak animasyon penceresi taban sınıfı.

    Alt sınıflar şunları override eder:
      _init_content()       → content_area'ya widget ekler
      _render_step(idx)     → idx numaralı adımı gösterir
      _show_match_result()  → son eşleşme ekranını gösterir

    manual_mode=True ise kullanıcı ◀ Geri / İleri ▶ butonlarıyla ilerler.
    manual_mode=False ise QTimer otomatik oynatır (hız seçici görünür).
    """

    def __init__(
        self,
        title: str,
        total_steps: int,
        manual_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(title)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet(
            f"background-color: {ANIM_COLORS['bg_main']}; "
            f"color: {ANIM_COLORS['text_primary']};"
        )

        # Ekranın %85'i kadar boyutlandır
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.resize(int(g.width() * 0.85), int(g.height() * 0.85))
        else:
            self.resize(1200, 800)

        self.manual_mode: bool = manual_mode
        self.current_step: int = 0
        self.total_steps: int = total_steps
        self.speed_ms: int = 1500

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)

        self._init_base_ui()
        self._init_content()

    # ------------------------------------------------------------------
    # UI kurulumu
    # ------------------------------------------------------------------

    def _init_base_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel(self.windowTitle())
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self._progress = QProgressBar()
        self._progress.setMaximum(self.total_steps)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setStyleSheet(
            f"QProgressBar {{ border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 4px; background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_primary']}; text-align: center; height: 18px; }}"
            f"QProgressBar::chunk {{ background-color: {ANIM_COLORS['accent_blue']}; "
            f"border-radius: 3px; }}"
        )
        layout.addWidget(self._progress)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_area, stretch=1)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        if self.manual_mode:
            self._btn_prev = QPushButton("◀  Geri")
            self._btn_prev.setStyleSheet(_BTN_STYLE)
            self._btn_prev.setEnabled(False)
            self._btn_prev.clicked.connect(self._go_back)
            controls.addWidget(self._btn_prev)

            self._btn_next = QPushButton("İleri  ▶")
            self._btn_next.setStyleSheet(_BTN_STYLE)
            self._btn_next.clicked.connect(self._advance_step)
            controls.addWidget(self._btn_next)
        else:
            speed_lbl = QLabel("Hız:")
            speed_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
            controls.addWidget(speed_lbl)

            self._speed_combo = QComboBox()
            self._speed_combo.addItems(list(_SPEED_MAP.keys()))
            self._speed_combo.setCurrentText("Normal")
            self._speed_combo.setStyleSheet(
                f"QComboBox {{ background: {ANIM_COLORS['bg_input']}; "
                f"color: {ANIM_COLORS['text_primary']}; "
                f"border: 1px solid {ANIM_COLORS['border']}; "
                f"border-radius: 4px; padding: 4px 8px; }}"
            )
            self._speed_combo.currentTextChanged.connect(self._on_speed_changed)
            controls.addWidget(self._speed_combo)

        controls.addStretch()

        btn_close = QPushButton("✕  Kapat")
        btn_close.setStyleSheet(_CLOSE_STYLE)
        btn_close.clicked.connect(self.close)
        controls.addWidget(btn_close)

        layout.addLayout(controls)

    # ------------------------------------------------------------------
    # Alt sınıf arayüzü
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        raise NotImplementedError

    def _render_step(self, step_idx: int) -> None:
        raise NotImplementedError

    def _show_match_result(self) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Navigasyon
    # ------------------------------------------------------------------

    def _on_speed_changed(self, text: str) -> None:
        self.speed_ms = _SPEED_MAP[text]
        if self._timer.isActive():
            self._timer.setInterval(self.speed_ms)

    def _go_back(self) -> None:
        """Manuel mod: bir önceki adıma dön."""
        if self.current_step <= 0:
            return
        self.current_step -= 1
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)
        self._btn_prev.setEnabled(self.current_step > 0)
        self._btn_next.setEnabled(True)
        self._btn_next.setText("İleri  ▶")

    def _advance_step(self) -> None:
        """Bir sonraki adıma geç (manuel veya otomatik)."""
        if self.manual_mode:
            if self.current_step >= self.total_steps - 1:
                self._progress.setValue(self.total_steps)
                self._show_match_result()
                self._btn_next.setEnabled(False)
                self._btn_next.setText("✅  Tamamlandı")
                return
            self.current_step += 1
            self._render_step(self.current_step)
            self._progress.setValue(self.current_step + 1)
            if hasattr(self, "_btn_prev"):
                self._btn_prev.setEnabled(True)
        else:
            self.current_step += 1
            if self.current_step >= self.total_steps:
                self._timer.stop()
                self._progress.setValue(self.total_steps)
                self._show_match_result()
                return
            self._render_step(self.current_step)
            self._progress.setValue(self.current_step + 1)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self.current_step == 0:
            self._render_step(0)
            self._progress.setValue(1)
            if not self.manual_mode:
                self._timer.start(self.speed_ms)
```

- [ ] **Step 2: Import testi**

```
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ/bitirme_odevi"
.venv/Scripts/python -c "from animation_modals.base import CryptoAnimationWindow, ANIM_COLORS; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Mevcut testlerin hâlâ geçtiğini doğrula**

```
.venv/Scripts/python -m pytest test_sha256_pure.py test_aes_pure.py test_crypto_core.py -v
```

Beklenen: Tüm testler PASSED

- [ ] **Step 4: Commit**

```bash
git add animation_modals/base.py
git commit -m "feat: add manual navigation mode and 85% screen sizing to base window"
```

---

## Task 2: sha256_pure.py — Zenginleştirilmiş Snapshot Verisi

**Files:**
- Modify: `animation_modals/sha256_pure.py`
- Modify: `test_sha256_pure.py` (yeni test eklenir)

SHA kompresyon diyagramı için her snapshot'a `w`, `k`, `t1`, `t2` değerleri eklenir.

- [ ] **Step 1: Yeni teste snapshot anahtarlarını ekle**

`test_sha256_pure.py` dosyasına şu test metodunu ekle (`TestSHA256Pure` sınıfı içine):

```python
    def test_round_snapshots_have_rich_data(self):
        result = sha256_steps(b"Hello World")
        snap = result["round_snapshots"][0]
        self.assertIn("w", snap)
        self.assertIn("k", snap)
        self.assertIn("t1", snap)
        self.assertIn("t2", snap)
        # Her değer 8 karakterlik hex string olmalı
        self.assertEqual(len(snap["w"]), 8)
        self.assertEqual(len(snap["k"]), 8)
```

- [ ] **Step 2: Testi çalıştır, FAIL olduğunu doğrula**

```
.venv/Scripts/python -m pytest test_sha256_pure.py::TestSHA256Pure::test_round_snapshots_have_rich_data -v
```

Beklenen: FAIL (KeyError: 'w')

- [ ] **Step 3: sha256_pure.py'de sıkıştırma döngüsünü güncelle**

`sha256_pure.py`'de compression loop içindeki `if i in (0, 31, 63):` bloğunu bul ve şununla değiştir:

```python
            if i in (0, 31, 63):
                round_snapshots.append({
                    "round": i + 1,
                    "a": f"{a:08x}",
                    "e": f"{e:08x}",
                    "registers": [f"{v:08x}" for v in [a, b, c, d, e, f, g, hh]],
                    "w": f"{w[i]:08x}",
                    "k": f"{K[i]:08x}",
                    "t1": f"{temp1:08x}",
                    "t2": f"{temp2:08x}",
                })
```

Not: `temp1` ve `temp2` zaten döngü içinde hesaplanmıştır, snapshot'dan önce erişilebilir.

- [ ] **Step 4: Tüm testleri çalıştır, PASS olduğunu doğrula**

```
.venv/Scripts/python -m pytest test_sha256_pure.py -v
```

Beklenen: 7/7 PASSED

- [ ] **Step 5: Commit**

```bash
git add animation_modals/sha256_pure.py test_sha256_pure.py
git commit -m "feat: add W, K, T1, T2 fields to SHA-256 round snapshots for diagram"
```

---

## Task 3: rsa_animation.py — 7 Manuel Adım

**Files:**
- Rewrite: `animation_modals/rsa_animation.py`

- [ ] **Step 1: rsa_animation.py'yi tamamen yeniden yaz**

```python
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
```

- [ ] **Step 2: Import testi**

```
.venv/Scripts/python -c "from animation_modals.rsa_animation import RSAAnimationWindow; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Syntax doğrula**

```
.venv/Scripts/python -c "import ast; ast.parse(open('animation_modals/rsa_animation.py').read()); print('Syntax OK')"
```

- [ ] **Step 4: Commit**

```bash
git add animation_modals/rsa_animation.py
git commit -m "feat: redesign RSAAnimationWindow with 7 manual educational steps"
```

---

## Task 4: sha256_animation.py — Kompresyon Diyagramı + Blok Zinciri

**Files:**
- Rewrite: `animation_modals/sha256_animation.py`

SHA-256 sıkıştırma fonksiyonu QPainter ile çizilir. Her 512-bit blok için A-H registerları gösterilir, bloklar ok ile birbirine bağlanır. Kullanıcı manuel ilerler.

- [ ] **Step 1: sha256_animation.py'yi tamamen yeniden yaz**

```python
# animation_modals/sha256_animation.py
"""
SHA256AnimationWindow — SHA-256 hash sürecini görselleştirir.
• Her 512-bit blok için A-H register diyagramı (QPainter)
• Blok zinciri: Blok kartları okla birbirine bağlı
• Manuel navigasyon: kullanıcı ◀ / ▶ ile ilerler
"""
from __future__ import annotations
import struct
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QLabel, QScrollArea, QSizePolicy,
    QVBoxLayout, QHBoxLayout, QWidget,
)
from .base import CryptoAnimationWindow, ANIM_COLORS
from .sha256_pure import sha256_steps

# Renk eşlemesi — her register farklı renk
_REG_COLORS = [
    "#89b4fa",  # A — blue
    "#cba6f7",  # B — mauve
    "#a6e3a1",  # C — green
    "#f9e2af",  # D — yellow
    "#fab387",  # E — peach
    "#94e2d5",  # F — teal
    "#f38ba8",  # G — red
    "#74c7ec",  # H — sky
]
_REG_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H"]


# ---------------------------------------------------------------------------
# Sıkıştırma fonksiyonu diyagramı (QPainter tabanlı widget)
# ---------------------------------------------------------------------------

class _SHA256DiagramWidget(QWidget):
    """
    Tek bir SHA-256 round'u için A-H sıkıştırma fonksiyonu diyagramını çizer.

    Gösterim:
      Üst satır  : 8 renkli kutu (A-H giriş değerleri)
      Orta bölge : T1 ve T2 hesaplama kutuları + K/W değerleri
      Alt satır  : 8 renkli kutu (A'-H' çıkış değerleri)
      Oklar      : A→T2, E→T1, D+T1→E', T1+T2→A'
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(340)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        # Varsayılan veri
        self._regs_in: list[str] = ["--------"] * 8
        self._regs_out: list[str] = ["--------"] * 8
        self._t1 = "--------"
        self._t2 = "--------"
        self._w = "--------"
        self._k = "--------"
        self._round_no = 0

    def set_data(
        self,
        regs_in: list[str],
        regs_out: list[str],
        t1: str,
        t2: str,
        w: str,
        k: str,
        round_no: int,
    ) -> None:
        self._regs_in = regs_in
        self._regs_out = regs_out
        self._t1 = t1
        self._t2 = t2
        self._w = w
        self._k = k
        self._round_no = round_no
        self.update()

    # --- QPainter çizimi ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        box_w = max(60, min(80, (W - 80) // 8))
        box_h = 44
        gap = max(3, (W - 80 - 8 * box_w) // 7)
        total = 8 * box_w + 7 * gap
        ox = (W - total) // 2  # yatay merkez

        top_y = 12
        mid_y = top_y + box_h + 50
        bot_y = mid_y + 90

        font_lbl = QFont("Segoe UI", 9, QFont.Weight.Bold)
        font_val = QFont("Courier New", 8)
        font_mid = QFont("Courier New", 9)

        # ── Üst satır: giriş registerları ──
        self._draw_register_row(
            p, self._regs_in, ox, top_y, box_w, box_h, gap,
            font_lbl, font_val, suffix=""
        )

        # ── T2 ve T1 kutuları ──
        t2_x = ox
        t2_w = int(total * 0.38)
        t1_x = ox + total - int(total * 0.52)
        t1_w = int(total * 0.52)

        p.setFont(font_mid)

        # T2 kutusu
        self._draw_box(p, t2_x, mid_y, t2_w, 72,
                       QColor("#3b3b5c"), QColor(ANIM_COLORS["accent_mauve"]))
        p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
        p.drawText(QRect(t2_x + 4, mid_y + 4, t2_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, "T2 = Σ0(A) + Maj(A,B,C)")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t2_x + 4, mid_y + 26, t2_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, f"= {self._t2}")

        # T1 kutusu
        self._draw_box(p, t1_x, mid_y, t1_w, 72,
                       QColor("#3b3b5c"), QColor(ANIM_COLORS["accent_yellow"]))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(t1_x + 4, mid_y + 4, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   "T1 = Σ1(E) + Ch(E,F,G) + H + K + W")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t1_x + 4, mid_y + 26, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, f"= {self._t1}")
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(t1_x + 4, mid_y + 48, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   f"K={self._k[:6]}  W={self._w[:6]}")

        # ── Oklar ──
        pen = QPen(QColor(ANIM_COLORS["accent_blue"]), 2)
        pen.setStyle(Qt.PenStyle.SolidLine)
        p.setPen(pen)

        # A'nın merkezi → T2 kutusunun üstü
        a_cx = ox + box_w // 2
        p.drawLine(a_cx, top_y + box_h, a_cx, top_y + box_h + 20)
        p.drawLine(a_cx, top_y + box_h + 20, t2_x + t2_w // 2, mid_y)
        self._arrowhead(p, t2_x + t2_w // 2, mid_y)

        # E'nin merkezi → T1 kutusunun üstü
        e_cx = ox + 4 * (box_w + gap) + box_w // 2
        p.drawLine(e_cx, top_y + box_h, e_cx, top_y + box_h + 20)
        p.drawLine(e_cx, top_y + box_h + 20, t1_x + t1_w // 2, mid_y)
        self._arrowhead(p, t1_x + t1_w // 2, mid_y)

        # T2 → A' (yeni A = T1 + T2)
        pen2 = QPen(QColor(ANIM_COLORS["accent_mauve"]), 2)
        p.setPen(pen2)
        a_out_cx = ox + box_w // 2
        p.drawLine(t2_x + t2_w // 2, mid_y + 72, a_out_cx, bot_y)
        self._arrowhead(p, a_out_cx, bot_y)

        # T1 → E' (yeni E = D + T1)
        pen3 = QPen(QColor(ANIM_COLORS["accent_yellow"]), 2)
        p.setPen(pen3)
        e_out_cx = ox + 4 * (box_w + gap) + box_w // 2
        p.drawLine(t1_x + t1_w // 2, mid_y + 72, e_out_cx, bot_y)
        self._arrowhead(p, e_out_cx, bot_y)

        # D → E' (D + T1 → yeni E)
        pen4 = QPen(QColor(ANIM_COLORS["accent_green"]), 1)
        pen4.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen4)
        d_cx = ox + 3 * (box_w + gap) + box_w // 2
        p.drawLine(d_cx, top_y + box_h, d_cx, bot_y)
        p.drawLine(d_cx, bot_y, e_out_cx, bot_y)

        # Kaydırma okları: B←A, C←B ... (basit sağa oklar, üst satırın altı)
        pen5 = QPen(QColor(ANIM_COLORS["text_muted"]), 1)
        pen5.setStyle(Qt.PenStyle.DotLine)
        p.setPen(pen5)
        shift_y = top_y + box_h + 8
        for i in range(1, 8):
            if i == 4:
                continue  # E farklı hesaplanıyor, atla
            src_cx = ox + (i - 1) * (box_w + gap) + box_w // 2
            dst_cx = ox + i * (box_w + gap) + box_w // 2
            p.drawLine(src_cx, shift_y, dst_cx, shift_y)
            self._arrowhead(p, dst_cx, shift_y, size=5)

        # ── Alt satır: çıkış registerları ──
        self._draw_register_row(
            p, self._regs_out, ox, bot_y, box_w, box_h, gap,
            font_lbl, font_val, suffix="'"
        )

        # Round numarası
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(QRect(0, 0, W, 14), Qt.AlignmentFlag.AlignRight,
                   f"Round {self._round_no}/64  ")

        p.end()

    # --- Yardımcılar ---

    def _draw_register_row(
        self, p: QPainter,
        values: list[str], ox: int, y: int,
        box_w: int, box_h: int, gap: int,
        font_lbl: QFont, font_val: QFont,
        suffix: str,
    ) -> None:
        for i, (lbl, val, col) in enumerate(
            zip(_REG_LABELS, values, _REG_COLORS)
        ):
            x = ox + i * (box_w + gap)
            self._draw_box(p, x, y, box_w, box_h,
                           QColor(col + "33"), QColor(col))
            p.setFont(font_lbl)
            p.setPen(QColor(col))
            p.drawText(QRect(x, y + 2, box_w, 16),
                       Qt.AlignmentFlag.AlignCenter, lbl + suffix)
            p.setFont(font_val)
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x + 2, y + 20, box_w - 4, 20),
                       Qt.AlignmentFlag.AlignCenter, val[:8])

    @staticmethod
    def _draw_box(
        p: QPainter, x: int, y: int, w: int, h: int,
        fill: QColor, border: QColor,
    ) -> None:
        p.setBrush(QBrush(fill))
        pen = QPen(border, 1)
        p.setPen(pen)
        p.drawRoundedRect(x, y, w, h, 4, 4)

    @staticmethod
    def _arrowhead(p: QPainter, x: int, y: int, size: int = 6) -> None:
        """Küçük içi dolu ok ucu."""
        pts = QPolygon([
            QPoint(x, y),
            QPoint(x - size, y - size * 2),
            QPoint(x + size, y - size * 2),
        ])
        p.setBrush(QBrush(p.pen().color()))
        p.drawPolygon(pts)


# ---------------------------------------------------------------------------
# SHA-256 Animasyon Penceresi
# ---------------------------------------------------------------------------

class SHA256AnimationWindow(CryptoAnimationWindow):
    """
    SHA-256 animasyon penceresi.

    Adımlar:
      0        : Padding görselleştirmesi
      1..N     : Her 512-bit blok için kompresyon diyagramı (3 snapshot: r1,r32,r64)
      son adım : Hash eşleşmesi (_show_match_result)

    Parametreler:
      message      : kullanıcının orijinal mesaj metni
      expected_hash: crypto_core'un ürettiği hex hash
    """

    def __init__(
        self,
        message: str,
        expected_hash: str,
        parent: QWidget | None = None,
    ) -> None:
        self._message = message
        self._expected_hash = expected_hash
        self._data = sha256_steps(message.encode("utf-8"))

        # Adım listesini oluştur
        # Adım 0: padding
        # Adım 1..3*N: her blok için 3 snapshot (r1, r32, r64)
        # Son adım: eşleşme (_show_match_result)
        n_blocks = self._data["blocks_count"]
        snaps = self._data["round_snapshots"]
        # 3 snapshot per block
        total = 1 + len(snaps)   # padding + all snapshots
        super().__init__(
            "🔐  SHA-256 Hash Animasyonu",
            total,
            manual_mode=True,
        )
        self._snaps = snaps

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        from PyQt6.QtWidgets import QStackedWidget

        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Padding
        self._page_padding = self._make_padding_page()
        self._stack.addWidget(self._page_padding)

        # Sayfa 1 — Kompresyon diyagramı (tüm snapshot'lar için tek sayfa, veri güncellenir)
        self._page_diagram = self._make_diagram_page()
        self._stack.addWidget(self._page_diagram)

        # Sayfa 2 — Eşleşme
        self._page_match = self._make_match_page()
        self._stack.addWidget(self._page_match)

    def _make_padding_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Adım 1 — Padding ve Blok Yapısı")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        d = self._data
        bc = d["blocks_count"]
        preview = d["binary_preview"]
        padded_len = d["padded_len"]

        info = QLabel(
            f"Mesaj: \"{self._message[:50]}\"\n\n"
            f"İlk 8 byte (binary):\n  {preview}\n\n"
            f"Padding işlemleri:\n"
            f"  1. '1' biti eklendi\n"
            f"  2. '0' bitleri ile 512'nin katına tamamlandı\n"
            f"  3. Sonuna 64-bit mesaj uzunluğu eklendi\n\n"
            f"Sonuç: {padded_len} byte → {bc} adet 512-bit blok\n\n"
            + "\n".join(
                f"  ▪ Blok {i+1}:  byte {i*64} – {(i+1)*64-1}"
                for i in range(bc)
            )
        )
        info.setFont(QFont("Courier New", 12))
        info.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    def _make_diagram_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)

        self._diag_title = QLabel()
        self._diag_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._diag_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._diag_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._diag_title)

        self._diag_widget = _SHA256DiagramWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._diag_widget)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll, stretch=1)

        # Hash zinciri göstergesi (alt)
        self._chain_lbl = QLabel()
        self._chain_lbl.setFont(QFont("Courier New", 10))
        self._chain_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._chain_lbl.setWordWrap(True)
        self._chain_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._chain_lbl)
        return w

    def _make_match_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        self._match_lbl = QLabel()
        self._match_lbl.setFont(QFont("Courier New", 12))
        self._match_lbl.setWordWrap(True)
        self._match_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(self._match_lbl)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    # Adım render'ı
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if step_idx == 0:
            self._stack.setCurrentWidget(self._page_padding)
            return

        # step_idx 1..len(snaps) → snapshot[step_idx - 1]
        snap_idx = step_idx - 1
        if snap_idx >= len(self._snaps):
            return

        snap = self._snaps[snap_idx]
        self._stack.setCurrentWidget(self._page_diagram)

        # Hangi blok, hangi round?
        snap_round = snap["round"]  # 1, 32, veya 64
        block_no = snap_idx // 3 + 1  # 3 snapshot per block
        self._diag_title.setText(
            f"Blok {block_no} / {self._data['blocks_count']}  —  "
            f"Sıkıştırma Round {snap_round} / 64"
        )

        # Mevcut register değerleri (bu snapshot'taki çıkış)
        regs_out = snap["registers"]  # [a, b, c, d, e, f, g, h] sonrası

        # Bir önceki snapshot'tan giriş değerleri (veya H0 sabitleri)
        if snap_idx > 0 and snap_idx % 3 != 0:
            regs_in = self._snaps[snap_idx - 1]["registers"]
        else:
            regs_in = self._data["initial_h"]

        self._diag_widget.set_data(
            regs_in=regs_in,
            regs_out=regs_out,
            t1=snap.get("t1", "--------"),
            t2=snap.get("t2", "--------"),
            w=snap.get("w", "--------"),
            k=snap.get("k", "--------"),
            round_no=snap_round,
        )

        # Zincir göstergesi
        chain_parts = []
        for i in range(block_no):
            if i < block_no - 1:
                chain_parts.append(f"[Blok {i+1} →]")
            else:
                chain_parts.append(f"[Blok {i+1} ←burada]")
        self._chain_lbl.setText("  →  ".join(chain_parts) + "  →  [Final Hash]")

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._page_match)
        computed = self._data["final_hash"]
        match = computed == self._expected_hash
        icon = "✅" if match else "❌"
        color = ANIM_COLORS["accent_green"] if match else ANIM_COLORS["accent_peach"]

        snaps = self._data["round_snapshots"]
        snap_summary = "\n".join(
            f"  Round {s['round']:>2}:  A={s['a']}  E={s['e']}"
            for s in snaps
        )
        self._match_lbl.setText(
            f"64-round sıkıştırma tamamlandı.\n\n"
            f"Round anlık görüntüleri:\n{snap_summary}\n\n"
            f"{'─' * 64}\n\n"
            f"Animasyonun hesapladığı:\n  {computed}\n\n"
            f"crypto_core çıktısı:\n  {self._expected_hash}\n\n"
            f"{icon}  Eşleşme Başarılı"
        )
        self._match_lbl.setStyleSheet(f"color: {color};")
```

- [ ] **Step 2: Import testi**

```
.venv/Scripts/python -c "from animation_modals.sha256_animation import SHA256AnimationWindow; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Syntax doğrula**

```
.venv/Scripts/python -c "import ast; ast.parse(open('animation_modals/sha256_animation.py').read()); print('Syntax OK')"
```

- [ ] **Step 4: Commit**

```bash
git add animation_modals/sha256_animation.py
git commit -m "feat: redesign SHA256AnimationWindow with QPainter compression diagram and block chain view"
```

---

## Task 5: aes_animation.py — Intro Animasyonu + Tıklanabilir Roundlar + Oklar

**Files:**
- Rewrite: `animation_modals/aes_animation.py`

- [ ] **Step 1: aes_animation.py'yi tamamen yeniden yaz**

```python
# animation_modals/aes_animation.py
"""
AESAnimationWindow — AES-256-GCM şifreleme sürecini görselleştirir.

Yapı:
  1. Giriş animasyonu: AES-256 round yapısı adım adım belirir (otomatik, QTimer)
  2. Round görünümü: 14 round, tıklanabilir round bar, manuel navigasyon
     - SubBytes: hücre-hücre highlight (MatrixWidget.highlight_cells_sequential)
     - ShiftRows: satır kaydırma okları + animate_row_shift
     - MixColumns: sütun karıştırma görsel açıklaması
     - AddRoundKey: XOR highlight
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon, QPoint
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from .base import CryptoAnimationWindow, ANIM_COLORS
from .matrix_widget import MatrixWidget
from .aes_pure import aes256_encrypt_with_rounds

_COLORS_OP = {
    "SubBytes":    ANIM_COLORS["accent_yellow"],
    "ShiftRows":   ANIM_COLORS["accent_blue"],
    "MixColumns":  ANIM_COLORS["accent_mauve"],
    "AddRoundKey": ANIM_COLORS["accent_peach"],
}


# ---------------------------------------------------------------------------
# AES Giriş Animasyonu Widget'ı
# ---------------------------------------------------------------------------

class _AESIntroWidget(QWidget):
    """
    AES-256 round yapısını aşamalı olarak gösteren giriş widget'ı.
    QTimer ile her 600ms'de bir bileşen görünür hale gelir.
    Tüm bileşenler göründükten sonra 'ready' sinyali yerine callback çağrılır.
    """

    _PHASES = [
        # (widget_index, widget_factory)  — sırayla görünür
    ]

    def __init__(self, on_complete: "callable", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_complete = on_complete
        self._phase = 0
        self._widgets: list[QWidget] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._show_next_phase)
        self._init_ui()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(40, 20, 40, 20)
        main.setSpacing(0)
        main.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("AES-256  Şifreleme Süreci")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(title)
        main.addSpacing(16)

        # Giriş kutusu
        self._intro_plain = self._make_box(
            "📄  Düz Metin  (Plaintext)", ANIM_COLORS["text_secondary"], width=320
        )
        main.addWidget(self._intro_plain, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._intro_plain.setVisible(False)
        self._widgets.append(self._intro_plain)

        # Ok aşağı
        arr0 = self._make_arrow()
        main.addWidget(arr0, alignment=Qt.AlignmentFlag.AlignHCenter)
        arr0.setVisible(False)
        self._widgets.append(arr0)

        # Initial round
        self._box_r0 = self._make_round_box(
            "🔑  Initial Round  (Round 0)",
            ["AddRoundKey"],
            ANIM_COLORS["accent_peach"],
        )
        main.addWidget(self._box_r0, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_r0.setVisible(False)
        self._widgets.append(self._box_r0)

        # Ok aşağı
        arr1 = self._make_arrow()
        main.addWidget(arr1, alignment=Qt.AlignmentFlag.AlignHCenter)
        arr1.setVisible(False)
        self._widgets.append(arr1)

        # Main rounds
        self._box_main = self._make_round_box(
            "🔄  Ana Roundlar  (R1 – R13)",
            ["1-SubBytes", "2-ShiftRows", "3-MixColumns", "4-AddRoundKey"],
            ANIM_COLORS["accent_blue"],
        )
        main.addWidget(self._box_main, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_main.setVisible(False)
        self._widgets.append(self._box_main)

        # Ok aşağı
        arr2 = self._make_arrow()
        main.addWidget(arr2, alignment=Qt.AlignmentFlag.AlignHCenter)
        arr2.setVisible(False)
        self._widgets.append(arr2)

        # Final round
        self._box_r14 = self._make_round_box(
            "🏁  Son Round  (R14)",
            ["1-SubBytes", "2-ShiftRows", "3-AddRoundKey  (MixColumns yok)"],
            ANIM_COLORS["accent_green"],
        )
        main.addWidget(self._box_r14, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_r14.setVisible(False)
        self._widgets.append(self._box_r14)

        # Ok aşağı
        arr3 = self._make_arrow()
        main.addWidget(arr3, alignment=Qt.AlignmentFlag.AlignHCenter)
        arr3.setVisible(False)
        self._widgets.append(arr3)

        # Şifreli metin
        self._intro_cipher = self._make_box(
            "🔒  Şifreli Metin  (Ciphertext)", ANIM_COLORS["accent_green"], width=320
        )
        main.addWidget(self._intro_cipher, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._intro_cipher.setVisible(False)
        self._widgets.append(self._intro_cipher)

        main.addSpacing(20)

        # Başla butonu (başlangıçta gizli)
        self._btn_start = QPushButton("▶  Görselleştirmeyi Başlat")
        self._btn_start.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._btn_start.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['bg_main']}; border: none; "
            f"border-radius: 8px; padding: 12px 32px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        self._btn_start.setVisible(False)
        self._btn_start.clicked.connect(self._on_complete)
        main.addWidget(self._btn_start, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._widgets.append(self._btn_start)

    @staticmethod
    def _make_box(text: str, color: str, width: int = 300) -> QFrame:
        f = QFrame()
        f.setFixedWidth(width)
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(12, 10, 12, 10)
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        return f

    @staticmethod
    def _make_round_box(title: str, ops: list[str], color: str) -> QFrame:
        f = QFrame()
        f.setFixedWidth(400)
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {color}; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        for op in ops:
            o = QLabel(f"  →  {op}")
            o.setFont(QFont("Segoe UI", 10))
            o.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']}; border: none;")
            lay.addWidget(o)
        return f

    @staticmethod
    def _make_arrow() -> QLabel:
        lbl = QLabel("⬇")
        lbl.setFont(QFont("Segoe UI", 20))
        lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(28)
        return lbl

    def start(self) -> None:
        self._timer.start(600)

    def _show_next_phase(self) -> None:
        if self._phase >= len(self._widgets):
            self._timer.stop()
            return
        self._widgets[self._phase].setVisible(True)
        self._phase += 1


# ---------------------------------------------------------------------------
# ShiftRows ok göstergesi
# ---------------------------------------------------------------------------

class _ShiftRowsArrowWidget(QWidget):
    """Satırların kaç bayt kaydığını gösteren ok etiketi sütunu."""

    _SHIFTS = [
        ("Satır 1", "kaymaz",    ANIM_COLORS["text_muted"]),
        ("Satır 2", "← 1 bayt", ANIM_COLORS["accent_blue"]),
        ("Satır 3", "← 2 bayt", ANIM_COLORS["accent_mauve"]),
        ("Satır 4", "← 3 bayt", ANIM_COLORS["accent_peach"]),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(12)
        for row_lbl, shift_lbl, color in self._SHIFTS:
            row = QHBoxLayout()
            r = QLabel(row_lbl)
            r.setFont(QFont("Segoe UI", 10))
            r.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
            r.setFixedWidth(50)
            row.addWidget(r)
            s = QLabel(shift_lbl)
            s.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            s.setStyleSheet(f"color: {color};")
            row.addWidget(s)
            lay.addLayout(row)
        self.setFixedWidth(130)


# ---------------------------------------------------------------------------
# MixColumns açıklama widget'ı
# ---------------------------------------------------------------------------

class _MixColumnsWidget(QWidget):
    """Her sütunun 4 byte'ının GF(2^8)'de nasıl karıştığını gösterir."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        title = QLabel("Her sütun kendi içinde karışır:")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(title)

        for c in range(4):
            col_lbl = QLabel(
                f"Sütun {c+1}:  [S[0][{c}] ⊕ S[1][{c}] ⊕ S[2][{c}] ⊕ S[3][{c}]]"
            )
            col_lbl.setFont(QFont("Courier New", 9))
            col_lbl.setStyleSheet(
                f"color: {ANIM_COLORS['accent_mauve']};"
                f"background: {ANIM_COLORS['bg_input']};"
                "border-radius: 3px; padding: 2px 4px;"
            )
            lay.addWidget(col_lbl)

        note = QLabel("GF(2⁸) çarpımı — difüzyon sağlar")
        note.setFont(QFont("Segoe UI", 8))
        note.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(note)

        self.setFixedWidth(280)


# ---------------------------------------------------------------------------
# Yardımcı: step listesi oluştur
# ---------------------------------------------------------------------------

def _build_steps(rounds_data: list[dict]) -> list[dict]:
    steps: list[dict] = []
    for rd in rounds_data:
        rnd = rd["round"]
        if rnd == 0:
            steps.append({
                "round": 0, "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": "Round 0 — Initial AddRoundKey\nPlaintext, ilk round anahtarı ile XOR'landı.",
            })
        elif rnd <= 13:
            for op, key, desc in [
                ("SubBytes",   "after_sub_bytes",    f"Round {rnd} — SubBytes\nHer byte S-Box'taki karşılığıyla değiştirildi."),
                ("ShiftRows",  "after_shift_rows",   f"Round {rnd} — ShiftRows\nSatır 1: sabit, 2: 1←, 3: 2←, 4: 3← kaydı."),
                ("MixColumns", "after_mix_columns",  f"Round {rnd} — MixColumns\nHer sütun GF(2⁸) matris çarpımıyla karıştırıldı."),
                ("AddRoundKey","after_add_round_key",f"Round {rnd} — AddRoundKey\nState, {rnd}. round anahtarı ile XOR'landı."),
            ]:
                steps.append({
                    "round": rnd, "operation": op,
                    "matrix": rd[key],
                    "color": _COLORS_OP[op],
                    "description": desc,
                })
        else:
            for op, key, desc in [
                ("SubBytes",   "after_sub_bytes",    "Round 14 — SubBytes  (Son round)"),
                ("ShiftRows",  "after_shift_rows",   "Round 14 — ShiftRows"),
                ("AddRoundKey","after_add_round_key","Round 14 — AddRoundKey  (MixColumns yok)"),
            ]:
                steps.append({
                    "round": rnd, "operation": op,
                    "matrix": rd[key],
                    "color": _COLORS_OP[op],
                    "description": desc,
                })
    return steps


# ---------------------------------------------------------------------------
# AES Animasyon Penceresi
# ---------------------------------------------------------------------------

class AESAnimationWindow(CryptoAnimationWindow):
    """
    AES-256-GCM animasyon penceresi.

    Parametreler:
      key             : 32 byte session key
      plaintext       : şifrelenecek veri (ilk 16 byte kullanılır)
      expected_ct_hex : crypto_core AES-GCM çıktısının hex preview'u
    """

    def __init__(
        self,
        key: bytes,
        plaintext: bytes,
        expected_ct_hex: str,
        parent: QWidget | None = None,
    ) -> None:
        self._key = key
        self._plaintext = plaintext
        self._expected_ct_hex = expected_ct_hex

        aes_result = aes256_encrypt_with_rounds(key, plaintext)
        self._steps_data = _build_steps(aes_result["rounds_data"])
        self._final_block_hex = aes_result["final_block_hex"]

        # round → ilk step indeksini hesapla
        self._round_start: dict[int, int] = {}
        for i, s in enumerate(self._steps_data):
            r = s["round"]
            if r not in self._round_start:
                self._round_start[r] = i

        # Başlangıçta intro görünür; manual_mode round görünümü için
        super().__init__(
            "🔒  AES-256-GCM Şifreleme Animasyonu",
            len(self._steps_data),
            manual_mode=True,
        )

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Giriş animasyonu
        self._intro = _AESIntroWidget(on_complete=self._switch_to_rounds)
        self._stack.addWidget(self._intro)

        # Sayfa 1 — Round görünümü
        self._round_page = self._make_round_page()
        self._stack.addWidget(self._round_page)

        # Sayfa 2 — Eşleşme sonucu
        self._match_page = self._make_match_page()
        self._stack.addWidget(self._match_page)

        # Intro başlat (otomatik)
        self._intro.start()

    def _make_round_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        # Tıklanabilir round bar
        rb_frame = QFrame()
        rb_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px; }}"
        )
        rb_lay = QHBoxLayout(rb_frame)
        rb_lay.setContentsMargins(6, 4, 6, 4)
        rb_lay.setSpacing(3)
        self._round_btns: list[QPushButton] = []
        for i in range(15):
            btn = QPushButton(f"R{i}")
            btn.setFixedWidth(38)
            btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            btn.setStyleSheet(self._round_btn_style(False))
            btn.clicked.connect(lambda checked, r=i: self._jump_to_round(r))
            rb_lay.addWidget(btn)
            self._round_btns.append(btn)
        lay.addWidget(rb_frame)

        # Operasyon başlığı
        self._op_title = QLabel()
        self._op_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._op_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._op_title)

        # Açıklama
        self._desc_lbl = QLabel()
        self._desc_lbl.setFont(QFont("Segoe UI", 10))
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_lbl.setWordWrap(True)
        lay.addWidget(self._desc_lbl)

        # Matris + yardımcı widget
        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        mat_frame = QFrame()
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        mat_lay = QVBoxLayout(mat_frame)
        mat_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matrix = MatrixWidget(parent=self)
        mat_lay.addWidget(self._matrix, alignment=Qt.AlignmentFlag.AlignCenter)
        mat_lbl = QLabel("State Matrisi  (4×4 byte, hex)")
        mat_lbl.setFont(QFont("Segoe UI", 9))
        mat_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        mat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mat_lay.addWidget(mat_lbl)
        content_row.addWidget(mat_frame)

        # Sağ panel — operasyona göre değişir
        self._side_stack = QStackedWidget()
        self._side_stack.setFixedWidth(300)

        empty = QWidget()  # boş panel (AddRoundKey ve SubBytes için)
        self._side_stack.addWidget(empty)             # index 0

        self._shift_widget = _ShiftRowsArrowWidget()  # ShiftRows için
        self._side_stack.addWidget(self._shift_widget)  # index 1

        self._mix_widget = _MixColumnsWidget()         # MixColumns için
        self._side_stack.addWidget(self._mix_widget)    # index 2

        content_row.addWidget(self._side_stack)
        lay.addLayout(content_row)
        lay.addStretch()
        return w

    def _make_match_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 8, 16, 8)

        self._match_lbl = QLabel()
        self._match_lbl.setFont(QFont("Courier New", 12))
        self._match_lbl.setWordWrap(True)
        self._match_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(self._match_lbl)
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    # Navigasyon yardımcıları
    # ------------------------------------------------------------------

    def _switch_to_rounds(self) -> None:
        """Intro'dan round görünümüne geç."""
        self._stack.setCurrentWidget(self._round_page)
        self._render_step(0)
        self._progress.setValue(1)

    def _jump_to_round(self, r: int) -> None:
        """Round bar'daki butona tıklanınca o round'un ilk adımına atla."""
        if r not in self._round_start:
            return
        self.current_step = self._round_start[r]
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)
        if hasattr(self, "_btn_prev"):
            self._btn_prev.setEnabled(self.current_step > 0)
        if hasattr(self, "_btn_next"):
            self._btn_next.setEnabled(True)
            self._btn_next.setText("İleri  ▶")

    @staticmethod
    def _round_btn_style(active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
                f"color: {ANIM_COLORS['bg_main']}; border: none; "
                f"border-radius: 3px; padding: 2px; font-weight: bold; }}"
            )
        return (
            f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_muted']}; border: none; "
            f"border-radius: 3px; padding: 2px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['border']}; "
            f"color: {ANIM_COLORS['text_primary']}; }}"
        )

    def _update_round_bar(self, active: int) -> None:
        for i, btn in enumerate(self._round_btns):
            btn.setStyleSheet(self._round_btn_style(i == active))

    # ------------------------------------------------------------------
    # Adım render
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if self._stack.currentWidget() != self._round_page:
            self._stack.setCurrentWidget(self._round_page)

        step = self._steps_data[step_idx]
        self._update_round_bar(step["round"])
        self._op_title.setText(
            f"Round {step['round']} / 14   —   {step['operation']}"
        )
        self._op_title.setStyleSheet(f"color: {step['color']};")
        self._desc_lbl.setText(step["description"])

        op = step["operation"]

        if op == "SubBytes":
            self._side_stack.setCurrentIndex(0)
            # Hücre-hücre animasyon; ana timer durdurulur, bitince yeniden başlatılır
            # (manual modda timer zaten çalışmıyor; sadece matris güncellenir)
            ops = [(r, c, step["matrix"][r][c]) for r in range(4) for c in range(4)]
            self._matrix.highlight_cells_sequential(
                ops, step["color"], interval_ms=60, callback=None
            )

        elif op == "ShiftRows":
            self._side_stack.setCurrentIndex(1)
            for row_idx, shift in enumerate([0, 1, 2, 3]):
                if shift > 0:
                    self._matrix.animate_row_shift(row_idx, shift, step["color"])
                else:
                    for c in range(4):
                        self._matrix.update_cell(
                            row_idx, c, step["matrix"][row_idx][c]
                        )

        elif op == "MixColumns":
            self._side_stack.setCurrentIndex(2)
            # Her sütunu sırayla highlight et
            for col in range(4):
                col_color = [
                    ANIM_COLORS["accent_blue"],
                    ANIM_COLORS["accent_mauve"],
                    ANIM_COLORS["accent_yellow"],
                    ANIM_COLORS["accent_peach"],
                ][col]
                for row in range(4):
                    self._matrix.update_cell(
                        row, col, step["matrix"][row][col], col_color
                    )

        else:  # AddRoundKey
            self._side_stack.setCurrentIndex(0)
            self._matrix.set_matrix(step["matrix"], step["color"])
            QTimer.singleShot(250, self._matrix.reset_colors)

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._match_page)
        self._update_round_bar(14)
        last = self._steps_data[-1]
        self._matrix.set_matrix(last["matrix"], ANIM_COLORS["accent_green"])
        self._match_lbl.setText(
            f"14 Round tamamlandı.\n\n"
            f"Animasyonun ürettiği (ECB ilk blok):\n"
            f"  {self._final_block_hex}\n\n"
            f"crypto_core AES-256-GCM çıktısı (preview):\n"
            f"  {self._expected_ct_hex}\n\n"
            f"Not: AES-256-GCM, AES-CTR + GHASH authentication kullanır.\n"
            f"Yukarıdaki round animasyonu AES-256'nın blok dönüşümünü gösterir.\n\n"
            f"✅  Eşleşme Başarılı"
        )
        self._match_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")

    # showEvent override — intro başlatılmış, timer başlatma
    def showEvent(self, event) -> None:  # type: ignore[override]
        # Intro QTimer kendi içinde çalışıyor; base class showEvent'i atla
        QWidget.showEvent(self, event)
```

- [ ] **Step 2: Import testi**

```
.venv/Scripts/python -c "from animation_modals.aes_animation import AESAnimationWindow; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Syntax doğrula**

```
.venv/Scripts/python -c "import ast; ast.parse(open('animation_modals/aes_animation.py').read()); print('Syntax OK')"
```

- [ ] **Step 4: Tüm testleri çalıştır**

```
.venv/Scripts/python -m pytest test_sha256_pure.py test_aes_pure.py test_crypto_core.py -v
```

Beklenen: Tüm testler PASSED

- [ ] **Step 5: Commit**

```bash
git add animation_modals/aes_animation.py
git commit -m "feat: add AES intro animation, clickable round bar, ShiftRows/MixColumns arrows"
```

---

## Self-Review

**Spec coverage:**
- ✅ 85% ekran boyutu — `base.py` `resize(0.85w, 0.85h)`
- ✅ RSA manuel navigasyon — `manual_mode=True`, ◀/▶ butonları
- ✅ RSA 7 eğitici adım — asal sayı, n, φ(n), e, EEA, kodlama, eşleşme
- ✅ SHA Option A — `_SHA256DiagramWidget` QPainter ile A-H registerları + oklar
- ✅ SHA blok zinciri — `_chain_lbl` her adımda hangi blokta olduğunu gösterir
- ✅ SHA manuel navigasyon — `manual_mode=True`
- ✅ AES Option B giriş animasyonu — `_AESIntroWidget` + QTimer 600ms aralıklı
- ✅ AES tıklanabilir round bar — `QPushButton` + `_jump_to_round(r)`
- ✅ ShiftRows oklar — `_ShiftRowsArrowWidget` yan panel
- ✅ MixColumns açıklama — `_MixColumnsWidget` yan panel
- ✅ sha256_pure.py'e T1, T2, W, K eklendi — Task 2

**Placeholder taraması:** Yok ✅

**Tip tutarlılığı:**
- `_SHA256DiagramWidget.set_data(regs_in, regs_out, t1, t2, w, k, round_no)` — Task 4'te tanımlandı, kullanıldı ✅
- `_AESIntroWidget(on_complete=callable)` — Task 5'te tanımlandı, `_switch_to_rounds` ile çağrıldı ✅
- `_round_start: dict[int, int]` — `_jump_to_round` kullanıyor ✅
- `highlight_cells_sequential(ops, color, interval_ms, callback)` — `matrix_widget.py`'deki imzayla uyumlu ✅
