# animation_modals/sha256_animation.py
"""
SHA256AnimationWindow — SHA-256 hash sürecini görselleştirir.
• Her 512-bit blok için A-H register diyagramı (QPainter)
• Blok zinciri: Blok kartları okla birbirine bağlı
• Manuel navigasyon: kullanıcı ◀ / ▶ ile ilerler
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QLabel, QScrollArea, QSizePolicy,
    QVBoxLayout, QHBoxLayout, QWidget,
)
from .base import CryptoAnimationWindow, ANIM_COLORS
from .sha256_pure import sha256_steps

# Renk eşlemesi — her register farklı renk
_REG_COLORS = [
    "#89b4fa",  # A — blue
    "#cba6f7",  # B — mauve
    "#a6e3a1",  # C — green
    "#f9e2af",  # D — yellow
    "#fab387",  # E — peach
    "#94e2d5",  # F — teal
    "#f38ba8",  # G — red
    "#74c7ec",  # H — sky
]
_REG_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H"]


# ---------------------------------------------------------------------------
# Sıkıştırma fonksiyonu diyagramı (QPainter tabanlı widget)
# ---------------------------------------------------------------------------

class _SHA256DiagramWidget(QWidget):
    """
    Tek bir SHA-256 round'u için A-H sıkıştırma fonksiyonu diyagramını çizer.

    Gösterim:
      Üst satır  : 8 renkli kutu (A-H giriş değerleri)
      Orta bölge : T1 ve T2 hesaplama kutuları + K/W değerleri
      Alt satır  : 8 renkli kutu (A'-H' çıkış değerleri)
      Oklar      : A→T2, E→T1, D+T1→E', T1+T2→A'
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(340)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        # Varsayılan veri
        self._regs_in: list[str] = ["--------"] * 8
        self._regs_out: list[str] = ["--------"] * 8
        self._t1 = "--------"
        self._t2 = "--------"
        self._w = "--------"
        self._k = "--------"
        self._round_no = 0

    def set_data(
        self,
        regs_in: list[str],
        regs_out: list[str],
        t1: str,
        t2: str,
        w: str,
        k: str,
        round_no: int,
    ) -> None:
        self._regs_in = regs_in
        self._regs_out = regs_out
        self._t1 = t1
        self._t2 = t2
        self._w = w
        self._k = k
        self._round_no = round_no
        self.update()

    # --- QPainter çizimi ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        box_w = max(60, min(80, (W - 80) // 8))
        box_h = 44
        gap = max(3, (W - 80 - 8 * box_w) // 7)
        total = 8 * box_w + 7 * gap
        ox = (W - total) // 2  # yatay merkez

        top_y = 12
        mid_y = top_y + box_h + 50
        bot_y = mid_y + 90

        font_lbl = QFont("Segoe UI", 9, QFont.Weight.Bold)
        font_val = QFont("Courier New", 8)
        font_mid = QFont("Courier New", 9)

        # ── Üst satır: giriş registerları ──
        self._draw_register_row(
            p, self._regs_in, ox, top_y, box_w, box_h, gap,
            font_lbl, font_val, suffix=""
        )

        # ── T2 ve T1 kutuları ──
        t2_x = ox
        t2_w = int(total * 0.38)
        t1_x = ox + total - int(total * 0.52)
        t1_w = int(total * 0.52)

        p.setFont(font_mid)

        # T2 kutusu
        self._draw_box(p, t2_x, mid_y, t2_w, 72,
                       QColor("#3b3b5c"), QColor(ANIM_COLORS["accent_mauve"]))
        p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
        p.drawText(QRect(t2_x + 4, mid_y + 4, t2_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, "T2 = Σ0(A) + Maj(A,B,C)")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t2_x + 4, mid_y + 26, t2_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, f"= {self._t2}")

        # T1 kutusu
        self._draw_box(p, t1_x, mid_y, t1_w, 72,
                       QColor("#3b3b5c"), QColor(ANIM_COLORS["accent_yellow"]))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(t1_x + 4, mid_y + 4, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   "T1 = Σ1(E) + Ch(E,F,G) + H + K + W")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t1_x + 4, mid_y + 26, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, f"= {self._t1}")
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(t1_x + 4, mid_y + 48, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   f"K={self._k[:6]}  W={self._w[:6]}")

        # ── Oklar ──
        pen = QPen(QColor(ANIM_COLORS["accent_blue"]), 2)
        pen.setStyle(Qt.PenStyle.SolidLine)
        p.setPen(pen)

        # A'nın merkezi → T2 kutusunun üstü
        a_cx = ox + box_w // 2
        p.drawLine(a_cx, top_y + box_h, a_cx, top_y + box_h + 20)
        p.drawLine(a_cx, top_y + box_h + 20, t2_x + t2_w // 2, mid_y)
        self._arrowhead(p, t2_x + t2_w // 2, mid_y)

        # E'nin merkezi → T1 kutusunun üstü
        e_cx = ox + 4 * (box_w + gap) + box_w // 2
        p.drawLine(e_cx, top_y + box_h, e_cx, top_y + box_h + 20)
        p.drawLine(e_cx, top_y + box_h + 20, t1_x + t1_w // 2, mid_y)
        self._arrowhead(p, t1_x + t1_w // 2, mid_y)

        # T2 → A' (yeni A = T1 + T2)
        pen2 = QPen(QColor(ANIM_COLORS["accent_mauve"]), 2)
        p.setPen(pen2)
        a_out_cx = ox + box_w // 2
        p.drawLine(t2_x + t2_w // 2, mid_y + 72, a_out_cx, bot_y)
        self._arrowhead(p, a_out_cx, bot_y)

        # T1 → E' (yeni E = D + T1)
        pen3 = QPen(QColor(ANIM_COLORS["accent_yellow"]), 2)
        p.setPen(pen3)
        e_out_cx = ox + 4 * (box_w + gap) + box_w // 2
        p.drawLine(t1_x + t1_w // 2, mid_y + 72, e_out_cx, bot_y)
        self._arrowhead(p, e_out_cx, bot_y)

        # D → E' (D + T1 → yeni E)
        pen4 = QPen(QColor(ANIM_COLORS["accent_green"]), 1)
        pen4.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen4)
        d_cx = ox + 3 * (box_w + gap) + box_w // 2
        p.drawLine(d_cx, top_y + box_h, d_cx, bot_y)
        p.drawLine(d_cx, bot_y, e_out_cx, bot_y)

        # Kaydırma okları: B←A, C←B ... (basit sağa oklar, üst satırın altı)
        pen5 = QPen(QColor(ANIM_COLORS["text_muted"]), 1)
        pen5.setStyle(Qt.PenStyle.DotLine)
        p.setPen(pen5)
        shift_y = top_y + box_h + 8
        for i in range(1, 8):
            if i == 4:
                continue  # E farklı hesaplanıyor, atla
            src_cx = ox + (i - 1) * (box_w + gap) + box_w // 2
            dst_cx = ox + i * (box_w + gap) + box_w // 2
            p.drawLine(src_cx, shift_y, dst_cx, shift_y)
            self._arrowhead(p, dst_cx, shift_y, size=5)

        # ── Alt satır: çıkış registerları ──
        self._draw_register_row(
            p, self._regs_out, ox, bot_y, box_w, box_h, gap,
            font_lbl, font_val, suffix="'"
        )

        # Round numarası
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(QRect(0, 0, W, 14), Qt.AlignmentFlag.AlignRight,
                   f"Round {self._round_no}/64  ")

        p.end()

    # --- Yardımcılar ---

    def _draw_register_row(
        self, p: QPainter,
        values: list[str], ox: int, y: int,
        box_w: int, box_h: int, gap: int,
        font_lbl: QFont, font_val: QFont,
        suffix: str,
    ) -> None:
        for i, (lbl, val, col) in enumerate(
            zip(_REG_LABELS, values, _REG_COLORS)
        ):
            x = ox + i * (box_w + gap)
            self._draw_box(p, x, y, box_w, box_h,
                           QColor(col + "33"), QColor(col))
            p.setFont(font_lbl)
            p.setPen(QColor(col))
            p.drawText(QRect(x, y + 2, box_w, 16),
                       Qt.AlignmentFlag.AlignCenter, lbl + suffix)
            p.setFont(font_val)
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(x + 2, y + 20, box_w - 4, 20),
                       Qt.AlignmentFlag.AlignCenter, val[:8])

    @staticmethod
    def _draw_box(
        p: QPainter, x: int, y: int, w: int, h: int,
        fill: QColor, border: QColor,
    ) -> None:
        p.setBrush(QBrush(fill))
        pen = QPen(border, 1)
        p.setPen(pen)
        p.drawRoundedRect(x, y, w, h, 4, 4)

    @staticmethod
    def _arrowhead(p: QPainter, x: int, y: int, size: int = 6) -> None:
        """Küçük içi dolu ok ucu."""
        pts = QPolygon([
            QPoint(x, y),
            QPoint(x - size, y - size * 2),
            QPoint(x + size, y - size * 2),
        ])
        p.setBrush(QBrush(p.pen().color()))
        p.drawPolygon(pts)


# ---------------------------------------------------------------------------
# SHA-256 Animasyon Penceresi
# ---------------------------------------------------------------------------

class SHA256AnimationWindow(CryptoAnimationWindow):
    """
    SHA-256 animasyon penceresi.

    Adımlar:
      0        : Padding görselleştirmesi
      1..N     : Her 512-bit blok için kompresyon diyagramı (3 snapshot: r1,r32,r64)
      son adım : Hash eşleşmesi (_show_match_result)

    Parametreler:
      message      : kullanıcının orijinal mesaj metni
      expected_hash: crypto_core'un ürettiği hex hash
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

        # Adım 0: padding
        # Adım 1..3*N: her blok için 3 snapshot (r1, r32, r64)
        # Son adım: eşleşme (_show_match_result)
        snaps = self._data["round_snapshots"]
        # 3 snapshot per block
        total = 1 + len(snaps)   # padding + all snapshots
        super().__init__(
            "🔐  SHA-256 Hash Animasyonu",
            total,
            manual_mode=True,
        )
        self._snaps = snaps

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        from PyQt6.QtWidgets import QStackedWidget

        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        # Sayfa 0 — Padding
        self._page_padding = self._make_padding_page()
        self._stack.addWidget(self._page_padding)

        # Sayfa 1 — Kompresyon diyagramı (tüm snapshot'lar için tek sayfa, veri güncellenir)
        self._page_diagram = self._make_diagram_page()
        self._stack.addWidget(self._page_diagram)

        # Sayfa 2 — Eşleşme
        self._page_match = self._make_match_page()
        self._stack.addWidget(self._page_match)

    def _make_padding_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Adım 1 — Padding ve Blok Yapısı")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        d = self._data
        bc = d["blocks_count"]
        preview = d["binary_preview"]
        padded_len = d["padded_len"]

        info = QLabel(
            f"Mesaj: \"{self._message[:50]}\"\n\n"
            f"İlk 8 byte (binary):\n  {preview}\n\n"
            f"Padding işlemleri:\n"
            f"  1. '1' biti eklendi\n"
            f"  2. '0' bitleri ile 512'nin katına tamamlandı\n"
            f"  3. Sonuna 64-bit mesaj uzunluğu eklendi\n\n"
            f"Sonuç: {padded_len} byte → {bc} adet 512-bit blok\n\n"
            + "\n".join(
                f"  ▪ Blok {i+1}:  byte {i*64} – {(i+1)*64-1}"
                for i in range(bc)
            )
        )
        info.setFont(QFont("Courier New", 12))
        info.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    def _make_diagram_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)

        self._diag_title = QLabel()
        self._diag_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._diag_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._diag_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._diag_title)

        self._diag_widget = _SHA256DiagramWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._diag_widget)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll, stretch=1)

        # Hash zinciri göstergesi (alt)
        self._chain_lbl = QLabel()
        self._chain_lbl.setFont(QFont("Courier New", 10))
        self._chain_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._chain_lbl.setWordWrap(True)
        self._chain_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._chain_lbl)
        return w

    def _make_match_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(scroll)
        return w

    # ------------------------------------------------------------------
    # Adım render'ı
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        if step_idx == 0:
            self._stack.setCurrentWidget(self._page_padding)
            return

        # step_idx 1..len(snaps) → snapshot[step_idx - 1]
        snap_idx = step_idx - 1
        if snap_idx >= len(self._snaps):
            return

        snap = self._snaps[snap_idx]
        self._stack.setCurrentWidget(self._page_diagram)

        # Hangi blok, hangi round?
        snap_round = snap["round"]  # 1, 32, veya 64
        block_no = snap_idx // 3 + 1  # 3 snapshot per block
        self._diag_title.setText(
            f"Blok {block_no} / {self._data['blocks_count']}  —  "
            f"Sıkıştırma Round {snap_round} / 64"
        )

        # Mevcut register değerleri (bu snapshot'taki çıkış)
        regs_out = snap["registers"]  # [a, b, c, d, e, f, g, h] sonrası

        # Bir önceki snapshot'tan giriş değerleri (veya H0 sabitleri)
        if snap_idx > 0 and snap_idx % 3 != 0:
            regs_in = self._snaps[snap_idx - 1]["registers"]
        else:
            regs_in = self._data["initial_h"]

        self._diag_widget.set_data(
            regs_in=regs_in,
            regs_out=regs_out,
            t1=snap.get("t1", "--------"),
            t2=snap.get("t2", "--------"),
            w=snap.get("w", "--------"),
            k=snap.get("k", "--------"),
            round_no=snap_round,
        )

        # Zincir göstergesi
        chain_parts = []
        for i in range(block_no):
            if i < block_no - 1:
                chain_parts.append(f"[Blok {i+1} →]")
            else:
                chain_parts.append(f"[Blok {i+1} ←burada]")
        self._chain_lbl.setText("  →  ".join(chain_parts) + "  →  [Final Hash]")

    def _show_match_result(self) -> None:
        self._stack.setCurrentWidget(self._page_match)
        computed = self._data["final_hash"]
        match = computed == self._expected_hash
        icon = "✅" if match else "❌"
        color = ANIM_COLORS["accent_green"] if match else ANIM_COLORS["accent_peach"]

        snaps = self._data["round_snapshots"]
        snap_summary = "\n".join(
            f"  Round {s['round']:>2}:  A={s['a']}  E={s['e']}"
            for s in snaps
        )
        self._match_lbl.setText(
            f"64-round sıkıştırma tamamlandı.\n\n"
            f"Round anlık görüntüleri:\n{snap_summary}\n\n"
            f"{'─' * 64}\n\n"
            f"Animasyonun hesapladığı:\n  {computed}\n\n"
            f"crypto_core çıktısı:\n  {self._expected_hash}\n\n"
            f"{icon}  Eşleşme Başarılı"
        )
        self._match_lbl.setStyleSheet(f"color: {color};")
