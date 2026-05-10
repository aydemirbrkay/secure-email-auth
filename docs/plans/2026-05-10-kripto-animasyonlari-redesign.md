# Kripto Animasyonları Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** EEA, RSA ve SHA-256 animasyonlarındaki dört "fazla metin / nereden geldi belli değil" noktasını tezdeki Tablo `tab:RSAExample` ve Algoritma `algo:EEA` ile birebir hizalı, animasyon ağırlıklı bileşenlerle değiştir.

**Architecture:** İki dosyaya 5 bileşenlik dokunma: `rsa_animation.py` (sabit değerler + EEA yeniden yazımı + yeni Adım 8) ve `sha256_animation.py` (W-expansion ve match sayfalarının widget tabanlı yeniden yazımı). Tüm yeni widget'lar mevcut `QPainter` + `QTimer`-faz makinesi kalıbını izler; saf Python referans modülleri (`sha256_pure.py`, `_eea_steps`) değişmez.

**Tech Stack:** Python 3.11, PyQt6, mevcut `CryptoAnimationWindow` taban sınıfı, `unittest` (root dizinde `test_*.py`).

**İlgili tasarım dokümanı:** [docs/specs/2026-05-10-kripto-animasyonlari-redesign-design.md](../specs/2026-05-10-kripto-animasyonlari-redesign-design.md)

---

## File Structure

| Dosya | Değişiklik | Sorumluluk |
| --- | --- | --- |
| `animation_modals/rsa_animation.py` | Modify (önemli) | Sabit tez değerleri, `_EEAWidget` yeniden yazımı, `_RSAEncryptDecryptWidget` yeni sınıf, `RSAAnimationWindow` 7→8 step |
| `animation_modals/sha256_animation.py` | Modify (önemli) | `_WExpansionWidget` ve `_MatchAssemblyWidget` yeni sınıflar; `_make_wexpand_page` / `_make_match_page` / `_show_match_result` indirgemesi |
| `animation_modals/sha256_pure.py` | No-change | `w_expansion`, `pre_final_h`, `final_working`, `final_h_parts`, `final_hash` zaten doğru dönüyor |
| `test_rsa_animation.py` | Create | Sabit değer invariantları + 8 adım invariantı + import-only smoke testler |
| `test_sha256_pure.py` | No-change | Mevcut testler korunur |

UI widget'ları için `QApplication` başlatmadan **import-only** smoke testleri yazıyoruz; görsel doğrulama manuel.

---

## Task 1: RSA — Tez Değerlerini Sabitle, Random Seed'i Kaldır

**Files:**
- Modify: `animation_modals/rsa_animation.py:87-139` (sabitler + `_reseed_demo`)
- Modify: `animation_modals/rsa_animation.py:1404-1406` (`_reseed_demo()` çağrısı)
- Create: `test_rsa_animation.py`

### - [ ] Step 1.1: `test_rsa_animation.py` ile failing test yaz

Yeni dosya `c:\Users\sasss\Desktop\BİTİRME PROJESİ\test_rsa_animation.py`:

```python
# test_rsa_animation.py
"""
RSA animasyon modülünün tezdeki değerlerle hizalandığını doğrular.
PyQt UI bileşenleri çalışma zamanında test edilemez (QApplication gerekir);
bu yüzden burada modül seviyesindeki invariantları kontrol ederiz.
"""
import unittest


class TestRSAAnimationConstants(unittest.TestCase):

    def test_thesis_values_are_fixed(self):
        """Tezdeki Tablo tab:RSAExample değerleriyle birebir uymalı."""
        from animation_modals import rsa_animation as rsa
        self.assertEqual(rsa._P, 61)
        self.assertEqual(rsa._Q, 53)
        self.assertEqual(rsa._N, 3233)
        self.assertEqual(rsa._PHI, 3120)
        self.assertEqual(rsa._E, 17)
        self.assertEqual(rsa._D, 2753)

    def test_rsa_invariant_holds(self):
        """e · d ≡ 1 (mod φ) RSA tanımının temel invariantı."""
        from animation_modals import rsa_animation as rsa
        self.assertEqual((rsa._E * rsa._D) % rsa._PHI, 1)

    def test_random_seed_function_removed(self):
        """_reseed_demo modülde olmamalı — sabit tez değerleri var."""
        from animation_modals import rsa_animation as rsa
        self.assertFalse(hasattr(rsa, "_reseed_demo"),
                         "_reseed_demo kaldırılmış olmalı")
        self.assertFalse(hasattr(rsa, "_PRIME_POOL"),
                         "_PRIME_POOL kaldırılmış olmalı")


if __name__ == "__main__":
    unittest.main()
```

### - [ ] Step 1.2: Test'i çalıştır, başarısız olduğunu doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_rsa_animation -v
```

Beklenen: `test_random_seed_function_removed` FAIL (mevcut `_reseed_demo` ve `_PRIME_POOL` hâlâ var). Diğer iki test ya geçer ya değer farklılığında fail eder.

### - [ ] Step 1.3: `rsa_animation.py:87-139` aralığını yeniden yaz

`animation_modals/rsa_animation.py` içindeki **87-139 satır** aralığı (bu blok `_PRIME_POOL`, modül seviyesi sabitler, ve `_reseed_demo()` fonksiyonunu içerir) **şu blokla** değiştirilir:

```python
# ---------------------------------------------------------------------------
# Tez değerleri — tab:RSAExample ile birebir uyumlu (chapter1.tex)
# Tüm widget'lar bu sabitleri __init__'lerinde okur.
# ---------------------------------------------------------------------------

_P:   int = 61
_Q:   int = 53
_N:   int = _P * _Q          # 3233
_PHI: int = (_P - 1) * (_Q - 1)  # 3120
_E:   int = 17
_D:   int = pow(_E, -1, _PHI)    # 2753

assert (_E * _D) % _PHI == 1, "RSA invariant ihlal edildi: e · d ≢ 1 (mod φ)"

_DER_N:   bytes = _der_int(_N)
_DER_E:   bytes = _der_int(_E)
_DER_SEQ: bytes = bytes([0x30, len(_DER_N) + len(_DER_E)]) + _DER_N + _DER_E
_B64_DEMO: str  = base64.b64encode(_DER_SEQ).decode()
```

### - [ ] Step 1.4: `_reseed_demo()` çağrısını `__init__`'ten kaldır

`animation_modals/rsa_animation.py:1404-1406` aralığı şu anda:

```python
        # Her açılışta rastgele küçük asal çifti seç (11..97 havuzundan)
        # Tüm widget'lar bu cari değerleri __init__'lerinde okuyacak
        _reseed_demo()
```

Üç satır da silinir (yorum dahil). `__init__`'in başı doğrudan `self._alice_b64 = alice_pub_b64` olur.

### - [ ] Step 1.5: `import random` artırımı temizle

Dosyanın başında `import random` satırı (`rsa_animation.py:19`) artık kullanılmadığı için silinir.

### - [ ] Step 1.6: Test'i çalıştır, geçtiğini doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_rsa_animation -v
```

Beklenen: 3 test PASS.

### - [ ] Step 1.7: Mevcut testlerin bozulmadığını doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover -v
```

Beklenen: tüm testler PASS.

### - [ ] Step 1.8: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/rsa_animation.py test_rsa_animation.py && git commit -m "kripto: RSA demo değerleri tezdeki sabitlere kilitlendi (61, 53)"
```

---

## Task 2: EEA Canlı Hesaplama Şeridi

**Files:**
- Modify: `animation_modals/rsa_animation.py:838-1010` (`_EEAWidget` sınıfı tamamen yeniden yazılır)

### - [ ] Step 2.1: Failing test ekle (`test_rsa_animation.py`'a)

Dosyanın `TestRSAAnimationConstants` sınıfına aşağıdaki test eklenir:

