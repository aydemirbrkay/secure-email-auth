# animation_modals/rsa/der_widget.py
"""Adım 6 — DER ve Base64 kodlaması byte akışı widget'ı."""
from __future__ import annotations
import base64
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
from ..base import CryptoAnimationWindow, ANIM_COLORS
from . import helpers as H

# ---------------------------------------------------------------------------
# 7) Adım 6 — DER ve Base64 Kodlaması
# ---------------------------------------------------------------------------

class _DERByteFlowWidget(QWidget):
    """
    Sayılar → byte → DER yapısı → Base64 dönüşümü.
    Son faz: Alice'in gerçek RSA-2048 anahtarlarının oluşumunu gösterir.
    """

    def __init__(
        self, alice_b64: str, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._alice_b64 = alice_b64
        # Bölüm 2 sadeleştirilmiş 3 narratif satırla + Bölüm 3 blok yapısı
        # (SEQUENCE / n-INT / e-INT, 3 başlık + 8 detay satırı) + Aşama A/B +
        # Alice/Bob anahtar kutuları için intrinsic yükseklik 1000 px.
        # Parent QScrollArea bunu kullanarak K⁻ Bob anahtarı dahil tüm
        # içeriği erişilebilir tutar.
        self.setMinimumHeight(1000)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._phase = 0
        self.update()
        self._timer.start(900)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        if self._phase < 4:  # 0..4 (5 phases including Alice's keys)
            self._phase += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()

        # Ortalanmış metni word-wrap ile çizer; uzun satır yatay taşma yerine
        # alt satıra sarar. Mevcut font/kalem kullanılır. y nonlocal olarak
        # gerçek (sarılmış) yüksekliğe göre ilerletilir.
        def _cline(text: str, line_h: int = 18, gap: int = 4) -> None:
            nonlocal y
            flags = (Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                     | Qt.TextFlag.TextWordWrap)
            bound = p.boundingRect(QRect(8, y, W - 16, 4000), flags, text)
            h = max(line_h, bound.height())
            p.drawText(QRect(8, y, W - 16, h), flags, text)
            y += h + gap

        # 1) Sayılar
        y = 6
        p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        p.drawText(QRect(0, y, W, 20), Qt.AlignmentFlag.AlignCenter,
                   "1)  Tam sayılar:")
        y += 22
        p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, y, W, 22), Qt.AlignmentFlag.AlignCenter,
                   f"n = {H._N}    e = {H._E}")

        # 2) Byte gösterimi — n ve e için 'sayı → byte dizisi' dönüşümü iki narratif
        # satırda anlatılır: bölme işlemi + sonuç hex'i aynı satırda; ek detay/not
        # gerektirmez. Önceki versiyondaki üst hex satırı ve "yüksek/düşük bayt"
        # ayrı satırı kaldırıldı — bilgi narratif satırlara gömüldü.
        y += 28
        n_bytes = H._N.to_bytes((H._N.bit_length() + 7) // 8, "big")
        e_bytes = H._E.to_bytes(max(1, (H._E.bit_length() + 7) // 8), "big")
        if self._phase >= 1:
            p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(0, y, W, 20), Qt.AlignmentFlag.AlignCenter,
                       "2)  Big-endian byte dizisi:")
            y += 22

            # n için narratif satır: bölme / tek-bayt / çok-bayt durumlarına göre
            # uygun ifade. 2-baytta "N ÷ 256 = hi kalan lo → HI LO".
            n_hex = " ".join(f"{b:02X}" for b in n_bytes)
            e_hex = " ".join(f"{b:02X}" for b in e_bytes)
            p.setFont(QFont("Courier New", 11))
            p.setPen(QColor(ANIM_COLORS["accent_blue"]))
            if len(n_bytes) == 2:
                hi, lo = n_bytes[0], n_bytes[1]
                line_n = f"n = {H._N}:  {H._N} ÷ 256 = {hi} kalan {lo}   →   {n_hex}"
            elif len(n_bytes) == 1:
                line_n = f"n = {H._N}:  {H._N} < 256, tek bayta sığar   →   {n_hex}"
            else:
                line_n = f"n = {H._N}:  ardışık 256'ya bölme ile {len(n_bytes)} bayt   →   {n_hex}"
            p.drawText(QRect(0, y, W, 20), Qt.AlignmentFlag.AlignCenter, line_n)
            y += 22

            # e için narratif satır — e tipik olarak 7 veya 65537.
            if len(e_bytes) == 1:
                line_e = f"e = {H._E}:  {H._E} < 256, tek bayta sığar   →   {e_hex}"
            else:
                line_e = f"e = {H._E}:  {len(e_bytes)} bayta açılır       →   {e_hex}"
            p.drawText(QRect(0, y, W, 20), Qt.AlignmentFlag.AlignCenter, line_e)
            y += 22

            # Kısa not (gerekirse alt satıra sarar).
            p.setFont(QFont("Georgia", 10))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            _cline("(Sayı 256'ya bölünerek bayt-bayt parçalanır; her bayt = 2 hex hane.)")

        # 3) DER yapısı — kompakt tek-satır + 3 mantıksal blok (SEQUENCE başlığı,
        # n'nin INTEGER kaydı, e'nin INTEGER kaydı). Her satır 'hex değer =
        # Türkçe açıklama' biçiminde. Kullanıcı 0x02'nin INTEGER etiketi olduğu,
        # sonraki baytın uzunluk, devamının değer olduğu yapıyı net görür.
        y += 18
        if self._phase >= 2:
            p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            p.drawText(QRect(0, y, W, 20), Qt.AlignmentFlag.AlignCenter,
                       "3)  ASN.1 / DER paketleme:")
            y += 22
            # SEQUENCE [ 02 len(n) <n_bytes>  02 len(e) <e_bytes> ]
            der_hex = " ".join(f"{b:02X}" for b in H._DER_SEQ)
            seq_content_len = len(H._DER_SEQ) - 2
            len_n = len(H._DER_N) - 2
            len_e = len(H._DER_E) - 2
            n_value_hex = " ".join(f"{b:02X}" for b in H._DER_N[2:])
            e_value_hex = " ".join(f"{b:02X}" for b in H._DER_E[2:])

            # Kompakt tek-satır özet (üst görsel anchor)
            p.setFont(QFont("Courier New", 10))
            p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
            p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                       f"30 {seq_content_len:02X}  ·  02 {len_n:02X} {n_value_hex}"
                       f"  ·  02 {len_e:02X} {e_value_hex}")
            y += 22

            # Yardımcı: 2 sütun satırı (sol: hex, sağ: açıklama). Sayfanın
            # ortasını blok-başlangıcı olarak kullan; sol sütun sağ-hizalı,
            # sağ sütun sol-hizalı.
            mid_x = W // 2 - 60   # bloğun ortası biraz sola kaydırılır
            hex_col_w = 120
            # Açıklama sütunu widget'ın SAĞ kenarına kadar uzanır (eskiden
            # W//2+80 idi → kenarı ~32 px aşıp metni kırpıyordu). Uzun
            # açıklamalar yatay kaydırma yerine alt satıra sarar.
            desc_x = mid_x + 12
            desc_col_w = max(140, W - desc_x - 8)

            def _block_header(title: str, color_key: str) -> None:
                nonlocal y
                font = QFont("Georgia", 10, QFont.Weight.Bold)
                font.setItalic(True)
                p.setFont(font)
                p.setPen(QColor(ANIM_COLORS[color_key]))
                p.drawText(QRect(0, y, W, 18),
                           Qt.AlignmentFlag.AlignCenter, title)
                y += 18

            def _row(hex_txt: str, desc: str) -> None:
                nonlocal y
                desc_txt = "=  " + desc
                wrap_flags = (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                              | Qt.TextFlag.TextWordWrap)
                # Açıklamanın word-wrap ile kaplayacağı yüksekliği ölç → satır
                # yüksekliği buna göre büyür (taşma yerine alt satır).
                p.setFont(QFont("Georgia", 10))
                bound = p.boundingRect(
                    QRect(desc_x, y, desc_col_w, 1000), wrap_flags, desc_txt)
                row_h = max(18, bound.height())
                # Hex (sağ-hizalı, ilk satıra hizalı)
                p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_blue"]))
                p.drawText(QRect(mid_x - hex_col_w, y, hex_col_w, 18),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           hex_txt)
                # Açıklama (word-wrap, sol-üst hizalı)
                p.setFont(QFont("Georgia", 10))
                p.setPen(QColor(ANIM_COLORS["text_secondary"]))
                p.drawText(QRect(desc_x, y, desc_col_w, row_h), wrap_flags, desc_txt)
                y += row_h + 2

            # SEQUENCE başlığı
            _block_header("SEQUENCE başlığı:", "accent_blue")
            _row("0x30", "SEQUENCE etiketi  (sonraki öğeler bir grup olarak gelir)")
            _row(f"0x{seq_content_len:02X}", f"grubun toplam uzunluğu ({seq_content_len} bayt)")
            y += 6

            # n için INTEGER kaydı
            _block_header("n için INTEGER kaydı:", "accent_mauve")
            _row("0x02", "INTEGER etiketi  (ASN.1'de \"tam sayı\" anlamına gelen sabit kod)")
            _row(f"0x{len_n:02X}", f"n'nin uzunluğu = {len_n} bayt")
            _row(n_value_hex, "n'nin baytları (Bölüm 2'den)")
            y += 6

            # e için INTEGER kaydı
            _block_header("e için INTEGER kaydı:", "accent_peach")
            _row("0x02", "INTEGER etiketi (aynı kod)")
            _row(f"0x{len_e:02X}", f"e'nin uzunluğu = {len_e} bayt")
            _row(e_value_hex, "e'nin baytı (Bölüm 2'den)" if len_e == 1
                              else "e'nin baytları (Bölüm 2'den)")
            y += 8

            # Final birleşik DER hex
            p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(0, y, W, 18), Qt.AlignmentFlag.AlignCenter,
                       f"DER ({len(H._DER_SEQ)} bayt): {der_hex}")

        # 4) Base64 — adım adım anlaşılır anlatım:
        #    Aşama A: DEMO DER byte'ları (üstteki bölüm 3'le aynı) gruplandırılır
        #             ve hangi b64 karakterine karşılık geldiği gösterilir.
        #    Aşama B: Aynı yöntem Alice'in GERÇEK 2048-bit anahtarının ilk 3 byte'ına
        #             uygulanır; 24 bit → 6-bit gruplar → indeks → harf eşlemesi
        #             tek tek izlenir (önceki ve sonraki örnek aynı algoritma).
        #
        # Önceki versiyon karışıktı: bölüm 4 doğrudan Alice byte'larını gösteriyor,
        # bölüm 3 ise DEMO DER byte'larını gösteriyordu (5C ↔ 30 uyumsuzluğu). Şimdi
        # bölüm 4 yukarıdaki DEMO bytes'ı izliyor, sonrasında ayrı bir "Aşama B"
        # ile Alice anahtarına geçiş kuruluyor.
        y += 22
        if self._phase >= 3:
            p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            _cline("4)  Base64 dönüşümü  (her 3 bayt → 4 karakter)")

            # --- AŞAMA A: DEMO DER bytes → DEMO Base64 ---
            # Bölüm 3'te gösterilen aynı 9 byte (DEMO DER) Base64'e çevrilir.
            # Böylece bölüm 3 → bölüm 4 byte zinciri kopmaz.
            p.setFont(QFont("Georgia", 10))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            _cline("Aşama A — yukarıdaki DEMO DER (9 byte) gruplandırılır:")

            der = H._DER_SEQ
            b64 = H._B64_DEMO
            n_groups = (len(der) + 2) // 3
            group_w = 110
            total_groups_w = n_groups * group_w + (n_groups - 1) * 12
            ox = max(8, (W - total_groups_w) // 2)

            for gi in range(n_groups):
                gx = ox + gi * (group_w + 12)
                byte_chunk = der[gi * 3 : gi * 3 + 3]
                b64_chunk = b64[gi * 4 : gi * 4 + 4]

                # Üst: 3 byte'lık grup
                p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_blue"]))
                byte_hex = " ".join(f"{b:02X}" for b in byte_chunk)
                p.drawText(QRect(gx, y, group_w, 18),
                           Qt.AlignmentFlag.AlignCenter, byte_hex)

                # Ok
                p.setFont(QFont("Georgia", 11))
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                p.drawText(QRect(gx, y + 16, group_w, 14),
                           Qt.AlignmentFlag.AlignCenter, "↓")

                # Alt: 4 base64 karakteri (13pt → grup okunaklığı belirgin)
                p.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_green"]))
                p.drawText(QRect(gx, y + 30, group_w, 20),
                           Qt.AlignmentFlag.AlignCenter, b64_chunk)

            y += 54
            p.setFont(QFont("Georgia", 10))
            p.setPen(QColor(ANIM_COLORS["text_secondary"]))
            _cline(f"= Demo Base64 ({len(H._B64_DEMO)} karakter, temsilî · "
                   f"gerçek anahtar değil): {H._B64_DEMO}", gap=8)

            # --- AŞAMA B: Alice'in gerçek anahtarına aynı yöntemin uygulanışı ---
            # Bölüm 3'teki DEMO yapı sadece eğitim örneği; Alice'in 2048-bit
            # anahtarı için DER ~270 byte ve b64 ~360 karakter. Burada sadece
            # İLK 3 BYTE → İLK 4 KARAKTER dönüşümünü adım adım gösteriyoruz.
            # Bu sayede kullanıcı "aynı algoritma gerçek anahtara şöyle uygulanır"
            # bağlantısını net görür.
            p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1, Qt.PenStyle.DashLine))
            p.drawLine(40, y, W - 40, y)
            y += 8

            p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            _cline("Aşama B — Aynı yöntem Alice'in gerçek anahtarına uygulanırsa:")

            alice_first4 = self._alice_b64[:4]   # ör. "MIIB"
            try:
                alice_first3 = base64.b64decode(alice_first4 + "==")[:3]
            except Exception:
                alice_first3 = b""

            if len(alice_first3) == 3:
                bits = "".join(f"{b:08b}" for b in alice_first3)     # 24 bit
                groups = [bits[i:i+6] for i in range(0, 24, 6)]      # 4 × 6-bit
                indices = [int(g, 2) for g in groups]

                # Adım B1: Alice anahtarının ilk 3 byte'ı
                p.setFont(QFont("Georgia", 10))
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                _cline("B1) Alice 2048-bit anahtarının ilk 3 byte'ı:", line_h=16, gap=2)
                hex_str = " ".join(f"{b:02X}" for b in alice_first3)
                p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_blue"]))
                _cline(hex_str, gap=6)

                # Adım B2: 24-bit binary açılım
                p.setFont(QFont("Georgia", 10))
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                _cline("B2) Hex → binary  (3 × 8 = 24 bit):", line_h=16, gap=2)
                bin_str = " ".join(f"{b:08b}" for b in alice_first3)
                p.setFont(QFont("Courier New", 11))
                p.setPen(QColor(ANIM_COLORS["text_secondary"]))
                _cline(bin_str, gap=6)

                # Adım B3: 24 bit → 4 × 6-bit gruplar
                p.setFont(QFont("Georgia", 10))
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                _cline("B3) 24 bit → 4 adet 6-bit grup:", line_h=16, gap=2)
                grouped_str = " | ".join(groups)
                p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
                _cline(grouped_str, gap=6)

                # Adım B4: indeks → karakter eşleme
                p.setFont(QFont("Georgia", 10))
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                _cline("B4) Her 6-bit grubun indeksi → Base64 alfabesi (A-Z a-z 0-9 + /):",
                       line_h=16, gap=2)
                mapping = "   ".join(
                    f"{g}={idx}→{ch}"
                    for g, idx, ch in zip(groups, indices, alice_first4)
                )
                p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_green"]))
                _cline(mapping, gap=6)

                # Sonuç: Alice b64'ün ilk 4 karakteri
                p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
                p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
                _cline(f"= Alice b64'ünün ilk 4 karakteri: {alice_first4}", gap=6)

        # 5) ALICE'İN GERÇEK ANAHTARLARI — son faz
        y += 26
        if self._phase >= 4:
            # Ayraç + başlık
            p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1, Qt.PenStyle.DashLine))
            p.drawLine(40, y, W - 40, y)
            y += 6

            p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            _cline("↓  Aynı yöntemle Alice'in gerçek RSA-2048 anahtarları:")

            # Açık anahtar (K⁺)
            self._draw_real_key_box(
                p, x=12, y=y, w=W - 24, h=24,
                icon="K⁺", icon_color=ANIM_COLORS["accent_blue"],
                label="Alice Açık Anahtarı:",
                value=self._alice_b64,
            )
            y += 28

            # Gizli anahtar (K⁻) — içerik gösterilmez (güvenlik)
            self._draw_real_key_box(
                p, x=12, y=y, w=W - 24, h=24,
                icon="K⁻", icon_color=ANIM_COLORS["accent_green"],
                label="Alice Gizli Anahtarı:",
                value="(n, d) — yalnızca Alice'te tutulur",
                value_color=ANIM_COLORS["text_muted"],
                italic_value=True,
            )
        p.end()

    @staticmethod
    def _draw_real_key_box(
        p: QPainter, x: int, y: int, w: int, h: int,
        icon: str, icon_color: str,
        label: str, value: str,
        value_color: str | None = None,
        italic_value: bool = False,
    ) -> None:
        # Çerçeve
        fill = QColor(ANIM_COLORS["bg_input"])
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor(icon_color), 1))
        p.drawRoundedRect(x, y, w, h, 4, 4)

        # K⁺ / K⁻ simge alanı (sol)
        icon_w = 36
        p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        p.setPen(QColor(icon_color))
        p.drawText(QRect(x + 4, y, icon_w, h),
                   Qt.AlignmentFlag.AlignCenter, icon)

        # Etiket — "Alice Açık Anahtarı:" 19 karakter, eski 110 px dar kalıyordu.
        # 150 px ve 10pt font ile kırpılmadan sığar.
        p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_secondary"]))
        label_w = 150
        p.drawText(QRect(x + icon_w + 4, y, label_w, h),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   label)

        # Değer — Courier 8pt çok küçüktü, 9pt'a büyütüldü
        font = QFont("Courier New", 9)
        if italic_value:
            font.setItalic(True)
        p.setFont(font)
        p.setPen(QColor(value_color or ANIM_COLORS["text_primary"]))
        value_x = x + icon_w + 4 + label_w + 4
        value_w = w - (value_x - x) - 6
        # Tek satıra sığacak şekilde uzun b64'ü kırp (9pt için karakter ~7px)
        max_chars = max(20, value_w // 7)
        display = value if len(value) <= max_chars else value[:max_chars - 1] + "…"
        p.drawText(QRect(value_x, y, value_w, h),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   display)



