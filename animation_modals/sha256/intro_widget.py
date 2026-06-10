# animation_modals/sha256/intro_widget.py
"""SHA-256 ön tanıtma (intro) widget'ı."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)
from ..base import CryptoAnimationWindow, ANIM_COLORS, get_animation_tick_ms
from .register_demo import _RegisterDemoWidget

# ---------------------------------------------------------------------------
# SHA-256 Ön Tanıtma Widget'ı
# ---------------------------------------------------------------------------

class _SHA256IntroWidget(QWidget):
    """
    SHA-256 ön tanıtma widget'ı.
    Sol  : canlı A-H register animasyonu (_RegisterDemoWidget)
    Sağ  : SHA-256 süreç akış şeması (kademeli görünüm, 500ms/adım)
    Alt  : "Görselleştirmeyi Başlat" butonu
    """

    def __init__(self, on_start: "callable", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_start = on_start
        self._phase = 0
        self._reveal_widgets: list[QWidget] = []
        self._reveal_timer = QTimer(self)
        self._reveal_timer.timeout.connect(self._reveal_next)
        self._init_ui()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 6, 12, 6)
        main.setSpacing(4)

        # Başlık
        title = QLabel("SHA-256  Hash Algoritması")
        title.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(title)
        self._title_lbl = title

        # ── Yatay bölüm: sol=register demo, sağ=akış şeması ──
        h_row = QHBoxLayout()
        h_row.setSpacing(12)
        main.addLayout(h_row)

        # Sol: register animasyonu
        left_frame = QFrame()
        left_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 10px; }}"
        )
        self._left_frame = left_frame
        left_lay = QVBoxLayout(left_frame)
        left_lay.setContentsMargins(8, 6, 8, 6)
        left_lay.setSpacing(2)
        demo_lbl = QLabel("Sıkıştırma Fonksiyonu Önizlemesi")
        demo_lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        demo_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        demo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._demo_lbl = demo_lbl
        left_lay.addWidget(demo_lbl)
        self._reg_demo = _RegisterDemoWidget()
        left_lay.addWidget(self._reg_demo, stretch=1)
        h_row.addWidget(left_frame, stretch=2)

        # Sağ: akış şeması — dış _anim_scroll zaten kaydırma sağlar, iç scroll gereksiz
        right_container = QWidget()
        right_container_lay = QVBoxLayout(right_container)
        right_container_lay.setContentsMargins(0, 0, 0, 0)
        right_container_lay.setSpacing(4)
        h_row.addWidget(right_container, stretch=3)

        right_lay = right_container_lay
        right_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Akış şeması kutular + oklar. Renk DEĞERİ değil ANAHTARI saklanır;
        # tema değişiminde restyle ANIM_COLORS[key] ile yeniden çözer.
        flow_items = [
            ("plain",  "Mesaj Girişi",                          "text_secondary",  None),
            ("arrow",  None, None, None),
            ("detail", "Padding  (512-bit katı)",                "accent_peach",
             ["→  '1' biti eklenir",
              "→  '0' bitleriyle 512-bit katına tamamlanır",
              "→  Sonuna 64-bit mesaj uzunluğu yazılır"]),
            ("arrow",  None, None, None),
            ("detail", "Blok Bölme  (N × 512-bit)",              "accent_blue",
             ["→  Her blok 64 bayt / 512 bit",
              "→  16 adet 32-bit kelime  (W0 – W15)"]),
            ("arrow",  None, None, None),
            ("detail", "Sıkıştırma  (64 Round / Blok)",          "accent_mauve",
             ["→  Çalışma değişkenleri: A, B, C, D, E, F, G, H",
              "→  T1 = Σ1(E) + Ch(E,F,G) + H + Kᵢ + Wᵢ",
              "→  T2 = Σ0(A) + Maj(A,B,C)"]),
            ("arrow",  None, None, None),
            ("plain",  "H Değerlerini Güncelle",                 "accent_yellow",   None),
            ("arrow",  None, None, None),
            ("plain",  "256-bit SHA-256 Hash",                   "accent_green",    None),
        ]

        # restyle() için stillenebilir kutu/ok widget'larını sakla.
        self._flow_widgets: list[QFrame] = []
        self._arrow_lbls: list[QLabel] = []
        for kind, text, color_key, subs in flow_items:
            if kind == "arrow":
                w = self._make_arrow()
                self._arrow_lbls.append(w)
            elif kind == "plain":
                w = self._make_box(text, color_key)
                self._flow_widgets.append(w)
            else:
                w = self._make_detail_box(text, subs, color_key)
                self._flow_widgets.append(w)
            right_lay.addWidget(w)
            w.setVisible(False)
            self._reveal_widgets.append(w)

        # Başla butonu — scroll area dışında, her zaman görünür konumda
        self._btn_start = QPushButton("Görselleştirmeyi Başlat")
        self._btn_start.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
        self._btn_start.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; "
            f"border-radius: 6px; padding: 6px 18px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        self._btn_start.setVisible(False)
        self._btn_start.clicked.connect(self._on_start)
        right_container_lay.addWidget(self._btn_start, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._reveal_widgets.append(self._btn_start)

    @staticmethod
    def _make_box(text: str, color_key: str) -> QFrame:
        color = ANIM_COLORS[color_key]
        f = QFrame()
        f._color_key = color_key  # type: ignore[attr-defined]
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 5, 8, 5)
        lbl = QLabel(text)
        lbl.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {color}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        f._title_lbl = lbl       # type: ignore[attr-defined]
        f._sub_lbls = []          # type: ignore[attr-defined]
        return f

    @staticmethod
    def _make_detail_box(title: str, items: list[str], color_key: str) -> QFrame:
        color = ANIM_COLORS[color_key]
        f = QFrame()
        f._color_key = color_key  # type: ignore[attr-defined]
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 5, 8, 5)
        lay.setSpacing(2)
        t = QLabel(title)
        t.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {color}; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setWordWrap(True)
        lay.addWidget(t)
        sub_lbls = []
        for item in items:
            o = QLabel(item)
            o.setFont(QFont("Segoe UI", 9))
            o.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']}; border: none;")
            o.setWordWrap(True)
            lay.addWidget(o)
            sub_lbls.append(o)
        f._title_lbl = t          # type: ignore[attr-defined]
        f._sub_lbls = sub_lbls    # type: ignore[attr-defined]
        return f

    @staticmethod
    def _restyle_flow_box(f: QFrame) -> None:
        """Tema değişiminde akış kutusunu (plain/detail) saklı color_key ile
        yeniden boyar; metin/görünürlük korunur."""
        color = ANIM_COLORS[f._color_key]  # type: ignore[attr-defined]
        f.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {color}; border-radius: 6px; }}"
        )
        f._title_lbl.setStyleSheet(f"color: {color}; border: none;")  # type: ignore[attr-defined]
        for o in f._sub_lbls:  # type: ignore[attr-defined]
            o.setStyleSheet(
                f"color: {ANIM_COLORS['text_secondary']}; border: none;")

    @staticmethod
    def _make_arrow() -> QLabel:
        lbl = QLabel("⬇")
        lbl.setFont(QFont("Segoe UI", 12))
        lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(16)
        return lbl

    def restyle(self) -> None:
        """Tema değişiminde QLabel/QFrame tabanlı içeriği DURUM BOZMADAN yeniden
        boyar (metin/görünürlük/timer korunur). İçteki _RegisterDemoWidget
        QPainter'dır → refresh_theme'deki update() ile yenilenir."""
        self._title_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        self._left_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 10px; }}"
        )
        self._demo_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        for f in self._flow_widgets:
            self._restyle_flow_box(f)
        for lbl in self._arrow_lbls:
            lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']}; border: none;")
        self._btn_start.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; "
            f"border-radius: 6px; padding: 6px 18px; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )

    def start(self) -> None:
        self._reveal_timer.start(get_animation_tick_ms(500))

    def _reveal_next(self) -> None:
        if self._phase >= len(self._reveal_widgets):
            self._reveal_timer.stop()
            return
        self._reveal_widgets[self._phase].setVisible(True)
        self._phase += 1


