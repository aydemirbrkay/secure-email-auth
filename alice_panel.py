"""
alice_panel.py – Gönderici (Alice) Panel Widget
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from crypto_core import StepResult
from theme import COLORS, STEP_COLORS_ALICE
from utils import _build_step_content, _make_step_box


class AlicePanel(QWidget):
    """Gönderici (Alice) paneli — sol taraf.

    Kutucuk mantığı — içten dışa şifreleme:
      • Adım 1 (SHA-256) en içte gösterilir — sade, orijinal mesaj + özet.
      • Her yeni adım önceki kutucuğu sarar; dışa çıkıldıkça karmaşıklaşır.
      • Adım 6 (Paket Gönderimi) en dışta — tam şifreli yapı.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._steps: list[StepResult] = []
        self._current_step: int = 0
        self._step_widgets: list[QGroupBox] = []
        self._outermost_box: Optional[QGroupBox] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("👩\u200d💻 Gönderici — Alice")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        msg_group = QGroupBox("E-posta Mesajı")
        msg_layout = QVBoxLayout(msg_group)
        self.msg_input = QTextEdit()
        self.msg_input.setPlaceholderText("Mesajınızı buraya yazın...")
        self.msg_input.setMaximumHeight(100)
        msg_layout.addWidget(self.msg_input)
        layout.addWidget(msg_group)

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

        self.status_label = QLabel("🔐 Mesajınızı yazın ve şifreleme sürecini başlatın.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; padding: 4px;"
        )
        layout.addWidget(self.status_label)

    def reset(self) -> None:
        self._steps = []
        self._current_step = 0
        self._step_widgets.clear()
        self._outermost_box = None
        while self._nested_container.count():
            item = self._nested_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.status_label.setText(
            "🔐 Mesajınızı yazın ve şifreleme sürecini başlatın."
        )

    def set_steps(self, steps: list[StepResult]) -> None:
        self.reset()
        self._steps = steps

    def show_next_step(self) -> bool:
        """Sonraki adımı dışa-sararak kümülatif gösterir.

        Her yeni adım, önceki tüm kutucukları içine alır (wrap-outward):
        Adım 1 en içte (en sade) → Adım 6 en dışta (en karmaşık).
        """
        if self._current_step >= len(self._steps):
            return False

        step = self._steps[self._current_step]
        color = STEP_COLORS_ALICE[self._current_step % len(STEP_COLORS_ALICE)]
        content = _build_step_content(step)
        box = _make_step_box(
            f"Adım {step.step_number}: {step.step_name}",
            content,
            color,
        )
        self._step_widgets.append(box)

        if self._outermost_box is None:
            self._outermost_box = box
            self._nested_container.addWidget(box)
        else:
            self._nested_container.removeWidget(self._outermost_box)
            box.layout().addWidget(self._outermost_box)
            self._outermost_box = box
            self._nested_container.addWidget(box)

        self._current_step += 1
        self.status_label.setText(
            f"✅ Adım {step.step_number}/{len(self._steps)} tamamlandı: {step.step_name}"
        )
        return self._current_step < len(self._steps)
