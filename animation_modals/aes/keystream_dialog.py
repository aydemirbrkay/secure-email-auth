"""AES-256-GCM keystream'i adım adım açıklayan sihirbaz diyaloğu.

Kullanıcı "mesaj keystream ile XOR'lanır" cümlesini görünce *keystream nedir,
sabit bir sayı mı yoksa üretilen bir şey mi, nasıl oluşur* diye merak eder. Bu
diyalog tam da bunu yanıtlar — S-Box türetim sihirbazıyla aynı kalıpta: üstte
dört sahnelik ilerleme şeridi, altta o an aktif sahnenin tam çizimi.

Gezinme TAMAMEN manueldir (otomatik oynatma yoktur): üstteki kutuya tıklamak o
sahneye atlar; gövdeye tıklamak bir sonraki sahneye geçer. Her sahne anında ve
TAM çizilir (yarım dolu satır / üst üste yazı olmaz).

Sahneler (üretim-önce akış — önce keystream'in nasıl üretildiği, en sonda nasıl
kullanıldığı anlatılır):
  0) Sayaç bloğu  → AES'in şifrelediği SAYAÇ BLOĞUNUN ÜRETİMİ: nonce (12B) ‖
                    sayaç (00 00 00 02) birleşip 16 baytlık blok olur, 4×4
                    column-major matrise yerleşir. (Her işlemin görsel karşılığı.)
  1) Üretim       → sayaç bloğu, gizli anahtarla AES-256'dan geçer (kara kutu)
                    → 16 byte keystream çıkar. (İç round'lar ayrı animasyondadır.)
  2) Keystream    → çıkan 16 byte = şifrelemede kullanılan GERÇEK keystream;
                    deterministik, nonce'la değişir.
  3) Kullanım     → mesaj ⊕ keystream = şifreli metin; uzun mesajda sayaç artar.

Eski metin-duvarı referans diyaloğunun yerini alır.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QVBoxLayout, QWidget,
)

from ..base import ANIM_COLORS, cached_font
from arayuz.theme import MANAGER


# Sahne başlıkları ve vurgu renk anahtarları (soldan sağa üretim akışı).
_SCENE_TITLES = ["Sayaç bloğu", "Üretim", "Keystream", "Kullanım"]
_SCENE_COLOR_KEYS = ["accent_peach", "accent_blue", "accent_green", "accent_yellow"]
_SCENE_COUNT = 4

# Üstteki ilerleme şeridi geometrisi (mousePressEvent ile aynı kullanılır).
_STRIP_Y = 10
_STRIP_H = 40


def _matrix_from_bytes(data: bytes, shown: int = 16) -> list[list[str]]:
    """İlk ``shown`` baytı AES column-major 4×4 hex matrisine yerleştirir."""
    matrix = [["--"] * 4 for _ in range(4)]
    for i in range(min(16, len(data), shown)):
        matrix[i % 4][i // 4] = f"{data[i]:02x}"
    return matrix


class _KeystreamWizardWidget(QWidget):
    """Keystream'in nasıl üretildiğini dört sahnede manuel (tıkla-ilerle) gösterir."""

    def __init__(
        self,
        counter_block: bytes,
        keystream: bytes,
        nonce: bytes,
        rounds_data: list[dict] | None = None,   # uyumluluk için; artık kullanılmaz
        initial_state_hex: list[list[str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.counter_block = counter_block
        self.keystream = keystream
        self.nonce = nonce
        self._counter_matrix = (
            initial_state_hex if initial_state_hex else _matrix_from_bytes(counter_block)
        )
        self._keystream_matrix = _matrix_from_bytes(keystream)
        self._scene_index = 0
        self.setMinimumHeight(360)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ------------------------------------------------------------------
    # Manuel sahne gezintisi (otomatik oynatma yok)
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Sihirbazı ilk sahneye sıfırlar ('Baştan oynat')."""
        self._scene_index = 0
        self.update()

    def stop(self) -> None:
        """Geriye dönük uyumluluk: artık zamanlayıcı yok, no-op."""
        return

    def _scene(self) -> int:
        """Aktif sahne indeksini (0..3) verir."""
        return self._scene_index

    def jump_to_scene(self, scene: int) -> None:
        """Belirtilen sahneye atlar."""
        self._scene_index = max(0, min(_SCENE_COUNT - 1, scene))
        self.update()

    def _advance_scene(self) -> None:
        """Bir sonraki sahneye geçer (son sahnede durur)."""
        if self._scene_index < _SCENE_COUNT - 1:
            self._scene_index += 1
            self.update()

    # ------------------------------------------------------------------
    # Etkileşim: şerit kutuları 'buton', gövdeye tıklamak ise 'ileri'dir
    # ------------------------------------------------------------------

    def _strip_box_at(self, x: int, y: int) -> int | None:
        """(x, y) hangi ilerleme-şeridi kutusunun içinde? (yoksa None)."""
        if not (_STRIP_Y <= y <= _STRIP_Y + _STRIP_H):
            return None
        n = _SCENE_COUNT
        gap = 8
        bw = (self.width() - 16 - gap * (n - 1)) // n
        for i in range(n):
            bx = 8 + i * (bw + gap)
            if bx <= x <= bx + bw:
                return i
        return None

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        idx = self._strip_box_at(event.pos().x(), event.pos().y())
        if idx is not None:
            self.jump_to_scene(idx)
            return
        # Gövdeye tıklamak bir sonraki sahneye ilerletir.
        self._advance_scene()

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
            self._draw_scene_counter(p, body)
        elif scene == 1:
            self._draw_scene_generate(p, body)
        elif scene == 2:
            self._draw_scene_keystream(p, body)
        else:
            self._draw_scene_usage(p, body)
        p.end()

    def _draw_progress_strip(self, p: QPainter, W: int, active: int) -> None:
        """Üstte dört sahnelik ilerleme şeridini çizer; aktif sahne vurgulu.

        Kutular tıklanabilir (mousePressEvent) → küçük 'tıkla' ipucu yazılır.
        """
        n = _SCENE_COUNT
        gap = 8
        bw = (W - 16 - gap * (n - 1)) // n
        y = _STRIP_Y
        h = _STRIP_H
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

    # --- Sahne 0: Sayaç bloğunun üretimi (nonce ‖ sayaç → 16 byte → 4×4) ---

    def _draw_scene_counter(self, p: QPainter, area: QRect) -> None:
        cx = area.center().x()
        y = area.top() + 12

        p.setFont(cached_font("IBM Plex Sans", 11))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 22),
                   Qt.AlignmentFlag.AlignCenter,
                   "AES mesajı değil, SAYAÇ BLOĞUNU şifreler. Bu blok nasıl kurulur?")
        y += 30

        # 1) İşlem: birleştirme (nonce ‖ sayaç). İki grup ayrı renkte, aralarında ‖.
        peach = ANIM_COLORS["accent_peach"]
        blue = ANIM_COLORS["accent_blue"]
        nonce_part = self.counter_block[:12]
        ctr_part = self.counter_block[12:16]
        box_w = 30
        gap = 3
        sep_w = 26
        nonce_w = len(nonce_part) * (box_w + gap) - gap
        ctr_w = len(ctr_part) * (box_w + gap) - gap
        total = nonce_w + sep_w + ctr_w
        if total > area.width() - 16:                       # dar pencere: küçült
            box_w = max(20, (area.width() - 16 - sep_w) // 16 - gap)
            nonce_w = len(nonce_part) * (box_w + gap) - gap
            ctr_w = len(ctr_part) * (box_w + gap) - gap
            total = nonce_w + sep_w + ctr_w
        ox = max(8, cx - total // 2)

        # Grup etiketleri
        p.setFont(cached_font("IBM Plex Sans", 8, QFont.Weight.Bold))
        p.setPen(QColor(peach))
        p.drawText(QRect(ox, y, nonce_w, 14),
                   Qt.AlignmentFlag.AlignCenter, "nonce (12 byte)")
        p.setPen(QColor(blue))
        p.drawText(QRect(ox + nonce_w + sep_w, y, ctr_w, 14),
                   Qt.AlignmentFlag.AlignCenter, "sayaç (00 00 00 02)")
        y += 18

        self._draw_hex_boxes(p, ox, y, nonce_part, peach, box_w=box_w, gap=gap)
        p.setFont(cached_font("Georgia", 16, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(ox + nonce_w, y, sep_w, box_w),
                   Qt.AlignmentFlag.AlignCenter, "‖")
        self._draw_hex_boxes(p, ox + nonce_w + sep_w, y, ctr_part, blue,
                             box_w=box_w, gap=gap)
        y += box_w + 8

        p.setFont(cached_font("Courier New", 10, QFont.Weight.Bold))
        p.setPen(QColor(peach))
        p.drawText(QRect(area.left(), y, area.width(), 18),
                   Qt.AlignmentFlag.AlignCenter,
                   "=  sayaç bloğu (16 byte)  ↓")
        # Matrisin kendi başlığı (y-16'da çizilir) bu satırla çakışmasın diye
        # yeterli dikey boşluk bırakılır (eski 26 → 42).
        y += 42

        # 2) İşlem: 16 baytın 4×4 column-major matrise yerleşmesi
        self._draw_matrix(p, cx - 92, y, self._counter_matrix,
                          peach, title="4×4 (column-major)")
        y += 4 * 42 + 3 * 4 + 22

        p.setFont(cached_font("IBM Plex Sans", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 40),
                   Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                   "nonce her şifrelemede rastgele üretilir (değerler bu yüzden "
                   "'rastgele' görünür); 00 00 00 02 ise GCM'de ilk veri bloğunun "
                   "sayaç değeridir.")

    # --- Sahne 1: Üretim (AES-256 kara kutu, round'lar YOK) ----------

    def _draw_scene_generate(self, p: QPainter, area: QRect) -> None:
        y = area.top() + 14

        p.setFont(cached_font("IBM Plex Sans", 11))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 40),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                   | Qt.TextFlag.TextWordWrap,
                   "AES-256, sayaç bloğunu gizli oturum anahtarıyla şifreler. "
                   "Çıkan 16 byte keystream'dir.")
        y += 50

        cell = 26
        mat_w = 4 * cell + 3 * 4
        box_w = 130
        arrow_w = 36
        total = mat_w + arrow_w + box_w + arrow_w + mat_w
        ox = max(8, area.center().x() - total // 2)
        row_y = y + 20

        # 1) Sayaç bloğu matrisi
        self._draw_matrix(p, ox, row_y, self._counter_matrix,
                          ANIM_COLORS["accent_peach"], title="sayaç bloğu", cell=cell)
        x = ox + mat_w

        # → ok
        self._draw_arrow(p, x, row_y + mat_w // 2, arrow_w)
        x += arrow_w

        # 2) AES-256 kara kutu (anahtarla)
        self._draw_aes_box(p, x, row_y, box_w, 4 * cell + 3 * 4)
        x += box_w

        # → ok
        self._draw_arrow(p, x, row_y + mat_w // 2, arrow_w)
        x += arrow_w

        # 3) Keystream matrisi (tam dolu)
        self._draw_matrix(p, x, row_y, self._keystream_matrix,
                          ANIM_COLORS["accent_green"], title="keystream", cell=cell)

    # --- Sahne 2: Keystream sonucu -----------------------------------

    def _draw_scene_keystream(self, p: QPainter, area: QRect) -> None:
        cx = area.center().x()
        y = area.top() + 14

        p.setFont(cached_font("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(area.left(), y, area.width(), 24),
                   Qt.AlignmentFlag.AlignCenter,
                   "Çıkan 16 byte  =  KEYSTREAM")
        y += 34

        self._draw_matrix(p, cx - 92, y, self._keystream_matrix,
                          ANIM_COLORS["accent_green"])
        # 4×4 (cell 42) matrisin tam yüksekliği + başlık payı.
        y += 4 * 42 + 3 * 4 + 22

        p.setFont(cached_font("IBM Plex Sans", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 22),
                   Qt.AlignmentFlag.AlignCenter,
                   "Bu, şifrelemende kullanılan GERÇEK keystream.")
        y += 28

        p.setFont(cached_font("IBM Plex Sans", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 40),
                   Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                   "Aynı nonce ve anahtarla her zaman aynı keystream üretilir. "
                   "Nonce her şifrelemede yeni ve rastgele olduğu için keystream "
                   "asla tekrar etmez.")

    # --- Sahne 3: Kullanım (mesaj ⊕ keystream) -----------------------

    def _draw_scene_usage(self, p: QPainter, area: QRect) -> None:
        cx = area.center().x()
        y = area.top() + 16

        p.setFont(cached_font("IBM Plex Sans", 11))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 22),
                   Qt.AlignmentFlag.AlignCenter,
                   "Keystream üretildi; mesaj artık onunla XOR'lanır:")
        y += 40

        p.setFont(cached_font("Courier New", 13, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(area.left(), y, area.width(), 28),
                   Qt.AlignmentFlag.AlignCenter,
                   "mesaj   ⊕   keystream   =   şifreli metin")
        y += 42

        # Aşağıdaki satır KEYSTREAM'dir (şifreli metin değil) — kullanıcı bunu
        # sonuç sanmasın diye açıkça etiketlenir. Şifreli metin, bu keystream
        # mesajla XOR'lanınca elde edilir ve ana ekrandaki matriste gösterilir.
        p.setFont(cached_font("IBM Plex Sans", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(area.left(), y, area.width(), 16),
                   Qt.AlignmentFlag.AlignCenter, "keystream (16 byte)")
        y += 20

        self._draw_hex_row(p, cx, y, self.keystream, 16,
                           ANIM_COLORS["accent_green"])
        y += 64

        p.setFont(cached_font("IBM Plex Sans", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(area.left() + 12, y, area.width() - 24, 56),
                   Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                   "Bu satır keystream'dir; mesaj baytlarıyla XOR'lanınca "
                   "şifreli metni verir (ana ekrandaki matriste gösterilir). "
                   "Mesaj 16 bayttan uzunsa sayaç birer artar (00 00 00 03, "
                   "00 00 00 04 …) ve sonraki her blok kendi keystream'ini üretir.")

    # ------------------------------------------------------------------
    # Çizim yardımcıları
    # ------------------------------------------------------------------

    def _draw_arrow(self, p: QPainter, x: int, mid_y: int, w: int) -> None:
        """Aşamalar arası yatay '→' oku."""
        color = QColor(ANIM_COLORS["accent_yellow"])
        p.setFont(cached_font("Georgia", 18, QFont.Weight.Bold))
        p.setPen(color)
        p.drawText(QRect(x, mid_y - 16, w, 32), Qt.AlignmentFlag.AlignCenter, "→")

    def _draw_aes_box(self, p: QPainter, x: int, y: int, w: int, h: int) -> None:
        """'AES-256' kara kutusu — gizli anahtar ipucuyla."""
        color = QColor(ANIM_COLORS["accent_blue"])
        bg = QColor(color)
        bg.setAlphaF(0.22)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(color, 2))
        p.drawRoundedRect(x, y, w, h, 8, 8)
        p.setFont(cached_font("Georgia", 12, QFont.Weight.Bold))
        p.setPen(color)
        p.drawText(QRect(x, y + h // 2 - 18, w, 22),
                   Qt.AlignmentFlag.AlignCenter, "AES-256")
        p.setFont(cached_font("IBM Plex Sans", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(x + 4, y + h // 2 + 6, w - 8, 18),
                   Qt.AlignmentFlag.AlignCenter, "🔑 gizli anahtar")

    def _draw_hex_boxes(
        self, p: QPainter, x0: int, y: int, data: bytes, color_hex: str,
        *, box_w: int = 30, gap: int = 3,
    ) -> None:
        """``data`` baytlarını ``x0``'dan başlayan tek satır hex kutusu olarak çizer."""
        color = QColor(color_hex)
        for i, b in enumerate(data):
            x = x0 + i * (box_w + gap)
            bg = QColor(color); bg.setAlphaF(0.18)
            p.setBrush(QBrush(bg))
            p.setPen(QPen(color, 1))
            p.drawRoundedRect(x, y, box_w, box_w, 4, 4)
            p.setFont(cached_font("Courier New", max(8, box_w // 3),
                                  QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x, y, box_w, box_w),
                       Qt.AlignmentFlag.AlignCenter, f"{b:02x}")

    def _draw_hex_row(
        self, p: QPainter, cx: int, y: int, data: bytes, shown: int, color_hex: str,
    ) -> None:
        """16 baytı küçük hex kutuları satırında çizer (ilk ``shown`` tanesi görünür)."""
        n = 16
        bw, gap = 30, 3
        total = n * bw + (n - 1) * gap
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
        *, title: str | None = None, cell: int = 42,
    ) -> None:
        """4×4 hex matrisini kart olarak çizer."""
        color = QColor(color_hex)
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
                value = matrix[r][c]
                dim = value == "--"
                bg = QColor(color)
                bg.setAlphaF(0.04 if dim else 0.16)
                p.setBrush(QBrush(bg))
                p.setPen(QPen(QColor(ANIM_COLORS["border"] if dim else color_hex), 1))
                p.drawRoundedRect(cxp, cyp, cell, cell, 5, 5)
                p.setFont(cached_font("Courier New", max(9, cell // 4),
                                      QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["text_muted"] if dim
                                else ANIM_COLORS["text_primary"]))
                p.drawText(QRect(cxp, cyp, cell, cell),
                           Qt.AlignmentFlag.AlignCenter, value)


class _KeystreamReferenceDialog(QDialog):
    """Keystream sihirbazını barındıran ince, metin-duvarsız diyalog.

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
        self._build_ui(initial_state_hex)
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
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)

    def _build_ui(self, initial_state_hex: list[list[str]] | None) -> None:
        """Başlık + sihirbaz + 'baştan oynat' düğmesini kurar."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)

        self.title_label = QLabel("Keystream nedir, nasıl üretilir?")
        self.title_label.setFont(QFont("Georgia", 15, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # NOT: "İpucu" satırı ve "Baştan oynat" düğmesi kaldırıldı — gezinme
        # tamamen üstteki sahne kutularıyla (tıkla-seç) yapılıyor, otomatik
        # oynatma/animasyon durumu yok; bu yüzden ipucu ve baştan-oynat gereksiz.
        self.wizard = _KeystreamWizardWidget(
            self.counter_block, self.keystream, self.nonce,
            initial_state_hex=initial_state_hex, parent=self,
        )
        layout.addWidget(self.wizard, stretch=1)

        self.wizard.start()

    def _resize_to_available_screen(self) -> None:
        """Diyaloğu mevcut ekranı taşırmadan boyutlandırır."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(840, 620)
            return
        available = screen.availableGeometry()
        self.resize(
            min(920, int(available.width() * 0.80)),
            min(660, int(available.height() * 0.80)),
        )

    def restyle(self) -> None:
        """Açık diyaloğu aktif uygulama temasına geçirir."""
        self.setStyleSheet(
            f"QDialog {{ background: {ANIM_COLORS['bg_panel']}; }}"
        )
        self.title_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_yellow']}; background: transparent;"
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
