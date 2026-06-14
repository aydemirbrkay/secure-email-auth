"""AES SubBytes adımı için ekranı dolduran S-Box referans diyaloğu."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..aes_pure import SBOX
from ..base import ANIM_COLORS
from .sbox_derivation import _SBoxDerivationWidget
from arayuz.theme import MANAGER


class _SBoxReferenceDialog(QDialog):
    """Sabit AES S-Box tablosunu mevcut SubBytes eşlemeleriyle açıklar."""

    def __init__(
        self,
        mappings: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mappings = [(source.lower(), result.lower()) for source, result in mappings]
        self._used_inputs = {source for source, _ in self._mappings}

        self._configure_window()
        self._build_ui()
        self._populate_table()
        self._highlight_used_cells()
        self._resize_to_available_screen()
        self.restyle()
        MANAGER.themeChanged.connect(self._on_theme_changed)
        self.finished.connect(self._disconnect_theme_signal)

    @property
    def used_inputs(self) -> set[str]:
        return set(self._used_inputs)

    def highlighted_cells(self) -> set[tuple[int, int]]:
        return {
            (int(source[0], 16), int(source[1], 16))
            for source in self._used_inputs
        }

    def _configure_window(self) -> None:
        self.setWindowTitle("AES S-Box Referans Tablosu")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.NonModal)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        self.rule_label = QLabel(
            "S-Box kullanımı: Girdi byte'ının ilk hex hanesi satırı, "
            "ikinci hex hanesi sütunu seçer."
        )
        self.rule_label.setWordWrap(True)
        self.rule_label.setFont(QFont("IBM Plex Sans", 10, QFont.Weight.Bold))
        layout.addWidget(self.rule_label)

        self.example_label = QLabel(self._example_text())
        self.example_label.setWordWrap(True)
        layout.addWidget(self.example_label)

        self.used_mappings_label = QLabel(self._used_mappings_text())
        self.used_mappings_label.setWordWrap(True)
        layout.addWidget(self.used_mappings_label)

        # Sayfa geçiş butonları: tablo ↔ "S-Box nasıl üretildi?" türetimi.
        nav_row = QHBoxLayout()
        self.show_table_btn = QPushButton("S-Box Tablosu")
        self.show_table_btn.clicked.connect(self.show_table_page)
        self.show_derivation_btn = QPushButton("S-Box nasıl üretildi?")
        self.show_derivation_btn.clicked.connect(self._show_default_derivation)
        nav_row.addWidget(self.show_table_btn)
        nav_row.addWidget(self.show_derivation_btn)
        nav_row.addStretch()
        layout.addLayout(nav_row)

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._build_table_page())
        self._stack.addWidget(self._build_derivation_page())
        layout.addWidget(self._stack, stretch=1)

    def _build_table_page(self) -> QWidget:
        """16×16 S-Box referans tablosunu taşıyan sayfayı kurar."""
        self.table_frame = QFrame(self)
        self.table_layout = QVBoxLayout(self.table_frame)
        self.table_layout.setContentsMargins(12, 10, 12, 12)
        self.table_layout.setSpacing(0)

        self.table = QTableWidget(16, 16, self.table_frame)
        self._table = self.table
        headers = [f"{index:X}" for index in range(16)]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setVerticalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setFixedHeight(30)
        self.table.verticalHeader().setFixedWidth(40)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table_layout.addWidget(self.table)
        return self.table_frame

    def _build_derivation_page(self) -> QWidget:
        """S-Box türetim sayfasını kurar: solda tıklanabilir girdi matrisi,
        sağda türetim animasyonu.

        Sol matristen bir byte seçmek o byte'ın türetimini baştan oynatır;
        böylece kullanıcı istediği değerin hesabını seçip izleyebilir ve
        animasyonu kaçırdıysa aynı değere dönüp yeniden görebilir.
        """
        self.derivation_frame = QFrame(self)
        outer = QHBoxLayout(self.derivation_frame)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(12)

        outer.addWidget(self._build_input_matrix(), stretch=0)

        self.derivation_widget = _SBoxDerivationWidget(self.derivation_frame)
        self.derivation_widget.set_mappings(self._mappings)
        outer.addWidget(self.derivation_widget, stretch=1)
        return self.derivation_frame

    def _build_input_matrix(self) -> QWidget:
        """Mesajın SubBytes girdi byte'larını tıklanabilir bir ızgara olarak kurar.

        Her hücre, o adımdaki benzersiz bir girdi byte'ını gösterir; tıklanınca
        ``show_derivation_for`` ile o byte'ın türetim animasyonu baştan oynar.
        Amaç: kullanıcı istediği değerin hesabını seçebilsin ve kaçırırsa geri
        dönüp tekrar izleyebilsin. Girdi yoksa kısa bir bilgi etiketi gösterilir.

        Dönüş: sol panele yerleştirilecek hazır ``QWidget``.
        """
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.input_matrix_title = QLabel("Girdi byte'ları\n(tıkla → hesabı izle)")
        self.input_matrix_title.setWordWrap(True)
        self.input_matrix_title.setFont(QFont("IBM Plex Sans", 9, QFont.Weight.Bold))
        lay.addWidget(self.input_matrix_title)

        self._input_buttons: list[tuple[int, QPushButton]] = []
        self._selected_input_byte: int | None = None
        self.input_empty_hint: QLabel | None = None

        inputs = list(dict.fromkeys(source for source, _ in self._mappings))
        if not inputs:
            self.input_empty_hint = QLabel(
                "Bu adımda girdi yok; varsayılan örnek gösteriliyor.")
            self.input_empty_hint.setWordWrap(True)
            self.input_empty_hint.setFont(QFont("IBM Plex Sans", 8))
            lay.addWidget(self.input_empty_hint)
        else:
            grid_host = QWidget()
            grid = QGridLayout(grid_host)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(4)
            cols = 4
            for idx, source in enumerate(inputs):
                byte = int(source, 16)
                btn = QPushButton(f"{byte:02x}")
                btn.setFixedSize(42, 34)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(
                    lambda _checked=False, b=byte: self._on_input_selected(b))
                self._input_buttons.append((byte, btn))
                grid.addWidget(btn, idx // cols, idx % cols)
            lay.addWidget(grid_host)

        lay.addStretch(1)
        panel.setFixedWidth(190)
        return panel

    def _on_input_selected(self, byte: int) -> None:
        """Girdi matrisinden seçilen byte'ın türetimini baştan oynatır.

        ``byte`` 0-255 arası girdi değeridir. Seçim, türetim widget'ını o byte'a
        kilitler (``show_derivation_for``) ve seçili hücreyi vurgular.
        """
        self._selected_input_byte = byte
        self.show_derivation_for(byte)
        self._style_input_buttons()

    def _style_input_buttons(self) -> None:
        """Girdi matrisi düğmelerini aktif temaya göre boyar; seçili byte vurgulu.

        Seçili hücre sarı zemin + koyu metinle ayrışır; diğerleri nötr zemin
        ve hover'da sarı kenarlık alır. Tema değişiminde de yeniden çağrılır.
        """
        for byte, btn in getattr(self, "_input_buttons", []):
            if byte == self._selected_input_byte:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {ANIM_COLORS['accent_yellow']}; "
                    f"color: {ANIM_COLORS['bg_main']}; "
                    f"border: 2px solid {ANIM_COLORS['accent_yellow']}; "
                    "border-radius: 5px; font-weight: bold; }}")
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {ANIM_COLORS['bg_input']}; "
                    f"color: {ANIM_COLORS['text_primary']}; "
                    f"border: 1px solid {ANIM_COLORS['border']}; "
                    "border-radius: 5px; font-weight: bold; }}"
                    f"QPushButton:hover {{ border: 1px solid "
                    f"{ANIM_COLORS['accent_yellow']}; }}")

    def _example_text(self) -> str:
        if not self._mappings:
            return "Bu adım için gösterilecek S-Box eşlemesi yok."
        source, result = self._mappings[0]
        row, col = source[0].upper(), source[1].upper()
        return (
            f"Bu adımın ilk örneği: {source} → satır {row}, sütun {col} "
            f"→ S[{row},{col}] = {result}"
        )

    def _used_mappings_text(self) -> str:
        unique = list(dict.fromkeys(self._mappings))
        summary = ", ".join(f"{source}→{result}" for source, result in unique)
        return f"Bu adımda kullanılan eşlemeler: {summary}"

    # ------------------------------------------------------------------
    # Sayfa geçişi ve S-Box türetimi anlatımı
    # ------------------------------------------------------------------

    def show_table_page(self) -> None:
        """Referans tablosu sayfasını gösterir ve türetim animasyonunu durdurur."""
        self.derivation_widget.stop()
        self._stack.setCurrentIndex(0)

    def show_derivation_for(self, byte: int) -> None:
        """Verilen byte'a kilitlenip türetim sayfasına geçer ve animasyonu başlatır."""
        self.derivation_widget.set_byte(byte)
        self.derivation_widget.start()
        self._stack.setCurrentIndex(1)

    def _show_default_derivation(self) -> None:
        """Türetim butonu için mesaj eşlemeleri arasında gezen animasyonu başlatır.

        Eşleme yoksa varsayılan byte (0x53) üzerinde durur; aksi halde
        kullanıcının mesajındaki SubBytes girdileri arasında otomatik gezer.
        """
        self.derivation_widget.set_mappings(self._mappings)
        self.derivation_widget.start()
        self._stack.setCurrentIndex(1)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Tablodaki bir hücreye tıklanınca o girdi byte'ının türetimini açar."""
        self.show_derivation_for(row * 16 + col)

    def _populate_table(self) -> None:
        for row in range(16):
            for col in range(16):
                item = QTableWidgetItem(f"{SBOX[row * 16 + col]:02x}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

    def _highlight_used_cells(self) -> None:
        """Bu adımda kullanılan tüm girdi hücrelerini aynı biçimde vurgular.

        Her vurgulu hücre sarı zemin + koyu metin alır; ilk eşleme dahil
        hiçbir hücre kalın/büyük yazıyla ayrıcalıklı gösterilmez.
        """
        for source in self._used_inputs:
            row, col = int(source[0], 16), int(source[1], 16)
            item = self.table.item(row, col)
            item.setBackground(QBrush(QColor(ANIM_COLORS["accent_yellow"])))
            item.setForeground(QBrush(QColor(ANIM_COLORS["bg_main"])))

    def _resize_to_available_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(900, 700)
            return
        available = screen.availableGeometry()
        target_width = min(1180, int(available.width() * 0.90))
        target_height = min(820, int(available.height() * 0.82))
        self.resize(target_width, target_height)

    def restyle(self) -> None:
        """Açık diyaloğu aktif uygulama temasına geçirir.

        Diyaloğun kendi kapsayıcı stili açıkça verilir; böylece parent
        (AES penceresi) stylesheet'inin etiketlere sızması (örn. kasıtsız
        mavi yuvarlak çerçeve) engellenir ve zemin ana uygulamayla aynı kalır.
        """
        self.setStyleSheet(
            f"QDialog {{ background: {ANIM_COLORS['bg_panel']}; }}"
            f"QLabel {{ background: transparent; border: none; }}"
        )
        self.rule_label.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self.example_label.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self.used_mappings_label.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self.table_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_primary']}; "
            f"gridline-color: {ANIM_COLORS['border']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; }}"
            f"QTableWidget::item {{ padding: 3px; }}"
            f"QHeaderView::section {{ background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_secondary']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; padding: 4px; }}"
            f"QTableCornerButton::section {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; }}"
        )
        self.derivation_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        self.derivation_widget.update()  # QPainter widget'ı yeni paletle yeniden boyanır.
        if hasattr(self, "input_matrix_title"):
            self.input_matrix_title.setStyleSheet(
                f"color: {ANIM_COLORS['text_secondary']};")
        if getattr(self, "input_empty_hint", None) is not None:
            self.input_empty_hint.setStyleSheet(
                f"color: {ANIM_COLORS['text_muted']};")
        self._style_input_buttons()
        self._highlight_used_cells()
        self.update()

    def _on_theme_changed(self, _mode: str) -> None:
        self.restyle()

    def _disconnect_theme_signal(self, _result: int) -> None:
        """Diyalog kapanınca tema sinyalini çözer ve türetim animasyonunu durdurur."""
        self.derivation_widget.stop()
        try:
            MANAGER.themeChanged.disconnect(self._on_theme_changed)
        except TypeError:
            pass
