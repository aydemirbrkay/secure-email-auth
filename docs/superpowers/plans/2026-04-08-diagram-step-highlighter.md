# Diagram Step Highlighter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bob panelinin üstünde `alice and bob.png` diyagramını göster; Alice'in her adımında ilgili diyagram bloğu 1 sn aralıkla kırmızı yanıp sönsün, "Kapat" butonu ile kapansın.

**Architecture:** `DiagramWidget` (QWidget alt sınıfı) `bob_panel.py`'e eklenir; `QTimer` + `paintEvent` ile blink animasyonu sağlar. `BobPanel` bir container widget içinde diyagramı ve kapat butonunu barındırır. `main_gui.py`'de alice fazı adım döngüsüne 4 satır eklenir.

**Tech Stack:** PyQt6 (QWidget, QPainter, QTimer, QPixmap, QPen, QColor, QRect)

---

## File Map

| Dosya | Değişiklik |
|-------|-----------|
| `bob_panel.py` | `DiagramWidget` sınıfı (module-level) + `BobPanel` metodları/container |
| `main_gui.py` | `_on_next_step()` alice fazına ~10 satır |
| `alice and bob.png` | Sadece okunur |

---

## Task 1: Koordinat Haritası Testi

**Files:**
- Create: `test_diagram_rects.py`

- [ ] **Step 1: Koordinat sabit listesini test eden dosyayı yaz**

```python
# test_diagram_rects.py
"""DIAGRAM_RECTS listesinin geçerliliğini test eder — display gerektirmez."""

DIAGRAM_W = 623
DIAGRAM_H = 283

# Spec'ten koordinatlar — bob_panel.py ile senkron tutulmalı
DIAGRAM_RECTS_RAW = [
    (95, 78, 95, 38),    # 0: SHA-256
    (195, 78, 80, 38),   # 1: RSA İmza
    (268, 108, 44, 44),  # 2: Birleştir (+)
    (330, 90, 85, 38),   # 3: AES
    (330, 155, 85, 38),  # 4: RSA Anahtar
    (408, 118, 158, 62), # 5: Gönder / Internet
]


def test_rect_count():
    assert len(DIAGRAM_RECTS_RAW) == 6, "Alice'in 6 adımına karşılık 6 rect olmalı"


def test_rects_positive_dimensions():
    for i, (x, y, w, h) in enumerate(DIAGRAM_RECTS_RAW):
        assert w > 0 and h > 0, f"Rect {i}: genişlik ve yükseklik pozitif olmalı"


def test_rects_within_image_bounds():
    for i, (x, y, w, h) in enumerate(DIAGRAM_RECTS_RAW):
        assert x >= 0 and y >= 0, f"Rect {i}: koordinatlar negatif olamaz"
        assert x + w <= DIAGRAM_W, f"Rect {i}: sağ kenar ({x+w}) görsel genişliğini ({DIAGRAM_W}) aşıyor"
        assert y + h <= DIAGRAM_H, f"Rect {i}: alt kenar ({y+h}) görsel yüksekliğini ({DIAGRAM_H}) aşıyor"


def test_image_file_exists():
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alice and bob.png")
    assert os.path.isfile(path), f"Görsel dosyası bulunamadı: {path}"
```

- [ ] **Step 2: Testi çalıştır — geçmeli**

```
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ/bitirme_odevi"
.venv/Scripts/python -m pytest test_diagram_rects.py -v
```

Beklenen: 4 test PASS

- [ ] **Step 3: Commit**

```bash
git add test_diagram_rects.py
git commit -m "test: add diagram rect boundary tests"
```

---

## Task 2: DiagramWidget Sınıfı

**Files:**
- Modify: `bob_panel.py` (module başına import ekle + `DiagramWidget` sınıfı ekle)

- [ ] **Step 1: `bob_panel.py` import bloğunu güncelle**

[bob_panel.py](bob_panel.py) dosyasını aç. Mevcut import bloğu:

```python
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
```

Bunu şununla değiştir:

```python
import os

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
```

- [ ] **Step 2: `DiagramWidget` sınıfını `bob_panel.py`'e ekle**

`from crypto_core import ...` satırından hemen önce, dosyanın başına (import bloğundan sonra) şu sabitler ve sınıfı ekle:

```python
# ---------------------------------------------------------------------------
# Diyagram Koordinat Haritası (alice and bob.png, 623×283 üzerinde)
# ---------------------------------------------------------------------------

_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alice and bob.png")
_DIAGRAM_W = 623
_DIAGRAM_H = 283
_BLINK_MS = 1000

_STEP_RECTS: list[QRect] = [
    QRect(95, 78, 95, 38),    # 0: SHA-256 — m → H(·)
    QRect(195, 78, 80, 38),   # 1: RSA İmza — K_A^-(·)
    QRect(268, 108, 44, 44),  # 2: Birleştir — (+)
    QRect(330, 90, 85, 38),   # 3: AES — K_S(·)
    QRect(330, 155, 85, 38),  # 4: RSA Anahtar — K_B^+(·)
    QRect(408, 118, 158, 62), # 5: Gönder — (+) + Internet
]

_RED = QColor(229, 57, 53)          # #E53935 kenarlık
_RED_FILL = QColor(229, 57, 53, 64) # %25 şeffaf kırmızı dolgu
_GREEN_FILL = QColor(76, 175, 80, 51) # %20 şeffaf yeşil dolgu


class DiagramWidget(QWidget):
    """623×283 alice and bob.png görseli + adım vurgulama animasyonu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_DIAGRAM_W, _DIAGRAM_H)

        self._pixmap = QPixmap()
        if os.path.isfile(_IMAGE_PATH):
            self._pixmap = QPixmap(_IMAGE_PATH).scaled(
                _DIAGRAM_W, _DIAGRAM_H,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            print(f"[DiagramWidget] Uyarı: görsel bulunamadı → {_IMAGE_PATH}")

        self._active_step: int = -1
        self._completed_steps: set[int] = set()
        self._blink_on: bool = False

        self._timer = QTimer(self)
        self._timer.setInterval(_BLINK_MS)
        self._timer.timeout.connect(self._toggle_blink)

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------

    def set_active_step(self, idx: int) -> None:
        """İdx'i aktif (yanıp sönen) adım olarak ayarla ve timer'ı başlat."""
        self._active_step = idx
        self._blink_on = True
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def mark_step_done(self, idx: int) -> None:
        """İdx'i tamamlandı (yeşil) olarak işaretle."""
        self._completed_steps.add(idx)
        self.update()

    def stop_blink(self) -> None:
        """Timer'ı durdur, aktif adımı temizle."""
        self._timer.stop()
        self._active_step = -1
        self._blink_on = False
        self.update()

    def reset(self) -> None:
        """Tüm durumu başa döndür."""
        self._timer.stop()
        self._active_step = -1
        self._completed_steps.clear()
        self._blink_on = False
        self.update()

    # ------------------------------------------------------------------
    # İç Metodlar
    # ------------------------------------------------------------------

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)

        # 1) Görseli çiz (veya gri arka plan)
        if not self._pixmap.isNull():
            painter.drawPixmap(0, 0, self._pixmap)
        else:
            painter.fillRect(self.rect(), QColor(40, 40, 60))

        # 2) Tamamlanmış adımlar — yeşil dolgu, kenarlıksız
        painter.setPen(Qt.PenStyle.NoPen)
        for idx in self._completed_steps:
            if 0 <= idx < len(_STEP_RECTS):
                painter.fillRect(_STEP_RECTS[idx], _GREEN_FILL)

        # 3) Aktif adım — kırmızı kenarlık, blink_on ise kırmızı dolgu
        if 0 <= self._active_step < len(_STEP_RECTS):
            rect = _STEP_RECTS[self._active_step]
            if self._blink_on:
                painter.fillRect(rect, _RED_FILL)
            pen = QPen(_RED, 3)
            painter.setPen(pen)
            painter.drawRect(rect)

        painter.end()
```

- [ ] **Step 3: Sözdizimi kontrolü**

```
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ/bitirme_odevi"
.venv/Scripts/python -c "import bob_panel; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 4: Koordinat testini tekrar çalıştır**

```
.venv/Scripts/python -m pytest test_diagram_rects.py -v
```

Beklenen: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add bob_panel.py
git commit -m "feat: add DiagramWidget with blink animation"
```

---

## Task 3: BobPanel Container + Public API

**Files:**
- Modify: `bob_panel.py` (`BobPanel` sınıfı içi)

- [ ] **Step 1: `BobPanel.__init__` attribute listesine ekle**

