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

from ..aes_pure import derive_sbox_value, _gf_mul, gf_inverse_exponent_steps
from ..base import ANIM_COLORS, get_animation_tick_ms

# Her adımın başlığı ve vurgu rengi (soldan sağa türetim akışı).
_STEP_TITLES = ["Girdi", "Çarpımsal Ters", "Affine Dönüşüm", "Sonuç"]
_STEP_COLOR_KEYS = ["accent_blue", "accent_mauve", "accent_yellow", "accent_green"]
_STEP_COUNT = 4

# Her adımın tick bütçesi (sakin tempo; her adım rahat takip edilsin, hareket
# azaltma ile ayrıca ölçeklenir). Affine bitleri tek tek görünür kalsın diye
# _BIT_TICKS bilhassa yüksek tutulur.
_INTRO_TICKS = 8      # Adım 0: girdi belirir.
_INV_TICKS = 40       # Adım 1: a⁻¹ = a²⁵⁴ üs alma — kareleme zinciri (a,a²,…,a¹²⁸)
                      #         + seçili karelerin çarpımı + a·a⁻¹=01 doğrulaması.
_BIT_TICKS = 5        # Affine'de her çıkış biti için alt-tick (okunaklı tempo).
_AFFINE_TICKS = 8 * _BIT_TICKS  # Adım 2: 8 çıkış biti tek tek (8×5=40 tick).
_RESULT_TICKS = 12    # Adım 3: sonuç + S[satır,sütun] şeması.
_TRANSITION_TICKS = 5  # Adımlar arası "uçan byte" kaydırma süresi.
_HOLD_TICKS = 12      # Son adımdan sonra, sonraki byte'a geçmeden bekleme.

# Her adımın içeriği bittikten sonra, sonucu ekranda sabit tutan bekleme.
# Timer ~120ms/tick olduğundan 25 tick ≈ 3 sn: kullanıcı her adımın sonucunu
# (ters doğrulaması, affine'in 8 biti, sonuç) rahatça görür.
_STEP_HOLD_TICKS = 25

# Adımların İÇERİK süreleri (animasyonun aktif aktığı kısım). Her adım penceresi
# bu içerik süresine _STEP_HOLD_TICKS eklenerek uzatılır; hold boyunca o adımın
# tamamlanmış hâli (progress=1.0) sabit kalır.
_STEP_CONTENT_TICKS = [_INTRO_TICKS, _INV_TICKS, _AFFINE_TICKS, _RESULT_TICKS]


def _build_timeline() -> tuple[
    list[tuple[int, int]], list[int], list[tuple[int, int]], int
]:
    """Adım/hold/geçiş pencerelerini kümülatif tick aralıklarına çevirir.

    Dönüş: ``(adım_pencereleri, içerik_bitiş_tickleri, geçiş_pencereleri,
    toplam_tick)``. ``adım_pencereleri`` her adımın TAM penceresidir
    (içerik + hold); ``içerik_bitiş_tickleri[i]`` o adımda animasyonun bittiği
    (hold'un başladığı) tick'tir — ilerleme bu noktaya göre 1.0'a ulaşır.
    Adım i bittikten sonra (son adım hariç) bir geçiş penceresi gelir.
    """
    step_bounds: list[tuple[int, int]] = []
    content_ends: list[int] = []
    transition_bounds: list[tuple[int, int]] = []
    cursor = 0
    for i, content in enumerate(_STEP_CONTENT_TICKS):
        start = cursor
        content_ends.append(start + content)
        window = content + _STEP_HOLD_TICKS  # içerik + ~3 sn bekleme
        step_bounds.append((start, start + window))
        cursor += window
        if i < _STEP_COUNT - 1:
            transition_bounds.append((cursor, cursor + _TRANSITION_TICKS))
            cursor += _TRANSITION_TICKS
    cursor += _HOLD_TICKS  # Son adımdan sonra (sonraki byte'a geçmeden) bekleme.
    return step_bounds, content_ends, transition_bounds, cursor


