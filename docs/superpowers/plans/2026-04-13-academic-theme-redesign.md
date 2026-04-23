# Academic Theme Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the entire UI from Catppuccin Mocha dark theme to a warm ivory academic light theme with serif headings, sans-serif body text, and reduced emoji usage.

**Architecture:** All color definitions live in two central dictionaries (`COLORS` in theme.py, `ANIM_COLORS` in base.py). Most files reference these dictionaries, so updating them propagates widely. A handful of hardcoded hex values in sha256_animation.py and matrix_widget.py need direct replacement. Font changes require touching every `QFont("Segoe UI", ...)` call in heading positions. Emoji removal is string-level find-and-replace in specific locations.

**Tech Stack:** Python 3, PyQt6, no new dependencies

**Spec:** `docs/superpowers/specs/2026-04-13-academic-theme-redesign-design.md`

---

## File Map

| File | Role | Change Type |
|------|------|-------------|
| `theme.py` | Central color palette + global stylesheet | Full rewrite of COLORS, GLOBAL_STYLESHEET, STEP_COLORS |
| `animation_modals/base.py` | Animation color palette + button styles | Full rewrite of ANIM_COLORS, _BTN_STYLE, _CLOSE_STYLE |
| `animation_modals/matrix_widget.py` | AES/SHA matrix grid | Replace 3 hardcoded color values |
| `main_gui.py` | Main window | Fonts, emoji removal, hardcoded styles |
| `alice_panel.py` | Sender panel | Fonts, emoji removal |
| `bob_panel.py` | Receiver panel + diagram overlay | Fonts, emoji removal, overlay colors |
| `utils.py` | Step box builder | Font size update |
| `toast.py` | Verification toast | Fonts, emoji removal |
| `animation_modals/rsa_animation.py` | RSA animation | Title emoji, fonts |
| `animation_modals/sha256_animation.py` | SHA-256 animation | Register colors, hardcoded fills, fonts |
| `animation_modals/aes_animation.py` | AES animation | Op colors, fonts |

---

### Task 1: Update Core Color Palette (theme.py)

**Files:**
- Modify: `theme.py:1-105`

- [ ] **Step 1: Replace COLORS dictionary**

Replace the entire `COLORS` dict (lines 6-23) with:

```python
COLORS = {
    "bg_main":        "#FAFAF5",
    "bg_panel":       "#FFFFFF",
    "bg_card":        "#F0F1ED",
    "bg_input":       "#E8E9E4",
    "text_primary":   "#1F2937",
    "text_secondary": "#4B5563",
    "text_muted":     "#9CA3AF",
    "accent_blue":    "#3B6FA0",
    "accent_green":   "#4E8B60",
    "accent_red":     "#B94A4A",
    "accent_yellow":  "#B8860B",
    "accent_mauve":   "#7B5EA7",
    "accent_teal":    "#3D8B80",
    "accent_peach":   "#B87333",
    "border":         "#D1D5DB",
    "border_highlight": "#3B6FA0",
}
```

- [ ] **Step 2: Replace GLOBAL_STYLESHEET**

Replace `GLOBAL_STYLESHEET` (lines 25-85) with:

```python
GLOBAL_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["bg_main"]};
}}
QWidget {{
    color: {COLORS["text_primary"]};
    font-family: "IBM Plex Sans", "Inter", "Segoe UI", sans-serif;
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
    color: #FFFFFF;
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
    font-family: "Georgia", "Palatino Linotype", serif;
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
```

Note: Button text color changed from `bg_main` (dark) to `#FFFFFF` (white) because bg_main is now light ivory.

- [ ] **Step 3: Verify STEP_COLORS arrays use correct keys**

STEP_COLORS_ALICE and STEP_COLORS_BOB already reference COLORS dict keys. No code change needed — the new hex values propagate automatically. Verify the arrays still reference valid keys (they do: accent_blue, accent_mauve, accent_yellow, accent_green, accent_peach, accent_teal).

- [ ] **Step 4: Commit**

```bash
git add theme.py
git commit -m "feat: update theme.py to warm ivory academic palette"
```

---

### Task 2: Update Animation Color Palette (base.py)

**Files:**
- Modify: `animation_modals/base.py:24-57`

- [ ] **Step 1: Replace ANIM_COLORS dictionary**

Replace lines 26-38 with:

