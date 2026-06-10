# animation_modals/sha256/diagram_widget.py
"""SHA-256 sıkıştırma fonksiyonu diyagramı (QPainter)."""
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
from ..base import CryptoAnimationWindow, ANIM_COLORS
from .constants import _REG_COLORS, _REG_LABELS

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

    # Animasyon aşamaları:
    # 0 = giriş registerları
    # 1 = A→T2 vurgusu
    # 2 = E→T1 vurgusu
    # 3 = T2→A' vurgusu
    # 4 = T1→E' vurgusu
    # 5 = tüm çıkış registerları (tamamlandı)
    _ANIM_PHASES = 6

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # İçerik gerçekte ~255 px'e sığar (aşama etiketi + giriş kutuları +
        # T1/T2 + çıkış kutuları + legend). Eski 340 px min, 230 px'lik scroll
        # alanına sığmayıp gereksiz DİKEY scroll açıyordu. Min/max gerçek
        # içeriğe yakın tutulur → diyagram tek bakışta görünür, alt navigasyon
        # butonları daima ekranda kalır.
        self.setMinimumHeight(265)
        self.setMaximumHeight(285)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        # Varsayılan veri
        self._regs_in: list[str] = ["--------"] * 8
        self._regs_out: list[str] = ["--------"] * 8
        self._t1 = "--------"
        self._t2 = "--------"
        self._w = "--------"
        self._k = "--------"
        self._round_no = 0
        # Animasyon
        self._phase = self._ANIM_PHASES  # başlangıçta statik
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._next_phase)
        # Aktif ok nabzı (pulse): faz içinde ok kalınlığını 3↔5 px arası
        # değiştirip "şu an bu ok akıyor" hissi verir. Ayrı, hızlı bir timer
        # ile faz timer'ından bağımsız çalışır.
        self._pulse_on = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._toggle_pulse)

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
        # Animasyonu başlat
        self._phase = 0
        self._anim_timer.start(380)
        self._pulse_on = True
        self._pulse_timer.start(190)  # faz süresinin yarısı → faz başına 1 nabız
        self.update()

    def _next_phase(self) -> None:
        """Bir sonraki animasyon fazına geç. Son faza ulaşınca hem faz hem nabız
        timer'ı durur (oklar 'tamamlandı' durumunda sabitlenir)."""
        self._phase += 1
        if self._phase >= self._ANIM_PHASES:
            self._phase = self._ANIM_PHASES
            self._anim_timer.stop()
            self._pulse_timer.stop()
            self._pulse_on = False
        self.update()

    def _toggle_pulse(self) -> None:
        """Aktif okun nabız durumunu çevirir (kalın↔ince) ve yeniden boyar.
        Yalnızca animasyon sürerken çağrılır; aksi halde oklar sabit kalır."""
        self._pulse_on = not self._pulse_on
        self.update()

    # --- QPainter çizimi ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ph = self._phase  # mevcut animasyon aşaması
        W = self.width()
        box_w = max(60, min(80, (W - 80) // 8))
        box_h = 44
        gap = max(3, (W - 80 - 8 * box_w) // 7)
        total = 8 * box_w + 7 * gap
        ox = (W - total) // 2

        # top_y = 24: aşama etiketi (y=0-16) ile register kutuları (y=24+)
        # arasında 8 px boşluk kalır → 'D + T1 → E' etiketi ile A register
        # kutusunun üst kenarı artık çakışmaz.
        top_y = 24
        mid_y = top_y + box_h + 36
        bot_y = mid_y + 84

        font_lbl = QFont("Georgia", 9, QFont.Weight.Bold)
        font_val = QFont("Courier New", 8)
        font_mid = QFont("Courier New", 9)

        # Aşamaya göre vurgu belirleme
        # ph 0: sadece giriş
        # ph 1: A→T2 aktif
        # ph 2: E→T1 aktif
        # ph 3: T2→A' aktif
        # ph 4: T1→E' aktif
        # ph 5+: tümü göster
        highlight_a_in   = ph >= 1  # A giriş registerı vurgusu
        highlight_e_in   = ph >= 2
        highlight_t2     = ph >= 1
        highlight_t1     = ph >= 2
        highlight_a_out  = ph >= 3
        highlight_e_out  = ph >= 4
        show_out         = ph >= 3

        # ── Üst satır: giriş registerları ──
        # A ve E aşamaya göre daha parlak gösterilir
        custom_in_colors = list(_REG_COLORS)
        if highlight_a_in:
            custom_in_colors[0] = ANIM_COLORS["accent_blue"]  # A parlar
        if highlight_e_in:
            custom_in_colors[4] = ANIM_COLORS["accent_yellow"]  # E parlar
        self._draw_register_row(
            p, self._regs_in, ox, top_y, box_w, box_h, gap,
            font_lbl, font_val, suffix="",
            custom_colors=custom_in_colors,
        )

        # ── T2 kutusu ──
        t2_x = ox
        t2_w = int(total * 0.38)
        t1_x = ox + total - int(total * 0.52)
        t1_w = int(total * 0.52)

        t2_border = QColor(ANIM_COLORS["accent_mauve"])
        t2_fill = QColor(ANIM_COLORS["hl_mauve"]) if highlight_t2 else QColor(ANIM_COLORS["bg_card"])
        self._draw_box(p, t2_x, mid_y, t2_w, 72, t2_fill, t2_border)
        p.setFont(font_mid)
        p.setPen(t2_border)
        p.drawText(QRect(t2_x + 4, mid_y + 4, t2_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, "T2 = Σ0(A) + Maj(A,B,C)")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t2_x + 4, mid_y + 26, t2_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, f"= {self._t2}" if ph >= 1 else "= ...")

        # ── T1 kutusu ──
        t1_border = QColor(ANIM_COLORS["accent_yellow"])
        t1_fill = QColor(ANIM_COLORS["hl_yellow"]) if highlight_t1 else QColor(ANIM_COLORS["bg_card"])
        self._draw_box(p, t1_x, mid_y, t1_w, 72, t1_fill, t1_border)
        p.setPen(t1_border)
        p.drawText(QRect(t1_x + 4, mid_y + 4, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   "T1 = Σ1(E) + Ch(E,F,G) + H + K + W")
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(t1_x + 4, mid_y + 26, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter, f"= {self._t1}" if ph >= 2 else "= ...")
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(t1_x + 4, mid_y + 48, t1_w - 8, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   f"K={self._k[:6]}  W={self._w[:6]}")

        # ── Oklar ──
        # Her ok 3 durumdan birinde: PASİF (henüz sırası gelmedi → soluk/ince),
        # AKTİF (o anki faz → kalın + parlak + büyük ok ucu + pulse), TAMAMLANDI
        # (geçti → düz, orta kalınlık). Böylece hangi değerin hangi kutuya gittiği
        # ve "şu an ne akıyor" net görünür (Görsel 4 düzeltmesi).
        # Aktif okta pulse: alt-tick ile 3↔5 px arası nabız (canlılık hissi).
        pulse = 5 if (self._anim_timer.isActive() and self._pulse_on) else 3
        a_cx = ox + box_w // 2
        e_cx = ox + 4 * (box_w + gap) + box_w // 2
        a_out_cx = ox + box_w // 2
        e_out_cx = ox + 4 * (box_w + gap) + box_w // 2
        d_cx = ox + 3 * (box_w + gap) + box_w // 2

        # A → T2 (aktif: ph==1; tamamlandı: ph>1)
        a_state = self._arrow_state(ph, active_at=1)
        self._draw_flow_arrow(
            p, ANIM_COLORS["accent_blue"], a_state, pulse,
            [(a_cx, top_y + box_h), (a_cx, top_y + box_h + 20),
             (t2_x + t2_w // 2, mid_y)],
            head="down", head_xy=(t2_x + t2_w // 2, mid_y),
            label="A", label_xy=(a_cx + 6, top_y + box_h + 6),
        )

        # E → T1 (aktif: ph==2)
        e_state = self._arrow_state(ph, active_at=2)
        self._draw_flow_arrow(
            p, ANIM_COLORS["accent_yellow"], e_state, pulse,
            [(e_cx, top_y + box_h), (e_cx, top_y + box_h + 20),
             (t1_x + t1_w // 2, mid_y)],
            head="down", head_xy=(t1_x + t1_w // 2, mid_y),
            label="E", label_xy=(e_cx + 6, top_y + box_h + 6),
        )

        # T2 → A' (aktif: ph==3). Etiket HEDEF kutu (A') hizasında, kutunun
        # hemen üstünde (bot_y - 16) → eskiden geniş T2 kutusunun merkezine
        # göre konumlanıp yanlışlıkla B' üstüne düşüyordu (Görsel 3).
        t2a_state = self._arrow_state(ph, active_at=3)
        self._draw_flow_arrow(
            p, ANIM_COLORS["accent_mauve"], t2a_state, pulse,
            [(t2_x + t2_w // 2, mid_y + 72), (a_out_cx, bot_y)],
            head="down", head_xy=(a_out_cx, bot_y),
            label="T2", label_xy=(a_out_cx + 6, bot_y - 16),
        )

        # T1 → E' (aktif: ph==4). Etiket HEDEF kutu (E') hizasında (eskiden T1
        # kutusu merkezine göre F' üstüne düşüyordu).
        t1e_state = self._arrow_state(ph, active_at=4)
        self._draw_flow_arrow(
            p, ANIM_COLORS["accent_yellow"], t1e_state, pulse,
            [(t1_x + t1_w // 2, mid_y + 72), (e_out_cx, bot_y)],
            head="down", head_xy=(e_out_cx, bot_y),
            label="T1", label_xy=(e_out_cx + 6, bot_y - 16),
        )

        # D → E' (kesikli, shift katkısı) — E' aktifken (ph==4) vurgulanır
        d_active = ph == 4
        d_col = QColor(ANIM_COLORS["accent_green"])
        if not (ph >= 4):
            d_col.setAlpha(90)  # henüz sırası gelmedi → soluk
        pen4 = QPen(d_col, 3 if d_active else 1)
        pen4.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen4)
        p.drawLine(d_cx, top_y + box_h, d_cx, bot_y)
        p.drawLine(d_cx, bot_y, e_out_cx, bot_y)
        self._arrowhead_right(p, e_out_cx, bot_y, size=8 if d_active else 6)
        p.setFont(QFont("IBM Plex Sans", 7, QFont.Weight.Bold))
        p.setPen(d_col)
        # "+D" etiketi E' kutusunun İÇİNE değil, kutunun ÜSTÜNDEKİ ok bölgesine
        # çizilir (bot_y - 16). Eskiden bot_y hizasında olduğu için çıkış
        # register kutusunun değeriyle çakışıyordu (Görsel 2).
        p.drawText(QRect(e_out_cx - box_w - 4, bot_y - 16, box_w, 14),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "+D")

        # ── Kaydırma okları: B→C', C→D', F→G', G→H' ──
        # SHA-256'da her round'da yalnız A' ve E' hesaplanır; diğer registerlar
        # bir SAĞA kaydırılır (B'=A, C'=B, ... ekranda gösterilen kaydırmalar).
        # Bu kaydırmalar ince/soluk diagonal oklarla gösterilir ki "tüm
        # registerlar hareket ediyor" hissi oluşsun ama ana işlem (T1/T2/A'/E')
        # öne çıkmaya devam etsin (oklar düşük alpha + 1px). Yalnız çıkış
        # görünürken (ph>=3) çizilir.
        if show_out:
            self._draw_shift_arrows(
                p, ox, top_y + box_h, bot_y, box_w, gap,
            )

        # ── Alt satır: çıkış registerları ──
        custom_out_colors = list(_REG_COLORS)
        if highlight_a_out:
            custom_out_colors[0] = ANIM_COLORS["accent_mauve"]  # A' vurgusu
        if highlight_e_out:
            custom_out_colors[4] = ANIM_COLORS["accent_yellow"]  # E' vurgusu
        out_vals = self._regs_out if show_out else ["--------"] * 8
        self._draw_register_row(
            p, out_vals, ox, bot_y, box_w, box_h, gap,
            font_lbl, font_val, suffix="'",
            custom_colors=custom_out_colors,
        )

        # Kaydırma açıklaması (legend)
        p.setFont(QFont("IBM Plex Sans", 8))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        legend_y = bot_y + box_h + 6
        p.drawText(QRect(ox, legend_y, total, 14),
                   Qt.AlignmentFlag.AlignCenter,
                   "B'=A  C'=B  D'=C  F'=E  G'=F  H'=G  (diğerleri kaydırılır)")

        # Aşama etiketi (sağ alt)
        phase_labels = [
            "Giriş registerları →",
            "A → T2 (Σ0 + Maj) ►",
            "E → T1 (Σ1 + Ch + H + K + W) ►",
            "T2 + T1 → A' ►",
            "D + T1 → E' ►",
            "✓ Round tamamlandı",
        ]
        p.setPen(QColor(ANIM_COLORS["accent_blue"] if ph < 5 else ANIM_COLORS["accent_green"]))
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        lbl_idx = min(ph, len(phase_labels) - 1)
        p.drawText(QRect(0, 0, W, 16), Qt.AlignmentFlag.AlignLeft,
                   f"  {phase_labels[lbl_idx]}")

        # Round numarası (sağ)
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.setFont(QFont("IBM Plex Sans", 10))
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
        custom_colors: list[str] | None = None,
    ) -> None:
        colors = custom_colors if custom_colors is not None else _REG_COLORS
        for i, (lbl, val, col) in enumerate(
            zip(_REG_LABELS, values, colors)
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
    def _arrow_state(ph: int, active_at: int) -> str:
        """Bir okun mevcut faza (ph) göre durumunu döndürür.

        Amaç: paintEvent'in her ok için tek satırda 'pasif/aktif/tamamlandı'
        kararını almasını sağlar; çizim mantığı sadeleşir.

        Parametreler:
          ph        : o anki animasyon fazı (0..5).
          active_at : bu okun aktif olduğu faz numarası.

        Dönüş: "pending" (henüz sırası gelmedi), "active" (tam o faz) veya
        "done" (faz geçti) — _draw_flow_arrow bu değere göre stil seçer.
        """
        if ph < active_at:
            return "pending"
        if ph == active_at:
            return "active"
        return "done"

    def _draw_flow_arrow(
        self, p: QPainter, color_hex: str, state: str, pulse: int,
        pts: list[tuple[int, int]],
        head: str, head_xy: tuple[int, int],
        label: str, label_xy: tuple[int, int],
    ) -> None:
        """Durum-duyarlı (pasif/aktif/tamamlandı) etiketli bir akış oku çizer.

        Amaç: SHA round diyagramında hangi register'ın hangi kutuya katkı
        verdiğini, hangi okun 'şu an' aktif olduğunu görselleştirir
        (Görsel 4 düzeltmesi). Aktif ok kalın + parlak + büyük ok ucu + nabız;
        pasif ok soluk/ince; tamamlanmış ok orta kalınlıkta düz.

        Parametreler:
          color_hex : okun temel rengi (ANIM_COLORS değeri).
          state     : "pending" | "active" | "done" (_arrow_state çıktısı).
          pulse     : aktif ok için nabızlı kalınlık (3 veya 5 px).
          pts       : okun gövde çizgisini oluşturan ardışık (x, y) noktaları.
          head      : ok ucu yönü — "down" (aşağı).
          head_xy   : ok ucunun çizileceği (x, y) konumu.
          label     : ok yanına yazılacak kısa etiket (örn. "A", "T2").
          label_xy  : etiketin sol-üst (x, y) konumu.

        Yan etki: verilen QPainter üzerine çizim yapar (kalem/fırça değişir).
        """
        col = QColor(color_hex)
        if state == "pending":
            col.setAlpha(80)        # henüz akmadı → soluk
            width = 1
            head_sz = 5
        elif state == "active":
            width = pulse           # nabızlı kalın
            head_sz = 9
        else:  # done
            width = 2               # akış tamamlandı → düz orta
            head_sz = 6

        p.setPen(QPen(col, width))
        for i in range(len(pts) - 1):
            p.drawLine(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
        if head == "down":
            self._arrowhead(p, head_xy[0], head_xy[1], size=head_sz)

        # Etiket — yalnızca pasif değilse okunaklı renkte (pasifken soluk).
        p.setFont(QFont("IBM Plex Sans", 7, QFont.Weight.Bold))
        p.setPen(col)
        p.drawText(label_xy[0], label_xy[1], label)

    def _draw_shift_arrows(
        self, p: QPainter, ox: int, src_y: int, dst_y: int,
        box_w: int, gap: int,
    ) -> None:
        """Register kaydırma oklarını (B→C', C→D', F→G', G→H') çizer.

        Amaç: SHA-256 round'unda A' ve E' dışındaki registerların bir sağa
        kaydırıldığını görselleştirir (eğitsel hareketlilik). Oklar ince ve
        soluk (düşük alpha) çizilir ki ana işlem akış oklarının (T1/T2)
        önüne geçmesin; her kaynak register kutusunun altından hedef çıkış
        register kutusunun üstüne ince diagonal çizgi + küçük ok ucu.

        Parametreler:
          ox    : register satırının sol kenarı (x).
          src_y : kaynak (üst) register kutularının ALT kenarı (y).
          dst_y : hedef (alt/çıkış) register kutularının ÜST kenarı (y).
          box_w : kutu genişliği. gap: kutular arası yatay boşluk.

        Yan etki: verilen QPainter üzerine çizim yapar.
        """
        # (kaynak_idx, hedef_idx): B(1)→C'(2), C(2)→D'(3), F(5)→G'(6), G(6)→H'(7)
        shifts = [(1, 2), (2, 3), (5, 6), (6, 7)]
        col = QColor(ANIM_COLORS["text_muted"])
        col.setAlpha(110)  # soluk: ikincil kaydırma, ana okların önüne geçmez
        p.setPen(QPen(col, 1))
        for src, dst in shifts:
            sx = ox + src * (box_w + gap) + box_w // 2
            dx = ox + dst * (box_w + gap) + box_w // 2
            p.drawLine(sx, src_y, dx, dst_y)
            self._arrowhead(p, dx, dst_y, size=4)

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

    @staticmethod
    def _arrowhead_right(p: QPainter, x: int, y: int, size: int = 6) -> None:
        """Sağa bakan ok ucu."""
        pts = QPolygon([
            QPoint(x, y),
            QPoint(x - size * 2, y - size),
            QPoint(x - size * 2, y + size),
        ])
        p.setBrush(QBrush(p.pen().color()))
        p.drawPolygon(pts)


