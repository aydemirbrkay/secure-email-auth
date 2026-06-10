# animation_modals/aes/window.py
"""AESAnimationWindow — AES-256-GCM şifreleme sürecini görselleştirir."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS
from ..aes_matrix_view import _AESStateCompareWidget
from ..aes_pure import aes256_encrypt_with_rounds
from .constants import _COLORS_OP
from .intro_widget import _AESIntroWidget
from .prep_widget import _AESPlaintextPrepWidget
from .op_widgets import (
    _ShiftRowsAnimWidget, _MixColumnsAnimWidget,
    _SubBytesAnimWidget, _AddRoundKeyAnimWidget,
)
from .steps import _build_steps
from .round_flow import _AESRoundFlowWidget

class AESAnimationWindow(CryptoAnimationWindow):
    """
    AES-256-GCM animasyon penceresi.

    Parametreler:
      key             : 32 byte session key
      plaintext       : şifrelenecek veri (ilk 16 byte kullanılır)
      expected_ct_hex : crypto_core AES-GCM çıktısının (ciphertext ‖ 16 byte
                        kimlik doğrulama etiketi) ilk 32 byte'ına ait hex
                        önizlemedir. Kısa mesajlarda bu önizleme tag
                        baytlarını da içerebilir; uzun mesajlarda ise
                        yalnızca ciphertext'in başlangıcı görünür.
    """

    def __init__(
        self,
        key: bytes,
        plaintext: bytes,
        expected_ct_hex: str,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self._key = key
        self._plaintext = plaintext
        self._expected_ct_hex = expected_ct_hex

        aes_result = aes256_encrypt_with_rounds(key, plaintext)
        self._steps_data = _build_steps(aes_result["rounds_data"])
        self._final_block_hex = aes_result["final_block_hex"]
        # Round flow widget için ek veri
        self._rounds_data = aes_result["rounds_data"]
        self._round_keys_hex = aes_result["round_keys_hex"]
        self._initial_state_hex = aes_result["initial_state_hex"]

        # Plaintext Hazırlığı sayfası için yeni alanlar (aes_pure'dan gelir)
        self._plaintext_text_str = aes_result.get("plaintext_text", "")
        self._plaintext_bytes_data = aes_result.get("plaintext_bytes", b"")
        self._padded_plaintext_data = aes_result.get("padded_plaintext", b"")
        self._first_block_data = aes_result.get("first_block", b"")
        self._blocks_total_data = aes_result.get("blocks_total", 1)
        self._state_matrix_data = aes_result.get(
            "state_matrix", [["--"] * 4 for _ in range(4)]
        )

        # round → ilk step indeksini hesapla
        self._round_start: dict[int, int] = {}
        for i, s in enumerate(self._steps_data):
            r = s["round"]
            if r not in self._round_start:
                self._round_start[r] = i

        # Başlangıçta intro görünür; manual_mode round görünümü için
        super().__init__(
            "AES-256-GCM Şifreleme Animasyonu",
            len(self._steps_data),
            manual_mode=True,
            on_close=on_close,
        )

        # Pencere boyutu base sınıftan gelir (standalone modda ekranın %82'si).
        # SHA introsuyla birebir aynı davranış için AES burada KENDİNİ KÜÇÜLTMEZ;
        # eskiden resize(820,620) intro'yu kompakt yapıyordu ama bu, stack'in
        # round/flow sayfa min-genişliklerinin pencereye sığmamasına ve intro
        # ekranında boşluklu yatay scroll'a yol açıyordu. Büyük açılınca intro
        # ekranı doldurur, butonlar sabit kalır, yatay scroll çıkmaz.

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Giriş animasyonu. SHA introsuyla aynı kalıp: intro'yu dikey
        # QScrollArea'ya sarıyoruz ki içerik adım adım açılırken sayfanın doğal
        # yüksekliği şişip alt navigasyon butonlarını dışarı itmesin (gerekirse
        # kullanıcı sayfa içinde dikey kaydırır; yatay kaydırma byte grid
        # adaptif olduğundan artık çıkmaz).
        from PyQt6.QtWidgets import QScrollArea
        self._intro = _AESIntroWidget(on_complete=self._switch_to_plaintext_prep)
        intro_scroll = QScrollArea()
        intro_scroll.setWidget(self._intro)
        intro_scroll.setWidgetResizable(True)
        intro_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        intro_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        intro_scroll.setStyleSheet("background: transparent; border: none;")
        intro_scroll.setMinimumHeight(260)
        self._stack.addWidget(intro_scroll)

        # Sayfa 1 — Plaintext Hazırlığı (yeni, tek seferlik pre-step)
        self._plaintext_page = self._make_plaintext_prep_page()
        self._stack.addWidget(self._plaintext_page)

        # Sayfa 2 — Round görünümü (tek round detayı)
        self._round_page = self._make_round_page()
        self._stack.addWidget(self._round_page)

        # Sayfa 3 — Tüm Roundlar Akışı (FIPS 197 tarzı)
        self._flow_page = self._make_flow_page()
        self._stack.addWidget(self._flow_page)

        # Sayfa 4 — Eşleşme sonucu
        self._match_page = self._make_match_page()
        self._stack.addWidget(self._match_page)

        # Intro başlat (otomatik)
        self._intro.start()

    def _make_plaintext_prep_page(self) -> QWidget:
        """Yeni Plaintext Hazırlığı sayfası — _AESPlaintextPrepWidget içerir."""
        from PyQt6.QtWidgets import QScrollArea
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        self._plaintext_widget = _AESPlaintextPrepWidget(
            plaintext_text=self._plaintext_text_str,
            plaintext_bytes=self._plaintext_bytes_data,
            padded_plaintext=self._padded_plaintext_data,
            first_block=self._first_block_data,
            blocks_total=self._blocks_total_data,
            state_matrix=self._state_matrix_data,
            on_continue=self._switch_to_rounds_only,
        )
        scroll = QScrollArea()
        scroll.setWidget(self._plaintext_widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    def _make_round_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        # Tıklanabilir round bar
        self._rb_frame = QFrame()
        rb_frame = self._rb_frame
        rb_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px; }}"
        )
        rb_lay = QHBoxLayout(rb_frame)
        rb_lay.setContentsMargins(6, 4, 6, 4)
        rb_lay.setSpacing(3)
        self._round_btns: list[QPushButton] = []
        for i in range(15):
            btn = QPushButton(f"R{i}")
            # Sabit 38px yerine: butonlar satır genişliğini eşit paylaşarak
            # yatayda genişler (yükseklik değişmez). Böylece round çubuğu tüm
            # genişliğe yayılır, sağda büyük boş alan kalmaz.
            btn.setMinimumWidth(34)
            btn.setFixedHeight(30)
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            # SHA round bar ile tutarlı: Courier New yerine daha okunur
            # IBM Plex Sans (Görsel 3 okunabilirlik düzeltmesi).
            btn.setFont(QFont("IBM Plex Sans", 9, QFont.Weight.Bold))
            btn.setStyleSheet(self._round_btn_style(False))
            btn.clicked.connect(lambda checked, r=i: self._jump_to_round(r))
            rb_lay.addWidget(btn, stretch=1)
            self._round_btns.append(btn)

        # Tüm Roundlar Akışı butonu — sabit boyutta, round butonlarının
        # sağında; küçük bir boşlukla ayrılır ("Tüm Akış" yazısı kırpılmaz).
        rb_lay.addSpacing(6)
        self._flow_btn = QPushButton("Tüm Akış")
        flow_btn = self._flow_btn
        flow_btn.setFixedHeight(28)
        flow_btn.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        flow_btn.setStyleSheet(self._flow_btn_style())
        flow_btn.clicked.connect(self._switch_to_flow_view)
        rb_lay.addWidget(flow_btn)
        lay.addWidget(rb_frame)

        # Operasyon başlığı
        self._op_title = QLabel()
        self._op_title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._op_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._op_title)

        # Açıklama
        self._desc_lbl = QLabel()
        self._desc_lbl.setFont(QFont("IBM Plex Sans", 10))
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_lbl.setWordWrap(True)
        lay.addWidget(self._desc_lbl)

        # Matris + yardımcı widget
        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        self._mat_frame = QFrame()
        mat_frame = self._mat_frame
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {ANIM_COLORS['accent_blue']}; border-radius: 8px; }}"
        )
        mat_lay = QVBoxLayout(mat_frame)
        mat_lay.setContentsMargins(8, 6, 8, 6)
        mat_lay.setSpacing(4)

        # Yan yana iki QPainter matris + Yeniden Oynat butonu.
        # Operasyon adı zaten _op_title (üstte) ve _arrow_label
        # (matrislerin arasında "→ OperationName →") tarafından
        # gösterildiği için ayrı bir matrix_context etiketi yok.
        self._matrix_pair = _AESStateCompareWidget(parent=self)
        mat_lay.addWidget(self._matrix_pair)

        content_row.addWidget(mat_frame)

        # Sağ panel — operasyona göre değişir. Min 300 ve max 470: yan panel
        # widget'ları (XOR/S-Box/MixColumns) büyütülen hücre ve yazılarına yer
        # bulsun, yazılar taşmadan sığsın; çok dar viewport'larda yine de
        # makul kalır (gerektiğinde dış kaydırma devreye girer).
        self._side_stack = QStackedWidget()
        self._side_stack.setMinimumWidth(300)
        self._side_stack.setMaximumWidth(470)

        empty = QWidget()  # boş panel (yedek)
        self._side_stack.addWidget(empty)                    # index 0

        # ShiftRows: scroll area içinde (4 satır × 92px = ~400px gerektirir)
        from PyQt6.QtWidgets import QScrollArea
        self._shift_widget = _ShiftRowsAnimWidget()
        shift_scroll = QScrollArea()
        shift_scroll.setWidget(self._shift_widget)
        shift_scroll.setWidgetResizable(True)
        shift_scroll.setStyleSheet("background: transparent; border: none;")
        self._side_stack.addWidget(shift_scroll)             # index 1

        self._mix_widget = _MixColumnsAnimWidget()           # MixColumns için
        self._side_stack.addWidget(self._mix_widget)         # index 2

        # SubBytes: byte → S-Box[byte] görselleştirmesi
        self._sub_widget = _SubBytesAnimWidget()
        sub_scroll = QScrollArea()
        sub_scroll.setWidget(self._sub_widget)
        sub_scroll.setWidgetResizable(True)
        sub_scroll.setStyleSheet("background: transparent; border: none;")
        self._side_stack.addWidget(sub_scroll)               # index 3

        # AddRoundKey: state ⊕ round_key = yeni state
        self._ark_widget = _AddRoundKeyAnimWidget()
        ark_scroll = QScrollArea()
        ark_scroll.setWidget(self._ark_widget)
        ark_scroll.setWidgetResizable(True)
        ark_scroll.setStyleSheet("background: transparent; border: none;")
        self._side_stack.addWidget(ark_scroll)               # index 4

        content_row.addWidget(self._side_stack)
        # content_row'u (matris 598px + side_stack 300px ≈ 920px) bir konteynere
        # koyup yatay scroll'a sarıyoruz. Aksi halde bu geniş min-width
        # QStackedWidget üzerinden TÜM sayfalara (intro dahil) yayılıp pencereyi
        # 820px'e küçülmekten alıkoyuyor ve intro ekranında gereksiz yatay scroll
        # bırakıyordu (Görsel 6). Scroll yalnızca dar pencerede devreye girer.
        content_wrap = QWidget()
        content_wrap.setLayout(content_row)
        row_scroll = QScrollArea()
        row_scroll.setWidget(content_wrap)
        row_scroll.setWidgetResizable(True)
        row_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        row_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        row_scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(row_scroll, stretch=1)
        return w

    def _make_flow_page(self) -> QWidget:
        """FIPS 197 tarzı tüm round akışı sayfası — scroll'lu liste."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        # Üst bar — geri dönüş + başlık
        top_row = QHBoxLayout()
        self._flow_back_btn = QPushButton("◀  Tek Round Detayı")
        self._flow_back_btn.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        self._flow_back_btn.setFixedHeight(30)
        self._flow_back_btn.setStyleSheet(self._flow_back_btn_style())
        self._flow_back_btn.clicked.connect(self._back_to_round_view)
        top_row.addWidget(self._flow_back_btn)

        self._flow_title = QLabel("Tüm 14 Round Akışı  (FIPS 197 referans biçimi)")
        self._flow_title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        self._flow_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._flow_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self._flow_title, stretch=1)
        top_row.addStretch()
        lay.addLayout(top_row)

        # Açıklayıcı alt başlık
        self._flow_legend = QLabel(
            "Her satır bir round'u gösterir. Soldan sağa: Başlangıç → SubBytes → "
            "ShiftRows → MixColumns ⊕ Round Key.   "
            "Round 0 sadece AddRoundKey içerir; Round 14'te MixColumns atlanır."
        )
        self._flow_legend.setFont(QFont("IBM Plex Sans", 9))
        self._flow_legend.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._flow_legend.setWordWrap(True)
        self._flow_legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Uzun tek-satır QLabel'ın minimumSizeHint'i ~960px'e çıkıp stack'i
        # (dolayısıyla intro sayfasını) şişiriyordu. Küçük min-width verilince
        # word-wrap devreye girer, sayfa dar pencerede de sığar, intro yatay
        # scroll kalmaz (Y1 sağlamlık).
        self._flow_legend.setMinimumWidth(240)
        lay.addWidget(self._flow_legend)

        # Scroll area içine yeni round flow widget'ı
        from PyQt6.QtWidgets import QScrollArea
        flow = _AESRoundFlowWidget(
            rounds_data=self._rounds_data,
            round_keys_hex=self._round_keys_hex,
            initial_state_hex=self._initial_state_hex,
        )
        self._flow_scroll = QScrollArea()
        scroll = self._flow_scroll
        scroll.setWidget(flow)
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        lay.addWidget(scroll, stretch=1)
        return w

    def _switch_to_flow_view(self) -> None:
        """Round detay görünümünden Tüm Roundlar Akışı'na geçer."""
        self._stack.setCurrentWidget(self._flow_page)

    def _back_to_round_view(self) -> None:
        """Akış görünümünden tek-round detayına döner."""
        self._stack.setCurrentWidget(self._round_page)

    def _make_match_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 8, 16, 8)

        self._match_lbl = QLabel()
        self._match_lbl.setFont(QFont("Courier New", 12))
        self._match_lbl.setWordWrap(True)
        self._match_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._match_card = QFrame()
        card = self._match_card
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(self._match_lbl)
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    # Navigasyon yardımcıları
    # ------------------------------------------------------------------

    def _switch_to_plaintext_prep(self) -> None:
        """Intro tamamlanınca plaintext prep sayfasına geçer ve animasyonu başlatır.

        Pencere zaten base sınıftan büyük (ekranın %82'si) açıldığı için burada
        yeniden boyutlandırma YOK; eskiden intro 820×620 küçük açıldığından bu
        metot pencereyi büyütüyordu. SHA introsuyla aynı davranış: boyut sabit
        kalır, yalnızca görünen sayfa değişir.
        """
        self._stack.setCurrentWidget(self._plaintext_page)
        self._plaintext_widget.start()

    def _switch_to_rounds_only(self) -> None:
        """Plaintext prep tamamlanınca: rounds sayfasına geç (pencere büyütme YOK, zaten büyük)."""
        self._stack.setCurrentWidget(self._round_page)
        self._render_step(0)
        self._progress.setValue(1)

    # Geriye dönük uyumluluk için: eski isim _switch_to_rounds_only çağırır.
    def _switch_to_rounds(self) -> None:
        """Eski isim — _switch_to_rounds_only çağırır."""
        self._switch_to_rounds_only()

    def _jump_to_round(self, r: int) -> None:
        """Round bar'daki butona tıklanınca o round'un ilk adımına atla."""
        if r not in self._round_start:
            return
        self.current_step = self._round_start[r]
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)
        if hasattr(self, "_btn_prev"):
            self._btn_prev.setEnabled(self.current_step > 0)
        if hasattr(self, "_btn_next"):
            self._btn_next.setEnabled(True)
            self._btn_next.setText("İleri  ▶")

    @staticmethod
    def _round_btn_style(active: bool) -> str:
        """Round (R0-R14) seçici buton stili. SHA round bar ile tutarlı:
        aktif/pasif AYNI 2px border kalınlığı (yalnızca renkle ayrılır) →
        aktif round değişince layout kaymaz; padding ile etiket sıkışmaz."""
        if active:
            return (
                f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
                f"color: #FFFFFF; border: 2px solid {ANIM_COLORS['accent_blue']}; "
                f"border-radius: 3px; padding: 2px 4px; font-weight: bold; }}"
            )
        return (
            f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_secondary']}; "
            f"border: 2px solid {ANIM_COLORS['border']}; "
            f"border-radius: 3px; padding: 2px 4px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border-color: {ANIM_COLORS['accent_blue']}; }}"
        )

    @staticmethod
    def _flow_btn_style() -> str:
        return (
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; border-radius: 5px; "
            f"padding: 4px 12px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )

    @staticmethod
    def _flow_back_btn_style() -> str:
        return (
            f"QPushButton {{ background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_secondary']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 5px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; }}"
        )

    def _update_round_bar(self, active: int) -> None:
        self._active_round = active
        for i, btn in enumerate(self._round_btns):
            btn.setStyleSheet(self._round_btn_style(i == active))

    def _restyle_content(self) -> None:
        """Tema değişiminde QLabel/QFrame tabanlı AES içeriğini durum bozmadan
        yeniden boyar. QPainter widget'ları (matrisler, shift/mix/sub/ark/flow)
        refresh_theme'deki update() ile yenilenir."""
        _card = (
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; border-radius: 6px; }}"
        )
        self._rb_frame.setStyleSheet(_card)
        self._flow_btn.setStyleSheet(self._flow_btn_style())
        self._update_round_bar(getattr(self, "_active_round", 0))
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {ANIM_COLORS['accent_blue']}; border-radius: 8px; }}"
        )
        # Akış sayfası
        self._flow_back_btn.setStyleSheet(self._flow_back_btn_style())
        self._flow_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._flow_legend.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._flow_scroll.setStyleSheet(
            f"QScrollArea {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        # Eşleşme kartı
        self._match_card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        # QLabel tabanlı sayfa widget'ları
        for w in (getattr(self, "_intro", None), getattr(self, "_plaintext_widget", None)):
            if w is not None and hasattr(w, "restyle"):
                w.restyle()

    # ------------------------------------------------------------------
    # Adım render
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if self._stack.currentWidget() != self._round_page:
            self._stack.setCurrentWidget(self._round_page)

        step = self._steps_data[step_idx]
        self._update_round_bar(step["round"])
        self._op_title.setText(
            f"Round {step['round']} / 14   —   {step['operation']}"
        )
        self._op_title.setStyleSheet(f"color: {step['color']};")
        self._desc_lbl.setText(step["description"])

        op = step["operation"]

        # Bir önceki adımın matrisi (before state)
        before = (
            self._steps_data[step_idx - 1]["matrix"]
            if step_idx > 0
            else step["matrix"]
        )
        after = step["matrix"]

        # Sağ panel — operasyona göre değişir (eskisi gibi)
        rnd = step["round"]
        rk: list[list[str]] | None = None
        if op == "SubBytes":
            self._side_stack.setCurrentIndex(3)
            self._sub_widget.set_data(before, after)
        elif op == "ShiftRows":
            self._side_stack.setCurrentIndex(1)
            self._shift_widget.set_data(before, after)
        elif op == "MixColumns":
            self._side_stack.setCurrentIndex(2)
            self._mix_widget.set_data(before, after)
        else:  # AddRoundKey
            self._side_stack.setCurrentIndex(4)
            if rnd < len(self._round_keys_hex):
                rk = self._round_keys_hex[rnd]
                self._ark_widget.set_data(before, after, rk, rnd)

        # State matrisi: yan yana iki matris + animasyon (tek satıra indi)
        self._matrix_pair.start_step(
            op, before, after, step["color"], round_key=rk,
        )

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._match_page)
        self._update_round_bar(14)
        last = self._steps_data[-1]
        mat = last["matrix"]   # 4×4 liste
        self._matrix_pair.show_final(mat)

        # ── Final state matrisi → şifreli metin byte sırası ──
        # AES, state matrisini sütun-öncelikli (column-major) okur
        col_bytes: list[list[str]] = [
            [mat[r][c] for r in range(4)] for c in range(4)
        ]
        hex_out = "".join("".join(col) for col in col_bytes)
        assert len(hex_out) == 32, f"Unexpected hex_out length: {len(hex_out)}"

        col_lines = []
        for c in range(4):
            vals = " ".join(col_bytes[c])
            col_lines.append(f"  Sütun {c+1}: [{vals}]")

        lines = [
            "━━  14 ROUND TAMAMLANDI  ━━",
            "",
            "Final State Matrisi (Round 14 çıkışı):",
            "  ┌────────────────────────┐",
        ]
        for r in range(4):
            lines.append(f"  │  {' '.join(mat[r])}  │")
        lines += [
            "  └────────────────────────┘",
            "",
            "━━  MATRİS → ŞİFRELİ ÇIKIŞ  ━━",
            "",
            "AES, matrisi sütun-öncelikli okur (Column-Major):",
            "",
        ]
        lines += col_lines
        lines += [
            "",
            "Birleştirme: Sütun1 ‖ Sütun2 ‖ Sütun3 ‖ Sütun4",
            f"  → {hex_out[:16]}",
            f"     {hex_out[16:32]}",
            "",
            "━━  GCM MODU  ━━",
            "",
            "AES-256-GCM'de bu 16-byte blok doğrudan şifreli metin değil,",
            "CTR sayacının şifrelenmiş halidir (keystream).",
            "",
            "keystream ⊕ plaintext = ciphertext",
            "",
            "GHASH fonksiyonu da ayrıca kimlik doğrulama etiketi üretir.",
            "",
            "AAD (protokol etiketi + gönderen parmak izi + Unix zaman damgası)",
            "tag hesabına dahil edilir; zaman damgası tazelik/replay kontrolüne",
            "(bob_receive katmanı) temel oluşturur.",
            "",
            "─" * 54,
            f"Animasyon çıktısı (AES-ECB blok dönüşümü):  {self._final_block_hex}",
            f"crypto_core AES-GCM çıktısı — ct(‖tag) ilk 32 byte kesiti:  {self._expected_ct_hex}",
            "",
        ]

        # Build HTML for the label so the ⚠ warning line can be colored
        # differently (yellow) from the ✅ success line (green via stylesheet).
        warning_line = (
            f'<span style="color:{ANIM_COLORS["accent_yellow"]}; font-weight:bold;">'
            "⚠  Bu iki değer farklıdır — bu beklenen bir durumdur:"
            "</span>"
        )
        plain_lines = [
            "",
            "  Animasyon: plaintext'in 14 round AES-ECB çıktısı (tek blok, tag yok)",
            "  GCM modu:  CTR sayacı şifrelenir → plaintext ⊕ keystream → ciphertext",
            "             ardından GHASH ile 16 byte kimlik doğrulama etiketi (tag)",
            "             ciphertext'in sonuna eklenir.",
            "             Aynı anahtar, farklı IV ve counter → farklı çıktı",
            "",
            "  Not: Yukarıdaki \"GCM çıktısı\" tam şifreli metin değil, yalnızca",
            "  ciphertext‖tag değerinin ilk 32 byte'ının hex ÖNİZLEMESİDİR.",
            "  Kısa mesajlarda bu önizleme tag baytlarını da içerir.",
            "",
            "✅  AES-256-GCM Şifreleme Doğru Çalıştı",
        ]
        html_body = "<br>".join(lines) + "<br>" + warning_line + "<br>" + "<br>".join(plain_lines)
        self._match_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._match_lbl.setText(html_body)
        self._match_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")

    # showEvent override — intro başlatılmış, timer başlatma
    def showEvent(self, event) -> None:  # type: ignore[override]
        # Intro QTimer kendi içinde çalışıyor; base class showEvent'i atla
        QWidget.showEvent(self, event)