```python
ANIM_COLORS = {
    "bg_main":        "#FAFAF5",
    "bg_card":        "#F0F1ED",
    "bg_input":       "#E8E9E4",
    "text_primary":   "#1F2937",
    "text_secondary": "#4B5563",
    "text_muted":     "#9CA3AF",
    "accent_blue":    "#3B6FA0",
    "accent_green":   "#4E8B60",
    "accent_yellow":  "#B8860B",
    "accent_mauve":   "#7B5EA7",
    "accent_peach":   "#B87333",
    "border":         "#D1D5DB",
}
```

- [ ] **Step 2: Update _BTN_STYLE button text color**

Replace line 44 `color: {ANIM_COLORS['bg_main']}` with `color: #FFFFFF` — button text must be white on colored backgrounds now that bg_main is light:

```python
_BTN_STYLE = (
    f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
    f"color: #FFFFFF; border: none; "
    f"border-radius: 5px; padding: 5px 14px; font-weight: bold; font-size: 11px; }}"
    f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
    f"QPushButton:disabled {{ background: {ANIM_COLORS['bg_card']}; "
    f"color: {ANIM_COLORS['text_muted']}; }}"
)
```

- [ ] **Step 3: Update _CLOSE_STYLE hover text color**

Replace line 56 `color: {ANIM_COLORS['bg_main']}` with `color: #FFFFFF`:

```python
_CLOSE_STYLE = (
    f"QPushButton {{ background: {ANIM_COLORS['bg_card']}; "
    f"color: {ANIM_COLORS['text_secondary']}; border: 1px solid {ANIM_COLORS['border']}; "
    f"border-radius: 5px; padding: 5px 12px; font-size: 11px; }}"
    f"QPushButton:hover {{ background: {ANIM_COLORS['accent_peach']}; "
    f"color: #FFFFFF; }}"
)
```

- [ ] **Step 4: Update header font to Georgia in _init_base_ui**

Change line 125:

```python
        header.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
```

- [ ] **Step 5: Commit**

```bash
git add animation_modals/base.py
git commit -m "feat: update ANIM_COLORS to academic light theme"
```

---

### Task 3: Update Matrix Widget Colors (matrix_widget.py)

**Files:**
- Modify: `animation_modals/matrix_widget.py:11-12,102`

- [ ] **Step 1: Replace default color constants**

Change lines 11-12:

```python
_DEFAULT_BG = "#F0F1ED"
_DEFAULT_FG = "#1F2937"
```

- [ ] **Step 2: Replace animate_row_shift default color**

Change line 102 default parameter:

```python
    def animate_row_shift(self, row: int, shift: int, color: str = "#3B6FA0") -> None:
```

- [ ] **Step 3: Commit**

```bash
git add animation_modals/matrix_widget.py
git commit -m "feat: update matrix_widget default colors for light theme"
```

---

### Task 4: Update Main Window (main_gui.py)

**Files:**
- Modify: `main_gui.py`

- [ ] **Step 1: Update header — remove emoji, set Georgia font**

Change line 78-79:

```python
        header = QLabel("Secure Email Authentication and Message Integrity")
        header.setFont(QFont("Georgia", 20, QFont.Weight.Bold))
```

- [ ] **Step 2: Remove emoji from all buttons**

Change lines 120-139:

```python
        self._btn_keygen = QPushButton("Anahtar Üret")
```

```python
        self._btn_start = QPushButton("Şifreleme Başlat")
```

```python
        self._btn_next = QPushButton("Sonraki Adım")
```

```python
        self._btn_reset = QPushButton("Sıfırla")
```

- [ ] **Step 3: Remove emoji from GroupBox titles**

Change line 144:

```python
        self._key_info_group = QGroupBox("RSA-2048 Anahtar Bilgileri")
```

Change line 155:

```python
        key_header = QLabel("Anahtarlar Başarıyla Üretildi")
        key_header.setFont(QFont("Georgia", 13, QFont.Weight.Bold))
```

Change lines 162-163 (Alice key label):

```python
        alice_key_lbl = QLabel("Alice Açık Anahtarı (K⁺_A):")
        alice_key_lbl.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
```

Change lines 179-180 (Bob key label):

```python
        bob_key_lbl = QLabel("Bob Açık Anahtarı (K⁺_B):")
        bob_key_lbl.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
```

Change line 195-196 (comparison group):

```python
        self._comparison_group = QGroupBox(
            "Orijinal Mesaj ↔ Alınan Mesaj Karşılaştırması"
        )
```

