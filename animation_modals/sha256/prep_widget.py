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

    _TICK_MS = 45

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
        """Mesaj byte görsellerini önceki kısa zaman çizelgesiyle sırayla açar."""
        self._tick += 1
        if self._is_empty:
            # Boş mesaj: kısa bir bekleme sonrası doğrudan faz 4'e
            if self._tick >= 12:
                self._jump_to_final()
            return

        if self._tick == 8:
            self._phase = 1
        elif self._tick == 26:
            self._phase = 2
        elif self._tick == 40:
            self._phase = 3
            self._strip.setVisible(True)
        elif self._tick >= 52:
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
    Veri başından sonuna aynı görünür. Mesaj, 0x80 ayracı, 0x00 dolgusu ve
    son 8 byte açıklamaları otomatik akmaz; kullanıcı ilgili düğmeye tıklayarak
    kendi okuma hızında tek ayrıntı alanında açar.
    """

    _TICK_MS = 60

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

        # Padding bileşenleri otomatik akan metin yerine kullanıcının seçimiyle
        # açıklanır. Düğmeler, ilgili bileşenlerin altında tek satırda durur.
        explanation_row = QHBoxLayout()
        explanation_row.setContentsMargins(0, 0, 0, 0)
        explanation_row.setSpacing(6)
        self._explanation_buttons: dict[str, QPushButton] = {}
        for key, text in (
            ("message", "Mesaj"),
            ("separator", "0x80 ayraç"),
            ("zeros", "0x00 dolgu"),
            ("length", "Son 8 byte"),
        ):
            button = QPushButton(text)
            button.setFont(QFont("IBM Plex Sans", 9, QFont.Weight.Bold))
            button.clicked.connect(
                lambda _checked=False, component=key: self._show_component_explanation(component)
            )
            explanation_row.addWidget(button, stretch=1)
            self._explanation_buttons[key] = button
        lay.addLayout(explanation_row)

        self._detail_explanation = QLabel()
        self._detail_explanation.setFont(QFont("IBM Plex Sans", 9))
        self._detail_explanation.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_explanation.setWordWrap(True)
        self._detail_explanation.setVisible(False)
        lay.addWidget(self._detail_explanation)

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
        self._detail_explanation.setStyleSheet(
            f"color: {ANIM_COLORS['text_secondary']}; "
            f"background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            "border-radius: 6px; padding: 8px;"
        )
        for button in self._explanation_buttons.values():
            button.setStyleSheet(
                f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
                f"color: {ANIM_COLORS['accent_yellow']}; "
                f"border: 1px solid {ANIM_COLORS['accent_yellow']}; "
                "border-radius: 5px; padding: 5px 8px; font-weight: bold; }}"
            )
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

    def _component_explanation(self, component: str) -> str:
        """Seçilen padding bileşeninin görevini gerçek mesaj değerleriyle açıklar."""
        bd = self._padding_breakdown()
        if component == "message":
            if bd["msg"] == 0:
                return "Mesaj boş olduğu için blok doğrudan padding bileşenleriyle başlar."
            return (
                f"Mesaj: İlk {bd['msg']} byte kullanıcının gerçek verisidir. "
                "SHA-256 bu baytları değiştirmez; padding bunların arkasına eklenir."
            )
        if component == "separator":
            return (
                "0x80 ayraç: Mesajın bittiği yere zorunlu tek '1' bitini ekler "
                "(ikili 1000 0000); ardından sıfır dolgusu başlar."
            )
        if component == "zeros":
            return (f"0x00 dolgusu — {bd['zeros']} adet sıfır bayt; blok 56 "
                    f"byte'a tamamlanır (sonra 8 byte uzunluk gelir)")
        if component == "length":
            return (
                "Son 8 byte, orijinal mesaj uzunluğunu bit cinsinden big-endian "
                f"kodlar: {bd['bit_len']} bit → {bd['last8_hex']}. Padding sonrası "
                "oluşan 64 byte blok, bu son 8 byte dahil, SHA-256 compression "
                "fonksiyonuna girdi olur; uzunluk alanı da diğer baytlarla birlikte "
                "hash sonucunu etkiler. Sonda durur çünkü standart, önce mesajı ve "
                "dolguyu yerleştirip son 64 biti uzunluk alanına ayırır."
            )
        return ""

    def _show_component_explanation(self, component: str) -> None:
        """Tıklanan padding bileşeninin açıklamasını tek ayrıntı alanında gösterir."""
        self._detail_explanation.setText(self._component_explanation(component))
        self._detail_explanation.setVisible(True)

    def _current_block_bytes(self) -> bytes:
        start = self._current_block * 64
        return self._padded_bytes[start:start + 64]

    def start(self) -> None:
        """Padding verisi hazır olduğundan otomatik metin akıtmadan sayfayı tamamlar."""
        self._jump_to_final()

    def _on_tick(self) -> None:
        """Geriye dönük timer çağrılarını otomatik açıklama değiştirmeden sonlandırır."""
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


