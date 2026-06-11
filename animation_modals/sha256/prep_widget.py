# animation_modals/sha256/prep_widget.py
"""SHA-256 mesaj hazırlığı (UTF-8) ve padding widget'ları."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS, get_animation_tick_ms

# ---------------------------------------------------------------------------
# SHA Mesaj Hazırlığı (metin → UTF-8 byte) — Task 7 widget'ı
# ---------------------------------------------------------------------------

class _SHAMessagePrepWidget(QWidget):
    """
    SHA Mesaj Hazırlığı sayfası — kullanıcının metnini UTF-8 byte'lara dönüştürme
    sürecini görselleştirir.

    Fazlar (QTimer _TICK_MS=60):
      0: Mesaj label'ı fade-in
      1: İlk 16 byte char->ASCII->hex satırları kademeli
      2: Binary satırı
      3: Alt byte strip görünür
      4: Özet kartı — animasyon durur, on_finished callback çağrılır

    Boş mesaj: faz 1-2-3 atlanır, doğrudan faz 4'e geçilir.
    """

    _TICK_MS = 60
    _PHASE_DWELL_TICKS = 83

    def __init__(
        self,
        message_text: str,
        message_bytes: bytes,
        on_finished=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from animation_modals.byte_widgets import (
            _ColoredByteGridWidget,
            _ByteStripWidget,
        )

        self._message_text = message_text
        self._message_bytes = message_bytes
        self._on_finished = on_finished
        self._is_empty = len(message_bytes) == 0
        self._tick = 0
        self._phase = 0
        self._finished = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        # Üst başlık
        title = QLabel("Mesaj Hazırlığı — Metin → UTF-8 Byte Dizisi")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        self._title_lbl = title

        # Mesaj label — TAM mesaj gösterilir (eski 60 karakter kesilmesi
        # kaldırıldı); uzun mesajlarda QLabel word-wrap ile alt satıra iner.
        if self._is_empty:
            label_text = "<i>(boş mesaj)</i>"
            label_color = ANIM_COLORS["text_muted"]
        else:
            label_text = f"Mesaj: \"{message_text}\""
            label_color = ANIM_COLORS["text_secondary"]
        self._msg_lbl = QLabel(label_text)
        self._msg_lbl.setFont(QFont("IBM Plex Sans", 11))
        self._msg_lbl.setStyleSheet(f"color: {label_color};")
        self._msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._msg_lbl.setWordWrap(True)
        lay.addWidget(self._msg_lbl)

        # Detail grid — TÜM mesaj byte'ları gösterilir (16 cap KALDIRILDI):
        # Kutu boyutu sabit (66 px), kutu SAYISI mesaj uzunluğuyla artar.
        # 71-byte mesaj → 71 kutu, ~5000 px genişlikte widget; QScrollArea
        # yatay scroll ile kullanıcı tüm byte'ları (e-mail boyu kadar uzun
        # mesajı dahi) baştan sona gezebilir. Kutu boyutu küçülmez —
        # binary, hex, decimal her durumda okunaklı kalır.
        detail_lbl = QLabel("Byte detayı (yatay kaydırarak tüm byte'ları gör):")
        detail_lbl.setFont(QFont("IBM Plex Sans", 9))
        detail_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(detail_lbl)
        self._detail_lbl = detail_lbl

        # max_cells = len(data): cap yok, tüm byte'lar gösterilir.
        # Boş mesaj için fallback 1 (görsel olarak hiçbir kutu çizmez).
        n_cells = max(1, len(message_bytes))
        self._grid = _ColoredByteGridWidget(message_bytes, max_cells=n_cells)
        cell_w_fixed = 66
        cell_h_fixed = 36
        grid_w = 86 + n_cells * (cell_w_fixed + 3)
        grid_h = 4 * (cell_h_fixed + 4) + 30
        self._grid.setFixedSize(grid_w, grid_h)

        grid_scroll = QScrollArea()
        grid_scroll.setWidget(self._grid)
        grid_scroll.setWidgetResizable(False)  # sabit boyut → yatay scroll
        grid_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        grid_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        grid_scroll.setStyleSheet("background: transparent; border: none;")
        grid_scroll.setFixedHeight(grid_h + 18)  # +18 yatay scrollbar payı
        lay.addWidget(grid_scroll)

        # Byte strip (tüm byte'lar) — scroll içinde
        strip_lbl = QLabel("Tüm byte'lar:")
        strip_lbl.setFont(QFont("IBM Plex Sans", 9))
        strip_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(strip_lbl)
        self._strip_lbl = strip_lbl
        self._strip = _ByteStripWidget(message_bytes)
        strip_scroll = QScrollArea()
        strip_scroll.setWidget(self._strip)
        strip_scroll.setWidgetResizable(True)
        strip_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        strip_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        strip_scroll.setStyleSheet("background: transparent; border: none;")
        # 22 (cell_h) + 24 (üst etiket alanı) ≈ 46, buffer ile 56
        strip_scroll.setFixedHeight(56)
        self._strip.setVisible(False)
        lay.addWidget(strip_scroll)

        # Özet kartı
        if self._is_empty:
            summary_text = "Mesaj boş — yalnızca padding işlemi yapılacak"
        else:
            summary_text = (
                f"{len(message_text)} karakter → {len(message_bytes)} byte"
            )
        self._summary = QLabel(summary_text)
        self._summary.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        self._summary.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']}; "
            f"padding: 8px; background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px;"
        )
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary.setVisible(False)
        lay.addWidget(self._summary)

        # NOT: addStretch() çıkarıldı — pencere büyük olsa bile widget kompakt
        # kalsın, alt taraf scrollu/boş alanlı görünmesin. Üst hizalama parent
        # tarafından (_make_msgprep_page) AlignTop ile sağlanır.

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def restyle(self) -> None:
        """Tema değişiminde QLabel stillerini DURUM BOZMADAN yeniden uygular.
        İçteki _ColoredByteGridWidget / _ByteStripWidget QPainter'dır →
        refresh_theme'deki update() ile yenilenir, dokunulmaz."""
        self._title_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        label_color = (ANIM_COLORS["text_muted"] if self._is_empty
                       else ANIM_COLORS["text_secondary"])
        self._msg_lbl.setStyleSheet(f"color: {label_color};")
        self._detail_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._strip_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._summary.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']}; "
            f"padding: 8px; background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px;"
        )

    def start(self) -> None:
        self._timer.start(get_animation_tick_ms(self._TICK_MS))

    def _on_tick(self) -> None:
        """Açıklama fazlarını yaklaşık beş saniyelik okunma aralıklarıyla ilerletir."""
        self._tick += 1
        if self._is_empty:
            # Boş mesaj: kısa bir bekleme sonrası doğrudan faz 4'e
            if self._tick >= self._PHASE_DWELL_TICKS:
                self._jump_to_final()
            return

        # Normal akış: her faz açıklaması okunabilecek kadar ekranda kalır.
        dwell = self._PHASE_DWELL_TICKS
        if self._tick == dwell:
            self._phase = 1
        elif self._tick == dwell * 2:
            self._phase = 2
        elif self._tick == dwell * 3:
            self._phase = 3
            self._strip.setVisible(True)
        elif self._tick >= dwell * 4:
            self._jump_to_final()

    def _jump_to_final(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        self._strip.setVisible(not self._is_empty)
        self._summary.setVisible(True)
        if self._on_finished:
            self._on_finished()

    def closeEvent(self, e) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(e)


class _SHA256PaddingWidget(QWidget):
    """
    SHA-256 Padding sayfası — görsel byte stripi üzerinde padding sürecini gösterir.

    Strip her zaman TÜM 64 byte'ı (tam padded blok) gösterir. Kullanıcının
    mesaj byte'ları normal renkli kareler, padding byte'ları (0x80 + 0x00
    dolgu + 8 byte length) beyaz 1px border + alpha 0.7 ile ayrışır.
    Fazlar yalnızca açıklayıcı etiketi günceller; veri başından sonuna
    aynı görünür ki kullanıcı "yazdığım yazı şurada, padding şurada başlıyor"
    ilişkisini anında görsün.

    Fazlar (etiket güncellemeleri):
      0: "Kullanıcının metni soldaki renkli kareler; geri kalan padding"
      1: "0x80 ayracı — padding başlangıç byte'ı"
      2: "0x00 dolgusu — 56 byte'a tamamlanır"
      3: "Son 8 byte — mesaj uzunluğu (big-endian)"
      4: "Padding tamamlandı — N byte / K blok"
    """

    _TICK_MS = 60
    _PHASE_DWELL_TICKS = 83

    def __init__(
        self,
        message_bytes: bytes,
        padded_bytes: bytes,
        blocks_count: int,
        message_text: str = "",
        on_finished=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from animation_modals.byte_widgets import _ByteStripWidget

        self._message_text = message_text
        self._message_bytes = message_bytes
        self._padded_bytes = padded_bytes
        self._blocks_count = blocks_count
        self._on_finished = on_finished
        self._current_block = 0
        self._tick = 0
        self._phase = 0
        self._finished = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        # Başlık
        title = QLabel("Adım 2 / 5  Padding ve Blok Yapısı")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        self._title_lbl = title
        self._msg_is_empty = len(message_bytes) == 0

        # Mesaj label — Adım 1 ile simetri; kullanıcının yazdığı metin tam
        # haliyle görünür (word-wrap ile uzun mesajlar alt satıra iner).
        if len(message_bytes) == 0:
            msg_label_text = "<i>(boş mesaj)</i>"
            msg_color = ANIM_COLORS["text_muted"]
        else:
            msg_label_text = f"Mesaj: \"{message_text}\""
            msg_color = ANIM_COLORS["text_secondary"]
        self._msg_lbl = QLabel(msg_label_text)
        self._msg_lbl.setFont(QFont("IBM Plex Sans", 11))
        self._msg_lbl.setStyleSheet(f"color: {msg_color};")
        self._msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._msg_lbl.setWordWrap(True)
        lay.addWidget(self._msg_lbl)

        # Info etiketi — padding bileşenlerinin SAYILARIYLA (kaç 0x80, kaç
        # 0x00, kaç uzunluk baytı) gösterilir ki kullanıcı '0x00 dolgu'nun
        # somut olarak kaç sıfır bayt olduğunu görsün.
        bd = self._padding_breakdown()
        if len(message_bytes) == 0:
            info_text = (
                f"Boş mesaj → padding: 1 byte ayraç (0x80) + {bd['zeros']} byte "
                f"sıfır (0x00) + 8 byte uzunluk = {bd['total']} byte (1 blok)"
            )
        else:
            info_text = (
                f"Padding: {bd['msg']} byte mesaj + 1 byte ayraç (0x80) + "
                f"{bd['zeros']} byte sıfır (0x00) + 8 byte uzunluk = "
                f"{bd['total']} byte ({blocks_count} blok)"
            )
        self._info_lbl = QLabel(info_text)
        self._info_lbl.setFont(QFont("IBM Plex Sans", 10))
        self._info_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_lbl.setWordWrap(True)
        lay.addWidget(self._info_lbl)

        # Blok navigasyon butonları — eskiden burada başlıkla grid arasındaydı;
        # kullanıcı geri bildirimi: yatay scrollbar'ın hemen ÜSTÜNDE, sol-alt
        # köşede küçük butonlar olsun. Buton oluşturuluyor ama lay'e burada
        # eklenmiyor — grid'den sonra eklenecek (aşağı bak).
        self._block_lbl = None
        self._btn_prev_block = None
        self._btn_next_block = None
        if blocks_count > 1:
            self._btn_prev_block = QPushButton("◀ Önceki")
            self._btn_prev_block.setFont(QFont("IBM Plex Sans", 8))
            self._btn_prev_block.setFixedHeight(22)
            self._btn_prev_block.setMaximumWidth(82)
            self._btn_prev_block.clicked.connect(self._prev_block)
            self._btn_prev_block.setEnabled(False)

            self._block_lbl = QLabel(f"Blok 1 / {blocks_count}")
            self._block_lbl.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            self._block_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
            self._block_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._block_lbl.setFixedHeight(22)

            self._btn_next_block = QPushButton("Sonraki ▶")
            self._btn_next_block.setFont(QFont("IBM Plex Sans", 8))
            self._btn_next_block.setFixedHeight(22)
            self._btn_next_block.setMaximumWidth(82)
            self._btn_next_block.clicked.connect(self._next_block)
            self._btn_next_block.setEnabled(blocks_count > 1)

        # Faz etiketi — kullanıcıya hangi padding bileşeninin vurgulandığını söyler
        self._phase_lbl = QLabel(self._phase_label_text(0))
        self._phase_lbl.setFont(QFont("IBM Plex Sans", 9, QFont.Weight.Bold))
        self._phase_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
        self._phase_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._phase_lbl.setWordWrap(True)
        lay.addWidget(self._phase_lbl)

        # 64 byte detay grid'i — TÜM padded blok karakter/ASCII/hex/binary
        # satırları halinde gösterilir. Mesaj byte'ları normal renkli; padding
        # byte'ları (0x80 + 0x00 dolgu + 8 byte length) beyaz 2px border +
        # alpha 0.7 + [80]/[00]/[len] etiketleriyle ayrışır. Yatay scroll
        # ile tüm 64 byte erişilebilir (sığmadığında).
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        initial_mask = self._full_padding_mask()
        initial_labels = self._full_padding_labels()
        # Hücre boyutu: 66×36 — binary satırı (Courier 9pt "01100101"
        # ≈ 56 px) için 10 px padding'le rahat sığacak taban. Tüm satırlar
        # (Karakter / ASCII / Hex / Binary) aynı 66 px genişliği kullanır;
        # böylece satırlar bütünsel görünür ve binary kesilmez.
        # (Önceki 54×34 + 9pt zaman zaman 1-2 px taşıyabiliyordu.)
        self._grid = _ColoredByteGridWidget(
            self._current_block_bytes(),
            max_cells=64,
            cell_w=66,
            cell_h=36,
            padding_mask=initial_mask,
            padding_labels=initial_labels,
        )
        # 64 hücre × (66+3) + label (80) + sol kenar (6) ≈ 4502 px sabit
        # (yatay scroll mevcut, görsel etki yok — kullanıcı scroll'la
        # 64 baytı tek tek gezebilir).
        grid_width = 80 + 6 + 64 * (66 + 3)
        grid_height = 4 * (36 + 4) + 30 + 16  # 4 satır + padding etiket alanı
        self._grid.setFixedSize(grid_width, grid_height)

        grid_scroll = QScrollArea()
        grid_scroll.setWidget(self._grid)
        grid_scroll.setWidgetResizable(False)  # sabit boyut + yatay scroll
        grid_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        grid_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        grid_scroll.setStyleSheet("background: transparent; border: none;")
        grid_scroll.setFixedHeight(grid_height + 24)
        lay.addWidget(grid_scroll)
        self._grid_scroll = grid_scroll

        # Blok navigasyon satırı — grid scroll'un HEMEN ALTINA, sol-alta küçük
        # butonlar olarak yerleştirilir (kullanıcı isteği). Sağ tarafta esnek
        # boşluk → tek mesajda nav row dahil edilmez.
        if blocks_count > 1:
            nav_row = QHBoxLayout()
            nav_row.setContentsMargins(0, 0, 0, 0)
            nav_row.setSpacing(6)
            nav_row.addWidget(self._btn_prev_block)
            nav_row.addWidget(self._block_lbl)
            nav_row.addWidget(self._btn_next_block)
            nav_row.addStretch(1)   # geri kalan boşluğu sağa it
            lay.addLayout(nav_row)

        # Bit length etiketi — son 8 byte'ın GERÇEK değeri (big-endian 64-bit
        # mesaj uzunluğu) gösterilir; kullanıcı 'son 8 byte'ın ne olduğunu
        # ve değerinin bilindiğini (mesaj uzunluğu) somut görür.
        self._bitlen_lbl = QLabel(
            f"Son 8 byte (uzunluk alanı): {bd['bit_len']} bit = "
            f"{bd['last8_hex']}  (big-endian)"
        )
        self._bitlen_lbl.setFont(QFont("Courier New", 9))
        self._bitlen_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._bitlen_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bitlen_lbl.setVisible(False)
        lay.addWidget(self._bitlen_lbl)

        # NOT: addStretch() çıkarıldı — sayfada gereksiz dikey boşluk yaratıyordu.

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def restyle(self) -> None:
        """Tema değişiminde QLabel stillerini DURUM BOZMADAN yeniden uygular
        (metin/görünürlük/faz/timer korunur). İçteki _ColoredByteGridWidget
        QPainter'dır → refresh_theme'deki update() ile yenilenir."""
        self._title_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        msg_color = (ANIM_COLORS["text_muted"] if self._msg_is_empty
                     else ANIM_COLORS["text_secondary"])
        self._msg_lbl.setStyleSheet(f"color: {msg_color};")
        self._info_lbl.setStyleSheet(
            f"color: {ANIM_COLORS['text_secondary']};")
        self._phase_lbl.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']};")
        self._bitlen_lbl.setStyleSheet(
            f"color: {ANIM_COLORS['accent_yellow']};")
        if self._block_lbl is not None:
            self._block_lbl.setStyleSheet(
                f"color: {ANIM_COLORS['accent_yellow']};")

    def _full_padding_mask(self) -> list[bool]:
        """Tam padding mask — mesaj byte'ları False, geri kalan tüm
        padding bileşenleri (0x80, 0x00 dolgu, length) True. İlk blok için
        mesaj uzunluğuna göre hesaplanır; sonraki bloklar tamamen padding."""
        n_msg = len(self._message_bytes)
        if self._current_block == 0:
            # İlk 64 byte içinde mesaj byte'larından sonraki her şey padding
            cutoff = min(n_msg, 64)
            return [False] * cutoff + [True] * (64 - cutoff)
        # Sonraki bloklar: tamamen padding (mesaj zaten önceki bloklarda)
        return [True] * 64

    def _full_padding_labels(self) -> list[str]:
        """Her byte için padding türü etiketi: mesaj byte'larında '' (etiket
        yok), 0x80 → '80', 0x00 → '00', son 8 byte → 'len'. Kullanıcı her
        kutucuğun hangi padding bileşenine ait olduğunu okuyarak görür."""
        block_data = self._current_block_bytes()
        block_start = self._current_block * 64
        total_padded = len(self._padded_bytes)
        n_msg_total = len(self._message_bytes)
        last8_start = total_padded - 8  # mesaj uzunluğu byte'larının başlangıcı
        labels: list[str] = []
        for i, byte_val in enumerate(block_data):
            absolute = block_start + i
            if absolute < n_msg_total:
                labels.append("")  # mesaj byte'ı — etiket yok
            elif absolute >= last8_start:
                labels.append("len")  # son 8 byte: mesaj uzunluğu
            elif byte_val == 0x80:
                labels.append("80")  # padding ayracı
            else:
                labels.append("00")  # sıfır dolgu
        # 64'e tamamla (eksikse boş etiket)
        while len(labels) < 64:
            labels.append("")
        return labels[:64]

    def _padding_breakdown(self) -> dict:
        """Padding bileşenlerini SAYILARIYLA döndürür (açıklama etiketleri için).

        SHA-256 padding'i: mesaj baytları + 1 byte ayraç (0x80) + N byte sıfır
        (0x00) + 8 byte mesaj-uzunluğu (big-endian, bit cinsinden). Bu yardımcı
        her bileşenin kaç bayt olduğunu ve son 8 baytın gerçek değerini verir.

        Dönüş: ``{'msg','zeros','total','bit_len','last8_hex'}``. zeros =
        toplam − mesaj − 1 (0x80) − 8 (uzunluk); last8_hex son 8 baytın
        boşlukla ayrılmış 2-hane hex'i (uzunluk alanının gerçek değeri).
        """
        n = len(self._message_bytes)
        total = len(self._padded_bytes)
        zeros = total - n - 1 - 8  # mesaj + 1 ayraç(0x80) + zeros + 8 uzunluk
        last8 = self._padded_bytes[-8:]
        return {
            "msg": n,
            "zeros": zeros,
            "total": total,
            "bit_len": n * 8,
            "last8_hex": " ".join(f"{b:02X}" for b in last8),
        }

    def _phase_label_text(self, phase: int) -> str:
        """Aktif faza göre kullanıcıya ne vurgulandığını anlatan etiket."""
        n_msg = len(self._message_bytes)
        bd = self._padding_breakdown()
        if phase == 0:
            if n_msg == 0:
                return "Boş mesaj — tüm 64 byte padding (0x80 + 0x00 dolgu + uzunluk)"
            return (
                f"Soldaki {n_msg} renkli kare = kullanıcının metni; "
                f"geri kalan {64 - min(n_msg, 64)} kare = padding"
            )
        if phase == 1:
            return ("0x80 = ikili 1000 0000 — mesajın bittiğini gösteren "
                    "zorunlu tek '1' biti (ayraç)")
        if phase == 2:
            return (f"0x00 dolgusu — {bd['zeros']} adet sıfır bayt; blok 56 "
                    f"byte'a tamamlanır (sonra 8 byte uzunluk gelir)")
        if phase == 3:
            return (
                "Mesaj başta, 0x80 + 0x00 dolgusu ortada, mesaj uzunluğu en "
                f"sonda: {bd['bit_len']} bit → {bd['last8_hex']}. Neden sonda? "
                "Blok tam 64 byte'a tamamlansın ve hash mesajın GERÇEK uzunluğunu "
                "da içersin; böylece farklı uzunluktaki mesajlar ayırt edilsin."
            )
        return (
            f"Padding tamamlandı — {len(self._padded_bytes)} byte / "
            f"{self._blocks_count} blok"
        )

    def _current_block_bytes(self) -> bytes:
        start = self._current_block * 64
        return self._padded_bytes[start:start + 64]

    def start(self) -> None:
        self._timer.start(get_animation_tick_ms(self._TICK_MS))

    def _on_tick(self) -> None:
        """Padding açıklamalarını yaklaşık beş saniyelik aralıklarla sırayla gösterir."""
        # Veri görseli baştan tam — fazlar sadece açıklama etiketini günceller.
        # Bu sayede kullanıcı "yazdığım yazı / padding" ayrımını anında görür,
        # fazlar her bir padding bileşenini sırayla vurgular.
        self._tick += 1
        dwell = self._PHASE_DWELL_TICKS
        if self._tick == dwell:
            self._phase = 1
            self._phase_lbl.setText(self._phase_label_text(1))
        elif self._tick == dwell * 2:
            self._phase = 2
            self._phase_lbl.setText(self._phase_label_text(2))
        elif self._tick == dwell * 3:
            self._phase = 3
            self._phase_lbl.setText(self._phase_label_text(3))
            self._bitlen_lbl.setVisible(True)
        elif self._tick >= dwell * 4:
            self._phase = 4
            self._phase_lbl.setText(self._phase_label_text(4))
            self._jump_to_final()

    def _jump_to_final(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        if self._on_finished:
            self._on_finished()

    def _prev_block(self) -> None:
        if self._current_block > 0:
            self._current_block -= 1
            self._update_block_view()

    def _next_block(self) -> None:
        if self._current_block < self._blocks_count - 1:
            self._current_block += 1
            self._update_block_view()

    def _update_block_view(self) -> None:
        if self._block_lbl is not None:
            self._block_lbl.setText(f"Blok {self._current_block + 1} / {self._blocks_count}")
        if self._btn_prev_block is not None:
            self._btn_prev_block.setEnabled(self._current_block > 0)
        if self._btn_next_block is not None:
            self._btn_next_block.setEnabled(self._current_block < self._blocks_count - 1)
        # Blok değişiminde tam mask + etiket uygulanır — mesaj/padding ayrımı
        # her blokta baştan görünür (sonraki bloklar tamamen padding).
        self._grid.set_data(
            self._current_block_bytes(),
            padding_mask=self._full_padding_mask(),
            padding_labels=self._full_padding_labels(),
        )

    def closeEvent(self, e) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(e)


