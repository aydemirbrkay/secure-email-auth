"""S-Box türetimini adım adım canlandıran çok sahneli sihirbaz widget'ı.

Bir byte'ın S-Box değerine nasıl dönüştüğünü dört adımda anlatır:
Girdi → Çarpımsal Ters (GF(2⁸)) → Affine Dönüşüm → Sonuç. Üstte dört
kutuluk bir ilerleme şeridi adımları gösterir; altta o an aktif olan
adımın tam-ekran sahnesi canlanır. İzleyicinin ne çarpımsal tersi ne de
affine dönüşümü bildiği varsayılarak her adım görsel olarak açılır.

Adımlar tick döngüsünde otomatik ilerler; mesajdan gelen SubBytes
eşlemeleri verildiğinde döngü sonunda bir sonraki byte'a geçer (projedeki
diğer animasyonlar gibi kullanıcının mesajına göre dinamik). Tabloda bir
hücreye tıklanınca o byte'a kilitlenir.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygon
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..aes_pure import derive_sbox_value, _gf_mul
from ..base import ANIM_COLORS, get_animation_tick_ms

# Her adımın başlığı ve vurgu rengi (soldan sağa türetim akışı).
_STEP_TITLES = ["Girdi", "Çarpımsal Ters", "Affine Dönüşüm", "Sonuç"]
_STEP_COLOR_KEYS = ["accent_blue", "accent_mauve", "accent_yellow", "accent_green"]
_STEP_COUNT = 4

# Her adımın tick bütçesi (sade tempo; hareket azaltma ile ölçeklenir).
_INTRO_TICKS = 6     # Adım 0: girdi belirir.
_INV_TICKS = 16      # Adım 1: ters kavramı + a·x=01 doğrulaması.
_BIT_TICKS = 2       # Affine'de her çıkış biti için alt-tick.
_AFFINE_TICKS = 8 * _BIT_TICKS  # Adım 2: 8 çıkış biti tek tek.
_RESULT_TICKS = 8    # Adım 3: sonuç + S[satır,sütun] şeması.
_TRANSITION_TICKS = 3  # Adımlar arası "uçan byte" kaydırma süresi.
_HOLD_TICKS = 8      # Son adımdan sonra, sonraki byte'a geçmeden bekleme.

# Adım süreleri ve aralarındaki geçişler tek bir zaman çizelgesine dizilir:
#   [intro] (geçiş) [inverse] (geçiş) [affine] (geçiş) [result] [hold]
_STEP_TICKS = [_INTRO_TICKS, _INV_TICKS, _AFFINE_TICKS, _RESULT_TICKS]


def _build_timeline() -> tuple[list[tuple[int, int]], list[tuple[int, int]], int]:
    """Adım ve geçiş pencerelerini kümülatif tick aralıklarına çevirir.

    Dönüş: (adım_aralıkları, geçiş_aralıkları, toplam_tick). Her aralık
    ``(başlangıç, bitiş)`` yarı-açık tick penceresidir. Adım i bittikten
    sonra (son adım hariç) bir geçiş penceresi gelir.
    """
    step_bounds: list[tuple[int, int]] = []
    transition_bounds: list[tuple[int, int]] = []
    cursor = 0
    for i, dur in enumerate(_STEP_TICKS):
        step_bounds.append((cursor, cursor + dur))
        cursor += dur
        if i < _STEP_COUNT - 1:
            transition_bounds.append((cursor, cursor + _TRANSITION_TICKS))
            cursor += _TRANSITION_TICKS
    cursor += _HOLD_TICKS  # Son adımdan sonra bekleme.
    return step_bounds, transition_bounds, cursor


_STEP_BOUNDS, _TRANSITION_BOUNDS, _CYCLE_TICKS = _build_timeline()


class _SBoxDerivationWidget(QWidget):
    """S-Box türetimini çok sahneli sihirbazla canlandıran widget.

    ``mappings`` verildiğinde mesajın SubBytes girdileri arasında otomatik
    gezer; ``set_byte`` ile tek bir byte'a kilitlenir (otomatik gezinme durur).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mapping_bytes: list[int] = []
        self._mapping_index = 0
        self._byte = 0xe5  # Anlamlı varsayılan (ters ve affine örneği belirgin).
        self._locked = False
        self._tick = 0
        self.setMinimumSize(460, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    # ------------------------------------------------------------------
    # Genel API (sbox_dialog.py bu imzalara bağımlıdır)
    # ------------------------------------------------------------------

    def set_mappings(self, mappings: list[tuple[str, str]]) -> None:
        """Mesajın SubBytes eşlemelerini verir; ilk byte'tan gezinmeye başlar.

        ``mappings`` ``(girdi_hex, sonuc_hex)`` ikililerinden oluşur; yalnızca
        benzersiz girdiler, görülme sırasına göre alınır. Liste boşsa varsayılan
        byte korunur.
        """
        seen: list[int] = []
        for source, _ in mappings:
            value = int(source, 16)
            if value not in seen:
                seen.append(value)
        self._mapping_bytes = seen
        self._mapping_index = 0
        self._locked = False
        if seen:
            self._byte = seen[0]
        self._tick = 0
        self.update()

    def set_byte(self, byte: int) -> None:
        """Tek bir byte'a kilitlenir (tabloya tıklanınca); otomatik gezinmeyi durdurur."""
        if not 0 <= byte <= 255:
            raise ValueError("S-Box türetimi için 0-255 arası bir byte gerekli")
        self._byte = byte
        self._locked = True
        self._tick = 0
        self.update()

    @property
    def current_byte(self) -> int:
        """Şu an türetimi gösterilen byte."""
        return self._byte

    @property
    def current_derivation(self):
        """Şu anki byte'ın ``SBoxDerivation`` ara değerleri (canlı hesaplanır)."""
        return derive_sbox_value(self._byte)

    def start(self) -> None:
        """Animasyon zamanlayıcısını başlatır (sayfa görünür olunca)."""
        self._timer.start(get_animation_tick_ms(90))

    def stop(self) -> None:
        """Animasyon zamanlayıcısını durdurur (sayfa gizlenince/kapanınca)."""
        self._timer.stop()

    # ------------------------------------------------------------------
    # İç döngü
    # ------------------------------------------------------------------

    def _advance(self) -> None:
        """Tek tick ilerletir; döngü tamamlanınca (kilitli değilse) sonraki byte'a geçer."""
        self._tick += 1
        if self._tick >= _CYCLE_TICKS:
            self._tick = 0
            if not self._locked and len(self._mapping_bytes) > 1:
                self._mapping_index = (self._mapping_index + 1) % len(self._mapping_bytes)
                self._byte = self._mapping_bytes[self._mapping_index]
        self.update()

    def _active_step(self) -> int:
        """Şu an gösterilen adımın indeksini (0-3) döndürür.

        Geçiş ve bekleme pencerelerinde, bir önceki tamamlanan adımda kalınır.
        """
        for i, (start, end) in enumerate(_STEP_BOUNDS):
            if self._tick < end:
                return i
        return _STEP_COUNT - 1

    def _step_local_progress(self, step: int) -> float:
        """Verilen adımın kendi içindeki ilerlemeyi [0,1] aralığında döndürür."""
        start, end = _STEP_BOUNDS[step]
        if self._tick <= start:
            return 0.0
        if self._tick >= end:
            return 1.0
        return (self._tick - start) / max(1, end - start)

    def _active_transition(self) -> tuple[int, float] | None:
        """Bir geçiş penceresindeysek (kaynak_adım, ilerleme) döndürür, değilse None."""
        for i, (start, end) in enumerate(_TRANSITION_BOUNDS):
            if start <= self._tick < end:
                return i, (self._tick - start) / max(1, end - start)
        return None

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Başlık, üst ilerleme şeridi ve aktif adımın alt sahnesini çizer."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Başlık.
        title_h = 30
        p.setFont(QFont("IBM Plex Sans", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(
            QRect(0, 6, W, title_h),
            Qt.AlignmentFlag.AlignCenter,
            f"S-Box değeri nasıl üretilir?  (örnek: {self._byte:02x})",
        )

        # Üst ilerleme şeridi.
        strip_top = title_h + 10
        strip_h = 70
        self._paint_progress_strip(p, QRect(0, strip_top, W, strip_h))

        # Alt sahne alanı.
        scene_top = strip_top + strip_h + 16
        scene_rect = QRect(20, scene_top, W - 40, max(60, H - scene_top - 18))

        transition = self._active_transition()
        if transition is not None:
            self._paint_transition(p, scene_rect, *transition)
            return

        step = self._active_step()
        if step == 0:
            self._paint_scene_input(p, scene_rect)
        elif step == 1:
            self._paint_scene_inverse(p, scene_rect)
        elif step == 2:
            self._paint_scene_affine(p, scene_rect)
        else:
            self._paint_scene_result(p, scene_rect)

    # ------------------------------------------------------------------
    # Üst ilerleme şeridi
    # ------------------------------------------------------------------

    def _paint_progress_strip(self, p: QPainter, rect: QRect) -> None:
        """Dört adım kutusunu ve aralarındaki okları çizer; aktif adım parlar."""
        active = self._active_step()
        margin = 24
        gap = 22
        box_w = max(60, min(150, (rect.width() - 2 * margin - 3 * gap) // 4))
        box_h = min(58, rect.height())
        total_w = 4 * box_w + 3 * gap
        ox = rect.left() + (rect.width() - total_w) // 2
        oy = rect.top() + (rect.height() - box_h) // 2

        d = derive_sbox_value(self._byte)
        values = [
            f"{self._byte:02x}",
            f"{d.inverse:02x}",
            "…",
            f"{d.result:02x}",
        ]

        for i in range(4):
            x = ox + i * (box_w + gap)
            done = i < active
            lit = i <= active
            color = QColor(ANIM_COLORS[_STEP_COLOR_KEYS[i]])
            fill = QColor(color)
            fill.setAlpha(70 if done else (50 if lit else 16))
            p.setBrush(QBrush(fill))
            p.setPen(QPen(color if lit else QColor(ANIM_COLORS["border"]), 2 if i == active else 1))
            p.drawRoundedRect(x, oy, box_w, box_h, 8, 8)

            p.setFont(QFont("IBM Plex Sans", 8, QFont.Weight.Bold))
            p.setPen(color)
            p.drawText(
                QRect(x + 2, oy + 4, box_w - 4, 18),
                Qt.AlignmentFlag.AlignCenter,
                _STEP_TITLES[i],
            )
            p.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
            p.setPen(
                QColor(ANIM_COLORS["text_primary"]) if lit
                else QColor(ANIM_COLORS["text_muted"])
            )
            p.drawText(
                QRect(x, oy + box_h // 2 - 4, box_w, box_h // 2),
                Qt.AlignmentFlag.AlignCenter,
                values[i] if i != 2 else ("✓" if lit else "…"),
            )

            if i < 3:
                ax = x + box_w
                ay = oy + box_h // 2
                arrow_lit = (i + 1) <= active
                self._paint_arrow(p, ax + 3, ay, ax + gap - 5, ay,
                                  color if arrow_lit else QColor(ANIM_COLORS["border"]))

    def _paint_arrow(self, p: QPainter, x0: int, y0: int, x1: int, y1: int,
                     color: QColor) -> None:
        """(x0,y0)'dan (x1,y1)'e yatay bir ok çizer (ok başı sağda)."""
        p.setPen(QPen(color, 2))
        p.drawLine(x0, y0, x1, y1)
        head = QPolygon([
            QPoint(x1, y1),
            QPoint(x1 - 6, y1 - 5),
            QPoint(x1 - 6, y1 + 5),
        ])
        p.setBrush(QBrush(color))
        p.drawPolygon(head)

    # ------------------------------------------------------------------
    # Sahne 0 — Girdi
    # ------------------------------------------------------------------

    def _paint_scene_input(self, p: QPainter, rect: QRect) -> None:
        """Girdi byte'ını ve hex hanelerinin satır/sütun anlamını gösterir."""
        progress = self._step_local_progress(0)
        color = QColor(ANIM_COLORS["accent_blue"])
        hi = self._byte >> 4
        lo = self._byte & 0xF

        cx = rect.center().x()
        box = 64
        gap = 10
        top = rect.top() + 20
        # İki hex hanesi ayrı kutularda.
        x0 = cx - box - gap // 2
        x1 = cx + gap // 2
        for idx, (x, digit, label) in enumerate((
            (x0, f"{hi:X}", "satır"),
            (x1, f"{lo:X}", "sütun"),
        )):
            shown = progress > (idx * 0.4)
            fill = QColor(color)
            fill.setAlpha(60 if shown else 14)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(color if shown else QColor(ANIM_COLORS["border"]), 2))
            p.drawRoundedRect(x, top, box, box, 8, 8)
            p.setFont(QFont("Courier New", 26, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]) if shown
                     else QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x, top, box, box), Qt.AlignmentFlag.AlignCenter, digit)
            p.setFont(QFont("IBM Plex Sans", 9))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(x, top + box + 4, box, 18),
                       Qt.AlignmentFlag.AlignCenter, label)

        note = (
            f"Girdi byte'ı: {self._byte:02x}  —  ilk hex hanesi satırı, "
            f"ikinci hex hanesi sütunu seçer."
        )
        self._paint_note(p, rect, note)

    # ------------------------------------------------------------------
    # Sahne 1 — Çarpımsal Ters (kavram + a·x=01 doğrulaması)
    # ------------------------------------------------------------------

    def _paint_scene_inverse(self, p: QPainter, rect: QRect) -> None:
        """Çarpımsal ters kavramını kurar ve GF(2⁸)'de a·x=01 ile doğrular."""
        d = derive_sbox_value(self._byte)
        progress = self._step_local_progress(1)

        if self._byte == 0:
            self._paint_centered_big(p, rect, "00", QColor(ANIM_COLORS["accent_mauve"]))
            self._paint_note(
                p, rect,
                "0x00'ın çarpımsal tersi yoktur; AES sözleşmesiyle 0 alınır.",
            )
            return

        # Faz eşikleri (adım içi ilerlemeye göre).
        show_inverse = progress >= 0.35   # ? yerine ters belirir.
        show_verify = progress >= 0.65    # GF çarpımı 01 doğrulanır.

        mauve = QColor(ANIM_COLORS["accent_mauve"])
        green = QColor(ANIM_COLORS["accent_green"])

        # a · x = 01 eşitliği (ortada büyük).
        cy = rect.top() + 46
        p.setFont(QFont("Courier New", 24, QFont.Weight.Bold))
        a_txt = f"{self._byte:02x}"
        x_txt = f"{d.inverse:02x}" if show_inverse else "?"
        self._paint_equation(
            p, rect.center().x(), cy,
            [(a_txt, QColor(ANIM_COLORS["accent_blue"])),
             (" · ", QColor(ANIM_COLORS["text_secondary"])),
             (x_txt, green if show_inverse else mauve),
             (" = ", QColor(ANIM_COLORS["text_secondary"])),
             ("01", QColor(ANIM_COLORS["text_primary"]))],
        )

        # Açıklama: önce kavram, sonra doğrulama.
        if show_verify:
            check = _gf_mul(self._byte, d.inverse)
            note = (
                f"Doğrulama (GF(2⁸)): {self._byte:02x} · {d.inverse:02x} = "
                f"{check:02x} ✓  →  {d.inverse:02x}, {self._byte:02x}'in tersidir."
            )
            p.setPen(green)
        elif show_inverse:
            note = f"Bu eşi {d.inverse:02x}; çarpımları gerçekten 01 mi? Doğrulayalım…"
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        else:
            note = (
                "GF(2⁸)'de 0 dışında her sayının, çarpımı 01 veren tek bir eşi "
                "(çarpımsal tersi) vardır. Bu eşi arıyoruz."
            )
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        self._paint_note(p, rect, note, set_pen=False)

    # ------------------------------------------------------------------
    # Sahne 2 — Affine (geçici sade gösterim; Aşama 4'te bit-bit XOR olacak)
    # ------------------------------------------------------------------

    def _paint_scene_affine(self, p: QPainter, rect: QRect) -> None:
        """Affine dönüşümünü gösterir (bit-bit XOR akışı sonraki aşamada)."""
        d = derive_sbox_value(self._byte)
        yellow = QColor(ANIM_COLORS["accent_yellow"])
        cy = rect.top() + 46
        p.setFont(QFont("Courier New", 22, QFont.Weight.Bold))
        self._paint_equation(
            p, rect.center().x(), cy,
            [("affine(", QColor(ANIM_COLORS["text_secondary"])),
             (f"{d.inverse:02x}", QColor(ANIM_COLORS["accent_mauve"])),
             (") = ", QColor(ANIM_COLORS["text_secondary"])),
             (f"{d.result:02x}", yellow)],
        )
        self._paint_note(
            p, rect,
            f"Ters değer, bit-döndürmeli XOR ve {d.affine_const:02x} sabitiyle "
            f"birleşerek S-Box çıktısını verir.",
        )

    # ------------------------------------------------------------------
    # Sahne 3 — Sonuç
    # ------------------------------------------------------------------

    def _paint_scene_result(self, p: QPainter, rect: QRect) -> None:
        """Sonuç byte'ını ve S[satır,sütun] şemasını parlatır."""
        d = derive_sbox_value(self._byte)
        self._paint_centered_big(p, rect, f"{d.result:02x}",
                                 QColor(ANIM_COLORS["accent_green"]))
        self._paint_note(
            p, rect,
            f"S[{self._byte >> 4:X},{self._byte & 0xF:X}] = {d.result:02x}  "
            f"(girdi {self._byte:02x} → S-Box çıktısı {d.result:02x})",
        )

    # ------------------------------------------------------------------
    # Sahne geçişleri (geçici: Aşama 5'te "uçan byte" olacak)
    # ------------------------------------------------------------------

    def _paint_transition(self, p: QPainter, rect: QRect, source_step: int,
                          t: float) -> None:
        """Geçiş penceresinde kaynak adımın çıktısını gösterir.

        Şimdilik kaynak adımın bitmiş hâlini çizer; "uçan byte" kaydırma
        animasyonu sonraki aşamada eklenecek.
        """
        if source_step == 0:
            self._paint_scene_input(p, rect)
        elif source_step == 1:
            self._paint_scene_inverse(p, rect)
        else:
            self._paint_scene_affine(p, rect)

    # ------------------------------------------------------------------
    # Ortak çizim yardımcıları
    # ------------------------------------------------------------------

    def _paint_centered_big(self, p: QPainter, rect: QRect, text: str,
                            color: QColor) -> None:
        """Ortada büyük bir byte kutusu çizer (sonuç/özel durumlar için)."""
        box = 80
        x = rect.center().x() - box // 2
        y = rect.top() + 24
        fill = QColor(color)
        fill.setAlpha(55)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(color, 2))
        p.drawRoundedRect(x, y, box, box, 10, 10)
        p.setFont(QFont("Courier New", 30, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(x, y, box, box), Qt.AlignmentFlag.AlignCenter, text)

    def _paint_equation(self, p: QPainter, cx: int, cy: int,
                        parts: list[tuple[str, QColor]]) -> None:
        """Renkli parçalardan oluşan tek satırlık bir ifadeyi yatayda ortalar.

        ``parts`` ``(metin, renk)`` ikilileridir; çağırmadan önce font ayarlanır.
        """
        fm = p.fontMetrics()
        total = sum(fm.horizontalAdvance(text) for text, _ in parts)
        x = cx - total // 2
        for text, color in parts:
            p.setPen(color)
            w = fm.horizontalAdvance(text)
            p.drawText(QRect(x, cy - fm.height() // 2, w, fm.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            x += w

    def _paint_note(self, p: QPainter, rect: QRect, text: str,
                    set_pen: bool = True) -> None:
        """Sahnenin altında, sarmalı kısa bir açıklama metni çizer."""
        p.setFont(QFont("IBM Plex Sans", 10))
        if set_pen:
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(
            QRect(rect.left() + 4, rect.bottom() - 60, rect.width() - 8, 56),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            text,
        )
