"""
bob_panel.py – Alıcı (Bob) Panel Widget
"""
from __future__ import annotations

from typing import Optional

import os

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Diyagram Koordinat Haritası (alice and bob.png, 623×283 üzerinde)
# ---------------------------------------------------------------------------

_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alice and bob.png")
_DIAGRAM_W = 623
_DIAGRAM_H = 283
_BLINK_MS = 1000

_STEP_RECTS: list[QRect] = [
    QRect(95, 78, 95, 38),    # 0: SHA-256 — m → H(·)
    QRect(195, 78, 80, 38),   # 1: RSA İmza — K_A^-(·)
    QRect(268, 108, 44, 44),  # 2: Birleştir — (+)
    QRect(330, 90, 85, 38),   # 3: AES — K_S(·)
    QRect(330, 155, 85, 38),  # 4: RSA Anahtar — K_B^+(·)
    QRect(408, 118, 158, 62), # 5: Gönder — (+) + Internet
]

_RED = QColor(229, 57, 53)           # #E53935 kenarlık
_RED_FILL = QColor(229, 57, 53, 64)  # %25 şeffaf kırmızı dolgu
_GREEN_FILL = QColor(76, 175, 80, 51) # %20 şeffaf yeşil dolgu


class DiagramWidget(QWidget):
    """Bob panelini tamamen kaplayan alice and bob.png görseli + adım vurgulama animasyonu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 150)

        self._pixmap = QPixmap()
        if os.path.isfile(_IMAGE_PATH):
            self._pixmap = QPixmap(_IMAGE_PATH)
        else:
            print(f"[DiagramWidget] Uyarı: görsel bulunamadı → {_IMAGE_PATH}")

        self._active_step: int = -1
        self._completed_steps: set[int] = set()
        self._blink_on: bool = False

        self._timer = QTimer(self)
        self._timer.setInterval(_BLINK_MS)
        self._timer.timeout.connect(self._toggle_blink)

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------

    def set_active_step(self, idx: int) -> None:
        """Idx'i aktif (yanıp sönen) adım olarak ayarla ve timer'ı başlat."""
        self._active_step = idx
        self._blink_on = True
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def mark_step_done(self, idx: int) -> None:
        """Idx'i tamamlandı (yeşil) olarak işaretle."""
        self._completed_steps.add(idx)
        self.update()

    def stop_blink(self) -> None:
        """Timer'ı durdur, aktif adımı temizle."""
        self._timer.stop()
        self._active_step = -1
        self._blink_on = False
        self.update()

    def reset(self) -> None:
        """Tüm durumu başa döndür."""
        self._timer.stop()
        self._active_step = -1
        self._completed_steps.clear()
        self._blink_on = False
        self.update()

    # ------------------------------------------------------------------
    # İç Metodlar
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().closeEvent(event)

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.update()

    def _scaled_rect(self, r: QRect) -> QRect:
        """623×283 koordinat uzayındaki rect'i mevcut widget boyutuna ölçekler."""
        sx = self.width() / _DIAGRAM_W
        sy = self.height() / _DIAGRAM_H
        return QRect(round(r.x() * sx), round(r.y() * sy),
                     round(r.width() * sx), round(r.height() * sy))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            if not self._pixmap.isNull():
                painter.drawPixmap(self.rect(), self._pixmap)
            else:
                painter.fillRect(self.rect(), QColor(40, 40, 60))

            painter.setPen(Qt.PenStyle.NoPen)
            for idx in self._completed_steps:
                if 0 <= idx < len(_STEP_RECTS):
                    painter.fillRect(self._scaled_rect(_STEP_RECTS[idx]), _GREEN_FILL)

            if 0 <= self._active_step < len(_STEP_RECTS):
                sr = self._scaled_rect(_STEP_RECTS[self._active_step])
                if self._blink_on:
                    painter.fillRect(sr, _RED_FILL)
                painter.setPen(QPen(_RED, 3))
                painter.drawRect(sr)
        finally:
            painter.end()


from crypto_core import EncryptedPacket, StepResult
from theme import COLORS, STEP_COLORS_BOB
from utils import _build_step_content, _make_step_box