```python
    def test_eea_steps_for_thesis_values(self):
        """φ=3120, e=17 için EEA çıktısının ilk satırları sabittir.

        Tezdeki Algoritma algo:EEA ile q, r, s, t kolonlarının
        deterministik olduğunu doğrular.
        """
        from animation_modals.rsa_animation import _eea_steps, _PHI, _E
        rows = _eea_steps(_PHI, _E)
        # İlk iki satır seed: (0, 0, 3120, 1, 0) ve (1, 0, 17, 0, 1)
        self.assertEqual(rows[0], (0, 0, 3120, 1, 0))
        self.assertEqual(rows[1], (1, 0, 17, 0, 1))
        # i=2 için: q=⌊3120/17⌋=183, r=3120-183·17=9, s=1, t=-183
        self.assertEqual(rows[2], (2, 183, 9, 1, -183))
        # GCD=1 satırı → t değeri pozitif moda alınınca _D olmalı
        gcd_row = next(row for row in rows if row[2] == 1)
        t = gcd_row[4]
        self.assertEqual(t % _PHI, _D)  # _D = 2753
```

### - [ ] Step 2.2: Test'i çalıştır, geçtiğini doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_rsa_animation.TestRSAAnimationConstants.test_eea_steps_for_thesis_values -v
```

Beklenen: PASS (Task 1'de değerler zaten sabitlendi). Bu test, ilerideki UI değişiklikleri sırasında `_eea_steps`'in çıktısının değişmediğine dair bir koruma.

### - [ ] Step 2.3: `_EEAWidget`'ı yeniden yaz — faz makinesi tabanlı

`animation_modals/rsa_animation.py:838-1010` aralığındaki **mevcut `_EEAWidget` sınıfı tamamen** şu yeni sınıfla değiştirilir:

```python
class _EEAWidget(QWidget):
    """
    Genişletilmiş Öklid Algoritması tablosu + canlı hesaplama şeridi.

    Faz makinesi (her satır için):
      STRIP_SHOW (1100 ms) — sırada yerleştirilecek satırın altında bir
        hesaplama şeridi belirir; q, r, s, t formülleri sayısal değerleriyle
        görünür. Önceki satırın r₀, r₁, s₀, s₁, t₀, t₁ hücreleri vurgulanır.
      STRIP_FADE (400 ms) — şerit söner, satır tabloya yerleşir.
      Sonraki satıra geç.

    Tüm satırlar yerleşince GCD=1 vurgusu, "(durma satırı)", d hesabı,
    doğrulama satırı sırayla görünür (mevcut hâliyle).
    """

    _COLS = ["i", "bölüm", "kalan", "s", "t"]
    _COL_WIDTHS = [32, 60, 76, 76, 76]

    # Faz tick aralığı (ms) — base interval, fazlar bunun katlarıyla biter
    _TICK_MS = 80
    _STRIP_SHOW_TICKS = 14   # 14 × 80 = 1120 ms
    _STRIP_FADE_TICKS = 5    # 5 × 80 = 400 ms

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._rows = _eea_steps(_PHI, _E)

        # Faz makinesi durumu
        self._placed_count = 0   # tabloya yerleşmiş satır sayısı
        self._phase = "DONE"     # "STRIP_SHOW" | "STRIP_FADE" | "BETWEEN" | "DONE"
        self._phase_tick = 0
        self._final_reveal = 0   # 0=hiç, 1=d kutusu, 2=doğrulama satırı

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        # Sıfırla ve baştan başlat
        # İlk iki satır seed (i=0, i=1) — bunlar şeritle gösterilmez
        # Direkt yerleşir; faz makinesi i=2'den başlar.
        self._placed_count = 2
        self._phase = "STRIP_SHOW"
        self._phase_tick = 0
        self._final_reveal = 0
        self.update()
        self._timer.start(self._TICK_MS)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        self._phase_tick += 1

        if self._phase == "STRIP_SHOW" and self._phase_tick >= self._STRIP_SHOW_TICKS:
            self._phase = "STRIP_FADE"
            self._phase_tick = 0
        elif self._phase == "STRIP_FADE" and self._phase_tick >= self._STRIP_FADE_TICKS:
            # Şerit söndü — satır artık yerleşmiş kabul edilir
            self._placed_count += 1
            self._phase_tick = 0
            if self._placed_count >= len(self._rows):
                self._phase = "DONE"
                # Final ortaya çıkma: d kutusu, sonra doğrulama
                self._final_reveal = 0
                self._final_timer = QTimer(self)
                self._final_timer.timeout.connect(self._final_tick)
                self._final_timer.start(420)
                self._timer.stop()
                self.update()
                return
            self._phase = "STRIP_SHOW"

        self.update()

    def _final_tick(self) -> None:
        self._final_reveal += 1
        if self._final_reveal >= 2:
            self._final_timer.stop()
        self.update()

    # --- Çizim ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Başlık
        p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 4, W, 22), Qt.AlignmentFlag.AlignCenter,
                   "Genişletilmiş Öklid Algoritması")
        p.setFont(QFont("Georgia", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 26, W, 18), Qt.AlignmentFlag.AlignCenter,
                   f"Amaç: e·d ≡ 1 (mod φ)   ·   φ = {_PHI},  e = {_E}")

        # Tablo merkezleme
        total_col_w = sum(self._COL_WIDTHS)
        annot_w = 130
        ox = (W - total_col_w - annot_w) // 2
        header_y = 50
        row_h = 20

        gcd_row_idx = len(self._rows) - 2

        # Başlık satırı
        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_blue"]))
        x = ox
        for col, w in zip(self._COLS, self._COL_WIDTHS):
            p.drawText(QRect(x, header_y, w, row_h),
                       Qt.AlignmentFlag.AlignCenter, col)
            x += w
        p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))
        p.drawLine(ox, header_y + row_h, ox + total_col_w, header_y + row_h)

        # Yerleşmiş satırlar
        # Aktif olan satır indeksi (şerit gösterilen) self._placed_count
        active_row_idx = (
            self._placed_count
            if self._phase in ("STRIP_SHOW", "STRIP_FADE")
            else -1
        )
        prev_row_idx = active_row_idx - 1 if active_row_idx > 1 else -1

        # Yerleşmiş satırları çiz (önceki satırın hücreleri gerekirse vurgulanır)
        for ri in range(self._placed_count):
            self._draw_row(
                p, ri, ox, header_y, row_h, total_col_w, annot_w, gcd_row_idx,
                highlight_operands=(ri == prev_row_idx and self._phase == "STRIP_SHOW"),
            )

        # Aktif şerit (varsa)
        if self._phase in ("STRIP_SHOW", "STRIP_FADE"):
            strip_y = header_y + (self._placed_count + 1) * row_h + 8
            opacity = 1.0
            if self._phase == "STRIP_FADE":
                opacity = 1.0 - (self._phase_tick / self._STRIP_FADE_TICKS)
            self._draw_strip(
                p, ox, strip_y, total_col_w + annot_w, active_row_idx, opacity,
            )

        # d hesaplama bloğu — tüm satırlar yerleşince
        last_t = self._rows[gcd_row_idx][4]
        if self._phase == "DONE" and self._final_reveal >= 1:
            calc_y = header_y + (len(self._rows) + 1) * row_h + 12
            p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_green"]))
            p.drawText(
                QRect(0, calc_y, W, 22),
                Qt.AlignmentFlag.AlignCenter,
                f"d  =  t  mod  φ  =  {last_t}  mod  {_PHI}  =  {_D}",
            )
            if last_t < 0:
                p.setFont(QFont("Georgia", 8))
                p.setPen(QColor(ANIM_COLORS["text_muted"]))
                p.drawText(
                    QRect(0, calc_y + 22, W, 16),
                    Qt.AlignmentFlag.AlignCenter,
                    "(negatif → +φ ekle)",
                )

        # Doğrulama
        if self._phase == "DONE" and self._final_reveal >= 2:
            verify_y = header_y + (len(self._rows) + 1) * row_h + 50
            p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
            check = (_E * _D) % _PHI
            p.drawText(
                QRect(0, verify_y, W, 20),
                Qt.AlignmentFlag.AlignCenter,
                f"Doğrulama:  e × d  mod  φ  =  {_E} × {_D}  mod  {_PHI}  =  {check}   ✓",
            )
        p.end()

    def _draw_row(
        self, p: QPainter, ri: int, ox: int, header_y: int, row_h: int,
        total_col_w: int, annot_w: int, gcd_row_idx: int,
        highlight_operands: bool,
    ) -> None:
        i, q, r, s, t = self._rows[ri]
        y = header_y + (ri + 1) * row_h + 2

        is_gcd_row = (ri == gcd_row_idx) and self._placed_count > gcd_row_idx
        is_terminator = ri == len(self._rows) - 1 and self._placed_count == len(self._rows)

        # Vurgulama: GCD=1 satırı yeşil arka plan
        if is_gcd_row:
            fill = QColor(ANIM_COLORS["accent_green"])
            fill.setAlpha(50)
            p.setBrush(QBrush(fill))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(ox, y - 1, total_col_w, row_h)

        # "Önceki satır operand vurgusu" — şerit aktifken bu satır vurgulanırsa
        if highlight_operands:
            fill = QColor(ANIM_COLORS["accent_blue"])
            fill.setAlpha(35)
            p.setBrush(QBrush(fill))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(ox, y - 1, total_col_w, row_h)

        # Hücre değerleri
        x = ox
        values = [str(i), str(q) if ri >= 2 else "—", str(r), str(s), str(t)]
        if is_gcd_row:
            colors = [
                ANIM_COLORS["text_primary"],
                ANIM_COLORS["text_primary"],
                ANIM_COLORS["accent_yellow"],
                ANIM_COLORS["text_primary"],
                ANIM_COLORS["accent_green"],
            ]
            font_weight = QFont.Weight.Bold
        elif is_terminator:
            muted = ANIM_COLORS["text_muted"]
            colors = [muted, muted, muted, muted, muted]
            font_weight = QFont.Weight.Normal
        else:
            colors = [
                ANIM_COLORS["text_muted"],
                ANIM_COLORS["text_secondary"],
                ANIM_COLORS["text_primary"],
                ANIM_COLORS["text_secondary"],
                ANIM_COLORS["accent_peach"],
            ]
            font_weight = QFont.Weight.Normal

        font = QFont("Courier New", 10, font_weight)
        p.setFont(font)
        for val, w, col in zip(values, self._COL_WIDTHS, colors):
            p.setPen(QColor(col))
            p.drawText(QRect(x, y, w, row_h - 2),
                       Qt.AlignmentFlag.AlignCenter, val)
            x += w

        # Sağ taraf açıklamalar
        annot_x = ox + total_col_w + 8
        if is_gcd_row:
            p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["accent_green"]))
            p.drawText(QRect(annot_x, y, annot_w, row_h - 2),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "← GCD = 1, t'yi al")
        elif is_terminator:
            p.setFont(QFont("Georgia", 9))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(annot_x, y, annot_w, row_h - 2),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "(durma satırı)")

    def _draw_strip(
        self, p: QPainter, ox: int, y: int, w: int,
        active_row_idx: int, opacity: float,
    ) -> None:
        """Aktif satır için q, r, s, t formüllerini sayısal değerleriyle çiz."""
        if active_row_idx < 2 or active_row_idx >= len(self._rows):
            return
        # Önceki satır indeks: active - 1 → r₁ ve s₁,t₁ (current); active - 2 → r₀, s₀, t₀
        i, q, r, s, t = self._rows[active_row_idx]
        _, _, r1, s1, t1 = self._rows[active_row_idx - 1]
        _, _, r0, s0, t0 = self._rows[active_row_idx - 2]

        # Şerit kutusu
        strip_h = 90
        bg = QColor(ANIM_COLORS["bg_input"])
        bg.setAlphaF(opacity * 0.9)
        border = QColor(ANIM_COLORS["accent_blue"])
        border.setAlphaF(opacity)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, 1))
        p.drawRoundedRect(ox, y, w, strip_h, 6, 6)

        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)

        p.setFont(QFont("Courier New", 10))
        p.setPen(text_col)
        lines = [
            f"q = ⌊{r0} / {r1}⌋ = {q}",
            f"r = {r0} − {q}·{r1} = {r}",
            f"s = {s0} − {q}·{s1} = {s}",
            f"t = {t0} − {q}·{t1} = {t}",
        ]
        for li, line in enumerate(lines):
            p.drawText(QRect(ox + 12, y + 6 + li * 20, w - 24, 18),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       line)
