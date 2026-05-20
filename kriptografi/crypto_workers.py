"""
crypto_workers.py – QThread tabanlı kripto iş parçacıkları
==========================================================
RSA-2048 anahtar üretimi, Alice gönderim akışı ve Bob alım akışı
UI ana iş parçacığı yerine QThread worker'larında çalıştırılır.
Böylece kriptografik hesaplama süresince UI donmaz.

Her worker iki sinyal yayımlar:
  - ``finished_ok(*payload)``: başarı durumunda sonuçlar.
  - ``failed(exc)``: herhangi bir istisna durumunda, ``Exception``
    nesnesi ile birlikte. UI tarafı bu nesneyi
    ``utils.format_crypto_exception`` ile kullanıcı-dostu mesaja
    çevirebilir.

Tasarım notu — paylaşılan durum: ``CryptoCore`` objesi ana iş
parçacığında yaşar; worker yalnızca mevcut metodları çağırır.
``setup_keys`` anahtarları ``CryptoCore`` nesnesinin üstüne yazar
(kütüphanedeki mevcut sözleşme). Python GIL + Qt'nin sinyal-yuvası
mekanizması bu durumda main-thread ile worker arasında görünürlük
sorunu üretmez: ``finished_ok`` sinyalinin yuva çağrısı ana thread'in
event loop'u üzerinden işlendiğinde set işlemleri zaten görünür olur.
"""
from __future__ import annotations

from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from kriptografi.crypto_core import CryptoCore, EncryptedPacket, RSAKeyPair, StepResult


class KeygenWorker(QThread):
    """Alice ve Bob için RSA-2048 anahtar çiftlerini üretir (~1-2 sn)."""

    finished_ok = pyqtSignal(object, object)  # (alice_kp, bob_kp) → RSAKeyPair
    failed = pyqtSignal(Exception)

    def __init__(self, crypto: CryptoCore, parent=None) -> None:
        super().__init__(parent)
        self._crypto = crypto

    def run(self) -> None:  # noqa: D401 — QThread protocol
        try:
            alice_kp, bob_kp = self._crypto.setup_keys()
        except Exception as exc:   # noqa: BLE001 — UI'a taşınacak
            self.failed.emit(exc)
            return
        self.finished_ok.emit(alice_kp, bob_kp)


class AliceSendWorker(QThread):
    """Alice'in tam gönderim akışını arka planda yürütür."""

    finished_ok = pyqtSignal(object, list)  # (EncryptedPacket, list[StepResult])
    failed = pyqtSignal(Exception)

    def __init__(self, crypto: CryptoCore, message: str, parent=None) -> None:
        super().__init__(parent)
        self._crypto = crypto
        self._message = message

    def run(self) -> None:
        try:
            packet, steps = self._crypto.alice_send(self._message)
        except Exception as exc:   # noqa: BLE001
            self.failed.emit(exc)
            return
        self.finished_ok.emit(packet, steps)


class BobReceiveWorker(QThread):
    """Bob'un tam alım + doğrulama akışını arka planda yürütür."""

    finished_ok = pyqtSignal(str, bool, list)  # (message, is_valid, list[StepResult])
    failed = pyqtSignal(Exception)

    def __init__(self, crypto: CryptoCore, packet: EncryptedPacket, parent=None) -> None:
        super().__init__(parent)
        self._crypto = crypto
        self._packet = packet

    def run(self) -> None:
        try:
            message, is_valid, steps = self._crypto.bob_receive(self._packet)
        except Exception as exc:   # noqa: BLE001
            self.failed.emit(exc)
            return
        self.finished_ok.emit(message, is_valid, steps)
