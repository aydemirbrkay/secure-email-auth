# main_gui.py Split Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `main_gui.py` (1220 satır) içindeki 4 farklı sorumluluğu ayrı dosyalara taşımak; mantık, isimlendirme veya davranış değiştirilmez.

**Architecture:** Stil sabitleri `theme.py`'a, yardımcı fonksiyonlar `utils.py`'a, her widget sınıfı kendi dosyasına taşınır. `main_gui.py` yalnızca `MainWindow` ve `main()` içerir. Import zinciri döngüsüzdür: `theme → utils → panel dosyaları → main_gui`.

**Tech Stack:** Python 3.x, PyQt6

---

## Dosya Haritası

| Dosya | İşlem | İçerik |
|---|---|---|
| `theme.py` | Oluştur | `COLORS`, `GLOBAL_STYLESHEET`, `STEP_COLORS_ALICE`, `STEP_COLORS_BOB` |
| `utils.py` | Oluştur | `FRIENDLY_NAMES`, `_make_step_box`, `_truncate_hex`, `_build_step_content` |
| `alice_panel.py` | Oluştur | `AlicePanel` sınıfı |
| `bob_panel.py` | Oluştur | `BobPanel` sınıfı |
| `toast.py` | Oluştur | `VerificationToast` sınıfı |
| `main_gui.py` | Güncelle | Sadece `MainWindow` + `main()` kalır, importlar güncellenir |

---

## Task 1: theme.py oluştur

**Files:**
- Create: `theme.py`

- [ ] **Step 1: Dosyayı oluştur**

```python
"""
theme.py – Renk Paleti ve Stil Sabitleri
"""
from __future__ import annotations

COLORS = {
    "bg_main": "#1e1e2e",
    "bg_panel": "#282840",
    "bg_card": "#313150",
    "bg_input": "#3b3b5c",
    "text_primary": "#cdd6f4",
    "text_secondary": "#a6adc8",
    "text_muted": "#6c7086",
    "accent_blue": "#89b4fa",
    "accent_green": "#a6e3a1",
    "accent_red": "#f38ba8",
    "accent_yellow": "#f9e2af",
    "accent_mauve": "#cba6f7",
    "accent_teal": "#94e2d5",
    "accent_peach": "#fab387",
    "border": "#45475a",
    "border_highlight": "#89b4fa",
}

GLOBAL_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["bg_main"]};
}}
QWidget {{
    color: {COLORS["text_primary"]};
    font-family: "Segoe UI", "Noto Sans", "Ubuntu", sans-serif;
}}
QLabel {{
    color: {COLORS["text_primary"]};
}}
QLineEdit, QTextEdit {{
    background-color: {COLORS["bg_input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 8px;
    color: {COLORS["text_primary"]};
    font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {COLORS["border_highlight"]};
}}
QPushButton {{
    background-color: {COLORS["accent_blue"]};
    color: {COLORS["bg_main"]};
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: bold;
    font-size: 14px;
}}
QPushButton:hover {{
    background-color: {COLORS["accent_mauve"]};
}}
QPushButton:disabled {{
    background-color: {COLORS["text_muted"]};
    color: {COLORS["bg_panel"]};
}}
QGroupBox {{
    border: 2px solid {COLORS["border"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 10px 10px 10px;
    font-weight: bold;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {COLORS["accent_blue"]};
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QSplitter::handle {{
    background-color: {COLORS["border"]};
    width: 2px;
}}
"""

# Adım renkleri — Alice: içten dışa (sade → karmaşık)
STEP_COLORS_ALICE = [
    COLORS["accent_blue"],
    COLORS["accent_mauve"],
    COLORS["accent_yellow"],
    COLORS["accent_green"],
    COLORS["accent_peach"],
    COLORS["accent_teal"],
]

# Adım renkleri — Bob: dıştan içe (karmaşık → sade)
STEP_COLORS_BOB = [
    COLORS["accent_peach"],
    COLORS["accent_green"],
    COLORS["accent_yellow"],
    COLORS["accent_blue"],
    COLORS["accent_mauve"],
]
```

- [ ] **Step 2: Import edilebilir olduğunu doğrula**

```bash
python -c "from theme import COLORS, GLOBAL_STYLESHEET, STEP_COLORS_ALICE, STEP_COLORS_BOB; print('OK')"
```

Beklenen çıktı: `OK`

- [ ] **Step 3: Commit**

```bash
git add theme.py
git commit -m "refactor: extract theme constants to theme.py"
```

---

## Task 2: utils.py oluştur

**Files:**
- Create: `utils.py`
- Depends on: `theme.py` (Task 1), `crypto_core.py` (değişmez)

- [ ] **Step 1: Dosyayı oluştur**

