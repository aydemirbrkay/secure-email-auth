"""
alice_panel.py – Gönderici (Alice) Panel Widget
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from crypto_core import StepResult
from theme import COLORS, STEP_COLORS_ALICE
from utils import _build_step_content, _make_step_box, _svg_pixmap
from bob_panel import BobDecryptDiagramWidget


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
        self._normal_widgets: list[QWidget] = []  # populated by _init_ui
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._title_widget = QWidget()
        _th = QHBoxLayout(self._title_widget)
        _th.setContentsMargins(0, 0, 0, 0)
        _th.setSpacing(8)
        _th.addStretch()
        _icon_lbl = QLabel()
        _icon_lbl.setPixmap(_svg_pixmap("alice_sender.svg", COLORS["accent_mauve"], 26))
        _th.addWidget(_icon_lbl)
        self._title = QLabel("Gönderici — Alice")
        self._title.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {COLORS['accent_mauve']};")
        _th.addWidget(self._title)
        _th.addStretch()
        layout.addWidget(self._title_widget)

        self._msg_group = QGroupBox("E-posta Mesajı")
        msg_layout = QVBoxLayout(self._msg_group)
        self.msg_input = QTextEdit()
        self.msg_input.setPlaceholderText("Mesajınızı buraya yazın...")
        self.msg_input.setMaximumHeight(100)
        msg_layout.addWidget(self.msg_input)
        layout.addWidget(self._msg_group)

        self._cumulative_area = QWidget()
        self._cumulative_layout = QVBoxLayout(self._cumulative_area)
        self._cumulative_layout.setContentsMargins(0, 0, 0, 0)
        self._cumulative_layout.setSpacing(6)

        self._nested_container = QVBoxLayout()
        self._cumulative_layout.addLayout(self._nested_container)
        self._cumulative_layout.addStretch()

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._cumulative_area)
        self._scroll.setStyleSheet("background-color: transparent;")
        layout.addWidget(self._scroll, stretch=1)

        self.status_label = QLabel("Mesajınızı yazın ve şifreleme sürecini başlatın.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; padding: 4px;"
        )
        layout.addWidget(self.status_label)

        # ── Animasyon container (başta gizli) ─────────────────────────────
        self._anim_container = QWidget()
        anim_layout = QVBoxLayout(self._anim_container)
        anim_layout.setContentsMargins(0, 0, 0, 0)
        self._anim_scroll = QScrollArea()
        self._anim_scroll.setWidgetResizable(True)
        self._anim_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._anim_scroll.setStyleSheet("background: transparent; border: none;")
        anim_layout.addWidget(self._anim_scroll)
        self._anim_container.setVisible(False)
        layout.addWidget(self._anim_container, stretch=1)
        # ─────────────────────────────────────────────────────────────────

        # ── Bob deşifreleme diyagramı container (başta gizli) ─────────────
        self._bob_diag_container = QWidget()
        bob_diag_layout = QVBoxLayout(self._bob_diag_container)
        bob_diag_layout.setContentsMargins(0, 0, 0, 4)
        bob_diag_layout.setSpacing(4)
        self._bob_diag_widget = BobDecryptDiagramWidget()
        bob_diag_layout.addWidget(self._bob_diag_widget)
        self._btn_close_bob_diag = QPushButton("✖  Kapat")
        self._btn_close_bob_diag.setEnabled(False)
        self._btn_close_bob_diag.setFixedHeight(32)
        self._btn_close_bob_diag.setStyleSheet(
            "QPushButton { background: rgba(198,40,40,0.12); border: 2px solid #C62828; "
            "border-radius: 6px; color: #C62828; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background: rgba(198,40,40,0.28); }"
            "QPushButton:disabled { background: #536070; border: 1px solid #5A6272; color: #8896A8; }"
        )
        self._btn_close_bob_diag.clicked.connect(self._on_close_bob_diagram)
        bob_diag_layout.addWidget(self._btn_close_bob_diag)
        self._bob_diag_container.setVisible(False)
        layout.addWidget(self._bob_diag_container, stretch=1)
        # ─────────────────────────────────────────────────────────────────

        self._normal_widgets: list[QWidget] = [
            self._title_widget, self._msg_group, self._scroll, self.status_label
        ]

    def show_animation(self, widget: QWidget) -> None:
        """Normal içeriği gizle, animasyon widget'ını QScrollArea içinde göster."""
        old = self._anim_scroll.takeWidget()
        if old is not None and old is not widget:
            if hasattr(old, "_stop_timers"):
                old._stop_timers()
            old.deleteLater()
        self._anim_scroll.setWidget(widget)
        for w in self._normal_widgets:
            w.setVisible(False)
        self._anim_container.setVisible(True)

    def hide_animation(self) -> None:
        """Animasyonu temizle ve normal içeriği geri getir."""
        old = self._anim_scroll.takeWidget()
        if old is not None:
            if hasattr(old, "_stop_timers"):
                old._stop_timers()
            old.deleteLater()
        self._anim_container.setVisible(False)
        for w in self._normal_widgets:
            w.setVisible(True)

    # ------------------------------------------------------------------
    # Bob Deşifreleme Diyagramı API
    # ------------------------------------------------------------------

    def show_bob_diagram(self) -> None:
        """Bob deşifreleme fazı başladığında diyagramı Alice panelinde göster."""
        old = self._anim_scroll.takeWidget()
        if old is not None:
            if hasattr(old, "_stop_timers"):
                old._stop_timers()
            old.deleteLater()
        self._anim_container.setVisible(False)
        for w in self._normal_widgets:
            w.setVisible(False)
        self._bob_diag_container.setVisible(True)

    def set_bob_diagram_step(self, step_idx: int) -> None:
        """Önceki adımı yeşil yap, step_idx'i kırmızı blink ile vurgula."""
        if step_idx > 0:
            self._bob_diag_widget.mark_step_done(step_idx - 1)
        self._bob_diag_widget.set_active_step(step_idx)

    def enable_bob_close_button(self) -> None:
        """Bob'un son adımı tamamlandıktan sonra Kapat butonunu aktif et."""
        self._btn_close_bob_diag.setEnabled(True)

    def _on_close_bob_diagram(self) -> None:
        """Kapat butonuna basıldığında diyagramı gizle, Alice içeriğini geri getir."""
        self._bob_diag_widget.stop_blink()
        self._bob_diag_container.setVisible(False)
        for w in self._normal_widgets:
            w.setVisible(True)

    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.hide_animation()
        self._bob_diag_widget.reset()
        self._bob_diag_container.setVisible(False)
        self._btn_close_bob_diag.setEnabled(False)
        self._steps = []
        self._current_step = 0
        self._step_widgets.clear()
        self._outermost_box = None
        while self._nested_container.count():
            item = self._nested_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.status_label.setText(
            "Mesajınızı yazın ve şifreleme sürecini başlatın."
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
            # İlk adım: doğrudan container'a ekle
            self._outermost_box = box
            self._nested_container.addWidget(box)
        else:
            # Yeni adım mevcut outermost'u içine alır → yeni outermost olur
            self._nested_container.removeWidget(self._outermost_box)
            box.layout().addWidget(self._outermost_box)
            self._outermost_box = box
            self._nested_container.addWidget(box)

        self._current_step += 1
        self.status_label.setText(
            f"✅ Adım {step.step_number}/{len(self._steps)} tamamlandı: {step.step_name}"
        )
        return self._current_step < len(self._steps)
