# AES State Matrix — Byte-Hareket Animasyonu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AES state matris görselleştirmesini, byte-hareket animasyonları, before/after yan-yana karşılaştırma ve operasyon başına özel koreografi içeren QPainter tabanlı yeni bir widget setiyle değiştir.

**Architecture:** Yeni dosya `aes_matrix_view.py` iki sınıf içerir — `_AESMatrixView` (tek QPainter matris + animasyon motoru) ve `_AESStateCompareWidget` (yan yana iki view + Yeniden Oynat butonu). AES penceresi `mat_frame` içeriğini bu kapsayıcıyla değiştirir; `_render_step` tek satıra iner.

**Tech Stack:** Python 3.11, PyQt6 (QPainter, QTimer, QWidget), mevcut `ANIM_COLORS` paleti, `unittest` test framework'ü.

**İlgili tasarım dokümanı:** [docs/specs/2026-05-12-aes-matrix-animation-design.md](../specs/2026-05-12-aes-matrix-animation-design.md)

---

## File Structure

| Dosya | Değişim | Sorumluluk |
| --- | --- | --- |
| `animation_modals/aes_matrix_view.py` | Create (~500 satır) | `_AESMatrixView` + `_AESStateCompareWidget`. QPainter tabanlı matris çizimi ve operasyon başına koreografi (`_draw_overlay_<op>`) |
| `animation_modals/aes_animation.py` | Modify | `mat_frame` içeriği değişir; `_matrix_pair` instance attr; `_render_step` indirgemesi; `_show_match_result` indirgemesi |
| `test_aes_matrix_view.py` | Create | Birim testleri: state atama, animasyon timer kurulumu, on_done callback, replay, stop_animation |
| `animation_modals/matrix_widget.py` | No-change | AES kullanmaz olur ama smoke test referansı için kalır |

---

## Task 1: `_AESMatrixView` — Skeleton + Animasyon Infrastructure

**Files:**
- Create: `animation_modals/aes_matrix_view.py`
- Create: `test_aes_matrix_view.py`

### - [ ] Step 1.1: Failing testler yaz

Yeni dosya `c:\Users\sasss\Desktop\BİTİRME PROJESİ\test_aes_matrix_view.py`:

```python
"""
test_aes_matrix_view.py — _AESMatrixView ve _AESStateCompareWidget birim testleri
=================================================================================
QPainter çizimini test edemeyiz (pixel doğrulaması yok); state yönetimi,
animasyon timer kurulumu, callback çağrılması gibi invariant'ları test ederiz.
Görsel doğrulama manuel.
"""
import unittest


class TestAESMatrixViewBasics(unittest.TestCase):
    """_AESMatrixView temel state yönetimi."""

    def _make_view(self):
        from animation_modals.aes_matrix_view import _AESMatrixView
        return _AESMatrixView(label_title="Test")

    def test_class_exists(self):
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESMatrixView"))

    def test_constructs_without_error(self):
        view = self._make_view()
        self.assertIsNotNone(view)

    def test_default_state_is_4x4_zeros(self):
        view = self._make_view()
        self.assertEqual(view._state, [["00"] * 4 for _ in range(4)])

    def test_set_state_stores_matrix(self):
        view = self._make_view()
        matrix = [[f"{r}{c}" for c in range(4)] for r in range(4)]
        view.set_state(matrix)
        self.assertEqual(view._state, matrix)

    def test_set_state_stops_active_animation(self):
        view = self._make_view()
        view._anim_timer.start(40)  # sahte aktif animasyon
        self.assertTrue(view._anim_timer.isActive())
        view.set_state([["FF"] * 4 for _ in range(4)])
        self.assertFalse(view._anim_timer.isActive())


class TestAESMatrixViewAnimation(unittest.TestCase):
    """_AESMatrixView animasyon timer ve callback davranışı."""

    def _make_view(self):
        from animation_modals.aes_matrix_view import _AESMatrixView
        return _AESMatrixView()

    def test_play_animation_starts_timer(self):
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("AddRoundKey", before, after)
        self.assertTrue(view._anim_timer.isActive())
        self.assertEqual(view._op, "AddRoundKey")
        self.assertEqual(view._tick, 0)
        self.assertGreater(view._total_ticks, 0)

    def test_play_animation_unknown_op_raises(self):
        view = self._make_view()
        with self.assertRaises(ValueError):
            view.play_animation("BogusOp", [], [])

    def test_play_animation_stores_round_key(self):
        view = self._make_view()
        rk = [["AA"] * 4 for _ in range(4)]
        view.play_animation(
            "AddRoundKey",
            [["00"] * 4 for _ in range(4)],
            [["FF"] * 4 for _ in range(4)],
            round_key=rk,
        )
        self.assertEqual(view._round_key, rk)

    def test_stop_animation_advances_to_end(self):
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("AddRoundKey", before, after)
        view.stop_animation()
        self.assertFalse(view._anim_timer.isActive())
        self.assertEqual(view._tick, view._total_ticks)
        self.assertEqual(view._state, after)

    def test_on_tick_advances_and_completes(self):
        """_total_ticks tick'inden sonra timer durmalı, callback çağrılmalı."""
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        callback_calls = []
        view.play_animation(
            "AddRoundKey", before, after,
            on_done=lambda: callback_calls.append(True),
        )
        # _total_ticks kadar manuel tick at
        total = view._total_ticks
        for _ in range(total):
            view._on_tick()
        self.assertFalse(view._anim_timer.isActive())
        self.assertEqual(view._state, after)
        self.assertEqual(callback_calls, [True])

    def test_replay_reuses_last_params(self):
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("ShiftRows", before, after)
        view._tick = 50  # animasyon ortasında
        view.replay()
        self.assertEqual(view._tick, 0)
        self.assertEqual(view._op, "ShiftRows")

    def test_replay_without_prior_animation_is_noop(self):
        view = self._make_view()
        view.replay()  # hata olmamalı
        self.assertIsNone(view._op)


if __name__ == "__main__":
    unittest.main()
```

### - [ ] Step 1.2: Testlerin başarısız olduğunu doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_aes_matrix_view -v
```

Beklenen: tüm testler FAIL/ERROR çünkü `aes_matrix_view.py` modülü yok.

### - [ ] Step 1.3: `aes_matrix_view.py` dosyasını oluştur

Yeni dosya `c:\Users\sasss\Desktop\BİTİRME PROJESİ\animation_modals\aes_matrix_view.py`:

```python
# animation_modals/aes_matrix_view.py
"""
_AESMatrixView ve _AESStateCompareWidget — AES state matrisi için
QPainter tabanlı byte-hareket animasyon görünümü.

_AESMatrixView: tek 4×4 matris, statik veya animasyonlu mod.
_AESStateCompareWidget: yan yana iki _AESMatrixView (Önceki / Şimdiki)
                        + Yeniden Oynat butonu.

Operasyon başına koreografi `_draw_overlay_<op>` metodlarında tanımlı
(Task 4-7'de doldurulacak).
"""
from __future__ import annotations
from collections.abc import Callable

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from .base import ANIM_COLORS


