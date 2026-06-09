# animation_modals/base.py
"""
CryptoAnimationWindow — Tüm animasyon pencerelerinin taban sınıfı.
QWidget subclass. on_close=None (varsayılan): bağımsız pencere olarak açılır, ekranın
%85'ine yeniden boyutlandırılır. on_close verilirse: gömülü widget olarak davranır
(pencere bayrağı ve boyut ayarı atlanır).
manual_mode=True: kullanıcı tıklayarak ilerler (RSA, SHA, AES roundları).
manual_mode=False: QTimer otomatik oynatır (AES intro).
"""
from __future__ import annotations
from collections.abc import Callable
from enum import Enum
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Paylaşılan tek renk kaynağı (arayuz.theme). Tema değişiminde yerinde güncellenir,
# bu yüzden animasyon pencereleri açıldıkları anda aktif temayı alır.
from arayuz.theme import (
    ANIM_COLORS,
    button_primary_style,
    button_secondary_style,
    progress_bar_style,
)


class AnimationSpeed(Enum):
    """Otomatik oynatma adım gecikmesi (ms). İç mantık bu Enum'u kullanır;
    UI'da gösterilen Türkçe etiketler ``SPEED_LABELS_TR`` üzerinden çözülür."""

    SLOW = 2000
    NORMAL = 1500
    FAST = 800


# Enum → kullanıcıya görünen Türkçe etiket. UI etiketleri Türkçe kalır,
# kod tarafı identifier'ları (Enum üyeleri) İngilizce'dir.
SPEED_LABELS_TR: dict[AnimationSpeed, str] = {
    AnimationSpeed.SLOW: "Yavaş",
    AnimationSpeed.NORMAL: "Normal",
    AnimationSpeed.FAST: "Hızlı",
}

# Türkçe etiket → Enum (ComboBox seçimini geri çözmek için ters harita).
_LABEL_TO_SPEED: dict[str, AnimationSpeed] = {
    label: speed for speed, label in SPEED_LABELS_TR.items()
}


# Navigasyon butonları (Geri/İleri/Kapat) yüksekliği. Birincil buton stili
# min-height:34 + padding ile ~50 px'e çıkar; gömülü panelde dikey yer
# kazanmak ve nav butonlarının kaydırmasız sığması için üst sınır koyulur.
_NAV_BTN_HEIGHT = 36


def _btn_style() -> str:
    # Birincil buton stili tek kaynaktan (arayuz.theme) gelir.
    return button_primary_style()


def _close_style() -> str:
    # İkincil/kapat butonu stili tek kaynaktan (arayuz.theme) gelir.
    return button_secondary_style()


