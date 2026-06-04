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

from kriptografi.crypto_core import StepResult
from kriptografi.utils import _build_step_content, _make_step_box, _style_step_box
from arayuz.theme import COLORS, STEP_COLORS_ALICE
from arayuz.bob_panel import BobDecryptDiagramWidget


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
        _th.setSpacing(0)
        _th.addStretch()
        self._title = QLabel("Gönderici — Alice")
        self._title.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
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
        self._btn_close_bob_diag.clicked.connect(self._on_close_bob_diagram)
        bob_diag_layout.addWidget(self._btn_close_bob_diag)
        self._bob_diag_container.setVisible(False)
        layout.addWidget(self._bob_diag_container, stretch=1)
        # ─────────────────────────────────────────────────────────────────

        self._normal_widgets: list[QWidget] = [
            self._title_widget, self._msg_group, self._scroll, self.status_label
        ]

        self._apply_styles()

    def _apply_styles(self) -> None:
        """Renk taşıyan stilleri aktif palete göre (yeniden) uygular."""
        c = COLORS
        self._title.setStyleSheet(f"color: {c['accent_mauve']};")
        self.status_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: 12px; padding: 4px;"
        )
        self._btn_close_bob_diag.setStyleSheet(
            f"QPushButton {{ background: rgba(217,85,85,0.12); "
            f"border: 2px solid {c['accent_red']}; border-radius: 6px; "
            f"color: {c['accent_red']}; font-weight: bold; font-size: 12px; }}"
            f"QPushButton:hover {{ background: rgba(217,85,85,0.28); }}"
            f"QPushButton:disabled {{ background: {c['bg_card']}; "
            f"border: 1px solid {c['border']}; color: {c['text_muted']}; }}"
        )
        # Mevcut adım kutularını da aktif temaya göre yeniden stillendir
        for i, box in enumerate(self._step_widgets):
            _style_step_box(box, STEP_COLORS_ALICE[i % len(STEP_COLORS_ALICE)])

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

    def show_bob_verification_result(self, is_valid: bool) -> None:
        """Bob'un 5 kripto adımından sonra karşılaştırma kutusunu sonuç rengiyle vurgula."""
        self._bob_diag_widget.show_comparison_result(is_valid)

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