class _AESMatrixView(QWidget):
    """Tek bir 4×4 AES state matrisini QPainter ile çizer.

    İki mod:
      - statik: ``set_state(matrix)`` ile dondurulmuş matris
      - animasyonlu: ``play_animation(op, before, after, ...)`` ile koreografi
    """

    # Hücre boyutları
    _CELL_W = 56
    _CELL_H = 44
    _CELL_GAP = 4
    _LABEL_W = 18      # sol r0..r3 etiket sütunu genişliği
    _LABEL_H = 16      # üst c0..c3 etiket satırı yüksekliği
    _TITLE_H = 22      # opsiyonel başlık satırı yüksekliği

    # Animasyon
    _TICK_MS = 40      # 25 fps

    # Operasyon başına toplam tick sayıları
    _TICKS_BY_OP: dict[str, int] = {
        "AddRoundKey": 60,    # ~2.4 s
        "SubBytes":    64,    # ~2.6 s
        "ShiftRows":   80,    # ~3.2 s
        "MixColumns":  80,    # ~3.2 s
    }

    def __init__(
        self,
        *,
        label_title: str = "",
        label_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label_title = label_title
        self._label_color = label_color or ANIM_COLORS["text_secondary"]

        # State
        self._state: list[list[str]] = [["00"] * 4 for _ in range(4)]
        self._before: list[list[str]] = [["00"] * 4 for _ in range(4)]
        self._after: list[list[str]] = [["00"] * 4 for _ in range(4)]
        self._round_key: list[list[str]] | None = None
        self._op: str | None = None
        self._tick: int = 0
        self._total_ticks: int = 0
        self._on_done: Callable[[], None] | None = None

        # Timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_tick)

        # Boyut
        title_h = self._TITLE_H if label_title else 0
        total_w = self._LABEL_W + 4 * self._CELL_W + 3 * self._CELL_GAP + 12
        total_h = (
            title_h + self._LABEL_H + 4 * self._CELL_H + 3 * self._CELL_GAP + 12
        )
        self.setMinimumSize(total_w, total_h)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # --- Public API ---

    def set_state(self, matrix: list[list[str]]) -> None:
        """Animasyonsuz, anlık durum atama (donmuş matris için)."""
        self._state = [row[:] for row in matrix]
        self._op = None
        self._anim_timer.stop()
        self.update()

    def play_animation(
        self,
        operation: str,
        before: list[list[str]],
        after: list[list[str]],
        *,
        round_key: list[list[str]] | None = None,
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """Operasyon koreografisini başlat."""
        if operation not in self._TICKS_BY_OP:
            raise ValueError(f"Bilinmeyen operasyon: {operation}")
        self._op = operation
        self._before = [row[:] for row in before]
        self._after = [row[:] for row in after]
        self._round_key = (
            [row[:] for row in round_key] if round_key is not None else None
        )
        self._state = [row[:] for row in self._before]
        self._tick = 0
        self._total_ticks = self._TICKS_BY_OP[operation]
        self._on_done = on_done
        self._anim_timer.start(self._TICK_MS)
        self.update()

    def replay(self) -> None:
        """En son play_animation çağrısını baştan oyna."""
        if self._op is None:
            return
        self.play_animation(
            self._op, self._before, self._after,
            round_key=self._round_key, on_done=self._on_done,
        )

    def stop_animation(self) -> None:
        """Animasyonu durdur, after state'e atla."""
        self._anim_timer.stop()
        if self._op is not None:
            self._tick = self._total_ticks
            self._state = [row[:] for row in self._after]
        self.update()

    # --- Timer ---

    def _on_tick(self) -> None:
        self._tick += 1
        if self._tick >= self._total_ticks:
            self._anim_timer.stop()
            self._state = [row[:] for row in self._after]
            cb = self._on_done
            self._on_done = None
            self.update()
            if cb is not None:
                cb()
            return
        self.update()

    # --- Çizim ---

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Başlık (varsa)
        title_h = self._TITLE_H if self._label_title else 0
        if self._label_title:
            p.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
            p.setPen(QColor(self._label_color))
            p.drawText(QRect(0, 4, self.width(), 18),
                       Qt.AlignmentFlag.AlignCenter, self._label_title)

        ox = 6
        oy = title_h + 4

        # Sütun etiketleri (c0..c3)
        p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
        p.setPen(QColor(ANIM_COLORS["text_muted"]))
        for c in range(4):
            x = ox + self._LABEL_W + c * (self._CELL_W + self._CELL_GAP)
            p.drawText(QRect(x, oy, self._CELL_W, self._LABEL_H),
                       Qt.AlignmentFlag.AlignCenter, f"c{c}")

        # Satır etiketleri + hücreler
        cell_oy = oy + self._LABEL_H
        for r in range(4):
            cy = cell_oy + r * (self._CELL_H + self._CELL_GAP)
            # Satır etiketi
            p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
            p.setPen(QColor(ANIM_COLORS["text_muted"]))
            p.drawText(QRect(ox, cy, self._LABEL_W, self._CELL_H),
                       Qt.AlignmentFlag.AlignCenter, f"r{r}")
            for c in range(4):
                cx = ox + self._LABEL_W + c * (self._CELL_W + self._CELL_GAP)
                self._draw_cell(p, cx, cy, self._state[r][c])

        # Overlay (animasyon)
        if self._op is not None and 0 <= self._tick < self._total_ticks:
            self._draw_overlay(p, ox + self._LABEL_W, cell_oy)

        p.end()

    def _draw_cell(
        self, p: QPainter, x: int, y: int, value: str,
        *, bg: str | None = None, border: str | None = None,
        alpha: float = 1.0,
    ) -> None:
        bg_color = QColor(bg or ANIM_COLORS["bg_card"])
        bg_color.setAlphaF(alpha)
        border_color = QColor(border or ANIM_COLORS["border"])
        border_color.setAlphaF(alpha)
        p.setBrush(QBrush(bg_color))
        p.setPen(QPen(border_color, 1))
        p.drawRoundedRect(x, y, self._CELL_W, self._CELL_H, 4, 4)
        text_col = QColor(ANIM_COLORS["text_primary"])
        text_col.setAlphaF(alpha)
        p.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        p.setPen(text_col)
        p.drawText(QRect(x, y, self._CELL_W, self._CELL_H),
                   Qt.AlignmentFlag.AlignCenter, value)

    def _cell_xy(self, ox: int, oy: int, r: int, c: int) -> tuple[int, int]:
        """Verilen satır/sütun için hücre sol-üst piksel koordinatı."""
        x = ox + c * (self._CELL_W + self._CELL_GAP)
        y = oy + r * (self._CELL_H + self._CELL_GAP)
        return x, y

    def _draw_overlay(self, p: QPainter, ox: int, oy: int) -> None:
        """Operasyon-özgü overlay. Task 4-7'de doldurulacak."""
        op = self._op
        if op == "AddRoundKey":
            self._draw_overlay_addroundkey(p, ox, oy)
        elif op == "SubBytes":
            self._draw_overlay_subbytes(p, ox, oy)
        elif op == "ShiftRows":
            self._draw_overlay_shiftrows(p, ox, oy)
        elif op == "MixColumns":
            self._draw_overlay_mixcolumns(p, ox, oy)

    # Koreografi hook'ları — Task 4-7'de doldurulacak.
    def _draw_overlay_addroundkey(self, p: QPainter, ox: int, oy: int) -> None:
        pass

    def _draw_overlay_subbytes(self, p: QPainter, ox: int, oy: int) -> None:
        pass

    def _draw_overlay_shiftrows(self, p: QPainter, ox: int, oy: int) -> None:
        pass

    def _draw_overlay_mixcolumns(self, p: QPainter, ox: int, oy: int) -> None:
        pass
```

### - [ ] Step 1.4: Testleri çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_aes_matrix_view -v
```

Beklenen: 11 yeni test PASS.

### - [ ] Step 1.5: Tüm testler hâlâ geçiyor mu kontrol

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover 2>&1 | tail -3
```

Beklenen: 143 test PASS (132 mevcut + 11 yeni).

### - [ ] Step 1.6: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/aes_matrix_view.py test_aes_matrix_view.py && git commit -m "kripto: AES matris animasyon altyapısı — _AESMatrixView iskeleti"
```

---

## Task 2: `_AESStateCompareWidget` — Yan-Yana Kapsayıcı

**Files:**
- Modify: `animation_modals/aes_matrix_view.py` (sınıf ekle)
- Modify: `test_aes_matrix_view.py` (testler ekle)

### - [ ] Step 2.1: Failing testler ekle

`test_aes_matrix_view.py` dosyasının altına (en altta `if __name__` öncesi) ekle:

```python
class TestAESStateCompareWidget(unittest.TestCase):
    """_AESStateCompareWidget kapsayıcı widget."""

    def _make_widget(self):
        from animation_modals.aes_matrix_view import _AESStateCompareWidget
        return _AESStateCompareWidget()

    def test_class_exists(self):
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESStateCompareWidget"))

    def test_constructs_without_error(self):
        w = self._make_widget()
        self.assertIsNotNone(w)
        # Önceki ve şimdiki view'lar erişilebilir olmalı
        self.assertTrue(hasattr(w, "_prev_view"))
        self.assertTrue(hasattr(w, "_curr_view"))
        # Yeniden Oynat butonu
        self.assertTrue(hasattr(w, "_replay_btn"))

    def test_start_step_sets_prev_state_and_plays_curr(self):
        w = self._make_widget()
        before = [[f"b{r}{c}" for c in range(4)] for r in range(4)]
        after = [[f"a{r}{c}" for c in range(4)] for r in range(4)]
        w.start_step("AddRoundKey", before, after, op_color="#5B8EC2")
        # Önceki view'da before donmuş olmalı
        self.assertEqual(w._prev_view._state, before)
        # Şimdiki view animasyon başlatmış olmalı
        self.assertEqual(w._curr_view._op, "AddRoundKey")
        self.assertTrue(w._curr_view._anim_timer.isActive())

    def test_start_step_sets_arrow_label(self):
        w = self._make_widget()
        w.start_step(
            "ShiftRows",
            [["00"] * 4] * 4, [["FF"] * 4] * 4,
            op_color="#5B8EC2",
        )
        self.assertIn("ShiftRows", w._arrow_label.text())

    def test_show_final_sets_both_to_same_state(self):
        w = self._make_widget()
        final = [[f"f{r}{c}" for c in range(4)] for r in range(4)]
        w.show_final(final)
        self.assertEqual(w._prev_view._state, final)
        self.assertEqual(w._curr_view._state, final)
        # Animasyon yok
        self.assertIsNone(w._curr_view._op)

    def test_replay_button_triggers_curr_replay(self):
        w = self._make_widget()
        before = [["00"] * 4] * 4
        after = [["FF"] * 4] * 4
        w.start_step("AddRoundKey", before, after, op_color="#5B8EC2")
        # Sahte ilerleme
        w._curr_view._tick = 30
        # Butonu programatik tıkla
        w._replay_btn.click()
        # _tick sıfırlanmış olmalı
        self.assertEqual(w._curr_view._tick, 0)
```

### - [ ] Step 2.2: Testlerin başarısız olduğunu doğrula

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_aes_matrix_view.TestAESStateCompareWidget -v
```

Beklenen: 6 yeni test FAIL (sınıf yok).

### - [ ] Step 2.3: `_AESStateCompareWidget` sınıfını ekle

`animation_modals/aes_matrix_view.py` dosyasının en altına (son `pass` satırından sonra) ekle:

```python


class _AESStateCompareWidget(QWidget):
    """Yan yana iki _AESMatrixView + Yeniden Oynat butonu.

    Sol: önceki state (donmuş, set_state ile)
    Orta: aktif operasyon etiketi (renkli ok)
    Sağ: şimdiki state (canlı, play_animation ile)
    Üst sağ: Yeniden Oynat butonu
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        # Üst sağ: Yeniden Oynat butonu
        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self._replay_btn = QPushButton("⟲  Yeniden Oynat")
        self._replay_btn.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['accent_blue']}; "
            f"color: #FFFFFF; border: none; border-radius: 6px; "
            f"padding: 4px 14px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_mauve']}; }}"
        )
        self._replay_btn.setFixedHeight(28)
        self._replay_btn.clicked.connect(self._on_replay)
        top_row.addWidget(self._replay_btn)
        outer.addLayout(top_row)

        # Orta: önceki view → ok → şimdiki view
        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)
        mid_row.addStretch(1)

        self._prev_view = _AESMatrixView(
            label_title="ÖNCEKİ",
            label_color=ANIM_COLORS["text_muted"],
        )
        mid_row.addWidget(self._prev_view)

        self._arrow_label = QLabel("→")
        self._arrow_label.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        self._arrow_label.setStyleSheet(
            f"color: {ANIM_COLORS['text_muted']};"
        )
        self._arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow_label.setMinimumWidth(120)
        mid_row.addWidget(self._arrow_label)

        self._curr_view = _AESMatrixView(
            label_title="ŞİMDİKİ (canlı)",
            label_color=ANIM_COLORS["accent_blue"],
        )
        mid_row.addWidget(self._curr_view)

        mid_row.addStretch(1)
        outer.addLayout(mid_row)
        outer.addStretch(1)

    def start_step(
        self,
        operation: str,
        before: list[list[str]],
        after: list[list[str]],
        op_color: str,
        *,
        round_key: list[list[str]] | None = None,
    ) -> None:
        """Adımı başlat: önceki donmuş, şimdiki animasyonlu."""
        # Önceki çalışan animasyonu durdur
        self._curr_view.stop_animation()
        # Önceki view'a donmuş before state
        self._prev_view.set_state(before)
        # Ok etiketini güncelle
        self._arrow_label.setText(f"→  {operation}  →")
        self._arrow_label.setStyleSheet(
            f"color: {op_color}; font-weight: bold;"
        )
        # Şimdiki view'a animasyon
        self._curr_view.play_animation(
            operation, before, after, round_key=round_key,
        )

    def show_final(self, final_state: list[list[str]]) -> None:
        """Round 14 sonrası: iki matris de final state, animasyon yok."""
        self._curr_view.stop_animation()
        self._prev_view.set_state(final_state)
        self._curr_view.set_state(final_state)
        self._arrow_label.setText("=  FINAL  =")
        self._arrow_label.setStyleSheet(
            f"color: {ANIM_COLORS['accent_green']}; font-weight: bold;"
        )

    def _on_replay(self) -> None:
        self._curr_view.replay()
```

### - [ ] Step 2.4: Testleri çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_aes_matrix_view -v
```

Beklenen: 17 test PASS (11 önceki + 6 yeni).

### - [ ] Step 2.5: Tüm testler

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover 2>&1 | tail -3
```

Beklenen: 149 test PASS.

### - [ ] Step 2.6: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/aes_matrix_view.py test_aes_matrix_view.py && git commit -m "kripto: _AESStateCompareWidget — yan yana iki matris + Yeniden Oynat"
```

---

## Task 3: AES Penceresi Entegrasyonu

**Files:**
- Modify: `animation_modals/aes_animation.py` (üç bölge: imports, `_make_round_page`, `_render_step`, `_show_match_result`)

### - [ ] Step 3.1: Import ekle

`animation_modals/aes_animation.py` dosyasının en üstündeki diğer animation_modals import'larının yanına ekle. Aramak için: `from .matrix_widget import MatrixWidget` satırını bul, hemen üstüne veya altına yeni satır ekle:

```python
from .aes_matrix_view import _AESStateCompareWidget
```

(`MatrixWidget` import'u kalıyor — dosyanın başka bir yerinde başka kullanım olabilir; smoke test referansı için modül de duruyor.)

### - [ ] Step 3.2: `mat_frame` içeriğini değiştir

`aes_animation.py:1467` civarında — `mat_frame = QFrame()` ile başlayan bloğu bul. Bu blok `mat_frame.setStyleSheet(...)` ile başlayıp `content_row.addWidget(mat_frame)` ile biten yaklaşık 25 satırlık alandır.

**ESKİ BLOK (replace):**

```python
        mat_frame = QFrame()
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {ANIM_COLORS['accent_blue']}; border-radius: 8px; }}"
        )
        mat_lay = QVBoxLayout(mat_frame)
        mat_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mat_lay.setContentsMargins(8, 6, 8, 6)
        mat_lay.setSpacing(4)

        # Üst etiket — "State Matrisi" başlığı, prominence için belirgin
        mat_title = QLabel("State Matrisi  (4×4 byte, hex)")
        mat_title.setFont(QFont("Georgia", 10, QFont.Weight.Bold))
        mat_title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        mat_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mat_lay.addWidget(mat_title)

        # İşlem-bağlam alt başlığı — "Round 1 — ShiftRows: 2. satır 1 bayt sola"
        # _render_step her adımda günceller; kullanıcı şu an hangi
        # satır/sütun üzerinde işlem yapıldığını net görür.
        self._matrix_context = QLabel("")
        self._matrix_context.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        self._matrix_context.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._matrix_context.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matrix_context.setWordWrap(True)
        mat_lay.addWidget(self._matrix_context)

        # Matrisin kendisi — satır/sütun etiketleri ile (r0..r3, c0..c3)
        self._matrix = MatrixWidget(parent=self, show_labels=True)
        mat_lay.addWidget(self._matrix, alignment=Qt.AlignmentFlag.AlignCenter)

        content_row.addWidget(mat_frame)
```

**YENİ BLOK (with):**

```python
        mat_frame = QFrame()
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 2px solid {ANIM_COLORS['accent_blue']}; border-radius: 8px; }}"
        )
        mat_lay = QVBoxLayout(mat_frame)
        mat_lay.setContentsMargins(8, 6, 8, 6)
        mat_lay.setSpacing(4)

        # İşlem-bağlam alt başlığı — _render_step her adımda günceller
        self._matrix_context = QLabel("")
        self._matrix_context.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        self._matrix_context.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._matrix_context.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matrix_context.setWordWrap(True)
        mat_lay.addWidget(self._matrix_context)

        # Yeni: yan yana iki QPainter matris + Yeniden Oynat butonu
        self._matrix_pair = _AESStateCompareWidget(parent=self)
        mat_lay.addWidget(self._matrix_pair)

        content_row.addWidget(mat_frame)
```

### - [ ] Step 3.3: `_render_step` indirgemesi

`aes_animation.py:1706` civarında — `op = step["operation"]` satırından sonra başlayan if/elif zincirini bul. Şu mevcut blok (yaklaşık 40 satır):

**ESKİ BLOK (replace):**

```python
        op = step["operation"]

        # State matrix bağlam başlığını güncelle — hangi satır/sütun aktif
        self._matrix_context.setText(
            f"{op}: {self._MATRIX_CONTEXT_BY_OP.get(op, '')}"
        )
        self._matrix_context.setStyleSheet(f"color: {step['color']};")

        # Bir önceki adımın matrisi (before state)
        before = (
            self._steps_data[step_idx - 1]["matrix"]
            if step_idx > 0
            else step["matrix"]
        )
        after = step["matrix"]

        if op == "SubBytes":
            # Sağ panel: byte → S-Box[byte] görselleştirmesi
            self._side_stack.setCurrentIndex(3)
            self._sub_widget.set_data(before, after)
            # Ana matris: hücre hücre canlandır
            ops = [(r, c, after[r][c]) for r in range(4) for c in range(4)]
            self._matrix.highlight_cells_sequential(
                ops, step["color"], interval_ms=60, callback=None
            )

        elif op == "ShiftRows":
            self._side_stack.setCurrentIndex(1)
            # Sağ panel: animasyonlu ok diyagramı (önce → sonra)
            self._shift_widget.set_data(before, after)
            # Ana matris: satır kaydırma animasyonu
            for row_idx, shift in enumerate([0, 1, 2, 3]):
                if shift > 0:
                    self._matrix.animate_row_shift(row_idx, shift, step["color"])
                else:
                    for c in range(4):
                        self._matrix.update_cell(row_idx, c, after[row_idx][c])
            # Animasyon bittikten sonra satır renklerini default'a döndür —
            # böylece "hangi satırı kullanıyoruz" karışıklığı olmaz, sağ paneldeki
            # renk kodu zaten hangi satırın kaç bayt kaydığını net anlatıyor.
            QTimer.singleShot(900, self._matrix.reset_colors)

        elif op == "MixColumns":
            self._side_stack.setCurrentIndex(2)
            # Sağ panel: animasyonlu sütun karıştırma diyagramı
            self._mix_widget.set_data(before, after)
            # Ana matris: sütun renkleriyle güncelle
            col_colors = [
                ANIM_COLORS["accent_blue"],
                ANIM_COLORS["accent_mauve"],
                ANIM_COLORS["accent_yellow"],
                ANIM_COLORS["accent_peach"],
            ]
            for col in range(4):
                for row in range(4):
                    self._matrix.update_cell(row, col, after[row][col], col_colors[col])

        else:  # AddRoundKey
            # Sağ panel: state ⊕ round_key = yeni state byte-bazlı XOR
            self._side_stack.setCurrentIndex(4)
            rnd = step["round"]
            rk = self._round_keys_hex[rnd] if rnd < len(self._round_keys_hex) else None
            if rk is not None:
                self._ark_widget.set_data(before, after, rk, rnd)
            self._matrix.set_matrix(after, step["color"])
            QTimer.singleShot(250, self._matrix.reset_colors)
```

**YENİ BLOK (with):**

```python
        op = step["operation"]

        # State matrix bağlam başlığını güncelle — hangi satır/sütun aktif
        self._matrix_context.setText(
            f"{op}: {self._MATRIX_CONTEXT_BY_OP.get(op, '')}"
        )
        self._matrix_context.setStyleSheet(f"color: {step['color']};")

        # Bir önceki adımın matrisi (before state)
        before = (
            self._steps_data[step_idx - 1]["matrix"]
            if step_idx > 0
            else step["matrix"]
        )
        after = step["matrix"]

        # Sağ panel — operasyona göre değişir (eskisi gibi)
        rnd = step["round"]
        rk: list[list[str]] | None = None
        if op == "SubBytes":
            self._side_stack.setCurrentIndex(3)
            self._sub_widget.set_data(before, after)
        elif op == "ShiftRows":
            self._side_stack.setCurrentIndex(1)
            self._shift_widget.set_data(before, after)
        elif op == "MixColumns":
            self._side_stack.setCurrentIndex(2)
            self._mix_widget.set_data(before, after)
        else:  # AddRoundKey
            self._side_stack.setCurrentIndex(4)
            if rnd < len(self._round_keys_hex):
                rk = self._round_keys_hex[rnd]
                self._ark_widget.set_data(before, after, rk, rnd)

        # State matrisi: yan yana iki matris + animasyon (tek satıra indi)
        self._matrix_pair.start_step(
            op, before, after, step["color"], round_key=rk,
        )
```

### - [ ] Step 3.4: `_show_match_result` indirgemesi

`aes_animation.py` içinde `_show_match_result` metodunu bul. İçinde `self._matrix.set_matrix(...)` veya `self._matrix.update_cell(...)` çağrıları varsa onları `self._matrix_pair.show_final(mat)` ile değiştir.

Örnek (asıl satırlar projenize göre farklı olabilir — `set_matrix` yerine `show_final` çağrısı yap):

```python
    def _show_match_result(self) -> None:
        # ... mevcut kod ...
        last = self._steps_data[-1]
        mat = last["matrix"]
        self._matrix_pair.show_final(mat)
        # ... geri kalan match sayfası gösterimi ...
```

`self._matrix.set_matrix(...)` çağrılarını `self._matrix_pair.show_final(...)` ile değiştir.

### - [ ] Step 3.5: Manuel görsel doğrulama

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python main_gui.py
```

1. AES animasyonunu aç (Alice paneli üzerinden)
2. Round 0 (AddRoundKey) ile başla — iki matrisin yan yana görünmesini ve "ÖNCEKİ → AddRoundKey → ŞİMDİKİ" şeritini doğrula
3. Animasyonda overlay henüz yok — beklenen davranış: `_TICKS_BY_OP["AddRoundKey"] = 60` tick (~2.4s) sonunda şimdiki matris after state'e snap eder
4. R1, R2 ▶ ile ilerle — her round'ta önceki/şimdiki matrislerin güncellendiğini doğrula
5. "⟲ Yeniden Oynat" butonuna tıkla — şimdiki matris animasyonu (snap) baştan oynar

### - [ ] Step 3.6: Tüm testler

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover 2>&1 | tail -3
```

Beklenen: 149 test PASS (mevcut tests etkilenmedi).

### - [ ] Step 3.7: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/aes_animation.py && git commit -m "kripto: AES penceresi yeni matris kapsayıcısına entegre edildi"
```

---

## Task 4: AddRoundKey Koreografisi

**Files:**
- Modify: `animation_modals/aes_matrix_view.py` (`_draw_overlay_addroundkey` doldur)

### - [ ] Step 4.1: Koreografi koduunu yaz

`animation_modals/aes_matrix_view.py` içindeki `_draw_overlay_addroundkey` metodunu bul (şu an `pass`). Şu kodla değiştir:

```python
    def _draw_overlay_addroundkey(self, p: QPainter, ox: int, oy: int) -> None:
        """AddRoundKey koreografisi — round_key sağdan kayar gelir,
        16 hücreye sırayla ⊕ sembolü ve sonuç değeri yerleşir.

        Faz haritası (toplam 60 tick):
          0–15 : KEY_REVEAL    — round_key sağdan kayarak gelir
          16–55: XOR_PER_ROW   — 4 satır × 10 tick, her satırda 4 hücre yanar
          56–59: FADEOUT       — round_key fade-out
        """
        if self._round_key is None:
            return

        t = self._tick
        accent = QColor(ANIM_COLORS["accent_peach"])

        # round_key overlay'in başlangıç ve son x pozisyonu
        rk_w = 4 * self._CELL_W + 3 * self._CELL_GAP
        rk_target_x = ox + rk_w + 16   # matrisin sağında, 16px gap
        rk_start_x = self.width() + 10
        if t <= 15:
            progress = t / 15.0
            rk_x = int(rk_start_x + (rk_target_x - rk_start_x) * progress)
            rk_alpha = progress
        elif t < 56:
            rk_x = rk_target_x
            rk_alpha = 1.0
        else:
            # Fadeout
            progress = (t - 55) / 5.0
            rk_x = rk_target_x
            rk_alpha = max(0.0, 1.0 - progress)

        # round_key 4×4 grid çiz
        for r in range(4):
            for c in range(4):
                cx, cy = self._cell_xy(rk_x, oy, r, c)
                self._draw_cell(
                    p, cx, cy, self._round_key[r][c],
                    bg=ANIM_COLORS["accent_peach"], border=ANIM_COLORS["accent_peach"],
                    alpha=rk_alpha * 0.35,
                )

        # Faz 2: sırayla hücreleri XOR
        if 16 <= t < 56:
            phase_t = t - 16  # 0..39
            cells_active = min(16, phase_t // 2 + 1)  # her 2 tick'te 1 yeni hücre
            for idx in range(cells_active):
                r = idx // 4
                c = idx % 4
                cx, cy = self._cell_xy(ox, oy, r, c)
                # Hücre üstüne ⊕ + sonuç (önceden _state'e yazıldı)
                # Görsel olarak vurgu: kalın çerçeve + üzerinde ⊕ rozeti
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(accent, 2))
                p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)
                # Mini ⊕ rozeti
                p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
                p.setPen(accent)
                p.drawText(QRect(cx + self._CELL_W - 14, cy + 2, 12, 12),
                           Qt.AlignmentFlag.AlignCenter, "⊕")
                # _state'i bu hücre için after değerine yükselt
                if (self._state[r][c] != self._after[r][c]):
                    self._state[r][c] = self._after[r][c]
```

### - [ ] Step 4.2: Smoke test ekle

`test_aes_matrix_view.py`'da `TestAESMatrixViewAnimation` sınıfının altına ekle:

```python
    def test_addroundkey_overlay_draws_without_error(self):
        """AddRoundKey overlay paint event'i hata vermeden çağrılır."""
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "AddRoundKey",
            [["00"] * 4 for _ in range(4)],
            [["FF"] * 4 for _ in range(4)],
            round_key=[["AA"] * 4 for _ in range(4)],
        )
        view._tick = 30  # XOR_PER_ROW fazı
        # Bir QPixmap'a render et — pixel doğrulamayız ama hata fırlamamalı
        pix = QPixmap(view.width(), view.height())
        p = QPainter(pix)
        view._draw_overlay(p, 24, 24)
        p.end()
```

### - [ ] Step 4.3: Testleri çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_aes_matrix_view -v
```

Beklenen: 18 test PASS.

### - [ ] Step 4.4: Manuel görsel doğrulama

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python main_gui.py
```

1. AES → Round 0 (AddRoundKey)
2. **Doğrula:**
   - 1.5 sn boyunca round_key matris sağdan kayarak gelir
   - 4 satır × 2 sn boyunca state hücrelerine sırayla ⊕ rozeti ve sonuç değeri belirir
   - Round_key matrisi fade-out olur
   - Şimdiki matris after state'e yerleşir
3. "⟲ Yeniden Oynat" butonu — animasyon baştan oynar

### - [ ] Step 4.5: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/aes_matrix_view.py test_aes_matrix_view.py && git commit -m "kripto: AddRoundKey koreografisi — round_key reveal + XOR per cell"
```

---

## Task 5: SubBytes Koreografisi

**Files:**
- Modify: `animation_modals/aes_matrix_view.py` (`_draw_overlay_subbytes` doldur)

### - [ ] Step 5.1: Koreografi koduunu yaz

`_draw_overlay_subbytes` metodunu bul, şu kodla değiştir:

```python
    def _draw_overlay_subbytes(self, p: QPainter, ox: int, oy: int) -> None:
        """SubBytes koreografisi — 16 hücre row-major sırayla S-Box dönüşümü.

        Hücre başına 4 tick (toplam 64):
          tick 0 : mavi çerçeve (aktif vurgu)
          tick 1 : 'S[xy]=zz' rozeti hücrenin üstünde
          tick 2 : hücre değeri eski → yeni (color flash turuncu→yeşil)
          tick 3 : rozet söner, vurgu kalır
        """
        t = self._tick
        cells_total = 16
        ticks_per_cell = 4

        cell_idx = min(cells_total - 1, t // ticks_per_cell)
        phase_t = t % ticks_per_cell

        accent_blue = QColor(ANIM_COLORS["accent_blue"])
        accent_peach = QColor(ANIM_COLORS["accent_peach"])
        accent_green = QColor(ANIM_COLORS["accent_green"])

        # Tamamlanmış önceki hücreleri yeni değerle güncelle
        for idx in range(cell_idx):
            r = idx // 4
            c = idx % 4
            self._state[r][c] = self._after[r][c]

        # Aktif hücre — vurgu + rozet
        ar = cell_idx // 4
        ac = cell_idx % 4
        cx, cy = self._cell_xy(ox, oy, ar, ac)

        # Vurgu çerçevesi (her zaman aktif hücrede)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(accent_blue, 2))
        p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

        # Hücre değeri color flash:
        # phase 0-1: turuncu (eski) → phase 2: yeşil (yeni)
        if phase_t >= 2:
            self._state[ar][ac] = self._after[ar][ac]
            flash_color = accent_green
        else:
            flash_color = accent_peach
        flash = QColor(flash_color)
        flash.setAlphaF(0.30)
        p.setBrush(QBrush(flash))
        p.setPen(QPen(flash_color, 1))
        p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

        # Rozet (phase 1-2): "S[xy]=zz"
        if 1 <= phase_t <= 2:
            before_val = self._before[ar][ac]
            after_val = self._after[ar][ac]
            p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
            p.setPen(accent_blue)
            badge_text = f"S[{before_val}]={after_val}"
            badge_y = cy - 14 if cy > 18 else cy + self._CELL_H + 2
            p.drawText(QRect(cx - 10, badge_y, self._CELL_W + 20, 14),
                       Qt.AlignmentFlag.AlignCenter, badge_text)
```

### - [ ] Step 5.2: Smoke test ekle

```python
    def test_subbytes_overlay_draws_without_error(self):
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "SubBytes",
            [[f"{r}{c}" for c in range(4)] for r in range(4)],
            [[f"S{r}{c}" for c in range(4)] for r in range(4)],
        )
        view._tick = 30
        pix = QPixmap(view.width(), view.height())
        p = QPainter(pix)
        view._draw_overlay(p, 24, 24)
        p.end()
```

### - [ ] Step 5.3: Testler

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_aes_matrix_view -v
```

Beklenen: 19 test PASS.

### - [ ] Step 5.4: Manuel görsel doğrulama

1. AES → Round 1'in SubBytes adımı
2. **Doğrula:** 16 hücre row-major sırayla mavi vurgu + "S[xx]=yy" rozeti + turuncu→yeşil color flash

### - [ ] Step 5.5: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/aes_matrix_view.py test_aes_matrix_view.py && git commit -m "kripto: SubBytes koreografisi — hücre hücre S-Box dönüşümü"
```

---

## Task 6: ShiftRows Koreografisi (En karmaşık)

**Files:**
- Modify: `animation_modals/aes_matrix_view.py` (`_draw_overlay_shiftrows` doldur)

### - [ ] Step 6.1: Koreografi koduunu yaz

`_draw_overlay_shiftrows` metodunu bul, şu kodla değiştir:

```python
    def _draw_overlay_shiftrows(self, p: QPainter, ox: int, oy: int) -> None:
        """ShiftRows koreografisi — 4 satır sırayla K bayt sola kayar.

        Faz haritası (toplam 80 tick):
          0–9  : Satır 0 vurgulanır, "sabit" etiketi
          10–29: Satır 1 — 1 bayt sola, ilk 10 tick hareket + wrap, son 10 oturur
          30–49: Satır 2 — 2 bayt sola
          50–69: Satır 3 — 3 bayt sola
          70–79: Final, vurgu söner
        """
        t = self._tick

        row_phases = [
            (0,  10, 0, 0),    # satır 0, sabit
            (10, 30, 1, 1),    # satır 1, shift 1
            (30, 50, 2, 2),    # satır 2, shift 2
            (50, 70, 3, 3),    # satır 3, shift 3
        ]

        accent = QColor(ANIM_COLORS["accent_blue"])
        muted = QColor(ANIM_COLORS["text_muted"])

        for r_start, r_end, row, shift in row_phases:
            if r_start <= t < r_end:
                phase_t = t - r_start
                phase_len = r_end - r_start

                # Aktif satırı vurgula
                for c in range(4):
                    cx, cy = self._cell_xy(ox, oy, row, c)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(accent, 2))
                    p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

                if shift == 0:
                    # "sabit" etiketi
                    if phase_t < 6:
                        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
                        p.setPen(muted)
                        row_y = oy + row * (self._CELL_H + self._CELL_GAP)
                        p.drawText(
                            QRect(ox + 4 * (self._CELL_W + self._CELL_GAP) + 4,
                                  row_y, 60, self._CELL_H),
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                            "sabit",
                        )
                else:
                    # Bayt hareketi animasyonu
                    progress = min(1.0, phase_t / (phase_len / 2))  # ilk yarıda hareket
                    after_row = self._after[row]
                    before_row = self._before[row]

                    if phase_t < phase_len / 2:
                        # İlk yarı: hareket
                        for c in range(4):
                            cx_orig, cy = self._cell_xy(ox, oy, row, c)
                            byte_val = before_row[c]
                            # Sol K bayt (c < shift): sol kenardan dışarı kayar
                            if c < shift:
                                offset = -int(self._CELL_W * progress * (shift - c))
                                cx_anim = cx_orig + offset
                                alpha = 1.0 - progress
                                self._draw_cell(
                                    p, cx_anim, cy, byte_val,
                                    bg=ANIM_COLORS["accent_blue"],
                                    border=ANIM_COLORS["accent_blue"],
                                    alpha=alpha * 0.6,
                                )
                                # Wrap iz: sağ kenardan giriyor
                                wrap_cx, _ = self._cell_xy(ox, oy, row, 4 - shift + c)
                                wrap_anim = wrap_cx + int(self._CELL_W * (1 - progress))
                                self._draw_cell(
                                    p, wrap_anim, cy, byte_val,
                                    bg=ANIM_COLORS["accent_blue"],
                                    border=ANIM_COLORS["accent_blue"],
                                    alpha=progress * 0.6,
                                )
                            else:
                                # Sağ kalan baytlar düz sola kayar
                                offset = -int(self._CELL_W * progress)
                                cx_anim = cx_orig + offset * shift
                                # Daha basit: shift kadar sola lerp
                                target_c = c - shift
                                target_x, _ = self._cell_xy(ox, oy, row, target_c)
                                cx_anim = int(cx_orig + (target_x - cx_orig) * progress)
                                self._draw_cell(
                                    p, cx_anim, cy, byte_val,
                                    bg=ANIM_COLORS["accent_blue"],
                                    border=ANIM_COLORS["accent_blue"],
                                    alpha=0.8,
                                )
                        # Aşağıdaki "snap" engellenir; orijinal _state'i gizle
                        # Bu satırın _state hücrelerini transparan kaplama ile sil
                        for c in range(4):
                            cx, cy = self._cell_xy(ox, oy, row, c)
                            mask = QColor(ANIM_COLORS["bg_card"])
                            mask.setAlphaF(1.0)
                            p.setBrush(QBrush(mask))
                            p.setPen(QPen(QColor(ANIM_COLORS["border"]), 1))
                            p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)
                            # ve animasyonlu kutuyu yeniden çiz
                    else:
                        # İkinci yarı: yerleşmiş after_row'u göster
                        for c in range(4):
                            self._state[row][c] = after_row[c]
```

**Not:** Bu çizim shift mantığı karmaşık — ShiftRows animasyonu QPainter-tabanlı sprite hareketinin en zor kısmı. Manuel görsel doğrulama sırasında "wrap" ve "düz kayma" görünümü beklendiği gibi olmazsa, koreografi'yi basitleştirmek için `_TICKS_BY_OP["ShiftRows"]` artırılabilir veya hareket yerine "anlık snap + ok overlay" yaklaşımına dönülebilir.

### - [ ] Step 6.2: Smoke test ekle

```python
    def test_shiftrows_overlay_draws_without_error(self):
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "ShiftRows",
            [[f"{r}{c}" for c in range(4)] for r in range(4)],
            [[f"{r}{(c+r)%4}" for c in range(4)] for r in range(4)],
        )
        for tick in (5, 20, 40, 60, 75):
            view._tick = tick
            pix = QPixmap(view.width(), view.height())
            p = QPainter(pix)
            view._draw_overlay(p, 24, 24)
            p.end()
```

### - [ ] Step 6.3: Testler

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_aes_matrix_view -v
```

Beklenen: 20 test PASS.

### - [ ] Step 6.4: Manuel görsel doğrulama (ÖZEL DİKKAT)

ShiftRows animasyonu en karmaşık ve görsel uygunluk en önemli. Manuel test:

1. AES → Round 1'in ShiftRows adımı
2. **Doğrula:**
   - Satır 0 (r0): "sabit" etiketi belirir, kısa süre sonra söner
   - Satır 1: 1 bayt sola hareket — sol kenardan 1 bayt şeffaflaşır, sağdan 1 bayt belirir
   - Satır 2: 2 bayt — aynı mantık
   - Satır 3: 3 bayt — aynı
   - Sonunda matris doğru after state'inde

Eğer görünüm beklenmeyen şekilde bozuksa, koreografi'yi basitleştirmek için Step 6.5'i yap.

### - [ ] Step 6.5: (KOŞULLU) Basitleştir — sadece görsel bozuksa

Eğer 6.4'te görünüm bozuksa, `_draw_overlay_shiftrows`'u şu basit versiyonla değiştir:

```python
    def _draw_overlay_shiftrows(self, p: QPainter, ox: int, oy: int) -> None:
        """Basitleştirilmiş ShiftRows — satır vurgusu + ok rozeti, sprite yok."""
        t = self._tick
        row_phases = [(0, 10, 0, 0), (10, 30, 1, 1), (30, 50, 2, 2), (50, 70, 3, 3)]
        accent = QColor(ANIM_COLORS["accent_blue"])
        for r_start, r_end, row, shift in row_phases:
            if r_start <= t < r_end:
                # Aktif satırı vurgula + after state'e zaten yerleştirildi
                for c in range(4):
                    cx, cy = self._cell_xy(ox, oy, row, c)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(accent, 2))
                    p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)
                # Satırın sağ kenarına ok rozeti
                row_y = oy + row * (self._CELL_H + self._CELL_GAP)
                p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
                p.setPen(accent)
                lbl = "sabit" if shift == 0 else f"← {shift} bayt"
                p.drawText(
                    QRect(ox + 4 * (self._CELL_W + self._CELL_GAP) + 4,
                          row_y, 80, self._CELL_H),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    lbl,
                )
                # _state'i adım adım after'a kaydır
                if r_start + (r_end - r_start) // 2 <= t:
                    for c in range(4):
                        self._state[row][c] = self._after[row][c]
