"""
bob_panel.py – Alıcı (Bob) Panel Widget
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._cumulative_area)
        scroll.setStyleSheet("background-color: transparent;")
        layout.addWidget(scroll, stretch=1)

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

    def reset(self) -> None:
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
