"""
main_gui.py – Ana Pencere
=========================
Secure Email Authentication and Message Integrity projesi için
PyQt6 tabanlı iki panelli, adım adım kümülatif görselleştirme arayüzü.

Erciyes Üniversitesi – Bilgisayar Mühendisliği Bitirme Projesi
Berkay Aydemir – 1030521387
Danışman: Prof. Dr. Serkan ÖZTÜRK
"""

from __future__ import annotations

import hashlib
import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from kriptografi.crypto_core import CryptoCore, EncryptedPacket, StepType
from kriptografi.crypto_workers import AliceSendWorker, BobReceiveWorker, KeygenWorker
from kriptografi.utils import constant_time_equal
from arayuz.error_dialog import CryptoErrorDialog
from arayuz.accessibility import build_tab_order, set_accessible
from arayuz.widget_utils import png_icon_pixmap, svg_pixmap
from animation_modals import RSAAnimationWindow, SHA256AnimationWindow, AESAnimationWindow
from animation_modals.base import CryptoAnimationWindow
from arayuz import theme
from arayuz.theme import COLORS, MANAGER, card_style, label_title_style
from arayuz.constants import (
    CONTROLS_SPACING,
    MAIN_LAYOUT_MARGIN,
    MAIN_LAYOUT_SPACING,
    MAIN_WINDOW_MIN_HEIGHT,
    MAIN_WINDOW_MIN_WIDTH,
    SPLITTER_HANDLE_WIDTH,
    SPLITTER_INITIAL_PANEL_WIDTH,
)
from arayuz.theme_toggle import ThemeToggle
from arayuz.alice_panel import AlicePanel
from arayuz.bob_panel import BobPanel
from arayuz.toast import VerificationToast