```python
"""
utils.py – Yardımcı Fonksiyonlar ve Sabitler
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from crypto_core import StepResult
from theme import COLORS

FRIENDLY_NAMES: dict[str, str] = {
    "nonce_hex":              "Rastgele Sayı (Nonce)",
    "session_key_hex":        "Oturum Anahtarı (K_S)",
    "hash_hex":               "SHA-256 Özet Değeri H(m)",
    "signature_hex":          "Dijital İmza",
    "encrypted_key_hex":      "RSA Şifreli Oturum Anahtarı",
    "ciphertext_hex_preview": "Şifreli Mesaj (Önizleme)",
    "verification_result":    "Doğrulama Sonucu",
    "key_info":               "Kullanılan Anahtar",
    "combined_size":          "Birleşik Veri Boyutu",
    "message_size":           "Mesaj Boyutu",
    "signature_size":         "İmza Boyutu",
    "ciphertext_size":        "Şifreli Veri Boyutu",
    "encrypted_key_size":     "RSA Şifreli Anahtar Boyutu",
    "total_packet_size":      "Toplam Paket Boyutu",
    "message":                "Mesaj İçeriği",
    "elapsed_ms":             "İşlem Süresi",
}


def _make_step_box(title: str, content: str, border_color: str) -> QGroupBox:
    """Kümülatif görselleştirme için renkli çerçeveli kutucuk oluşturur."""
    box = QGroupBox(title)
    box.setStyleSheet(
        f"QGroupBox {{ border: 2px solid {border_color}; border-radius: 8px; "
        f"margin-top: 14px; padding: 14px 8px 8px 8px; }}"
        f"QGroupBox::title {{ color: {border_color}; font-weight: bold; }}"
    )
    layout = QVBoxLayout(box)
    layout.setContentsMargins(8, 18, 8, 8)

    lbl = QLabel(content)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(lbl)

    return box


def _truncate_hex(hex_str: str, max_len: int = 48) -> str:
    """Uzun hex değerlerini görüntüleme için kısaltır."""
    if len(hex_str) > max_len:
        return hex_str[:max_len] + "…"
    return hex_str


def _build_step_content(step: StepResult) -> str:
    """Adım verilerini kullanıcı dostu Türkçe etiketlerle formatlar."""
    lines = [step.description, ""]
    for key, value in step.data.items():
        if key.endswith("_bytes"):
            continue
        display_key = FRIENDLY_NAMES.get(key, key)
        if key == "verification_result":
            display_val = "✅ DOĞRULANDI" if value else "❌ DOĞRULANAMADI"
        elif isinstance(value, str) and len(value) > 64:
            display_val = _truncate_hex(value)
        else:
            display_val = value
        lines.append(f"  • {display_key}: {display_val}")
    return "\n".join(lines)
```

- [ ] **Step 2: Import edilebilir olduğunu doğrula**

```bash
python -c "from utils import FRIENDLY_NAMES, _make_step_box, _truncate_hex, _build_step_content; print('OK')"
```

Beklenen çıktı: `OK`

- [ ] **Step 3: Commit**

```bash
git add utils.py
git commit -m "refactor: extract helper functions to utils.py"
```

---

## Task 3: alice_panel.py oluştur

**Files:**
- Create: `alice_panel.py`
- Depends on: `theme.py` (Task 1), `utils.py` (Task 2)

- [ ] **Step 1: Dosyayı oluştur**

```python
"""
alice_panel.py – Gönderici (Alice) Panel Widget
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from crypto_core import StepResult
from theme import COLORS, STEP_COLORS_ALICE
from utils import _build_step_content, _make_step_box


class AlicePanel(QWidget):
    """Gönderici (Alice) paneli — sol taraf.

    Kutucuk mantığı — içten dışa şifreleme:
      • Adım 1 (SHA-256) en içte gösterilir — sade, orijinal mesaj + özet.
      • Her yeni adım önceki kutucuğu sarar; dışa çıkıldıkça karmaşıklaşır.
      • Adım 6 (Paket Gönderimi) en dışta — tam şifreli yapı.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._steps: list[StepResult] = []
        self._current_step: int = 0
        self._step_widgets: list[QGroupBox] = []
        self._outermost_box: Optional[QGroupBox] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("👩\u200d💻 Gönderici — Alice")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        msg_group = QGroupBox("E-posta Mesajı")
        msg_layout = QVBoxLayout(msg_group)
        self.msg_input = QTextEdit()
        self.msg_input.setPlaceholderText("Mesajınızı buraya yazın...")
        self.msg_input.setMaximumHeight(100)
        msg_layout.addWidget(self.msg_input)
        layout.addWidget(msg_group)

        self._cumulative_area = QWidget()
        self._cumulative_layout = QVBoxLayout(self._cumulative_area)
        self._cumulative_layout.setContentsMargins(0, 0, 0, 0)
        self._cumulative_layout.setSpacing(6)

        self._nested_container = QVBoxLayout()
        self._cumulative_layout.addLayout(self._nested_container)
        self._cumulative_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._cumulative_area)
        scroll.setStyleSheet("background-color: transparent;")
        layout.addWidget(scroll, stretch=1)

        self.status_label = QLabel("🔐 Mesajınızı yazın ve şifreleme sürecini başlatın.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; padding: 4px;"
        )
        layout.addWidget(self.status_label)

    def reset(self) -> None:
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

    def set_steps(self, steps: list[StepResult]) -> None:
        self.reset()
        self._steps = steps

    def show_next_step(self) -> bool:
        """Sonraki adımı dışa-sararak kümülatif gösterir.

        Her yeni adım, önceki tüm kutucukları içine alır (wrap-outward):
        Adım 1 en içte (en sade) → Adım 6 en dışta (en karmaşık).
        """
        if self._current_step >= len(self._steps):
            return False

        step = self._steps[self._current_step]
        color = STEP_COLORS_ALICE[self._current_step % len(STEP_COLORS_ALICE)]
        content = _build_step_content(step)
        box = _make_step_box(
            f"Adım {step.step_number}: {step.step_name}",
            content,
            color,
        )
        self._step_widgets.append(box)

        if self._outermost_box is None:
            self._outermost_box = box
            self._nested_container.addWidget(box)
        else:
            self._nested_container.removeWidget(self._outermost_box)
            box.layout().addWidget(self._outermost_box)
            self._outermost_box = box
            self._nested_container.addWidget(box)

        self._current_step += 1
        self.status_label.setText(
            f"✅ Adım {step.step_number}/{len(self._steps)} tamamlandı: {step.step_name}"
        )
        return self._current_step < len(self._steps)
```