```

### - [ ] Step 2.4: Smoke testlerle modülün hâlâ import edildiğini doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -c "from animation_modals.rsa_animation import _EEAWidget, _eea_steps, _PHI, _E, _D; print('OK')"
```

Beklenen: `OK`. Eğer ImportError çıkarsa, syntax hatasıdır — düzeltilir.

### - [ ] Step 2.5: Tüm testleri çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover -v
```

Beklenen: tüm testler PASS.

### - [ ] Step 2.6: Manuel görsel doğrulama

1. `python main_gui.py` ile uygulamayı aç (Python 3.11 gerekir).
2. RSA animasyonunu başlat (Alice/Bob panelindeki RSA butonu).
3. ▶ ile Adım 5'e (EEA) gel.
4. **Şu davranışı doğrula:**
   - İlk iki satır (i=0, i=1) hızla yerleşir.
   - i=2 satırı için altında bir hesaplama şeridi belirir, içinde 4 satırlık formül görünür: `q = ⌊3120/17⌋ = 183` …
   - Şerit yaklaşık 1.1 sn boyunca durur, ardından söner.
   - i=2 satırı tabloya yerleşir.
   - Sonraki satırlar için aynı döngü tekrarlanır.
   - Tüm satırlar yerleşince `d = -367 mod 3120 = 2753` ve doğrulama satırı sırayla belirir.

### - [ ] Step 2.7: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/rsa_animation.py test_rsa_animation.py && git commit -m "kripto: EEA tablosuna canlı hesaplama şeridi eklendi"
```

---

## Task 3: RSA Adım 8 — Şifreleme/Deşifreleme Turu

**Files:**
- Modify: `animation_modals/rsa_animation.py` — yeni `_RSAEncryptDecryptWidget` sınıfı eklenir
- Modify: `animation_modals/rsa_animation.py:1372-1395` — `_TITLES` ve `_CAPTIONS` 7→8 entry
- Modify: `animation_modals/rsa_animation.py:1458-1466` — `_page_widgets` listesine yeni widget
- Modify: `animation_modals/rsa_animation.py:1494-1507` — `_render_step` ve `_show_match_result` semantiği

### - [ ] Step 3.1: Failing testler ekle

`test_rsa_animation.py`'a `TestRSAAnimationConstants` sınıfının altına yeni test sınıfı eklenir:

```python
class TestRSAAnimationStructure(unittest.TestCase):
    """RSAAnimationWindow'un 8 adımlı yapısını doğrular (UI başlatmadan)."""

    def test_titles_have_eight_entries(self):
        from animation_modals.rsa_animation import RSAAnimationWindow
        self.assertEqual(len(RSAAnimationWindow._TITLES), 8)

    def test_captions_have_eight_entries(self):
        from animation_modals.rsa_animation import RSAAnimationWindow
        self.assertEqual(len(RSAAnimationWindow._CAPTIONS), 8)

    def test_titles_use_eight_format(self):
        """Her adım başlığı 'Adım N / 8' formatında olmalı."""
        from animation_modals.rsa_animation import RSAAnimationWindow
        for i, title in enumerate(RSAAnimationWindow._TITLES):
            self.assertIn(f"Adım {i+1} / 8", title,
                          f"index {i}: '{title}'")

    def test_eighth_title_is_encryption_tour(self):
        from animation_modals.rsa_animation import RSAAnimationWindow
        self.assertIn("Şifreleme", RSAAnimationWindow._TITLES[7])

    def test_encrypt_decrypt_widget_exists(self):
        from animation_modals import rsa_animation as rsa
        self.assertTrue(hasattr(rsa, "_RSAEncryptDecryptWidget"))
```

### - [ ] Step 3.2: Test'i çalıştır, başarısız olduğunu doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_rsa_animation.TestRSAAnimationStructure -v
```

Beklenen: 5 test FAIL.

### - [ ] Step 3.3: `_RSAEncryptDecryptWidget` sınıfını ekle

`animation_modals/rsa_animation.py` dosyasında `_KeyMatchWidget` sınıfının (`rsa_animation.py:1244` civarı) **hemen ardından**, `RSAAnimationWindow` sınıfının başlamadan önce, şu yeni sınıf eklenir:

```python
# ---------------------------------------------------------------------------
# 8) Adım 8 — Şifreleme/Deşifreleme Turu (Eq:RSAExample)
# ---------------------------------------------------------------------------

