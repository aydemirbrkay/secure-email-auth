"""AES-256-GCM keystream'i adım adım açıklayan sihirbaz diyaloğu.

Kullanıcı "mesaj keystream ile XOR'lanır" cümlesini görünce *keystream nedir,
sabit bir sayı mı yoksa üretilen bir şey mi, nasıl oluşur* diye merak eder. Bu
diyalog tam da bunu yanıtlar — S-Box türetim sihirbazıyla aynı kalıpta: üstte
dört sahnelik ilerleme şeridi, altta o an aktif sahnenin canlı çizimi.

Sahneler (tick döngüsünde otomatik ilerler, sonunda sabit kalır):
  0) Keystream nedir?  → mesaj ⊕ [16 byte] = şifreli; "sabit değil, üretilir"
  1) Girdi             → AES-256'nın şifrelediği SAYAÇ BLOĞU (nonce ‖ sayaç)
  2) Üretim            → sayaç bloğu 14 AES round'undan geçer (gerçek round verisi)
  3) Sonuç             → çıkan 16 byte = keystream; deterministik, nonce'la değişir

Eski metin-duvarı referans diyaloğunun yerini alır.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ..base import ANIM_COLORS, cached_font, get_animation_tick_ms
from arayuz.theme import MANAGER


# Sahne başlıkları ve vurgu renk anahtarları (soldan sağa üretim akışı).
_SCENE_TITLES = ["Keystream nedir?", "Girdi: Sayaç", "Üretim: AES-256", "Sonuç"]
_SCENE_COLOR_KEYS = ["accent_yellow", "accent_peach", "accent_blue", "accent_green"]
_SCENE_COUNT = 4

# Her sahnenin tick bütçesi (sakin tempo; hareket azaltma ile ayrıca ölçeklenir).
_SCENE0_TICKS = 30        # Keystream nedir? — soru belirir.
_SCENE1_TICKS = 28        # Girdi: sayaç bloğu.
_ROUND_TICKS = 6          # Üretim sahnesinde her round için tick.
_SCENE2_TICKS = 15 * _ROUND_TICKS  # 15 round (0..14) tek tek.
_SCENE3_TICKS = 36        # Sonuç + deterministiklik notu.
_SCENE_BUDGETS = [_SCENE0_TICKS, _SCENE1_TICKS, _SCENE2_TICKS, _SCENE3_TICKS]


def _scene_bounds() -> list[tuple[int, int]]:
    """Her sahnenin [başlangıç, bitiş) kümülatif tick aralığını döndürür."""
    bounds: list[tuple[int, int]] = []
    cursor = 0
    for budget in _SCENE_BUDGETS:
        bounds.append((cursor, cursor + budget))
        cursor += budget
    return bounds


_SCENE_BOUNDS = _scene_bounds()
_TOTAL_TICKS = _SCENE_BOUNDS[-1][1]


def _matrix_from_bytes(data: bytes) -> list[list[str]]:
    """16 baytı AES column-major 4×4 hex matrisine yerleştirir."""
    matrix = [["--"] * 4 for _ in range(4)]
    for i in range(min(16, len(data))):
        matrix[i % 4][i // 4] = f"{data[i]:02x}"
    return matrix


class _KeystreamWizardWidget(QWidget):
    """Keystream'in ne olduğunu ve nasıl üretildiğini dört sahnede canlandırır."""

    _TICK_MS = 70

    def __init__(
        self,
        counter_block: bytes,
        keystream: bytes,
        nonce: bytes,
        rounds_data: list[dict] | None = None,
        initial_state_hex: list[list[str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.counter_block = counter_block
        self.keystream = keystream
        self.nonce = nonce
        self._rounds = rounds_data or []
        self._counter_matrix = (
            initial_state_hex if initial_state_hex else _matrix_from_bytes(counter_block)
        )
        self._keystream_matrix = _matrix_from_bytes(keystream)
        self._tick = 0
        self.setMinimumHeight(330)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    # ------------------------------------------------------------------
    # Tick motoru
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Sihirbazı baştan başlatır."""
        self._tick = 0
        self._timer.start(get_animation_tick_ms(self._TICK_MS))
        self.update()

    def stop(self) -> None:
        """Tick zamanlayıcısını durdurur."""
        self._timer.stop()

    def _advance(self) -> None:
        if self._tick < _TOTAL_TICKS:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def _scene(self) -> int:
        """Aktif sahne indeksini (0..3) verir."""
        for i, (a, b) in enumerate(_SCENE_BOUNDS):
            if self._tick < b:
                return i
        return _SCENE_COUNT - 1

    def _scene_local(self, scene: int) -> int:
        """Verilen sahnenin içindeki yerel tick (0'dan başlar)."""
        return self._tick - _SCENE_BOUNDS[scene][0]

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()
        scene = self._scene()

        self._draw_progress_strip(p, W, scene)

        body = QRect(0, 64, W, self.height() - 64)
        if scene == 0:
            self._draw_scene_what(p, body)
        elif scene == 1:
            self._draw_scene_input(p, body)
        elif scene == 2:
            self._draw_scene_generate(p, body)
        else:
            self._draw_scene_result(p, body)
        p.end()

    def _draw_progress_strip(self, p: QPainter, W: int, active: int) -> None:
        """Üstte dört sahnelik ilerleme şeridini çizer; aktif sahne vurgulu."""
        n = _SCENE_COUNT
        gap = 8
        bw = (W - 16 - gap * (n - 1)) // n
        y = 10
        h = 40
        for i, title in enumerate(_SCENE_TITLES):
            x = 8 + i * (bw + gap)
            color = QColor(ANIM_COLORS[_SCENE_COLOR_KEYS[i]])
            done = i < active
            cur = i == active
            bg = QColor(color)
            bg.setAlphaF(0.28 if cur else (0.16 if done else 0.07))
            p.setBrush(QBrush(bg))
            p.setPen(QPen(color, 2 if cur else 1))
            p.drawRoundedRect(x, y, bw, h, 7, 7)
            p.setFont(cached_font("Georgia", 9, QFont.Weight.Bold))
            p.setPen(color if (cur or done) else QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x + 4, y + 4, bw - 8, 16),
                       Qt.AlignmentFlag.AlignCenter, f"{i + 1}")
            p.setFont(cached_font("IBM Plex Sans", 8, QFont.Weight.Bold))
            p.drawText(QRect(x + 2, y + 19, bw - 4, 18),
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, title)

    # --- Sahne 0: Keystream nedir? -----------------------------------

    def _draw_scene_what(self, p: QPainter, area: QRect) -> None:
        local = self._scene_local(0)
        cx = area.center().x()
        y = area.top() + 8

        p.setFont(cached_font("IBM Plex Sans", 11))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 22),
                   Qt.AlignmentFlag.AlignCenter,
                   "Mesajın AES'ten geçmez; sonunda 16 byte'lık bir blokla XOR'lanır:")
        y += 40

        # mesaj ⊕ [keystream] = şifreli  (kavramsal şerit)
        p.setFont(cached_font("Courier New", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(area.left(), y, area.width(), 26),
                   Qt.AlignmentFlag.AlignCenter, "mesaj   ⊕   keystream   =   şifreli metin")
        y += 40

        # keystream baytları (kademeli belirir)
        shown = min(16, max(0, (local - 6)))
        self._draw_hex_row(p, cx, y, self.keystream, shown,
                           ANIM_COLORS["accent_yellow"])
        y += 56

        if local > 20:
            p.setFont(cached_font("Georgia", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            p.drawText(QRect(area.left() + 12, y, area.width() - 24, 24),
                       Qt.AlignmentFlag.AlignCenter,
                       "Bu 16 byte sabit bir sayı mı?  →  HAYIR, üretilir.  Nasıl? ↓")

    # --- Sahne 1: Girdi (sayaç bloğu) --------------------------------

    def _draw_scene_input(self, p: QPainter, area: QRect) -> None:
        local = self._scene_local(1)
        cx = area.center().x()
        y = area.top() + 8

        p.setFont(cached_font("IBM Plex Sans", 11))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 22),
                   Qt.AlignmentFlag.AlignCenter,
                   "AES-256'nın şifrelediği şey mesaj değil — SAYAÇ BLOĞU:")
        y += 32

        p.setFont(cached_font("Courier New", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_peach"]))
        p.drawText(QRect(area.left(), y, area.width(), 20),
                   Qt.AlignmentFlag.AlignCenter,
                   "sayaç bloğu  =  nonce (12 byte)  ‖  sayaç (00 00 00 02)")
        y += 30

        shown = min(16, max(0, local))
        self._draw_hex_row(p, cx, y, self.counter_block, shown,
                           ANIM_COLORS["accent_peach"])
        y += 54

        if local > 14:
            self._draw_matrix(p, cx - 92, y, self._counter_matrix,
                              ANIM_COLORS["accent_peach"], title="4×4 (column-major)")

    # --- Sahne 2: Üretim (14 round) ----------------------------------

    def _draw_scene_generate(self, p: QPainter, area: QRect) -> None:
        local = self._scene_local(2)
        cx = area.center().x()
        y = area.top() + 8
        ri = min(14, local // _ROUND_TICKS)

        p.setFont(cached_font("IBM Plex Sans", 11))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 22),
                   Qt.AlignmentFlag.AlignCenter,
                   "Sayaç bloğu 14 AES-256 round'undan geçer (her round state'i değiştirir):")
        y += 30

        # Round sayacı + ilerleme çubuğu
        label = "Round 0 — başlangıç AddRoundKey" if ri == 0 else f"Round {ri} / 14"
        p.setFont(cached_font("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_blue"]))
        p.drawText(QRect(area.left(), y, area.width(), 24),
                   Qt.AlignmentFlag.AlignCenter, label)
        y += 28
        self._draw_progress_bar(p, cx - 150, y, 300, ri / 14.0)
        y += 22

        # State matrisi: bu round'dan sonraki state; önceki round'a göre değişen
        # hücreler vurgulanır → kullanıcı "dönüşümü" görür.
        cur = self._round_state(ri)
        prev = self._round_state(ri - 1) if ri > 0 else self._counter_matrix
        self._draw_matrix(p, cx - 92, y, cur, ANIM_COLORS["accent_blue"],
                          changed_vs=prev)

    # --- Sahne 3: Sonuç ----------------------------------------------

    def _draw_scene_result(self, p: QPainter, area: QRect) -> None:
        local = self._scene_local(3)
        cx = area.center().x()
        y = area.top() + 8

        p.setFont(cached_font("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(area.left(), y, area.width(), 24),
                   Qt.AlignmentFlag.AlignCenter,
                   "Çıkan 16 byte  =  KEYSTREAM")
        y += 30

        self._draw_matrix(p, cx - 92, y, self._keystream_matrix,
                          ANIM_COLORS["accent_green"])
        y += 150

        if local > 8:
            p.setFont(cached_font("IBM Plex Sans", 10))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(area.left() + 12, y, area.width() - 24, 40),
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       "Deterministik: aynı nonce + anahtar → her zaman aynı keystream. "
                       "Nonce her şifrelemede yeni & rastgele üretildiği için keystream "
                       "asla tekrar etmez.")
            y += 44

        if local > 16:
            p.setFont(cached_font("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            p.drawText(QRect(area.left(), y, area.width(), 22),
                       Qt.AlignmentFlag.AlignCenter,
                       "keystream  ⊕  mesaj  =  şifreli metin")
            y += 24

        if local > 22:
            p.setFont(cached_font("IBM Plex Sans", 9))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(area.left() + 12, y, area.width() - 24, 36),
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       "Mesaj 16 bayttan uzunsa sayaç birer artar (00 00 00 03, "
                       "00 00 00 04 …) ve sonraki her blok kendi keystream'ini "
                       "aynı yolla üretir.")

    # ------------------------------------------------------------------
    # Çizim yardımcıları
    # ------------------------------------------------------------------

    def _round_state(self, ri: int) -> list[list[str]]:
        """ri round'undan sonraki 4×4 state (gerçek round verisinden)."""
        if 0 <= ri < len(self._rounds):
            return self._rounds[ri].get("after_add_round_key", self._keystream_matrix)
        return self._keystream_matrix

    def _draw_hex_row(
        self, p: QPainter, cx: int, y: int, data: bytes, shown: int, color_hex: str,
    ) -> None:
        """16 baytı küçük hex kutuları satırında çizer (ilk ``shown`` tanesi görünür)."""
        n = 16
        bw, gap = 30, 3
        total = n * bw + (n - 1) * gap
        # Dar pencerede 8'erli iki satıra böl.
        if total > self.width() - 16:
            self._draw_hex_grid(p, cx, y, data, shown, color_hex, per_row=8)
            return
        x0 = cx - total // 2
        color = QColor(color_hex)
        for i in range(min(shown, len(data), n)):
            x = x0 + i * (bw + gap)
            bg = QColor(color); bg.setAlphaF(0.18)
            p.setBrush(QBrush(bg))
            p.setPen(QPen(color, 1))
            p.drawRoundedRect(x, y, bw, 30, 4, 4)
            p.setFont(cached_font("Courier New", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x, y, bw, 30), Qt.AlignmentFlag.AlignCenter,
                       f"{data[i]:02x}")

    def _draw_hex_grid(
        self, p: QPainter, cx: int, y: int, data: bytes, shown: int,
        color_hex: str, per_row: int = 8,
    ) -> None:
        """Hex kutularını ``per_row`` sütunlu ızgaraya yerleştirir (dar pencere)."""
        bw, gap = 30, 3
        total = per_row * bw + (per_row - 1) * gap
        x0 = cx - total // 2
        color = QColor(color_hex)
        for i in range(min(shown, len(data), 16)):
            r, c = divmod(i, per_row)
            x = x0 + c * (bw + gap)
            yy = y + r * (30 + gap)
            bg = QColor(color); bg.setAlphaF(0.18)
            p.setBrush(QBrush(bg))
            p.setPen(QPen(color, 1))
            p.drawRoundedRect(x, yy, bw, 30, 4, 4)
            p.setFont(cached_font("Courier New", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x, yy, bw, 30), Qt.AlignmentFlag.AlignCenter,
                       f"{data[i]:02x}")

    def _draw_matrix(
        self, p: QPainter, x: int, y: int, matrix: list[list[str]], color_hex: str,
        *, title: str | None = None, changed_vs: list[list[str]] | None = None,
    ) -> None:
        """4×4 hex matrisini kart olarak çizer; değişen hücreler vurgulanır."""
        color = QColor(color_hex)
        cell = 42
        gap = 4
        grid = 4 * cell + 3 * gap
        if title:
            p.setFont(cached_font("IBM Plex Sans", 8))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x, y - 16, grid, 14),
                       Qt.AlignmentFlag.AlignCenter, title)
        for r in range(4):
            for c in range(4):
                cxp = x + c * (cell + gap)
                cyp = y + r * (cell + gap)
                changed = (
                    changed_vs is not None
                    and matrix[r][c] != changed_vs[r][c]
                )
                bg = QColor(color)
                bg.setAlphaF(0.30 if changed else 0.12)
                p.setBrush(QBrush(bg))
                if changed:
                    p.setPen(QPen(QColor(ANIM_COLORS["accent_yellow"]), 2))
                else:
                    p.setPen(QPen(color, 1))
                p.drawRoundedRect(cxp, cyp, cell, cell, 5, 5)
                p.setFont(cached_font("Courier New", 11, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["text_primary"]))
                p.drawText(QRect(cxp, cyp, cell, cell),
                           Qt.AlignmentFlag.AlignCenter, matrix[r][c])

    def _draw_progress_bar(
        self, p: QPainter, x: int, y: int, w: int, frac: float,
    ) -> None:
        """İnce ilerleme çubuğu (round ilerlemesi)."""
        p.setBrush(QBrush(QColor(ANIM_COLORS["bg_input"])))
        p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))
        p.drawRoundedRect(x, y, w, 8, 4, 4)
        fill = max(0.0, min(1.0, frac))
        if fill > 0:
            p.setBrush(QBrush(QColor(ANIM_COLORS["accent_blue"])))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, int(w * fill), 8, 4, 4)