- [ ] **Step 2: Import edilebilir olduğunu doğrula**

```bash
python -c "from alice_panel import AlicePanel; print('OK')"
```

Beklenen çıktı: `OK`

- [ ] **Step 3: Commit**

```bash
git add alice_panel.py
git commit -m "refactor: extract AlicePanel to alice_panel.py"
```

---

## Task 4: bob_panel.py oluştur

**Files:**
- Create: `bob_panel.py`
- Depends on: `theme.py` (Task 1), `utils.py` (Task 2)

- [ ] **Step 1: Dosyayı oluştur**

```python
"""
bob_panel.py – Alıcı (Bob) Panel Widget
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from crypto_core import EncryptedPacket, StepResult
from theme import COLORS, STEP_COLORS_BOB
from utils import _build_step_content, _make_step_box


class BobPanel(QWidget):
    """Alıcı (Bob) paneli — sağ taraf.

    Kutucuk mantığı — dıştan içe deşifreleme:
      • Adım 1 (RSA Anahtar Çözme) en dışta — şifreli paket, en karmaşık.
      • Her yeni adım bir öncekinin içine eklenir; içe girdikçe sadeleşir.
      • Adım 5 (İmza Doğrulama) en içte — doğrulanmış orijinal mesaj.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._steps: list[StepResult] = []
        self._current_step: int = 0
        self._step_widgets: list[QGroupBox] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("👨\u200d💻 Alıcı — Bob")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_green']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._received_group = QGroupBox("Alınan Şifreli Paket")
        recv_layout = QVBoxLayout(self._received_group)
        self._received_label = QLabel("⏳ Henüz bir paket alınmadı.")
        self._received_label.setWordWrap(True)
        self._received_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px;"
        )
        recv_layout.addWidget(self._received_label)
        layout.addWidget(self._received_group)

        self._cumulative_area = QWidget()
        self._cumulative_layout = QVBoxLayout(self._cumulative_area)
        self._cumulative_layout.setContentsMargins(0, 0, 0, 0)
        self._cumulative_layout.setSpacing(6)

        self._nested_container = QVBoxLayout()
        self._cumulative_layout.addLayout(self._nested_container)
        self._cumulative_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._cumulative_area)
        scroll.setStyleSheet("background-color: transparent;")
        layout.addWidget(scroll, stretch=1)

        self._result_group = QGroupBox("Doğrulama Sonucu")
        result_layout = QVBoxLayout(self._result_group)
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        result_layout.addWidget(self._result_label)
        self._result_group.setVisible(False)
        layout.addWidget(self._result_group)

        self.status_label = QLabel("📬 Alice'den paket bekleniyor...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; padding: 4px;"
        )
        layout.addWidget(self.status_label)

    def reset(self) -> None:
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

    def set_packet_info(self, packet: EncryptedPacket) -> None:
        info = (
            f"📦 Şifreli mesaj boyutu: {len(packet.encrypted_message)} byte\n"
            f"🔑 Şifreli oturum anahtarı: {len(packet.encrypted_session_key)} byte\n"
            f"🎲 Rastgele Sayı (Nonce): {packet.nonce.hex()[:32]}…"
        )
        self._received_label.setText(info)
        self._received_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;"
        )

    def set_steps(self, steps: list[StepResult]) -> None:
        self._steps = steps
        self._current_step = 0
        self._step_widgets.clear()
        while self._nested_container.count():
            item = self._nested_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_next_step(self) -> bool:
        """Sonraki adımı içe-sararak kümülatif gösterir.

        Her yeni adım bir öncekinin içine eklenir (içe-sarma):
        Adım 1 en dışta (en karmaşık) → Adım 5 en içte (doğrulanmış mesaj).
        """
        if self._current_step >= len(self._steps):
            return False

        step = self._steps[self._current_step]
        color = STEP_COLORS_BOB[self._current_step % len(STEP_COLORS_BOB)]
        content = _build_step_content(step)
        box = _make_step_box(
            f"Adım {step.step_number}: {step.step_name}",
            content,
            color,
        )
        self._step_widgets.append(box)

        if self._current_step == 0:
            self._nested_container.addWidget(box)
        else:
            prev_box = self._step_widgets[self._current_step - 1]
            prev_box.layout().addWidget(box)

        self._current_step += 1
        self.status_label.setText(
            f"✅ Adım {step.step_number}/{len(self._steps)} tamamlandı: {step.step_name}"
        )
        return self._current_step < len(self._steps)
```

- [ ] **Step 2: Import edilebilir olduğunu doğrula**

```bash
python -c "from bob_panel import BobPanel; print('OK')"
```

Beklenen çıktı: `OK`

- [ ] **Step 3: Commit**

```bash
git add bob_panel.py
git commit -m "refactor: extract BobPanel to bob_panel.py"
```

---

## Task 5: toast.py oluştur

**Files:**
- Create: `toast.py`
- Depends on: `theme.py` (Task 1)

- [ ] **Step 1: Dosyayı oluştur**