```

### - [ ] Step 6.6: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/aes_matrix_view.py test_aes_matrix_view.py && git commit -m "kripto: ShiftRows koreografisi — satır kaydırma görselleştirmesi"
```

---

## Task 7: MixColumns Koreografisi

**Files:**
- Modify: `animation_modals/aes_matrix_view.py` (`_draw_overlay_mixcolumns` doldur)

### - [ ] Step 7.1: Koreografi koduunu yaz

`_draw_overlay_mixcolumns` metodunu bul, şu kodla değiştir:

```python
    def _draw_overlay_mixcolumns(self, p: QPainter, ox: int, oy: int) -> None:
        """MixColumns koreografisi — 4 sütun sırayla GF(2⁸) dönüşümü.

        Faz haritası (toplam 80 tick), sütun başına 20 tick:
          tick 0–4   : Sütun vurgusu (4 hücre çerçevesi sütun rengi)
          tick 5–14  : Sütun yanında formül balonu, 4 hücre tek tek güncellenir
          tick 15–19 : Balon söner
        """
        t = self._tick
        ticks_per_col = 20
        col_idx = min(3, t // ticks_per_col)
        phase_t = t % ticks_per_col

        col_colors = [
            ANIM_COLORS["accent_blue"],
            ANIM_COLORS["accent_mauve"],
            ANIM_COLORS["accent_yellow"],
            ANIM_COLORS["accent_peach"],
        ]
        col_color = QColor(col_colors[col_idx])

        # Tamamlanmış önceki sütunları kalıcı renkle çiz
        for completed_c in range(col_idx):
            cc = QColor(col_colors[completed_c])
            for r in range(4):
                cx, cy = self._cell_xy(ox, oy, r, completed_c)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(cc, 2))
                p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)
                self._state[r][completed_c] = self._after[r][completed_c]

        # Aktif sütun vurgusu
        for r in range(4):
            cx, cy = self._cell_xy(ox, oy, r, col_idx)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(col_color, 2))
            p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

        # Faz 2: 4 hücreyi sırayla yenisiyle değiştir
        if 5 <= phase_t < 15:
            rows_done = min(4, (phase_t - 5) // 2 + 1)
            for r in range(rows_done):
                self._state[r][col_idx] = self._after[r][col_idx]
                cx, cy = self._cell_xy(ox, oy, r, col_idx)
                # Color flash — yeşil
                flash = QColor(ANIM_COLORS["accent_green"])
                flash.setAlphaF(0.30)
                p.setBrush(QBrush(flash))
                p.setPen(QPen(QColor(ANIM_COLORS["accent_green"]), 1))
                p.drawRoundedRect(cx, cy, self._CELL_W, self._CELL_H, 4, 4)

        # Formül balonu (sütunun sağında)
        if 4 <= phase_t < 18:
            balloon_x = ox + 4 * (self._CELL_W + self._CELL_GAP) + 4
            balloon_y = oy + 4
            p.setFont(QFont("Courier New", 8))
            p.setPen(col_color)
            p.drawText(QRect(balloon_x, balloon_y, 120, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"Sütun {col_idx}: GF(2⁸) ×")
            p.drawText(QRect(balloon_x, balloon_y + 16, 120, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "2·a₀ ⊕ 3·a₁ ⊕")
            p.drawText(QRect(balloon_x, balloon_y + 32, 120, 14),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       "a₂ ⊕ a₃  (vb.)")
```

