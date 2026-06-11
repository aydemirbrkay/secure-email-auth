"""AES-256-GCM keystream üretimi ve kullanımını açıklayan referans diyaloğu."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from ..base import ANIM_COLORS, cached_font, get_animation_tick_ms
from arayuz.theme import MANAGER


class _KeystreamGenerationWidget(QWidget):
    """Gerçek sayaç bloğunun AES-256 round'larından geçip keystream oluşunu canlandırır."""

    _TICK_MS = 60
    _TOTAL_TICKS = 100

    def __init__(self, counter_block: bytes, keystream: bytes, parent=None) -> None:
        super().__init__(parent)
        self.counter_block = counter_block
        self.keystream = keystream
        self._tick = 0
        self._phase = 0
        self.setMinimumHeight(190)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    def start(self) -> None:
        """Gerçek sayaçtan keystream'e üretim animasyonunu baştan başlatır."""
        self._tick = 0
        self._phase = 0
        self._timer.start(get_animation_tick_ms(self._TICK_MS))
        self.update()

    def stop(self) -> None:
        """Üretim animasyonu zamanlayıcısını durdurur."""
        self._timer.stop()

    def _advance(self) -> None:
        """Sayaç, AES round'ları ve keystream fazlarını zaman çizelgesinde ilerletir."""
        self._tick += 1
        self._phase = 0 if self._tick < 20 else (1 if self._tick < 82 else 2)
        if self._tick >= self._TOTAL_TICKS:
            self._tick = self._TOTAL_TICKS
            self._phase = 2
            self._timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Gerçek değerli sayaç → AES-256/14 round → keystream akışını çizer."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width()
        box_w = min(250, max(190, (width - 150) // 3))
        gap = 50
        total = box_w * 3 + gap * 2
        x0 = max(8, (width - total) // 2)
        y = 40
        self._draw_box(p, x0, y, box_w, "SAYAÇ BLOĞU",
                       self.counter_block.hex(" "), "accent_peach", self._phase == 0)
        self._draw_arrow(p, x0 + box_w, y, gap, "→")
        round_no = min(14, max(0, (self._tick - 20) * 14 // 62))
        self._draw_box(p, x0 + box_w + gap, y, box_w, "AES-256",
                       f"14 round\nilerleme: {round_no}/14", "accent_blue", self._phase == 1)
        self._draw_arrow(p, x0 + box_w * 2 + gap, y, gap, "→")
        shown = self.keystream.hex(" ") if self._phase == 2 else "henüz üretiliyor..."
        self._draw_box(p, x0 + box_w * 2 + gap * 2, y, box_w, "KEYSTREAM",
                       shown, "accent_green", self._phase == 2)
        p.end()

    @staticmethod
    def _draw_arrow(p: QPainter, x: int, y: int, width: int, text: str) -> None:
        """Üretim aşamaları arasındaki oku çizer."""
        p.setFont(cached_font("Georgia", 20, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(x, y, width, 105), Qt.AlignmentFlag.AlignCenter, text)

    @staticmethod
    def _draw_box(
        p: QPainter, x: int, y: int, width: int, title: str, body: str,
        color_key: str, active: bool,
    ) -> None:
        """Bir keystream üretim aşamasını başlık ve gerçek değerle kart olarak çizer."""
        color = QColor(ANIM_COLORS[color_key])
        bg = QColor(color)
        bg.setAlphaF(0.25 if active else 0.10)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(color, 3 if active else 1))
        p.drawRoundedRect(x, y, width, 105, 8, 8)
        p.setFont(cached_font("Georgia", 10, QFont.Weight.Bold))
        p.setPen(color)
        p.drawText(QRect(x + 8, y + 8, width - 16, 20), Qt.AlignmentFlag.AlignCenter, title)
        p.setFont(cached_font("Courier New", 8))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(x + 10, y + 32, width - 20, 65),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, body)


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
        self.counter_block = nonce + (2).to_bytes(4, "big")
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
        self.generation_widget = _KeystreamGenerationWidget(
            self.counter_block, self.keystream, self
        )
        self.replay_generation_btn = QPushButton("Üretimi yeniden oynat")
        self.replay_generation_btn.clicked.connect(self.generation_widget.start)
        layout.addWidget(self.generation_widget)
        layout.addWidget(self.replay_generation_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.generation_widget.start()
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
        self.replay_generation_btn.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['text_on_accent']}; border: none; "
            "border-radius: 6px; padding: 7px 16px; font-weight: bold; }}"
        )
        self.generation_widget.update()
        self.update()

    def _on_theme_changed(self, _mode: str) -> None:
        """Tema yöneticisinden gelen değişiklikte açık diyaloğu yeniden stillendirir."""
        self.restyle()

    def _disconnect_theme_signal(self, _result: int) -> None:
        """Diyalog kapanınca tema sinyali bağlantısını güvenle çözer."""
        self.generation_widget.stop()
        try:
            MANAGER.themeChanged.disconnect(self._on_theme_changed)
        except TypeError:
            pass