```python
"""
toast.py – Doğrulama Bildirimi Widget
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from theme import COLORS


class VerificationToast(QWidget):
    """
    Doğrulama sonucunu gösteren açılır bildirim penceresi.
    8 saniye sonra otomatik kapanır; 'Kapat' butonu ile erken kapatılabilir.
    """

    _LIFE_SECS = 8

    def __init__(self, is_valid: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._secs = self._LIFE_SECS

        color = COLORS["accent_green"] if is_valid else COLORS["accent_red"]
        icon  = "✅" if is_valid else "❌"
        title = "DOĞRULAMA BAŞARILI" if is_valid else "DOĞRULAMA BAŞARISIZ"

        self.setStyleSheet(
            f"QWidget {{ background: {COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 12px; }}"
        )
        self.setFixedWidth(440)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI", 36))
        icon_lbl.setStyleSheet("border: none;")
        icon_lbl.setFixedWidth(52)
        hdr.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {color}; border: none;")
        title_lbl.setWordWrap(True)
        hdr.addWidget(title_lbl, stretch=1)
        lay.addLayout(hdr)

        sep = QLabel()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background-color: {color}; border: none;")
        lay.addWidget(sep)

        if is_valid:
            items = [
                (COLORS["accent_green"], "✓  Kimlik Doğrulama  (Authentication)"),
                (COLORS["accent_green"], "✓  Mesaj Bütünlüğü   (Integrity)"),
                (COLORS["accent_green"], "✓  Gizlilik           (Confidentiality)"),
            ]
        else:
            items = [
                (COLORS["accent_red"],
                 "✗  İmza doğrulanamadı\n"
                 "    Mesaj değiştirilmiş veya gönderici kimliği sahte olabilir!"),
            ]
        for c, text in items:
            lbl = QLabel(text)
            lbl.setFont(QFont("Segoe UI", 12))
            lbl.setStyleSheet(f"color: {c}; border: none;")
            lbl.setWordWrap(True)
            lay.addWidget(lbl)

        lay.addSpacing(4)

        self._close_btn = QPushButton(f"✕  Kapat  ({self._secs}s)")
        self._close_btn.setStyleSheet(
            f"QPushButton {{ background: {color}22; border: 2px solid {color}; "
            f"border-radius: 6px; color: {color}; font-weight: bold; "
            f"font-size: 12px; padding: 8px 24px; }}"
            f"QPushButton:hover {{ background: {color}55; }}"
        )
        self._close_btn.clicked.connect(self.close)
        lay.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.adjustSize()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self) -> None:
        self._secs -= 1
        if self._secs <= 0:
            self.close()
        else:
            self._close_btn.setText(f"✕  Kapat  ({self._secs}s)")

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        par = self.parent()
        if par:
            pg = par.geometry()
            sg = self.frameGeometry()
            self.move(
                pg.x() + (pg.width()  - sg.width())  // 2,
                pg.y() + (pg.height() - sg.height()) // 2,
            )
```

- [ ] **Step 2: Import edilebilir olduğunu doğrula**

```bash
python -c "from toast import VerificationToast; print('OK')"
```

Beklenen çıktı: `OK`

- [ ] **Step 3: Commit**

```bash
git add toast.py
git commit -m "refactor: extract VerificationToast to toast.py"
```

---

## Task 6: main_gui.py güncelle

**Files:**
- Modify: `main_gui.py`

- [ ] **Step 1: main_gui.py içeriğini yeni haliyle değiştir**

