# animation_modals/aes_animation.py
"""
AESAnimationWindow — AES-256-GCM şifreleme sürecini görselleştirir.

Yapı:
  1. Giriş animasyonu: AES-256 round yapısı adım adım belirir (otomatik, QTimer)
  2. Round görünümü: 14 round, tıklanabilir round bar, manuel navigasyon
     - SubBytes: hücre-hücre highlight (MatrixWidget.highlight_cells_sequential)
     - ShiftRows: satır kaydırma okları + animate_row_shift
     - MixColumns: sütun karıştırma görsel açıklaması
     - AddRoundKey: XOR highlight
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
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


# ---------------------------------------------------------------------------
# AES Giriş Animasyonu Widget'ı
# ---------------------------------------------------------------------------

class _AESIntroWidget(QWidget):
    """
    AES-256 round yapısını aşamalı olarak gösteren giriş widget'ı.
    QTimer ile her 600ms'de bir bileşen görünür hale gelir.
    Tüm bileşenler göründükten sonra 'ready' sinyali yerine callback çağrılır.
    """

    def __init__(self, on_complete: "callable", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_complete = on_complete
        self._phase = 0
        self._widgets: list[QWidget] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._show_next_phase)
        self._init_ui()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(40, 20, 40, 20)
        main.setSpacing(0)
        main.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("AES-256  Şifreleme Süreci")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(title)
        main.addSpacing(16)

        # Giriş kutusu
        self._intro_plain = self._make_box(
            "📄  Düz Metin  (Plaintext)", ANIM_COLORS["text_secondary"], width=320
        )
        main.addWidget(self._intro_plain, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._intro_plain.setVisible(False)
        self._widgets.append(self._intro_plain)

        # Ok aşağı
        arr0 = self._make_arrow()
        main.addWidget(arr0, alignment=Qt.AlignmentFlag.AlignHCenter)
        arr0.setVisible(False)
        self._widgets.append(arr0)

        # Initial round
        self._box_r0 = self._make_round_box(
            "🔑  Initial Round  (Round 0)",
            ["AddRoundKey"],
            ANIM_COLORS["accent_peach"],
        )
        main.addWidget(self._box_r0, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_r0.setVisible(False)
        self._widgets.append(self._box_r0)

        # Ok aşağı
        arr1 = self._make_arrow()
        main.addWidget(arr1, alignment=Qt.AlignmentFlag.AlignHCenter)
        arr1.setVisible(False)
        self._widgets.append(arr1)

        # Main rounds
        self._box_main = self._make_round_box(
            "🔄  Ana Roundlar  (R1 – R13)",
            ["1-SubBytes", "2-ShiftRows", "3-MixColumns", "4-AddRoundKey"],
            ANIM_COLORS["accent_blue"],
        )
        main.addWidget(self._box_main, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_main.setVisible(False)
        self._widgets.append(self._box_main)

        # Ok aşağı
        arr2 = self._make_arrow()
        main.addWidget(arr2, alignment=Qt.AlignmentFlag.AlignHCenter)
        arr2.setVisible(False)
        self._widgets.append(arr2)

        # Final round
        self._box_r14 = self._make_round_box(
            "🏁  Son Round  (R14)",
            ["1-SubBytes", "2-ShiftRows", "3-AddRoundKey  (MixColumns yok)"],
            ANIM_COLORS["accent_green"],
        )
        main.addWidget(self._box_r14, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._box_r14.setVisible(False)
        self._widgets.append(self._box_r14)

        # Ok aşağı
        arr3 = self._make_arrow()
        main.addWidget(arr3, alignment=Qt.AlignmentFlag.AlignHCenter)
        arr3.setVisible(False)
        self._widgets.append(arr3)

        # Şifreli metin
        self._intro_cipher = self._make_box(
            "🔒  Şifreli Metin  (Ciphertext)", ANIM_COLORS["accent_green"], width=320
        )
        main.addWidget(self._intro_cipher, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._intro_cipher.setVisible(False)
        self._widgets.append(self._intro_cipher)

        main.addSpacing(20)

        # Başla butonu (başlangıçta gizli)
        self._btn_start = QPushButton("▶  Görselleştirmeyi Başlat")
        self._btn_start.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._btn_start.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: {ANIM_COLORS['bg_main']}; border: none; "
            f"border-radius: 8px; padding: 12px 32px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        self._btn_start.setVisible(False)
        self._btn_start.clicked.connect(self._on_complete)
        main.addWidget(self._btn_start, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._widgets.append(self._btn_start)

    @staticmethod
    def _make_box(text: str, color: str, width: int = 300) -> QFrame:
        f = QFrame()
        f.setFixedWidth(width)
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(12, 10, 12, 10)
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        return f

    @staticmethod
    def _make_round_box(title: str, ops: list[str], color: str) -> QFrame:
        f = QFrame()
        f.setFixedWidth(400)
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {color}; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        for op in ops:
            o = QLabel(f"  →  {op}")
            o.setFont(QFont("Segoe UI", 10))
            o.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']}; border: none;")
            lay.addWidget(o)
        return f

    @staticmethod
    def _make_arrow() -> QLabel:
        lbl = QLabel("⬇")
        lbl.setFont(QFont("Segoe UI", 20))
        lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(28)
        return lbl

    def start(self) -> None:
        self._timer.start(600)

    def _show_next_phase(self) -> None:
        if self._phase >= len(self._widgets):
            self._timer.stop()
            return
        self._widgets[self._phase].setVisible(True)
        self._phase += 1


# ---------------------------------------------------------------------------
# ShiftRows ok göstergesi
# ---------------------------------------------------------------------------

class _ShiftRowsArrowWidget(QWidget):
    """Satırların kaç bayt kaydığını gösteren ok etiketi sütunu."""

    _SHIFTS = [
        ("Satır 1", "kaymaz",    ANIM_COLORS["text_muted"]),
        ("Satır 2", "← 1 bayt", ANIM_COLORS["accent_blue"]),
        ("Satır 3", "← 2 bayt", ANIM_COLORS["accent_mauve"]),
        ("Satır 4", "← 3 bayt", ANIM_COLORS["accent_peach"]),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(12)
        for row_lbl, shift_lbl, color in self._SHIFTS:
            row = QHBoxLayout()
            r = QLabel(row_lbl)
            r.setFont(QFont("Segoe UI", 10))
            r.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
            r.setFixedWidth(50)
            row.addWidget(r)
            s = QLabel(shift_lbl)
            s.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            s.setStyleSheet(f"color: {color};")
            row.addWidget(s)
            lay.addLayout(row)
        self.setFixedWidth(130)


# ---------------------------------------------------------------------------
# MixColumns açıklama widget'ı
# ---------------------------------------------------------------------------

class _MixColumnsWidget(QWidget):
    """Her sütunun 4 byte'ının GF(2^8)'de nasıl karıştığını gösterir."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)

        title = QLabel("Her sütun kendi içinde karışır:")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(title)

        for c in range(4):
            col_lbl = QLabel(
                f"Sütun {c+1}:  [S[0][{c}] ⊕ S[1][{c}] ⊕ S[2][{c}] ⊕ S[3][{c}]]"
            )
            col_lbl.setFont(QFont("Courier New", 9))
            col_lbl.setStyleSheet(
                f"color: {ANIM_COLORS['accent_mauve']};"
                f"background: {ANIM_COLORS['bg_input']};"
                "border-radius: 3px; padding: 2px 4px;"
            )
            lay.addWidget(col_lbl)

        note = QLabel("GF(2⁸) çarpımı — difüzyon sağlar")
        note.setFont(QFont("Segoe UI", 8))
        note.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        lay.addWidget(note)

        self.setFixedWidth(280)