class BobPanel(QWidget):
    """Alıcı (Bob) paneli — sağ taraf.

    Kutucuk mantığı — dıştan içe deşifreleme:
      • Adım 1 (RSA Anahtar Çözme) en dışta — şifreli paket, en karmaşık.
      • Her yeni adım bir öncekinin içine eklenir; içe girdikçe sadeleşir.
      • Adım 5 (İmza Doğrulama) en içte — doğrulanmış orijinal mesaj.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._steps: list[StepResult] = []
        self._current_step: int = 0
        self._step_widgets: list[QGroupBox] = []
        self._diagram_widget: DiagramWidget | None = None
        self._btn_close_diagram: QPushButton | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("👨\u200d💻 Alıcı — Bob")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_green']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # --- Diyagram Container (Alice fazında görünür) ---
        self._diagram_container = QWidget()
        self._diagram_container.setVisible(False)
        diag_layout = QVBoxLayout(self._diagram_container)
        diag_layout.setContentsMargins(0, 0, 0, 4)
        diag_layout.setSpacing(4)

        self._diagram_widget = DiagramWidget()
        diag_layout.addWidget(self._diagram_widget)

        self._btn_close_diagram = QPushButton("✖  Kapat")
        self._btn_close_diagram.setEnabled(False)
        self._btn_close_diagram.setFixedHeight(32)
        self._btn_close_diagram.setStyleSheet(
            "QPushButton { background: rgba(229,57,53,0.12); border: 2px solid #E53935; "
            "border-radius: 6px; color: #E53935; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background: rgba(229,57,53,0.28); }"
            "QPushButton:disabled { background: #1e1e2e; border: 1px solid #45475a; color: #6c7086; }"
        )
        self._btn_close_diagram.clicked.connect(self._on_close_diagram)
        diag_layout.addWidget(self._btn_close_diagram)

        layout.addWidget(self._diagram_container, stretch=1)
        # --- Diyagram Container sonu ---

        self._received_group = QGroupBox("Alınan Şifreli Paket")
        recv_layout = QVBoxLayout(self._received_group)
        self._received_label = QLabel("⏳ Henüz bir paket alınmadı.")
        self._received_label.setWordWrap(True)
        self._received_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px;"
        )
        recv_layout.addWidget(self._received_label)
        layout.addWidget(self._received_group)

        self._cumulative_area = QWidget()
        self._cumulative_layout = QVBoxLayout(self._cumulative_area)
        self._cumulative_layout.setContentsMargins(0, 0, 0, 0)
        self._cumulative_layout.setSpacing(6)

        self._nested_container = QVBoxLayout()
        self._cumulative_layout.addLayout(self._nested_container)
        self._cumulative_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(self._cumulative_area)
        self._scroll_area.setStyleSheet("background-color: transparent;")
        layout.addWidget(self._scroll_area, stretch=1)

        self._result_group = QGroupBox("Doğrulama Sonucu")
        result_layout = QVBoxLayout(self._result_group)
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        result_layout.addWidget(self._result_label)
        self._result_group.setVisible(False)
        layout.addWidget(self._result_group)

        self.status_label = QLabel("📬 Alice'den paket bekleniyor...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; padding: 4px;"
        )
        layout.addWidget(self.status_label)

    # ------------------------------------------------------------------
    # Diyagram API
    # ------------------------------------------------------------------

    def show_diagram(self) -> None:
        """Alice fazı başladığında diyagramı göster, diğer içerikleri gizle."""
        self._received_group.setVisible(False)
        self._scroll_area.setVisible(False)
        self.status_label.setVisible(False)
        self._diagram_container.setVisible(True)

    def set_diagram_step(self, step_idx: int) -> None:
        """Önceki adımı yeşil yap, step_idx'i kırmızı blink ile vurgula."""
        if step_idx > 0:
            self._diagram_widget.mark_step_done(step_idx - 1)
        self._diagram_widget.set_active_step(step_idx)

    def enable_close_button(self) -> None:
        """Alice'in son adımı tamamlandıktan sonra Kapat butonunu aktif et."""
        self._btn_close_diagram.setEnabled(True)

    def _on_close_diagram(self) -> None:
        """Kapat butonuna basıldığında diyagramı gizle, Bob içeriğini geri getir."""
        self._diagram_widget.stop_blink()
        self._diagram_container.setVisible(False)
        self._received_group.setVisible(True)
        self._scroll_area.setVisible(True)
        self.status_label.setVisible(True)

    def reset(self) -> None:
        self._diagram_widget.reset()
        self._diagram_container.setVisible(False)
        self._btn_close_diagram.setEnabled(False)
        self._received_group.setVisible(True)
        self._scroll_area.setVisible(True)
        self.status_label.setVisible(True)
        self._steps = []
        self._current_step = 0
        self._step_widgets.clear()
        while self._nested_container.count():
            item = self._nested_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._received_label.setText("⏳ Henüz bir paket alınmadı.")
        self._result_label.setText("")
        self._result_group.setVisible(False)
        self.status_label.setText("📬 Alice'den paket bekleniyor...")

    def set_packet_info(self, packet: EncryptedPacket) -> None:
        info = (
            f"📦 Şifreli mesaj boyutu: {len(packet.encrypted_message)} byte\n"
            f"🔑 Şifreli oturum anahtarı: {len(packet.encrypted_session_key)} byte\n"
            f"🎲 Rastgele Sayı (Nonce): {packet.nonce.hex()[:32]}…"
        )
        self._received_label.setText(info)
        self._received_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;"
        )

    def set_steps(self, steps: list[StepResult]) -> None:
        self._steps = steps
        self._current_step = 0
        self._step_widgets.clear()
        while self._nested_container.count():
            item = self._nested_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_next_step(self) -> bool:
        """Sonraki adımı içe-sararak kümülatif gösterir.

        Her yeni adım bir öncekinin içine eklenir (içe-sarma):
        Adım 1 en dışta (en karmaşık) → Adım 5 en içte (doğrulanmış mesaj).
        """
        if self._current_step >= len(self._steps):
            return False

        step = self._steps[self._current_step]
        color = STEP_COLORS_BOB[self._current_step % len(STEP_COLORS_BOB)]
        content = _build_step_content(step)
        box = _make_step_box(
            f"Adım {step.step_number}: {step.step_name}",
            content,
            color,
        )
        self._step_widgets.append(box)

        if self._current_step == 0:
            self._nested_container.addWidget(box)
        else:
            prev_box = self._step_widgets[self._current_step - 1]
            prev_box.layout().addWidget(box)

        self._current_step += 1
        self.status_label.setText(
            f"✅ Adım {step.step_number}/{len(self._steps)} tamamlandı: {step.step_name}"
        )
        return self._current_step < len(self._steps)