class _RSAEncryptDecryptWidget(QWidget):
    """
    Tezdeki Eq:RSAExample animasyonu:
      m = 65   →   c = m^e mod n = 65^17 mod 3233 = 2790
      c = 2790 →   m' = c^d mod n = 2790^2753 mod 3233 = 65   ✓

    Faz makinesi (toplam ~3.6 sn):
      PLAINTEXT_IN  (400 ms): m kutusu belirir
      ENC_FORMULA   (800 ms): şifreleme formülü satır satır yazılır,
                              açık anahtar kartı parlar
      CIPHER_OUT    (400 ms): c kutusu belirir
      CIPHER_IN     (200 ms): c alt yola düşer
      DEC_FORMULA   (800 ms): deşifreleme formülü, gizli anahtar kartı parlar
      PLAINTEXT_OUT (400 ms): m' kutusu belirir
      MATCH         (600 ms): m' = m ✓ yeşil pulse
    """

    _M = 65
    _C = pow(_M, _E, _N)             # 2790
    _M_PRIME = pow(_C, _D, _N)       # 65

    _TICK_MS = 50

    # Faz tick eşikleri (kümülatif)
    _T_PLAIN_IN_END  = 8    # 400 ms
    _T_ENC_END       = 24   # +800 ms = 1200
    _T_CIPHER_END    = 32   # +400 ms = 1600
    _T_CIPHER_IN_END = 36   # +200 ms = 1800
    _T_DEC_END       = 52   # +800 ms = 2600
    _T_PLAIN_OUT_END = 60   # +400 ms = 3000
    _T_MATCH_END     = 72   # +600 ms = 3600

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._tick = 0
        self.update()
        self._timer.start(self._TICK_MS)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self) -> None:
        if self._tick < self._T_MATCH_END:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        t = self._tick

        box_w, box_h = 110, 50
        margin = 30
        ox = margin
        center_x = W // 2

        # ── Üst yol: Şifreleme ──
        enc_y = 50
        # m kutusu
        if t >= 1:
            self._draw_box(
                p, ox, enc_y, box_w, box_h,
                f"m = {self._M}", ANIM_COLORS["accent_blue"],
                opacity=min(1.0, t / self._T_PLAIN_IN_END),
            )
        # Şifreleme formülü kutusu
        if t > self._T_PLAIN_IN_END:
            opacity = min(1.0, (t - self._T_PLAIN_IN_END) / (self._T_ENC_END - self._T_PLAIN_IN_END))
            self._draw_formula_box(
                p, center_x - 130, enc_y - 10, 260, 70,
                "c = m^e mod n",
                f"= {self._M}^{_E} mod {_N}",
                f"= {self._C}",
                ANIM_COLORS["accent_mauve"],
                lines_revealed=int(3 * opacity) + 1,
            )
            # Açık anahtar kartı
            if t > self._T_PLAIN_IN_END + 4:
                self._draw_key_card(
                    p, W - margin - 140, enc_y - 10,
                    "Açık Anahtar", f"(n={_N}, e={_E})",
                    ANIM_COLORS["accent_blue"],
                )
        # c kutusu
        if t >= self._T_ENC_END:
            opacity = min(1.0, (t - self._T_ENC_END) / (self._T_CIPHER_END - self._T_ENC_END))
            self._draw_box(
                p, W - margin - box_w, enc_y, box_w, box_h,
                f"c = {self._C}", ANIM_COLORS["accent_peach"], opacity=opacity,
            )

        # ── Alt yol: Deşifreleme ──
        dec_y = enc_y + 130
        # c (alt yolda sol)
        if t >= self._T_CIPHER_IN_END:
            self._draw_box(
                p, ox, dec_y, box_w, box_h,
                f"c = {self._C}", ANIM_COLORS["accent_peach"],
            )
        # Deşifreleme formülü
        if t > self._T_CIPHER_IN_END:
            opacity = min(1.0, (t - self._T_CIPHER_IN_END) / (self._T_DEC_END - self._T_CIPHER_IN_END))
            self._draw_formula_box(
                p, center_x - 130, dec_y - 10, 260, 70,
                "m' = c^d mod n",
                f"= {self._C}^{_D} mod {_N}",
                f"= {self._M_PRIME}",
                ANIM_COLORS["accent_green"],
                lines_revealed=int(3 * opacity) + 1,
            )
            if t > self._T_CIPHER_IN_END + 4:
                self._draw_key_card(
                    p, W - margin - 140, dec_y - 10,
                    "Gizli Anahtar", f"(n={_N}, d={_D})",
                    ANIM_COLORS["accent_mauve"],
                )
        # m' kutusu
        if t >= self._T_DEC_END:
            opacity = min(1.0, (t - self._T_DEC_END) / (self._T_PLAIN_OUT_END - self._T_DEC_END))
            label = f"m' = {self._M_PRIME}"
            if t >= self._T_PLAIN_OUT_END:
                label = f"m' = {self._M_PRIME} = m ✓"
            color = ANIM_COLORS["accent_green"] if t >= self._T_PLAIN_OUT_END else ANIM_COLORS["accent_blue"]
            self._draw_box(
                p, W - margin - box_w, dec_y, box_w, box_h,
                label, color, opacity=opacity,
                pulse=(t >= self._T_PLAIN_OUT_END and t < self._T_MATCH_END),
            )

        p.end()

    def _draw_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        text: str, color: str, opacity: float = 1.0, pulse: bool = False,
    ) -> None:
        col = QColor(color)
        col.setAlphaF(opacity)
        fill = QColor(color)
        fill.setAlphaF(opacity * 0.18)
        if pulse:
            # Hafif yanıp sönme efekti — ms cinsinden tick'le hesaplanır
            phase = (self._tick % 8) / 8.0
            fill.setAlphaF(opacity * (0.18 + 0.20 * abs(0.5 - phase) * 2))

        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)
        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)
        p.setPen(text_col)
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_formula_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        line1: str, line2: str, line3: str, color: str,
        lines_revealed: int,
    ) -> None:
        col = QColor(color)
        fill = QColor(color)
        fill.setAlphaF(0.15)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)

        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        p.setPen(text_col)
        lines = [line1, line2, line3]
        for li in range(min(lines_revealed, 3)):
            p.drawText(QRect(x + 8, y + 6 + li * 20, w - 16, 18),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       lines[li])

    def _draw_key_card(
        self, p: QPainter, x: int, y: int, title: str, val: str, color: str,
    ) -> None:
        col = QColor(color)
        fill = QColor(color)
        fill.setAlphaF(0.20)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 1))
        p.drawRoundedRect(x, y, 140, 60, 6, 6)
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(col)
        p.drawText(QRect(x, y + 6, 140, 18), Qt.AlignmentFlag.AlignCenter, title)
        p.setFont(QFont("Courier New", 9))
        p.setPen(QColor(ANIM_COLORS["text_primary"]))
        p.drawText(QRect(x, y + 28, 140, 26), Qt.AlignmentFlag.AlignCenter, val)
```

### - [ ] Step 3.4: `_TITLES` ve `_CAPTIONS` listelerini güncelle

`rsa_animation.py:1372-1395` aralığındaki mevcut `_TITLES` ve `_CAPTIONS` blokları şununla değiştirilir:

```python
    _TITLES = [
        "Adım 1 / 8 — p ve q Seçimi",
        "Adım 2 / 8 — n = p × q",
        "Adım 3 / 8 — φ(n) = (p − 1)(q − 1)",
        "Adım 4 / 8 — Açık Üs e Seçimi",
        "Adım 5 / 8 — Gizli Üs d  (Genişletilmiş Öklid)",
        "Adım 6 / 8 — DER ve Base64 Kodlaması",
        "Adım 7 / 8 — Gerçek Anahtarlarla Eşleşme",
        "Adım 8 / 8 — Şifreleme / Deşifreleme Turu",
    ]

    _CAPTIONS = [
        "p ve q rastgele iki büyük asaldır; n ve φ(n) hesabının temelini oluştururlar.",
        "n = p × q  →  modülüs; hem açık hem gizli anahtarda yer alır.",
        "φ(n) = (p − 1)(q − 1)  →  Euler totient fonksiyonu.",
        "gcd(e, φ(n)) = 1  koşulu sağlanmalı; e açık anahtarın üs bileşenidir.",
        "d, e'nin φ(n) modülünde tersidir:  e · d ≡ 1  (mod φ).",
        "Anahtar dosyada DER yapısında, satır içinde Base64 olarak kodlanır.",
        "Aynı matematik · farklı boyut: demo 12-bit n, gerçek 2048-bit n.",
        "m → c → m'  döngüsü; her iki yön de aynı m değerine ulaşır (Eq:RSAExample).",
    ]
