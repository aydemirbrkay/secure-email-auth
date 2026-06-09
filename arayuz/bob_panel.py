"""
bob_panel.py – Alıcı (Bob) Panel Widget
"""
from __future__ import annotations

from typing import Optional

import logging
import os

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Diyagram Koordinat Haritası
# Koordinatlar 623×283 sanal uzayında; paintEvent widget boyutuna ölçekler.
# Gerçek görsel: 2752×1536 — ölçek: x/4.418, y/5.430
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_IMAGE_PATH = os.path.join(_PROJECT_ROOT, "görseller", "alice and bob.png")

# Alice diyagramı sanal koordinat uzayı (rect'lerin tanımlı olduğu boyut).
_DIAGRAM_VIRTUAL_WIDTH = 623
_DIAGRAM_VIRTUAL_HEIGHT = 283
# alice and bob.png kaynak görselinin gerçek piksel boyutu (kalibrasyon referansı).
_DIAGRAM_SOURCE_WIDTH = 2752
_DIAGRAM_SOURCE_HEIGHT = 1536
# Kaynak → sanal uzay ölçek katsayıları (yalnızca belge/doğrulama amaçlı; ~4.418 / ~5.430).
_DIAGRAM_SCALE_X = _DIAGRAM_SOURCE_WIDTH / _DIAGRAM_VIRTUAL_WIDTH
_DIAGRAM_SCALE_Y = _DIAGRAM_SOURCE_HEIGHT / _DIAGRAM_VIRTUAL_HEIGHT

# Geriye dönük kısa adlar (paintEvent ölçeklemesinde kullanılır).
_DIAGRAM_W = _DIAGRAM_VIRTUAL_WIDTH
_DIAGRAM_H = _DIAGRAM_VIRTUAL_HEIGHT

_BLINK_MS = 1000

# Alice'in 6 gönderme adımı için vurgulama alanları
# Koordinatlar 623×283 sanal uzayında; piksel kalibrasyonu 2752×1536 görselinden hesaplandı.
_STEP_RECTS: list[QRect] = [
    QRect(178, 100, 39, 19),  # 0: SHA-256 — H(·) kutusu
    QRect(223, 100, 39, 18),  # 1: RSA İmza — K_A^-(·) kutusu
    QRect(250, 124, 34, 23),  # 2: Birleştir — sol ⊕ dairesi
    QRect(363, 124, 39, 19),  # 3: AES — K_S(·) kutusu
    QRect(363, 174, 40, 22),  # 4: RSA Anahtar — K_B^+(·) kutusu
    QRect(437, 133, 178, 52), # 5: Gönder — sağ ⊕ + Internet bulutu
]

# Anahtar üretimi adımı için K_A^- ve K_B^+ ikon alanları
_KEYGEN_RECTS: list[QRect] = [
    QRect(210, 73, 62, 28),  # K_A^- etiket + anahtar ikonu (K_A^-(·) kutusunun üstü)
    QRect(354, 194, 62, 26), # K_B^+ etiket + anahtar ikonu (K_B^+(·) kutusunun altı)
]

_RED = QColor(198, 40, 40)            # #C62828 kenarlık (açık arka planda daha net)
_RED_FILL = QColor(198, 40, 40, 50)  # %20 şeffaf kırmızı dolgu
_GREEN_FILL = QColor(78, 139, 96, 50) # %20 şeffaf adaçayı dolgu


