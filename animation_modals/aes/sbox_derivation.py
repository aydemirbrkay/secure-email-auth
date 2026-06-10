"""S-Box türetimini adım adım canlandıran animasyon widget'ı.

Bir byte'ın S-Box değerine nasıl dönüştüğünü dört kutu hâlinde gösterir:
Girdi → Çarpımsal Ters (GF(2⁸)) → Affine Dönüşüm → Sonuç. Kutular tick
döngüsünde sırayla parlar; mesajdan gelen SubBytes eşlemeleri verildiğinde
döngü sonunda bir sonraki byte'a geçer (projedeki diğer animasyonlar gibi
kullanıcının mesajına göre dinamik). Tabloda bir hücreye tıklanınca o byte'a
kilitlenir.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygon
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..aes_pure import derive_sbox_value
from ..base import ANIM_COLORS, get_animation_tick_ms

# Her kutunun başlığı ve vurgu rengi (soldan sağa türetim akışı).
_STEP_TITLES = ["Girdi", "Çarpımsal Ters", "Affine Dönüşüm", "Sonuç"]
_STEP_COLOR_KEYS = ["accent_blue", "accent_mauve", "accent_yellow", "accent_green"]

# Her adım için kaç tick beklenir (sade tempo; hareket azaltma ile ölçeklenir).
_TICKS_PER_STEP = 8
_STEP_COUNT = 4
_HOLD_TICKS = 10  # Son adımda, sonraki byte'a geçmeden önce bekleme.
_CYCLE_TICKS = _STEP_COUNT * _TICKS_PER_STEP + _HOLD_TICKS


class _SBoxDerivationWidget(QWidget):
    """S-Box türetimini dört kutuyla canlandıran widget.

    ``mappings`` verildiğinde mesajın SubBytes girdileri arasında otomatik
    gezer; ``set_byte`` ile tek bir byte'a kilitlenir (otomatik gezinme durur).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mapping_bytes: list[int] = []
        self._mapping_index = 0
        self._byte = 0x53  # Anlamlı varsayılan (ters ve affine örneği belirgin).
        self._locked = False
        self._tick = 0
        self.setMinimumSize(420, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    # ------------------------------------------------------------------
    # Genel API
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
        """Şu an parlayan adımın indeksini (0-3) döndürür; bekleme fazında 3 kalır."""
        return min(self._tick // _TICKS_PER_STEP, _STEP_COUNT - 1)

    def _step_values(self) -> list[str]:
        """Dört kutuda gösterilecek hex metinleri sırayla döndürür."""
        d = derive_sbox_value(self._byte)
        return [
            f"{self._byte:02x}",
            f"{d.inverse:02x}",
            f"{d.affine_const:02x} ⊕ …",
            f"{d.result:02x}",
        ]

    # ------------------------------------------------------------------
    # Çizim
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Dört türetim kutusunu, aralarındaki okları ve aktif adımı çizer."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        d = derive_sbox_value(self._byte)
        active = self._active_step()
        values = self._step_values()

        title_h = 30
        p.setFont(QFont("IBM Plex Sans", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(
            QRect(0, 6, W, title_h),
            Qt.AlignmentFlag.AlignCenter,
            f"S-Box değeri nasıl üretilir?  (örnek: {self._byte:02x})",
        )

        margin = 24
        gap = 26
        box_w = max(70, min(150, (W - 2 * margin - 3 * gap) // 4))
        box_h = max(60, min(96, (H - title_h - 60) // 2))
        total_w = 4 * box_w + 3 * gap
        ox = (W - total_w) // 2
        oy = title_h + 40

        for i in range(4):
            x = ox + i * (box_w + gap)
            lit = i <= active
            color = QColor(ANIM_COLORS[_STEP_COLOR_KEYS[i]])
            fill = QColor(color)
            fill.setAlpha(60 if lit else 18)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(color if lit else QColor(ANIM_COLORS["border"]), 2 if i == active else 1))
            p.drawRoundedRect(x, oy, box_w, box_h, 8, 8)

            p.setFont(QFont("IBM Plex Sans", 8, QFont.Weight.Bold))
            p.setPen(color)
            p.drawText(
                QRect(x + 2, oy + 4, box_w - 4, 20),
                Qt.AlignmentFlag.AlignCenter,
                _STEP_TITLES[i],
            )
            p.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
            p.setPen(
                QColor(ANIM_COLORS["text_primary"]) if lit
                else QColor(ANIM_COLORS["text_muted"])
            )
            p.drawText(
                QRect(x, oy + box_h // 2 - 6, box_w, box_h // 2),
                Qt.AlignmentFlag.AlignCenter,
                values[i],
            )

            # Kutular arası ok (son kutudan sonra çizilmez).
            if i < 3:
                ax = x + box_w
                ay = oy + box_h // 2
                arrow_lit = (i + 1) <= active
                p.setPen(QPen(
                    color if arrow_lit else QColor(ANIM_COLORS["border"]), 2
                ))
                p.drawLine(ax + 4, ay, ax + gap - 6, ay)
                head = QPolygon([
                    QPoint(ax + gap - 6, ay),
                    QPoint(ax + gap - 12, ay - 5),
                    QPoint(ax + gap - 12, ay + 5),
                ])
                p.setBrush(QBrush(
                    color if arrow_lit else QColor(ANIM_COLORS["border"])
                ))
                p.drawPolygon(head)

        # Aktif adımın altında kısa açıklama (öğrenci diline indirgenmiş).
        notes = [
            f"Girdi byte: {self._byte:02x}",
            (
                "0x00'ın tersi yoktur; 0 alınır."
                if self._byte == 0
                else f"GF(2⁸): {self._byte:02x} · {d.inverse:02x} = 01 → tersi {d.inverse:02x}"
            ),
            f"Ters değer, bit-döndürmeli XOR ve {d.affine_const:02x} sabitiyle birleşir.",
            f"S[{self._byte >> 4:X},{self._byte & 0xF:X}] = {d.result:02x}",
        ]
        p.setFont(QFont("IBM Plex Sans", 10))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(
            QRect(margin, oy + box_h + 22, W - 2 * margin, 48),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            notes[active],
        )
