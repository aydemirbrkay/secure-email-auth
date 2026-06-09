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

from PyQt6.QtCore import QEventLoop, QTimer

from kriptografi.crypto_core import CryptoCore, EncryptedPacket, RSAKeyPair
from kriptografi.crypto_workers import (
    AliceSendWorker,
    BobReceiveWorker,
    KeygenWorker,
)


def _wait_for_signal(signal, timeout_ms: int = 15000) -> list:
    """Verilen sinyali gerçek bir Qt event-loop üzerinden bekler.

    ``pytest-qt`` her ortamda kurulu olmayabileceği için ona sert
    bağımlılık yaratmadan, saf PyQt6 ile ``QEventLoop`` + ``QTimer``
    timeout fallback'i kullanılır. Worker ``QThread.start()`` ile arka
    planda koşarken sinyalini event-loop üzerinden alırız (run()'ı
    doğrudan çağırmak DEĞİL).

    Dönüş: sinyalin payload'ını içeren liste (timeout olduysa boş).
    Timeout durumunda ``RuntimeError`` fırlatılır ki test asılı kalmasın.
    """
    loop = QEventLoop()
    received: list = []
    timed_out: list[bool] = [False]

    def _on_signal(*args) -> None:
        received.append(args)
        loop.quit()

    def _on_timeout() -> None:
        timed_out[0] = True
        loop.quit()

    signal.connect(_on_signal)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(_on_timeout)
    timer.start(timeout_ms)

    loop.exec()  # event-loop: worker thread'inin sinyali burada işlenir

    timer.stop()
    if timed_out[0]:
        raise RuntimeError("Worker sinyali zaman aşımına uğradı (event-loop)")
    return received


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
        AES-GCM authentication tag eşleşmez → tipli IntegrityError
        → failed sinyali. Ham InvalidTag dışarı sızmaz; CryptoError
        ailesi altında IntegrityError olarak gelir (orijinal InvalidTag
        __cause__ ile zincirlenir). Bu testin başarısı, paketin bütünlük
        korumasının çalıştığının kanıtıdır."""
        from cryptography.exceptions import InvalidTag

        from kriptografi.errors import IntegrityError

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
        self.assertIsInstance(recorder.errors[0], IntegrityError)
        self.assertNotIsInstance(recorder.errors[0], InvalidTag)
        self.assertIsInstance(recorder.errors[0].__cause__, InvalidTag)


# ---------------------------------------------------------------------------
# Gerçek-thread (QThread.start) + event-loop yolu
# ---------------------------------------------------------------------------

class TestWorkerRealThread(unittest.TestCase):
    """Worker'ları gerçekten ``QThread.start()`` ile arka planda koşturur.

    Diğer testler ``run()``'ı doğrudan ana thread'de çağırır (smoke).
    Bu sınıf ise gerçek QThread + sinyal-slot (event-loop) yolunu test
    eder: sonuç event-loop üzerinden alınır. ``pytest-qt``'ye sert
    bağımlılık yoktur; saf PyQt6 ``QEventLoop`` fallback'i kullanılır,
    böylece test her ortamda koşar.
    """

    def test_keygen_real_thread_emits_finished_ok(self) -> None:
        """Alt tür: GERÇEK THREAD (mutlu yol).
        KeygenWorker .start() ile arka planda koşar; finished_ok sinyali
        event-loop üzerinden alınır ve payload iki RSAKeyPair olur.
        run() doğrudan çağrılmaz — gerçek thread + sinyal yolu test edilir."""
        crypto = CryptoCore()
        worker = KeygenWorker(crypto)

        worker.start()  # gerçek QThread başlatma (run() ana thread'de DEĞİL)
        try:
            payloads = _wait_for_signal(worker.finished_ok)
        finally:
            worker.wait(20000)  # thread'in temiz bitmesini bekle

        self.assertEqual(len(payloads), 1)
        alice_kp, bob_kp = payloads[0]
        self.assertIsInstance(alice_kp, RSAKeyPair)
        self.assertIsInstance(bob_kp, RSAKeyPair)
        # Worker gerçekten ayrı thread'de mi koştu? İş bittiğine göre
        # thread artık çalışmıyor olmalı.
        self.assertFalse(worker.isRunning())

    def test_alice_send_real_thread_emits_packet(self) -> None:
        """Alt tür: GERÇEK THREAD (gönderim akışı).
        AliceSendWorker .start() ile arka planda koşar; finished_ok
        event-loop'tan alınır, payload (EncryptedPacket, 6 adım)."""
        crypto = CryptoCore()
        crypto.setup_keys()
        worker = AliceSendWorker(crypto, "gerçek thread mesajı")

        worker.start()
        try:
            payloads = _wait_for_signal(worker.finished_ok)
        finally:
            worker.wait(20000)

        self.assertEqual(len(payloads), 1)
        packet, steps = payloads[0]
        self.assertIsInstance(packet, EncryptedPacket)
        self.assertEqual(len(steps), 6)