### - [ ] Step 7.2: Smoke test ekle

```python
    def test_mixcolumns_overlay_draws_without_error(self):
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "MixColumns",
            [[f"{r}{c}" for c in range(4)] for r in range(4)],
            [[f"M{r}{c}" for c in range(4)] for r in range(4)],
        )
        for tick in (10, 30, 50, 70):
            view._tick = tick
            pix = QPixmap(view.width(), view.height())
            p = QPainter(pix)
            view._draw_overlay(p, 24, 24)
            p.end()
```

### - [ ] Step 7.3: Testler

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_aes_matrix_view -v
```

Beklenen: 21 test PASS.

### - [ ] Step 7.4: Manuel görsel doğrulama

1. AES → Round 1'in MixColumns adımı
2. **Doğrula:**
   - 4 sütun sırayla (mavi, mor, sarı, şeftali) vurgu
   - Her sütun yanında "GF(2⁸) × 2·a₀ ⊕ ..." formül balonu
   - Her sütundaki 4 hücre yeşil flash ile teker teker güncellenir

### - [ ] Step 7.5: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add animation_modals/aes_matrix_view.py test_aes_matrix_view.py && git commit -m "kripto: MixColumns koreografisi — sütun sütun GF(2⁸) dönüşümü"
```

---

## Task 8: End-to-end Smoke Testler + Final Manuel Doğrulama