# ---------------------------------------------------------------------------
# Ana Pencere
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Secure Email Authentication — Ana Pencere."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(
            "Secure Email Authentication and Message Integrity"
        )
        self.setMinimumSize(MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT)

        self._crypto = CryptoCore()
        self._packet: Optional[EncryptedPacket] = None
        self._rsa_data: tuple | None = None
        self._sha_data: tuple | None = None
        self._aes_data: tuple | None = None
        self._phase: str = "idle"
        self._alice_has_more: bool = False
        self._bob_has_more: bool = False
        self._original_message: str = ""
        self._decoded_message: str = ""
        self._is_valid: bool = False

        # Kripto worker referansları — garbage collect edilmelerini
        # engellemek için instance üzerinde tutulurlar. İş bitince
        # sinyal handler'larında temizlenirler.
        self._keygen_worker: Optional[KeygenWorker] = None
        self._send_worker: Optional[AliceSendWorker] = None
        self._receive_worker: Optional[BobReceiveWorker] = None

        # İşlem jetonu (operation token / generation id). Her yeni işlem
        # (keygen/send/receive) ve her reset bu sayacı artırır. Worker
        # başlatılırken o anki generation yakalanır; worker bittiğinde
        # gelen sonucun generation'ı güncel değer ile uyuşmuyorsa sonuç
        # bayat (stale) sayılıp yok sayılır. Hızlı reset/yeniden-başlatmada
        # eski worker'ın sonucunun sıfırlanmış UI'ı bozmasını engeller.
        self._op_generation: int = 0

        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(
            MAIN_LAYOUT_MARGIN, MAIN_LAYOUT_MARGIN,
            MAIN_LAYOUT_MARGIN, MAIN_LAYOUT_MARGIN,
        )
        main_layout.setSpacing(MAIN_LAYOUT_SPACING)

        self._build_header(main_layout)
        self._build_participant_panels(main_layout)
        self._build_controls(main_layout)
        self._key_info_group = self._build_key_info_group()

        self._comparison_group = self._build_comparison_group()

        self._build_bottom_section(main_layout)

        # Renkleri tek noktadan uygula (tema değişiminde tekrar çağrılır)
        self._apply_styles()
        self._update_toggle_label()
        MANAGER.themeChanged.connect(self._on_theme_changed)

        # Erişilebilirlik: ekran-okuyucu adları ve Tab gezinme sırası.
        self._apply_accessibility()

    def _build_header(self, main_layout: QVBoxLayout) -> None:
        header_row = QHBoxLayout()
        header_row.setSpacing(0)
        header_row.addStretch()
        self._header = QLabel("Secure Email Authentication and Message Integrity")
        self._header.setFont(QFont("Georgia", 20, QFont.Weight.Bold))
        header_row.addWidget(self._header)
        self._header_icon = QLabel()
        header_row.addWidget(self._header_icon)
        header_row.addStretch()
        self._theme_toggle = ThemeToggle()
        header_row.addWidget(self._theme_toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(header_row)

        self._subtitle = QLabel(
            "Gizlilik (Confidentiality)  •  Bütünlük (Integrity)  •  "
            "Kimlik Doğrulama (Authentication)"
        )
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self._subtitle)

    def _build_participant_panels(self, main_layout: QVBoxLayout) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)

        self._alice_frame = QFrame()
        alice_inner = QVBoxLayout(self._alice_frame)
        alice_inner.setContentsMargins(0, 0, 0, 0)
        self._alice_panel = AlicePanel()
        alice_inner.addWidget(self._alice_panel)
        splitter.addWidget(self._alice_frame)

        self._bob_frame = QFrame()
        bob_inner = QVBoxLayout(self._bob_frame)
        bob_inner.setContentsMargins(0, 0, 0, 0)
        self._bob_panel = BobPanel()
        bob_inner.addWidget(self._bob_panel)
        splitter.addWidget(self._bob_frame)

        splitter.setSizes(
            [SPLITTER_INITIAL_PANEL_WIDTH, SPLITTER_INITIAL_PANEL_WIDTH]
        )
        main_layout.addWidget(splitter, stretch=1)

    def _build_controls(self, main_layout: QVBoxLayout) -> None:
        controls = QHBoxLayout()
        controls.setSpacing(CONTROLS_SPACING)

        self._btn_keygen = QPushButton("Anahtar Üret")
        self._btn_keygen.setToolTip("Alice ve Bob için RSA-2048 anahtar çiftleri üret")
        self._btn_keygen.clicked.connect(self._on_keygen)
        controls.addWidget(self._btn_keygen)

        self._btn_start = QPushButton("Şifreleme Başlat")
        self._btn_start.setToolTip("Alice'in mesajı şifreleme sürecini başlat")
        self._btn_start.setEnabled(False)
        self._btn_start.clicked.connect(self._on_start)
        controls.addWidget(self._btn_start)

        self._btn_next = QPushButton("Sonraki Adım")
        self._btn_next.setToolTip("Bir sonraki kriptografik adımı göster")
        self._btn_next.setEnabled(False)
        self._btn_next.clicked.connect(self._on_next_step)
        controls.addWidget(self._btn_next)

        self._btn_reset = QPushButton("Sıfırla")
        self._btn_reset.setToolTip("Tüm adımları sıfırla ve baştan başla")
        self._btn_reset.clicked.connect(self._on_reset)
        controls.addWidget(self._btn_reset)

        main_layout.addLayout(controls)

    def _build_key_info_group(self) -> QGroupBox:
        group = QGroupBox(
            "RSA-2048 Anahtar Bilgileri  —  Anahtarlar Başarıyla Üretildi"
        )
        group.setVisible(False)
        layout = QVBoxLayout(group)
        layout.setSpacing(3)
        layout.setContentsMargins(6, 8, 6, 4)

        alice_row = QHBoxLayout()
        self._alice_key_lbl = QLabel("Alice Açık Anahtarı (K⁺_A):")
        self._alice_key_lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        self._alice_key_lbl.setMinimumWidth(190)
        self._alice_key_lbl.setMaximumWidth(210)
        alice_row.addWidget(self._alice_key_lbl)
        self._alice_key_value = QLabel("")
        self._alice_key_value.setWordWrap(True)
        self._alice_key_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        alice_row.addWidget(self._alice_key_value, stretch=1)
        layout.addLayout(alice_row)

        bob_row = QHBoxLayout()
        self._bob_key_lbl = QLabel("Bob Açık Anahtarı (K⁺_B):")
        self._bob_key_lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        self._bob_key_lbl.setMinimumWidth(190)
        self._bob_key_lbl.setMaximumWidth(210)
        bob_row.addWidget(self._bob_key_lbl)
        self._bob_key_value = QLabel("")
        self._bob_key_value.setWordWrap(True)
        self._bob_key_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        bob_row.addWidget(self._bob_key_value, stretch=1)
        layout.addLayout(bob_row)
        return group

    def _build_comparison_group(self) -> QGroupBox:
        group = QGroupBox("Orijinal Mesaj ↔ Alınan Mesaj Karşılaştırması")
        group.setVisible(False)
        outer = QVBoxLayout(group)
        outer.setSpacing(4)
        outer.setContentsMargins(6, 8, 6, 4)

        # Kart çerçeveleri tema değişiminde yeniden stillendirilmek üzere toplanır.
        self._card_frames: list[QFrame] = []

        msg_row = QHBoxLayout()
        msg_row.setSpacing(10)

        alice_msg_f = QFrame()
        self._card_frames.append(alice_msg_f)
        alice_msg_f.setMinimumHeight(62)
        alice_msg_lay = QVBoxLayout(alice_msg_f)
        alice_msg_lay.setContentsMargins(8, 6, 8, 6)
        alice_msg_lay.setSpacing(2)
        self._alice_msg_title = QLabel("Alice'in Gönderdiği")
        self._alice_msg_title.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        alice_msg_lay.addWidget(self._alice_msg_title)
        self._alice_msg_cmp = QLabel("")
        self._alice_msg_cmp.setWordWrap(True)
        self._alice_msg_cmp.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        alice_msg_lay.addWidget(self._alice_msg_cmp)
        msg_row.addWidget(alice_msg_f, stretch=3)

        msg_mid_f = QFrame()
        self._card_frames.append(msg_mid_f)
        msg_mid_f.setMinimumHeight(62)
        msg_mid_f.setMaximumWidth(70)
        msg_mid_lay = QVBoxLayout(msg_mid_f)
        msg_mid_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_mid_lay.setContentsMargins(4, 4, 4, 4)
        msg_mid_lay.setSpacing(2)
        self._cmp_msg_icon = QLabel("")
        self._cmp_msg_icon.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self._cmp_msg_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_mid_lay.addWidget(self._cmp_msg_icon)
        self._cmp_msg_label = QLabel("Mesaj")
        self._cmp_msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_mid_lay.addWidget(self._cmp_msg_label)
        msg_row.addWidget(msg_mid_f)

        bob_msg_f = QFrame()
        self._card_frames.append(bob_msg_f)
        bob_msg_f.setMinimumHeight(62)
        bob_msg_lay = QVBoxLayout(bob_msg_f)
        bob_msg_lay.setContentsMargins(8, 6, 8, 6)
        bob_msg_lay.setSpacing(2)
        self._bob_msg_title = QLabel("Bob'un Aldığı")
        self._bob_msg_title.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        bob_msg_lay.addWidget(self._bob_msg_title)
        self._bob_msg_cmp = QLabel("")
        self._bob_msg_cmp.setWordWrap(True)
        self._bob_msg_cmp.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        bob_msg_lay.addWidget(self._bob_msg_cmp)
        msg_row.addWidget(bob_msg_f, stretch=3)
        outer.addLayout(msg_row)

        hash_row = QHBoxLayout()
        hash_row.setSpacing(10)

        alice_hash_f = QFrame()
        self._card_frames.append(alice_hash_f)
        alice_hash_f.setMinimumHeight(48)
        alice_hash_lay = QVBoxLayout(alice_hash_f)
        alice_hash_lay.setContentsMargins(8, 4, 8, 4)
        self._alice_hash_cmp = QLabel("")
        self._alice_hash_cmp.setWordWrap(True)
        self._alice_hash_cmp.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        alice_hash_lay.addWidget(self._alice_hash_cmp)
        hash_row.addWidget(alice_hash_f, stretch=3)

        hash_mid_f = QFrame()
        self._card_frames.append(hash_mid_f)
        hash_mid_f.setMinimumHeight(48)
        hash_mid_f.setMaximumWidth(70)
        hash_mid_lay = QVBoxLayout(hash_mid_f)
        hash_mid_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hash_mid_lay.setContentsMargins(4, 4, 4, 4)
        hash_mid_lay.setSpacing(2)
        self._cmp_hash_icon = QLabel("")
        self._cmp_hash_icon.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self._cmp_hash_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hash_mid_lay.addWidget(self._cmp_hash_icon)
        self._cmp_hash_label = QLabel("Hash")
        self._cmp_hash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hash_mid_lay.addWidget(self._cmp_hash_label)
        hash_row.addWidget(hash_mid_f)

        bob_hash_f = QFrame()
        self._card_frames.append(bob_hash_f)
        bob_hash_f.setMinimumHeight(48)
        bob_hash_lay = QVBoxLayout(bob_hash_f)
        bob_hash_lay.setContentsMargins(8, 4, 8, 4)
        self._bob_hash_cmp = QLabel("")
        self._bob_hash_cmp.setWordWrap(True)
        self._bob_hash_cmp.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        bob_hash_lay.addWidget(self._bob_hash_cmp)
        hash_row.addWidget(bob_hash_f, stretch=3)
        outer.addLayout(hash_row)
        return group

    def _build_bottom_section(self, main_layout: QVBoxLayout) -> None:
        self._bottom_section = QWidget()
        self._bottom_section.setVisible(False)
        bs_lay = QVBoxLayout(self._bottom_section)
        bs_lay.setContentsMargins(0, 0, 0, 0)
        bs_lay.setSpacing(4)

        self._bottom_toggle_btn = QPushButton()
        self._bottom_toggle_btn.clicked.connect(self._toggle_bottom)
        bs_lay.addWidget(self._bottom_toggle_btn)

        self._bottom_body = QWidget()
        body_row = QHBoxLayout(self._bottom_body)
        body_row.setSpacing(10)
        body_row.setContentsMargins(0, 4, 0, 0)

        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.addWidget(self._key_info_group)
        left_col.addWidget(self._comparison_group)
        left_w = QWidget()
        left_w.setLayout(left_col)
        body_row.addWidget(left_w, stretch=3)

        self._algo_panel = self._make_algo_panel()
        body_row.addWidget(self._algo_panel, stretch=1)

        self._bottom_body.setVisible(False)
        bs_lay.addWidget(self._bottom_body)
        main_layout.addWidget(self._bottom_section)

    # ------------------------------------------------------------------
    # Erişilebilirlik (a11y)
    # ------------------------------------------------------------------

    def _apply_accessibility(self) -> None:
        """İnteraktif öğelere Türkçe erişilebilir ad/açıklama + Tab sırası."""
        set_accessible(self._btn_keygen, "Anahtar Üret",
                       "Alice ve Bob için RSA-2048 anahtar çiftleri üretir.")
        set_accessible(self._btn_start, "Şifreleme Başlat",
                       "Alice'in mesajı şifreleme sürecini başlatır.")
        set_accessible(self._btn_next, "Sonraki Adım",
                       "Bir sonraki kriptografik adımı gösterir.")
        set_accessible(self._btn_reset, "Sıfırla",
                       "Tüm adımları sıfırlar ve baştan başlar.")
        msg_input = getattr(self._alice_panel, "msg_input", None)
        if msg_input is not None:
            set_accessible(msg_input, "E-posta Mesajı",
                           "Gönderilecek e-posta metnini buraya yazın.")
        set_accessible(self._alice_panel, "Alice Paneli (Gönderici)")
        set_accessible(self._bob_panel, "Bob Paneli (Alıcı)")

        # Mantıksal Tab sırası: mesaj girişi → eylem butonları.
        tab_chain = [w for w in (msg_input, self._btn_keygen, self._btn_start,
                                 self._btn_next, self._btn_reset) if w is not None]
        build_tab_order(*tab_chain)

    # ------------------------------------------------------------------
    # Tema / Stil
    # ------------------------------------------------------------------

    def _apply_styles(self) -> None:
        """Renk taşıyan tüm widget stillerini aktif palete göre (yeniden) uygular.

        İlk kurulumda bir kez, tema değişiminde tekrar çağrılır. Yalnız renk
        değerlerini günceller; yerleşim/boyut/font değişmez.
        """
        c = COLORS
        # Başlık + alt başlık + ikon
        self._header.setStyleSheet(
            f"color: {c['accent_blue']}; padding: 8px 0px 8px 8px;"
        )
        self._header_icon.setPixmap(
            png_icon_pixmap("secure-email-simge.png", c["text_primary"], 96, thickness=1.25)
        )
        self._subtitle.setStyleSheet(f"color: {c['text_muted']}; font-size: 13px;")

        # Alice / Bob panel çerçeveleri
        _panel_frame = (
            f"QFrame {{ background-color: {c['bg_panel']}; border-radius: 12px; "
            f"border: 2px solid {c['border']}; }}"
        )
        self._alice_frame.setStyleSheet(_panel_frame)
        self._bob_frame.setStyleSheet(_panel_frame)

        # Anahtar bilgi grubu (yeşil)
        self._key_info_group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {c['accent_green']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 4px 8px 4px 8px; }}"
            f"QGroupBox::title {{ color: {c['accent_green']}; "
            f"font-size: 12px; font-weight: bold; subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        # Alice = mor, Bob = yeşil
        self._alice_key_lbl.setStyleSheet(f"color: {c['accent_mauve']};")
        self._bob_key_lbl.setStyleSheet(f"color: {c['accent_green']};")
        _key_val = f"color: {c['text_secondary']}; font-size: 10px; font-family: monospace;"
        self._alice_key_value.setStyleSheet(_key_val)
        self._bob_key_value.setStyleSheet(_key_val)

        # Karşılaştırma grubu (teal) + kart çerçeveleri
        self._comparison_group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {c['accent_teal']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 4px 8px 4px 8px; }}"
            f"QGroupBox::title {{ color: {c['accent_teal']}; "
            f"font-size: 12px; font-weight: bold; subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        _card = card_style()
        for frame in self._card_frames:
            frame.setStyleSheet(_card)
        self._alice_msg_title.setStyleSheet(label_title_style("accent_mauve"))
        self._bob_msg_title.setStyleSheet(label_title_style("accent_green"))
        _cmp_val = f"color: {c['text_secondary']}; font-size: 11px;"
        self._alice_msg_cmp.setStyleSheet(_cmp_val)
        self._bob_msg_cmp.setStyleSheet(_cmp_val)
        _hash_val = (
            f"color: {c['text_secondary']}; font-size: 10px; "
            f"font-family: 'Courier New', monospace;"
        )
        self._alice_hash_cmp.setStyleSheet(_hash_val)
        self._bob_hash_cmp.setStyleSheet(_hash_val)
        _mid_lbl = f"color: {c['text_muted']}; font-size: 10px; font-weight: bold;"
        self._cmp_msg_label.setStyleSheet(_mid_lbl)
        self._cmp_hash_label.setStyleSheet(_mid_lbl)

        # Alt bölüm geçiş butonu
        self._bottom_toggle_btn.setStyleSheet(
            f"QPushButton {{ background: {c['bg_card']}; "
            f"border: 1px solid {c['border']}; border-radius: 8px; "
            f"color: {c['text_secondary']}; font-size: 12px; "
            f"font-weight: bold; padding: 8px 16px; text-align: left; }}"
            f"QPushButton:hover {{ background: {c['bg_input']}; "
            f"border-color: {c['accent_blue']}; }}"
        )

        # Algoritma paneli
        self._algo_box.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {c['accent_blue']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 4px 6px 4px 6px; }}"
            f"QGroupBox::title {{ color: {c['accent_blue']}; "
            f"font-size: 12px; font-weight: bold; "
            f"subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        self._algo_gear.setPixmap(svg_pixmap("gear.svg", c["accent_blue"], 14))
        self._algo_info_lbl.setStyleSheet(f"color: {c['text_muted']}; font-size: 10px;")
        self._btn_anim_rsa.setStyleSheet(self._algo_btn_style(c["accent_mauve"]))
        self._btn_anim_sha.setStyleSheet(self._algo_btn_style(c["accent_blue"]))
        self._btn_anim_aes.setStyleSheet(self._algo_btn_style(c["accent_yellow"]))

    def _on_theme_changed(self, _mode: str) -> None:
        """Tema değişiminde uygulama genelini ve panelleri yeniden stillendirir."""
        app = QApplication.instance()
        if app is not None:
            app.setPalette(_build_app_palette())
            app.setStyleSheet(theme.build_global_stylesheet())
        self._apply_styles()
        for panel_attr in ("_alice_panel", "_bob_panel"):
            panel = getattr(self, panel_attr, None)
            if panel is not None and hasattr(panel, "_apply_styles"):
                panel._apply_styles()
        # Açık (gömülü) animasyon pencerelerini içerikleriyle yeniden temalandır
        for anim in self.findChildren(CryptoAnimationWindow):
            anim.refresh_theme()
        for w in self.findChildren(QWidget):
            w.update()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Kapanışta global tema sinyalinden ayrıl. Aksi halde kapatılmış
        (ama henüz yok edilmemiş) pencere, sonraki tema değişiminde yarı-yıkık
        widget ağacına erişip çökmeye yol açabilir."""
        try:
            MANAGER.themeChanged.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Algoritma Paneli
    # ------------------------------------------------------------------

    def _make_algo_panel(self) -> QGroupBox:
        """Algoritmaları tekrar izleme paneli (sağ alt)."""
        box = QGroupBox("Algoritmaları İzle")
        self._algo_box = box
        lay = QVBoxLayout(box)
        lay.setSpacing(5)
        lay.setContentsMargins(6, 8, 6, 6)

        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        info_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._algo_gear = QLabel()
        info_row.addWidget(self._algo_gear)
        self._algo_info_lbl = QLabel("Her algoritmayı adım adım izleyin")
        info_row.addWidget(self._algo_info_lbl)
        lay.addLayout(info_row)

        self._btn_anim_rsa = QPushButton("RSA-2048\nAnahtar Şifreleme")
        self._btn_anim_rsa.setEnabled(False)
        self._btn_anim_rsa.clicked.connect(self._reopen_rsa)
        lay.addWidget(self._btn_anim_rsa)

        self._btn_anim_sha = QPushButton("SHA-256\nHash Hesaplama")
        self._btn_anim_sha.setEnabled(False)
        self._btn_anim_sha.clicked.connect(self._reopen_sha)
        lay.addWidget(self._btn_anim_sha)

        self._btn_anim_aes = QPushButton("AES-256-GCM\nSimetrik Şifreleme")
        self._btn_anim_aes.setEnabled(False)
        self._btn_anim_aes.clicked.connect(self._reopen_aes)
        lay.addWidget(self._btn_anim_aes)

        lay.addStretch()
        return box

    @staticmethod
    def _algo_btn_style(color: str) -> str:
        h = color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (
            f"QPushButton {{ background: rgba({r},{g},{b},0.12); "
            f"border: 2px solid {color}; border-radius: 8px; color: {color}; "
            f"font-weight: bold; font-size: 11px; padding: 4px 6px; min-height: 36px; }}"
            f"QPushButton:hover {{ background: rgba({r},{g},{b},0.28); }}"
            f"QPushButton:disabled {{ background: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; "
            f"color: {COLORS['text_muted']}; font-size: 11px; padding: 4px 6px; min-height: 36px; }}"
        )

    def _reopen_rsa(self) -> None:
        if self._rsa_data is None:
            return
        alice_b64, bob_b64 = self._rsa_data
        win = RSAAnimationWindow(
            alice_b64, bob_b64,
            on_close=self._alice_panel.hide_animation,
        )
        self._alice_panel.show_animation(win)

    def _reopen_sha(self) -> None:
        if self._sha_data is None:
            return
        message, hash_hex = self._sha_data
        win = SHA256AnimationWindow(
            message, hash_hex,
            on_close=self._alice_panel.hide_animation,
        )
        self._alice_panel.show_animation(win)

    def _reopen_aes(self) -> None:
        if self._aes_data is None:
            return
        key_bytes, plaintext, ct_hex = self._aes_data
        win = AESAnimationWindow(
            key=key_bytes,
            plaintext=plaintext,
            expected_ct_hex=ct_hex,
            on_close=self._alice_panel.hide_animation,
        )
        self._alice_panel.show_animation(win)

    def _toggle_bottom(self) -> None:
        self._bottom_body.setVisible(not self._bottom_body.isVisible())
        self._update_toggle_label()

    def _update_toggle_label(self) -> None:
        rsa = "RSA-2048 ✓" if self._rsa_data else "RSA-2048"
        sha = "SHA-256 ✓" if self._sha_data else "SHA-256"
        aes = "AES-256-GCM ✓" if self._aes_data else "AES-256-GCM"
        arrow = "▲  Kapat" if self._bottom_body.isVisible() else "▼  Genişlet"
        self._bottom_toggle_btn.setText(
            f"  {rsa}   •   {sha}   •   {aes}                    {arrow}"
        )

    # ------------------------------------------------------------------
    # Olay İşleyicileri (Event Handlers)
    # ------------------------------------------------------------------

    def _next_generation(self) -> int:
        """Yeni bir işlem jetonu üretir ve güncel generation'ı döndürür.

        Sayacı artırır; çağıran (worker başlatan slot) dönen değeri yerel
        bir değişkende/closure'da yakalayıp worker bittiğinde
        ``_is_current_generation`` ile karşılaştırır.
        """
        self._op_generation += 1
        return self._op_generation

    def _is_current_generation(self, gen: int) -> bool:
        """Verilen generation'ın hâlâ güncel olup olmadığını söyler.

        Worker tamamlandığında çağrılır; ``False`` dönerse sonuç bayattır
        (arada reset veya yeni bir işlem başlamıştır) ve UI'a yansıtılmaz.
        """
        return gen == self._op_generation

    def _finalize_worker(self, attr: str, *, wait: bool) -> None:
        """Bir QThread worker'ını güvenle emekliye ayırır.

        Sinyalleri koparır, ``wait=True`` ise iş parçacığının bitmesini bekler
        (reset sırasında "QThread: Destroyed while thread is still running"
        uyarısını ve paylaşılan ``CryptoCore`` üstündeki yarışı önler), sonra
        ``deleteLater`` ile siler ve referansı temizler. ``deleteLater`` ayrıca
        ``parent=self`` ile biriken worker'ların bellek sızıntısını da kapatır.
        """
        w = getattr(self, attr, None)
        if w is None:
            return
        try:
            w.finished_ok.disconnect()
            w.failed.disconnect()
        except TypeError:
            pass  # zaten bağlı değilse sessiz geç
        if wait and w.isRunning():
            w.quit()        # run() event loop kullanmaz; etkisiz ama zararsız
            w.wait(3000)    # kripto bitene dek bekle (kısa; keygen ~1-2 sn)
        w.deleteLater()
        setattr(self, attr, None)

    def _on_keygen(self) -> None:
        # RSA-2048 anahtar üretimi ~1-2 sn sürebilir; UI donmaması için
        # arka planda bir QThread worker'ı kullanıyoruz.
        # Güvenlik kilidi: önceki worker hâlâ koşuyorsa yeni başlatma
        # (buton zaten devre dışı kalır ama defansif guard paylaşılan
        # CryptoCore üstünde çakışmayı kesin engeller).
        if self._keygen_worker is not None and self._keygen_worker.isRunning():
            return
        self._btn_keygen.setEnabled(False)
        self._btn_keygen.setText("Anahtar Üretiliyor…")
        self._bob_panel.show_keygen_step()

        gen = self._next_generation()
        self._keygen_worker = KeygenWorker(self._crypto, self)
        # Worker'ın o anki generation'ını yakala; sonuç geldiğinde bu
        # değer güncel değilse (reset/yeni işlem araya girdiyse) yok say.
        self._keygen_worker.finished_ok.connect(
            lambda a, b, g=gen: self._on_keygen_done(a, b, g)
        )
        self._keygen_worker.failed.connect(self._on_crypto_error)
        self._keygen_worker.start()

    def _on_keygen_done(self, alice_keys, bob_keys, gen: int = 0) -> None:
        """KeygenWorker.finished_ok sinyaline bağlanan sonuç işleyici.

        Ana thread'de çalışır; UI'ı anahtarlar üretildikten sonraki
        duruma getirir. ``gen`` worker başlatılırken yakalanan işlem
        jetonudur; güncel değilse sonuç bayattır ve yok sayılır.
        """
        if not self._is_current_generation(gen):
            return  # bayat sonuç — araya reset/yeni işlem girdi
        self._btn_keygen.setText("Anahtar Üret")
        self._finalize_worker("_keygen_worker", wait=False)

        alice_lines = alice_keys.public_pem().decode().strip().split("\n")
        bob_lines = bob_keys.public_pem().decode().strip().split("\n")
        alice_body = alice_lines[1:-1] or alice_lines
        bob_body = bob_lines[1:-1] or bob_lines
        alice_b64 = "".join(alice_body)[:60] + "…"
        bob_b64 = "".join(bob_body)[:60] + "…"

        self._alice_key_value.setText(alice_b64)
        self._bob_key_value.setText(bob_b64)
        self._key_info_group.setVisible(True)

        self._rsa_data = (alice_b64, bob_b64)
        self._btn_anim_rsa.setEnabled(True)

        self._bottom_section.setVisible(True)
        self._update_toggle_label()

        self._btn_start.setEnabled(True)
        self._phase = "ready"
        rsa_win = RSAAnimationWindow(
            alice_b64, bob_b64,
            on_close=self._alice_panel.hide_animation,
        )
        self._alice_panel.show_animation(rsa_win)

    def _on_receive_done(self, message: str, is_valid: bool, bob_steps: list, gen: int = 0) -> None:
        """BobReceiveWorker tamamlandığında UI'ı bob fazına geçirir.

        ``gen`` worker başlatılırken yakalanan işlem jetonudur; güncel
        değilse sonuç bayattır ve yok sayılır.
        """
        if not self._is_current_generation(gen):
            return  # bayat sonuç — araya reset/yeni işlem girdi
        self._finalize_worker("_receive_worker", wait=False)
        self._decoded_message = message
        self._is_valid = is_valid
        self._bob_panel.set_steps(bob_steps)
        self._bob_has_more = True
        self._phase = "bob"
        self._btn_next.setText("Sonraki Adım")
        self._btn_next.setEnabled(True)
        self._alice_panel.show_bob_diagram()

    def _on_crypto_error(self, exc: Exception) -> None:
        """Herhangi bir kripto worker'ının failed sinyaline ortak işleyici.

        Hatayı kullanıcıya anlaşılır bir mesajla gösterir ve UI'ı
        önceki durumuna döndürür (butonları yeniden etkinleştirir).
        """
        # Öğretici 3 bölümlü hata diyaloğu (özet / "bu ne demek?" / öneri).
        CryptoErrorDialog(exc, self).exec()

        # Worker referansını temizle — hangi worker patladı bilmiyoruz,
        # ama hepsini güvenle emekliye ayırabiliriz (failed sonrası run bitti).
        self._finalize_worker("_keygen_worker", wait=False)
        self._finalize_worker("_send_worker", wait=False)
        self._finalize_worker("_receive_worker", wait=False)

        # Buton durumları: kullanıcı tekrar deneyebilmeli.
        self._btn_keygen.setEnabled(True)
        self._btn_keygen.setText("Anahtar Üret")
        self._btn_next.setEnabled(True)
        self._btn_next.setText("Sonraki Adım")

    def _on_start(self) -> None:
        # Defansif guard: önceki gönderim worker'ı hâlâ koşuyorsa bekle.
        if self._send_worker is not None and self._send_worker.isRunning():
            return
        message = self._alice_panel.msg_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir e-posta mesajı yazın!")
            return

        # Gönderim akışını arka plana al — özellikle büyük mesajlarda
        # SHA-256 + RSA PSS + AES-GCM + RSA-OAEP zinciri UI'ı
        # kilitleyebilir. Süre tipik kısa mesajlarda milisaniyelerdir
        # ancak kullanıcıya "hangi iş yapılıyor" geri bildirimi için
        # asenkron yürütüyoruz.
        self._original_message = message
        self._btn_start.setEnabled(False)
        self._btn_start.setText("Şifreleniyor…")
        self._alice_panel.msg_input.setReadOnly(True)

        gen = self._next_generation()
        self._send_worker = AliceSendWorker(self._crypto, message, self)
        self._send_worker.finished_ok.connect(
            lambda p, s, g=gen: self._on_send_done(p, s, g)
        )
        self._send_worker.failed.connect(self._on_crypto_error)
        self._send_worker.start()

    def _on_send_done(self, packet: EncryptedPacket, alice_steps: list, gen: int = 0) -> None:
        """AliceSendWorker tamamlandığında UI'ı bir sonraki faza hazırlar.

        ``gen`` worker başlatılırken yakalanan işlem jetonudur; güncel
        değilse sonuç bayattır ve yok sayılır.
        """
        if not self._is_current_generation(gen):
            return  # bayat sonuç — araya reset/yeni işlem girdi
        self._packet = packet
        self._finalize_worker("_send_worker", wait=False)
        self._btn_start.setText("Şifreleme Başlat")

        self._alice_panel.set_steps(alice_steps)
        self._phase = "alice"
        self._alice_has_more = True
        self._btn_next.setEnabled(True)

    def _on_next_step(self) -> None:
        if self._phase == "alice":
            # show_next_step() indeksi değiştirmeden ÖNCE oku
            step_idx = self._alice_panel.current_step  # 0..5

            # On first step, show the diagram on Bob's panel
            if step_idx == 0:
                self._bob_panel.show_diagram()

            # Animasyon açma kararı görünen ada (string) değil, makineye
            # okunur step_type'a bakar; adı değişse bile akış bozulmaz.
            next_step = self._alice_panel.peek_next_step()
            if next_step is not None:
                if next_step.step_type == StepType.HASH:
                    hash_hex = next_step.data.get("hash_hex", "")
                    self._sha_data = (self._original_message, hash_hex)
                    self._btn_anim_sha.setEnabled(True)
                    self._update_toggle_label()
                    sha_win = SHA256AnimationWindow(
                        self._original_message, hash_hex,
                        on_close=self._alice_panel.hide_animation,
                    )
                    self._alice_panel.show_animation(sha_win)
                elif next_step.step_type == StepType.AES_ENCRYPT:
                    key_hex = next_step.data.get("session_key_hex", "")
                    ct_preview = next_step.data.get("ciphertext_hex_preview", "")
                    key_bytes = bytes.fromhex(key_hex) if key_hex else b"\x00" * 32
                    plaintext = self._original_message.encode("utf-8")
                    self._aes_data = (key_bytes, plaintext, ct_preview)
                    self._btn_anim_aes.setEnabled(True)
                    self._update_toggle_label()
                    aes_win = AESAnimationWindow(
                        key=key_bytes,
                        plaintext=plaintext,
                        expected_ct_hex=ct_preview,
                        on_close=self._alice_panel.hide_animation,
                    )
                    self._alice_panel.show_animation(aes_win)

            self._alice_has_more = self._alice_panel.show_next_step()

            # Highlight this step in the diagram
            self._bob_panel.set_diagram_step(step_idx)

            if not self._alice_has_more:
                # Last step: enable close button, transition phase
                self._bob_panel.enable_close_button()
                self._phase = "transit"
                self._btn_next.setText("Paketi Bob'a Gönder")

        elif self._phase == "transit":
            if self._packet is not None:
                # Defansif guard: önceki alım worker'ı hâlâ koşuyorsa bekle.
                if (self._receive_worker is not None
                        and self._receive_worker.isRunning()):
                    return
                self._bob_panel.set_packet_info(self._packet)
                # Deşifreleme akışını arka plana al (RSA-OAEP çözme +
                # AES-GCM doğrulamalı deşifre + RSA-PSS imza doğrulama).
                self._btn_next.setEnabled(False)
                self._btn_next.setText("Bob Deşifre Ediyor…")

                gen = self._next_generation()
                self._receive_worker = BobReceiveWorker(
                    self._crypto, self._packet, self
                )
                self._receive_worker.finished_ok.connect(
                    lambda m, v, s, g=gen: self._on_receive_done(m, v, s, g)
                )
                self._receive_worker.failed.connect(self._on_crypto_error)
                self._receive_worker.start()

        elif self._phase == "bob":
            step_idx = self._bob_panel.current_step
            self._bob_has_more = self._bob_panel.show_next_step()
            self._alice_panel.set_bob_diagram_step(step_idx)
            if not self._bob_has_more:
                self._phase = "done"
                self._btn_next.setEnabled(False)
                self._btn_next.setText("Tamamlandı")
                # Karşılaştırma kutusunu (diyagramın son adımı) doğrulama sonucuna göre vurgula
                self._alice_panel.show_bob_verification_result(self._is_valid)
                self._alice_panel.enable_bob_close_button()
                self._show_comparison(self._original_message, self._decoded_message)
                toast = VerificationToast(self._is_valid, parent=self)
                toast.show()

    def _show_comparison(self, orig: str, received: str) -> None:
        orig_hash = hashlib.sha256(orig.encode("utf-8")).hexdigest()
        recv_hash = hashlib.sha256(received.encode("utf-8")).hexdigest()

        # Mesaj ve hash karşılaştırması sabit-zamanlı yapılır; düz '=='
        # içerik uzunluğuna/ortak ön-eke göre zamanlama yan-kanalı sızdırır.
        messages_match = constant_time_equal(orig, received)
        hashes_match = constant_time_equal(orig_hash, recv_hash)

        msg_preview = orig if len(orig) <= 80 else orig[:80] + "…"
        self._alice_msg_cmp.setText(msg_preview)
        self._alice_hash_cmp.setText(orig_hash)

        recv_preview = received if len(received) <= 80 else received[:80] + "…"
        self._bob_msg_cmp.setText(recv_preview)
        self._bob_hash_cmp.setText(recv_hash)

        if messages_match:
            self._cmp_msg_icon.setText("✅")
            self._cmp_msg_icon.setStyleSheet(f"color: {COLORS['accent_green']};")
            self._cmp_msg_label.setText("Mesaj\nEşleşti")
            self._cmp_msg_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 11px; font-weight: bold;"
            )
        else:
            self._cmp_msg_icon.setText("❌")
            self._cmp_msg_icon.setStyleSheet(f"color: {COLORS['accent_red']};")
            self._cmp_msg_label.setText("Mesaj\nEşleşmedi!")
            self._cmp_msg_label.setStyleSheet(
                f"color: {COLORS['accent_red']}; font-size: 11px; font-weight: bold;"
            )

        if hashes_match:
            self._cmp_hash_icon.setText("✅")
            self._cmp_hash_icon.setStyleSheet(f"color: {COLORS['accent_green']};")
            self._cmp_hash_label.setText("Hash\nEşleşti")
            self._cmp_hash_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 11px; font-weight: bold;"
            )
        else:
            self._cmp_hash_icon.setText("❌")
            self._cmp_hash_icon.setStyleSheet(f"color: {COLORS['accent_red']};")
            self._cmp_hash_label.setText("Hash\nEşleşmedi!")
            self._cmp_hash_label.setStyleSheet(
                f"color: {COLORS['accent_red']}; font-size: 11px; font-weight: bold;"
            )

        self._comparison_group.setVisible(True)

    def _on_reset(self) -> None:
        # İşlem jetonunu artır — bu noktadan sonra hâlâ koşan eski
        # worker'ların sonucu bayat sayılır ve _on_*_done slotlarında
        # yok sayılır. Sinyal disconnect'i ek bir güvenlik katmanıdır;
        # generation kontrolü asıl korumadır (disconnect başlatıldıktan
        # hemen sonra emit edilen sinyalin yarış durumunu da kapatır).
        self._next_generation()

        # Koşan bir worker varsa sinyallerini kopar ve bitmesini bekle —
        # geç gelen finished_ok çağrıları sıfırlanmış UI üstüne yazmasın ve
        # Python referansı None'a çekilirken hâlâ koşan QThread "Destroyed
        # while running" uyarısı vermesin. Kripto C seviyesinde interrupt
        # edilemez; bu yüzden quit() etkisizdir ama wait() ile bitişi bekleriz.
        for attr in ("_keygen_worker", "_send_worker", "_receive_worker"):
            self._finalize_worker(attr, wait=True)

        self._alice_panel.reset()
        self._bob_panel.reset()
        self._alice_panel.msg_input.setReadOnly(False)
        self._alice_panel.msg_input.clear()
        self._packet = None
        self._phase = "idle"
        self._alice_has_more = False
        self._bob_has_more = False
        self._original_message = ""
        self._decoded_message = ""
        self._is_valid = False
        self._btn_keygen.setEnabled(True)
        self._btn_keygen.setText("Anahtar Üret")
        self._btn_start.setEnabled(False)
        self._btn_start.setText("Şifreleme Başlat")
        self._btn_next.setEnabled(False)
        self._btn_next.setText("Sonraki Adım")
        self._key_info_group.setVisible(False)
        self._comparison_group.setVisible(False)
        self._rsa_data = None
        self._sha_data = None
        self._aes_data = None
        self._btn_anim_rsa.setEnabled(False)
        self._btn_anim_sha.setEnabled(False)
        self._btn_anim_aes.setEnabled(False)
        self._bottom_body.setVisible(False)
        self._bottom_section.setVisible(False)


# ---------------------------------------------------------------------------
# Uygulama Giriş Noktası
# ---------------------------------------------------------------------------

def _build_app_palette() -> QPalette:
    """Aktif COLORS paletinden uygulama geneli QPalette üretir."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(COLORS["bg_main"]))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(COLORS["bg_input"]))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(COLORS["bg_panel"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button,          QColor(COLORS["bg_panel"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(COLORS["accent_blue"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(COLORS["bg_card"]))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLORS["text_muted"]))
    return palette


def main() -> None:
    """Uygulamayı tam ekran olarak başlatır."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setPalette(_build_app_palette())
    app.setStyleSheet(theme.build_global_stylesheet())
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
