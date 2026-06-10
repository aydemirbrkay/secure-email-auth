# animation_modals/aes/intro_widget.py
"""AES giriş animasyonu: canlı matris demo + round yapısı şeması."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS
from arayuz.theme import get_animation_tick_ms

# ---------------------------------------------------------------------------
# Canlı matris demo widget'ı — intro için AES operasyonlarını simüle eder
# ---------------------------------------------------------------------------

class _MatrixDemoWidget(QWidget):
    """
    AES intro ekranında gösterilen canlı 4×4 matris animasyonu.
    QTimer ile SubBytes → ShiftRows → MixColumns → AddRoundKey döngüsü yapar.
    """

    _OP_COLORS = [
        ANIM_COLORS["accent_yellow"],   # SubBytes
        ANIM_COLORS["accent_blue"],     # ShiftRows
        ANIM_COLORS["accent_mauve"],    # MixColumns
        ANIM_COLORS["accent_peach"],    # AddRoundKey
    ]
    _OP_NAMES = ["SubBytes", "ShiftRows", "MixColumns", "AddRoundKey"]

    # Başlangıç demo değerleri (görsel amaçlı)
    _INIT_VALS = [
        ["19", "a0", "9a", "e9"],
        ["3d", "f4", "c6", "f8"],
        ["e3", "e2", "8d", "48"],
        ["be", "2b", "2a", "08"],
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tick = 0
        self._cells = [row[:] for row in self._INIT_VALS]
        self._bg_colors = [[ANIM_COLORS["bg_card"]] * 4 for _ in range(4)]
        self._op_idx = 0      # hangi operasyon (0-3)
        self._op_tick = 0     # operasyon içi adım
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        # Hareket azaltma açıksa hızlı tick yumuşatılır (110 → 330 ms).
        self._timer.start(get_animation_tick_ms(110))
        # SHA introsuyla aynı: matris genişliği sınırlanmaz; sol panel (stretch=2)
        # büyüdükçe matris de büyür. Hücreler paintEvent'te adaptif ölçeklendiği
        # için her boyutta okunaklı kalır.
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _step(self) -> None:
        self._tick += 1
        t = self._tick

        # Her operasyon 24 tick sürer
        op = (t // 24) % 4
        sub = t % 24
        self._op_idx = op

        if op == 0:  # SubBytes: hücreleri sırayla highlight et
            r, c = divmod(sub % 16, 4)
            self._bg_colors = [[ANIM_COLORS["bg_card"]] * 4 for _ in range(4)]
            self._bg_colors[r][c] = self._OP_COLORS[0]
            self._cells[r][c] = f"{(self._tick * 37 + r * 4 + c) % 256:02x}"

        elif op == 1:  # ShiftRows: satır satır highlight
            row = sub // 6
            row = min(row, 3)
            self._bg_colors = [[ANIM_COLORS["bg_card"]] * 4 for _ in range(4)]
            row_colors = [
                ANIM_COLORS["text_muted"],
                ANIM_COLORS["accent_blue"],
                ANIM_COLORS["accent_mauve"],
                ANIM_COLORS["accent_peach"],
            ]
            for c in range(4):
                self._bg_colors[row][c] = row_colors[row]

        elif op == 2:  # MixColumns: sütun sütun highlight
            col = sub // 6
            col = min(col, 3)
            self._bg_colors = [[ANIM_COLORS["bg_card"]] * 4 for _ in range(4)]
            col_colors = [
                ANIM_COLORS["accent_blue"],
                ANIM_COLORS["accent_mauve"],
                ANIM_COLORS["accent_yellow"],
                ANIM_COLORS["accent_peach"],
            ]
            for r in range(4):
                self._bg_colors[r][col] = col_colors[col]

        else:  # AddRoundKey: tümü yanıp söner
            lit = (sub % 6) < 3
            color = self._OP_COLORS[3] if lit else ANIM_COLORS["bg_card"]
            self._bg_colors = [[color] * 4 for _ in range(4)]

        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        margin = 12
        label_h = 28
        avail_w = W - 2 * margin
        avail_h = H - label_h - margin
        cell_size = min(avail_w // 4, avail_h // 4) - 4
        gap = 4
        grid_w = 4 * cell_size + 3 * gap
        grid_h = 4 * cell_size + 3 * gap
        ox = (W - grid_w) // 2
        oy = label_h + (avail_h - grid_h) // 2

        # Operasyon etiketi
        op_color = self._OP_COLORS[self._op_idx]
        p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        p.setPen(QColor(op_color))
        p.drawText(QRect(0, 4, W, label_h - 4),
                   Qt.AlignmentFlag.AlignCenter,
                   self._OP_NAMES[self._op_idx])

        # Hücreler
        font_val = QFont("Courier New", max(9, cell_size // 4), QFont.Weight.Bold)
        for r in range(4):
            for c in range(4):
                x = ox + c * (cell_size + gap)
                y = oy + r * (cell_size + gap)
                bg = QColor(self._bg_colors[r][c])
                border = QColor(bg).lighter(150)
                p.setBrush(QBrush(bg))
                p.setPen(QPen(border, 1))
                p.drawRoundedRect(x, y, cell_size, cell_size, 5, 5)
                p.setFont(font_val)
                p.setPen(QColor(ANIM_COLORS["text_primary"]))
                p.drawText(QRect(x, y, cell_size, cell_size),
                           Qt.AlignmentFlag.AlignCenter, self._cells[r][c])

        p.end()


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
        # 16 px sağ margin → kullanıcının istediği "~5% sağ boşluk"
        main.setContentsMargins(8, 4, 16, 4)
        main.setSpacing(3)

        # ── Yatay bölüm: sol=canlı matris, sağ=başlık + akış şeması ──
        # (Başlık eskiden main'de full-width centered idi → kullanıcı geri
        # bildirimi: başlık adımların üstünde, sağ kolonun başında olsun.)
        h_row = QHBoxLayout()
        h_row.setSpacing(8)
        main.addLayout(h_row)

        # Sol: canlı matris animasyonu. SHA introsuyla BİREBİR aynı yerleşim:
        # sabit dar genişlik (200-240px) yerine oranlı stretch=2 ile büyük açılır,
        # ekranın solunu kaplar. Matrix demo paintEvent'te adaptif ölçeklendiği
        # için büyük panelde de okunaklı kalır.
        self._left_frame = QFrame()
        left_frame = self._left_frame
        left_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(6, 4, 6, 4)
        left_lay.setSpacing(2)
        self._demo_title = QLabel("Canlı Şifreleme Önizlemesi")
        self._demo_title.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        self._demo_title.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._demo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._demo_title.setWordWrap(True)
        left_lay.addWidget(self._demo_title)
        self._matrix_demo = _MatrixDemoWidget()
        left_lay.addWidget(self._matrix_demo, stretch=1)
        h_row.addWidget(left_frame, stretch=2)

        # Sağ: başlık + akış şeması — SHA gibi stretch=3 ile kalan alanı alır.
        # İçerik artık sola yaslı DEĞİL; kutular tam genişlik olduğundan panel
        # ortasında düzgün dolar (SHA introsundaki düzen).
        right_w = QWidget()
        right_lay = QVBoxLayout(right_w)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(4)
        right_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_w.setMinimumWidth(230)
        h_row.addWidget(right_w, stretch=3)

        # ── Sağ taraf: önce BAŞLIK, sonra akış şeması widget'ları ──

        self._intro_title = QLabel("AES-256  Şifreleme Süreci")
        self._intro_title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        self._intro_title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        self._intro_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        right_lay.addWidget(self._intro_title)

        right_lay.addSpacing(4)

        self._arrows: list[QLabel] = []

        # Giriş kutusu
        self._intro_plain = self._make_box(
            "Düz Metin  (Plaintext)", "text_secondary"
        )
        right_lay.addWidget(self._intro_plain)
        self._intro_plain.setVisible(False)
        self._widgets.append(self._intro_plain)

        arr0 = self._make_arrow()
        right_lay.addWidget(arr0)
        arr0.setVisible(False)
        self._widgets.append(arr0)
        self._arrows.append(arr0)

        self._box_r0 = self._make_round_box(
            "Initial Round  (Round 0)",
            ["AddRoundKey"],
            "accent_peach",
        )
        right_lay.addWidget(self._box_r0)
        self._box_r0.setVisible(False)
        self._widgets.append(self._box_r0)

        arr1 = self._make_arrow()
        right_lay.addWidget(arr1)
        arr1.setVisible(False)
        self._widgets.append(arr1)
        self._arrows.append(arr1)

        self._box_main = self._make_round_box(
            "Ana Roundlar  (R1 – R13)",
            ["1-SubBytes", "2-ShiftRows", "3-MixColumns", "4-AddRoundKey"],
            "accent_blue",
        )
        right_lay.addWidget(self._box_main)
        self._box_main.setVisible(False)
        self._widgets.append(self._box_main)

        arr2 = self._make_arrow()
        right_lay.addWidget(arr2)
        arr2.setVisible(False)
        self._widgets.append(arr2)
        self._arrows.append(arr2)

        self._box_r14 = self._make_round_box(
            "Son Round  (R14)",
            ["1-SubBytes", "2-ShiftRows", "3-AddRoundKey  (MixColumns yok)"],
            "accent_green",
        )
        right_lay.addWidget(self._box_r14)
        self._box_r14.setVisible(False)
        self._widgets.append(self._box_r14)

        arr3 = self._make_arrow()
        right_lay.addWidget(arr3)
        arr3.setVisible(False)
        self._widgets.append(arr3)
        self._arrows.append(arr3)

        self._intro_cipher = self._make_box(
            "Şifreli Metin  (Ciphertext)", "accent_green"
        )
        right_lay.addWidget(self._intro_cipher)
        self._intro_cipher.setVisible(False)
        self._widgets.append(self._intro_cipher)

        right_lay.addSpacing(16)

        # Başla butonu
        self._btn_start = QPushButton("Görselleştirmeyi Başlat")
        self._btn_start.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
        self._btn_start.setStyleSheet(self._start_btn_style())
        self._btn_start.setVisible(False)
        self._btn_start.clicked.connect(self._on_complete)
        right_lay.addWidget(self._btn_start, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._widgets.append(self._btn_start)
        right_lay.addStretch()

    @staticmethod
    def _make_box(text: str, color_key: str) -> QFrame:
        color = ANIM_COLORS[color_key]
        f = QFrame()
        # SHA introsuyla aynı: kutu genişliği SINIRLANMAZ; sağ panelin tam
        # genişliğine yayılır. Tüm kutular aynı parent genişliğini aldığından
        # HEPSİ EŞİT genişlikte görünür ve panel düzgün dolar.
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(6, 3, 6, 3)  # daha kompakt
        lbl = QLabel(text)
        lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Kısa, sabit metin → word-wrap KAPALI. Açık olursa kutu sizeHint'i
        # minimum sarma genişliğine düşüp başlık 2 satıra kırpılır.
        lbl.setWordWrap(False)
        lay.addWidget(lbl)
        f._accent_key = color_key      # type: ignore[attr-defined]
        f._accent_lbls = [lbl]         # type: ignore[attr-defined]
        f._muted_lbls = []             # type: ignore[attr-defined]
        return f

    @staticmethod
    def _make_round_box(title: str, ops: list[str], color_key: str) -> QFrame:
        color = ANIM_COLORS[color_key]
        f = QFrame()
        # SHA introsuyla aynı: kutu sağ panelin tam genişliğine yayılır (tüm
        # kutular eşit genişlikte). Max-width sınırı kaldırıldı.
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 4, 8, 4)  # daha kompakt — boş alan azaldı
        lay.setSpacing(1)
        t = QLabel(title)
        t.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {color}; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Kısa başlık → word-wrap KAPALI (kutu içeriğe göre boyutlansın,
        # sarılıp kırpılmasın).
        t.setWordWrap(False)
        lay.addWidget(t)
        muted = []
        for op in ops:
            o = QLabel(f"  →  {op}")
            o.setFont(QFont("Segoe UI", 9))
            o.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']}; border: none;")
            o.setWordWrap(False)
            lay.addWidget(o)
            muted.append(o)
        f._accent_key = color_key      # type: ignore[attr-defined]
        f._accent_lbls = [t]           # type: ignore[attr-defined]
        f._muted_lbls = muted          # type: ignore[attr-defined]
        return f

    @staticmethod
    def _make_arrow() -> QLabel:
        lbl = QLabel("⬇")
        lbl.setFont(QFont("Segoe UI", 14))
        # SHA introsuyla aynı: kutular tam genişlik ve ortalı olduğundan ok da
        # ortalanır (sola yaslı girinti kaldırıldı).
        lbl.setStyleSheet(
            f"color: {ANIM_COLORS['text_muted']}; border: none;"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(20)
        return lbl

    @staticmethod
    def _start_btn_style() -> str:
        return (
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; "
            f"border-radius: 6px; padding: 6px 18px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )

    def restyle(self) -> None:
        """Tema değişiminde QLabel/QFrame içeriğini durum bozmadan yeniden boyar.
        _MatrixDemoWidget (QPainter) update() ile yenilenir."""
        self._left_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        self._demo_title.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._intro_title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        for box in (self._intro_plain, self._box_r0, self._box_main,
                    self._box_r14, self._intro_cipher):
            color = ANIM_COLORS[box._accent_key]  # type: ignore[attr-defined]
            box.setStyleSheet(
                f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
                f"border: 2px solid {color}; border-radius: 6px; }}"
            )
            for lbl in box._accent_lbls:  # type: ignore[attr-defined]
                lbl.setStyleSheet(f"color: {color}; border: none;")
            for lbl in box._muted_lbls:  # type: ignore[attr-defined]
                lbl.setStyleSheet(
                    f"color: {ANIM_COLORS['text_secondary']}; border: none;"
                )
        for arr in self._arrows:
            arr.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; border: none;")
        self._btn_start.setStyleSheet(self._start_btn_style())

    def start(self) -> None:
        self._timer.start(get_animation_tick_ms(600))

    def _show_next_phase(self) -> None:
        if self._phase >= len(self._widgets):
            self._timer.stop()
            return
        self._widgets[self._phase].setVisible(True)
        self._phase += 1