[bob_panel.py:32-37](bob_panel.py#L32-L37) — `__init__` içinde `self._init_ui()` çağrısından önce:

```python
def __init__(self, parent: Optional[QWidget] = None) -> None:
    super().__init__(parent)
    self._steps: list[StepResult] = []
    self._current_step: int = 0
    self._step_widgets: list[QGroupBox] = []
    self._diagram_widget: DiagramWidget | None = None      # Task 3'te init edilir
    self._btn_close_diagram: QPushButton | None = None     # Task 3'te init edilir
    self._init_ui()
```

- [ ] **Step 2: `_init_ui` içine diyagram container'ı ekle**

[bob_panel.py:39-58](bob_panel.py#L39-L58) — `layout = QVBoxLayout(self)` bloğundan sonra, `self._received_group = ...` satırından **önce**:

```python
# --- Diyagram Container (Alice fazında görünür) ---
self._diagram_container = QWidget()
self._diagram_container.setVisible(False)
diag_layout = QVBoxLayout(self._diagram_container)
diag_layout.setContentsMargins(0, 0, 0, 4)
diag_layout.setSpacing(4)

self._diagram_widget = DiagramWidget()
diag_layout.addWidget(self._diagram_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

self._btn_close_diagram = QPushButton("✖  Kapat")
self._btn_close_diagram.setEnabled(False)
self._btn_close_diagram.setFixedHeight(32)
self._btn_close_diagram.setStyleSheet(
    "QPushButton { background: rgba(229,57,53,0.12); border: 2px solid #E53935; "
    "border-radius: 6px; color: #E53935; font-weight: bold; font-size: 12px; }"
    "QPushButton:hover { background: rgba(229,57,53,0.28); }"
    "QPushButton:disabled { background: #1e1e2e; border: 1px solid #45475a; color: #6c7086; }"
)
self._btn_close_diagram.clicked.connect(self._on_close_diagram)
diag_layout.addWidget(self._btn_close_diagram)

layout.addWidget(self._diagram_container)
# --- Diyagram Container sonu ---
```

- [ ] **Step 3: Public API metodlarını `BobPanel`'e ekle**

`reset(self)` metodundan hemen önce şu metodları ekle:

```python
# ------------------------------------------------------------------
# Diyagram API
# ------------------------------------------------------------------

def show_diagram(self) -> None:
    """Alice fazı başladığında diyagramı göster."""
    self._diagram_container.setVisible(True)

def set_diagram_step(self, step_idx: int) -> None:
    """Önceki adımı yeşil yap, step_idx'i kırmızı blink ile vurgula."""
    if step_idx > 0:
        self._diagram_widget.mark_step_done(step_idx - 1)
    self._diagram_widget.set_active_step(step_idx)

def enable_close_button(self) -> None:
    """Alice'in son adımı tamamlandıktan sonra Kapat butonunu aktif et."""
    self._btn_close_diagram.setEnabled(True)

def _on_close_diagram(self) -> None:
    """Kapat butonuna basıldığında diyagramı gizle."""
    self._diagram_widget.stop_blink()
    self._diagram_container.setVisible(False)
```

- [ ] **Step 4: `reset()` metodunu güncelle**

Mevcut `reset()` metoduna [bob_panel.py:92-103](bob_panel.py#L92-L103) şu satırları ekle (metodun **başına**, `self._steps = []` satırından önce):

```python
def reset(self) -> None:
    self._diagram_widget.reset()
    self._diagram_container.setVisible(False)
    self._btn_close_diagram.setEnabled(False)
    self._steps = []
    self._current_step = 0
    self._step_widgets.clear()
    while self._nested_container.count():
        item = self._nested_container.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    self._received_label.setText("⏳ Henüz bir paket alınmadı.")
    self._result_label.setText("")
    self._result_group.setVisible(False)
    self.status_label.setText("📬 Alice'den paket bekleniyor...")
```

- [ ] **Step 5: Sözdizimi kontrolü**

```
.venv/Scripts/python -c "import bob_panel; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 6: Commit**

```bash
git add bob_panel.py
git commit -m "feat: integrate DiagramWidget into BobPanel with public API"
```

---

## Task 4: main_gui.py Entegrasyonu

**Files:**
- Modify: `main_gui.py` (`_on_next_step` alice fazı bloğu)

- [ ] **Step 1: `_on_next_step` alice fazını güncelle**

[main_gui.py:497-528](main_gui.py#L497-L528) — mevcut `elif self._phase == "alice":` bloğunu aşağıdakiyle **değiştir**:

```python
elif self._phase == "alice":
    # Gösterilecek adımın indeksini ÖNCE oku (show_next_step() değiştirir)
    step_idx = self._alice_panel._current_step  # 0..5

    # İlk adımda Bob panelinde diyagramı aç
    if step_idx == 0:
        self._bob_panel.show_diagram()

    if step_idx < len(self._alice_panel._steps):
        next_step = self._alice_panel._steps[step_idx]
        if "SHA" in next_step.step_name:
            hash_hex = next_step.data.get("hash_hex", "")
            self._sha_data = (self._original_message, hash_hex)
            self._btn_anim_sha.setEnabled(True)
            self._update_toggle_label()
            sha_win = SHA256AnimationWindow(self._original_message, hash_hex)
            sha_win.show()
            self._anim_windows.append(sha_win)
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
            )
            aes_win.show()
            self._anim_windows.append(aes_win)

    self._alice_has_more = self._alice_panel.show_next_step()

    # Diyagramda aktif adımı vurgula
    self._bob_panel.set_diagram_step(step_idx)

    if not self._alice_has_more:
        # Son adım: Kapat butonunu aktif et, faz geç
        self._bob_panel.enable_close_button()
        self._phase = "transit"
        self._btn_next.setText("📨 Paketi Bob'a Gönder")
```

> **Not:** Mevcut `main_gui.py`'de `idx = self._alice_panel._current_step` vardı — bu blok onu tamamen `step_idx` ile değiştiriyor. Eski `idx` referansı kalmadığından emin ol.

- [ ] **Step 2: Sözdizimi kontrolü**

```
.venv/Scripts/python -c "import main_gui; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Uygulamayı başlat ve manuel test et**

```
.venv/Scripts/python main_gui.py
```

Test sırası:
1. "Anahtar Üret" → RSA animasyon penceresi açılır
2. Mesaj yaz → "Şifreleme Başlat"
3. "Sonraki Adım" (1. kez) → Bob panelinde diyagram açılır, SHA-256 bloğu kırmızı blinker (1 sn)
4. "Sonraki Adım" (2. kez) → SHA bloğu yeşil dolgu, RSA İmza bloğu kırmızı blinker
5. Adım 3-6 aynı şekilde devam eder
6. 6. adımdan sonra "Kapat" butonu aktif olur
7. "Kapat" tıkla → diyagram kapanır
8. "Paketi Bob'a Gönder" → Bob deşifreleme adımları normal çalışır
9. "Sıfırla" → Bob panelinde diyagram gizli, her şey temiz

- [ ] **Step 4: Commit**

```bash
git add main_gui.py
git commit -m "feat: drive DiagramWidget from main_gui alice phase"
```

---

## Task 5: Koordinat Kalibrasyonu

**Files:**
- Modify: `bob_panel.py` (`_STEP_RECTS` listesi)

- [ ] **Step 1: Uygulamayı görsel referansla karşılaştır**

Uygulamayı çalıştır, adım adım ilerle. Her adımda kırmızı çerçevenin diyagramdaki doğru bloğu çevirip çevirmediğini kontrol et:

| Adım | Beklenen blok |
|------|--------------|
| 0 | m → H(·) kutusu |
| 1 | K_A^-(·) kutusu |
| 2 | Sol (+) dairesi |
| 3 | K_S(·) kutusu |
| 4 | K_B^+(·) kutusu |
| 5 | Sağ (+) dairesi + Internet bulutu |

- [ ] **Step 2: Gerekirse `_STEP_RECTS` koordinatlarını güncelle**

[bob_panel.py](bob_panel.py) dosyasındaki `_STEP_RECTS` listesinde yanlış hizalanan adımların `QRect(x, y, w, h)` değerlerini gerçek görsel pozisyonuna göre düzelt.

- [ ] **Step 3: Testi çalıştır (sınır kontrolü)**

```
.venv/Scripts/python -m pytest test_diagram_rects.py -v
```

> **Not:** `test_diagram_rects.py` içindeki `DIAGRAM_RECTS_RAW` listesini de `_STEP_RECTS` ile senkron tut.

- [ ] **Step 4: Son commit**

```bash
git add bob_panel.py test_diagram_rects.py
git commit -m "fix: calibrate diagram step highlight coordinates"
```

---

## Özet

| Task | Dosya | Amaç |
|------|-------|-------|
| 1 | `test_diagram_rects.py` | Koordinat sınır testleri |
| 2 | `bob_panel.py` | `DiagramWidget` sınıfı |
| 3 | `bob_panel.py` | `BobPanel` container + API |
| 4 | `main_gui.py` | Alice fazı entegrasyonu |
| 5 | `bob_panel.py` | Koordinat kalibrasyonu |
