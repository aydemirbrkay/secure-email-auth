# Embedded Animation in Alice Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RSA, SHA-256 ve AES animasyon pencerelerini bağımsız üst-düzey pencere yerine Alice paneli alanında (ekranın sol yarısı) gömülü widget olarak göster — tıpkı Bob panelindeki DiagramWidget gibi.

**Architecture:** `CryptoAnimationWindow`'a opsiyonel `on_close` callback parametresi eklenir; bu parametre verildiğinde widget bağımsız pencere olarak açılmaz. `AlicePanel`'e `_anim_container` + `show_animation()` / `hide_animation()` API'si eklenir (BobPanel'deki `_diagram_container` örüntüsü). `main_gui.py` tüm animasyon açma çağrılarını bu yeni API'ye yönlendirir. AES taşma sorunu `QScrollArea` sarmalayıcısı sayesinde çözülür.

**Tech Stack:** Python 3.11+, PyQt6, pytest

---

## Dosya Haritası

| Dosya | Değişim |
|---|---|
| `animation_modals/base.py` | `on_close` parametresi eklenir; embedded/standalone dal |
| `alice_panel.py` | `_anim_container`, `show_animation()`, `hide_animation()` eklenir |
| `main_gui.py` | `_anim_windows` kaldırılır; tüm animasyon çağrıları yeni API'ye geçer |

---

## Task 1: `animation_modals/base.py` — Embedded Mod Desteği

**Files:**
- Modify: `animation_modals/base.py`

### Değişiklikler

`__init__` imzasına `on_close` eklenir. Bu parametre `None` olmadığında widget bağımsız pencere yerine gömülü widget gibi davranır.

- [ ] **Step 1: `__init__` imzasını ve başını güncelle**

`animation_modals/base.py`'de `__init__` metodunu bul (satır 71–103) ve şu şekilde değiştir:

```python
def __init__(
    self,
    title: str,
    total_steps: int,
    manual_mode: bool = False,
    parent: QWidget | None = None,
    on_close: "callable | None" = None,
) -> None:
    super().__init__(parent)
    self._on_close = on_close

    # Standalone modda bağımsız pencere olarak aç
    if on_close is None:
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    self.setWindowTitle(title)
    self.setStyleSheet(
        f"background-color: {ANIM_COLORS['bg_main']}; "
        f"color: {ANIM_COLORS['text_primary']};"
    )

    # Ekranın %85'i kadar boyutlandır — sadece standalone modda
    if on_close is None:
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.resize(int(g.width() * 0.82), int(g.height() * 0.85))
        else:
            self.resize(1280, 860)

    self.manual_mode: bool = manual_mode
    self.current_step: int = 0
    self.total_steps: int = total_steps
    self.speed_ms: int = 1500

    self._timer = QTimer(self)
    self._timer.timeout.connect(self._advance_step)

    self._init_base_ui()
    self._init_content()
```

- [ ] **Step 2: "Kapat" butonunu `_init_base_ui`'de `_on_close`'a bağla**

`_init_base_ui` metodunda "Kapat" butonunu oluşturan satırları bul (şu an `btn_close.clicked.connect(self.close)` diyor) ve değiştir:

```python
btn_close = QPushButton("✕  Kapat")
btn_close.setStyleSheet(_CLOSE_STYLE)
if self._on_close is not None:
    btn_close.clicked.connect(self._on_close)
else:
    btn_close.clicked.connect(self.close)
controls.addWidget(btn_close)
```

- [ ] **Step 3: Manuel olarak doğrula**

Uygulamayı çalıştır (`python main_gui.py`). "Anahtar Üret" butonuna bas → RSA animasyonu eski davranışla (bağımsız pencere) açılıyorsa `on_close=None` dalı doğru çalışıyor demektir.

- [ ] **Step 4: Commit**

```bash
git add animation_modals/base.py
git commit -m "feat: add on_close param to CryptoAnimationWindow for embedded mode"
```

---

## Task 2: `alice_panel.py` — Animasyon Container API

**Files:**
- Modify: `alice_panel.py`

BobPanel'deki `_diagram_container` örüntüsünü Alice tarafına taşır. Normal içerik (başlık, mesaj kutusu, adım scroll alanı, durum etiketi) gizlenip yerlerine animasyon widget'ı gösterilir.

- [ ] **Step 1: Import ekle**

`alice_panel.py` başındaki import bloğuna `QScrollArea`'nın zaten var olduğunu doğrula (var). Ayrıca `Qt`'nin de import edildiğini doğrula (var). Ek import gerekmez.

- [ ] **Step 2: `_init_ui` içinde normal widget referanslarını instance değişkene al**

`_init_ui` metodunu aşağıdaki şekilde güncelle. `title` ve `msg_group` artık `self._title` ve `self._msg_group` olarak saklanacak. `scroll` da `self._scroll` olacak. `_anim_container` en sona eklenir:

```python
def _init_ui(self) -> None:
    layout = QVBoxLayout(self)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    self._title = QLabel("👩\u200d💻 Gönderici — Alice")
    self._title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    self._title.setStyleSheet(f"color: {COLORS['accent_blue']};")
    self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self._title)

    self._msg_group = QGroupBox("E-posta Mesajı")
    msg_layout = QVBoxLayout(self._msg_group)
    self.msg_input = QTextEdit()
    self.msg_input.setPlaceholderText("Mesajınızı buraya yazın...")
    self.msg_input.setMaximumHeight(100)
    msg_layout.addWidget(self.msg_input)
    layout.addWidget(self._msg_group)

    self._cumulative_area = QWidget()
    self._cumulative_layout = QVBoxLayout(self._cumulative_area)
    self._cumulative_layout.setContentsMargins(0, 0, 0, 0)
    self._cumulative_layout.setSpacing(6)

    self._nested_container = QVBoxLayout()
    self._cumulative_layout.addLayout(self._nested_container)
    self._cumulative_layout.addStretch()

    self._scroll = QScrollArea()
    self._scroll.setWidgetResizable(True)
    self._scroll.setWidget(self._cumulative_area)
    self._scroll.setStyleSheet("background-color: transparent;")
    layout.addWidget(self._scroll, stretch=1)

    self.status_label = QLabel("🔐 Mesajınızı yazın ve şifreleme sürecini başlatın.")
    self.status_label.setWordWrap(True)
    self.status_label.setStyleSheet(
        f"color: {COLORS['text_muted']}; font-size: 12px; padding: 4px;"
    )
    layout.addWidget(self.status_label)

    # ── Animasyon container (başta gizli) ─────────────────────────────
    self._anim_container = QWidget()
    anim_layout = QVBoxLayout(self._anim_container)
    anim_layout.setContentsMargins(0, 0, 0, 0)
    self._anim_scroll = QScrollArea()
    self._anim_scroll.setWidgetResizable(True)
    self._anim_scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    self._anim_scroll.setStyleSheet("background: transparent; border: none;")
    anim_layout.addWidget(self._anim_scroll)
    self._anim_container.setVisible(False)
    layout.addWidget(self._anim_container, stretch=1)
    # ─────────────────────────────────────────────────────────────────

    self._normal_widgets: list[QWidget] = [
        self._title, self._msg_group, self._scroll, self.status_label
    ]
```

- [ ] **Step 3: `show_animation` ve `hide_animation` metodlarını ekle**

`reset` metodundan hemen önce şu iki metodu ekle:

```python
def show_animation(self, widget: QWidget) -> None:
    """Normal içeriği gizle, animasyon widget'ını QScrollArea içinde göster."""
    # Önceki animasyon varsa temizle
    old = self._anim_scroll.takeWidget()
    if old is not None:
        old.deleteLater()
    # Yeni widget'ı ekle ve container'ı göster
    self._anim_scroll.setWidget(widget)
    for w in self._normal_widgets:
        w.setVisible(False)
    self._anim_container.setVisible(True)

def hide_animation(self) -> None:
    """Animasyonu temizle ve normal içeriği geri getir."""
    old = self._anim_scroll.takeWidget()
    if old is not None:
        old.deleteLater()
    self._anim_container.setVisible(False)
    for w in self._normal_widgets:
        w.setVisible(True)
```

- [ ] **Step 4: `reset` metodunu güncelle**

`reset` içine `hide_animation()` çağrısı ekle (en başa):

```python
def reset(self) -> None:
    self.hide_animation()
    self._steps = []
    self._current_step = 0
    self._step_widgets.clear()
    self._outermost_box = None
    while self._nested_container.count():
        item = self._nested_container.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    self.status_label.setText(
        "🔐 Mesajınızı yazın ve şifreleme sürecini başlatın."
    )
```

- [ ] **Step 5: Manuel doğrula**

Uygulamayı çalıştır. Uygulama açılıyor mu, Alice paneli normal görünüyor mu? Evet → devam.

- [ ] **Step 6: Commit**

```bash
git add alice_panel.py
git commit -m "feat: add animation container to AlicePanel with show/hide API"
```

---

## Task 3: `main_gui.py` — Animasyonları Alice Paneline Yönlendir

**Files:**
- Modify: `main_gui.py`

`_anim_windows` listesi kaldırılır. Tüm animasyon oluşturma satırları `on_close=self._alice_panel.hide_animation` ile güncellenir ve `win.show()` yerine `self._alice_panel.show_animation(win)` çağrılır.

- [ ] **Step 1: `__init__`'te `_anim_windows` satırını kaldır**

`MainWindow.__init__` içinde şu satırı sil:
```python
self._anim_windows: list = []
```

- [ ] **Step 2: `_on_keygen` metodunu güncelle**

`_on_keygen` içindeki RSA animasyon bloğunu güncelle (en altta, `self._bob_panel.show_keygen_step()` öncesindeki satırlar):

```python
rsa_win = RSAAnimationWindow(
    alice_b64, bob_b64,
    on_close=self._alice_panel.hide_animation,
)
self._alice_panel.show_animation(rsa_win)
```

Eski `rsa_win.show()` ve `self._anim_windows.append(rsa_win)` satırlarını sil.

- [ ] **Step 3: `_on_next_step` içindeki SHA animasyon bloğunu güncelle**

