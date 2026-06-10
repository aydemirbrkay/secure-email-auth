"""AES SubBytes adımı için ekranı dolduran S-Box referans diyaloğu."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
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

from ..aes_pure import SBOX, derive_sbox_value
from ..base import ANIM_COLORS
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
        """Seçilen byte'ın S-Box türetim adımlarını gösteren sayfayı kurar."""
        self.derivation_frame = QFrame(self)
        derivation_layout = QVBoxLayout(self.derivation_frame)
        derivation_layout.setContentsMargins(16, 14, 16, 16)
        derivation_layout.setSpacing(8)

        self.derivation_label = QLabel("")
        self.derivation_label.setWordWrap(True)
        self.derivation_label.setTextFormat(Qt.TextFormat.RichText)
        self.derivation_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        derivation_layout.addWidget(self.derivation_label, stretch=1)
        return self.derivation_frame

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
        """Referans tablosu sayfasını gösterir."""
        self._stack.setCurrentIndex(0)

    def show_derivation_for(self, byte: int) -> None:
        """Verilen byte'ın S-Box türetimini açıklayıp türetim sayfasına geçer.

        Çarpımsal ters ve affine dönüşüm adımlarını öğrenci diline indirgenmiş
        biçimde ``derivation_label`` içine yazar ve sayfayı değiştirir.
        """
        self.derivation_label.setText(self._derivation_text(byte))
        self._stack.setCurrentIndex(1)

    def _show_default_derivation(self) -> None:
        """Türetim butonu için varsayılan örneği (ilk eşleme ya da 0x53) açar."""
        default = int(self._mappings[0][0], 16) if self._mappings else 0x53
        self.show_derivation_for(default)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Tablodaki bir hücreye tıklanınca o girdi byte'ının türetimini açar."""
        self.show_derivation_for(row * 16 + col)

    def _derivation_text(self, byte: int) -> str:
        """Bir byte'ın S-Box değerine türetilişini HTML metin olarak üretir."""
        d = derive_sbox_value(byte)
        inverse_note = (
            "0x00'ın çarpımsal tersi yoktur; AES sözleşmesi gereği 0 alınır."
            if byte == 0
            else f"GF(2⁸) gövdesinde {byte:02x} · {d.inverse:02x} = 01 "
            f"olduğu için tersi <b>{d.inverse:02x}</b>'dir."
        )
        return (
            f"<h3>S-Box değeri nasıl üretilir? (örnek: {byte:02x})</h3>"
            "S-Box sabit bir tablo değildir; her byte iki adımla üretilir.<br><br>"
            "<b>Adım 1 — Çarpımsal ters (GF(2⁸))</b><br>"
            f"{inverse_note}<br>"
            f"İndirgenemez polinom: 0x11B.<br><br>"
            "<b>Adım 2 — Affine dönüşüm</b><br>"
            f"Ters değer ({d.inverse:02x}) bit-döndürmeli XOR ve "
            f"<code>{d.affine_const:02x}</code> sabitiyle birleştirilir.<br><br>"
            f"<b>Sonuç:</b> S[{byte >> 4:X},{byte & 0xF:X}] = "
            f"<b>{d.result:02x}</b>"
        )

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
        self.derivation_label.setStyleSheet(
            f"color: {ANIM_COLORS['text_primary']};"
        )
        self._highlight_used_cells()
        self.update()

    def _on_theme_changed(self, _mode: str) -> None:
        self.restyle()

    def _disconnect_theme_signal(self, _result: int) -> None:
        try:
            MANAGER.themeChanged.disconnect(self._on_theme_changed)
        except TypeError:
            pass