```

### - [ ] Step 3.5: `_page_widgets` listesine yeni widget ekle

`rsa_animation.py:1458-1466` aralığındaki:

```python
        self._page_widgets: list[QWidget] = [
            _PrimeSieveWidget(),
            _MultiplicationWidget(),
            _TotientWidget(),
            _GCDWidget(),
            _EEAWidget(),
            _DERByteFlowWidget(self._alice_b64),
            _KeyMatchWidget(self._alice_b64, self._bob_b64),
        ]
```

şununla değiştirilir:

```python
        self._page_widgets: list[QWidget] = [
            _PrimeSieveWidget(),
            _MultiplicationWidget(),
            _TotientWidget(),
            _GCDWidget(),
            _EEAWidget(),
            _DERByteFlowWidget(self._alice_b64),
            _KeyMatchWidget(self._alice_b64, self._bob_b64),
            _RSAEncryptDecryptWidget(),
        ]
```

### - [ ] Step 3.6: `_render_step` ve `_show_match_result` semantiğini güncelle

`rsa_animation.py:1494-1507` aralığındaki:

```python
    def _render_step(self, idx: int) -> None:
        self._step_lbl.setText(self._TITLES[idx])
        self._stack.setCurrentIndex(idx)
        self._kb.set_step(idx)
        self._caption.setText(self._CAPTIONS[idx])
        self._fade_in_current_page()

    def _show_match_result(self) -> None:
        # Son adım — index 6
        self._step_lbl.setText(self._TITLES[6])
        self._stack.setCurrentIndex(6)
        self._kb.set_step(6)
        self._caption.setText(self._CAPTIONS[6])
        self._fade_in_current_page()
```

şununla değiştirilir:

```python
    def _render_step(self, idx: int) -> None:
        self._step_lbl.setText(self._TITLES[idx])
        self._stack.setCurrentIndex(idx)
        self._kb.set_step(idx)
        self._caption.setText(self._CAPTIONS[idx])
        self._fade_in_current_page()

    def _show_match_result(self) -> None:
        # Son adım — index 7 (Şifreleme/Deşifreleme Turu)
        self._step_lbl.setText(self._TITLES[7])
        self._stack.setCurrentIndex(7)
        self._kb.set_step(7)
        self._caption.setText(self._CAPTIONS[7])
        self._fade_in_current_page()
```

### - [ ] Step 3.7: Tüm testleri çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover -v
```

Beklenen: tüm testler PASS, dahil olmak üzere `TestRSAAnimationStructure`'daki 5 test.

### - [ ] Step 3.8: Manuel görsel doğrulama

1. `python main_gui.py` ile uygulamayı aç.
2. RSA animasyonunu başlat, ▶ ile sona kadar ilerle.
3. **Doğrula:**
   - Progress bar 8 adımı gösterir.
   - Adım 7 (Eşleşme) hâlâ doğru çalışır.
   - Adım 8'e geçince yeni şifreleme/deşifreleme turu animasyonu başlar.
   - `m=65 → c=2790 → m'=65 = m ✓` yeşil pulse ile biter.

### - [ ] Step 3.9: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/rsa_animation.py test_rsa_animation.py && git commit -m "kripto: RSA Adım 8 — şifreleme/deşifreleme turu animasyonu (Eq:RSAExample)"
```

---

## Task 4: SHA-256 Mesaj Genişletme Animasyonu

**Files:**
- Modify: `animation_modals/sha256_animation.py:807-870` (`_make_wexpand_page` fonksiyonu)
- Add: `animation_modals/sha256_animation.py` — yeni `_WExpansionWidget` sınıfı

### - [ ] Step 4.1: Smoke test ekle

`test_sha256_pure.py`'a (en alta, `unittest.main()`'den önce) yeni sınıf eklenir:

```python
class TestSHA256AnimationStructure(unittest.TestCase):
    """sha256_animation modülünün yeni widget yapısını doğrular."""

    def test_w_expansion_widget_exists(self):
        from animation_modals import sha256_animation as sha
        self.assertTrue(hasattr(sha, "_WExpansionWidget"))

    def test_match_assembly_widget_exists(self):
        from animation_modals import sha256_animation as sha
        self.assertTrue(hasattr(sha, "_MatchAssemblyWidget"))
```

### - [ ] Step 4.2: Test'i çalıştır, başarısız olduğunu doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_sha256_pure.TestSHA256AnimationStructure.test_w_expansion_widget_exists -v
```

Beklenen: FAIL (sınıf henüz yok).

### - [ ] Step 4.3: `_WExpansionWidget` sınıfını ekle

`animation_modals/sha256_animation.py` içinde `_RegisterDemoWidget` sınıfının (`sha256_animation.py:348` civarı) **hemen ardından**, `_SHA256IntroWidget`'tan önce, şu yeni sınıf eklenir:

