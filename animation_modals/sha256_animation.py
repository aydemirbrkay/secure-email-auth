# animation_modals/sha256_animation.py
"""
SHA256AnimationWindow — SHA-256 hash sürecini 4 adımda görselleştirir.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)
from .base import CryptoAnimationWindow, ANIM_COLORS
from .sha256_pure import sha256_steps

_STEP_TITLES = [
    "Adım 1 — Binary Dönüşüm ve Padding",
    "Adım 2 — 512-bit Bloklara Bölünme",
    "Adım 3 — Başlangıç Hash Değerleri  H0 – H7",
    "Adım 4 — 64-Round Sıkıştırma ve Final Hash",
]


class SHA256AnimationWindow(CryptoAnimationWindow):
    """
    SHA-256 animasyon penceresi (4 adım).

    Parametreler:
      message      : kullanıcının orijinal mesaj metni
      expected_hash: crypto_core'un ürettiği hex hash (doğrulama için)
    """

    def __init__(
        self,
        message: str,
        expected_hash: str,
        parent: QWidget | None = None,
    ) -> None:
        self._message = message
        self._expected_hash = expected_hash
        self._data = sha256_steps(message.encode("utf-8"))
        super().__init__("🔐 SHA-256 Hash Animasyonu", len(_STEP_TITLES))

    def _init_content(self) -> None:
        self._step_title = QLabel()
        self._step_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._step_title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        self._step_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._step_title)

        self._card = QFrame()
        self._card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(16, 12, 16, 12)
        self._card_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._card)
        scroll.setStyleSheet("background: transparent; border: none;")
        self.content_layout.addWidget(scroll, stretch=1)

        self._content_lbl = QLabel()
        self._content_lbl.setFont(QFont("Courier New", 11))
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._content_lbl.setWordWrap(True)
        self._content_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._card_layout.addWidget(self._content_lbl)

        self._h_grid = QWidget()
        grid = QGridLayout(self._h_grid)
        grid.setSpacing(4)
        self._h_labels: list[QLabel] = []
        for i in range(8):
            lbl = QLabel(f"H{i}")
            lbl.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"background: {ANIM_COLORS['bg_card']}; "
                f"color: {ANIM_COLORS['text_muted']}; "
                "border-radius: 4px; padding: 4px;"
            )
            lbl.setMinimumWidth(90)
            grid.addWidget(lbl, 0, i)
            val = QLabel("--------")
            val.setFont(QFont("Courier New", 10))
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setStyleSheet(
                f"background: {ANIM_COLORS['bg_input']}; "
                f"color: {ANIM_COLORS['accent_yellow']}; "
                "border-radius: 4px; padding: 4px;"
            )
            val.setMinimumWidth(90)
            grid.addWidget(val, 1, i)
            self._h_labels.append(val)
        self._h_grid.setVisible(False)
        self._card_layout.addWidget(self._h_grid)
        self._card_layout.addStretch()

    def _clear_card(self) -> None:
        self._content_lbl.setText("")
        self._h_grid.setVisible(False)

    def _render_step(self, step_idx: int) -> None:
        self._step_title.setText(_STEP_TITLES[step_idx])
        self._clear_card()
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")

        if step_idx == 0:
            preview = self._data["binary_preview"]
            padded_len = self._data["padded_len"]
            self._content_lbl.setText(
                f"Mesaj: \"{self._message[:40]}\"\n\n"
                f"İlk 8 byte binary:\n"
                f"  {preview}\n\n"
                f"Padding uygulandı:\n"
                f"  → '1' biti eklendi\n"
                f"  → '0' bitleri ile 512'nin katına tamamlandı\n"
                f"  → Sonuna 64-bit mesaj uzunluğu eklendi\n\n"
                f"Padding sonrası toplam: {padded_len} byte "
                f"({padded_len * 8} bit)"
            )
        elif step_idx == 1:
            bc = self._data["blocks_count"]
            self._content_lbl.setText(
                f"Padded mesaj 512-bit (64 byte) bloklara bölündü:\n\n"
                f"  Toplam blok sayısı: {bc}\n\n"
                + "\n".join(
                    f"  Blok {i + 1}:  [ byte {i * 64} – {(i + 1) * 64 - 1} ]"
                    for i in range(bc)
                )
                + f"\n\nHer blok bağımsız olarak sıkıştırma fonksiyonundan geçer."
            )
        elif step_idx == 2:
            self._h_grid.setVisible(True)
            init_h = self._data["initial_h"]
            for i, val in enumerate(init_h):
                self._h_labels[i].setText(val)
                self._h_labels[i].setStyleSheet(
                    f"background: {ANIM_COLORS['bg_input']}; "
                    f"color: {ANIM_COLORS['accent_yellow']}; "
                    "border-radius: 4px; padding: 4px;"
                )
            self._content_lbl.setText(
                "SHA-256 başlangıç sabit değerleri (H0-H7):\n"
                "İlk 8 asal sayının (2,3,5,7,11,13,17,19)\n"
                "kareköklerinin kesir kısımları."
            )

    def _show_match_result(self) -> None:
        self._step_title.setText(_STEP_TITLES[3])
        self._clear_card()

        snapshots = self._data["round_snapshots"]
        snap_text = ""
        for s in snapshots:
            snap_text += (
                f"  Round {s['round']:>2}:  "
                f"A={s['a']}  E={s['e']}\n"
            )

        computed = self._data["final_hash"]
        match = computed == self._expected_hash
        match_str = "✅  Eşleşme Başarılı" if match else "❌  Eşleşme Başarısız"
        color = ANIM_COLORS["accent_green"] if match else ANIM_COLORS["accent_peach"]

        self._content_lbl.setText(
            f"64-round sıkıştırma tamamlandı.\n\n"
            f"Round anlık görüntüleri (1 / 32 / 64):\n"
            f"{snap_text}\n"
            f"{'─' * 52}\n\n"
            f"Animasyonun hesapladığı hash:\n"
            f"  {computed}\n\n"
            f"crypto_core çıktısı:\n"
            f"  {self._expected_hash}\n\n"
            f"{match_str}"
        )
        self._content_lbl.setStyleSheet(f"color: {color};")