# ---------------------------------------------------------------------------
# Yardımcı: step listesi oluştur
# ---------------------------------------------------------------------------

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
            for op, key, desc in [
                ("SubBytes",   "after_sub_bytes",    f"Round {rnd} — SubBytes\nHer byte S-Box'taki karşılığıyla değiştirildi."),
                ("ShiftRows",  "after_shift_rows",   f"Round {rnd} — ShiftRows\nSatır 1: sabit, 2: 1←, 3: 2←, 4: 3← kaydı."),
                ("MixColumns", "after_mix_columns",  f"Round {rnd} — MixColumns\nHer sütun GF(2⁸) matris çarpımıyla karıştırıldı."),
                ("AddRoundKey","after_add_round_key",f"Round {rnd} — AddRoundKey\nState, {rnd}. round anahtarı ile XOR'landı."),
            ]:
                steps.append({
                    "round": rnd, "operation": op,
                    "matrix": rd[key],
                    "color": _COLORS_OP[op],
                    "description": desc,
                })
        else:
            for op, key, desc in [
                ("SubBytes",   "after_sub_bytes",    "Round 14 — SubBytes  (Son round)"),
                ("ShiftRows",  "after_shift_rows",   "Round 14 — ShiftRows"),
                ("AddRoundKey","after_add_round_key","Round 14 — AddRoundKey  (MixColumns yok)"),
            ]:
                steps.append({
                    "round": rnd, "operation": op,
                    "matrix": rd[key],
                    "color": _COLORS_OP[op],
                    "description": desc,
                })
    return steps