_STEP_BOUNDS, _STEP_CONTENT_ENDS, _TRANSITION_BOUNDS, _CYCLE_TICKS = _build_timeline()


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
        self._timer.start(get_animation_tick_ms(120))

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
        """Verilen adımın kendi içindeki ilerlemeyi [0,1] aralığında döndürür.

        İlerleme adımın İÇERİK süresine göre hesaplanır; içerik bitince
        (hold penceresi boyunca) 1.0'da sabit kalır — böylece adımın
        tamamlanmış hâli ~3 sn ekranda durur.
        """
        start = _STEP_BOUNDS[step][0]
        content_end = _STEP_CONTENT_ENDS[step]
        if self._tick <= start:
            return 0.0
        if self._tick >= content_end:
            return 1.0
        return (self._tick - start) / max(1, content_end - start)

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

    # Adım 1 fazları (adım içi ilerlemeye göre): kavram → kareleme zinciri →
    # seçili karelerin çarpımı → bulundu/doğrulama.
    _INV_SQUARE_START = 0.15
    _INV_MULTIPLY_START = 0.60
    _INV_FOUND_START = 0.90

    # Kareleme zincirindeki güç etiketleri: a^(2^k), k = 0..7.
    _SQUARE_LABELS = ("a", "a²", "a⁴", "a⁸", "a¹⁶", "a³²", "a⁶⁴", "a¹²⁸")

    def _inverse_phase(self, progress: float) -> tuple[str, int, int]:
        """(faz, gösterilen_kare_sayısı, gösterilen_çarpım_sayısı) döndürür.

        Faz akışı: ``concept`` (kavram) → ``square`` (kareleri üret) →
        ``multiply`` (seçili kareleri çarp) → ``found`` (ters + doğrulama).
        Kare sayısı 0..8, çarpım sayısı 0..7 (a hariç 7 kare çarpılır)."""
        if progress < self._INV_SQUARE_START:
            return "concept", 0, 0
        if progress < self._INV_MULTIPLY_START:
            f = (progress - self._INV_SQUARE_START) / (
                self._INV_MULTIPLY_START - self._INV_SQUARE_START)
            return "square", min(8, 1 + int(f * 8)), 0
        if progress < self._INV_FOUND_START:
            f = (progress - self._INV_MULTIPLY_START) / (
                self._INV_FOUND_START - self._INV_MULTIPLY_START)
            return "multiply", 8, min(7, int(f * 7))
        return "found", 8, 7

    def _paint_scene_inverse(self, p: QPainter, rect: QRect) -> None:
        """Çarpımsal tersi a⁻¹ = a²⁵⁴ ÜS ALMASIYLA (ardışık kareleme) BULUR.

        a → a² → a⁴ → … → a¹²⁸ kareleri üretilir; 254 = 11111110 olduğundan
        a hariç tüm kareler GF(2⁸)'de çarpılıp a⁻¹ elde edilir ve a·a⁻¹ = 01
        ile doğrulanır. ``_gf_inverse``'in gerçek (brute-force olmayan)
        mantığını birebir görselleştirir; brute-force 'tek tek deneme' yerine
        matematiksel yöntem gösterilir."""
        progress = self._step_local_progress(1)

        if self._byte == 0:
            self._paint_centered_big(p, rect, "00", QColor(ANIM_COLORS["accent_mauve"]))
            self._paint_note(
                p, rect,
                "0x00'ın çarpımsal tersi yoktur; AES sözleşmesiyle 0 alınır.",
            )
            return

        steps = gf_inverse_exponent_steps(self._byte)
        squares = steps["squares"]
        multiplied = steps["multiplied"]
        inv = steps["inverse"]

        mauve = QColor(ANIM_COLORS["accent_mauve"])
        green = QColor(ANIM_COLORS["accent_green"])
        yellow = QColor(ANIM_COLORS["accent_yellow"])
        sec = QColor(ANIM_COLORS["text_secondary"])
        muted = QColor(ANIM_COLORS["text_muted"])
        primary = QColor(ANIM_COLORS["text_primary"])
        border = QColor(ANIM_COLORS["border"])

        phase, squares_shown, products_shown = self._inverse_phase(progress)

        # Üst: kavram (a⁻¹ = a²⁵⁴, çünkü a²⁵⁵ = 1) ve üs ikili gösterimi.
        y = rect.top() + 2
        p.setFont(QFont("Courier New", 15, QFont.Weight.Bold))
        self._paint_equation(
            p, rect.center().x(), y + 12,
            [("a⁻¹ = a", sec), ("²⁵⁴", green),
             ("    (çünkü a²⁵⁵ = 1)", muted)],
        )
        p.setFont(QFont("IBM Plex Sans", 9))
        p.setPen(muted)
        p.drawText(QRect(rect.left(), y + 26, rect.width(), 14),
                   Qt.AlignmentFlag.AlignCenter,
                   "254 = 1111 1110₂  →  a hariç tüm kareler çarpılır")

        # Kareleme zinciri: a → a² → a⁴ → … → a¹²⁸ (chip'ler, ² ile bağlı).
        n = 8
        cw, ch = 50, 38
        arrow = 16
        row_w = n * cw + (n - 1) * arrow
        ox = rect.center().x() - row_w // 2
        cy = y + 56
        for i in range(n):
            x = ox + i * (cw + arrow)
            shown = i < squares_shown
            is_mult = i in multiplied  # bit=1 → çarpıma katılır
            col = green if is_mult else mauve
            fill = QColor(col)
            fill.setAlpha(60 if shown else 12)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(col if shown else border, 2 if shown else 1))
            p.drawRoundedRect(x, cy, cw, ch, 7, 7)
            p.setFont(QFont("IBM Plex Sans", 8, QFont.Weight.Bold))
            p.setPen(col if shown else muted)
            p.drawText(QRect(x - 4, cy - 14, cw + 8, 13),
                       Qt.AlignmentFlag.AlignCenter, self._SQUARE_LABELS[i])
            p.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
            p.setPen(primary if shown else muted)
            p.drawText(QRect(x, cy, cw, ch), Qt.AlignmentFlag.AlignCenter,
                       f"{squares[i]:02x}" if shown else "·")
            if i < n - 1:
                ax = x + cw
                lit = (i + 1) < squares_shown
                p.setPen(QPen(yellow if lit else border, 2))
                p.drawLine(ax + 2, cy + ch // 2, ax + arrow - 2, cy + ch // 2)
                p.setFont(QFont("IBM Plex Sans", 8, QFont.Weight.Bold))
                p.setPen(yellow if lit else muted)
                p.drawText(QRect(ax, cy - 1, arrow, 12),
                           Qt.AlignmentFlag.AlignCenter, "²")

        # Çarpım / sonuç satırı: a⁻¹ = a² · a⁴ · … = inv (birikerek).
        if phase in ("multiply", "found"):
            done = phase == "found"
            count = 7 if done else max(1, products_shown)
            terms = " · ".join(self._SQUARE_LABELS[i] for i in multiplied[:count])
            value = inv if done else steps["products"][count - 1]
            tail = "" if (done or count >= 7) else " · …"
            py = cy + ch + 22
            p.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
            self._paint_equation(
                p, rect.center().x(), py,
                [("a⁻¹ = ", sec), (terms + tail, green if done else yellow),
                 (" = ", sec), (f"{value:02x}", green)],
            )

        # Not / doğrulama.
        if phase == "concept":
            note = (
                "Tersi tek tek denemeyiz: GF(2⁸)'de a⁻¹ = a²⁵⁴. a'yı ardışık "
                "kareleyip (a, a², a⁴, …) 254'ün 1 olan bitlerine düşen kareleri "
                "çarparak buluruz."
            )
            p.setPen(sec)
        elif phase == "square":
            note = "Her kutu, bir öncekinin GF(2⁸)'deki karesidir: a → a² → a⁴ → …"
            p.setPen(sec)
        elif phase == "multiply":
            note = ("254 = 11111110 olduğundan a (en sağ bit 0) hariç tüm kareler "
                    "çarpılır; çarpım GF(2⁸)'de birikiyor.")
            p.setPen(sec)
        else:
            check = _gf_mul(self._byte, inv)
            note = (f"Bulundu: a⁻¹ = {inv:02x}.  Doğrulama: {self._byte:02x} · "
                    f"{inv:02x} = {check:02x} ✓")
            p.setPen(green)
        self._paint_note(p, rect, note, set_pen=False)

    # ------------------------------------------------------------------
    # Sahne 2 — Affine (bit-bit XOR akışı)
    # ------------------------------------------------------------------

    # Affine dönüşümünde her çıkış biti b'_i, girdinin şu bit indekslerinin
    # XOR'udur (aes_pure._affine_transform ile birebir): i, i+4, i+5, i+6, i+7
    # (mod 8), artı 0x63 sabitinin i. biti.
    _AFFINE_OFFSETS = (0, 4, 5, 6, 7)
    _AFFINE_CONST = 0x63

    def _affine_output_bit(self, inv: int, i: int) -> int:
        """Ters byte ``inv`` için affine çıkışının ``i``. bitini hesaplar."""
        bit = (self._AFFINE_CONST >> i) & 1
        for off in self._AFFINE_OFFSETS:
            bit ^= (inv >> ((i + off) % 8)) & 1
        return bit

    def _paint_scene_affine(self, p: QPainter, rect: QRect) -> None:
        """Affine dönüşümünü bit-bit XOR akışıyla canlandırır.

        Üstte ters byte'ın 8 biti, altında 0x63 sabitinin 8 biti gösterilir;
        çıkış bitleri b'₇…b'₀ tek tek üretilir. O an üretilen bit için XOR'a
        giren girdi bitleri ve sabit biti vurgulanır.
        """
        d = derive_sbox_value(self._byte)
        inv = d.inverse
        progress = self._step_local_progress(2)

        # Kaç çıkış biti üretildi? (0..8; 8 = tamamlandı.)
        produced = min(8, max(0, int(progress * 8)))
        # O an aktif olarak üretilen çıkış biti (MSB→LSB sırasıyla i=7..0).
        active_out = 7 - produced if produced < 8 else -1
        # Aktif bite katkı veren girdi bit indeksleri (vurgulama için).
        contrib = set()
        if active_out >= 0:
            contrib = {(active_out + off) % 8 for off in self._AFFINE_OFFSETS}

        mauve = QColor(ANIM_COLORS["accent_mauve"])
        yellow = QColor(ANIM_COLORS["accent_yellow"])
        green = QColor(ANIM_COLORS["accent_green"])
        muted = QColor(ANIM_COLORS["text_muted"])

        cell = 30
        gap = 6
        row_w = 8 * cell + 7 * gap
        ox = rect.center().x() - row_w // 2
        label_x = ox - 70

        y_inv = rect.top() + 6
        y_const = y_inv + cell + 10
        y_out = y_const + cell + 18

        # Satır etiketleri.
        p.setFont(QFont("IBM Plex Sans", 9, QFont.Weight.Bold))
        for y, text, col in (
            (y_inv, f"ters {inv:02x}", mauve),
            (y_const, f"sabit {self._AFFINE_CONST:02x}", QColor(ANIM_COLORS["text_secondary"])),
            (y_out, f"çıktı {d.result:02x}", yellow),
        ):
            p.setPen(col)
            p.drawText(QRect(label_x - 10, y, 76, cell),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, text)

        # Bitleri MSB→LSB (sol→sağ) çiz: kolon k → bit indeksi 7-k.
        for k in range(8):
            bit_idx = 7 - k
            x = ox + k * (cell + gap)
            inv_bit = (inv >> bit_idx) & 1
            const_bit = (self._AFFINE_CONST >> bit_idx) & 1

            # Ters biti (katkı veriyorsa vurgulu).
            highlighted = bit_idx in contrib
            self._paint_bit_cell(p, x, y_inv, cell, inv_bit,
                                 mauve if highlighted else muted,
                                 strong=highlighted)
            # Sabit biti (yalnızca aktif çıkış kolonunda vurgulu).
            const_hl = (bit_idx == active_out)
            self._paint_bit_cell(p, x, y_const, cell, const_bit,
                                 yellow if const_hl else muted,
                                 strong=const_hl)

            # Çıkış biti: üretildiyse değeri, aktifse vurgulu, henüz değilse boş.
            if k < produced:
                out_bit = self._affine_output_bit(inv, bit_idx)
                self._paint_bit_cell(p, x, y_out, cell, out_bit, green, strong=True)
            elif bit_idx == active_out:
                self._paint_bit_cell(p, x, y_out, cell, None, yellow, strong=True)
            else:
                self._paint_bit_cell(p, x, y_out, cell, None, muted, strong=False)

        # Açıklama: aktif bit varsa formülü, bittiyse sonucu göster.
        if active_out >= 0:
            terms = " ⊕ ".join(
                [f"b{(active_out + off) % 8}" for off in self._AFFINE_OFFSETS]
                + [f"c{active_out}"]
            )
            note = f"Çıkış biti b'{active_out} = {terms}  (her terim 0/1, XOR'lanır)"
        else:
            note = (
                f"8 bitin tümü üretildi → affine sonucu {d.result:02x}. "
                f"Her çıkış biti, ters byte'ın 5 dönük biti ve {self._AFFINE_CONST:02x} "
                f"sabitinin XOR'udur."
            )
        self._paint_note(p, rect, note)

    def _paint_bit_cell(self, p: QPainter, x: int, y: int, size: int,
                        value: int | None, color: QColor, strong: bool) -> None:
        """Tek bir bit hücresi çizer (value None ise boş/'?' gösterir)."""
        fill = QColor(color)
        fill.setAlpha(70 if strong else 16)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(color if strong else QColor(ANIM_COLORS["border"]),
                      2 if strong else 1))
        p.drawRoundedRect(x, y, size, size, 5, 5)
        p.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]) if (strong or value is not None)
                 else QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(x, y, size, size), Qt.AlignmentFlag.AlignCenter,
                   "·" if value is None else str(value))

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
    # Sahne geçişleri ("uçan byte" kaydırma — süreklilik)
    # ------------------------------------------------------------------

    def _paint_transition(self, p: QPainter, rect: QRect, source_step: int,
                          t: float) -> None:
        """Kaynak adımın çıktısını sonraki sahnenin giriş konumuna kaydırır.

        Hedef sahnenin sönük bir taslağı arkada durur; üstünde tek bir "uçan
        byte" kaynak çıkış noktasından hedef giriş noktasına lineer taşınır.
        Bu, "bir adımın çıktısı sonrakinin girdisidir" fikrini görselleştirir.
        """
        d = derive_sbox_value(self._byte)

        # Geçişe göre: uçan byte değeri/rengi, kaynak ve hedef noktalar.
        if source_step == 0:
            value = f"{self._byte:02x}"
            color = QColor(ANIM_COLORS["accent_blue"])
            src = QPoint(rect.center().x(), rect.top() + 52)
            dst = QPoint(rect.center().x() - 70, rect.top() + 46)
            ghost = self._paint_scene_inverse
        elif source_step == 1:
            value = f"{d.inverse:02x}"
            color = QColor(ANIM_COLORS["accent_mauve"])
            src = QPoint(rect.center().x(), rect.top() + 46)
            dst = QPoint(rect.center().x() - 110, rect.top() + 20)
            ghost = self._paint_scene_affine
        else:
            value = f"{d.result:02x}"
            color = QColor(ANIM_COLORS["accent_yellow"])
            src = QPoint(rect.center().x(), rect.top() + 46)
            dst = QPoint(rect.center().x(), rect.top() + 64)
            ghost = self._paint_scene_result

        # Hedef sahnenin sönük taslağı (yarı saydam) — bağlam korunur.
        p.save()
        p.setOpacity(0.18)
        ghost(p, rect)
        p.restore()

        # Uçan byte: src→dst lineer interpolasyon (hafif yukarı yay).
        x = int(src.x() + (dst.x() - src.x()) * t)
        y = int(src.y() + (dst.y() - src.y()) * t)
        box = 48
        fill = QColor(color)
        fill.setAlpha(80)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(color, 2))
        p.drawRoundedRect(x - box // 2, y - box // 2, box, box, 8, 8)
        p.setFont(QFont("Courier New", 20, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(x - box // 2, y - box // 2, box, box),
                   Qt.AlignmentFlag.AlignCenter, value)

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