class DiagramWidget(QWidget):
    """Bob panelini tamamen kaplayan alice and bob.png görseli + adım vurgulama animasyonu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 150)

        self._pixmap = QPixmap()
        if os.path.isfile(_IMAGE_PATH):
            self._pixmap = QPixmap(_IMAGE_PATH)
        else:
            logger.warning("DiagramWidget: görsel bulunamadı → %s", _IMAGE_PATH)

        self._active_step: int = -1
        self._completed_steps: set[int] = set()
        self._blink_on: bool = False
        self._keygen_mode: bool = False

        self._timer = QTimer(self)
        self._timer.setInterval(_BLINK_MS)
        self._timer.timeout.connect(self._toggle_blink)

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------

    def show_keygen(self) -> None:
        """Anahtar üretimi: K_A^- ve K_B^+ ikon alanlarını yanıp söndür."""
        self._keygen_mode = True
        self._active_step = -1
        self._blink_on = True
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def set_active_step(self, idx: int) -> None:
        """Idx'i aktif (yanıp sönen) adım olarak ayarla ve timer'ı başlat."""
        self._keygen_mode = False
        self._active_step = idx
        self._blink_on = True
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def mark_step_done(self, idx: int) -> None:
        """Idx'i tamamlandı (yeşil) olarak işaretle."""
        self._completed_steps.add(idx)
        self.update()

    def stop_blink(self) -> None:
        """Timer'ı durdur, aktif adımı temizle."""
        self._timer.stop()
        self._active_step = -1
        self._keygen_mode = False
        self._blink_on = False
        self.update()

    def reset(self) -> None:
        """Tüm durumu başa döndür."""
        self._timer.stop()
        self._active_step = -1
        self._completed_steps.clear()
        self._keygen_mode = False
        self._blink_on = False
        self.update()

    # ------------------------------------------------------------------
    # İç Metodlar
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().closeEvent(event)

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.update()

    def _scaled_rect(self, r: QRect) -> QRect:
        """623×283 koordinat uzayındaki rect'i mevcut widget boyutuna ölçekler."""
        sx = self.width() / _DIAGRAM_W
        sy = self.height() / _DIAGRAM_H
        return QRect(round(r.x() * sx), round(r.y() * sy),
                     round(r.width() * sx), round(r.height() * sy))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            if not self._pixmap.isNull():
                painter.drawPixmap(self.rect(), self._pixmap)
            else:
                painter.fillRect(self.rect(), QColor(40, 40, 60))

            painter.setPen(Qt.PenStyle.NoPen)
            for idx in self._completed_steps:
                if 0 <= idx < len(_STEP_RECTS):
                    painter.fillRect(self._scaled_rect(_STEP_RECTS[idx]), _GREEN_FILL)

            if self._keygen_mode:
                for r in _KEYGEN_RECTS:
                    sr = self._scaled_rect(r)
                    if self._blink_on:
                        painter.fillRect(sr, _RED_FILL)
                    painter.setPen(QPen(_RED, 3))
                    painter.drawRect(sr)
            elif 0 <= self._active_step < len(_STEP_RECTS):
                sr = self._scaled_rect(_STEP_RECTS[self._active_step])
                if self._blink_on:
                    painter.fillRect(sr, _RED_FILL)
                painter.setPen(QPen(_RED, 3))
                painter.drawRect(sr)
        finally:
            painter.end()


# ---------------------------------------------------------------------------
# Bob Deşifreleme Diyagramı — alice panelinde gösterilir
# Koordinatlar 546×307 sanal uzayında; paintEvent widget boyutuna ölçekler.
# Gerçek görsel: 2730×1536 — ölçek: x/5, y/5
# ---------------------------------------------------------------------------

_BOB_IMAGE_PATH = os.path.join(_PROJECT_ROOT, "görseller", "bob-tarafi-sifre-cozme.png")

# Bob deşifreleme diyagramı sanal koordinat uzayı.
_BOB_DIAGRAM_VIRTUAL_WIDTH = 546
_BOB_DIAGRAM_VIRTUAL_HEIGHT = 307
# bob-tarafi-sifre-cozme.png kaynak görselinin gerçek piksel boyutu.
_BOB_DIAGRAM_SOURCE_WIDTH = 2730
_BOB_DIAGRAM_SOURCE_HEIGHT = 1536
# Kaynak → sanal uzay ölçek katsayıları (yalnızca belge/doğrulama amaçlı; ~5 / ~5).
_BOB_DIAGRAM_SCALE_X = _BOB_DIAGRAM_SOURCE_WIDTH / _BOB_DIAGRAM_VIRTUAL_WIDTH
_BOB_DIAGRAM_SCALE_Y = _BOB_DIAGRAM_SOURCE_HEIGHT / _BOB_DIAGRAM_VIRTUAL_HEIGHT

