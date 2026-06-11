"""
test_main_gui_worker_lifecycle.py — Worker yaşam döngüsü ve hata yolu regresyonları
====================================================================================

İnceleme bulguları A1/A2/A3 için regresyon testleri:

- A1: ``closeEvent`` çalışan worker'ları ``_finalize_worker`` ile sonlandırır.
- A3: bayat (eski generation) ``failed`` sinyali ``_on_crypto_error``'da yok sayılır.
- A2: güncel generation'lı ``send`` hatasında mesaj alanı + başlat butonu geri
  yüklenir; ``keygen`` hatasında başlat butonu disabled kalır.

QApplication, conftest.py'deki session ``qapp`` fixture'ı (autouse) ile hazırdır.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from PyQt6.QtGui import QCloseEvent

import main_gui


def _make_window() -> main_gui.MainWindow:
    return main_gui.MainWindow()


# ---------------------------------------------------------------------------
# A1 — closeEvent çalışan worker'ları sonlandırır
# ---------------------------------------------------------------------------

def test_close_event_finalizes_running_workers() -> None:
    win = _make_window()
    try:
        worker = MagicMock()
        worker.isRunning.return_value = True
        worker.wait.return_value = True  # 3 sn içinde bitti
        win._keygen_worker = worker

        win.closeEvent(QCloseEvent())

        # Worker beklenip silinmeli ve referansı temizlenmeli.
        worker.quit.assert_called_once()
        worker.wait.assert_called_once()
        worker.deleteLater.assert_called_once()
        assert win._keygen_worker is None
    finally:
        win.deleteLater()


# ---------------------------------------------------------------------------
# A3 — bayat (eski generation) hata yok sayılır
# ---------------------------------------------------------------------------

def test_stale_crypto_error_is_ignored(monkeypatch) -> None:
    win = _make_window()
    try:
        # Worker başlatılırken yakalanan generation'ı taklit et, sonra reset/yeni
        # işlemi temsilen generation'ı ilerlet → eski gen artık bayat.
        stale_gen = win._op_generation
        win._next_generation()

        # Gönderim başlamış gibi UI'ı kilitle.
        win._alice_panel.msg_input.setReadOnly(True)
        win._btn_start.setEnabled(False)

        # Hata diyaloğu ÇAĞRILMAMALI (bayat hata erken döner). Çağrılırsa
        # spy ile yakalarız (exec() de blokladığından testi de korur).
        spy = MagicMock()
        monkeypatch.setattr(main_gui, "CryptoErrorDialog", spy)

        win._on_crypto_error(RuntimeError("bayat"), gen=stale_gen, phase="send")

        spy.assert_not_called()  # diyalog gösterilmedi
        # UI'a dokunulmadı (kilit korunur, yeni worker referansları bozulmaz).
        assert win._alice_panel.msg_input.isReadOnly() is True
        assert win._btn_start.isEnabled() is False
    finally:
        win.deleteLater()


# ---------------------------------------------------------------------------
# A2 — güncel generation'lı hatada faz'a göre tam UI rollback
# ---------------------------------------------------------------------------

def test_send_error_restores_message_and_start(monkeypatch) -> None:
    win = _make_window()
    try:
        gen = win._op_generation  # güncel generation
        # Diyaloğun exec()'i bloklamasın — sahte diyalogla değiştir.
        fake_dialog = MagicMock()
        fake_dialog.exec.return_value = 0
        monkeypatch.setattr(
            main_gui, "CryptoErrorDialog", lambda *a, **k: fake_dialog
        )

        # _on_start'ın yaptığı kilitlemeyi taklit et.
        win._alice_panel.msg_input.setReadOnly(True)
        win._btn_start.setEnabled(False)
        win._btn_start.setText("Şifreleniyor…")

        win._on_crypto_error(RuntimeError("send patladı"), gen=gen, phase="send")

        # Kullanıcı Reset'siz tekrar gönderebilmeli.
        assert win._alice_panel.msg_input.isReadOnly() is False
        assert win._btn_start.isEnabled() is True
        assert win._btn_start.text() == "Şifreleme Başlat"
    finally:
        win.deleteLater()


def test_keygen_error_keeps_start_disabled(monkeypatch) -> None:
    win = _make_window()
    try:
        gen = win._op_generation
        fake_dialog = MagicMock()
        fake_dialog.exec.return_value = 0
        monkeypatch.setattr(
            main_gui, "CryptoErrorDialog", lambda *a, **k: fake_dialog
        )

        # Keygen fazında anahtar yok → başlat butonu disabled olmalı.
        win._btn_start.setEnabled(False)

        win._on_crypto_error(RuntimeError("keygen patladı"), gen=gen, phase="keygen")

        assert win._btn_start.isEnabled() is False
    finally:
        win.deleteLater()