class _KeystreamReferenceDialog(QDialog):
    """Keystream sihirbazını barındıran ince, temasız metin-duvarsız diyalog.

    Geriye dönük uyumluluk: ``.keystream`` ve ``.nonce`` öznitelikleri korunur
    (window/test bunları okur).
    """

    def __init__(
        self,
        keystream: bytes,
        nonce: bytes,
        rounds_data: list[dict] | None = None,
        counter_block: bytes = b"",
        initial_state_hex: list[list[str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.keystream = keystream
        self.nonce = nonce
        self.counter_block = counter_block or (nonce + (2).to_bytes(4, "big"))
        self._configure_window()
        self._build_ui(rounds_data, initial_state_hex)
        self._resize_to_available_screen()
        self.restyle()
        MANAGER.themeChanged.connect(self._on_theme_changed)
        self.finished.connect(self._disconnect_theme_signal)

    def _configure_window(self) -> None:
        """Diyaloğu bağımsız, kapatma düğmeli, non-modal sihirbaz penceresi yapar."""
        self.setWindowTitle("AES-256-GCM Keystream Sihirbazı")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)

    def _build_ui(
        self,
        rounds_data: list[dict] | None,
        initial_state_hex: list[list[str]] | None,
    ) -> None:
        """Başlık + sihirbaz + 'baştan oynat' düğmesini kurar."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)

        self.title_label = QLabel("Keystream nedir, nasıl üretilir?")
        self.title_label.setFont(QFont("Georgia", 15, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.wizard = _KeystreamWizardWidget(
            self.counter_block, self.keystream, self.nonce,
            rounds_data=rounds_data, initial_state_hex=initial_state_hex,
            parent=self,
        )
        layout.addWidget(self.wizard, stretch=1)

        self.replay_btn = QPushButton("Baştan oynat")
        self.replay_btn.clicked.connect(self.wizard.start)
        layout.addWidget(self.replay_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.wizard.start()

    def _resize_to_available_screen(self) -> None:
        """Diyaloğu mevcut ekranı taşırmadan boyutlandırır."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(820, 600)
            return
        available = screen.availableGeometry()
        self.resize(
            min(900, int(available.width() * 0.80)),
            min(640, int(available.height() * 0.78)),
        )

    def restyle(self) -> None:
        """Açık diyaloğu aktif uygulama temasına geçirir."""
        self.setStyleSheet(
            f"QDialog {{ background: {ANIM_COLORS['bg_panel']}; }}"
        )
        self.title_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_yellow']}; background: transparent;"
        )
        self.replay_btn.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['text_on_accent']}; border: none; "
            "border-radius: 6px; padding: 7px 16px; font-weight: bold; }}"
        )
        self.wizard.update()
        self.update()

    def _on_theme_changed(self, _mode: str) -> None:
        """Tema değişiminde açık diyaloğu yeniden stillendirir."""
        self.restyle()

    def _disconnect_theme_signal(self, _result: int) -> None:
        """Diyalog kapanınca animasyonu durdurur ve tema sinyalini çözer."""
        self.wizard.stop()
        try:
            MANAGER.themeChanged.disconnect(self._on_theme_changed)
        except TypeError:
            pass
