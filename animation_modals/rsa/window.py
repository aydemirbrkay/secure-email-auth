# animation_modals/rsa/window.py
"""RSAAnimationWindow — RSA-2048 anahtar üretimini görsel animasyonla anlatır."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint,
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout,
    QWidget, QGraphicsOpacityEffect, QSizePolicy,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS
from arayuz.accessibility import set_accessible
from . import helpers as H
from .key_builder import _RSAKeyBuilderWidget
from .prime_sieve import _PrimeSieveWidget
from .arithmetic import _MultiplicationWidget, _TotientWidget, _GCDWidget
from .secret_exp import _EEAWidget
from .der_widget import _DERByteFlowWidget
from .key_match import _KeyMatchWidget, _RSAEncryptDecryptWidget


def _compact_secondary_style() -> str:
    """Üst satırdaki "Özelleştir" düğmesi için kompakt ikincil stil.

    Paylaşılan ``button_secondary_style()`` ``min-height: 34px`` ve geniş iç
    boşlukla gelir; düğme ``setMaximumHeight(24)`` ile sınırlandığında metin
    kırpılır (düğmenin tamamı görünmez). Bu stil; küçük font, dar iç boşluk ve
    min-height olmadan tek satıra sığar.
    """
    c = ANIM_COLORS
    return (
        f"QPushButton {{ background: {c['bg_card']}; "
        f"color: {c['text_secondary']}; border: 1px solid {c['border']}; "
        f"border-radius: 5px; padding: 2px 10px; font-size: 11px; }}"
        f"QPushButton:hover {{ background: {c['accent_peach']}; "
        f"color: {c['text_on_accent']}; }}"
    )


class RSAAnimationWindow(CryptoAnimationWindow):
    """
    RSA-2048 anahtar üretimi animasyonu — yeni görsel tasarım.

    Parametreler:
      alice_pub_b64: Alice'in açık anahtar Base64 önizlemesi
      bob_pub_b64  : Bob'un açık anahtar Base64 önizlemesi
    """

    _TITLES = [
        "Adım 1 / 8  p ve q Seçimi",
        "Adım 2 / 8  n = p × q",
        "Adım 3 / 8  ϕ(n) = (p − 1)(q − 1)",
        "Adım 4 / 8  Açık Üs e Seçimi",
        "Adım 5 / 8  Gizli Üs d  (e·d = 1 + k·ϕ)",
        "Adım 6 / 8  DER ve Base64 Kodlaması",
        "Adım 7 / 8  Gerçek Anahtarlarla Eşleşme",
        "Adım 8 / 8  Şifreleme / Deşifreleme Turu",
    ]

    _CAPTIONS = [
        "p ve q rastgele iki büyük asaldır; n ve ϕ(n) hesabının temelini oluştururlar.",
        "n = p × q  →  modülüs; hem açık hem gizli anahtarda yer alır.",
        "ϕ(n) = (p − 1)(q − 1)  →  Euler totient fonksiyonu.",
        "gcd(e, ϕ(n)) = 1  koşulu sağlanmalı; e açık anahtarın üs bileşenidir.",
        "d, e'nin ϕ(n) modülünde tersidir:  e · d ≡ 1  (mod ϕ).",
        "Anahtar dosyada DER yapısında, satır içinde Base64 olarak kodlanır.",
        "Aynı matematik · farklı boyut: demo 12-bit n, gerçek 2048-bit n.",
        "m → c → m'  döngüsü; her iki yön de aynı m değerine ulaşır (Eq:RSAExample).",
    ]

    def __init__(
        self,
        alice_pub_b64: str,
        bob_pub_b64: str,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        # Her açılışta rastgele farklı bir (p, q, e, d) seç — kullanıcı küçük
        # eğitsel sayı adımlarında (asal eleği, aritmetik) her demo'da farklı
        # sayılar görür. Widget'lar __init__ sırasında cari modül sabitlerini
        # okuduğu için bu çağrı SUPER ÇAĞRISINDAN ÖNCE yapılmalıdır
        # (super → _init_content → widget'lar).
        H._reseed_demo()
        # Alice/Bob b64: main_gui'den gelen GERÇEK 2048-bit açık anahtar
        # önizlemeleridir. der_widget "Aşama B" ve key_match bunları "Alice'in
        # gerçek anahtarı" diye sunduğu için DEMO değil GERÇEK değer kullanılır
        # (aksi halde gösterilen değerle etiket çelişirdi). Gerçek anahtar yoksa
        # (standalone/test) demo b64'e düşülür. Küçük sayı demoları yukarıdaki
        # _reseed_demo ile yine her açılışta değişir.
        self._alice_b64 = alice_pub_b64 or H._generate_demo_b64(H._N * 31 + H._E)
        self._bob_b64 = bob_pub_b64
        super().__init__(
            "RSA-2048 Anahtar Üretimi",
            len(self._TITLES) - 1,  # Son adım _show_match_result tarafından işlenir
            manual_mode=True,
            on_close=on_close,
        )

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        # Elle (özelleştirme) seçim modu durumu
        self._custom_mode = False

        # Üst: adım başlığı (ortada) + sağda "Özelleştir" düğmesi
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self._step_lbl = QLabel()
        self._step_lbl.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        self._step_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._step_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_lbl.setMaximumHeight(24)

        self._btn_custom = QPushButton("✎  Özelleştir")
        self._btn_custom.setMaximumHeight(26)
        self._btn_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_custom.setStyleSheet(_compact_secondary_style())
        self._btn_custom.clicked.connect(self._on_custom_clicked)
        set_accessible(
            self._btn_custom, "Asalları özelleştir",
            "p ve q asal sayılarını ızgaradan elle seçmenizi sağlar.",
        )

        # Başlığı görsel ortada tutmak için düğme genişliği kadar sol boşluk.
        # Düğme yalnız Adım 1'de görünür; gizlendiğinde boşluk da gizlenir ki
        # başlık ortada kalsın (bkz. _render_step).
        self._left_spacer = QWidget()
        self._left_spacer.setFixedWidth(self._btn_custom.sizeHint().width())
        top_row.addWidget(self._left_spacer)
        top_row.addWidget(self._step_lbl, stretch=1)
        top_row.addWidget(self._btn_custom)
        self.content_layout.addLayout(top_row)

        # Orta: yatay split — sol KeyBuilder, sağ Stack
        split = QHBoxLayout()
        split.setSpacing(6)
        split.setContentsMargins(0, 0, 0, 0)

        # Sol: KeyBuilder (dar)
        self._kb_frame = QFrame()
        self._kb_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        kb_layout = QVBoxLayout(self._kb_frame)
        kb_layout.setContentsMargins(0, 0, 0, 0)
        self._kb = _RSAKeyBuilderWidget()
        kb_layout.addWidget(self._kb)
        self._kb_frame.setMinimumWidth(155)
        self._kb_frame.setMaximumWidth(210)
        split.addWidget(self._kb_frame, stretch=0)

        # Sağ: 8 sayfalı stack
        # Scroll yalnızca Adım 6 (DER byte flow) için gerekli — uzun içerikli
        # tek sayfa odur. Outer stack scroll TÜM sayfalara scrollbar
        # eklediği için (örn. Adım 2 gibi kompakt sayfalarda da) kaldırıldı;
        # bunun yerine sadece _DERByteFlowWidget kendi QScrollArea'sıyla
        # sarılır → diğer sayfalar (Adım 1-5, 7, 8) scroll'suz görünür.
        from PyQt6.QtWidgets import QScrollArea
        self._stack_frame = QFrame()
        self._stack_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        stack_layout = QVBoxLayout(self._stack_frame)
        stack_layout.setContentsMargins(4, 4, 4, 4)

        # DER widget'ı QScrollArea içine sarılır — uzun içeriği gerekirse kaydırılır.
        # Scrollbar policy sayfa değişiminde dinamik: yalnızca Adım 6 aktifken
        # AsNeeded, aksi halde AlwaysOff (Adım 7/8'e scrollbar bant izi sızmasın).
        der_widget = _DERByteFlowWidget(self._alice_b64)
        self._der_scroll = QScrollArea()
        self._der_scroll.setWidget(der_widget)
        self._der_scroll.setWidgetResizable(True)
        self._der_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Başlangıçta Adım 1 (idx 0) gösterilir → der_scroll'un scrollbar'ı kapalı.
        self._der_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._der_scroll.setStyleSheet("background: transparent; border: none;")

        self._stack = QStackedWidget()
        self._sieve = _PrimeSieveWidget(on_applied=self._on_custom_pq_applied)
        self._page_widgets: list[QWidget] = [
            self._sieve,
            _MultiplicationWidget(),
            _TotientWidget(),
            _GCDWidget(),
            _EEAWidget(),
            self._der_scroll,
            _KeyMatchWidget(self._alice_b64, self._bob_b64),
            _RSAEncryptDecryptWidget(),
        ]
        for w in self._page_widgets:
            self._stack.addWidget(w)
        # Sayfa değiştikçe der_scroll'un dikey scrollbar politikasını ayarla.
        self._stack.currentChanged.connect(self._on_stack_page_changed)
        stack_layout.addWidget(self._stack)
        split.addWidget(self._stack_frame, stretch=1)

        split_holder = QWidget()
        split_holder.setLayout(split)
        self.content_layout.addWidget(split_holder, stretch=1)

        # Alt: kompakt açıklama — font 9pt → 10pt (okunaklığı artırma)
        # Word wrap aktif ve max yükseklik 50'ye çıkarıldı; uzun cümleler
        # iki satıra geçer ama taşmaz.
        self._caption = QLabel()
        self._caption.setFont(QFont("Georgia", 10))
        self._caption.setStyleSheet(
            f"QLabel {{ color: {ANIM_COLORS['text_secondary']}; "
            f"background: {ANIM_COLORS['bg_input']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 5px; padding: 4px 8px; }}"
        )
        self._caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._caption.setWordWrap(True)
        self._caption.setMaximumHeight(50)
        self.content_layout.addWidget(self._caption)

    # ------------------------------------------------------------------
    # Adım render'ı
    # ------------------------------------------------------------------

    def _restyle_content(self) -> None:
        """Tema değişiminde QLabel/QFrame tabanlı içeriği durum bozmadan yeniden
        boyar. QPainter sayfaları (sieve, çarpma, totient, gcd, eea, der, şifr.)
        refresh_theme'deki update() ile yenilenir."""
        self._step_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        if hasattr(self, "_btn_custom"):
            self._btn_custom.setStyleSheet(_compact_secondary_style())
        self._caption.setStyleSheet(
            f"QLabel {{ color: {ANIM_COLORS['text_secondary']}; "
            f"background: {ANIM_COLORS['bg_input']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 5px; padding: 4px 8px; }}"
        )
        _frame_style = (
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        self._kb_frame.setStyleSheet(_frame_style)
        self._stack_frame.setStyleSheet(_frame_style)
        self._kb.restyle()
        # QLabel tabanlı sayfa(lar) — _KeyMatchWidget vb. restyle() destekler
        for page in self._page_widgets:
            if hasattr(page, "restyle"):
                page.restyle()

    def _render_step(self, idx: int) -> None:
        self._step_lbl.setText(self._TITLES[idx])
        self._stack.setCurrentIndex(idx)
        self._kb.set_step(idx)
        self._caption.setText(self._CAPTIONS[idx])
        self._fade_in_current_page()
        # "Özelleştir/Rastgele Ata" yalnız Adım 1'de (p,q seçimi) anlamlıdır;
        # ilerledikten sonra gizlenir ki kullanıcı yanlışlıkla tıklayıp asal
        # seçimini sıfırlamasın. Sol boşluk da onunla birlikte gizlenir.
        self._set_custom_btn_visible(idx == 0)

    # ------------------------------------------------------------------
    # Elle (özelleştirme) asal seçimi
    # ------------------------------------------------------------------

    def _on_custom_clicked(self) -> None:
        """Düğme kendini açıklar: otomatik→elle ("✎ Özelleştir") ya da
        elle→otomatik ("🎲 Rastgele Ata")."""
        if not self._custom_mode:
            # Otomatik → Elle: Adım 1'e dön ve seçim modunu aç.
            if self.current_step != 0:
                self.current_step = 0
                self._render_step(0)
                self._progress.setValue(1)
                if hasattr(self, "_btn_prev"):
                    self._btn_prev.setEnabled(False)
                if hasattr(self, "_btn_next"):
                    self._btn_next.setEnabled(True)
                    self._btn_next.setText("İleri  ▶")
            self._custom_mode = True
            self._sieve.set_custom_mode(True)
            self._btn_custom.setText("🎲  Rastgele Ata")
        else:
            # Elle → Otomatik: yeni rastgele çift ata.
            H._reseed_demo()
            self._custom_mode = False
            self._sieve.set_custom_mode(False)
            self._btn_custom.setText("✎  Özelleştir")
            self._on_custom_pq_applied()

    def _on_custom_pq_applied(self) -> None:
        """p/q değiştiğinde sol paneli ve asal eleğini anında tazeler. Aşağı
        akış sayfaları kendi showEvent'lerinde güncel H değerlerini okur."""
        self._kb.set_step(self.current_step)
        self._sieve.update()

    def _set_custom_btn_visible(self, visible: bool) -> None:
        """Üst satırdaki özelleştirme düğmesini (ve dengeleyen sol boşluğu)
        gösterir/gizler. Yalnız Adım 1'de görünür kalır."""
        if hasattr(self, "_btn_custom"):
            self._btn_custom.setVisible(visible)
        if hasattr(self, "_left_spacer"):
            self._left_spacer.setVisible(visible)

    def _show_match_result(self) -> None:
        # Son adım — index 7 (Şifreleme/Deşifreleme Turu)
        self._step_lbl.setText(self._TITLES[7])
        self._stack.setCurrentIndex(7)
        self._kb.set_step(7)
        self._caption.setText(self._CAPTIONS[7])
        self._fade_in_current_page()
        self._set_custom_btn_visible(False)

    def _fade_in_current_page(self) -> None:
        """Aktif sayfaya 220 ms opacity 0→1 fade-in uygula."""
        page = self._stack.currentWidget()
        if page is None:
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        anim = QPropertyAnimation(effect, b"opacity", page)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_stack_page_changed(self, idx: int) -> None:
        """
        der_scroll'un dikey scrollbar'ını yalnızca Adım 6 (idx=5) aktifken etkin
        tut. Diğer sayfalar (Adım 7/8 dahil) gösterildiğinde AlwaysOff'a alarak
        QStackedWidget'ın scrollbar alan tahsisinden doğan görsel sızıntıyı keser.
        """
        if idx == 5:
            self._der_scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self._der_scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