`_on_next_step` içinde `"SHA" in next_step.step_name:` dalını güncelle:

```python
if "SHA" in next_step.step_name:
    hash_hex = next_step.data.get("hash_hex", "")
    self._sha_data = (self._original_message, hash_hex)
    self._btn_anim_sha.setEnabled(True)
    self._update_toggle_label()
    sha_win = SHA256AnimationWindow(
        self._original_message, hash_hex,
        on_close=self._alice_panel.hide_animation,
    )
    self._alice_panel.show_animation(sha_win)
```

Eski `sha_win.show()` ve `self._anim_windows.append(sha_win)` satırlarını sil.

- [ ] **Step 4: `_on_next_step` içindeki AES animasyon bloğunu güncelle**

`"AES" in next_step.step_name:` dalını güncelle:

```python
elif "AES" in next_step.step_name:
    key_hex = next_step.data.get("session_key_hex", "")
    ct_preview = next_step.data.get("ciphertext_hex_preview", "")
    key_bytes = bytes.fromhex(key_hex) if key_hex else b"\x00" * 32
    plaintext = self._original_message.encode("utf-8")
    self._aes_data = (key_bytes, plaintext, ct_preview)
    self._btn_anim_aes.setEnabled(True)
    self._update_toggle_label()
    aes_win = AESAnimationWindow(
        key=key_bytes,
        plaintext=plaintext,
        expected_ct_hex=ct_preview,
        on_close=self._alice_panel.hide_animation,
    )
    self._alice_panel.show_animation(aes_win)
```

Eski `aes_win.show()` ve `self._anim_windows.append(aes_win)` satırlarını sil.

- [ ] **Step 5: `_reopen_rsa` metodunu güncelle**

```python
def _reopen_rsa(self) -> None:
    if self._rsa_data is None:
        return
    alice_b64, bob_b64 = self._rsa_data
    win = RSAAnimationWindow(
        alice_b64, bob_b64,
        on_close=self._alice_panel.hide_animation,
    )
    self._alice_panel.show_animation(win)
```

- [ ] **Step 6: `_reopen_sha` metodunu güncelle**

```python
def _reopen_sha(self) -> None:
    if self._sha_data is None:
        return
    message, hash_hex = self._sha_data
    win = SHA256AnimationWindow(
        message, hash_hex,
        on_close=self._alice_panel.hide_animation,
    )
    self._alice_panel.show_animation(win)
```

- [ ] **Step 7: `_reopen_aes` metodunu güncelle**

```python
def _reopen_aes(self) -> None:
    if self._aes_data is None:
        return
    key_bytes, plaintext, ct_hex = self._aes_data
    win = AESAnimationWindow(
        key=key_bytes,
        plaintext=plaintext,
        expected_ct_hex=ct_hex,
        on_close=self._alice_panel.hide_animation,
    )
    self._alice_panel.show_animation(win)
```

- [ ] **Step 8: `_on_reset` içinden `_anim_windows.clear()` satırını kaldır**

`_on_reset` içinden şu satırı sil:
```python
self._anim_windows.clear()
```

`alice_panel.reset()` zaten `hide_animation()` çağırdığı için ek bir şey gerekmez.

- [ ] **Step 9: Tam senaryo testi**

Uygulamayı çalıştır (`python main_gui.py`) ve şunu doğrula:

1. **Anahtar Üret** → RSA animasyonu Alice panelinin tamamını kaplar (bağımsız pencere açılmaz)
2. Animasyondaki **✕ Kapat** → Alice paneli eski haline döner
3. **Şifreleme Başlat** + **Sonraki Adım** (SHA adımı) → SHA animasyonu Alice panelinde açılır
4. Kapat → **Sonraki Adım** (AES adımı) → AES animasyonu Alice panelinde açılır; dar alanda scroll çalışır
5. **Sıfırla** → animasyon kapalıysa da Alice paneli normal görünür
6. Alt paneldeki "Algoritmaları İzle" butonları → animasyon Alice panelinde yeniden açılır

- [ ] **Step 10: Commit**

```bash
git add main_gui.py
git commit -m "feat: route all animations to alice panel instead of standalone windows"
```

---

## Spec Kapsamı Kontrolü

| Spec Gereksinimi | Task |
|---|---|
| Animasyonlar Alice panelinde gömülü görünür | Task 2 + Task 3 |
| Bob paneli DiagramWidget örüntüsü | Task 2 |
| Normal içerik gizlenir, animasyon açılır | Task 2 `show_animation` |
| Kapat → normal içerik geri döner | Task 1 `on_close` + Task 2 `hide_animation` |
| Sıfırlamada animasyon zorla kapatılır | Task 2 `reset` |
| Yeni animasyon eskisini değiştirir | Task 2 `show_animation` (takeWidget) |
| "Algoritmaları İzle" butonları da Alice paneline yönlenir | Task 3 Step 5-7 |
| AES taşma düzeltilir | Task 2 (QScrollArea + HorizontalScrollBarAsNeeded) |
| Standalone mod (on_close=None) bozulmaz | Task 1 |