**Files:**
- Modify: `test_animation_smoke.py` (kapsam testleri)

### - [ ] Step 8.1: AES integration smoke testleri ekle

`test_animation_smoke.py` dosyasının altına (en altta, `if __name__` öncesi) ekle:

```python
class TestAESMatrixViewIntegration(unittest.TestCase):
    """AES penceresi yeni matris widget'ını kullanıyor mu?"""

    def test_module_imports(self):
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESMatrixView"))
        self.assertTrue(hasattr(aes_matrix_view, "_AESStateCompareWidget"))

    def test_aes_window_imports_compare_widget(self):
        """AES animasyon modülü _AESStateCompareWidget'ı import etmeli."""
        from animation_modals import aes_animation
        # _AESStateCompareWidget veya aes_matrix_view referansı olmalı
        import inspect
        source = inspect.getsource(aes_animation)
        self.assertIn("_AESStateCompareWidget", source)

    def test_aes_matrix_view_total_ticks_are_positive(self):
        from animation_modals.aes_matrix_view import _AESMatrixView
        for op, ticks in _AESMatrixView._TICKS_BY_OP.items():
            with self.subTest(op=op):
                self.assertGreater(ticks, 0, f"{op}: tick sayısı pozitif olmalı")
                self.assertLess(ticks, 200, f"{op}: tick sayısı makul olmalı (<200)")

    def test_aes_matrix_view_supports_all_four_ops(self):
        from animation_modals.aes_matrix_view import _AESMatrixView
        for op in ("AddRoundKey", "SubBytes", "ShiftRows", "MixColumns"):
            with self.subTest(op=op):
                self.assertIn(op, _AESMatrixView._TICKS_BY_OP)
```

