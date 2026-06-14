"""SHA-256 mesaj genişletmesini (W[16]) BIT DÜZEYINDE çözen drill-down.

W[16] = σ0(W[1]) + W[9] + σ1(W[14]) + W[0]  (mod 2³²) olduğunu, σ0/σ1'in iç
ROTR/SHR/XOR işlemlerini bit bit gösterir. Round drill-down'ıyla aynı dili
(paylaşılan bit_render) ve aynı manuel gezinmeyi (tıkla-ilerle) kullanır.

Sahneler:
  0) Giriş   → W[16] formülü + dört operand (W[0], W[1], W[9], W[14]).
  1) σ0(W[1])→ W[1] ⟲7, ⟲18, ≫3 ve XOR — bit düzeyi.
  2) σ1(W[14])→ W[14] ⟲17, ⟲19, ≫10 ve XOR — bit düzeyi.
  3) Toplam  → W[16] = W[0] + σ0 + W[9] + σ1 (hex); round'larda kullanılacak.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ..base import ANIM_COLORS, cached_font
from .bit_render import bit_grid_metrics, draw_bit_row
from arayuz.theme import MANAGER

_SCENE_TITLES = ["Giriş", "σ0(W[1])", "σ1(W[14])", "Toplam"]
_SCENE_COLOR_KEYS = ["accent_blue", "accent_mauve", "accent_teal", "accent_green"]
_SCENE_COUNT = 4

_STRIP_Y = 10
_STRIP_H = 40


class _WDetailWidget(QWidget):
    """W[16]'nın σ0/σ1 iç işleyişini 4 sahnede, bit düzeyinde (tıkla-ilerle) gösterir."""

    def __init__(self, detail: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.detail = detail
        # Operand indeksleri detail["i"]'den türer (drill-down dinamik W[i] çözer).
        self._i = detail["i"]
        self._i0 = self._i - 16   # W[i-16]
        self._is0 = self._i - 15  # σ0 operandı W[i-15]
        self._i7 = self._i - 7    # W[i-7]
        self._is1 = self._i - 2   # σ1 operandı W[i-2]
        self._titles = [
            "Giriş", f"σ0(W[{self._is0}])", f"σ1(W[{self._is1}])", "Toplam",
        ]
        self._scene_index = 0
        self._bits_x0, self._cell_w, self._nibble_gap = 220, 16, 6
        self.setMinimumHeight(360)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # --- Manuel gezinme (otomatik oynatma yok) ---

    def start(self) -> None:
        self._scene_index = 0
        self.update()

    def stop(self) -> None:
        return

    def _scene(self) -> int:
        return self._scene_index

    def jump_to_scene(self, scene: int) -> None:
        self._scene_index = max(0, min(_SCENE_COUNT - 1, scene))
        self.update()

    def _advance_scene(self) -> None:
        if self._scene_index < _SCENE_COUNT - 1:
            self._scene_index += 1
            self.update()

    def _strip_box_at(self, x: int, y: int) -> int | None:
        if not (_STRIP_Y <= y <= _STRIP_Y + _STRIP_H):
            return None
        n = _SCENE_COUNT
        gap = 6
        bw = (self.width() - 16 - gap * (n - 1)) // n
        for i in range(n):
            bx = 8 + i * (bw + gap)
            if bx <= x <= bx + bw:
                return i
        return None

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        # Yalnızca üst şerit kutusu sahne değiştirir; gövdeye tıklamak ilerletmez.
        idx = self._strip_box_at(event.pos().x(), event.pos().y())
        if idx is not None:
            self.jump_to_scene(idx)

    # --- Çizim ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()
        scene = self._scene()
        self._draw_strip(p, W, scene)
        self._bits_x0, self._cell_w, self._nibble_gap = bit_grid_metrics(W)
        body = QRect(0, 62, W, self.height() - 62)
        [self._sc_input, self._sc_sigma0, self._sc_sigma1, self._sc_total][scene](p, body)
        p.end()

    def _draw_strip(self, p: QPainter, W: int, active: int) -> None:
        n = _SCENE_COUNT
        gap = 6
        bw = (W - 16 - gap * (n - 1)) // n
        for i, title in enumerate(self._titles):
            x = 8 + i * (bw + gap)
            color = QColor(ANIM_COLORS[_SCENE_COLOR_KEYS[i]])
            done = i < active
            cur = i == active
            bg = QColor(color)
            bg.setAlphaF(0.28 if cur else (0.16 if done else 0.07))
            p.setBrush(QBrush(bg))
            p.setPen(QPen(color, 2 if cur else 1))
            p.drawRoundedRect(x, _STRIP_Y, bw, _STRIP_H, 7, 7)
            p.setFont(cached_font("Georgia", 9, QFont.Weight.Bold))
            p.setPen(color if (cur or done)
                     else QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(x + 2, _STRIP_Y + 3, bw - 4, 16),
                       Qt.AlignmentFlag.AlignCenter, f"{i + 1}")
            p.setFont(cached_font("IBM Plex Sans", 8, QFont.Weight.Bold))
            p.drawText(QRect(x + 2, _STRIP_Y + 19, bw - 4, 18),
                       Qt.AlignmentFlag.AlignCenter, title)

    def _bit_row(self, p, y, label, hexstr, color_hex, *, emphasize=False) -> int:
        return draw_bit_row(
            p, y=y, label=label, hexstr=hexstr, color_hex=color_hex,
            bits_x0=self._bits_x0, cell_w=self._cell_w,
            nibble_gap=self._nibble_gap, emphasize=emphasize,
        )

    def _title(self, p: QPainter, area: QRect, text: str, color_hex: str) -> int:
        p.setFont(cached_font("Georgia", 12, QFont.Weight.Bold))
        # color_hex bir ANIM_COLORS anahtarı ("accent_blue") veya ham hex
        # olabilir; anahtarı çöz, çözülemezse olduğu gibi kullan. (Eskiden
        # QColor("accent_blue") geçersiz=siyah render edip koyu temada
        # başlıkları görünmez yapıyordu.)
        p.setPen(QColor(ANIM_COLORS.get(color_hex, color_hex)))
        p.drawText(QRect(area.left() + 8, area.top() + 6, area.width() - 16, 24),
                   Qt.AlignmentFlag.AlignCenter, text)
        return area.top() + 38

    def _note(self, p: QPainter, area: QRect, y: int, text: str) -> int:
        p.setFont(cached_font("IBM Plex Sans", 9))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 50),
                   Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, text)
        return y + 52

    def _hex_eq(self, p: QPainter, area: QRect, y: int, text: str,
                color_hex: str) -> int:
        p.setFont(cached_font("Courier New", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS.get(color_hex, color_hex)))
        p.drawText(QRect(area.left() + 8, y, area.width() - 16, 24),
                   Qt.AlignmentFlag.AlignCenter, text)
        return y + 30

    # --- Sahneler ---

    def _sc_input(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        y = self._title(p, area, f"Mesaj genişletme: W[{self._i}] nasıl üretilir?",
                        "accent_blue")
        y = self._hex_eq(p, area, y,
                         f"W[{self._i}] = σ0(W[{self._is0}]) + W[{self._i7}] + "
                         f"σ1(W[{self._is1}]) + W[{self._i0}]",
                         "accent_yellow")
        y += 8
        chips = [(f"W[{self._i0}]", d["w_i16"]), (f"W[{self._is0}]", d["w_i15"]),
                 (f"W[{self._i7}]", d["w_i7"]), (f"W[{self._is1}]", d["w_i2"])]
        n = len(chips)
        cw = min(150, (area.width() - 24) // n)
        ox = area.left() + (area.width() - n * cw) // 2
        for i, (lbl, val) in enumerate(chips):
            x = ox + i * cw
            col = QColor(ANIM_COLORS["accent_blue"])
            bg = QColor(col); bg.setAlphaF(0.16)
            p.setBrush(QBrush(bg)); p.setPen(QPen(col, 1))
            p.drawRoundedRect(x + 4, y, cw - 8, 46, 5, 5)
            p.setFont(cached_font("Georgia", 9, QFont.Weight.Bold))
            p.setPen(col)
            p.drawText(QRect(x + 4, y + 4, cw - 8, 16),
                       Qt.AlignmentFlag.AlignCenter, lbl)
            p.setFont(cached_font("Courier New", 10))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x + 4, y + 22, cw - 8, 18),
                       Qt.AlignmentFlag.AlignCenter, val)
        y += 60
        self._note(p, area, y,
                   "W[0..15] doğrudan mesaj bloğundan gelir; W[16..63] ise σ0/σ1 "
                   "fonksiyonlarıyla bunlardan türetilir. Bu W değerleri sonra "
                   "sıkıştırma round'larında (T1'in içinde) kullanılır.")

    def _sc_sigma0(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        y = self._title(p, area,
                        f"σ0(W[{self._is0}]) = ROTR(x,7) ⊕ ROTR(x,18) ⊕ SHR(x,3)",
                        "accent_mauve")
        y += self._bit_row(p, y, f"x = W[{self._is0}]", d["w_i15"],
                           ANIM_COLORS["accent_blue"])
        y += self._bit_row(p, y, "ROTR(x,7)", d["x_rotr7"], ANIM_COLORS["accent_mauve"])
        y += self._bit_row(p, y, "ROTR(x,18)", d["x_rotr18"], ANIM_COLORS["accent_mauve"])
        y += self._bit_row(p, y, "SHR(x,3)", d["x_shr3"], ANIM_COLORS["accent_peach"])
        y += 6
        y += self._bit_row(p, y, "= σ0", d["sigma0"], ANIM_COLORS["accent_green"],
                           emphasize=True)
        self._note(p, area, y + 8,
                   "ROTR döndürür (çıkan bit diğer uçtan girer); SHR kaydırır "
                   "(soldan 0 girer, sağdaki bitler düşer). Üçünün XOR'u = σ0.")

    def _sc_sigma1(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        y = self._title(p, area,
                        f"σ1(W[{self._is1}]) = ROTR(y,17) ⊕ ROTR(y,19) ⊕ SHR(y,10)",
                        "accent_teal")
        y += self._bit_row(p, y, f"y = W[{self._is1}]", d["w_i2"],
                           ANIM_COLORS["accent_blue"])
        y += self._bit_row(p, y, "ROTR(y,17)", d["y_rotr17"], ANIM_COLORS["accent_teal"])
        y += self._bit_row(p, y, "ROTR(y,19)", d["y_rotr19"], ANIM_COLORS["accent_teal"])
        y += self._bit_row(p, y, "SHR(y,10)", d["y_shr10"], ANIM_COLORS["accent_peach"])
        y += 6
        y += self._bit_row(p, y, "= σ1", d["sigma1"], ANIM_COLORS["accent_green"],
                           emphasize=True)
        self._note(p, area, y + 8,
                   "σ1 σ0 ile aynı yapı, farklı döndürme/kaydırma miktarları. "
                   "Her sütun üç satırın XOR'u.")

    def _sc_total(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        y = self._title(p, area, f"W[{self._i}] toplaması (mod 2³²)", "accent_green")
        y = self._hex_eq(p, area, y + 6,
                         f"σ0 = {d['sigma0']}     σ1 = {d['sigma1']}",
                         "accent_mauve")
        y = self._hex_eq(p, area, y + 4,
                         f"W[{self._i}] = {d['w_i16']} + {d['sigma0']} + "
                         f"{d['w_i7']} + {d['sigma1']}",
                         "accent_yellow")
        y = self._hex_eq(p, area, y + 4, f"= {d['result']}",
                         "accent_green")
        self._note(p, area, y + 10,
                   f"İşte W[{self._i}] üretildi. Aynı formülle W[{self._i+1}..63] "
                   "de türetilir; bu 64 W değeri sıkıştırma round'larında mesajını "
                   "hash'e dönüştürmek için kullanılır.")


class _WDetailDialog(QDialog):
    """W[16] drill-down sihirbazını barındıran ince diyalog (round drill-down deseni)."""

    def __init__(self, detail: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.detail = detail
        self._configure_window()
        self._build_ui(detail)
        self._resize_to_available_screen()
        self.restyle()
        MANAGER.themeChanged.connect(self._on_theme_changed)
        self.finished.connect(self._disconnect_theme_signal)

    def _configure_window(self) -> None:
        self.setWindowTitle("SHA-256 Mesaj Genişletme — Bit Bit Çözüm")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)

    def _build_ui(self, detail) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        self.title_label = QLabel("Mesaj genişletme (W) bit bit nasıl üretilir?")
        self.title_label.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.hint_label = QLabel(
            "İpucu: üst kutulara tıkla; ilerlemek için Geri/İleri kullan.")
        self.hint_label.setFont(QFont("IBM Plex Sans", 9))
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)

        self.wizard = _WDetailWidget(detail, parent=self)
        layout.addWidget(self.wizard, stretch=1)

        # Gezinme: ◀ Geri / İleri ▶ (gövde-tıkla ilerletmez) + Baştan.
        nav_row = QHBoxLayout()
        nav_row.addStretch(1)
        self.prev_btn = QPushButton("◀ Geri")
        self.prev_btn.clicked.connect(self._go_prev)
        nav_row.addWidget(self.prev_btn)
        self.next_btn = QPushButton("İleri ▶")
        self.next_btn.clicked.connect(self._go_next)
        nav_row.addWidget(self.next_btn)
        self.replay_btn = QPushButton("Baştan")
        self.replay_btn.clicked.connect(self.wizard.start)
        nav_row.addWidget(self.replay_btn)
        nav_row.addStretch(1)
        layout.addLayout(nav_row)

        self.wizard.start()

    def _go_prev(self) -> None:
        self.wizard.jump_to_scene(self.wizard._scene() - 1)

    def _go_next(self) -> None:
        self.wizard.jump_to_scene(self.wizard._scene() + 1)

    def _resize_to_available_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(900, 600)
            return
        available = screen.availableGeometry()
        self.resize(
            min(960, int(available.width() * 0.85)),
            min(640, int(available.height() * 0.85)),
        )

    def restyle(self) -> None:
        self.setStyleSheet(f"QDialog {{ background: {ANIM_COLORS['bg_panel']}; }}")
        self.title_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_mauve']}; background: transparent;")
        self.hint_label.setStyleSheet(
            f"color: {ANIM_COLORS['text_secondary']}; background: transparent;")
        btn_style = (
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['text_on_accent']}; border: none; "
            "border-radius: 6px; padding: 7px 16px; font-weight: bold; }}")
        for btn in (self.prev_btn, self.next_btn, self.replay_btn):
            btn.setStyleSheet(btn_style)
        self.wizard.update()
        self.update()

    def _on_theme_changed(self, _mode: str) -> None:
        self.restyle()

    def _disconnect_theme_signal(self, _result: int) -> None:
        self.wizard.stop()
        try:
            MANAGER.themeChanged.disconnect(self._on_theme_changed)
        except TypeError:
            pass
