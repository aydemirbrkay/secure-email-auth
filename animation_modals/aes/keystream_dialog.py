"""AES-256-GCM keystream üretimi ve kullanımını açıklayan referans diyaloğu."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout, QWidget

from ..base import ANIM_COLORS
from arayuz.theme import MANAGER


class _KeystreamReferenceDialog(QDialog):
    """Gerçek keystream baytlarını ve AES-256-GCM akışındaki rollerini açıklar."""

    def __init__(
        self,
        keystream: bytes,
        nonce: bytes,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.keystream = keystream
        self.nonce = nonce
        self._configure_window()
        self._build_ui()
        self._resize_to_available_screen()
        self.restyle()
        MANAGER.themeChanged.connect(self._on_theme_changed)
        self.finished.connect(self._disconnect_theme_signal)

    def _configure_window(self) -> None:
        """Diyaloğu bağımsız, kapatma düğmeli ve non-modal referans penceresi yapar."""
        self.setWindowTitle("AES-256-GCM Keystream Referansı")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)

    def _build_ui(self) -> None:
        """Keystream üretimi, XOR kullanımı ve GCM güvenlik rolü kartlarını kurar."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Keystream nedir ve GCM neden kullanır?")
        title.setFont(QFont("Georgia", 15, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = title
        layout.addWidget(title)

        self.keystream_hex_label = self._make_label(
            "Animasyondaki 14 round'un gerçek sonucu:\n"
            f"{self.keystream.hex(' ')}",
            monospace=True,
        )
        self.generation_label = self._make_label(
            "Nasıl üretilir?\n"
            f"AES-256, GCM sayaç bloğunu şifreler: nonce ({self.nonce.hex(' ')}) "
            "‖ sayaç (00 00 00 02). Çıkan 16 byte blok keystream'dir."
        )
        self.usage_label = self._make_label(
            "Ne işe yarar?\n"
            "keystream ⊕ mesaj = şifreli metin. Bu XOR gizlilik sağlar. "
            "Aynı keystream tekrar kullanılmamalıdır; bu yüzden her şifrelemede "
            "yeni, rastgele 12 byte nonce üretilir."
        )
        self.gcm_label = self._make_label(
            "GCM nedir ve neden seçildi?\n"
            "GCM bir AEAD kipidir: CTR/keystream ile gizlilik, GHASH ve 16 byte tag "
            "ile bütünlük/doğrulama sağlar. Proje AES-256-GCM kullanır; çıktı "
            "ciphertext ‖ 16 byte tag biçimindedir. AAD, gönderen ve zaman gibi "
            "şifrelenmeyen bilgilerin de bütünlüğünü korur."
        )
        for label in (
            self.keystream_hex_label,
            self.generation_label,
            self.usage_label,
            self.gcm_label,
        ):
            layout.addWidget(label)
        layout.addStretch(1)

    @staticmethod
    def _make_label(text: str, *, monospace: bool = False) -> QLabel:
        """Uzun açıklamalar için word-wrap açık, okunabilir bir bilgi etiketi üretir."""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setFont(QFont("Courier New" if monospace else "IBM Plex Sans", 11))
        label.setMinimumHeight(70)
        return label

    def _resize_to_available_screen(self) -> None:
        """Diyaloğu mevcut ekranı taşırmadan geniş bir referans görünümüne boyutlandırır."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(900, 650)
            return
        available = screen.availableGeometry()
        self.resize(
            min(1100, int(available.width() * 0.88)),
            min(760, int(available.height() * 0.82)),
        )

    def restyle(self) -> None:
        """Açık diyaloğu aktif uygulama temasına geçirir."""
        self.setStyleSheet(
            f"QDialog {{ background: {ANIM_COLORS['bg_panel']}; }}"
            f"QLabel {{ color: {ANIM_COLORS['text_secondary']}; "
            f"background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            "border-radius: 8px; padding: 12px; }}"
        )
        self.title_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_yellow']}; "
            "background: transparent; border: none;"
        )
        self.keystream_hex_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']}; "
            f"background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['accent_green']}; "
            "border-radius: 8px; padding: 12px;"
        )
        self.update()

    def _on_theme_changed(self, _mode: str) -> None:
        """Tema yöneticisinden gelen değişiklikte açık diyaloğu yeniden stillendirir."""
        self.restyle()

    def _disconnect_theme_signal(self, _result: int) -> None:
        """Diyalog kapanınca tema sinyali bağlantısını güvenle çözer."""
        try:
            MANAGER.themeChanged.disconnect(self._on_theme_changed)
        except TypeError:
            pass
