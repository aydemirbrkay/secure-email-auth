# animation_modals/aes/window.py
"""AESAnimationWindow — AES-256-GCM şifreleme sürecini görselleştirir."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS
from ..aes_matrix_view import (
    _AESStateCompareWidget,
    _ColumnMajorLinearizeWidget,
    _GCMRealEncryptWidget,
)
from ..aes_pure import aes256_encrypt_with_rounds
from .constants import _COLORS_OP
from .intro_widget import _AESIntroWidget
from .prep_widget import _AESPlaintextPrepWidget
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
      nonce           : programın gerçek GCM şifrelemesinde kullanılan 12 byte
                        nonce. Verilirse final sayfada "programın gerçek AES'i"
                        köprü aşaması (gerçek keystream) gösterilir; boş ise
                        (eski çağrılar/testler) köprü gizlenir.
    """

    def __init__(
        self,
        key: bytes,
        plaintext: bytes,
        expected_ct_hex: str,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
        nonce: bytes = b"",
    ) -> None:
        self._key = key
        self._plaintext = plaintext
        self._expected_ct_hex = expected_ct_hex
        self._nonce = nonce
        # GCM modu: nonce verildiyse AES round'ları gerçek GCM'in yaptığı gibi
        # SAYAÇ BLOĞUNU (nonce ‖ 0x00000002) şifreler; çıkan son blok keystream'dir.
        # Mesaj AES'ten geçmez, finalde keystream ile XOR'lanır (bkz. match sayfası).
        # ECB modu: nonce yoksa (eski/standalone) eskisi gibi mesaj bloğu şifrelenir.
        self._gcm_mode = len(nonce) == 12
        self._message_bytes = plaintext  # XOR ve mesaj-izi için ayrı tutulur.
        if self._gcm_mode:
            aes_input = nonce + (2).to_bytes(4, "big")  # GCM sayaç bloğu (inc32(J0))
        else:
            aes_input = plaintext

        aes_result = aes256_encrypt_with_rounds(key, aes_input)
        message_prep_result = (
            aes256_encrypt_with_rounds(key, plaintext)
            if self._gcm_mode
            else aes_result
        )
        self._steps_data = _build_steps(aes_result["rounds_data"])
        # GCM modunda final blok = keystream; ECB modunda = şifreli blok.
        self._final_block_hex = aes_result["final_block_hex"]
        # Round flow widget için ek veri (girdi bloğunun round'ları)
        self._rounds_data = aes_result["rounds_data"]
        self._round_keys_hex = aes_result["round_keys_hex"]
        self._initial_state_hex = aes_result["initial_state_hex"]

        # Hazırlık sayfası alanları. GCM modunda state_matrix/first_block SAYAÇ
        # bloğunu temsil eder (AES'in gerçek girdisi); mesaj ayrı gösterilir.
        self._counter_block_data = aes_input if self._gcm_mode else b""
        self._plaintext_text_str = aes_result.get("plaintext_text", "")
        self._plaintext_bytes_data = aes_result.get("plaintext_bytes", b"")
        self._padded_plaintext_data = aes_result.get("padded_plaintext", b"")
        self._first_block_data = aes_result.get("first_block", b"")
        self._blocks_total_data = aes_result.get("blocks_total", 1)
        self._state_matrix_data = aes_result.get(
            "state_matrix", [["--"] * 4 for _ in range(4)]
        )
        self._message_prep_result = message_prep_result

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
        if on_close is not None:
            # Gömülü Alice panelinde dış QScrollArea tüm AES penceresini
            # kaydırmamalı. Viewport yüksekliğini kabul et; taşan round içeriğini
            # sayfa içindeki QScrollArea yönetir, alt navigasyon sabit kalır.
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored
            )

        # Pencere boyutu base sınıftan gelir (standalone modda ekranın %82'si).
        # SHA introsuyla birebir aynı davranış için AES burada KENDİNİ KÜÇÜLTMEZ;
        # eskiden resize(820,620) intro'yu kompakt yapıyordu ama bu, stack'in
        # round/flow sayfa min-genişliklerinin pencereye sığmamasına ve intro
        # ekranında boşluklu yatay scroll'a yol açıyordu. Büyük açılınca intro
        # ekranı doldurur, butonlar sabit kalır, yatay scroll çıkmaz.

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Gömülü modda dış panel yerine iç sayfaların scroll yapmasını sağla."""
        hint = super().sizeHint()
        if self._on_close is not None:
            hint.setHeight(self.minimumSizeHint().height())
        return hint

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        """Gömülü modda dış scroll'un word-wrap yüksekliğini dayatmasını önle."""
        if self._on_close is not None:
            return False
        return super().hasHeightForWidth()

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        if self._on_close is not None:
            return self.minimumSizeHint().height()
        return super().heightForWidth(width)

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
        """ECB için tek, GCM için mesaj ve sayaç rolleri ayrılmış iki hazırlık ekranı kurar."""
        from PyQt6.QtWidgets import QScrollArea
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        self._prep_stack = QStackedWidget()
        lay.addWidget(self._prep_stack)

        first_data = self._message_prep_result
        self._plaintext_widget = _AESPlaintextPrepWidget(
            plaintext_text=first_data.get("plaintext_text", ""),
            plaintext_bytes=first_data.get("plaintext_bytes", b""),
            padded_plaintext=first_data.get("padded_plaintext", b""),
            first_block=first_data.get("first_block", b""),
            blocks_total=first_data.get("blocks_total", 1),
            state_matrix=first_data.get("state_matrix", [["--"] * 4 for _ in range(4)]),
            on_continue=self._switch_to_gcm_prep if self._gcm_mode else self._switch_to_rounds_only,
            mode="ecb",
        )
        if self._gcm_mode:
            self._plaintext_widget._pp_title.setText("AES blok şifreleyici (temel)")
            self._plaintext_widget._txt_lbl.setText(
                "AES bir blok şifreleyicidir: 16 byte blok + 256-bit anahtar → "
                "14 round → 16 byte blok. GİRDİ = mesajınızın ilk bloğu."
            )
            self._plaintext_widget._txt_lbl.setWordWrap(True)
        self._plaintext_prep_scroll = QScrollArea()
        self._plaintext_prep_scroll.setWidget(self._plaintext_widget)
        self._plaintext_prep_scroll.setWidgetResizable(True)
        self._plaintext_prep_scroll.setStyleSheet("background: transparent; border: none;")
        self._prep_stack.addWidget(self._plaintext_prep_scroll)

        if self._gcm_mode:
            self._gcm_prep_widget = _AESPlaintextPrepWidget(
                plaintext_text=self._plaintext_text_str,
                plaintext_bytes=self._plaintext_bytes_data,
                padded_plaintext=self._padded_plaintext_data,
                first_block=self._first_block_data,
                blocks_total=self._blocks_total_data,
                state_matrix=self._state_matrix_data,
                on_continue=self._switch_to_rounds_only,
                mode="gcm",
                message_bytes=self._message_bytes,
            )
            self._gcm_prep_widget._pp_title.setText("Mesajınız GCM kullanıyor")
            self._gcm_prep_scroll = QScrollArea()
            self._gcm_prep_scroll.setWidget(self._gcm_prep_widget)
            self._gcm_prep_scroll.setWidgetResizable(True)
            self._gcm_prep_scroll.setStyleSheet("background: transparent; border: none;")
            self._prep_stack.addWidget(self._gcm_prep_scroll)
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

        # Tek içerik: yan yana iki QPainter matris (ÖNCEKİ / operatör / ŞİMDİKİ).
        # Tekrar eden operasyona-özel yan panel (_side_stack) kaldırıldı; sol
        # matris zaten işlemi gösteriyor, operatör (AddRoundKey'de ⊕/=, diğerlerde
        # "→") akışı anlatıyor. Operasyon adı üstte _op_title'da.
        self._mat_frame = QFrame()
        mat_frame = self._mat_frame
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {ANIM_COLORS['accent_blue']}; border-radius: 8px; }}"
        )
        mat_lay = QVBoxLayout(mat_frame)
        mat_lay.setContentsMargins(8, 6, 8, 6)
        mat_lay.setSpacing(4)
        self._matrix_pair = _AESStateCompareWidget(parent=self)
        mat_lay.addWidget(self._matrix_pair)

        # Matris çifti geniş olabildiğinden (AddRoundKey'de 3 matris yan yana)
        # dar pencerede yatay scroll güvenlik ağı olarak korunur; aksi halde
        # min-width stack üzerinden intro'ya sızabilir.
        from PyQt6.QtWidgets import QScrollArea
        row_scroll = QScrollArea()
        row_scroll.setWidget(mat_frame)
        row_scroll.setWidgetResizable(True)
        row_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        row_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        row_scroll.setStyleSheet("background: transparent; border: none;")
        self._round_scroll = row_scroll
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
        # QStackedWidget tüm sayfaların minimum genişliğini ortak kullanır.
        # Uzun başlık minimumSizeHint'iyle AES penceresini genişletmemeli;
        # dar panelde başlık mevcut alanı kullanır, akış içeriği kendi scroll'unda kalır.
        self._flow_title.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
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
        cl.setSpacing(10)
        # 1) Eğitim: final matris + column-major dizilim animasyonu (ECB blok).
        self._linearize_widget = _ColumnMajorLinearizeWidget(parent=card)
        cl.addWidget(self._linearize_widget)
        # 2) Köprü: programın GERÇEK GCM şifrelemesinin çekirdeği (gerçek K_S+nonce).
        self._gcm_sep = QLabel(
            "──  Peki program gerçekte ne yapıyor?  ──"
        )
        self._gcm_sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gcm_sep.setStyleSheet(
            f"color: {ANIM_COLORS['text_secondary']}; font-weight: bold;"
        )
        cl.addWidget(self._gcm_sep)
        self._gcm_widget = _GCMRealEncryptWidget(parent=card)
        cl.addWidget(self._gcm_widget)
        # 3) Sonra: kısa dürüst sözel özet.
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
        self._prep_stack.setCurrentIndex(0)
        self._plaintext_widget.start()

    def _switch_to_gcm_prep(self) -> None:
        """GCM akışında temel AES mesaj bloğu ekranından sayaç/keystream ekranına geçer."""
        if not self._gcm_mode:
            self._switch_to_rounds_only()
            return
        self._prep_stack.setCurrentWidget(self._gcm_prep_scroll)
        self._gcm_prep_widget.start()

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
                f"color: {ANIM_COLORS['text_on_accent']}; border: 2px solid {ANIM_COLORS['accent_blue']}; "
                f"border-radius: 3px; padding: 2px 4px; font-weight: bold; }}"
            )
        return (
            f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_secondary']}; "
            f"border: 2px solid {ANIM_COLORS['border']}; "
            f"border-radius: 3px; padding: 2px 4px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['text_on_accent']}; border-color: {ANIM_COLORS['accent_blue']}; }}"
        )

    @staticmethod
    def _flow_btn_style() -> str:
        return (
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['text_on_accent']}; border: none; border-radius: 5px; "
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
            f"color: {ANIM_COLORS['text_on_accent']}; }}"
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
        for w in (
            getattr(self, "_intro", None),
            getattr(self, "_plaintext_widget", None),
            getattr(self, "_gcm_prep_widget", None),
        ):
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
            else self._initial_state_hex
        )
        after = step["matrix"]

        # round_key yalnızca AddRoundKey adımında gerekir (matris_pair'de
        # "ÖNCEKİ ⊕ round_key = ŞİMDİKİ" düzeni için). Diğer operasyonlarda
        # (SubBytes/ShiftRows/MixColumns) tekrar eden yan panel kaldırıldı;
        # tek sol matris + aradaki "→" oku işlemi anlatmaya yeter.
        rnd = step["round"]
        rk: list[list[str]] | None = None
        if op == "AddRoundKey" and rnd < len(self._round_keys_hex):
            rk = self._round_keys_hex[rnd]

        # State matrisi: yan yana iki matris + animasyon (tek satıra indi)
        self._matrix_pair.start_step(
            op, before, after, step["color"], round_key=rk,
        )

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._match_page)
        self._update_round_bar(14)
        last = self._steps_data[-1]
        mat = last["matrix"]   # 4×4 liste — GCM'de keystream bloğu, ECB'de şifreli blok.
        self._matrix_pair.show_final(mat)  # round sayfasını günceller (match'te görünmez)

        # Final state'in column-major dizilişi (GCM'de bu keystream'dir).
        self._linearize_widget.set_state(mat)
        self._linearize_widget.start()

        # GCM köprüsü: round'ların ürettiği keystream'i mesajla XOR'la = şifreli metin.
        # Keystream = round animasyonunun son bloğu (_final_block_hex).
        if self._gcm_mode:
            keystream = bytes.fromhex(self._final_block_hex)
            self._gcm_widget.set_inputs(
                keystream, self._message_bytes, self._expected_ct_hex
            )
        else:
            self._gcm_widget.set_inputs(b"", b"", "")
        has_real = self._gcm_widget.has_inputs()
        self._gcm_sep.setVisible(has_real)
        self._gcm_widget.setVisible(has_real)
        if has_real:
            self._gcm_widget.start()

        # Dürüst özet. GCM modunda: round'lar gerçek keystream'i üretti, final XOR
        # gerçek şifreli metni verdi. ECB modunda (nonce yok): eğitim amaçlı blok.
        green = ANIM_COLORS["accent_green"]
        sec = ANIM_COLORS["text_secondary"]
        if self._gcm_mode:
            html_body = (
                f'<div style="color:{green}; font-weight:bold;">'
                "✅ Bu, programın gerçek AES-256-GCM şifrelemesidir."
                "</div>"
                f'<div style="color:{sec};">'
                "Yukarıdaki 14 round, GCM'in sayaç bloğunu gerçek oturum anahtarıyla "
                "(K_S) şifreleyip keystream üretişidir; keystream mesajınızla XOR'lanınca "
                "gönderilen şifreli metin elde edilir. Tam ciphertext'e ayrıca mesaja "
                "eklenen imza ve GCM kimlik doğrulama etiketi (tag) de dahildir."
                "</div>"
            )
        else:
            html_body = (
                f'<div style="color:{green}; font-weight:bold;">'
                "✅ Algoritma gerçektir: bu, FIPS-197 standardına uygun AES-256'nın ta kendisidir."
                "</div>"
                f'<div style="color:{sec};">'
                "Aynı AES · farklı mod: yukarıdaki çıktı tek-blok ECB'dir (eğitim için). "
                "Programın gerçek mesaj şifrelemesi aynı AES-256'yı GCM modunda kullanır."
                "</div>"
            )
        self._match_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._match_lbl.setText(html_body)
        self._match_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_primary']};")

    # showEvent override — intro başlatılmış, timer başlatma
    def showEvent(self, event) -> None:  # type: ignore[override]
        # Intro QTimer kendi içinde çalışıyor; base class showEvent'i atla
        QWidget.showEvent(self, event)
