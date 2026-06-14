"""SHA-256 sıkıştırma round'unu BIT DÜZEYINDE adım adım çözen drill-down.

Kullanıcı "SHA mesajımı dönüştürdü ve bu hash çıktı" der ama *gerçekten bu
algoritma mı, ben neyi hesapladım* diye merak eder. Bu diyalog, projedeki
GERÇEK hash hesabının SON bloğunun 64. round'unu alıp Σ1/Ch/Σ0/Maj'ı bit bit
(ROTR/SHR/XOR/AND/NOT) gösterir; kapanışta `A' + H0 = hash'in ilk word'ü`
köprüsüyle ekranda görünen çıktının bir parçasını birebir bağlar.

Gezinme keystream sihirbazıyla AYNI desendedir: üstte tıklanabilir sahne
şeridi, otomatik oynatma YOK; gövdeye tıklamak bir sonraki sahneye geçer. Her
sahne anında ve TAM çizilir.

Sahneler:
  0) Giriş     → round 64'ün a..h, K, W değerleri (mesajdan türeyen).
  1) Σ1(E)     → E ⟲6, ⟲11, ⟲25 ve XOR — bit düzeyi.
  2) Ch + T1   → Ch=(E∧F)⊕(¬E∧G) bit düzeyi; T1 = H+Σ1+Ch+K+W (hex toplam).
  3) Σ0(A)     → A ⟲2, ⟲13, ⟲22 ve XOR — bit düzeyi.
  4) Maj + T2  → Maj bit düzeyi; T2 = Σ0+Maj; A'=T1+T2, E'=D+T1 (hex).
  5) Köprü     → A' → H0 = 6a09e667 + A' = ekrandaki hash'in ilk 8 hanesi.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ..base import ANIM_COLORS, cached_font
from .bit_render import bits as _bits, bit_grid_metrics, draw_bit_row
from arayuz.theme import MANAGER

_SCENE_TITLES = ["Giriş", "Σ1(E)", "Ch → T1", "Σ0(A)", "Maj → T2", "Köprü"]
_SCENE_COLOR_KEYS = [
    "accent_blue", "accent_yellow", "accent_yellow",
    "accent_mauve", "accent_mauve", "accent_green",
]
_SCENE_COUNT = 6

_STRIP_Y = 10
_STRIP_H = 40


class _SHARoundDetailWidget(QWidget):
    """Round 64'ün iç işleyişini 6 sahnede, bit düzeyinde (tıkla-ilerle) gösterir."""

    def __init__(
        self,
        detail: dict,
        h0_init: str,
        final_word: str,
        final_hash: str,
        is_final_round: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.detail = detail
        self.h0_init = h0_init
        self.final_word = final_word
        self.final_hash = final_hash
        # Köprü sahnesi yalnız son bloğun 64. round'unda final hash'e bağlanır;
        # diğer round'larda çıktının sonraki round'a aktığı anlatılır.
        self.is_final_round = is_final_round
        self._scene_index = 0
        # Bit satırı yerleşimi (paintEvent her boyutta yeniden hesaplar).
        self._bits_x0 = 230
        self._cell_w = 16
        self._nibble_gap = 6
        self.setMinimumHeight(380)
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
        # Yalnızca üst şerit kutusuna tıklamak sahne değiştirir; gövdeye
        # tıklamak ilerletmez (yoğun bit ekranında kazara atlama olmasın).
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
        # Bit satırı grid'ini genişliğe göre hesapla (satırlar hizalı kalsın).
        self._bits_x0, self._cell_w, self._nibble_gap = bit_grid_metrics(W)

        body = QRect(0, 62, W, self.height() - 62)
        [self._sc_input, self._sc_sigma1, self._sc_ch, self._sc_sigma0,
         self._sc_maj, self._sc_bridge][scene](p, body)
        p.end()

    def _draw_strip(self, p: QPainter, W: int, active: int) -> None:
        n = _SCENE_COUNT
        gap = 6
        bw = (W - 16 - gap * (n - 1)) // n
        for i, title in enumerate(_SCENE_TITLES):
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

    # --- Bit satırı yardımcıları ---

    def _draw_bit_row(
        self, p: QPainter, y: int, label: str, hexstr: str, color_hex: str,
        *, emphasize: bool = False,
    ) -> int:
        """Paylaşılan bit-satırı çizicisine widget'ın grid ölçülerini geçirir."""
        return draw_bit_row(
            p, y=y, label=label, hexstr=hexstr, color_hex=color_hex,
            bits_x0=self._bits_x0, cell_w=self._cell_w,
            nibble_gap=self._nibble_gap, emphasize=emphasize,
        )

    def _draw_title(self, p: QPainter, area: QRect, text: str,
                    color_hex: str) -> int:
        p.setFont(cached_font("Georgia", 12, QFont.Weight.Bold))
        # color_hex bir ANIM_COLORS anahtarı ("accent_blue") veya ham hex
        # olabilir; anahtarı çöz, çözülemezse olduğu gibi kullan. (Eskiden
        # QColor("accent_blue") geçersiz=siyah render edip koyu temada
        # başlıkları görünmez yapıyordu.)
        p.setPen(QColor(ANIM_COLORS.get(color_hex, color_hex)))
        p.drawText(QRect(area.left() + 8, area.top() + 6, area.width() - 16, 24),
                   Qt.AlignmentFlag.AlignCenter, text)
        return area.top() + 38

    def _draw_note(self, p: QPainter, area: QRect, y: int, text: str) -> int:
        p.setFont(cached_font("IBM Plex Sans", 9))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 44),
                   Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, text)
        return y + 46

    def _draw_hex_eq(self, p: QPainter, area: QRect, y: int, text: str,
                     color_hex: str) -> int:
        p.setFont(cached_font("Courier New", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS.get(color_hex, color_hex)))
        p.drawText(QRect(area.left() + 8, y, area.width() - 16, 24),
                   Qt.AlignmentFlag.AlignCenter, text)
        return y + 30

    # --- Sahneler ---

    def _sc_input(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        blocks = d.get("blocks_count", 1)
        rn = d.get("round_no", 64)
        blk = d.get("block_no", 1)
        origin = ("senin mesaj bloğundan" if blocks == 1
                  else f"Blok {blk}/{blocks}'ten")
        y = self._draw_title(p, area,
                             f"Round {rn} — girişler", "accent_blue")
        # a..h chip satırı
        labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
        vals = [d[k] for k in "abcdefgh"]
        n = 8
        cw = min(86, (area.width() - 24) // n)
        ox = area.left() + (area.width() - n * cw) // 2
        for i, (lbl, val) in enumerate(zip(labels, vals)):
            x = ox + i * cw
            col = QColor(ANIM_COLORS["accent_blue"])
            bg = QColor(col); bg.setAlphaF(0.16)
            p.setBrush(QBrush(bg)); p.setPen(QPen(col, 1))
            p.drawRoundedRect(x + 2, y, cw - 4, 42, 5, 5)
            p.setFont(cached_font("Georgia", 9, QFont.Weight.Bold))
            p.setPen(col)
            p.drawText(QRect(x + 2, y + 2, cw - 4, 16),
                       Qt.AlignmentFlag.AlignCenter, lbl)
            p.setFont(cached_font("Courier New", 8))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x + 2, y + 20, cw - 4, 18),
                       Qt.AlignmentFlag.AlignCenter, val)
        y += 56
        y = self._draw_hex_eq(p, area, y,
                              f"K = {d['k']}      W = {d['w']}",
                              ANIM_COLORS["accent_peach"])
        self._draw_note(p, area, y + 6,
                        f"Bu round, {origin} türeyen W ve önceki round'ların "
                        "A..H değerleriyle çalışır. Aşağıdaki sahnelerde Σ1, Ch, "
                        "Σ0, Maj bit bit uygulanır.")

    def _sc_sigma1(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        y = self._draw_title(p, area,
                             "Σ1(E) = ROTR(E,6) ⊕ ROTR(E,11) ⊕ ROTR(E,25)",
                             "accent_yellow")
        y += self._draw_bit_row(p, y, "E", d["e"], ANIM_COLORS["accent_peach"])
        y += self._draw_bit_row(p, y, "ROTR(E,6)", d["e_rotr6"], ANIM_COLORS["accent_yellow"])
        y += self._draw_bit_row(p, y, "ROTR(E,11)", d["e_rotr11"], ANIM_COLORS["accent_yellow"])
        y += self._draw_bit_row(p, y, "ROTR(E,25)", d["e_rotr25"], ANIM_COLORS["accent_yellow"])
        y += 6
        y += self._draw_bit_row(p, y, "= Σ1(E)", d["sigma1"],
                                ANIM_COLORS["accent_green"], emphasize=True)
        self._draw_note(p, area, y + 8,
                        "Her sütun, üç döndürülmüş satırın XOR'u (tek sayıda 1 → 1). "
                        "ROTR = bitleri sağa döndür; soldan dolan bitler sağdan çıkanlardır.")

    def _sc_ch(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        y = self._draw_title(p, area, "Ch(E,F,G) = (E∧F) ⊕ (¬E∧G)",
                             "accent_yellow")
        y += self._draw_bit_row(p, y, "E", d["e"], ANIM_COLORS["accent_peach"])
        y += self._draw_bit_row(p, y, "F", d["f"], ANIM_COLORS["accent_teal"])
        y += self._draw_bit_row(p, y, "G", d["g"], ANIM_COLORS["accent_red"])
        y += self._draw_bit_row(p, y, "E ∧ F", d["e_and_f"], ANIM_COLORS["accent_yellow"])
        y += self._draw_bit_row(p, y, "¬E ∧ G", d["not_e_and_g"], ANIM_COLORS["accent_yellow"])
        y += self._draw_bit_row(p, y, "= Ch", d["ch"], ANIM_COLORS["accent_green"],
                                emphasize=True)
        y += 6
        y = self._draw_hex_eq(p, area, y,
                              f"T1 = H + Σ1(E) + Ch + K + W = {d['t1']}",
                              ANIM_COLORS["accent_yellow"])
        self._draw_note(p, area, y + 2,
                        "Ch 'seçici'dir: E'nin 1 olduğu bitlerde F'yi, 0 olduğu "
                        "bitlerde G'yi seçer. T1 toplaması mod 2³² (hex gösterildi).")

    def _sc_sigma0(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        y = self._draw_title(p, area,
                             "Σ0(A) = ROTR(A,2) ⊕ ROTR(A,13) ⊕ ROTR(A,22)",
                             "accent_mauve")
        y += self._draw_bit_row(p, y, "A", d["a"], ANIM_COLORS["accent_blue"])
        y += self._draw_bit_row(p, y, "ROTR(A,2)", d["a_rotr2"], ANIM_COLORS["accent_mauve"])
        y += self._draw_bit_row(p, y, "ROTR(A,13)", d["a_rotr13"], ANIM_COLORS["accent_mauve"])
        y += self._draw_bit_row(p, y, "ROTR(A,22)", d["a_rotr22"], ANIM_COLORS["accent_mauve"])
        y += 6
        y += self._draw_bit_row(p, y, "= Σ0(A)", d["sigma0"],
                                ANIM_COLORS["accent_green"], emphasize=True)
        self._draw_note(p, area, y + 8,
                        "Σ0, Σ1 ile aynı yapı (farklı döndürme miktarları). Yine "
                        "her sütun üç döndürülmüş satırın XOR'udur.")

    def _sc_maj(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        y = self._draw_title(p, area, "Maj(A,B,C) = (A∧B) ⊕ (A∧C) ⊕ (B∧C)",
                             "accent_mauve")
        y += self._draw_bit_row(p, y, "A", d["a"], ANIM_COLORS["accent_blue"])
        y += self._draw_bit_row(p, y, "B", d["b"], ANIM_COLORS["accent_mauve"])
        y += self._draw_bit_row(p, y, "C", d["c"], ANIM_COLORS["accent_green"])
        y += self._draw_bit_row(p, y, "A∧B", d["a_and_b"], ANIM_COLORS["accent_mauve"])
        y += self._draw_bit_row(p, y, "A∧C", d["a_and_c"], ANIM_COLORS["accent_mauve"])
        y += self._draw_bit_row(p, y, "B∧C", d["b_and_c"], ANIM_COLORS["accent_mauve"])
        y += self._draw_bit_row(p, y, "= Maj", d["maj"], ANIM_COLORS["accent_green"],
                                emphasize=True)
        y += 4
        y = self._draw_hex_eq(p, area, y,
                              f"T2 = Σ0(A) + Maj = {d['t2']}",
                              ANIM_COLORS["accent_mauve"])
        y = self._draw_hex_eq(p, area, y,
                              f"A' = T1 + T2 = {d['new_a']}    "
                              f"E' = D + T1 = {d['new_e']}",
                              ANIM_COLORS["accent_green"])

    def _sc_next_round(self, p: QPainter, area: QRect) -> None:
        """Son round DEĞİLSE: bu round'un çıktısının sonraki round'a nasıl
        aktığını gösterir (final hash köprüsü yalnız son round'da anlamlı)."""
        d = self.detail
        rn = d.get("round_no", 0)
        y = self._draw_title(p, area, "Bu round'un çıktısı ne olur?",
                             "accent_green")
        y = self._draw_hex_eq(p, area, y + 4,
                              f"A' = T1 + T2 = {d['new_a']}      "
                              f"E' = D + T1 = {d['new_e']}",
                              ANIM_COLORS["accent_green"])
        y = self._draw_hex_eq(p, area, y + 6,
                              f"Round {rn}  →  Round {rn + 1}: "
                              "A..H bir sağa kayar; A←A', E←E'",
                              ANIM_COLORS["accent_yellow"])
        self._draw_note(p, area, y + 10,
                        "Her round register'ları bir sağa kaydırır ve yalnız A "
                        "ile E'yi günceller (B..D, F..H bir önceki değerden gelir). "
                        "64 round sonra son bloğun çıkışı başlangıç H değerlerine "
                        "eklenir; bu toplam hash'i oluşturur — son round'un "
                        "'Köprü' sahnesi bunu ekrandaki hash'e bağlar.")

    def _sc_bridge(self, p: QPainter, area: QRect) -> None:
        d = self.detail
        if not self.is_final_round:
            self._sc_next_round(p, area)
            return
        y = self._draw_title(p, area, "Ben neyi hesapladım?", "accent_green")
        y = self._draw_hex_eq(p, area, y + 4,
                              f"64. round'un A çıkışı:  A' = {d['new_a']}",
                              ANIM_COLORS["accent_green"])
        y = self._draw_hex_eq(p, area, y + 6,
                              f"H0 = {self.h0_init} + {d['new_a']} = {self.final_word}",
                              ANIM_COLORS["accent_yellow"])
        y += 14
        # Final hash, ilk 8 hane vurgulu
        p.setFont(cached_font("Courier New", 11, QFont.Weight.Bold))
        first8 = self.final_hash[:8]
        rest = self.final_hash[8:40] + ("…" if len(self.final_hash) > 40 else "")
        fm = p.fontMetrics()
        total_w = fm.horizontalAdvance(first8 + rest)
        x = area.left() + (area.width() - total_w) // 2
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(x, y + 16, first8)
        x += fm.horizontalAdvance(first8)
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(x, y + 16, rest)
        y += 30
        self._draw_note(p, area, y,
                        "İlk 8 hane (yeşil) = ekranda gördüğün hash'in ilk word'ü. "
                        "İşte mesajın, SHA-256 ile dönüşüp bu çıktının bu parçasını "
                        "üretti — diğer 7 word de aynı yolla (kendi round 64 çıkışı "
                        "+ başlangıç H) hesaplanır.")


class _SHARoundDetailDialog(QDialog):
    """Round drill-down sihirbazını barındıran ince diyalog (keystream deseni)."""

    def __init__(
        self,
        detail: dict,
        h0_init: str,
        final_word: str,
        final_hash: str,
        is_final_round: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        # parent super'e verilmez: bagimsiz ust-duzey pencere → gorev cubugu
        # dugmesi + normal minimize (owned pencere koseye kuculmesin). Referans
        # cagiran pencerede tutulur, GC olmaz.
        super().__init__(None)
        self.detail = detail
        self.is_final_round = is_final_round
        self._configure_window()
        self._build_ui(detail, h0_init, final_word, final_hash)
        self._resize_to_available_screen()
        self.restyle()
        MANAGER.themeChanged.connect(self._on_theme_changed)
        self.finished.connect(self._disconnect_theme_signal)

    def _configure_window(self) -> None:
        rn = self.detail.get("round_no", 64)
        self.setWindowTitle(f"SHA-256 Round {rn} — Bit Bit Çözüm")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)

    def _build_ui(self, detail, h0_init, final_word, final_hash) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        rn = detail.get("round_no", 64)
        title_text = (
            "Mesajın hash'inin bir parçası nasıl hesaplandı?"
            if self.is_final_round
            else f"Sıkıştırma round {rn} bit bit nasıl hesaplanır?"
        )
        self.title_label = QLabel(title_text)
        self.title_label.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.hint_label = QLabel(
            "İpucu: üstteki kutulara tıkla ya da ilerlemek için sahneye tıkla.")
        self.hint_label.setFont(QFont("IBM Plex Sans", 9))
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)

        self.wizard = _SHARoundDetailWidget(
            detail, h0_init, final_word, final_hash,
            is_final_round=self.is_final_round, parent=self)
        layout.addWidget(self.wizard, stretch=1)

        # Gezinme: ◀ Geri / İleri ▶ (gövde-tıkla ilerletmez). "Baştan" kaldırıldı
        # — kullanıcı yanlışlıkla tıklayıp sahneyi sıfırlamasın; Geri/İleri yeter.
        nav_row = QHBoxLayout()
        nav_row.addStretch(1)
        self.prev_btn = QPushButton("◀ Geri")
        self.prev_btn.clicked.connect(self._go_prev)
        nav_row.addWidget(self.prev_btn)
        self.next_btn = QPushButton("İleri ▶")
        self.next_btn.clicked.connect(self._go_next)
        nav_row.addWidget(self.next_btn)
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
            self.resize(900, 620)
            return
        available = screen.availableGeometry()
        self.resize(
            min(960, int(available.width() * 0.85)),
            min(680, int(available.height() * 0.85)),
        )

    def restyle(self) -> None:
        self.setStyleSheet(f"QDialog {{ background: {ANIM_COLORS['bg_panel']}; }}")
        self.title_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_yellow']}; background: transparent;")
        self.hint_label.setStyleSheet(
            f"color: {ANIM_COLORS['text_secondary']}; background: transparent;")
        btn_style = (
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['text_on_accent']}; border: none; "
            "border-radius: 6px; padding: 7px 16px; font-weight: bold; }}")
        for btn in (self.prev_btn, self.next_btn):
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
