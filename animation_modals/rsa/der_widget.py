# animation_modals/rsa/der_widget.py
"""Adım 6 — DER ve Base64 kodlaması: uzamsal montaj animasyonu.

Eski sürüm tek bir paintEvent içinde ~5 fazlı metin duvarı çiziyordu;
kullanıcı yoğun metinde "şu an ne oluyor?" sorusuna görsel cevap
bulamıyordu. Bu sürüm AES sütun-yönlü dolum idiomunu mirror eder: sayılar
tek tek beliren hex BYTE KUTULARINA ayrılır, kutular DER (SEQUENCE / INTEGER)
yapısına sırayla yerleşip alanlar vurgulanır, ardından Base64 dönüşümü
gösterilir. Tüm açılım tek bir tick sayacıyla (_tick) sürülür; her tick
eşiği bir sonraki kutuyu/aşamayı açar.
"""
from __future__ import annotations
import base64
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QSizePolicy
from ..base import ANIM_COLORS, get_animation_tick_ms
from ..byte_widgets import _palette_6
from . import helpers as H

# ---------------------------------------------------------------------------
# Adım 6 — DER ve Base64 Kodlaması (uzamsal montaj)
# ---------------------------------------------------------------------------


class _DERByteFlowWidget(QWidget):
    """
    Sayılar → byte kutuları → DER (ASN.1 SEQUENCE) montajı → Base64.

    Animasyon tick tabanlıdır: ``_tick`` her ``_TICK_MS`` ms'de bir artar ve
    paintEvent, açığa çıkan kutu/aşama sayısını ``_tick``'ten türetir. Böylece
    kullanıcı kutuların DER yapısına tek tek "yerleştiğini" izler. Son fazda
    Alice'in gerçek RSA-2048 anahtar kutuları (K⁺/K⁻) gösterilir.

    Public yüzey korunur: yapıcı ``(alice_b64)`` alır; ``window.py`` bunu
    ``_DERByteFlowWidget(self._alice_b64)`` olarak QScrollArea içinde kurar.
    """

    _TICK_MS = 80                 # kutu açılış temposu (AES 60'tan biraz yavaş)
    _TICKS_PER_BOX = 2            # bir kutunun açılması kaç tick sürer
    _GAP = 4                     # aşamalar arası tick boşluğu
    _LABEL_DY = 13               # _byte_box etiketinin kutu üstüne çıkış payı (px)
    _LABEL_CLEARANCE = 14        # etiketli satır öncesi ayrılan dikey boşluk (≥ _LABEL_DY)

    def __init__(
        self, alice_b64: str, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._alice_b64 = alice_b64
        # Kutu tabanlı yerleşim → eski 1000 px metin duvarından düşük; bit
        # yeniden-gruplama satırları için ~860 px yeterli (kalanı scroll alanı).
        self.setMinimumHeight(860)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._compute_schedule()

    # ------------------------------------------------------------------
    # Zamanlama / tick motoru
    # ------------------------------------------------------------------

    def _compute_schedule(self) -> None:
        """Cari demo (H) değerlerinden açılış tik eşiklerini hesaplar.

        n/e'nin DER değer baytları ve toplam DER uzunluğundan, her aşamanın
        (sayı→byte, DER montajı, Base64, Aşama B, anahtarlar) hangi tikte
        başlayacağını belirler. Widget her açılışta (showEvent) yeniden
        çağrılır ki reseed sonrası uzunluklar güncel olsun.
        """
        self._n_val = H._DER_N[2:]            # n'nin DER değer baytları
        self._e_val = H._DER_E[2:]            # e'nin DER değer baytları
        self._der = H._DER_SEQ               # tam DER (30 len 02 .. 02 ..)
        per = self._TICKS_PER_BOX
        g = self._GAP

        self._t_nums = 2                                   # sayılar görünür
        self._t_n_start = self._t_nums + 1
        n_end = self._t_n_start + per * len(self._n_val)
        self._t_e_start = n_end + 1
        e_end = self._t_e_start + per * len(self._e_val)

        self._t_der_start = e_end + g
        der_end = self._t_der_start + per * len(self._der)

        # Base64 alt-fazları: 3 byte → 24 bit → 4×6-bit grup sütun-yönlü çözülür.
        self._t_b64 = der_end + g                          # 3 hex byte kutusu
        self._t_b64_bits = self._t_b64 + 2                 # 24 bit hücresi belirir
        self._t_b64_groups = self._t_b64_bits + 2          # ilk 6-bit grup çözülür
        b64_end = self._t_b64_groups + per * 4             # 4 grup birer birer
        self._t_asama_b = b64_end + g
        asama_b_end = self._t_asama_b + per * 6
        self._t_keys = asama_b_end + g
        self._t_end = self._t_keys + 4

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._compute_schedule()
        self._tick = 0
        self.update()
        self._timer.start(get_animation_tick_ms(self._TICK_MS))

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self) -> None:
        """Tik sayacını ilerletir; son tike ulaşınca zamanlayıcıyı durdurur."""
        if self._tick < self._t_end:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def _revealed(self, start_tick: int, count: int) -> int:
        """start_tick'ten bu yana açığa çıkan kutu sayısını (0..count) verir."""
        if self._tick < start_tick:
            return 0
        return min(count, (self._tick - start_tick) // self._TICKS_PER_BOX + 1)

    # ------------------------------------------------------------------
    # Çizim yardımcıları
    # ------------------------------------------------------------------

    def _byte_box(
        self, p: QPainter, x: int, y: int, text: str, fill_hex: str,
        *, w: int = 36, h: int = 28, label: str | None = None,
        label_color: str | None = None, highlight: bool = False,
        text_color: str | None = None,
    ) -> None:
        """Tek bir hex byte kutusu çizer (üstte küçük etiket, ortada değer).

        highlight=True iken kalın accent_yellow kenarlık ile "yeni yerleşti"
        vurgusu verir → kullanıcı son eklenen baytı kolayca takip eder.
        """
        if label:
            p.setFont(QFont("IBM Plex Sans", 7, QFont.Weight.Bold))
            p.setPen(QColor(label_color or ANIM_COLORS["text_muted"]))
            p.drawText(QRect(x - 6, y - self._LABEL_DY, w + 12, 12),
                       Qt.AlignmentFlag.AlignCenter, label)
        qc = QColor(fill_hex)
        p.setBrush(QBrush(qc))
        if highlight:
            p.setPen(QPen(QColor(ANIM_COLORS["accent_yellow"]), 2))
        else:
            p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))
        p.drawRoundedRect(x, y, w, h, 4, 4)
        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        p.setPen(QColor(text_color or ANIM_COLORS["text_on_accent"]))
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)

    def _section_title(self, p: QPainter, y: int, text: str,
                       color_key: str = "text_secondary") -> int:
        """Bölüm başlığını ortalı çizer ve bir sonraki y'yi döndürür."""
        p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS[color_key]))
        p.drawText(QRect(0, y, self.width(), 20),
                   Qt.AlignmentFlag.AlignCenter, text)
        return y + 24

    # ------------------------------------------------------------------
    # paintEvent
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()
        cx = W // 2
        y = 8

        # === 1) Sayı → byte dizisi ===
        y = self._section_title(p, y, "1)  Sayı  →  byte dizisi", "accent_blue")
        if self._tick >= self._t_nums:
            y = self._draw_number_to_bytes(p, cx, y)

        # === 2) DER paketleme (ASN.1 SEQUENCE) ===
        y += 10
        y = self._section_title(p, y, "2)  DER paketleme  —  ASN.1 SEQUENCE",
                               "accent_mauve")
        if self._tick >= self._t_der_start:
            y = self._draw_der_assembly(p, cx, y)

        # === 3) Base64 ===
        y += 10
        y = self._section_title(p, y, "3)  Base64  —  her 3 byte → 4 karakter",
                               "accent_green")
        if self._tick >= self._t_b64:
            y = self._draw_base64(p, cx, y)

        # === Aşama B — Alice'in gerçek anahtarı ===
        if self._tick >= self._t_asama_b:
            y += 10
            y = self._section_title(
                p, y, "Aşama B — aynı yöntem Alice'in gerçek anahtarına",
                "accent_yellow")
            y = self._draw_asama_b(p, cx, y)

        # === Alice'in gerçek anahtar kutuları ===
        if self._tick >= self._t_keys:
            y += 12
            y = self._draw_alice_keys(p, y)

        p.end()

    # ------------------------------------------------------------------
    # Bölüm çizimleri
    # ------------------------------------------------------------------

    def _draw_number_to_bytes(self, p: QPainter, cx: int, y: int) -> int:
        """n ve e sayılarını gösterir, ardından her birini tek tek beliren
        hex byte kutularına ayırır (sayı → big-endian byte dizisi)."""
        mauve = _palette_6()[3]
        peach = _palette_6()[4]
        rows = (
            ("n", H._N, self._n_val, self._t_n_start, mauve),
            ("e", H._E, self._e_val, self._t_e_start, peach),
        )
        for name, val, vbytes, start, color in rows:
            # Sol: "n = 253  →"
            p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            lead = f"{name} = {val}   →"
            p.drawText(QRect(cx - 230, y, 150, 28),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       lead)
            # Sağ: byte kutuları (tek tek açılır)
            shown = self._revealed(start, len(vbytes))
            bx = cx - 60
            for i in range(shown):
                fresh = (i == shown - 1 and
                         self._tick < start + self._TICKS_PER_BOX * len(vbytes))
                self._byte_box(p, bx + i * 42, y, f"{vbytes[i]:02X}", color,
                               highlight=fresh)
            y += 34
        return y

    def _draw_der_assembly(self, p: QPainter, cx: int, y: int) -> int:
        """DER baytlarını tek bir satırda, alan-renkli kutular hâlinde sırayla
        açar. Üstte her alanın (SEQUENCE / n INTEGER / e INTEGER) köşeli ayraç
        + etiketi, ilgili kutular tamamlanınca belirir."""
        der = self._der
        blue = _palette_6()[0]
        mauve = _palette_6()[3]
        peach = _palette_6()[4]

        # Alan sınırları: [30 len] | [02 lenN <n>] | [02 lenE <e>]
        seq_hdr = 2
        n_field = len(H._DER_N)
        seq_end = seq_hdr
        n_end = seq_hdr + n_field
        e_end = len(der)

        def field_of(idx: int) -> str:
            if idx < seq_end:
                return "seq"
            if idx < n_end:
                return "n"
            return "e"

        colors = {"seq": blue, "n": mauve, "e": peach}

        bw, gap = 34, 6
        total = len(der) * bw + (len(der) - 1) * gap
        ox = max(8, cx - total // 2)
        box_y = y + 22                      # üstte etiket/ayraç payı

        shown = self._revealed(self._t_der_start, len(der))

        # Alan köşeli ayraçları + etiketleri (tamamlanan alanlar)
        field_spans = [
            ("SEQUENCE", "seq", 0, seq_end, blue),
            ("n : INTEGER", "n", seq_end, n_end, mauve),
            ("e : INTEGER", "e", n_end, e_end, peach),
        ]
        for label, _key, a, b, col in field_spans:
            if shown <= a:
                continue
            xa = ox + a * (bw + gap)
            last = min(b, shown)
            xb = ox + (last - 1) * (bw + gap) + bw
            p.setPen(QPen(QColor(col), 1))
            p.drawLine(xa, box_y - 4, xb, box_y - 4)
            p.drawLine(xa, box_y - 4, xa, box_y - 1)
            p.drawLine(xb, box_y - 4, xb, box_y - 1)
            if shown >= b:                  # alan tamamlanınca etiketi yaz
                p.setFont(QFont("IBM Plex Sans", 7, QFont.Weight.Bold))
                p.setPen(QColor(col))
                p.drawText(QRect(xa, box_y - 18, xb - xa, 12),
                           Qt.AlignmentFlag.AlignCenter, label)

        # Byte kutuları
        for i in range(shown):
            key = field_of(i)
            fresh = (i == shown - 1 and
                     self._tick < self._t_der_start +
                     self._TICKS_PER_BOX * len(der))
            self._byte_box(p, ox + i * (bw + gap), box_y, f"{der[i]:02X}",
                           colors[key], w=bw, highlight=fresh)
        y = box_y + 34

        # Tamamlanınca toplam DER özeti
        if shown >= len(der):
            p.setFont(QFont("Georgia", 10))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(0, y, self.width(), 18),
                       Qt.AlignmentFlag.AlignCenter,
                       f"DER ({len(der)} bayt) hazır — satır içinde Base64'e kodlanır.")
            y += 22
        return y

    def _draw_base64(self, p: QPainter, cx: int, y: int) -> int:
        """DEMO DER'in ilk 3 baytını 24 bite açar ve bu 24 biti 4×6-bit gruba
        YENİDEN BÖLER; her 6-bit grup sütun-yönlü sırayla indeks → Base64
        karakterine çözülür (3 byte → 4 karakter). Bitler, kaynak baytlarının
        rengiyle boyanır; 6'lık yeniden gruplama köşeli ayraçlarla gösterilir
        → 8'lik byte sınırı ile 6'lık b64 sınırının kaymasını kullanıcı görür.
        """
        der = self._der
        b64 = H._B64_DEMO
        chunk = der[:3]
        if len(chunk) < 3:                  # demo DER her zaman ≥3 bayt; güvenlik
            return y
        bits = "".join(f"{b:08b}" for b in chunk)          # 24 bit
        groups = [bits[i:i + 6] for i in range(0, 24, 6)]  # 4 × 6-bit
        indices = [int(g, 2) for g in groups]
        chars = b64[:4]
        byte_cols = [_palette_6()[0], _palette_6()[3], _palette_6()[4]]

        # Kutuların üstündeki "bayt N" etiketi (_byte_box label'ı kutunun 13 px
        # üstüne yazar) bölüm başlığıyla çakışmasın diye satırı aşağı it.
        y += self._LABEL_CLEARANCE

        # --- 3 kaynak baytı (hex kutuları, byte renkleriyle) ---
        bw, gap = 36, 6
        grp3_w = 3 * bw + 2 * gap
        ox3 = cx - grp3_w // 2
        for i, b in enumerate(chunk):
            self._byte_box(p, ox3 + i * (bw + gap), y, f"{b:02X}", byte_cols[i],
                           w=bw, label=f"bayt {i+1}", label_color=byte_cols[i])
        y += 40

        # --- 24 bit hücresi (kaynak baytın rengiyle, 8|8|8) ---
        if self._tick < self._t_b64_bits:
            return y
        cw, ch = 18, 22
        total = 24 * cw
        ox = cx - total // 2
        bit_y = y
        for i, bit in enumerate(bits):
            col = byte_cols[i // 8]
            self._byte_box(p, ox + i * cw, bit_y, bit, col, w=cw, h=ch)
        y += ch + 4

        # --- 6'lık yeniden gruplama: köşeli ayraç + indeks → karakter ---
        groups_shown = 0
        if self._tick >= self._t_b64_groups:
            groups_shown = min(4, (self._tick - self._t_b64_groups) // 2 + 1)
        green = _palette_6()[1]
        char_y = y + 18
        for g in range(groups_shown):
            xa = ox + g * 6 * cw
            xb = ox + (g + 1) * 6 * cw
            fresh = (g == groups_shown - 1 and
                     self._tick < self._t_b64_groups + 2 * 4)
            col = ANIM_COLORS["accent_yellow"] if fresh else ANIM_COLORS["border"]
            p.setPen(QPen(QColor(col), 2 if fresh else 1))
            p.drawLine(xa + 1, y, xb - 1, y)
            p.drawLine(xa + 1, y, xa + 1, y + 4)
            p.drawLine(xb - 1, y, xb - 1, y + 4)
            # indeks etiketi
            p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(xa, y + 4, xb - xa, 12),
                       Qt.AlignmentFlag.AlignCenter, f"={indices[g]}")
            # sonuç karakter kutusu (grubun altında ortalı)
            self._byte_box(p, (xa + xb) // 2 - 17, char_y, chars[g], green,
                           w=34, highlight=fresh)
        y = char_y + 34

        if groups_shown >= 4:
            p.setFont(QFont("Georgia", 10))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(8, y, self.width() - 16, 18),
                       Qt.AlignmentFlag.AlignCenter,
                       f"Demo Base64 ({len(b64)} karakter, temsilî): {b64}")
            y += 22
        return y

    def _draw_asama_b(self, p: QPainter, cx: int, y: int) -> int:
        """Alice'in gerçek 2048-bit anahtarının ilk 3 baytını alıp aynı 3→4
        yöntemiyle ilk 4 Base64 karakterine eşler (gerçek anahtara köprü)."""
        first4 = self._alice_b64[:4]
        try:
            first3 = base64.b64decode(first4 + "==")[:3]
        except Exception:
            first3 = b""
        blue = _palette_6()[0]
        green = _palette_6()[1]
        bw, gap = 36, 6
        if len(first3) == 3:
            group_w = 3 * bw + 2 * gap
            ox = cx - group_w - 60
            for i, b in enumerate(first3):
                self._byte_box(p, ox + i * (bw + gap), y, f"{b:02X}", blue, w=bw)
            p.setFont(QFont("Georgia", 14))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(ox + group_w + 6, y, 44, 28),
                       Qt.AlignmentFlag.AlignCenter, "→")
            cx2 = ox + group_w + 56
            for i, ch in enumerate(first4):
                self._byte_box(p, cx2 + i * (bw + gap), y, ch, green, w=bw)
            y += 38
            p.setFont(QFont("Georgia", 10))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(8, y, self.width() - 16, 18),
                       Qt.AlignmentFlag.AlignCenter,
                       f"= Alice b64'ünün ilk 4 karakteri: {first4}")
            y += 22
        return y

    def _draw_alice_keys(self, p: QPainter, y: int) -> int:
        """Alice'in gerçek RSA-2048 anahtar kutularını (K⁺ açık, K⁻ gizli)
        çizer. K⁻ içeriği güvenlik gereği gösterilmez."""
        W = self.width()
        p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1, Qt.PenStyle.DashLine))
        p.drawLine(40, y, W - 40, y)
        y += 8
        p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "↓  Alice'in gerçek RSA-2048 anahtarları")
        y += 22
        self._draw_real_key_box(
            p, x=12, y=y, w=W - 24, h=24,
            icon="K⁺", icon_color=ANIM_COLORS["accent_blue"],
            label="Alice Açık Anahtarı:", value=self._alice_b64,
        )
        y += 28
        self._draw_real_key_box(
            p, x=12, y=y, w=W - 24, h=24,
            icon="K⁻", icon_color=ANIM_COLORS["accent_green"],
            label="Alice Gizli Anahtarı:",
            value="(n, d) — yalnızca Alice'te tutulur",
            value_color=ANIM_COLORS["text_muted"], italic_value=True,
        )
        return y + 28

    @staticmethod
    def _draw_real_key_box(
        p: QPainter, x: int, y: int, w: int, h: int,
        icon: str, icon_color: str,
        label: str, value: str,
        value_color: str | None = None,
        italic_value: bool = False,
    ) -> None:
        """Tek bir anahtar kutusu çizer: sol K⁺/K⁻ simgesi, etiket, ve tek
        satıra sığacak şekilde kırpılmış Base64 değer önizlemesi."""
        fill = QColor(ANIM_COLORS["bg_input"])
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(icon_color), 1))
        p.drawRoundedRect(x, y, w, h, 4, 4)

        icon_w = 36
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(icon_color))
        p.drawText(QRect(x + 4, y, icon_w, h),
                   Qt.AlignmentFlag.AlignCenter, icon)

        p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        label_w = 150
        p.drawText(QRect(x + icon_w + 4, y, label_w, h),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   label)

        font = QFont("Courier New", 9)
        if italic_value:
            font.setItalic(True)
        p.setFont(font)
        p.setPen(QColor(value_color or ANIM_COLORS["text_primary"]))
        value_x = x + icon_w + 4 + label_w + 4
        value_w = w - (value_x - x) - 6
        max_chars = max(20, value_w // 7)
        display = value if len(value) <= max_chars else value[:max_chars - 1] + "…"
        p.drawText(QRect(value_x, y, value_w, h),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   display)