- [ ] **Step 4: Remove emoji from comparison card labels**

Change line 216:

```python
        _lbl = QLabel("Alice'in Gönderdiği")
        _lbl.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
```

Change line 245:

```python
        _lbl2 = QLabel("Bob'un Aldığı")
        _lbl2.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
```

- [ ] **Step 5: Remove emoji from algo panel**

Change line 355 (algo panel title):

```python
        box = QGroupBox("Algoritmaları İzle")
```

Change lines 376-392 (algo buttons — remove emoji prefixes):

```python
        self._btn_anim_rsa = QPushButton("RSA-2048\nAnahtar Şifreleme")
```

```python
        self._btn_anim_sha = QPushButton("SHA-256\nHash Hesaplama")
```

```python
        self._btn_anim_aes = QPushButton("AES-256-GCM\nSimetrik Şifreleme")
```

- [ ] **Step 6: Update _algo_btn_style disabled state colors**

Change lines 406-407 inside `_algo_btn_style` — the disabled hardcoded colors need to match the light theme:

```python
            f"QPushButton:disabled {{ background: #FAFAF5; border: 1px solid #D1D5DB; "
            f"color: #9CA3AF; font-size: 11px; padding: 7px 6px; }}"
```

- [ ] **Step 7: Update toggle label — remove emoji prefixes**

Change lines 447-453 in `_update_toggle_label`:

```python
    def _update_toggle_label(self) -> None:
        rsa = "RSA-2048 ✓" if self._rsa_data else "RSA-2048"
        sha = "SHA-256 ✓" if self._sha_data else "SHA-256"
        aes = "AES-256-GCM ✓" if self._aes_data else "AES-256-GCM"
        arrow = "▲  Kapat" if self._bottom_body.isVisible() else "▼  Genişlet"
        self._bottom_toggle_btn.setText(
            f"  {rsa}   •   {sha}   •   {aes}                    {arrow}"
        )
```

- [ ] **Step 8: Update phase transition button texts — remove emoji**

Change line 553:

```python
                self._btn_next.setText("Paketi Bob'a Gönder")
```

Change line 568:

```python
                self._btn_next.setText("Sonraki Adım")
```

Change line 575:

```python
                self._btn_next.setText("Tamamlandı")
```

Change line 642 (reset):

```python
        self._btn_next.setText("Sonraki Adım")
```

- [ ] **Step 9: Commit**

```bash
git add main_gui.py
git commit -m "feat: update main_gui fonts, remove header/button emojis"
```

---

### Task 5: Update Alice Panel (alice_panel.py)

**Files:**
- Modify: `alice_panel.py`

- [ ] **Step 1: Update title — remove emoji, set Georgia font**

Change lines 47-49:

```python
        self._title = QLabel("Gönderici — Alice")
        self._title.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
```

- [ ] **Step 2: Update msg_group title font**

Change line 53 — set Georgia for GroupBox title via stylesheet or QFont. The GroupBox title font is set by GLOBAL_STYLESHEET, but we want serif for titles. Add after line 53:

```python
        self._msg_group = QGroupBox("E-posta Mesajı")
        self._msg_group.setFont(QFont("Georgia", 13, QFont.Weight.Bold))
```

- [ ] **Step 3: Remove emoji from status label**

Change line 76:

```python
        self.status_label = QLabel("Mesajınızı yazın ve şifreleme sürecini başlatın.")
```

Change line 136 (reset):

```python
        self.status_label.setText(
            "Mesajınızı yazın ve şifreleme sürecini başlatın."
        )
```

- [ ] **Step 4: Commit**

```bash
git add alice_panel.py
git commit -m "feat: update alice_panel fonts and remove header emojis"
```

---

### Task 6: Update Bob Panel (bob_panel.py)

**Files:**
- Modify: `bob_panel.py`

- [ ] **Step 1: Update DiagramWidget overlay colors for light background**

Change lines 51-53:

```python
_RED = QColor(198, 40, 40)              # #C62828 — koyu kırmızı (açık arka planda net)
_RED_FILL = QColor(198, 40, 40, 50)     # %20 şeffaf kırmızı dolgu
_GREEN_FILL = QColor(78, 139, 96, 50)   # %20 şeffaf adaçayı dolgu
```

- [ ] **Step 2: Update title — remove emoji, set Georgia font**

Change lines 200-201:

```python
        self._title_label = QLabel("Alıcı — Bob")
        self._title_label.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
```

