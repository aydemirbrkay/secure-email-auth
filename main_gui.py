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

from crypto_core import CryptoCore, EncryptedPacket
from animation_modals import RSAAnimationWindow, SHA256AnimationWindow, AESAnimationWindow
from theme import COLORS, GLOBAL_STYLESHEET
from alice_panel import AlicePanel
from bob_panel import BobPanel
from toast import VerificationToast
from utils import _png_icon_pixmap, _svg_pixmap


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
        self.setMinimumSize(1200, 750)

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

        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(0)
        header_row.addStretch()
        header = QLabel("Secure Email Authentication and Message Integrity")
        header.setFont(QFont("Georgia", 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['accent_blue']}; padding: 8px 0px 8px 8px;")
        header_row.addWidget(header)
        _nr = QLabel()
        _nr.setPixmap(_png_icon_pixmap("secure-email-simge.png", COLORS["text_primary"], 96, thickness=1.25))
        header_row.addWidget(_nr)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        subtitle = QLabel(
            "Gizlilik (Confidentiality)  •  Bütünlük (Integrity)  •  Kimlik Doğrulama (Authentication)"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        main_layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        alice_frame = QFrame()
        alice_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_panel']}; border-radius: 12px; "
            f"border: 2px solid {COLORS['border']}; }}"
        )
        alice_inner = QVBoxLayout(alice_frame)
        alice_inner.setContentsMargins(0, 0, 0, 0)
        self._alice_panel = AlicePanel()
        alice_inner.addWidget(self._alice_panel)
        splitter.addWidget(alice_frame)

        bob_frame = QFrame()
        bob_frame.setStyleSheet(
            f"QFrame {{ background-color: {COLORS['bg_panel']}; border-radius: 12px; "
            f"border: 2px solid {COLORS['border']}; }}"
        )
        bob_inner = QVBoxLayout(bob_frame)
        bob_inner.setContentsMargins(0, 0, 0, 0)
        self._bob_panel = BobPanel()
        bob_inner.addWidget(self._bob_panel)
        splitter.addWidget(bob_frame)

        splitter.setSizes([600, 600])
        main_layout.addWidget(splitter, stretch=1)

        controls = QHBoxLayout()
        controls.setSpacing(12)

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

        self._key_info_group = QGroupBox("RSA-2048 Anahtar Bilgileri  —  Anahtarlar Başarıyla Üretildi")
        self._key_info_group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {COLORS['accent_green']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 4px 8px 4px 8px; }}"
            f"QGroupBox::title {{ color: {COLORS['accent_green']}; "
            f"font-size: 12px; font-weight: bold; subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        self._key_info_group.setVisible(False)
        key_info_layout = QVBoxLayout(self._key_info_group)
        key_info_layout.setSpacing(3)
        key_info_layout.setContentsMargins(6, 8, 6, 4)

        alice_row = QHBoxLayout()
        alice_key_lbl = QLabel("Alice Açık Anahtarı (K⁺_A):")
        alice_key_lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        alice_key_lbl.setStyleSheet(f"color: {COLORS['accent_blue']};")
        alice_key_lbl.setMinimumWidth(190)
        alice_key_lbl.setMaximumWidth(210)
        alice_row.addWidget(alice_key_lbl)
        self._alice_key_value = QLabel("")
        self._alice_key_value.setWordWrap(True)
        self._alice_key_value.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-family: monospace;"
        )
        self._alice_key_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        alice_row.addWidget(self._alice_key_value, stretch=1)
        key_info_layout.addLayout(alice_row)

        bob_row = QHBoxLayout()
        bob_key_lbl = QLabel("Bob Açık Anahtarı (K⁺_B):")
        bob_key_lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        bob_key_lbl.setStyleSheet(f"color: {COLORS['accent_green']};")
        bob_key_lbl.setMinimumWidth(190)
        bob_key_lbl.setMaximumWidth(210)
        bob_row.addWidget(bob_key_lbl)
        self._bob_key_value = QLabel("")
        self._bob_key_value.setWordWrap(True)
        self._bob_key_value.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-family: monospace;"
        )
        self._bob_key_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        bob_row.addWidget(self._bob_key_value, stretch=1)
        key_info_layout.addLayout(bob_row)

        self._comparison_group = QGroupBox(
            "Orijinal Mesaj ↔ Alınan Mesaj Karşılaştırması"
        )
        self._comparison_group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {COLORS['accent_teal']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 4px 8px 4px 8px; }}"
            f"QGroupBox::title {{ color: {COLORS['accent_teal']}; "
            f"font-size: 12px; font-weight: bold; subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        self._comparison_group.setVisible(False)
        cmp_outer = QVBoxLayout(self._comparison_group)
        cmp_outer.setSpacing(4)
        cmp_outer.setContentsMargins(6, 8, 6, 4)

        _card = f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: 8px; }}"

        msg_row = QHBoxLayout()
        msg_row.setSpacing(10)

        alice_msg_f = QFrame(); alice_msg_f.setStyleSheet(_card)
        alice_msg_f.setMinimumHeight(62)
        alice_msg_lay = QVBoxLayout(alice_msg_f)
        alice_msg_lay.setContentsMargins(8, 6, 8, 6)
        alice_msg_lay.setSpacing(2)
        _lbl = QLabel("Alice'in Gönderdiği")
        _lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        _lbl.setStyleSheet(f"color: {COLORS['accent_blue']};")
        alice_msg_lay.addWidget(_lbl)
        self._alice_msg_cmp = QLabel("")
        self._alice_msg_cmp.setWordWrap(True)
        self._alice_msg_cmp.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self._alice_msg_cmp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        alice_msg_lay.addWidget(self._alice_msg_cmp)
        msg_row.addWidget(alice_msg_f, stretch=3)

        msg_mid_f = QFrame(); msg_mid_f.setStyleSheet(_card)
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
        self._cmp_msg_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: bold;")
        msg_mid_lay.addWidget(self._cmp_msg_label)
        msg_row.addWidget(msg_mid_f)

        bob_msg_f = QFrame(); bob_msg_f.setStyleSheet(_card)
        bob_msg_f.setMinimumHeight(62)
        bob_msg_lay = QVBoxLayout(bob_msg_f)
        bob_msg_lay.setContentsMargins(8, 6, 8, 6)
        bob_msg_lay.setSpacing(2)
        _lbl2 = QLabel("Bob'un Aldığı")
        _lbl2.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        _lbl2.setStyleSheet(f"color: {COLORS['accent_green']};")
        bob_msg_lay.addWidget(_lbl2)
        self._bob_msg_cmp = QLabel("")
        self._bob_msg_cmp.setWordWrap(True)
        self._bob_msg_cmp.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self._bob_msg_cmp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bob_msg_lay.addWidget(self._bob_msg_cmp)
        msg_row.addWidget(bob_msg_f, stretch=3)

        cmp_outer.addLayout(msg_row)

        hash_row = QHBoxLayout()
        hash_row.setSpacing(10)

        alice_hash_f = QFrame(); alice_hash_f.setStyleSheet(_card)
        alice_hash_f.setMinimumHeight(48)
        alice_hash_lay = QVBoxLayout(alice_hash_f)
        alice_hash_lay.setContentsMargins(8, 4, 8, 4)
        self._alice_hash_cmp = QLabel("")
        self._alice_hash_cmp.setWordWrap(True)
        self._alice_hash_cmp.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-family: 'Courier New', monospace;"
        )
        self._alice_hash_cmp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        alice_hash_lay.addWidget(self._alice_hash_cmp)
        hash_row.addWidget(alice_hash_f, stretch=3)

        hash_mid_f = QFrame(); hash_mid_f.setStyleSheet(_card)
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
        self._cmp_hash_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: bold;")
        hash_mid_lay.addWidget(self._cmp_hash_label)
        hash_row.addWidget(hash_mid_f)

        bob_hash_f = QFrame(); bob_hash_f.setStyleSheet(_card)
        bob_hash_f.setMinimumHeight(48)
        bob_hash_lay = QVBoxLayout(bob_hash_f)
        bob_hash_lay.setContentsMargins(8, 4, 8, 4)
        self._bob_hash_cmp = QLabel("")
        self._bob_hash_cmp.setWordWrap(True)
        self._bob_hash_cmp.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-family: 'Courier New', monospace;"
        )
        self._bob_hash_cmp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bob_hash_lay.addWidget(self._bob_hash_cmp)
        hash_row.addWidget(bob_hash_f, stretch=3)

        cmp_outer.addLayout(hash_row)

        self._bottom_section = QWidget()
        self._bottom_section.setVisible(False)
        bs_lay = QVBoxLayout(self._bottom_section)
        bs_lay.setContentsMargins(0, 0, 0, 0)
        bs_lay.setSpacing(4)

        self._bottom_toggle_btn = QPushButton()
        self._bottom_toggle_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['bg_card']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; "
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"font-weight: bold; padding: 8px 16px; text-align: left; }}"
            f"QPushButton:hover {{ background: {COLORS['bg_input']}; "
            f"border-color: {COLORS['accent_blue']}; }}"
        )
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
    # Algoritma Paneli
    # ------------------------------------------------------------------

    def _make_algo_panel(self) -> QGroupBox:
        """Algoritmaları tekrar izleme paneli (sağ alt)."""
        box = QGroupBox("Algoritmaları İzle")
        box.setStyleSheet(
            f"QGroupBox {{ border: 2px solid {COLORS['accent_blue']}; "
            f"border-radius: 8px; margin-top: 10px; padding: 4px 6px 4px 6px; }}"
            f"QGroupBox::title {{ color: {COLORS['accent_blue']}; "
            f"font-size: 12px; font-weight: bold; "
            f"subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        lay = QVBoxLayout(box)
        lay.setSpacing(5)
        lay.setContentsMargins(6, 8, 6, 6)

        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        info_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _gear = QLabel()
        _gear.setPixmap(_svg_pixmap("gear.svg", COLORS["accent_blue"], 14))
        info_row.addWidget(_gear)
        info_lbl = QLabel("Her algoritmayı adım adım izleyin")
        info_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        info_row.addWidget(info_lbl)
        lay.addLayout(info_row)

        self._btn_anim_rsa = QPushButton("RSA-2048\nAnahtar Şifreleme")
        self._btn_anim_rsa.setStyleSheet(self._algo_btn_style(COLORS["accent_mauve"]))
        self._btn_anim_rsa.setEnabled(False)
        self._btn_anim_rsa.clicked.connect(self._reopen_rsa)
        lay.addWidget(self._btn_anim_rsa)

        self._btn_anim_sha = QPushButton("SHA-256\nHash Hesaplama")
        self._btn_anim_sha.setStyleSheet(self._algo_btn_style(COLORS["accent_blue"]))
        self._btn_anim_sha.setEnabled(False)
        self._btn_anim_sha.clicked.connect(self._reopen_sha)
        lay.addWidget(self._btn_anim_sha)

        self._btn_anim_aes = QPushButton("AES-256-GCM\nSimetrik Şifreleme")
        self._btn_anim_aes.setStyleSheet(self._algo_btn_style(COLORS["accent_yellow"]))
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
            f"QPushButton:disabled {{ background: #536070; border: 1px solid #5A6272; "
            f"color: #8896A8; font-size: 11px; padding: 4px 6px; min-height: 36px; }}"
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

    def _on_keygen(self) -> None:
        alice_keys, bob_keys = self._crypto.setup_keys()

        alice_lines = alice_keys.public_pem().decode().strip().split("\n")
        bob_lines = bob_keys.public_pem().decode().strip().split("\n")
        alice_b64 = "".join(alice_lines[1:-1])[:60] + "…"
        bob_b64 = "".join(bob_lines[1:-1])[:60] + "…"

        self._alice_key_value.setText(alice_b64)
        self._bob_key_value.setText(bob_b64)
        self._key_info_group.setVisible(True)

        self._rsa_data = (alice_b64, bob_b64)
        self._btn_anim_rsa.setEnabled(True)

        self._bottom_section.setVisible(True)
        self._update_toggle_label()

        self._btn_start.setEnabled(True)
        self._btn_keygen.setEnabled(False)
        self._phase = "ready"
        rsa_win = RSAAnimationWindow(
            alice_b64, bob_b64,
            on_close=self._alice_panel.hide_animation,
        )
        self._alice_panel.show_animation(rsa_win)
        self._bob_panel.show_keygen_step()

    def _on_start(self) -> None:
        message = self._alice_panel.msg_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir e-posta mesajı yazın!")
            return

        try:
            self._packet, alice_steps = self._crypto.alice_send(message)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return

        self._original_message = message
        self._alice_panel.set_steps(alice_steps)
        self._phase = "alice"
        self._alice_has_more = True
        self._btn_start.setEnabled(False)
        self._btn_next.setEnabled(True)
        self._alice_panel.msg_input.setReadOnly(True)

    def _on_next_step(self) -> None:
        if self._phase == "alice":
            # Read step index BEFORE show_next_step() changes it
            step_idx = self._alice_panel._current_step  # 0..5

            # On first step, show the diagram on Bob's panel
            if step_idx == 0:
                self._bob_panel.show_diagram()

            if step_idx < len(self._alice_panel._steps):
                next_step = self._alice_panel._steps[step_idx]
                if "SHA" in next_step.step_name:
                    hash_hex = next_step.data.get("hash_hex", "")
                    self._sha_data = (self._original_message, hash_hex)
                    self._btn_anim_sha.setEnabled(True)
                    self._update_toggle_label()
                    sha_win = SHA256AnimationWindow(
                        self._original_message, hash_hex,
                        on_close=self._alice_panel.hide_animation,
                    )
                    self._alice_panel.show_animation(sha_win)
                elif "AES" in next_step.step_name:
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
                self._bob_panel.set_packet_info(self._packet)
                try:
                    message, is_valid, bob_steps = self._crypto.bob_receive(self._packet)
                except Exception as exc:
                    QMessageBox.critical(self, "Deşifreleme Hatası", str(exc))
                    return
                self._decoded_message = message
                self._is_valid = is_valid
                self._bob_panel.set_steps(bob_steps)
                self._bob_has_more = True
                self._phase = "bob"
                self._btn_next.setText("Sonraki Adım")
                self._alice_panel.show_bob_diagram()

        elif self._phase == "bob":
            step_idx = self._bob_panel._current_step
            self._bob_has_more = self._bob_panel.show_next_step()
            self._alice_panel.set_bob_diagram_step(step_idx)
            if not self._bob_has_more:
                self._phase = "done"
                self._btn_next.setEnabled(False)
                self._btn_next.setText("Tamamlandı")
                self._alice_panel.enable_bob_close_button()
                self._show_comparison(self._original_message, self._decoded_message)
                toast = VerificationToast(self._is_valid, parent=self)
                toast.show()

    def _show_comparison(self, orig: str, received: str) -> None:
        orig_hash = hashlib.sha256(orig.encode("utf-8")).hexdigest()
        recv_hash = hashlib.sha256(received.encode("utf-8")).hexdigest()

        messages_match = orig == received
        hashes_match = orig_hash == recv_hash

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
        self._btn_start.setEnabled(False)
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

def main() -> None:
    """Uygulamayı tam ekran olarak başlatır."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor("#3D4451"))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor("#F1F3F7"))
    palette.setColor(QPalette.ColorRole.Base,            QColor("#4D5769"))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#4A5568"))
    palette.setColor(QPalette.ColorRole.Text,            QColor("#F1F3F7"))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button,          QColor("#4A5568"))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#F1F3F7"))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor("#5B8EC2"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#536070"))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor("#F1F3F7"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8896A8"))
    app.setPalette(palette)

    app.setStyleSheet(GLOBAL_STYLESHEET)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
