"""
test_crypto_workers.py — QThread worker smoke testleri
======================================================
KeygenWorker, AliceSendWorker, BobReceiveWorker'lar QThread alt sınıflarıdır.

Test stratejisi: `worker.run()` doğrudan çağrılır — yeni bir thread spawn
edilmez. Aynı thread'de sinyal emit'leri DirectConnection ile slot'u
senkron olarak çağırır, bu yüzden Qt event loop'u (QCoreApplication.exec)
gerekmez.

Worker'lar sadece CryptoCore metodlarını çağırdığı için akış doğruluğu
zaten test_crypto_core.py'da kapsanmış; bu dosya yalnızca worker
sözleşmesini sınar: doğru sinyalin doğru argümanlarla emit edilmesi
ve hata durumunda failed sinyalinin kullanılması.
"""
import unittest

from cekirdek.crypto_core import CryptoCore, EncryptedPacket, RSAKeyPair
from cekirdek.crypto_workers import (
    AliceSendWorker,
    BobReceiveWorker,
    KeygenWorker,
)


class _SignalRecorder:
    """Worker sinyallerini Python listesine kaydedip iddialar için saklar."""

    def __init__(self, worker) -> None:
        self.ok_payloads: list[tuple] = []
        self.errors: list[Exception] = []
        worker.finished_ok.connect(self._on_ok)
        worker.failed.connect(self._on_failed)

    def _on_ok(self, *payload) -> None:
        self.ok_payloads.append(payload)

    def _on_failed(self, exc: Exception) -> None:
        self.errors.append(exc)


# ---------------------------------------------------------------------------
# KeygenWorker
# ---------------------------------------------------------------------------

class TestKeygenWorker(unittest.TestCase):
    """KeygenWorker — Alice ve Bob için RSA-2048 anahtar çiftleri üretir."""

    def test_constructs_without_error(self) -> None:
        crypto = CryptoCore()
        worker = KeygenWorker(crypto)
        self.assertIsNotNone(worker)
        self.assertTrue(hasattr(worker, "finished_ok"))
        self.assertTrue(hasattr(worker, "failed"))

    def test_run_emits_finished_ok_with_two_keypairs(self) -> None:
        """run() başarıyla iki RSAKeyPair üretip finished_ok emit etmeli."""
        crypto = CryptoCore()
        worker = KeygenWorker(crypto)
        recorder = _SignalRecorder(worker)

        worker.run()

        self.assertEqual(recorder.errors, [])
        self.assertEqual(len(recorder.ok_payloads), 1)
        alice_kp, bob_kp = recorder.ok_payloads[0]
        self.assertIsInstance(alice_kp, RSAKeyPair)
        self.assertIsInstance(bob_kp, RSAKeyPair)

    def test_run_populates_crypto_keys(self) -> None:
        """run() sonrasında CryptoCore üzerinde alice_keys ve bob_keys dolmalı."""
        crypto = CryptoCore()
        worker = KeygenWorker(crypto)
        self.assertIsNone(crypto.alice_keys)
        self.assertIsNone(crypto.bob_keys)

        worker.run()

        self.assertIsNotNone(crypto.alice_keys)
        self.assertIsNotNone(crypto.bob_keys)


# ---------------------------------------------------------------------------
# AliceSendWorker
# ---------------------------------------------------------------------------

class TestAliceSendWorker(unittest.TestCase):
    """AliceSendWorker — alice_send() iş akışını arka planda yürütür."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_constructs_with_message(self) -> None:
        worker = AliceSendWorker(self.crypto, "merhaba")
        self.assertIsNotNone(worker)

    def test_run_emits_packet_and_steps(self) -> None:
        """run() (EncryptedPacket, list[StepResult]) emit etmeli."""
        worker = AliceSendWorker(self.crypto, "test mesajı")
        recorder = _SignalRecorder(worker)

        worker.run()

        self.assertEqual(recorder.errors, [])
        self.assertEqual(len(recorder.ok_payloads), 1)
        packet, steps = recorder.ok_payloads[0]
        self.assertIsInstance(packet, EncryptedPacket)
        self.assertEqual(len(steps), 6)  # Alice akışı 6 adım

    def test_run_emits_failed_when_keys_missing(self) -> None:
        """setup_keys çağrılmadan run() → RuntimeError failed sinyali."""
        fresh_crypto = CryptoCore()  # anahtar yok
        worker = AliceSendWorker(fresh_crypto, "test")
        recorder = _SignalRecorder(worker)

        worker.run()

        self.assertEqual(recorder.ok_payloads, [])
        self.assertEqual(len(recorder.errors), 1)
        self.assertIsInstance(recorder.errors[0], RuntimeError)


# ---------------------------------------------------------------------------
# BobReceiveWorker
# ---------------------------------------------------------------------------

class TestBobReceiveWorker(unittest.TestCase):
    """BobReceiveWorker — bob_receive() iş akışını arka planda yürütür."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()
        self.message = "iletilen mesaj"
        self.packet, _ = self.crypto.alice_send(self.message)

    def test_constructs_with_packet(self) -> None:
        worker = BobReceiveWorker(self.crypto, self.packet)
        self.assertIsNotNone(worker)

    def test_run_emits_message_valid_steps(self) -> None:
        """run() (message, is_valid=True, list[StepResult]) emit etmeli."""
        worker = BobReceiveWorker(self.crypto, self.packet)
        recorder = _SignalRecorder(worker)

        worker.run()

        self.assertEqual(recorder.errors, [])
        self.assertEqual(len(recorder.ok_payloads), 1)
        msg, is_valid, steps = recorder.ok_payloads[0]
        self.assertEqual(msg, self.message)
        self.assertTrue(is_valid)
        self.assertEqual(len(steps), 5)  # Bob akışı 5 adım

    def test_run_emits_failed_on_corrupt_packet(self) -> None:
        """Tamamen boş paket çözülemez → failed sinyali."""
        bad_packet = EncryptedPacket(
            encrypted_message=b"",
            encrypted_session_key=b"",
            nonce=b"",
            associated_data=b"",
        )
        worker = BobReceiveWorker(self.crypto, bad_packet)
        recorder = _SignalRecorder(worker)

        worker.run()

        self.assertEqual(recorder.ok_payloads, [])
        self.assertEqual(len(recorder.errors), 1)

    def test_run_emits_failed_on_tampered_packet(self) -> None:
        """Bit-flip'lenmiş ciphertext → InvalidTag failed sinyali."""
        from cryptography.exceptions import InvalidTag

        tampered_ct = bytearray(self.packet.encrypted_message)
        tampered_ct[0] ^= 0xFF
        bad_packet = EncryptedPacket(
            encrypted_message=bytes(tampered_ct),
            encrypted_session_key=self.packet.encrypted_session_key,
            nonce=self.packet.nonce,
            associated_data=self.packet.associated_data,
        )
        worker = BobReceiveWorker(self.crypto, bad_packet)
        recorder = _SignalRecorder(worker)

        worker.run()

        self.assertEqual(recorder.ok_payloads, [])
        self.assertEqual(len(recorder.errors), 1)
        self.assertIsInstance(recorder.errors[0], InvalidTag)


if __name__ == "__main__":
    unittest.main()