class CryptoAnimationWindow(QWidget):
    """
    Ortak animasyon penceresi taban sınıfı.

    Alt sınıflar şunları override eder:
      _init_content()       → content_area'ya widget ekler
      _render_step(idx)     → idx numaralı adımı gösterir
      _show_match_result()  → son eşleşme ekranını gösterir

    manual_mode=True ise kullanıcı ◀ Geri / İleri ▶ butonlarıyla ilerler.
    manual_mode=False ise QTimer otomatik oynatır (hız seçici görünür).
    """

    def __init__(
        self,
        title: str,
        total_steps: int,
        manual_mode: bool = False,
        parent: QWidget | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_close = on_close

        # Standalone modda bağımsız pencere olarak aç
        if on_close is None:
            self.setWindowFlags(Qt.WindowType.Window)
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setWindowTitle(title)
        self.setStyleSheet(
            f"background-color: {ANIM_COLORS['bg_main']}; "
            f"color: {ANIM_COLORS['text_primary']};"
        )

        # Ekranın %85'i kadar boyutlandır — sadece standalone modda
        if on_close is None:
            screen = QApplication.primaryScreen()
            if screen:
                g = screen.availableGeometry()
                self.resize(int(g.width() * 0.82), int(g.height() * 0.85))
            else:
                self.resize(1280, 860)

        self.manual_mode: bool = manual_mode
        self.current_step: int = 0
        self.total_steps: int = total_steps
        self.speed_ms: int = AnimationSpeed.NORMAL.value

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)

        self._init_base_ui()
        self._init_content()

    # ------------------------------------------------------------------
    # UI kurulumu
    # ------------------------------------------------------------------

    def _init_base_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        self._header_lbl = QLabel(self.windowTitle())
        self._header_lbl.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        self._header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._header_lbl)

        self._progress = QProgressBar()
        self._progress.setMaximum(self.total_steps)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        layout.addWidget(self._progress)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_area, stretch=1)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        if self.manual_mode:
            self._btn_prev = QPushButton("◀  Geri")
            self._btn_prev.setEnabled(False)
            self._btn_prev.setFixedHeight(_NAV_BTN_HEIGHT)
            self._btn_prev.clicked.connect(self._go_back)
            controls.addWidget(self._btn_prev)

            self._btn_next = QPushButton("İleri  ▶")
            self._btn_next.setFixedHeight(_NAV_BTN_HEIGHT)
            self._btn_next.clicked.connect(self._advance_step)
            controls.addWidget(self._btn_next)
        else:
            self._speed_lbl = QLabel("Hız:")
            controls.addWidget(self._speed_lbl)

            self._speed_combo = QComboBox()
            self._speed_combo.addItems(list(SPEED_LABELS_TR.values()))
            self._speed_combo.setCurrentText(SPEED_LABELS_TR[AnimationSpeed.NORMAL])
            self._speed_combo.currentTextChanged.connect(self._on_speed_changed)
            controls.addWidget(self._speed_combo)

        controls.addStretch()

        self._btn_close = QPushButton("✕  Kapat")
        self._btn_close.setFixedHeight(_NAV_BTN_HEIGHT)
        if self._on_close is not None:
            self._btn_close.clicked.connect(self._on_close)
        else:
            self._btn_close.clicked.connect(self.close)
        controls.addWidget(self._btn_close)

        layout.addLayout(controls)

        self._apply_base_styles()

    def _apply_base_styles(self) -> None:
        """Pencere çerçevesi (chrome) stillerini aktif palete göre uygular."""
        self.setStyleSheet(
            f"background-color: {ANIM_COLORS['bg_main']}; "
            f"color: {ANIM_COLORS['text_primary']};"
        )
        self._header_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        self._progress.setStyleSheet(progress_bar_style())
        if hasattr(self, "_btn_prev"):
            self._btn_prev.setStyleSheet(_btn_style())
        if hasattr(self, "_btn_next"):
            self._btn_next.setStyleSheet(_btn_style())
        if hasattr(self, "_speed_lbl"):
            self._speed_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        if hasattr(self, "_speed_combo"):
            self._speed_combo.setStyleSheet(
                f"QComboBox {{ background: {ANIM_COLORS['bg_input']}; "
                f"color: {ANIM_COLORS['text_primary']}; "
                f"border: 1px solid {ANIM_COLORS['border']}; "
                f"border-radius: 4px; padding: 4px 8px; }}"
            )
        self._btn_close.setStyleSheet(_close_style())

    def refresh_theme(self) -> None:
        """Tema değişiminde pencereyi DURUMUNU BOZMADAN yeniden temalandırır.

        1) Chrome (başlık/progress/butonlar/arka plan) stilleri yeniden uygulanır.
        2) _restyle_content(): QLabel/QFrame tabanlı içerik stilleri yeniden
           uygulanır (alt sınıf override eder; mevcut render metotları çağrılır).
        3) update(): QPainter tabanlı içerik (ANIM_COLORS'u çizimde okuyan)
           canlı yeniden boyanır.

        İçerik YENİDEN KURULMAZ → animasyon durumu (round, timer, görünür adım)
        korunur; animasyon sıfırlanmaz/duraksamaz/iptal olmaz.
        """
        self._apply_base_styles()
        self._restyle_content()
        for w in self.findChildren(QWidget):
            w.update()

    def _restyle_content(self) -> None:
        """Alt sınıf, QLabel/QFrame tabanlı içerik stillerini burada yeniden
        uygular. Varsayılan: hiçbir şey (yalnız QPainter içerik varsa yeterli)."""
        pass

    # ------------------------------------------------------------------
    # Alt sınıf arayüzü
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        raise NotImplementedError

    def _render_step(self, step_idx: int) -> None:
        raise NotImplementedError

    def _show_match_result(self) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Navigasyon
    # ------------------------------------------------------------------

    def _on_speed_changed(self, text: str) -> None:
        # Türkçe etiket → Enum → ms süresi. UI etiketi Türkçe, iç mantık Enum.
        self.speed_ms = _LABEL_TO_SPEED[text].value
        if self._timer.isActive():
            self._timer.setInterval(self.speed_ms)

    def _go_back(self) -> None:
        """Manuel mod: bir önceki adıma dön."""
        if self.current_step <= 0:
            return
        self.current_step -= 1
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)
        self._btn_prev.setEnabled(self.current_step > 0)
        self._btn_next.setEnabled(True)
        self._btn_next.setText("İleri  ▶")

    def _advance_step(self) -> None:
        """Bir sonraki adıma geç (manuel veya otomatik)."""
        if self.manual_mode:
            if self.current_step >= self.total_steps - 1:
                self._progress.setValue(self.total_steps)
                self._show_match_result()
                self._btn_next.setEnabled(False)
                self._btn_next.setText("Tamamlandı")
                return
            self.current_step += 1
            self._render_step(self.current_step)
            self._progress.setValue(self.current_step + 1)
            if hasattr(self, "_btn_prev"):
                self._btn_prev.setEnabled(True)
        else:
            self.current_step += 1
            if self.current_step >= self.total_steps:
                self._timer.stop()
                self._progress.setValue(self.total_steps)
                self._show_match_result()
                return
            self._render_step(self.current_step)
            self._progress.setValue(self.current_step + 1)

    def _stop_timers(self) -> None:
        """Stop the base navigation timer. Subclasses should call super and stop their own timers."""
        self._timer.stop()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self.current_step == 0:
            self._render_step(0)
            self._progress.setValue(1)
            if not self.manual_mode:
                self._timer.start(self.speed_ms)
