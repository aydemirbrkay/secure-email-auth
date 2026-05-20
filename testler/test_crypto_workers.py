"""
test_crypto_workers.py — kriptografi/crypto_workers QThread smoke testleri
========================================================================

Test türü: SMOKE TESTİ (Sinyal Sözleşmesi)

Amaç:
    UI'da uzun süren işlemleri (RSA-2048 anahtar üretimi ~1-2 sn,
    Alice gönderim, Bob alım) thread'e taşıyan QThread worker'larının
    sinyal–slot sözleşmesini doğrular. Worker'ların gerçek kripto akışını
    test etmek bu dosyanın işi DEĞİL — onu test_crypto_core.py kapsar.

Kapsam:
    - KeygenWorker: anahtar üretimi tamamlanınca finished sinyali iki
      RSAKeyPair argümanıyla emit edilir.
    - AliceSendWorker: send tamamlanınca finished sinyali (EncryptedPacket,
      StepResult listesi) emit eder.
    - BobReceiveWorker: receive tamamlanınca finished sinyali (mesaj,
      bool geçerli, StepResult listesi) emit eder.
    - Hata yolu: CryptoCore istisna fırlatırsa failed sinyali emit edilir
      (exception nesnesiyle birlikte).

Strateji:
    worker.run() doğrudan ana thread'de çağrılır — yeni thread spawn
    edilmez. DirectConnection ile sinyal emit'leri slot'u senkron çağırır,
    Qt event loop'u (QCoreApplication.exec) gerekmez. Bu sayede testler
    deterministik ve hızlıdır.

Hata durumunda anlamı: GUI'de "Anahtar Üret" butonu sonsuza dek dönen
spinner gösterir veya yanlış sinyal slot'larına bağlanır.
"""
import unittest

from kriptografi.crypto_core import CryptoCore, EncryptedPacket, RSAKeyPair
from kriptografi.crypto_workers import (
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
        """Alt tür: SMOKE (sınıf instance + sinyal varlığı).
        KeygenWorker instance edilir VE iki PyQt sinyali (finished_ok,
        failed) attribute olarak erişilebilir. Eksik sinyal → main_gui'de
        slot bağlanamaz → button hep disabled kalır."""
        crypto = CryptoCore()
        worker = KeygenWorker(crypto)
        self.assertIsNotNone(worker)
        self.assertTrue(hasattr(worker, "finished_ok"))
        self.assertTrue(hasattr(worker, "failed"))

    def test_run_emits_finished_ok_with_two_keypairs(self) -> None:
        """Alt tür: SMOKE (mutlu yol sinyal payload'ı).
        run() doğrudan çağrılır (thread yok); başarılı bitince
        finished_ok sinyali TAM 1 KEZ emit eder; payload (alice_kp, bob_kp)
        ikilisi — ikisi de RSAKeyPair tipinde. failed listesi boş kalır."""
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
        """Alt tür: SMOKE (yan etki kontratı).
        run() başarısı sadece sinyal emit etmekle kalmaz, CryptoCore
        instance'ı üzerinde alice_keys ve bob_keys attribute'larını DA
        doldurur. Bu yan etki sayesinde main_gui akışın geri kalanında
        crypto.alice_send() çağrısı çalışır."""
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
        """Alt tür: SMOKE (instance creation).
        AliceSendWorker instance edilirken mesaj parametresi alır;
        exception fırlatmamalı."""
        worker = AliceSendWorker(self.crypto, "merhaba")
        self.assertIsNotNone(worker)

    def test_run_emits_packet_and_steps(self) -> None:
        """Alt tür: SMOKE (mutlu yol sinyal payload'ı).
        run() başarılı bitince finished_ok payload'ı (EncryptedPacket,
        list[StepResult]) ikilisi olmalı. Alice akışı tam 6 adım
        içerir (SHA, RSA imza, birleştirme, oturum anahtarı, AES,
        RSA-OAEP); step sayısı bu kontratla sabittir."""
        worker = AliceSendWorker(self.crypto, "test mesajı")
        recorder = _SignalRecorder(worker)

        worker.run()

        self.assertEqual(recorder.errors, [])
        self.assertEqual(len(recorder.ok_payloads), 1)
        packet, steps = recorder.ok_payloads[0]
        self.assertIsInstance(packet, EncryptedPacket)
        self.assertEqual(len(steps), 6)  # Alice akışı 6 adım

    def test_run_emits_failed_when_keys_missing(self) -> None:
        """Alt tür: HATA YOLU (ön koşul ihlali).
        setup_keys() çağrılmadan run() → CryptoCore RuntimeError
        fırlatır → worker yakalar ve failed sinyali emit eder.
        Bu fırsatla finished_ok ASLA emit edilmemeli (sessiz başarı
        olmaz). main_gui kullanıcıya hata mesajı gösterir."""
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
        """Alt tür: SMOKE (instance creation).
        BobReceiveWorker instance edilirken EncryptedPacket alır."""
        worker = BobReceiveWorker(self.crypto, self.packet)
        self.assertIsNotNone(worker)

    def test_run_emits_message_valid_steps(self) -> None:
        """Alt tür: SMOKE (mutlu yol — uçtan uca round-trip).
        Alice'in gönderdiği paket Bob tarafından çözülünce finished_ok
        sinyali (message, is_valid=True, steps) payload'ı emit eder.
        Mesaj round-trip eşitliği (msg == sent_message) + imza
        doğrulama (is_valid=True) + 5 adım (RSA-OAEP, AES-GCM, ayrıştır,
        SHA hesap, RSA-PSS doğrula). End-to-end fonksiyonelliğin testi."""
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
        """Alt tür: HATA YOLU (tamamen geçersiz girdi).
        Tüm alanları boş bytes olan paket çözülürken kripto kütüphanesi
        hata fırlatır → worker failed sinyali emit eder; finished_ok
        ASLA emit edilmemeli. Defensive test — kötü niyetli/bozuk
        veriyi tespit etme."""
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
        """Alt tür: HATA YOLU (ortadaki adam saldırı simülasyonu).
        Ciphertext'in ilk byte'ı XOR 0xFF ile bit-flip'lenir →
        AES-GCM authentication tag eşleşmez → InvalidTag istisnası
        → failed sinyali. Bu testin başarısı, paketin bütünlük
        korumasının çalıştığının kanıtıdır."""
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