- [ ] **Step 3: Update _btn_close_diagram hardcoded colors**

Change lines 219-224:

```python
        self._btn_close_diagram.setStyleSheet(
            "QPushButton { background: rgba(198,40,40,0.12); border: 2px solid #C62828; "
            "border-radius: 6px; color: #C62828; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background: rgba(198,40,40,0.28); }"
            "QPushButton:disabled { background: #FAFAF5; border: 1px solid #D1D5DB; color: #9CA3AF; }"
        )
```

- [ ] **Step 4: Remove emoji from status and waiting labels**

Change line 233:

```python
        self._received_label = QLabel("Henüz bir paket alınmadı.")
```

Change line 266:

```python
        self.status_label = QLabel("Alice'den paket bekleniyor...")
```

Change line 329 (reset):

```python
        self._received_label.setText("Henüz bir paket alınmadı.")
```

Change line 332 (reset):

```python
        self.status_label.setText("Alice'den paket bekleniyor...")
```

- [ ] **Step 5: Commit**

```bash
git add bob_panel.py
git commit -m "feat: update bob_panel fonts, emojis, overlay colors for light theme"
```

---

### Task 7: Update Utils (utils.py)

**Files:**
- Modify: `utils.py:32-49`

- [ ] **Step 1: Update step box title font to Georgia**

Change the `_make_step_box` function — add Georgia font to the GroupBox title via stylesheet. Replace lines 35-39:

```python
    box.setStyleSheet(
        f"QGroupBox {{ border: 2px solid {border_color}; border-radius: 8px; "
        f"margin-top: 14px; padding: 14px 8px 8px 8px; }}"
        f"QGroupBox::title {{ color: {border_color}; font-family: 'Georgia', 'Palatino Linotype', serif; "
        f"font-weight: bold; font-size: 15px; }}"
    )
```

- [ ] **Step 2: Commit**

```bash
git add utils.py
git commit -m "feat: update step box title font to Georgia serif"
```

---

### Task 8: Update Toast (toast.py)

**Files:**
- Modify: `toast.py`

- [ ] **Step 1: Remove icon label from header, set Georgia font on title**

Change lines 52-61. Remove the icon_lbl entirely, set Georgia font on title_lbl:

```python
        hdr = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {color}; border: none;")
        title_lbl.setWordWrap(True)
        hdr.addWidget(title_lbl, stretch=1)
        lay.addLayout(hdr)
```

- [ ] **Step 2: Commit**

```bash
git add toast.py
git commit -m "feat: update toast fonts, remove header icon"
```

---

### Task 9: Update RSA Animation (rsa_animation.py)

**Files:**
- Modify: `animation_modals/rsa_animation.py`

- [ ] **Step 1: Remove emoji from window title**

Change line 83:

```python
            "RSA-2048 Anahtar Üretimi",
```

- [ ] **Step 2: Update step label font to Georgia**

Change line 92:

```python
        self._step_lbl.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
```

- [ ] **Step 3: Commit**

```bash
git add animation_modals/rsa_animation.py
git commit -m "feat: update RSA animation title and fonts"
```

---

### Task 10: Update SHA-256 Animation Colors and Fonts (sha256_animation.py)

**CRITICAL: Only change color values and font families. Do NOT modify paintEvent logic, coordinates, rect sizes, arrow directions, or timer intervals.**

**Files:**
- Modify: `animation_modals/sha256_animation.py`

- [ ] **Step 1: Replace _REG_COLORS**

Replace lines 24-33:

```python
_REG_COLORS = [
    "#3B6FA0",  # A — blue
    "#7B5EA7",  # B — mauve
    "#4E8B60",  # C — green
    "#B8860B",  # D — yellow
    "#B87333",  # E — peach
    "#3D8B80",  # F — teal
    "#B94A4A",  # G — red
    "#2E86AB",  # H — sky
]
```

- [ ] **Step 2: Replace hardcoded QPainter fill colors in _SHA256DiagramWidget**

These are the T1/T2 box fill colors used in `paintEvent`. Replace the dark fills with light equivalents.

Line 166 — T2 highlight and default fill:

```python
        t2_fill = QColor("#E0D6EB") if highlight_t2 else QColor("#E8E9E4")
```

Line 178 — T1 highlight and default fill:

```python
        t1_fill = QColor("#EDE4CC") if highlight_t1 else QColor("#E8E9E4")
```

- [ ] **Step 3: Replace hardcoded QPainter fill colors in compact diagram variant**

