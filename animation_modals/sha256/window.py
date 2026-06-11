# animation_modals/sha256/window.py
"""SHA256AnimationWindow — SHA-256 hash sürecini görselleştirir."""
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
from ..base import CryptoAnimationWindow, ANIM_COLORS
from ..sha256_pure import sha256_steps
from .constants import _SNAPS_PER_BLOCK
from .diagram_widget import _SHA256DiagramWidget
from .w_expansion import _WExpansionWidget
from .match_widget import _MatchAssemblyWidget
from .intro_widget import _SHA256IntroWidget
from .prep_widget import _SHAMessagePrepWidget, _SHA256PaddingWidget

# ---------------------------------------------------------------------------
# SHA-256 Animasyon Penceresi
# ---------------------------------------------------------------------------

class SHA256AnimationWindow(CryptoAnimationWindow):
    """
    SHA-256 animasyon penceresi.

    Mantıksal adımlar (kullanıcı görünümü):
      Adım 1 / 5 : Mesaj Hazırlığı (UTF-8 byte dönüşümü)
      Adım 2 / 5 : Padding ve Blok Yapısı
      Adım 3 / 5 : Mesaj Genişletme (W_i)
      Adım 4 / 5 : Sıkıştırma Round Diyagramı (her snapshot bir alt adım)
      Adım 5 / 5 : Hash Eşleşmesi

    Underlying step_idx (progress bar):
      0         : Mesaj Hazırlığı
      1         : Padding
      2         : W expansion
      3..N+2    : Round snapshot'ları
      N+3       : Match (otomatik _show_match_result tetiklenir)

    Parametreler:
      message      : kullanıcının orijinal mesaj metni
      expected_hash: crypto_core'un ürettiği hex hash
    """

    _TITLES = [
        "Adım 1 / 5  Mesaj Hazırlığı",
        "Adım 2 / 5  Padding ve Blok Yapısı",
        "Adım 3 / 5  Mesaj Genişletme (W_i)",
        "Adım 4 / 5  Sıkıştırma Round Diyagramı",
        "Adım 5 / 5  Hash Eşleşmesi",
    ]
    _CAPTIONS = [
        "Metnin UTF-8 byte dizisine dönüşümü",
        "0x80 ayracı, 0x00 dolgu, 64-bit uzunluk eki",
        "İlk 16 word'den W[16..63] türetilir",
        "64 round, A..H register güncellemesi",
        "Final H[0..7] birleştirme + beklenen hash karşılaştırması",
    ]

    def __init__(
        self,
        message: str,
        expected_hash: str,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self._message = message
        self._expected_hash = expected_hash
        self._data = sha256_steps(message.encode("utf-8"))

        # Adım 0: mesaj hazırlığı (UTF-8 byte dönüşümü)
        # Adım 1: padding
        # Adım 2: W_i mesaj genişletme
        # Adım 3..len(snaps)+2: her blok için 9 snapshot (round 1,9,17,25,33,41,49,57,64)
        # Son adım: eşleşme (_show_match_result)
        snaps = self._data["round_snapshots"]
        total = 3 + len(snaps)   # message_prep + padding + W_i genişletme + all snapshots
        super().__init__(
            "SHA-256 Hash Animasyonu",
            total,
            manual_mode=True,
            on_close=on_close,
        )
        self._snaps = snaps

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _restyle_content(self) -> None:
        """Tema değişiminde QLabel/QFrame tabanlı içeriği DURUM BOZMADAN yeniden
        boyar (içerik rebuild edilmez; current_step/timer/görünür sayfa korunur).
        QPainter sayfaları (diagram, register demo, W genişletme, eşleşme)
        refresh_theme'deki update() ile canlı yenilenir."""
        # QLabel tabanlı sayfa widget'ları
        for w in (
            getattr(self, "_page_intro", None),
            getattr(self, "_msgprep_widget", None),
            getattr(self, "_padding_widget", None),
        ):
            if w is not None and hasattr(w, "restyle"):
                w.restyle()

        # _make_wexpand_page başlığı
        if hasattr(self, "_wexpand_title"):
            self._wexpand_title.setStyleSheet(
                f"color: {ANIM_COLORS['accent_mauve']};")

        # _make_match_page başlığı
        if hasattr(self, "_match_title"):
            self._match_title.setStyleSheet(
                f"color: {ANIM_COLORS['accent_green']};")

        # _make_diagram_page chrome'u (başlık, round bar, blok nav, zincir)
        if hasattr(self, "_diag_title"):
            self._diag_title.setStyleSheet(
                f"color: {ANIM_COLORS['accent_yellow']};")
        if hasattr(self, "_diag_rb_frame"):
            self._diag_rb_frame.setStyleSheet(
                f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
                f"border-radius: 6px; }}"
            )
        if getattr(self, "_diag_blk_lbl", None) is not None:
            self._diag_blk_lbl.setStyleSheet(
                f"color: {ANIM_COLORS['accent_yellow']};")
        if getattr(self, "_diag_sep", None) is not None:
            self._diag_sep.setStyleSheet(f"color: {ANIM_COLORS['border']};")
        if hasattr(self, "_diag_round_btns"):
            active = getattr(self, "_diag_active_round_idx", 0)
            for i, btn in enumerate(self._diag_round_btns):
                btn.setStyleSheet(self._diag_round_btn_style(i == active))
        if hasattr(self, "_chain_lbl"):
            self._chain_lbl.setStyleSheet(
                f"color: {ANIM_COLORS['text_muted']};")

    def _init_content(self) -> None:
        from PyQt6.QtWidgets import QStackedWidget

        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Ön tanıtma (intro). Akış şeması adım adım açıldığında
        # widget'ın sizeHint'i ~480 px'e ulaşıyor → QStackedWidget tüm
        # sayfalara bu yüksekliği dayatıyordu (Adım 2'de bile butonlar
        # ekrandan dışarı itiliyordu). Intro'yu kendi vertical scroll'una
        # sarıyoruz; sayfa intrinsic yüksekliği 290 px'te kalır, intro
        # içeriği gerekirse kullanıcı sayfada dikey scroll yapar.
        self._page_intro = _SHA256IntroWidget(on_start=self._switch_to_content)
        intro_scroll = QScrollArea()
        intro_scroll.setWidget(self._page_intro)
        intro_scroll.setWidgetResizable(True)
        intro_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        intro_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        intro_scroll.setStyleSheet("background: transparent; border: none;")
        intro_scroll.setMinimumHeight(260)
        self._stack.addWidget(intro_scroll)

        # Sayfa 1 — Mesaj Hazırlığı (yeni, Adım 1/5)
        self._page_msgprep = self._make_msgprep_page()
        self._stack.addWidget(self._page_msgprep)

        # Sayfa 2 — Padding (Adım 2/5)
        self._page_padding = self._make_padding_page()
        self._stack.addWidget(self._page_padding)

        # Sayfa 3 — Mesaj Genişletme (W_i) (Adım 3/5)
        self._page_wexpand = self._make_wexpand_page()
        self._stack.addWidget(self._page_wexpand)

        # Sayfa 4 — Kompresyon diyagramı (Adım 4/5, tüm snapshot'lar için tek sayfa, veri güncellenir)
        self._page_diagram = self._make_diagram_page()
        self._stack.addWidget(self._page_diagram)

        # Sayfa 5 — Eşleşme (Adım 5/5)
        self._page_match = self._make_match_page()
        self._stack.addWidget(self._page_match)

        # Intro animasyonunu başlat
        self._page_intro.start()

    def _make_msgprep_page(self) -> QWidget:
        """Yeni Mesaj Hazırlığı sayfası — _SHAMessagePrepWidget içerir.
        Widget üste hizalanır ki büyük pencerelerde alt boşluk olmasın."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)
        self._msgprep_widget = _SHAMessagePrepWidget(
            message_text=self._data["message_text"],
            message_bytes=self._data["message_bytes"],
            on_finished=self._on_msgprep_finished,
        )
        lay.addWidget(self._msgprep_widget, alignment=Qt.AlignmentFlag.AlignTop)
        return w

    def _on_msgprep_finished(self) -> None:
        """Mesaj Hazırlığı animasyonu bittiğinde — İleri butonu zaten manuel."""
        # Manuel modda buton zaten enabled, ek aksiyon gerekmez.
        # Bu callback, gelecekte buton durum yönetimi gerekirse genişler.
        pass

    def _make_padding_page(self) -> QWidget:
        """Yeni padding sayfası — _SHA256PaddingWidget içerir.
        Outer QScrollArea kaldırıldı: widget zaten kompakt, scroll gerekmez."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        self._padding_widget = _SHA256PaddingWidget(
            message_bytes=self._data["message_bytes"],
            padded_bytes=self._data["padded_bytes"],
            blocks_count=self._data["blocks_count"],
            message_text=self._data["message_text"],
        )
        lay.addWidget(self._padding_widget, alignment=Qt.AlignmentFlag.AlignTop)
        return w

    def _make_wexpand_page(self) -> QWidget:
        """Mesaj genişletme sayfası — _WExpansionWidget içerir.
        Widget min 340 px; içerik kompakt sayfalarda bile stack'in tercih
        yüksekliğini büyütüyordu. Scroll'a sararak sayfanın doğal yüksekliği
        ~290 px'te kalır, alt navigasyon butonları daima görünür."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Adım 2  Mesaj Genişletme (Message Schedule)")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_mauve']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        self._wexpand_title = title

        widget = _WExpansionWidget(self._data.get("w_expansion") or [])
        wexp_scroll = QScrollArea()
        wexp_scroll.setWidget(widget)
        wexp_scroll.setWidgetResizable(True)
        wexp_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        wexp_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        wexp_scroll.setStyleSheet("background: transparent; border: none;")
        wexp_scroll.setMinimumHeight(260)
        lay.addWidget(wexp_scroll, stretch=1)
        return w

    def _make_diagram_page(self) -> QWidget:
        # Sayfa düzeni:
        #   - Başlık (Blok N / Sıkıştırma Round M)
        #   - Round bar (tıklanabilir 9 buton: R1, R9, R17, ..., R64)
        #     + çok blok varsa solda blok seçici (◀ Blok N/M Blok ▶)
        #   - Diyagram widget'ı QScrollArea'da (stack height kontrolü)
        #   - Hash zinciri göstergesi
        #
        # Round bar AES'in tıklanabilir round bar deseninden esinleniyor;
        # kullanıcı bottom-bar ◀/▶ butonlarına gitmeden diyagramda
        # roundlar arası gezebilir.
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(4)

        self._diag_title = QLabel()
        self._diag_title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        self._diag_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._diag_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._diag_title)

        # Round bar (tıklanabilir 9 buton — her snapshot için). Çok blok
        # varsa solda blok navigasyonu.
        rb_frame = QFrame()
        rb_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px; }}"
        )
        self._diag_rb_frame = rb_frame
        rb_lay = QHBoxLayout(rb_frame)
        rb_lay.setContentsMargins(6, 4, 6, 4)
        rb_lay.setSpacing(4)

        # Blok navigasyonu — yalnızca >1 blok varsa
        self._diag_blk_prev: QPushButton | None = None
        self._diag_blk_next: QPushButton | None = None
        self._diag_blk_lbl: QLabel | None = None
        self._diag_sep: QLabel | None = None
        if self._data["blocks_count"] > 1:
            self._diag_blk_prev = QPushButton("◀ Blok")
            self._diag_blk_prev.setFixedHeight(28)
            self._diag_blk_prev.setFont(QFont("IBM Plex Sans", 9))
            self._diag_blk_prev.clicked.connect(
                lambda: self._diag_jump_block(-1))
            rb_lay.addWidget(self._diag_blk_prev)

            self._diag_blk_lbl = QLabel(f"Blok 1 / {self._data['blocks_count']}")
            self._diag_blk_lbl.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            self._diag_blk_lbl.setStyleSheet(
                f"color: {ANIM_COLORS['accent_yellow']};")
            self._diag_blk_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._diag_blk_lbl.setMinimumWidth(80)
            rb_lay.addWidget(self._diag_blk_lbl)

            self._diag_blk_next = QPushButton("Blok ▶")
            self._diag_blk_next.setFixedHeight(28)
            self._diag_blk_next.setFont(QFont("IBM Plex Sans", 9))
            self._diag_blk_next.clicked.connect(
                lambda: self._diag_jump_block(+1))
            rb_lay.addWidget(self._diag_blk_next)

            sep = QLabel("│")
            sep.setStyleSheet(f"color: {ANIM_COLORS['border']};")
            rb_lay.addWidget(sep)
            self._diag_sep = sep

        # Round buton dizisi — 9 buton (snapshot başına bir tane). Her buton
        # temsil ettiği sıkıştırma round'unu açıkça gösterir ("R1", "R9", ...).
        # Butonlar bar genişliğine EŞİT olarak yayılır (stretch=1) ve sabit
        # genişlik kaldırılır → kutular bar'ı tam doldurur, sağda boş alan
        # kalmaz; hangi round'a karşılık geldikleri net görünür.
        self._diag_active_round_idx = 0
        self._diag_round_btns: list[QPushButton] = []
        round_labels = ["R1", "R9", "R17", "R25", "R33", "R41", "R49", "R57", "R64"]
        for idx, lbl in enumerate(round_labels):
            btn = QPushButton(lbl)
            btn.setMinimumWidth(42)
            btn.setFixedHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            # Courier New dar viewport'ta sıkışıp okunmuyordu (Görsel 3).
            # IBM Plex Sans 10pt Bold daha okunur; etiketler kısa (R1..R64).
            btn.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
            btn.setStyleSheet(self._diag_round_btn_style(False))
            btn.clicked.connect(lambda checked=False, i=idx: self._diag_jump_round(i))
            rb_lay.addWidget(btn, stretch=1)
            self._diag_round_btns.append(btn)

        lay.addWidget(rb_frame)

        # Diyagramı dikey scroll içine al — diyagram min yüksekliği 265 px;
        # scroll viewport'unu buna yetecek kadar (285 px) açıyoruz ki diyagram
        # (giriş/çıkış kutuları + legend + aşama etiketi) DİKEY scroll
        # gerektirmeden tek bakışta görünsün. Scroll yalnızca çok kısa
        # pencerelerde devreye girer (güvenlik ağı).
        self._diag_widget = _SHA256DiagramWidget()
        diag_scroll = QScrollArea()
        diag_scroll.setWidget(self._diag_widget)
        diag_scroll.setWidgetResizable(True)
        diag_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        diag_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        diag_scroll.setStyleSheet("background: transparent; border: none;")
        diag_scroll.setMinimumHeight(285)
        lay.addWidget(diag_scroll, stretch=1)

        # Hash zinciri göstergesi (alt)
        self._chain_lbl = QLabel()
        self._chain_lbl.setFont(QFont("Courier New", 10))
        self._chain_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._chain_lbl.setWordWrap(True)
        self._chain_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._chain_lbl)
        return w

    @staticmethod
    def _diag_round_btn_style(active: bool) -> str:
        """Round seçici buton stili. Aktif/pasif AYNI 2px border kalınlığını
        kullanır (yalnızca renkle ayrılır) → aktif buton değişince layout
        kaymaz. Padding eklenerek etiket sıkışması (Görsel 3) giderilir."""
        if active:
            return (
                f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
                f"color: {ANIM_COLORS['text_on_accent']}; border: 2px solid {ANIM_COLORS['accent_blue']}; "
                f"border-radius: 4px; padding: 2px 4px; font-weight: bold; }}"
            )
        return (
            f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_secondary']}; "
            f"border: 2px solid {ANIM_COLORS['border']}; "
            f"border-radius: 4px; padding: 2px 4px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['text_on_accent']}; border-color: {ANIM_COLORS['accent_blue']}; }}"
        )

    def _diag_jump_round(self, round_idx_in_block: int) -> None:
        """Round bar'daki butonla aynı blok içinde başka bir snapshot'a atla.
        round_idx_in_block: 0..8 (R1, R9, R17, ..., R64'e karşılık gelir)."""
        # Mevcut blok numarasını current_step'ten çıkar
        cur_snap_idx = self.current_step - 3
        if cur_snap_idx < 0 or cur_snap_idx >= len(self._snaps):
            cur_block = 0
        else:
            cur_block = cur_snap_idx // _SNAPS_PER_BLOCK
        target_snap_idx = cur_block * _SNAPS_PER_BLOCK + round_idx_in_block
        if target_snap_idx >= len(self._snaps):
            return
        self._diag_jump_to_step(3 + target_snap_idx)

    def _diag_jump_block(self, delta: int) -> None:
        """◀ Blok / Blok ▶ butonu — aynı round (snapshot in-block index)
        konumunu koruyarak farklı bloka atla."""
        cur_snap_idx = self.current_step - 3
        if cur_snap_idx < 0 or cur_snap_idx >= len(self._snaps):
            return
        cur_block = cur_snap_idx // _SNAPS_PER_BLOCK
        in_block_idx = cur_snap_idx % _SNAPS_PER_BLOCK
        new_block = cur_block + delta
        if new_block < 0 or new_block >= self._data["blocks_count"]:
            return
        target_snap_idx = new_block * _SNAPS_PER_BLOCK + in_block_idx
        if target_snap_idx >= len(self._snaps):
            return
        self._diag_jump_to_step(3 + target_snap_idx)

    def _diag_jump_to_step(self, target_step: int) -> None:
        """Diyagram sayfasındaki butonlardan birine basıldığında modal'ın
        current_step / progress / bottom button state'ini güncelleyerek
        hedef adıma atla (AES'in _jump_to_round desenine paralel)."""
        self.current_step = target_step
        self._render_step(target_step)
        self._progress.setValue(target_step + 1)
        if hasattr(self, "_btn_prev"):
            self._btn_prev.setEnabled(target_step > 0)
        if hasattr(self, "_btn_next"):
            self._btn_next.setEnabled(True)
            self._btn_next.setText("İleri  ▶")

    def _diag_update_round_bar(self, in_block_idx: int) -> None:
        self._diag_active_round_idx = in_block_idx
        for i, btn in enumerate(self._diag_round_btns):
            btn.setStyleSheet(self._diag_round_btn_style(i == in_block_idx))

    def _make_match_page(self) -> QWidget:
        """Final eşleşme sayfası — _MatchAssemblyWidget içerir.
        Widget setMinimumHeight(460) ile QStackedWidget'ın max sizeHint'ini
        domine ediyordu → diğer kompakt sayfalarda bile modal'ın tercih
        yüksekliği 460+ olunca alice panelindeki viewport'a sığmıyor,
        kullanıcı butonları görmek için dikey scroll yapmak zorunda kalıyordu.
        Match widget'ı kendi dikey QScrollArea'sına sararak bu 460 px talebi
        sayfanın doğal yüksekliğine yansımıyor (sayfa ~290 px'te kalıyor)."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Final Hash Eşleşmesi")
        title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        self._match_title = title

        self._match_widget = _MatchAssemblyWidget()
        match_scroll = QScrollArea()
        match_scroll.setWidget(self._match_widget)
        match_scroll.setWidgetResizable(True)
        match_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        match_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        match_scroll.setStyleSheet("background: transparent; border: none;")
        match_scroll.setMinimumHeight(260)
        lay.addWidget(match_scroll, stretch=1)
        return w

    # ------------------------------------------------------------------
    # Adım render'ı
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if step_idx == 0:
            self._stack.setCurrentWidget(self._page_msgprep)
            self._msgprep_widget.start()
            return
        if step_idx == 1:
            self._stack.setCurrentWidget(self._page_padding)
            self._padding_widget.start()
            return
        if step_idx == 2:
            self._stack.setCurrentWidget(self._page_wexpand)
            return

        # step_idx 3..len(snaps)+2 → snapshot[step_idx - 3]
        snap_idx = step_idx - 3
        if snap_idx >= len(self._snaps):
            return

        snap = self._snaps[snap_idx]
        self._stack.setCurrentWidget(self._page_diagram)

        # Hangi blok, hangi round?
        snap_round = snap["round"]
        block_no = snap_idx // _SNAPS_PER_BLOCK + 1
        in_block_idx = snap_idx % _SNAPS_PER_BLOCK
        self._diag_title.setText(
            f"Blok {block_no} / {self._data['blocks_count']}  —  "
            f"Sıkıştırma Round {snap_round} / 64"
        )
        # Round bar ve blok etiketi senkronize
        self._diag_update_round_bar(in_block_idx)
        if self._diag_blk_lbl is not None:
            self._diag_blk_lbl.setText(
                f"Blok {block_no} / {self._data['blocks_count']}")
        if self._diag_blk_prev is not None:
            self._diag_blk_prev.setEnabled(block_no > 1)
        if self._diag_blk_next is not None:
            self._diag_blk_next.setEnabled(
                block_no < self._data["blocks_count"])

        # Mevcut register değerleri (bu snapshot'taki çıkış)
        regs_out = snap["registers"]

        # Giriş register'ları: blok içindeyse önceki snapshot çıkışı; bloğun
        # İLK snapshot'ında ise o bloğun başlangıç chaining değeri. Önceden her
        # bloğun ilk snapshot'ı H0 sabitlerini gösteriyordu — blok 2+ için
        # yanlıştı (chaining yerine H0). block_initial_states[blok] doğru değeri
        # verir (blok 0 → H0, blok N → önceki blokların biriktirdiği hash).
        if snap_idx % _SNAPS_PER_BLOCK != 0:
            regs_in = self._snaps[snap_idx - 1]["registers"]
        else:
            block_idx = snap_idx // _SNAPS_PER_BLOCK
            states = self._data.get("block_initial_states") or []
            if block_idx < len(states):
                regs_in = states[block_idx]
            else:
                regs_in = self._data["initial_h"]  # güvenli geri-düşüş

        self._diag_widget.set_data(
            regs_in=regs_in,
            regs_out=regs_out,
            t1=snap.get("t1", "--------"),
            t2=snap.get("t2", "--------"),
            w=snap.get("w", "--------"),
            k=snap.get("k", "--------"),
            round_no=snap_round,
        )

        # Zincir göstergesi
        chain_parts = []
        for i in range(block_no):
            if i < block_no - 1:
                chain_parts.append(f"[Blok {i+1} →]")
            else:
                chain_parts.append(f"[Blok {i+1} ←burada]")
        self._chain_lbl.setText("  →  ".join(chain_parts) + "  →  [Final Hash]")

    def _show_match_result(self) -> None:
        """Final eşleşme sayfasını göster, animasyonu başlat."""
        self._stack.setCurrentWidget(self._page_match)
        self._match_widget.start_animation(
            pre_h=self._data["pre_final_h"],
            working=self._data["final_working"],
            parts=self._data["final_h_parts"],
            computed=self._data["final_hash"],
            expected=self._expected_hash,
        )

    # ------------------------------------------------------------------
    # Navigasyon yardımcıları
    # ------------------------------------------------------------------

    def _switch_to_content(self) -> None:
        """Intro'dan Mesaj Hazırlığı sayfasına geç ve step 0'ı render et."""
        self._render_step(0)
        self._progress.setValue(1)

    # showEvent override — intro kendi timer'ını yönetiyor, base class'ı atla
    def showEvent(self, event) -> None:  # type: ignore[override]
        QWidget.showEvent(self, event)