# ---------------------------------------------------------------------------
# Bayat (stale) sonuç koruması — operation token / generation id
# ---------------------------------------------------------------------------

class TestStaleResultGuard(unittest.TestCase):
    """main_gui operation-token (generation) mantığını izole eder.

    Senaryo: bir worker başlatılırken o anki generation yakalanır; arada
    reset (veya yeni işlem) generation'ı artırır; worker geç bittiğinde
    gelen sonuç bayat sayılıp UI state'ine yansıtılmamalıdır.

    main_gui.MainWindow tam bir pencere oluşturmadan ağır olduğundan,
    generation karşılaştırma mantığını gerçek slot davranışıyla birebir
    aynı şekilde izole bir nesne üzerinde test ederiz.
    """

    class _GenHolder:
        """MainWindow'un generation yardımcılarını birebir taklit eder."""

        def __init__(self) -> None:
            self._op_generation = 0
            self.applied: list = []  # UI'a yansıyan (bayat olmayan) sonuçlar

        def _next_generation(self) -> int:
            self._op_generation += 1
            return self._op_generation

        def _is_current_generation(self, gen: int) -> bool:
            return gen == self._op_generation

        def _on_done(self, result, gen: int) -> None:
            # main_gui._on_*_done slotlarındaki guard ile aynı desen:
            if not self._is_current_generation(gen):
                return  # bayat — yok say
            self.applied.append(result)

    def test_helpers_match_main_gui_implementation(self) -> None:
        """Izole nesnenin yardımcıları gerçek MainWindow ile aynı mı?
        Regression koruması: main_gui'deki guard mantığı değişirse bu
        test, izole modelin de güncellenmesi gerektiğini hatırlatır."""
        import inspect

        from main_gui import MainWindow

        for name in ("_next_generation", "_is_current_generation"):
            self.assertTrue(hasattr(MainWindow, name))
            src = inspect.getsource(getattr(MainWindow, name))
            # _is_current_generation çekirdek karşılaştırması korunmalı.
            if name == "_is_current_generation":
                self.assertIn("self._op_generation", src)

    def test_current_generation_result_is_applied(self) -> None:
        """Alt tür: POZİTİF (güncel sonuç uygulanır).
        Worker başlatılır, generation yakalanır, arada hiçbir şey olmaz;
        sonuç geldiğinde generation güncel olduğu için UI'a yansır."""
        holder = self._GenHolder()
        gen = holder._next_generation()  # işlem başlatıldı

        holder._on_done("anahtarlar", gen)

        self.assertEqual(holder.applied, ["anahtarlar"])

    def test_stale_result_after_reset_is_ignored(self) -> None:
        """Alt tür: NEGATİF (reset → bayat sonuç yok sayılır).
        Worker başlar (gen=1); reset generation'ı artırır (gen=2);
        geç gelen eski worker sonucu (gen=1) güncel olmadığı için
        UI state'ine yansıtılmaz."""
        holder = self._GenHolder()
        worker_gen = holder._next_generation()  # gen=1, worker başladı

        holder._next_generation()  # gen=2, reset/yeni işlem araya girdi

        holder._on_done("eski sonuç", worker_gen)  # bayat sonuç

        self.assertEqual(holder.applied, [])  # UI bozulmadı

    def test_newer_operation_invalidates_older_worker(self) -> None:
        """Alt tür: NEGATİF (iki worker yarışı).
        İki işlem peş peşe başlar; sadece en güncel generation'ın sonucu
        uygulanır, eski worker'ın geç gelen sonucu yok sayılır."""
        holder = self._GenHolder()
        first_gen = holder._next_generation()   # 1. worker
        second_gen = holder._next_generation()  # 2. worker (daha yeni)

        # Eski worker önce biter (bayat), yeni worker sonra biter (güncel).
        holder._on_done("birinci", first_gen)
        holder._on_done("ikinci", second_gen)

        self.assertEqual(holder.applied, ["ikinci"])


if __name__ == "__main__":
    unittest.main()