```python
# ---------------------------------------------------------------------------
# Mesaj Genişletme (Message Schedule) animasyonu
# ---------------------------------------------------------------------------

class _WExpansionWidget(QWidget):
    """
    SHA-256 mesaj genişletme animasyonu.

    sha256_pure.sha256_steps()'ın döndürdüğü w_expansion listesi (16 entry,
    i=16..31) üzerinde gezinir. Her i için 4 girdi kutusu (W[i-16], σ0(W[i-15]),
    W[i-7], σ1(W[i-2])) sırayla doğar, ardından oklar `+` düğümüne akar ve
    sonuç W[i] kutusu yeşil pulse ile belirir.

    ◀ / ▶ butonları ile i = 16..31 arasında gezinilir.
    """

    _TICK_MS = 50
    _T_INPUTS_END = 24    # 1200 ms
    _T_ARROWS_END = 36    # +600 ms
    _T_RESULT_END = 44    # +400 ms

    def __init__(
        self, expansion: list[dict] | None, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._exp: list[dict] = expansion or []
        self._cur = 0  # mevcut i'nin _exp listesindeki indeksi (0..15)
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        self.setMinimumHeight(380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Alt navigasyon butonları
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.addStretch(1)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        nav.addStretch(1)

        self._btn_prev = QPushButton("◀ Önceki i")
        self._btn_next = QPushButton("Sonraki i ▶")
        for b in (self._btn_prev, self._btn_next):
            b.setStyleSheet(
                f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
                f"color: #FFFFFF; border: none; border-radius: 6px; "
                f"padding: 6px 14px; font-weight: bold; }}"
                f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
                f"QPushButton:disabled {{ background: {ANIM_COLORS['bg_card']}; "
                f"color: {ANIM_COLORS['text_muted']}; }}"
            )
        self._btn_prev.clicked.connect(self._prev_i)
        self._btn_next.clicked.connect(self._next_i)
        nav.addWidget(self._btn_prev)
        nav.addWidget(self._btn_next)
        nav.addStretch(1)
        outer.addLayout(nav)

        self._update_button_states()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._tick = 0
        self.update()
        if self._exp:
            self._timer.start(self._TICK_MS)

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self) -> None:
        if self._tick < self._T_RESULT_END:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def _prev_i(self) -> None:
        if self._cur > 0:
            self._cur -= 1
            self._restart_animation()

    def _next_i(self) -> None:
        if self._cur < len(self._exp) - 1:
            self._cur += 1
            self._restart_animation()

    def _restart_animation(self) -> None:
        self._tick = 0
        self._update_button_states()
        self.update()
        self._timer.start(self._TICK_MS)

    def _update_button_states(self) -> None:
        self._btn_prev.setEnabled(self._cur > 0)
        self._btn_next.setEnabled(self._cur < len(self._exp) - 1)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        if not self._exp:
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.setFont(QFont("Georgia", 11))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "w_expansion verisi yok")
            p.end()
            return

        entry = self._exp[self._cur]
        i_val = entry["i"]

        # Üst: σ formülleri sabit referans
        p.setFont(QFont("Courier New", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, 8, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "σ0(x) = ROTR(x,7) ⊕ ROTR(x,18) ⊕ SHR(x,3)")
        p.drawText(QRect(0, 26, W, 18), Qt.AlignmentFlag.AlignCenter,
                   "σ1(x) = ROTR(x,17) ⊕ ROTR(x,19) ⊕ SHR(x,10)")

        # Başlık: i = N / 31
        p.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        p.drawText(QRect(0, 50, W, 22), Qt.AlignmentFlag.AlignCenter,
                   f"W[{i_val}] = σ1(W[{i_val-2}]) + W[{i_val-7}] + "
                   f"σ0(W[{i_val-15}]) + W[{i_val-16}]   (mod 2³²)")

        # 4 girdi kutusu (yan yana 2x2 grid)
        box_w, box_h = 200, 56
        gap_x, gap_y = 30, 24
        total_w = 2 * box_w + gap_x
        ox = (W - total_w) // 2
        oy = 90

        inputs = [
            (ox, oy,
             f"W[{i_val-16}]",
             entry["w_i16"],
             None,
             ANIM_COLORS["accent_blue"]),
            (ox + box_w + gap_x, oy,
             f"σ0(W[{i_val-15}])",
             entry["w_i15"],
             entry["s0"],
             ANIM_COLORS["accent_mauve"]),
            (ox, oy + box_h + gap_y,
             f"W[{i_val-7}]",
             entry["w_i7"],
             None,
             ANIM_COLORS["accent_peach"]),
            (ox + box_w + gap_x, oy + box_h + gap_y,
             f"σ1(W[{i_val-2}])",
             entry["w_i2"],
             entry["s1"],
             ANIM_COLORS["accent_yellow"]),
        ]

        # Hangileri görünür?
        # 0..6 → kutu 0; 6..12 → kutu 0+1; 12..18 → +2; 18..24 → +3
        visible_count = min(4, max(0, (self._tick + 5) // 6))

        for idx, (bx, by, label, operand, result, color) in enumerate(inputs):
            if idx >= visible_count:
                continue
            opacity = 1.0
            if idx == visible_count - 1:
                progress = (self._tick - idx * 6) / 6.0
                opacity = max(0.0, min(1.0, progress))
            self._draw_input_box(p, bx, by, box_w, box_h,
                                 label, operand, result, color, opacity)

        # `+` düğümü merkezde
        node_x = W // 2 - 22
        node_y = oy + box_h + gap_y // 2 - 22
        if self._tick >= self._T_INPUTS_END:
            self._draw_plus_node(p, node_x, node_y)

        # 4 ok girdi → düğüm
        if self._tick > self._T_INPUTS_END:
            arrow_progress = min(1.0,
                (self._tick - self._T_INPUTS_END) /
                (self._T_ARROWS_END - self._T_INPUTS_END))
            for bx, by, _, _, _, color in inputs:
                self._draw_arrow_to_node(p, bx + box_w // 2, by + box_h,
                                          node_x + 22, node_y + 22,
                                          QColor(color), arrow_progress)

        # Sonuç kutusu altta
        result_y = oy + 2 * box_h + gap_y + 60
        if self._tick >= self._T_ARROWS_END:
            opacity = min(1.0,
                (self._tick - self._T_ARROWS_END) /
                (self._T_RESULT_END - self._T_ARROWS_END))
            pulse = self._tick >= self._T_RESULT_END
            self._draw_result_box(p, W // 2 - box_w // 2, result_y, box_w, box_h,
                                  i_val, entry["result"], opacity, pulse)
            # düğüm → sonuç oku
            self._draw_arrow_simple(p, node_x + 22, node_y + 44,
                                    W // 2, result_y, QColor(ANIM_COLORS["accent_green"]))

        # Alt: navigasyon göstergesi
        p.setFont(QFont("Georgia", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, H - 80, W, 18), Qt.AlignmentFlag.AlignCenter,
                   f"i = {i_val} / 31  ({self._cur + 1}/{len(self._exp)})")

        p.end()

    def _draw_input_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        label: str, operand: str, result: str | None, color: str,
        opacity: float,
    ) -> None:
        col = QColor(color)
        col.setAlphaF(opacity)
        fill = QColor(color)
        fill.setAlphaF(opacity * 0.18)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)

        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)
        p.setPen(text_col)
        p.drawText(QRect(x + 4, y + 2, w - 8, 18),
                   Qt.AlignmentFlag.AlignCenter, label)

        p.setFont(QFont("Courier New", 10))
        if result is None:
            p.drawText(QRect(x + 4, y + 22, w - 8, 28),
                       Qt.AlignmentFlag.AlignCenter, operand)
        else:
            p.drawText(QRect(x + 4, y + 22, w - 8, 16),
                       Qt.AlignmentFlag.AlignCenter, operand)
            p.setPen(QColor(ANIM_COLORS["accent_green"]))
            p.drawText(QRect(x + 4, y + 38, w - 8, 16),
                       Qt.AlignmentFlag.AlignCenter, f"→ {result}")

    def _draw_plus_node(self, p: QPainter, x: int, y: int) -> None:
        p.setBrush(QBrush(QColor(ANIM_COLORS["bg_input"])))
        p.setPen(QPen(QColor(ANIM_COLORS["accent_green"]), 2))
        p.drawEllipse(x, y, 44, 44)
        p.setFont(QFont("Courier New", 18, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_green"]))
        p.drawText(QRect(x, y, 44, 44), Qt.AlignmentFlag.AlignCenter, "+")

    def _draw_arrow_to_node(
        self, p: QPainter, x1: int, y1: int, x2: int, y2: int,
        color: QColor, progress: float,
    ) -> None:
        """x1,y1'den x2,y2'ye giden okun progress kadarını çiz."""
        col = QColor(color)
        col.setAlphaF(progress)
        p.setPen(QPen(col, 2))
        cx = int(x1 + (x2 - x1) * progress)
        cy = int(y1 + (y2 - y1) * progress)
        p.drawLine(x1, y1, cx, cy)

    def _draw_arrow_simple(
        self, p: QPainter, x1: int, y1: int, x2: int, y2: int,
        color: QColor,
    ) -> None:
        p.setPen(QPen(color, 2))
        p.drawLine(x1, y1, x2, y2)
        # ok ucu
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint
        size = 6
        pts = QPolygon([
            QPoint(x2, y2),
            QPoint(x2 - size, y2 - size * 2),
            QPoint(x2 + size, y2 - size * 2),
        ])
        p.setBrush(QBrush(color))
        p.drawPolygon(pts)

    def _draw_result_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        i: int, value: str, opacity: float, pulse: bool,
    ) -> None:
        col = QColor(ANIM_COLORS["accent_green"])
        col.setAlphaF(opacity)
        fill = QColor(ANIM_COLORS["accent_green"])
        if pulse:
            phase = (self._tick % 8) / 8.0
            fill.setAlphaF(opacity * (0.18 + 0.20 * abs(0.5 - phase) * 2))
        else:
            fill.setAlphaF(opacity * 0.20)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(x, y, w, h, 6, 6)

        p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)
        p.setPen(text_col)
        p.drawText(QRect(x, y, w, h), Qt.AlignmentFlag.AlignCenter,
                   f"W[{i}] = {value}")
```

### - [ ] Step 4.4: `_make_wexpand_page`'i indirgemek

`animation_modals/sha256_animation.py:807-870` aralığındaki **mevcut `_make_wexpand_page` fonksiyonunun tamamı** şununla değiştirilir:

```python
    def _make_wexpand_page(self) -> QWidget:
        """Mesaj genişletme sayfası — animasyonlu _WExpansionWidget."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Adım 2 — Mesaj Genişletme (Message Schedule)")
        title.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_mauve']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        widget = _WExpansionWidget(self._data.get("w_expansion") or [])
        lay.addWidget(widget, stretch=1)
        return w
```

### - [ ] Step 4.5: Smoke test'i çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_sha256_pure.TestSHA256AnimationStructure.test_w_expansion_widget_exists -v
```

Beklenen: PASS.

### - [ ] Step 4.6: Mevcut testlerin bozulmadığını doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover -v
```

Beklenen: tüm testler PASS.

### - [ ] Step 4.7: Manuel görsel doğrulama