Dosyanın tamamını aşağıdaki içerikle değiştir (satır 1'den itibaren):

```python
"""
main_gui.py – Ana Pencere
=========================
Secure Email Authentication and Message Integrity projesi için
PyQt6 tabanlı iki panelli, adım adım kümülatif görselleştirme arayüzü.

Erciyes Üniversitesi – Bilgisayar Mühendisliği Bitirme Projesi
Berkay Aydemir – 1030521387
Danışman: Prof. Dr. Serkan ÖZTÜRK
"""

from __future__ import annotations

import hashlib
import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from crypto_core import CryptoCore, EncryptedPacket
from animation_modals import RSAAnimationWindow, SHA256AnimationWindow, AESAnimationWindow
from theme import COLORS, GLOBAL_STYLESHEET
from alice_panel import AlicePanel
from bob_panel import BobPanel
from toast import VerificationToast


# ---------------------------------------------------------------------------
# Ana Pencere
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Secure Email Authentication — Ana Pencere."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(
            "Secure Email Authentication and Message Integrity"
        )
        self.setMinimumSize(1200, 750)

        self._crypto = CryptoCore()
        self._packet: Optional[EncryptedPacket] = None
        self._anim_windows: list = []
        self._rsa_data: tuple | None = None
        self._sha_data: tuple | None = None
        self._aes_data: tuple | None = None
        self._phase: str = "idle"
        self._alice_has_more: bool = False
        self._bob_has_more: bool = False
        self._original_message: str = ""
        self._decoded_message: str = ""
        self._is_valid: bool = False

        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        header = QLabel("🔐 Secure Email Authentication and Message Integrity")
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"color: {COLORS['accent_blue']}; padding: 8px;")
        main_layout.addWidget(header)

        subtitle = QLabel(
            "Gizlilik (Confidentiality)  •  Bütünlük (Integrity)  •  Kimlik Doğrulama (Authentication)"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        main_layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        alice_frame = QFrame()
        alice_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_panel']}; border-radius: 12px; }}"
        )
        alice_inner = QVBoxLayout(alice_frame)
        alice_inner.setContentsMargins(0, 0, 0, 0)
        self._alice_panel = AlicePanel()
        alice_inner.addWidget(self._alice_panel)
        splitter.addWidget(alice_frame)

        bob_frame = QFrame()
        bob_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_panel']}; border-radius: 12px; }}"
        )
        bob_inner = QVBoxLayout(bob_frame)
        bob_inner.setContentsMargins(0, 0, 0, 0)
        self._bob_panel = BobPanel()
        bob_inner.addWidget(self._bob_panel)
        splitter.addWidget(bob_frame)

        splitter.setSizes([600, 600])
        main_layout.addWidget(splitter, stretch=1)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._btn_keygen = QPushButton("🔑 Anahtar Üret")
        self._btn_keygen.setToolTip("Alice ve Bob için RSA-2048 anahtar çiftleri üret")
        self._btn_keygen.clicked.connect(self._on_keygen)
        controls.addWidget(self._btn_keygen)

        self._btn_start = QPushButton("▶️ Şifreleme Başlat")
        self._btn_start.setToolTip("Alice'in mesajı şifreleme sürecini başlat")
        self._btn_start.setEnabled(False)
        self._btn_start.clicked.connect(self._on_start)
        controls.addWidget(self._btn_start)

        self._btn_next = QPushButton("⏭️ Sonraki Adım")
        self._btn_next.setToolTip("Bir sonraki kriptografik adımı göster")
        self._btn_next.setEnabled(False)
        self._btn_next.clicked.connect(self._on_next_step)
        controls.addWidget(self._btn_next)

        self._btn_reset = QPushButton("🔄 Sıfırla")
        self._btn_reset.setToolTip("Tüm adımları sıfırla ve baştan başla")
        self._btn_reset.clicked.connect(self._on_reset)
        controls.addWidget(self._btn_reset)

        main_layout.addLayout(controls)

        self._key_info_group = QGroupBox("🔑 RSA-2048 Anahtar Bilgileri")
        self._key_info_group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {COLORS['accent_green']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 10px 10px 8px 10px; }}"
            f"QGroupBox::title {{ color: {COLORS['accent_green']}; "
            f"font-size: 13px; font-weight: bold; subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        self._key_info_group.setVisible(False)
        key_info_layout = QVBoxLayout(self._key_info_group)
        key_info_layout.setSpacing(6)

        key_header = QLabel("✅  Anahtarlar Başarıyla Üretildi")
        key_header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        key_header.setStyleSheet(f"color: {COLORS['accent_green']};")
        key_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        key_info_layout.addWidget(key_header)

        alice_row = QHBoxLayout()
        alice_key_lbl = QLabel("👩\u200d💻  Alice Açık Anahtarı (K⁺_A):")
        alice_key_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        alice_key_lbl.setStyleSheet(f"color: {COLORS['accent_blue']};")
        alice_key_lbl.setMinimumWidth(240)
        alice_row.addWidget(alice_key_lbl)
        self._alice_key_value = QLabel("")
        self._alice_key_value.setWordWrap(True)
        self._alice_key_value.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; font-family: monospace;"
        )
        self._alice_key_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        alice_row.addWidget(self._alice_key_value, stretch=1)
        key_info_layout.addLayout(alice_row)

        bob_row = QHBoxLayout()
        bob_key_lbl = QLabel("👨\u200d💻  Bob Açık Anahtarı (K⁺_B):")
        bob_key_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        bob_key_lbl.setStyleSheet(f"color: {COLORS['accent_green']};")
        bob_key_lbl.setMinimumWidth(240)
        bob_row.addWidget(bob_key_lbl)
        self._bob_key_value = QLabel("")
        self._bob_key_value.setWordWrap(True)
        self._bob_key_value.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; font-family: monospace;"
        )
        self._bob_key_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        bob_row.addWidget(self._bob_key_value, stretch=1)
        key_info_layout.addLayout(bob_row)

        self._comparison_group = QGroupBox(
            "📊 Orijinal Mesaj ↔ Alınan Mesaj Karşılaştırması"
        )
        self._comparison_group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {COLORS['accent_teal']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 10px 10px 8px 10px; }}"
            f"QGroupBox::title {{ color: {COLORS['accent_teal']}; "
            f"font-size: 13px; font-weight: bold; subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        self._comparison_group.setVisible(False)
        cmp_outer = QVBoxLayout(self._comparison_group)
        cmp_outer.setSpacing(6)

        _card = f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 8px; }}"

        msg_row = QHBoxLayout()
        msg_row.setSpacing(10)

        alice_msg_f = QFrame(); alice_msg_f.setStyleSheet(_card)
        alice_msg_lay = QVBoxLayout(alice_msg_f)
        alice_msg_lay.setContentsMargins(10, 8, 10, 8)
        _lbl = QLabel("👩\u200d💻 Alice'in Gönderdiği")
        _lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        _lbl.setStyleSheet(f"color: {COLORS['accent_blue']};")
        alice_msg_lay.addWidget(_lbl)
        self._alice_msg_cmp = QLabel("")
        self._alice_msg_cmp.setWordWrap(True)
        self._alice_msg_cmp.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self._alice_msg_cmp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        alice_msg_lay.addWidget(self._alice_msg_cmp)
        msg_row.addWidget(alice_msg_f, stretch=3)

        msg_mid_f = QFrame(); msg_mid_f.setStyleSheet(_card)
        msg_mid_lay = QVBoxLayout(msg_mid_f)
        msg_mid_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_mid_lay.setContentsMargins(4, 6, 4, 6)
        msg_mid_lay.setSpacing(2)
        self._cmp_msg_icon = QLabel("")
        self._cmp_msg_icon.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self._cmp_msg_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_mid_lay.addWidget(self._cmp_msg_icon)
        self._cmp_msg_label = QLabel("Mesaj")
        self._cmp_msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cmp_msg_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: bold;")
        msg_mid_lay.addWidget(self._cmp_msg_label)
        msg_row.addWidget(msg_mid_f, stretch=1)

        bob_msg_f = QFrame(); bob_msg_f.setStyleSheet(_card)
        bob_msg_lay = QVBoxLayout(bob_msg_f)
        bob_msg_lay.setContentsMargins(10, 8, 10, 8)
        _lbl2 = QLabel("👨\u200d💻 Bob'un Aldığı")
        _lbl2.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        _lbl2.setStyleSheet(f"color: {COLORS['accent_green']};")
        bob_msg_lay.addWidget(_lbl2)
        self._bob_msg_cmp = QLabel("")
        self._bob_msg_cmp.setWordWrap(True)
        self._bob_msg_cmp.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self._bob_msg_cmp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bob_msg_lay.addWidget(self._bob_msg_cmp)
        msg_row.addWidget(bob_msg_f, stretch=3)

        cmp_outer.addLayout(msg_row)

        hash_row = QHBoxLayout()
        hash_row.setSpacing(10)

        alice_hash_f = QFrame(); alice_hash_f.setStyleSheet(_card)
        alice_hash_lay = QVBoxLayout(alice_hash_f)
        alice_hash_lay.setContentsMargins(10, 8, 10, 8)
        self._alice_hash_cmp = QLabel("")
        self._alice_hash_cmp.setWordWrap(True)
        self._alice_hash_cmp.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-family: 'Courier New', monospace;"
        )
        self._alice_hash_cmp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        alice_hash_lay.addWidget(self._alice_hash_cmp)
        hash_row.addWidget(alice_hash_f, stretch=3)

        hash_mid_f = QFrame(); hash_mid_f.setStyleSheet(_card)
        hash_mid_lay = QVBoxLayout(hash_mid_f)
        hash_mid_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hash_mid_lay.setContentsMargins(4, 6, 4, 6)
        hash_mid_lay.setSpacing(2)
        self._cmp_hash_icon = QLabel("")
        self._cmp_hash_icon.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self._cmp_hash_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hash_mid_lay.addWidget(self._cmp_hash_icon)
        self._cmp_hash_label = QLabel("Hash")
        self._cmp_hash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cmp_hash_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: bold;")
        hash_mid_lay.addWidget(self._cmp_hash_label)
        hash_row.addWidget(hash_mid_f, stretch=1)

        bob_hash_f = QFrame(); bob_hash_f.setStyleSheet(_card)
        bob_hash_lay = QVBoxLayout(bob_hash_f)
        bob_hash_lay.setContentsMargins(10, 8, 10, 8)
        self._bob_hash_cmp = QLabel("")
        self._bob_hash_cmp.setWordWrap(True)
        self._bob_hash_cmp.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-family: 'Courier New', monospace;"
        )
        self._bob_hash_cmp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bob_hash_lay.addWidget(self._bob_hash_cmp)
        hash_row.addWidget(bob_hash_f, stretch=3)

        hash_content = QWidget()
        hash_content.setLayout(hash_row)
        hash_scroll = QScrollArea()
        hash_scroll.setWidgetResizable(True)
        hash_scroll.setMaximumHeight(80)
        hash_scroll.setStyleSheet("background: transparent; border: none;")
        hash_scroll.setWidget(hash_content)
        cmp_outer.addWidget(hash_scroll)

        self._bottom_section = QWidget()
        self._bottom_section.setVisible(False)
        bs_lay = QVBoxLayout(self._bottom_section)
        bs_lay.setContentsMargins(0, 0, 0, 0)
        bs_lay.setSpacing(4)

        self._bottom_toggle_btn = QPushButton()
        self._bottom_toggle_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; "
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"font-weight: bold; padding: 8px 16px; text-align: left; }}"
            f"QPushButton:hover {{ background: {COLORS['bg_input']}; "
            f"border-color: {COLORS['accent_blue']}; }}"
        )
        self._bottom_toggle_btn.clicked.connect(self._toggle_bottom)
        bs_lay.addWidget(self._bottom_toggle_btn)

        self._bottom_body = QWidget()
        body_row = QHBoxLayout(self._bottom_body)
        body_row.setSpacing(10)
        body_row.setContentsMargins(0, 4, 0, 0)

        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.addWidget(self._key_info_group)
        left_col.addWidget(self._comparison_group)
        left_w = QWidget()
        left_w.setLayout(left_col)
        body_row.addWidget(left_w, stretch=3)

        self._algo_panel = self._make_algo_panel()
        body_row.addWidget(self._algo_panel, stretch=1)

        self._bottom_body.setVisible(False)
        bs_lay.addWidget(self._bottom_body)

        main_layout.addWidget(self._bottom_section)

    # ------------------------------------------------------------------
    # Algoritma Paneli
    # ------------------------------------------------------------------

    def _make_algo_panel(self) -> QGroupBox:
        """Algoritmaları tekrar izleme paneli (sağ alt)."""
        box = QGroupBox("🔍  Algoritmaları İzle")
        box.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {COLORS['accent_blue']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 12px 10px 10px 10px; }}"
            f"QGroupBox::title {{ color: {COLORS['accent_blue']}; "
            f"font-size: 13px; font-weight: bold; "
            f"subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        lay = QVBoxLayout(box)
        lay.setSpacing(8)

        info_lbl = QLabel(
            "Simülasyon sırasında çalışan\nher algoritmayı adım adım\ntekrar gözlemleyebilirsiniz."
        )
        info_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_lbl.setWordWrap(True)
        lay.addWidget(info_lbl)

        lay.addSpacing(4)

        self._btn_anim_rsa = QPushButton("🔑  RSA-2048\nAnahtar Şifreleme")
        self._btn_anim_rsa.setStyleSheet(self._algo_btn_style(COLORS["accent_mauve"]))
        self._btn_anim_rsa.setEnabled(False)
        self._btn_anim_rsa.clicked.connect(self._reopen_rsa)
        lay.addWidget(self._btn_anim_rsa)

        self._btn_anim_sha = QPushButton("🔷  SHA-256\nHash Hesaplama")
        self._btn_anim_sha.setStyleSheet(self._algo_btn_style(COLORS["accent_blue"]))
        self._btn_anim_sha.setEnabled(False)
        self._btn_anim_sha.clicked.connect(self._reopen_sha)
        lay.addWidget(self._btn_anim_sha)

        self._btn_anim_aes = QPushButton("🔒  AES-256-GCM\nSimetrik Şifreleme")
        self._btn_anim_aes.setStyleSheet(self._algo_btn_style(COLORS["accent_yellow"]))
        self._btn_anim_aes.setEnabled(False)
        self._btn_anim_aes.clicked.connect(self._reopen_aes)
        lay.addWidget(self._btn_anim_aes)

        lay.addStretch()
        return box

    @staticmethod
    def _algo_btn_style(color: str) -> str:
        h = color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (
            f"QPushButton {{ background: rgba({r},{g},{b},0.12); "
            f"border: 2px solid {color}; border-radius: 8px; color: {color}; "
            f"font-weight: bold; font-size: 11px; padding: 7px 6px; }}"
            f"QPushButton:hover {{ background: rgba({r},{g},{b},0.28); }}"
            f"QPushButton:disabled {{ background: #1e1e2e; border: 1px solid #45475a; "
            f"color: #6c7086; font-size: 11px; padding: 7px 6px; }}"
        )

    def _reopen_rsa(self) -> None:
        if self._rsa_data is None:
            return
        alice_b64, bob_b64 = self._rsa_data
        win = RSAAnimationWindow(alice_b64, bob_b64)
        win.show()
        self._anim_windows.append(win)

    def _reopen_sha(self) -> None:
        if self._sha_data is None:
            return
        message, hash_hex = self._sha_data
        win = SHA256AnimationWindow(message, hash_hex)
        win.show()
        self._anim_windows.append(win)

    def _reopen_aes(self) -> None:
        if self._aes_data is None:
            return
        key_bytes, plaintext, ct_hex = self._aes_data
        win = AESAnimationWindow(key=key_bytes, plaintext=plaintext, expected_ct_hex=ct_hex)
        win.show()
        self._anim_windows.append(win)

    def _toggle_bottom(self) -> None:
        self._bottom_body.setVisible(not self._bottom_body.isVisible())
        self._update_toggle_label()

    def _update_toggle_label(self) -> None:
        rsa = "🔑 RSA-2048 ✓" if self._rsa_data else "🔑 RSA-2048"
        sha = "🔷 SHA-256 ✓" if self._sha_data else "🔷 SHA-256"
        aes = "🔒 AES-256-GCM ✓" if self._aes_data else "🔒 AES-256-GCM"
        arrow = "▲  Kapat" if self._bottom_body.isVisible() else "▼  Genişlet"
        self._bottom_toggle_btn.setText(
            f"  {rsa}   •   {sha}   •   {aes}                    {arrow}"
        )

    # ------------------------------------------------------------------
    # Olay İşleyicileri (Event Handlers)
    # ------------------------------------------------------------------

    def _on_keygen(self) -> None:
        alice_keys, bob_keys = self._crypto.setup_keys()

        alice_lines = alice_keys.public_pem().decode().strip().split("\n")
        bob_lines = bob_keys.public_pem().decode().strip().split("\n")
        alice_b64 = "".join(alice_lines[1:-1])[:60] + "…"
        bob_b64 = "".join(bob_lines[1:-1])[:60] + "…"

        self._alice_key_value.setText(alice_b64)
        self._bob_key_value.setText(bob_b64)
        self._key_info_group.setVisible(True)

        self._rsa_data = (alice_b64, bob_b64)
        self._btn_anim_rsa.setEnabled(True)

        self._bottom_section.setVisible(True)
        self._update_toggle_label()

        self._btn_start.setEnabled(True)
        self._btn_keygen.setEnabled(False)
        self._phase = "ready"
        rsa_win = RSAAnimationWindow(alice_b64, bob_b64)
        rsa_win.show()
        self._anim_windows.append(rsa_win)

    def _on_start(self) -> None:
        message = self._alice_panel.msg_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir e-posta mesajı yazın!")
            return

        try:
            self._packet, alice_steps = self._crypto.alice_send(message)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return

        self._original_message = message
        self._alice_panel.set_steps(alice_steps)
        self._phase = "alice"
        self._alice_has_more = True
        self._btn_start.setEnabled(False)
        self._btn_next.setEnabled(True)
        self._alice_panel.msg_input.setReadOnly(True)

    def _on_next_step(self) -> None:
        if self._phase == "alice":
            idx = self._alice_panel._current_step
            if idx < len(self._alice_panel._steps):
                next_step = self._alice_panel._steps[idx]
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
            if not self._alice_has_more:
                self._phase = "transit"
                self._btn_next.setText("📨 Paketi Bob'a Gönder")

        elif self._phase == "transit":
            if self._packet is not None:
                self._bob_panel.set_packet_info(self._packet)
                try:
                    message, is_valid, bob_steps = self._crypto.bob_receive(self._packet)
                except Exception as exc:
                    QMessageBox.critical(self, "Deşifreleme Hatası", str(exc))
                    return
                self._decoded_message = message
                self._is_valid = is_valid
                self._bob_panel.set_steps(bob_steps)
                self._bob_has_more = True
                self._phase = "bob"
                self._btn_next.setText("⏭️ Sonraki Adım")

        elif self._phase == "bob":
            self._bob_has_more = self._bob_panel.show_next_step()
            if not self._bob_has_more:
                self._phase = "done"
                self._btn_next.setEnabled(False)
                self._btn_next.setText("✅ Tamamlandı")
                self._show_comparison(self._original_message, self._decoded_message)
                toast = VerificationToast(self._is_valid, parent=self)
                toast.show()

    def _show_comparison(self, orig: str, received: str) -> None:
        orig_hash = hashlib.sha256(orig.encode("utf-8")).hexdigest()
        recv_hash = hashlib.sha256(received.encode("utf-8")).hexdigest()

        messages_match = orig == received
        hashes_match = orig_hash == recv_hash

        msg_preview = orig if len(orig) <= 80 else orig[:80] + "…"
        self._alice_msg_cmp.setText(f"📝  {msg_preview}")
        self._alice_hash_cmp.setText(f"🔷  {orig_hash}")

        recv_preview = received if len(received) <= 80 else received[:80] + "…"
        self._bob_msg_cmp.setText(f"📝  {recv_preview}")
        self._bob_hash_cmp.setText(f"🔷  {recv_hash}")

        if messages_match:
            self._cmp_msg_icon.setText("✅")
            self._cmp_msg_icon.setStyleSheet(f"color: {COLORS['accent_green']};")
            self._cmp_msg_label.setText("Mesaj\nEşleşti")
            self._cmp_msg_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 11px; font-weight: bold;"
            )
        else:
            self._cmp_msg_icon.setText("❌")
            self._cmp_msg_icon.setStyleSheet(f"color: {COLORS['accent_red']};")
            self._cmp_msg_label.setText("Mesaj\nEşleşmedi!")
            self._cmp_msg_label.setStyleSheet(
                f"color: {COLORS['accent_red']}; font-size: 11px; font-weight: bold;"
            )

        if hashes_match:
            self._cmp_hash_icon.setText("✅")
            self._cmp_hash_icon.setStyleSheet(f"color: {COLORS['accent_green']};")
            self._cmp_hash_label.setText("Hash\nEşleşti")
            self._cmp_hash_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 11px; font-weight: bold;"
            )
        else:
            self._cmp_hash_icon.setText("❌")
            self._cmp_hash_icon.setStyleSheet(f"color: {COLORS['accent_red']};")
            self._cmp_hash_label.setText("Hash\nEşleşmedi!")
            self._cmp_hash_label.setStyleSheet(
                f"color: {COLORS['accent_red']}; font-size: 11px; font-weight: bold;"
            )

        self._comparison_group.setVisible(True)

    def _on_reset(self) -> None:
        self._alice_panel.reset()
        self._bob_panel.reset()
        self._alice_panel.msg_input.setReadOnly(False)
        self._alice_panel.msg_input.clear()
        self._packet = None
        self._phase = "idle"
        self._alice_has_more = False
        self._bob_has_more = False
        self._original_message = ""
        self._decoded_message = ""
        self._is_valid = False
        self._btn_keygen.setEnabled(True)
        self._btn_start.setEnabled(False)
        self._btn_next.setEnabled(False)
        self._btn_next.setText("⏭️ Sonraki Adım")
        self._key_info_group.setVisible(False)
        self._comparison_group.setVisible(False)
        self._rsa_data = None
        self._sha_data = None
        self._aes_data = None
        self._btn_anim_rsa.setEnabled(False)
        self._btn_anim_sha.setEnabled(False)
        self._btn_anim_aes.setEnabled(False)
        self._bottom_body.setVisible(False)
        self._bottom_section.setVisible(False)


# ---------------------------------------------------------------------------
# Uygulama Giriş Noktası
# ---------------------------------------------------------------------------

def main() -> None:
    """Uygulamayı tam ekran olarak başlatır."""
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)
    app.setStyle("Fusion")

    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Mevcut testleri çalıştır**

```bash
python -m pytest test_crypto_core.py test_sha256_pure.py -v
```

Beklenen: tüm testler PASS

- [ ] **Step 3: Import zincirini doğrula**

```bash
python -c "from main_gui import MainWindow; print('OK')"
```

Beklenen çıktı: `OK`

- [ ] **Step 4: Satır sayısını doğrula**

```bash
python -c "
with open('main_gui.py') as f:
    lines = f.readlines()
print(f'main_gui.py: {len(lines)} satır')
for name in ['theme.py','utils.py','alice_panel.py','bob_panel.py','toast.py']:
    with open(name) as f:
        n = len(f.readlines())
    print(f'{name}: {n} satır')
"
```

Beklenen: `main_gui.py` < 300 satır

- [ ] **Step 5: Commit**

```bash
git add main_gui.py
git commit -m "refactor: slim down main_gui.py — import from theme, utils, panels, toast"
```

---

## Task 7: Son doğrulama

**Files:** Değişiklik yok — sadece doğrulama

- [ ] **Step 1: Tüm testleri çalıştır**

```bash
python -m pytest test_crypto_core.py test_sha256_pure.py test_aes_pure.py -v
```

Beklenen: tüm testler PASS

- [ ] **Step 2: Döngüsel import kontrolü**

```bash
python -c "
import importlib
for mod in ['theme','utils','alice_panel','bob_panel','toast','main_gui']:
    importlib.import_module(mod)
    print(f'{mod}: OK')
"
```

Beklenen: her satırda `OK`

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "refactor: complete main_gui.py split into theme, utils, panel files"
```
