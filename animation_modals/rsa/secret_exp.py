# animation_modals/rsa/secret_exp.py
"""Adım 5 — Gizli üs d (e·d = 1 + k·ϕ doğrudan arama) widget'ı."""
from __future__ import annotations
from collections.abc import Callable
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint,
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QPolygon,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget,
    QGraphicsOpacityEffect, QSizePolicy,
)
from ..base import (
    CryptoAnimationWindow, ANIM_COLORS, get_animation_tick_ms,
    motion_effects_enabled,
)
from . import helpers as H

# ---------------------------------------------------------------------------
# 6) Adım 5 — Gizli üs d (doğrudan arama: e·d = 1 + k·ϕ)
# ---------------------------------------------------------------------------

class _EEAWidget(QWidget):
    """
    d (gizli üs) hesaplama — DOĞRUDAN ARAMA yöntemi.

    Klasik EEA yerine kullanıcının pedagojik tercih ettiği "k bul, böl"
    yaklaşımı:

        e · d ≡ 1 (mod ϕ)   ⇒   e · d = 1 + k · ϕ
                            ⇒   d = (1 + k · ϕ) / e

    k = 1, 2, 3, ... için bölme tam sayı çıkana kadar denenir. İlk başarılı
    k'da d bulunmuştur. Sınıf adı geriye dönük uyumluluk için "_EEAWidget"
    olarak korunur.

    GEÇİŞ STİLİ — Adım 6 (DER) ile aynı tik tabanlı montaj idiomu:
    ``_tick`` her ``_TICK_MS`` ms'de bir artar; paintEvent açığa çıkan
    öğe sayısını ``_tick``'ten türetir. Öğeler tek tek belirir; en son
    beliren öğe (amaç kutusu / arama satırı) sarı vurgulu kenarlıkla
    işaretlenir → kullanıcı "şu an ne yerleşti?"yi gözle takip eder.
    Amaç, üç formül kutusu olarak soldan sağa ⇒ oklarıyla kurulur; aranan
    bilinmeyen d, son (yeşil) kutuda yalıtılır. Animasyon bittiğinde tüm
    bilgi ekrandadır (bilgi kaybı yok).
    """

    _TICK_MS = 90        # öğe açılış temposu
    _PER_FORM = 4        # bir amaç formül kutusunun açık kalma tik süresi
    _PER_ROW = 3         # bir arama satırının açılma tik süresi

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._compute_schedule()

    # ------------------------------------------------------------------
    # Zamanlama / tik motoru (Adım 6 idiomu)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_iterations() -> list[tuple[int, int, float, int, bool]]:
        """Her k için (k, num, q_float, q_int_or_0, success) listesi.

        Başarılıda q_int gerçek bölüm; başarısızda q_float gösterilir.
        """
        out: list[tuple[int, int, float, int, bool]] = []
        for k in range(1, H._E + 1):
            num = 1 + k * H._PHI
            q_float = num / H._E
            ok = (num % H._E == 0)
            q_int = num // H._E if ok else 0
            out.append((k, num, q_float, q_int, ok))
            if ok:
                break
        return out

    def _compute_schedule(self) -> None:
        """Cari demo (H) değerlerinden açılış tik eşiklerini hesaplar.

        showEvent her açılışta (reseed sonrası) yeniden çağırır; arama satırı
        sayısı demoya göre değiştiği için eşikler ona göre kurulur.
        """
        self._iterations = self._compute_iterations()
        iters = self._iterations
        if len(iters) > 6:
            self._visible: list[tuple[int, int, float, int, bool] | None] = (
                list(iters[:4]) + [None] + [iters[-1]]
            )
        else:
            self._visible = list(iters)
        n_rows = len(self._visible)

        self._t_goal = 1
        goal_end = self._t_goal + 3 * self._PER_FORM        # 3 formül kutusu
        self._t_strategy = goal_end + 1
        self._t_values = self._t_strategy + 2
        self._t_rows = self._t_values + 2
        rows_end = self._t_rows + n_rows * self._PER_ROW
        self._t_result = rows_end + 1
        self._t_verify = self._t_result + 2
        self._t_end = self._t_verify + 2

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._timer.stop()
        self._compute_schedule()
        if motion_effects_enabled():
            self._tick = 0
            self._timer.start(get_animation_tick_ms(self._TICK_MS))
        else:
            # Hareket azaltma açık: animasyon yok, her şey anında görünür.
            self._tick = self._t_end
        self.update()

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self) -> None:
        if self._tick < self._t_end:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def _is_fresh(self, start: int, i: int, per: int) -> bool:
        """i numaralı öğe en son açılan mı? (sarı vurgu için)"""
        return start + i * per <= self._tick < start + (i + 1) * per

    # ------------------------------------------------------------------
    # paintEvent
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()  # NOT: 'H' helpers modül takma adı; gölgelememek için yalnız W

        # Başlık
        p.setFont(QFont("Georgia", 13, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 6, W, 26), Qt.AlignmentFlag.AlignCenter,
                   "Gizli Üs d'nin Bulunması")

        # Amaç — üç formül kutusu soldan sağa montajla kurulur (Adım 6 idiomu)
        self._draw_goal(p, W, 34)

        # Strateji
        if self._tick >= self._t_strategy:
            p.setFont(QFont("Georgia", 9))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(0, 74, W, 16), Qt.AlignmentFlag.AlignCenter,
                       "k = 1, 2, 3, … için böl;  ilk tam sayı çıkan k'da  d  bulunmuştur.")

        # Bilinen değerler
        if self._tick >= self._t_values:
            p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_peach"]))
            p.drawText(QRect(0, 94, W, 20), Qt.AlignmentFlag.AlignCenter,
                       f"ϕ = {H._PHI},   e = {H._E}")

        # İterasyonlar (max 5 başarısız + 1 başarılı satır; arada ⋮)
        visible = self._visible
        row_y = 120
        line_h = 24

        # Satırların en uzunu için adaptif font seç
        sample_lines = []
        for it in visible:
            if it is None:
                continue
            k, num, qf, qi, ok = it
            if ok:
                sample_lines.append(
                    f"k = {k}:  (1 + {k} · {H._PHI}) / {H._E}  =  {num} / {H._E}  =  {qi}   ✓ bulundu"
                )
            else:
                sample_lines.append(
                    f"k = {k}:  (1 + {k} · {H._PHI}) / {H._E}  =  {num} / {H._E}  =  {qf:.3f}…   ✗"
                )
        avail_w = W - 16
        row_pt = 11
        for pt in (11, 10, 9, 8):
            p.setFont(QFont("Courier New", pt))
            longest = max(sample_lines, key=lambda s: p.fontMetrics().horizontalAdvance(s)) if sample_lines else ""
            if not longest or p.fontMetrics().horizontalAdvance(longest) <= avail_w:
                row_pt = pt
                break
        else:
            row_pt = 8

        success_color = QColor(ANIM_COLORS["accent_green"])
        fail_color = QColor(ANIM_COLORS["text_muted"])

        for i, it in enumerate(visible):
            # Satırlar tek tek (yukarıdan aşağı) belirir; gizliyse çiz(me).
            if self._tick < self._t_rows + i * self._PER_ROW:
                break
            y = row_y + i * line_h
            fresh = self._is_fresh(self._t_rows, i, self._PER_ROW)
            ok_row = (it is not None and it[4])

            # En son yerleşen satır sarı, başarılı satır (yerleştikten sonra)
            # yeşil zeminle vurgulanır — "şu an ne yerleşti?" görsel cevabı.
            if fresh:
                self._row_highlight(p, row_y_top=y, W=W, line_h=line_h,
                                    color_hex=ANIM_COLORS["accent_yellow"])
            elif ok_row:
                self._row_highlight(p, row_y_top=y, W=W, line_h=line_h,
                                    color_hex=ANIM_COLORS["accent_green"])

            if it is None:
                p.setFont(QFont("Courier New", row_pt))
                p.setPen(fail_color)
                p.drawText(QRect(0, y, W, line_h),
                           Qt.AlignmentFlag.AlignCenter, "⋮")
                continue
            k, num, qf, qi, ok = it
            color = success_color if ok else fail_color
            font = QFont("Courier New", row_pt,
                         QFont.Weight.Bold if ok else QFont.Weight.Normal)
            p.setFont(font)
            p.setPen(color)
            if ok:
                line = (
                    f"k = {k}:  (1 + {k} · {H._PHI}) / {H._E}  =  {num} / {H._E}"
                    f"  =  {qi}   ✓ bulundu"
                )
            else:
                line = (
                    f"k = {k}:  (1 + {k} · {H._PHI}) / {H._E}  =  {num} / {H._E}"
                    f"  =  {qf:.3f}…   ✗"
                )
            p.drawText(QRect(8, y, W - 16, line_h),
                       Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                       line)

        # Sonuç d — arama bittikten sonra çerçeveli kutuda belirir; "d bulundu"
        # mesajı kullanıcıya net görünsün diye yeşil kenarlıkla vurgulanır.
        result_y = row_y + len(visible) * line_h + 16
        if self._tick >= self._t_result:
            p.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
            d_text = f"d = {H._D}"
            box_w = p.fontMetrics().horizontalAdvance(d_text) + 48
            box_h = 32
            box_x = (W - box_w) // 2
            fill = QColor(success_color)
            fill.setAlpha(45)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(success_color, 2))
            p.drawRoundedRect(box_x, result_y, box_w, box_h, 6, 6)
            p.setPen(success_color)
            p.drawText(QRect(box_x, result_y, box_w, box_h),
                       Qt.AlignmentFlag.AlignCenter, d_text)

        # Doğrulama — kongrüans formunda (e·d ≡ 1 mod ϕ)
        verify_y = result_y + 36
        check = (H._E * H._D) % H._PHI
        symbolic = "Doğrulama:  e · d  ≡  1  (mod ϕ)"
        numeric = f"{H._E} · {H._D}  =  {H._E * H._D}  ≡  {check}  (mod {H._PHI})   ✓"

        ver_pt = 11
        for pt in (11, 10, 9, 8):
            p.setFont(QFont("Courier New", pt, QFont.Weight.Bold))
            longest = max(symbolic, numeric, key=lambda s: p.fontMetrics().horizontalAdvance(s))
            if p.fontMetrics().horizontalAdvance(longest) <= avail_w:
                ver_pt = pt
                break
        else:
            ver_pt = 8

        if self._tick >= self._t_verify:
            p.setFont(QFont("Courier New", ver_pt, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            p.drawText(QRect(8, verify_y, W - 16, 22),
                       Qt.AlignmentFlag.AlignCenter, symbolic)
            p.drawText(QRect(8, verify_y + 22, W - 16, 22),
                       Qt.AlignmentFlag.AlignCenter, numeric)

        p.end()

    # ------------------------------------------------------------------
    # Çizim yardımcıları
    # ------------------------------------------------------------------

    def _draw_goal(self, p: QPainter, W: int, y: int) -> None:
        """Amaç'ı üç formül kutusu olarak soldan sağa ⇒ oklarıyla kurar.

        Kutular tek tek (tik tik) belirir; en son beliren kutu sarı kenarlıkla
        vurgulanır. Üçüncü kutu (d = (1 + k·ϕ)/e) aranan bilinmeyen d'yi yalıtır
        ve yeşil çizilir → "bulmak istediğimiz değer bu". Satır tek parça
        ölçülüp ortalanır; kutu büyürken kayma olmaz.
        """
        prefix = "Amaç:"
        forms = [
            "e · d ≡ 1 (mod ϕ)",
            "e · d = 1 + k · ϕ",
            "d = (1 + k · ϕ) / e",
        ]
        bh = 26              # kutu yüksekliği
        pad = 9              # kutu içi yatay dolgu
        arrow_w = 26         # ⇒ oku için ayrılan genişlik
        gap = 8              # önek ile ilk kutu arası

        # Adaptif font: tüm satır (önek + 3 kutu + 2 ok) içeriğe sığana kadar küçült
        avail = W - 16
        box_font = QFont("Courier New", 11, QFont.Weight.Bold)
        pre_font = QFont("Georgia", 11, QFont.Weight.Bold)
        box_ws: list[int] = []
        total = 0
        for pt in (11, 10, 9, 8):
            box_font = QFont("Courier New", pt, QFont.Weight.Bold)
            pre_font = QFont("Georgia", pt, QFont.Weight.Bold)
            p.setFont(box_font)
            fm = p.fontMetrics()
            box_ws = [fm.horizontalAdvance(t) + 2 * pad for t in forms]
            p.setFont(pre_font)
            pre_w = p.fontMetrics().horizontalAdvance(prefix)
            total = pre_w + gap + sum(box_ws) + 2 * arrow_w
            if total <= avail:
                break

        x = (W - total) / 2.0
        cy = y + bh // 2

        # Önek "Amaç:"
        p.setFont(pre_font)
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        pre_w = p.fontMetrics().horizontalAdvance(prefix)
        p.drawText(QRect(int(x), y, pre_w + 4, bh),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, prefix)
        x += pre_w + gap

        for i, form in enumerate(forms):
            if self._tick < self._t_goal + i * self._PER_FORM:
                # Kutu henüz açılmadı → bu kutu ve sonrasını çizme.
                break
            # Bu kutudan önceki ok (i ≥ 1) — kutu görününce belirir
            if i >= 1:
                p.setFont(QFont("Georgia", 13))
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                p.drawText(QRect(int(x), y, arrow_w, bh),
                           Qt.AlignmentFlag.AlignCenter, "⇒")
                x += arrow_w

            bw = box_ws[i]
            fresh = self._is_fresh(self._t_goal, i, self._PER_FORM)
            is_primary = (i == 0)    # amacın kalbi: kongrüans kutusu kalıcı vurgulu

            # Kenarlık: ilk kutu (kongrüans) KALICI sarı vurgulu kalır; diğer
            # kutular yalnızca açıldıkları an (fresh) sarı, sonra sade kenarlık.
            if is_primary or fresh:
                border = QColor(ANIM_COLORS["accent_yellow"])
                bw_pen = 2
            else:
                border = QColor(ANIM_COLORS["border"])
                bw_pen = 1
            p.setBrush(QBrush(QColor(ANIM_COLORS["bg_card"])))
            p.setPen(QPen(border, bw_pen))
            p.drawRoundedRect(int(x), y, bw, bh, 5, 5)

            # Metin: ilk kutu sarı (vurgulu amaç), diğerleri birincil renk
            p.setFont(box_font)
            p.setPen(QColor(ANIM_COLORS["accent_yellow"] if is_primary
                            else ANIM_COLORS["text_primary"]))
            p.drawText(QRect(int(x), y, bw, bh),
                       Qt.AlignmentFlag.AlignCenter, form)
            x += bw

    @staticmethod
    def _row_highlight(p: QPainter, *, row_y_top: int, W: int, line_h: int,
                       color_hex: str) -> None:
        """Bir arama satırının arkasına soluk zemin + ince kenarlık çizer."""
        fill = QColor(color_hex)
        fill.setAlpha(38)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(color_hex), 1))
        p.drawRoundedRect(6, row_y_top + 1, W - 12, line_h - 2, 5, 5)