Line 443 — compact T2 fill:

```python
        t2_fill   = QColor("#E0D6EB" if t2_lit else "#E0E1DC")
```

Line 456 — compact T1 fill:

```python
        t1_fill   = QColor("#EDE4CC" if t1_lit else "#E0E1DC")
```

Color mapping:
- `#4a3b5c` (dark purple highlight) → `#E0D6EB` (light lavender)
- `#4a4a2c` (dark yellow highlight) → `#EDE4CC` (light gold)
- `#3b3b5c` (dark bg_input) → `#E8E9E4` (light bg_input)
- `#26263a` (dark non-lit) → `#E0E1DC` (slightly darker than bg_card)

- [ ] **Step 4: Update heading QFont calls to Georgia**

Find all `QFont("Segoe UI", ...)` calls that are used as TITLES/HEADINGS and change to Georgia. These are on lines:

Line 522:
```python
        title.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
```

Line 542:
```python
        demo_lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
```

Line 618:
```python
        lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
```

Line 636:
```python
        t.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
```

Line 747:
```python
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
```

Line 797:
```python
        self._diag_title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
```

Leave body/value fonts (`QFont("Courier New", ...)` and smaller `QFont("Segoe UI", 9)` description text) unchanged — they are body text and will inherit the global sans-serif.

- [ ] **Step 5: Commit**

```bash
git add animation_modals/sha256_animation.py
git commit -m "feat: update SHA-256 animation colors and heading fonts for light theme"
```

---

### Task 11: Update AES Animation Colors and Fonts (aes_animation.py)

**CRITICAL: Only change color values and font families. Do NOT modify paintEvent logic, coordinates, animation timers, or widget structure.**

**Files:**
- Modify: `animation_modals/aes_animation.py`

- [ ] **Step 1: Verify _COLORS_OP references ANIM_COLORS**

Lines 25-30 reference `ANIM_COLORS["accent_yellow"]` etc. Since ANIM_COLORS was updated in Task 2, these propagate automatically. No code change needed — just verify the keys still match.

- [ ] **Step 2: Update heading QFont calls to Georgia**

Line 189:
```python
        title.setFont(QFont("Georgia", 13, QFont.Weight.Bold))
```

Line 209:
```python
        demo_title.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
```

Line 316:
```python
        lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
```

Line 334:
```python
        t.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
```

Line 791:
```python
        self._op_title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
```

Leave body/value fonts unchanged.

- [ ] **Step 3: Commit**

```bash
git add animation_modals/aes_animation.py
git commit -m "feat: update AES animation heading fonts for light theme"
```

---

### Task 12: Visual Verification

**Files:** None (testing only)

- [ ] **Step 1: Launch the application**

```bash
cd "/c/Users/sasss/Desktop/BİTİRME PROJESİ/bitirme_odevi"
python main_gui.py
```

Verify: warm ivory background, white panels, dark text, serif headings, no emoji on buttons/headers.

- [ ] **Step 2: Test Alice encryption flow**

1. Click "Anahtar Üret" — verify RSA animation opens in Alice panel, no crash
2. Verify RSA-2048 anahtar bilgileri section appears (no emoji in title)
3. Type a message, click "Şifreleme Başlat"
4. Click "Sonraki Adım" 6 times — verify each step box appears with correct pastel border colors
5. Verify SHA-256 animation opens correctly when SHA step is reached — register diagram renders, colors visible on light background
6. Verify AES animation opens correctly when AES step is reached — matrix grid renders, SubBytes/ShiftRows/MixColumns/AddRoundKey colors visible

- [ ] **Step 3: Test Bob decryption flow**

1. Verify diagram overlay on Bob panel works (red blink visible on light png background)
2. Click "Paketi Bob'a Gönder"
3. Click through all 5 Bob steps — verify step boxes with correct colors
4. Verify toast notification appears with correct colors and no header icon
5. Verify comparison section renders correctly

- [ ] **Step 4: Test Reset**

Click "Sıfırla" — verify everything resets cleanly, no visual artifacts.

- [ ] **Step 5: Test algorithm replay buttons**

Click each of RSA-2048, SHA-256, AES-256-GCM buttons in the "Algoritmaları İzle" panel. Verify each animation:
- Opens without crash
- Colors are visible and readable on light background
- Navigation (İleri/Geri) works
- Match result screen renders correctly

- [ ] **Step 6: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: visual adjustments after theme verification"
```