# Geriye dönük kısa adlar (paintEvent ölçeklemesinde kullanılır).
_BOB_DIAGRAM_W = _BOB_DIAGRAM_VIRTUAL_WIDTH
_BOB_DIAGRAM_H = _BOB_DIAGRAM_VIRTUAL_HEIGHT

# Bob'un 6 deşifreleme + doğrulama adımı için vurgulama alanları
# Piksel ölçümleri kenar tespitiyle doğrulanmıştır (bkz. bob-tarafi-sifre-cozme.png).
_BOB_STEP_RECTS: list[QRect] = [
    QRect(195, 118, 34, 20),  # 0: RSA Oturum Anahtarı Çözme — K_B^-(·) kutusu    (a)   px(976, 590, 170, 102)
    QRect(234, 163, 34, 20),  # 1: AES-256-GCM Deşifreleme   — K_S(·) kutusu      (b üst) px(1171, 815, 170, 102)
    QRect(283, 163, 17, 18),  # 2: Mesaj ve İmza Ayrıştırma  — + dairesi          (b alt) px(1415, 815, 85, 90)
    QRect(319, 135, 34, 20),  # 3: SHA-256 Yeniden Hesaplama — H(·) kutusu         (d)   px(1593, 673, 168, 102)
    QRect(319, 188, 34, 21),  # 4: RSA İmza Doğrulama        — K_A^+(·) kutusu    (c)   px(1596, 942, 171, 103)
    QRect(386, 158, 31, 27),  # 5: H(m) = H(m) Karşılaştırma — karşılaştırma kutusu      px(1927, 789, 154, 135)
]

# Karşılaştırma sonucuna göre dolgu renkleri — yeşil: geçerli, kırmızı: geçersiz
_SUCCESS_FILL = QColor(78, 139, 96, 110)   # koyu yeşil dolgu (başarı)
_FAILURE_FILL = QColor(198, 40, 40, 110)   # koyu kırmızı dolgu (başarısız)