1. `python main_gui.py` ile uygulamayı aç.
2. Bir mesaj yaz, SHA-256 işlemini başlat.
3. SHA-256 animasyonunda Adım 2 (Mesaj Genişletme) sayfasına gel.
4. **Doğrula:**
   - 4 girdi kutusu sırayla doğar (~1.2 sn).
   - 4 ok merkezdeki `+` düğümüne akar (~0.6 sn).
   - W[i] sonuç kutusu yeşil pulse ile belirir (~0.4 sn).
   - "Sonraki i ▶" butonuna tıkla; animasyon i=17 için baştan oynar.
   - i=16'da "◀ Önceki i" pasif, i=31'de "Sonraki i ▶" pasif.

### - [ ] Step 4.8: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/sha256_animation.py test_sha256_pure.py && git commit -m "kripto: SHA-256 mesaj genişletmesi animasyonlu widget'a çevrildi"
```

---

## Task 5: SHA-256 Final Eşleşme Animasyonu

**Files:**
- Modify: `animation_modals/sha256_animation.py:899-923` (`_make_match_page`)
- Modify: `animation_modals/sha256_animation.py:981-1048` (`_show_match_result`)
- Add: `animation_modals/sha256_animation.py` — yeni `_MatchAssemblyWidget` sınıfı

### - [ ] Step 5.1: `_MatchAssemblyWidget` sınıfını ekle

`animation_modals/sha256_animation.py` içinde `_WExpansionWidget` sınıfının (Task 4'te eklendi) **hemen ardından** şu yeni sınıf eklenir:

```python
# ---------------------------------------------------------------------------
# Final Hash Eşleşme Animasyonu
# ---------------------------------------------------------------------------