### - [ ] Step 8.2: Testleri çalıştır

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest test_animation_smoke -v
```

Beklenen: tüm testler PASS.

### - [ ] Step 8.3: Tüm test suite

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python -m unittest discover 2>&1 | tail -5
```

Beklenen: en az 155 test PASS (132 mevcut + 21 yeni AES matris testi + 4 smoke).

### - [ ] Step 8.4: TAM uygulama testi — manuel

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && python main_gui.py
```

Tam akış:

1. Bir mesaj yaz, AES animasyonu aç
2. **Round 0 (AddRoundKey):**
   - Sol matris boş/başlangıç state'i, sağ matris animasyonu oynar
   - round_key sağdan kayarak gelir
   - 16 hücreye sırayla ⊕ rozeti ve sonuç değeri yerleşir
3. **Round 1 (SubBytes ▶):**
   - Sol matris Round 0 sonu, sağ matris SubBytes animasyonu
   - 16 hücre sırayla mavi vurgu + S-Box rozeti + color flash
4. **Round 1 (ShiftRows ▶):**
   - Sol matris SubBytes sonu, sağ matris ShiftRows
   - 4 satır sırayla shift animasyonu (basit veya sprite hareket)
5. **Round 1 (MixColumns ▶):**
   - 4 sütun sırayla GF(2⁸) animasyonu + formül balonları
6. **Round 1 (AddRoundKey ▶):**
   - AddRoundKey animasyonu Round 0 ile aynı şekilde
7. **R5 round bar butonuna tıkla — atla:**
   - Sol matris Round 4 sonu, sağ matris Round 5 animasyonu (yeni operasyon)
8. **"⟲ Yeniden Oynat" butonu:**
   - Son operasyonu baştan oynatır
9. **Round 14'e kadar ileri:**
   - Son adımda `_show_match_result` ile final hash gösterimi
   - İki matris aynı final state'i gösterir
10. **Regresyon kontrolü:**
    - SHA-256 animasyonunu da aç — beklenen davranış değişmemiş olmalı
    - RSA animasyonunu aç — değişmemiş olmalı

### - [ ] Step 8.5: Commit

```bash
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ" && git add test_animation_smoke.py && git commit -m "test: AES matris widget entegrasyon smoke testleri"
```

---

## Self-Review

**Spec coverage:**
- ✅ Bileşen 1 (`_AESMatrixView`) → Task 1
- ✅ Bileşen 2 (4 koreografi) → Task 4-7
- ✅ Bileşen 3 (`_AESStateCompareWidget`) → Task 2
- ✅ Bileşen 4 (AES penceresi entegrasyonu) → Task 3
- ✅ Test ve doğrulama planı → her görevde birim + manuel adım

**Placeholder scan:** Tüm görevlerde tam kod blokları, eksiksiz dosya yolları, çalıştırılabilir bash komutları var. Tek "koşullu" adım Task 6.5 — ShiftRows görsel olarak bozuksa basitleştirme önerisi; bu eklenmiş güvenlik mekanizması, plan eksikliği değil.

**Type/method consistency:**
- `_AESMatrixView.play_animation(operation, before, after, *, round_key=None, on_done=None)` — Task 1'de tanımlandı, Task 2'de `_AESStateCompareWidget.start_step` içinde aynı imzayla çağrıldı. ✓
- `_AESMatrixView.set_state(matrix)` — Task 1'de tanımlandı, Task 2 ve Task 3'te tüketildi. ✓
- `_AESMatrixView._TICKS_BY_OP` dict — Task 1'de tanımlandı, Task 4-7 koreografi metodları içinden tick sayılarını kullanır. Toplam tick sayıları (60/64/80/80) Task 1'de declared, Task 4-7'de implicit (faz makinesi içinden). ✓
- `_AESStateCompareWidget.start_step(op, before, after, op_color, *, round_key=None)` — Task 2'de tanımlandı, Task 3'te çağrıldı (`step["color"]` op_color olarak). ✓
- `_AESStateCompareWidget.show_final(final_state)` — Task 2'de tanımlandı, Task 3 Step 3.4'te çağrıldı. ✓

**Independent commit-ability:** Her görev kendi commit'i ile bağımsız uygulanabilir. Sıra önemli:
- Task 1 → Task 2: kapsayıcı view sınıfını kullanır
- Task 2 → Task 3: AES penceresi kapsayıcıyı kullanır
- Task 4-7: bağımsız (sıra serbest, herhangi biri Task 3'ten sonra)
- Task 8: tüm önceki görevlerin görsel doğrulamasını yapar