class BobDecryptDiagramWidget(QWidget):
    """Alice panelinde gösterilen bob-tarafi-sifre-cozme.png + adım vurgulama animasyonu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 150)

        self._pixmap = QPixmap()
        if os.path.isfile(_BOB_IMAGE_PATH):
            self._pixmap = QPixmap(_BOB_IMAGE_PATH)
        else:
            logger.warning("BobDecryptDiagramWidget: görsel bulunamadı → %s", _BOB_IMAGE_PATH)

        self._active_step: int = -1
        self._completed_steps: set[int] = set()
        self._blink_on: bool = False
        # Karşılaştırma adımının (index 5) sonuç rengini ayrı tut:
        # None → henüz gösterilmedi, True → başarılı (yeşil), False → başarısız (kırmızı)
        self._comparison_result: bool | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(_BLINK_MS)
        self._timer.timeout.connect(self._toggle_blink)

    def set_active_step(self, idx: int) -> None:
        self._active_step = idx
        self._blink_on = True
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def mark_step_done(self, idx: int) -> None:
        self._completed_steps.add(idx)
        self.update()

    def show_comparison_result(self, is_valid: bool) -> None:
        """Karşılaştırma adımını (index 5) sonuç rengine göre kalıcı vurgula.

        Önceki aktif adımı (genellikle index 4) yeşil olarak tamamlanmış işaretler,
        karşılaştırma kutusunu başarılıysa yeşil, değilse kırmızı renkle boyar.
        Yanıp sönme durur ve kutu durağan bir sonuç göstergesine dönüşür.
        """
        self._timer.stop()
        self._active_step = -1
        self._blink_on = False
        self._completed_steps.add(4)
        self._comparison_result = bool(is_valid)
        self.update()

    def stop_blink(self) -> None:
        self._timer.stop()
        self._active_step = -1
        self._blink_on = False
        self.update()

    def reset(self) -> None:
        self._timer.stop()
        self._active_step = -1
        self._completed_steps.clear()
        self._blink_on = False
        self._comparison_result = None
        self.update()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().closeEvent(event)

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.update()

    def _scaled_rect(self, r: QRect) -> QRect:
        sx = self.width() / _BOB_DIAGRAM_W
        sy = self.height() / _BOB_DIAGRAM_H
        return QRect(round(r.x() * sx), round(r.y() * sy),
                     round(r.width() * sx), round(r.height() * sy))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            if not self._pixmap.isNull():
                painter.drawPixmap(self.rect(), self._pixmap)
            else:
                painter.fillRect(self.rect(), QColor(40, 40, 60))

            painter.setPen(Qt.PenStyle.NoPen)
            for idx in self._completed_steps:
                if 0 <= idx < len(_BOB_STEP_RECTS):
                    painter.fillRect(self._scaled_rect(_BOB_STEP_RECTS[idx]), _GREEN_FILL)

            # Karşılaştırma sonucu (adım 5) — durağan, sonuç rengiyle boya
            if self._comparison_result is not None:
                cmp_rect = self._scaled_rect(_BOB_STEP_RECTS[5])
                fill = _SUCCESS_FILL if self._comparison_result else _FAILURE_FILL
                border = QColor(78, 139, 96) if self._comparison_result else _RED
                painter.fillRect(cmp_rect, fill)
                painter.setPen(QPen(border, 3))
                painter.drawRect(cmp_rect)
                painter.setPen(Qt.PenStyle.NoPen)

            if 0 <= self._active_step < len(_BOB_STEP_RECTS):
                sr = self._scaled_rect(_BOB_STEP_RECTS[self._active_step])
                if self._blink_on:
                    painter.fillRect(sr, _RED_FILL)
                painter.setPen(QPen(_RED, 3))
                painter.drawRect(sr)
        finally:
            painter.end()


from kriptografi.crypto_core import EncryptedPacket, StepResult
from arayuz.widget_utils import build_step_content, make_step_box, style_step_box
from arayuz.theme import COLORS, STEP_COLORS_BOB, label_title_style


class BobPanel(QWidget):
    """Alıcı (Bob) paneli — sağ taraf.

    Kutucuk mantığı — dıştan içe deşifreleme:
      • Adım 1 (RSA Anahtar Çözme) en dışta — şifreli paket, en karmaşık.
      • Her yeni adım bir öncekinin içine eklenir; içe girdikçe sadeleşir.
      • Adım 5 (İmza Doğrulama) en içte — doğrulanmış orijinal mesaj.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._steps: list[StepResult] = []
        self._current_step: int = 0
        self._step_widgets: list[QGroupBox] = []
        self._diagram_widget: DiagramWidget | None = None
        self._btn_close_diagram: QPushButton | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._title_widget = QWidget()
        _th = QHBoxLayout(self._title_widget)
        _th.setContentsMargins(0, 0, 0, 0)
        _th.setSpacing(0)
        _th.addStretch()
        self._title_label = QLabel("Alıcı — Bob")
        self._title_label.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        _th.addWidget(self._title_label)
        _th.addStretch()
        layout.addWidget(self._title_widget)

        # --- Diyagram Container (Alice fazında görünür) ---
        self._diagram_container = QWidget()
        self._diagram_container.setVisible(False)
        diag_layout = QVBoxLayout(self._diagram_container)
        diag_layout.setContentsMargins(0, 0, 0, 4)
        diag_layout.setSpacing(4)

        self._diagram_widget = DiagramWidget()
        diag_layout.addWidget(self._diagram_widget)

        self._btn_close_diagram = QPushButton("✖  Kapat")
        self._btn_close_diagram.setEnabled(False)
        self._btn_close_diagram.setFixedHeight(32)
        self._btn_close_diagram.clicked.connect(self._on_close_diagram)
        diag_layout.addWidget(self._btn_close_diagram)

        layout.addWidget(self._diagram_container, stretch=1)
        # --- Diyagram Container sonu ---

        self._received_group = QGroupBox("Alınan Şifreli Paket")
        recv_layout = QVBoxLayout(self._received_group)
        self._received_label = QLabel("Henüz bir paket alınmadı.")
        self._received_label.setWordWrap(True)
        recv_layout.addWidget(self._received_label)
        layout.addWidget(self._received_group)

        self._cumulative_area = QWidget()
        self._cumulative_layout = QVBoxLayout(self._cumulative_area)
        self._cumulative_layout.setContentsMargins(0, 0, 0, 0)
        self._cumulative_layout.setSpacing(6)

        self._nested_container = QVBoxLayout()
        self._cumulative_layout.addLayout(self._nested_container)
        self._cumulative_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(self._cumulative_area)
        self._scroll_area.setStyleSheet("background-color: transparent;")
        layout.addWidget(self._scroll_area, stretch=1)

        self._result_group = QGroupBox("Doğrulama Sonucu")
        result_layout = QVBoxLayout(self._result_group)
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        result_layout.addWidget(self._result_label)
        self._result_group.setVisible(False)
        layout.addWidget(self._result_group)

        self.status_label = QLabel("Alice'den paket bekleniyor...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self._apply_styles()

    def _apply_styles(self) -> None:
        """Renk taşıyan stilleri aktif palete göre (yeniden) uygular."""
        c = COLORS
        self._title_label.setStyleSheet(label_title_style("accent_green"))
        _muted = f"color: {c['text_secondary']}; font-size: 12px;"
        self._received_label.setStyleSheet(_muted)
        self.status_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: 12px; padding: 4px;"
        )
        self._btn_close_diagram.setStyleSheet(
            f"QPushButton {{ background: rgba(217,85,85,0.12); "
            f"border: 2px solid {c['accent_red']}; border-radius: 6px; "
            f"color: {c['accent_red']}; font-weight: bold; font-size: 12px; }}"
            f"QPushButton:hover {{ background: rgba(217,85,85,0.28); }}"
            f"QPushButton:disabled {{ background: {c['bg_card']}; "
            f"border: 1px solid {c['border']}; color: {c['text_muted']}; }}"
        )
        # Mevcut adım kutularını da aktif temaya göre yeniden stillendir
        for i, box in enumerate(self._step_widgets):
            style_step_box(box, STEP_COLORS_BOB[i % len(STEP_COLORS_BOB)])

    # ------------------------------------------------------------------
    # Diyagram API
    # ------------------------------------------------------------------

    def show_keygen_step(self) -> None:
        """RSA anahtar üretimi sırasında diyagramı göster, K_A^- ve K_B^+ vurgula."""
        self._title_widget.setVisible(False)
        self._received_group.setVisible(False)
        self._scroll_area.setVisible(False)
        self.status_label.setVisible(False)
        self._diagram_container.setVisible(True)
        self._diagram_widget.show_keygen()

    def show_diagram(self) -> None:
        """Alice fazı başladığında diyagramı keygen'den temizle ve adım moduna geç."""
        self._diagram_widget.reset()
        self._title_widget.setVisible(False)
        self._received_group.setVisible(False)
        self._scroll_area.setVisible(False)
        self.status_label.setVisible(False)
        self._diagram_container.setVisible(True)

    def set_diagram_step(self, step_idx: int) -> None:
        """Önceki adımı yeşil yap, step_idx'i kırmızı blink ile vurgula."""
        if step_idx > 0:
            self._diagram_widget.mark_step_done(step_idx - 1)
        self._diagram_widget.set_active_step(step_idx)

    def enable_close_button(self) -> None:
        """Alice'in son adımı tamamlandıktan sonra Kapat butonunu aktif et."""
        self._btn_close_diagram.setEnabled(True)

    def _on_close_diagram(self) -> None:
        """Kapat butonuna basıldığında diyagramı gizle, Bob içeriğini geri getir."""
        self._diagram_widget.stop_blink()
        self._diagram_container.setVisible(False)
        self._title_widget.setVisible(True)
        self._received_group.setVisible(True)
        self._scroll_area.setVisible(True)
        self.status_label.setVisible(True)

    def reset(self) -> None:
        self._diagram_widget.reset()
        self._diagram_container.setVisible(False)
        self._btn_close_diagram.setEnabled(False)
        self._title_widget.setVisible(True)
        self._received_group.setVisible(True)
        self._scroll_area.setVisible(True)
        self.status_label.setVisible(True)
        self._steps = []
        self._current_step = 0
        self._step_widgets.clear()
        while self._nested_container.count():
            item = self._nested_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._received_label.setText("Henüz bir paket alınmadı.")
        self._result_label.setText("")
        self._result_group.setVisible(False)
        self.status_label.setText("Alice'den paket bekleniyor...")

    def set_packet_info(self, packet: EncryptedPacket) -> None:
        aad_display = packet.associated_data.decode("ascii", errors="replace")
        info = (
            f"Şifreli mesaj boyutu: {len(packet.encrypted_message)} byte\n"
            f"Şifreli oturum anahtarı: {len(packet.encrypted_session_key)} byte\n"
            f"Rastgele Sayı (Nonce): {packet.nonce.hex()[:32]}…\n"
            f"AAD (Authenticated Metadata): {aad_display}"
        )
        self._received_label.setText(info)
        self._received_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;"
        )

    def set_steps(self, steps: list[StepResult]) -> None:
        self._steps = steps
        self._current_step = 0
        self._step_widgets.clear()
        while self._nested_container.count():
            item = self._nested_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @property
    def current_step(self) -> int:
        """Bir sonraki gösterilecek adımın indeksi (0 tabanlı).

        Dışarıdan akış kararı verirken ``_current_step`` private alanına
        erişmek yerine bu public property kullanılır.
        """
        return self._current_step

    def peek_next_step(self) -> Optional[StepResult]:
        """Bir sonraki adımı gerçekleştirmeden döndürür; sonda ``None``.

        ``show_next_step()`` çağrılmadan, sırada hangi adımın olduğunu
        öğrenmek için kullanılır. Durumu değiştirmez.
        """
        if self._current_step >= len(self._steps):
            return None
        return self._steps[self._current_step]

    def show_next_step(self) -> bool:
        """Sonraki adımı içe-sararak kümülatif gösterir.

        Her yeni adım bir öncekinin içine eklenir (içe-sarma):
        Adım 1 en dışta (en karmaşık) → Adım 5 en içte (doğrulanmış mesaj).
        """
        if self._current_step >= len(self._steps):
            return False

        step = self._steps[self._current_step]
        color = STEP_COLORS_BOB[self._current_step % len(STEP_COLORS_BOB)]
        content = build_step_content(step)
        box = make_step_box(
            f"Adım {step.step_number}: {step.step_name}",
            content,
            color,
        )
        self._step_widgets.append(box)

        if self._current_step == 0:
            self._nested_container.addWidget(box)
        else:
            prev_box = self._step_widgets[self._current_step - 1]
            prev_box.layout().addWidget(box)

        self._current_step += 1
        self.status_label.setText(
            f"✅ Adım {step.step_number}/{len(self._steps)} tamamlandı: {step.step_name}"
        )
        return self._current_step < len(self._steps)
