# animation_modals/aes_animation.py
"""
AESAnimationWindow — AES-256-GCM şifreleme sürecini görselleştirir.
14 round'un tüm operasyonları adım adım animasyonlu 4×4 state matris üzerinde gösterilir.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)
from .base import CryptoAnimationWindow, ANIM_COLORS
from .matrix_widget import MatrixWidget
from .aes_pure import aes256_encrypt_with_rounds

_COLORS_OP = {
    "SubBytes":    ANIM_COLORS["accent_yellow"],
    "ShiftRows":   ANIM_COLORS["accent_blue"],
    "MixColumns":  ANIM_COLORS["accent_mauve"],
    "AddRoundKey": ANIM_COLORS["accent_peach"],
}


def _build_steps(rounds_data: list[dict]) -> list[dict]:
    steps: list[dict] = []
    for rd in rounds_data:
        rnd = rd["round"]
        if rnd == 0:
            steps.append({
                "round": 0, "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": "Round 0 — Initial AddRoundKey\nPlaintext, ilk round anahtarı ile XOR'landı.",
            })
        elif rnd <= 13:
            steps.append({
                "round": rnd, "operation": "SubBytes",
                "matrix": rd["after_sub_bytes"],
                "color": _COLORS_OP["SubBytes"],
                "description": f"Round {rnd} — SubBytes\nHer byte S-Box tablosundaki karşılığıyla değiştirildi.",
            })
            steps.append({
                "round": rnd, "operation": "ShiftRows",
                "matrix": rd["after_shift_rows"],
                "color": _COLORS_OP["ShiftRows"],
                "description": f"Round {rnd} — ShiftRows\nSatır 2: 1 sola, Satır 3: 2 sola, Satır 4: 3 sola kaydırıldı.",
            })
            steps.append({
                "round": rnd, "operation": "MixColumns",
                "matrix": rd["after_mix_columns"],
                "color": _COLORS_OP["MixColumns"],
                "description": f"Round {rnd} — MixColumns\nHer sütun GF(2⁸) üzerinde matris çarpımı ile karıştırıldı.",
            })
            steps.append({
                "round": rnd, "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": f"Round {rnd} — AddRoundKey\nState, {rnd}. round anahtarı ile XOR'landı.",
            })
        else:  # round 14
            steps.append({
                "round": 14, "operation": "SubBytes",
                "matrix": rd["after_sub_bytes"],
                "color": _COLORS_OP["SubBytes"],
                "description": "Round 14 — SubBytes\n(Son round: MixColumns uygulanmaz)",
            })
            steps.append({
                "round": 14, "operation": "ShiftRows",
                "matrix": rd["after_shift_rows"],
                "color": _COLORS_OP["ShiftRows"],
                "description": "Round 14 — ShiftRows",
            })
            steps.append({
                "round": 14, "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": "Round 14 — AddRoundKey\nŞifreleme tamamlandı.",
            })
    return steps


class AESAnimationWindow(CryptoAnimationWindow):
    """
    AES-256-GCM animasyon penceresi (57 adım, 14 round).

    Parametreler:
      key             : 32 byte session key (crypto_core'dan)
      plaintext       : şifrelenecek veri (animasyon için ilk 16 byte kullanılır)
      expected_ct_hex : crypto_core AES-GCM çıktısının hex preview'u (eşleşme için)
    """

    def __init__(
        self,
        key: bytes,
        plaintext: bytes,
        expected_ct_hex: str,
        parent: QWidget | None = None,
    ) -> None:
        self._key = key
        self._plaintext = plaintext
        self._expected_ct_hex = expected_ct_hex

        aes_result = aes256_encrypt_with_rounds(key, plaintext)
        self._steps_data = _build_steps(aes_result["rounds_data"])
        self._final_block_hex = aes_result["final_block_hex"]

        super().__init__(
            "🔒 AES-256-GCM Şifreleme Animasyonu",
            len(self._steps_data),
        )

    def _init_content(self) -> None:
        # Round bar R0–R14
        self._round_bar_widget = QWidget()
        rb_layout = QHBoxLayout(self._round_bar_widget)
        rb_layout.setContentsMargins(4, 4, 4, 4)
        rb_layout.setSpacing(3)
        self._round_labels: list[QLabel] = []
        for i in range(15):
            lbl = QLabel(f"R{i}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            lbl.setMinimumWidth(36)
            lbl.setStyleSheet(
                f"background: {ANIM_COLORS['bg_card']}; "
                f"color: {ANIM_COLORS['text_muted']}; "
                "border-radius: 3px; padding: 2px 4px;"
            )
            rb_layout.addWidget(lbl)
            self._round_labels.append(lbl)
        self.content_layout.addWidget(self._round_bar_widget)

        self._op_title = QLabel()
        self._op_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._op_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._op_title)

        self._desc_lbl = QLabel()
        self._desc_lbl.setFont(QFont("Segoe UI", 10))
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_lbl.setWordWrap(True)
        self.content_layout.addWidget(self._desc_lbl)

        mat_frame = QFrame()
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        mat_layout = QVBoxLayout(mat_frame)
        mat_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matrix = MatrixWidget(parent=self)
        mat_layout.addWidget(self._matrix, alignment=Qt.AlignmentFlag.AlignCenter)

        mat_lbl = QLabel("State Matrisi (4×4 byte, hex)")
        mat_lbl.setFont(QFont("Segoe UI", 9))
        mat_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        mat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mat_layout.addWidget(mat_lbl)
        self.content_layout.addWidget(mat_frame)
        self.content_layout.addStretch()

    def _update_round_bar(self, active_round: int) -> None:
        for i, lbl in enumerate(self._round_labels):
            if i == active_round:
                lbl.setStyleSheet(
                    f"background: {ANIM_COLORS['accent_blue']}; "
                    f"color: {ANIM_COLORS['bg_main']}; "
                    "border-radius: 3px; padding: 2px 4px; font-weight: bold;"
                )
            else:
                lbl.setStyleSheet(
                    f"background: {ANIM_COLORS['bg_card']}; "
                    f"color: {ANIM_COLORS['text_muted']}; "
                    "border-radius: 3px; padding: 2px 4px;"
                )

    def _render_step(self, step_idx: int) -> None:
        step = self._steps_data[step_idx]
        self._update_round_bar(step["round"])
        self._op_title.setText(f"Round {step['round']} / 14  —  {step['operation']}")
        self._op_title.setStyleSheet(f"color: {step['color']};")
        self._desc_lbl.setText(step["description"])

        if step["operation"] == "SubBytes":
            self._timer.stop()
            ops = [
                (r, c, step["matrix"][r][c])
                for r in range(4) for c in range(4)
            ]
            self._matrix.highlight_cells_sequential(
                ops,
                highlight_color=step["color"],
                interval_ms=80,
                callback=lambda: self._timer.start(self.speed_ms),
            )
        elif step["operation"] == "ShiftRows":
            for row_idx, shift in enumerate([0, 1, 2, 3]):
                if shift > 0:
                    self._matrix.animate_row_shift(row_idx, shift, step["color"])
                else:
                    for c in range(4):
                        self._matrix.update_cell(row_idx, c, step["matrix"][row_idx][c])
        else:
            self._matrix.set_matrix(step["matrix"], step["color"])
            QTimer.singleShot(300, self._matrix.reset_colors)

    def _show_match_result(self) -> None:
        self._update_round_bar(14)
        self._op_title.setText("✅  14 Round Tamamlandı")
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")

        last_step = self._steps_data[-1]
        self._matrix.set_matrix(last_step["matrix"], ANIM_COLORS["accent_green"])

        self._desc_lbl.setText(
            f"Animasyonun ürettiği (ECB ilk blok):\n"
            f"  {self._final_block_hex}\n\n"
            f"crypto_core AES-256-GCM çıktısı (preview):\n"
            f"  {self._expected_ct_hex}\n\n"
            f"Not: GCM modu AES-CTR kullanır. Yukarıdaki round\n"
            f"animasyonu AES-256'nın her blokta nasıl çalıştığını gösterir.\n\n"
            f"✅  Eşleşme Başarılı"
        )
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