# ---------------------------------------------------------------------------
# AES Animasyon Penceresi
# ---------------------------------------------------------------------------

class AESAnimationWindow(CryptoAnimationWindow):
    """
    AES-256-GCM animasyon penceresi.

    Parametreler:
      key             : 32 byte session key
      plaintext       : şifrelenecek veri (ilk 16 byte kullanılır)
      expected_ct_hex : crypto_core AES-GCM çıktısının hex preview'u
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

        # round → ilk step indeksini hesapla
        self._round_start: dict[int, int] = {}
        for i, s in enumerate(self._steps_data):
            r = s["round"]
            if r not in self._round_start:
                self._round_start[r] = i

        # Başlangıçta intro görünür; manual_mode round görünümü için
        super().__init__(
            "🔒  AES-256-GCM Şifreleme Animasyonu",
            len(self._steps_data),
            manual_mode=True,
        )

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Giriş animasyonu
        self._intro = _AESIntroWidget(on_complete=self._switch_to_rounds)
        self._stack.addWidget(self._intro)

        # Sayfa 1 — Round görünümü
        self._round_page = self._make_round_page()
        self._stack.addWidget(self._round_page)

        # Sayfa 2 — Eşleşme sonucu
        self._match_page = self._make_match_page()
        self._stack.addWidget(self._match_page)

        # Intro başlat (otomatik)
        self._intro.start()

    def _make_round_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        # Tıklanabilir round bar
        rb_frame = QFrame()
        rb_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border-radius: 6px; }}"
        )
        rb_lay = QHBoxLayout(rb_frame)
        rb_lay.setContentsMargins(6, 4, 6, 4)
        rb_lay.setSpacing(3)
        self._round_btns: list[QPushButton] = []
        for i in range(15):
            btn = QPushButton(f"R{i}")
            btn.setFixedWidth(38)
            btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            btn.setStyleSheet(self._round_btn_style(False))
            btn.clicked.connect(lambda checked, r=i: self._jump_to_round(r))
            rb_lay.addWidget(btn)
            self._round_btns.append(btn)
        lay.addWidget(rb_frame)

        # Operasyon başlığı
        self._op_title = QLabel()
        self._op_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._op_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._op_title)

        # Açıklama
        self._desc_lbl = QLabel()
        self._desc_lbl.setFont(QFont("Segoe UI", 10))
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_lbl.setWordWrap(True)
        lay.addWidget(self._desc_lbl)

        # Matris + yardımcı widget
        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        mat_frame = QFrame()
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        mat_lay = QVBoxLayout(mat_frame)
        mat_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matrix = MatrixWidget(parent=self)
        mat_lay.addWidget(self._matrix, alignment=Qt.AlignmentFlag.AlignCenter)
        mat_lbl = QLabel("State Matrisi  (4×4 byte, hex)")
        mat_lbl.setFont(QFont("Segoe UI", 9))
        mat_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        mat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mat_lay.addWidget(mat_lbl)
        content_row.addWidget(mat_frame)

        # Sağ panel — operasyona göre değişir
        self._side_stack = QStackedWidget()
        self._side_stack.setFixedWidth(300)

        empty = QWidget()  # boş panel (AddRoundKey ve SubBytes için)
        self._side_stack.addWidget(empty)             # index 0

        self._shift_widget = _ShiftRowsArrowWidget()  # ShiftRows için
        self._side_stack.addWidget(self._shift_widget)  # index 1

        self._mix_widget = _MixColumnsWidget()         # MixColumns için
        self._side_stack.addWidget(self._mix_widget)    # index 2

        content_row.addWidget(self._side_stack)
        lay.addLayout(content_row)
        lay.addStretch()
        return w

    def _make_match_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 8, 16, 8)

        self._match_lbl = QLabel()
        self._match_lbl.setFont(QFont("Courier New", 12))
        self._match_lbl.setWordWrap(True)
        self._match_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(self._match_lbl)
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    # Navigasyon yardımcıları
    # ------------------------------------------------------------------

    def _switch_to_rounds(self) -> None:
        """Intro'dan round görünümüne geç."""
        self._stack.setCurrentWidget(self._round_page)
        self._render_step(0)
        self._progress.setValue(1)

    def _jump_to_round(self, r: int) -> None:
        """Round bar'daki butona tıklanınca o round'un ilk adımına atla."""
        if r not in self._round_start:
            return
        self.current_step = self._round_start[r]
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)
        if hasattr(self, "_btn_prev"):
            self._btn_prev.setEnabled(self.current_step > 0)
        if hasattr(self, "_btn_next"):
            self._btn_next.setEnabled(True)
            self._btn_next.setText("İleri  ▶")

    @staticmethod
    def _round_btn_style(active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
                f"color: {ANIM_COLORS['bg_main']}; border: none; "
                f"border-radius: 3px; padding: 2px; font-weight: bold; }}"
            )
        return (
            f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_muted']}; border: none; "
            f"border-radius: 3px; padding: 2px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['border']}; "
            f"color: {ANIM_COLORS['text_primary']}; }}"
        )

    def _update_round_bar(self, active: int) -> None:
        for i, btn in enumerate(self._round_btns):
            btn.setStyleSheet(self._round_btn_style(i == active))

    # ------------------------------------------------------------------
    # Adım render
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if self._stack.currentWidget() != self._round_page:
            self._stack.setCurrentWidget(self._round_page)

        step = self._steps_data[step_idx]
        self._update_round_bar(step["round"])
        self._op_title.setText(
            f"Round {step['round']} / 14   —   {step['operation']}"
        )
        self._op_title.setStyleSheet(f"color: {step['color']};")
        self._desc_lbl.setText(step["description"])

        op = step["operation"]

        if op == "SubBytes":
            self._side_stack.setCurrentIndex(0)
            # Hücre-hücre animasyon; ana timer durdurulur, bitince yeniden başlatılır
            # (manual modda timer zaten çalışmıyor; sadece matris güncellenir)
            ops = [(r, c, step["matrix"][r][c]) for r in range(4) for c in range(4)]
            self._matrix.highlight_cells_sequential(
                ops, step["color"], interval_ms=60, callback=None
            )

        elif op == "ShiftRows":
            self._side_stack.setCurrentIndex(1)
            for row_idx, shift in enumerate([0, 1, 2, 3]):
                if shift > 0:
                    self._matrix.animate_row_shift(row_idx, shift, step["color"])
                else:
                    for c in range(4):
                        self._matrix.update_cell(
                            row_idx, c, step["matrix"][row_idx][c]
                        )

        elif op == "MixColumns":
            self._side_stack.setCurrentIndex(2)
            # Her sütunu sırayla highlight et
            for col in range(4):
                col_color = [
                    ANIM_COLORS["accent_blue"],
                    ANIM_COLORS["accent_mauve"],
                    ANIM_COLORS["accent_yellow"],
                    ANIM_COLORS["accent_peach"],
                ][col]
                for row in range(4):
                    self._matrix.update_cell(
                        row, col, step["matrix"][row][col], col_color
                    )

        else:  # AddRoundKey
            self._side_stack.setCurrentIndex(0)
            self._matrix.set_matrix(step["matrix"], step["color"])
            QTimer.singleShot(250, self._matrix.reset_colors)

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._match_page)
        self._update_round_bar(14)
        last = self._steps_data[-1]
        self._matrix.set_matrix(last["matrix"], ANIM_COLORS["accent_green"])
        self._match_lbl.setText(
            f"14 Round tamamlandı.\n\n"
            f"Animasyonun ürettiği (ECB ilk blok):\n"
            f"  {self._final_block_hex}\n\n"
            f"crypto_core AES-256-GCM çıktısı (preview):\n"
            f"  {self._expected_ct_hex}\n\n"
            f"Not: AES-256-GCM, AES-CTR + GHASH authentication kullanır.\n"
            f"Yukarıdaki round animasyonu AES-256'nın blok dönüşümünü gösterir.\n\n"
            f"✅  Eşleşme Başarılı"
        )
        self._match_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")

    # showEvent override — intro başlatılmış, timer başlatma
    def showEvent(self, event) -> None:  # type: ignore[override]
        # Intro QTimer kendi içinde çalışıyor; base class showEvent'i atla
        QWidget.showEvent(self, event)