class _MatchAssemblyWidget(QWidget):
    """
    SHA-256 final hash eşleşme animasyonu.

    Dört faz (toplam ~4.7 sn):
      Faz 1 (1500 ms): 8 başlangıç H + 8 çalışma değişkeni kutuları parlar
      Faz 2 (1600 ms): Önceki H + Çalışma = Yeni H toplaması, 8 satır × 200 ms
      Faz 3 (800 ms):  8 yeni H yatayda birleşir → 256-bit hash şeridi
      Faz 4 (800 ms):  Şerit crypto_core ile karakter karakter eşleşir,
                        sonuç kartı (✅ / ❌)

    start_animation(pre_h, working, parts, computed, expected) ile başlatılır.
    """

    _TICK_MS = 50
    _T_F1_END = 30   # 1500 ms
    _T_F2_END = 62   # +1600 ms
    _T_F3_END = 78   # +800 ms
    _T_F4_END = 94   # +800 ms

    _REG_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H"]
    _H_LABELS   = ["H0", "H1", "H2", "H3", "H4", "H5", "H6", "H7"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pre_h: list[str] = ["--------"] * 8
        self._working: list[str] = ["--------"] * 8
        self._parts: list[str] = ["--------"] * 8
        self._computed: str = "0" * 64
        self._expected: str = "0" * 64
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def start_animation(
        self,
        pre_h: list[str],
        working: list[str],
        parts: list[str],
        computed: str,
        expected: str,
    ) -> None:
        self._pre_h = pre_h
        self._working = working
        self._parts = parts
        self._computed = computed
        self._expected = expected
        self._tick = 0
        self._timer.start(self._TICK_MS)
        self.update()

    def hideEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self) -> None:
        if self._tick < self._T_F4_END:
            self._tick += 1
            self.update()
        else:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        t = self._tick

        # Faz 1: Round özet (üstte) — her zaman görünür ama önce sönük
        self._draw_phase1(p, W, t)

        # Faz 2: Toplama tablosu (orta) — t >= T_F1_END
        if t >= self._T_F1_END:
            self._draw_phase2(p, W, t - self._T_F1_END)

        # Faz 3: Birleşim şeridi (alt) — t >= T_F2_END
        if t >= self._T_F2_END:
            self._draw_phase3(p, W, H, t - self._T_F2_END)

        # Faz 4: Eşleşme doğrulaması — t >= T_F3_END
        if t >= self._T_F3_END:
            self._draw_phase4(p, W, H, t - self._T_F3_END)

        p.end()

    def _draw_phase1(self, p: QPainter, W: int, t: int) -> None:
        """8 H başlangıç + 8 A-H çalışma değişkeni (üstte yan yana)."""
        y = 8
        # Sol: H0..H7
        x_start = 12
        box_w = 90
        gap = 4
        # Vurgulanan kutu: t // (1500 / 8) = t // 187.5ms ≈ t // 4 tick (200ms)
        h_lit = min(8, max(0, t // 2)) if t < self._T_F1_END else 8
        for i in range(8):
            x = x_start + i * (box_w + gap)
            opacity = 1.0 if i < h_lit else 0.3
            self._draw_small_box(
                p, x, y, box_w, 38,
                self._H_LABELS[i], self._pre_h[i],
                ANIM_COLORS["accent_blue"], opacity,
            )

        # Orta: → 64 round →
        center_x = W // 2
        if t >= 8:
            p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(0, y + 50, W, 18),
                       Qt.AlignmentFlag.AlignCenter, "→ 64 round →")

        # Sağ: A..H çalışma değişkenleri
        # Yukardakilerin ALTINDA bir satırda
        y2 = y + 70
        a_lit = min(8, max(0, (t - 8) // 2)) if t < self._T_F1_END else 8
        for i in range(8):
            x = x_start + i * (box_w + gap)
            opacity = 1.0 if i < a_lit else 0.3
            self._draw_small_box(
                p, x, y2, box_w, 38,
                self._REG_LABELS[i], self._working[i],
                ANIM_COLORS["accent_mauve"], opacity,
            )

    def _draw_phase2(self, p: QPainter, W: int, t: int) -> None:
        """Önceki H + Çalışma = Yeni H toplama tablosu (8 satır × 4 tick)."""
        oy = 130
        row_h = 22
        col_x = [50, 240, 290, 480, 540, 740]
        # Sütun başlıkları
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["accent_yellow"]))
        # Hizalı header: 3 sütun: Önceki H, +Çalışma, =Yeni H
        # Aslında 5 hücre: önceki | + | çalışma | = | yeni
        center_x = W // 2
        p.drawText(QRect(center_x - 280, oy - 18, 200, 16),
                   Qt.AlignmentFlag.AlignLeft, "Önceki H")
        p.drawText(QRect(center_x - 60, oy - 18, 160, 16),
                   Qt.AlignmentFlag.AlignLeft, "+ Çalışma")
        p.drawText(QRect(center_x + 140, oy - 18, 160, 16),
                   Qt.AlignmentFlag.AlignLeft, "= Yeni H")

        for i in range(8):
            row_t = t - i * 4  # 200 ms aralıkla
            if row_t < 0:
                continue
            row_y = oy + i * row_h
            # Önceki H
            p.setFont(QFont("Courier New", 10))
            p.setPen(QColor(ANIM_COLORS["text_primary"]))
            p.drawText(QRect(center_x - 280, row_y, 200, row_h),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"{self._H_LABELS[i]} = {self._pre_h[i]}")
            # + Çalışma
            if row_t >= 1:
                p.setPen(QColor(ANIM_COLORS["accent_mauve"]))
                p.drawText(QRect(center_x - 60, row_y, 200, row_h),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           f"+ {self._REG_LABELS[i]} = {self._working[i]}")
            # = Yeni H — pulse
            if row_t >= 2:
                pulse = (row_t < 8)
                col = QColor(ANIM_COLORS["accent_green"])
                if pulse:
                    phase = (self._tick % 6) / 6.0
                    col.setAlphaF(0.6 + 0.4 * abs(0.5 - phase) * 2)
                p.setPen(col)
                p.drawText(QRect(center_x + 140, row_y, 200, row_h),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           f"= {self._parts[i]}")

    def _draw_phase3(self, p: QPainter, W: int, H_total: int, t: int) -> None:
        """8 yeni H'nin tek bir 256-bit şeride birleşmesi."""
        # Şerit konumu — tablodan ~70 px aşağı
        y = 320
        max_t = self._T_F3_END - self._T_F2_END  # 16
        progress = min(1.0, t / max_t)
        # 8 H → şerit: ortaya doğru sıkıştırma efekti yok, sadece tek bloktaki gösterim
        full_hash = "".join(self._parts)
        # Şerit kutusu
        strip_w = min(W - 40, 720)
        strip_h = 40
        strip_x = (W - strip_w) // 2
        col = QColor(ANIM_COLORS["accent_green"])
        col.setAlphaF(progress)
        fill = QColor(ANIM_COLORS["accent_green"])
        fill.setAlphaF(progress * 0.20)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(strip_x, y, strip_w, strip_h, 6, 6)
        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(progress)
        p.setPen(text_col)
        # 64 hex karakter — gerekirse iki satıra böl
        if strip_w > 600:
            p.drawText(QRect(strip_x, y, strip_w, strip_h),
                       Qt.AlignmentFlag.AlignCenter, full_hash)
        else:
            p.drawText(QRect(strip_x, y, strip_w, strip_h // 2),
                       Qt.AlignmentFlag.AlignCenter, full_hash[:32])
            p.drawText(QRect(strip_x, y + strip_h // 2, strip_w, strip_h // 2),
                       Qt.AlignmentFlag.AlignCenter, full_hash[32:])

    def _draw_phase4(self, p: QPainter, W: int, H_total: int, t: int) -> None:
        """crypto_core ile karakter karakter eşleşme + sonuç kartı."""
        max_t = self._T_F4_END - self._T_F3_END  # 16
        # 64 hex karakter / 16 tick = 4 karakter/tick
        chars_revealed = min(64, t * 4)
        y = 380

        p.setFont(QFont("Courier New", 9))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        p.drawText(QRect(0, y, W, 16),
                   Qt.AlignmentFlag.AlignCenter, "crypto_core çıktısı:")

        # Karakter karakter çiz, eşleşenler yeşil
        y_chars = y + 18
        # Hizalı: 16 char × char_w merkez
        char_w = 11
        row_w = 64 * char_w
        ox = (W - row_w) // 2
        for i in range(min(chars_revealed, 64)):
            x = ox + i * char_w
            actual_char = self._expected[i] if i < len(self._expected) else "?"
            match = (i < len(self._computed) and i < len(self._expected)
                     and self._computed[i] == self._expected[i])
            col = QColor(ANIM_COLORS["accent_green"] if match
                         else ANIM_COLORS["accent_peach"])
            p.setPen(col)
            p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            p.drawText(QRect(x, y_chars, char_w, 16),
                       Qt.AlignmentFlag.AlignCenter, actual_char)

        # Sonuç kartı (tüm karakterler tarandıktan sonra)
        if chars_revealed >= 64:
            match_all = self._computed == self._expected
            card_y = y_chars + 30
            col = QColor(ANIM_COLORS["accent_green"] if match_all
                         else ANIM_COLORS["accent_peach"])
            fill = QColor(col)
            fill.setAlphaF(0.20)
            card_w = 280
            card_h = 36
            card_x = (W - card_w) // 2
            p.setBrush(QBrush(fill))
            p.setPen(QPen(col, 2))
            p.drawRoundedRect(card_x, card_y, card_w, card_h, 6, 6)
            p.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
            p.setPen(col)
            text = "✅  Eşleşme: Başarılı" if match_all else "❌  Eşleşme: HATA"
            p.drawText(QRect(card_x, card_y, card_w, card_h),
                       Qt.AlignmentFlag.AlignCenter, text)

    def _draw_small_box(
        self, p: QPainter, x: int, y: int, w: int, h: int,
        label: str, value: str, color: str, opacity: float,
    ) -> None:
        col = QColor(color)
        col.setAlphaF(opacity)
        fill = QColor(color)
        fill.setAlphaF(opacity * 0.18)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(col, 1))
        p.drawRoundedRect(x, y, w, h, 4, 4)

        p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(opacity)
        p.setPen(text_col)
        p.drawText(QRect(x, y + 2, w, 14), Qt.AlignmentFlag.AlignCenter, label)
        p.setFont(QFont("Courier New", 9))
        p.drawText(QRect(x, y + 18, w, 18),
                   Qt.AlignmentFlag.AlignCenter, value)
```

### - [ ] Step 5.2: `_make_match_page`'i indirgemek

`animation_modals/sha256_animation.py:899-923` aralığındaki **mevcut `_make_match_page` fonksiyonunun tamamı** şununla değiştirilir:

```python
    def _make_match_page(self) -> QWidget:
        """Final eşleşme sayfası — animasyonlu _MatchAssemblyWidget."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Final Hash Eşleşmesi")
        title.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        self._match_widget = _MatchAssemblyWidget()
        lay.addWidget(self._match_widget, stretch=1)
        return w
```

### - [ ] Step 5.3: `_show_match_result`'ı indirgemek

`animation_modals/sha256_animation.py:981-1048` aralığındaki **mevcut `_show_match_result` fonksiyonunun tamamı** şununla değiştirilir:

```python
    def _show_match_result(self) -> None:
        """Final eşleşme sayfasını göster, animasyonu başlat."""
        self._stack.setCurrentWidget(self._page_match)
        self._match_widget.start_animation(
            pre_h=self._data["pre_final_h"],
            working=self._data["final_working"],
            parts=self._data["final_h_parts"],
            computed=self._data["final_hash"],
            expected=self._expected_hash,
        )
```

### - [ ] Step 5.4: Smoke testleri çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_sha256_pure.TestSHA256AnimationStructure -v
```

Beklenen: 2 test PASS.

### - [ ] Step 5.5: Tüm testler çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover -v
```

Beklenen: tüm testler PASS, dahil olmak üzere `test_final_hash_matches_hashlib` (yani `_MatchAssemblyWidget`'in beslendiği veriler doğru).

### - [ ] Step 5.6: Manuel görsel doğrulama

1. `python main_gui.py` ile uygulamayı aç.
2. Bir mesaj yaz, SHA-256 animasyonunu başlat.
3. ▶ ile sona kadar ilerle (final eşleşme sayfasına).
4. **Doğrula:**
   - Faz 1: Üst kısımda 8 H + 8 A-H kutuları sırayla parlar.
   - Faz 2: 8 satırlık toplama tablosu satır satır canlanır, her satırda yeşil pulse.
   - Faz 3: Alt kısımda 256-bit hash şeridi belirir.
   - Faz 4: `crypto_core çıktısı:` etiketi altında 64 hex karakter sol→sağ taranır, hepsi yeşil → ✅ kart.

### - [ ] Step 5.7: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/sha256_animation.py && git commit -m "kripto: SHA-256 final eşleşme metni animasyonlu widget'a çevrildi"
```

---

## Final Self-Review

**Spec coverage check:**
- ✅ Bileşen 1 — EEA Canlı Hesaplama Şeridi → Task 2
- ✅ Bileşen 2 — RSA Tez Değerleri Sabitlenmesi → Task 1
- ✅ Bileşen 3 — RSA Adım 8 Şifreleme/Deşifreleme → Task 3
- ✅ Bileşen 4 — SHA-256 Mesaj Genişletme → Task 4
- ✅ Bileşen 5 — SHA-256 Final Eşleşme → Task 5
- ✅ Test ve Doğrulama Planı → her görevde manuel doğrulama adımı

**Type/method consistency:**
- `_MatchAssemblyWidget.start_animation(pre_h, working, parts, computed, expected)` — Task 5'te tanımlandı, Task 5.3'te aynı parametrelerle çağrıldı. ✓
- `_WExpansionWidget(expansion: list[dict])` — Task 4.3'te tanımlandı, Task 4.4'te `self._data.get("w_expansion") or []` ile çağrıldı. ✓
- `_RSAEncryptDecryptWidget()` — Task 3.3'te tanımlandı (parametresiz), Task 3.5'te parametresiz çağrıldı. ✓
- `_eea_steps`, `_PHI`, `_E`, `_D` — Task 1'de sabitlendi, Task 2'de tüketildi. ✓

**Placeholder scan:** Tüm görevlerde tam kod blokları, eksiksiz dosya yolları, çalıştırılabilir bash komutları var. "TODO" / "TBD" / "implement later" yok.

**Independent commit-ability:** Her görev kendi commit'i ile bağımsız uygulanabilir. Görev sırası önemli (Task 2 Task 1'in sabitlerine dayanıyor; Task 3 Task 1'in `_E`, `_D` değerlerine dayanıyor). Task 4 ve 5 birbirinden bağımsız ama her ikisi de Task 1-3'ten bağımsız.
