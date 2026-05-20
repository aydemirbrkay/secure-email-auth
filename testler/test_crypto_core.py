"""
test_crypto_core.py — kriptografi/crypto_core modülü birim testleri
================================================================

Test türü: BİRİM TESTİ (Unit Test) — projenin en kapsamlı test dosyası (46 test)

Amaç:
    SHA-256 + RSA-2048 + AES-256-GCM tabanlı hibrit kriptografi akışının
    üretim kütüphanesi (cryptography lib) üzerinden ucu uca doğruluğunu
    sınar. CryptoCore sınıfının her yöntemi (anahtar üretimi, imzalama,
    şifreleme, çözme, doğrulama) hem mutlu yolda hem 5 farklı hata
    dalında test edilir.

Strateji:
    - Anahtar üretimi: RSAKeyPair tipinin yapısı, public_pem/private_pem
      formatı, PEM ↔ key dönüşüm tutarlılığı.
    - Mutlu yol: alice_send() → bob_receive() round-trip, mesaj eşitliği,
      imza doğrulamasının True dönmesi, step listesinin formatı.
    - Hata yolları: bozulmuş ciphertext (InvalidTag), bozulmuş imza
      (InvalidSignature), kısa veri (ValueError), eksik anahtar
      (RuntimeError), yanlış Bob anahtarıyla çözme.
    - Tamper tespiti: AES nonce/tag/AAD bütünlüğü, RSA-OAEP oturum
      anahtarı sarması, RSA-PSS imza.

Hata durumunda anlamı: Üretim crypto modülünde kriptografik veya akış
hatası — uygulama gönderici/alıcı arasında veri bozulmasını yakalamayabilir.
"""

import copy
import os
import unittest

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from kriptografi.crypto_core import CryptoCore, EncryptedPacket, RSAKeyPair, StepResult


class TestSHA256(unittest.TestCase):
    """SHA-256 özet fonksiyonu testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()

    def test_hash_deterministic(self) -> None:
        """Alt tür: BİRİM — deterministik fonksiyon — aynı girdi → aynı özet.

        Aynı girdi her zaman aynı özeti üretmeli.
        """
        data = b"Hello World"
        h1 = self.crypto.sha256_hash(data)
        h2 = self.crypto.sha256_hash(data)
        self.assertEqual(h1, h2)

    def test_hash_length(self) -> None:
        """Alt tür: BİRİM — SHA-256 her zaman 32 byte üretir (FIPS 180-4).

        SHA-256 özeti 32 byte (256 bit) olmalı.
        """
        h = self.crypto.sha256_hash(b"test")
        self.assertEqual(len(h), 32)

    def test_hash_different_inputs(self) -> None:
        """Alt tür: BİRİM — kolizyon yok — farklı girdiler farklı hash.

        Farklı girdiler farklı özetler üretmeli.
        """
        h1 = self.crypto.sha256_hash(b"message1")
        h2 = self.crypto.sha256_hash(b"message2")
        self.assertNotEqual(h1, h2)

    def test_hash_hex(self) -> None:
        """Alt tür: BİRİM — hex format kontratı (64 karakter).

        Hex formatı 64 karakter olmalı.
        """
        hex_hash = self.crypto.sha256_hex(b"test")
        self.assertEqual(len(hex_hash), 64)
        # Hex karakterleri doğrula
        int(hex_hash, 16)

    def test_hash_empty_input(self) -> None:
        """Alt tür: SINIR KOŞULU — boş bytes'da bile geçerli 32 byte hash.

        Boş girdi bile geçerli özet üretmeli.
        """
        h = self.crypto.sha256_hash(b"")
        self.assertEqual(len(h), 32)


class TestRSAKeyGeneration(unittest.TestCase):
    """RSA-2048 anahtar üretimi testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()

    def test_generate_keypair(self) -> None:
        """Alt tür: BİRİM — RSAKeyPair tipi + iç alanlar.

        Anahtar çifti üretilebilmeli.
        """
        kp = self.crypto.generate_rsa_keypair()
        self.assertIsInstance(kp, RSAKeyPair)
        self.assertIsNotNone(kp.private_key)
        self.assertIsNotNone(kp.public_key)

    def test_key_size(self) -> None:
        """Alt tür: BİRİM — RSA-2048 anahtar boyutu garantisi.

        Anahtar boyutu 2048 bit olmalı.
        """
        kp = self.crypto.generate_rsa_keypair()
        self.assertEqual(kp.private_key.key_size, 2048)

    def test_setup_keys(self) -> None:
        """Alt tür: BİRİM — Alice + Bob anahtar üretimi yan etkili.

        Alice ve Bob anahtarları üretilebilmeli.
        """
        alice, bob = self.crypto.setup_keys()
        self.assertIsNotNone(alice)
        self.assertIsNotNone(bob)
        self.assertIsNotNone(self.crypto.alice_keys)
        self.assertIsNotNone(self.crypto.bob_keys)

    def test_pem_export(self) -> None:
        """Alt tür: BİRİM — PEM serileştirme başlık satırı.

        PEM dışa aktarımı çalışmalı.
        """
        kp = self.crypto.generate_rsa_keypair()
        priv_pem = kp.private_pem()
        pub_pem = kp.public_pem()
        self.assertTrue(priv_pem.startswith(b"-----BEGIN PRIVATE KEY-----"))
        self.assertTrue(pub_pem.startswith(b"-----BEGIN PUBLIC KEY-----"))

    def test_different_keys_per_call(self) -> None:
        """Alt tür: BİRİM — rastgele anahtar üretimi.

        Her çağrı farklı anahtar üretmeli.
        """
        kp1 = self.crypto.generate_rsa_keypair()
        kp2 = self.crypto.generate_rsa_keypair()
        self.assertNotEqual(kp1.public_pem(), kp2.public_pem())


class TestRSASignature(unittest.TestCase):
    """RSA dijital imza testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()
        self.msg_hash = self.crypto.sha256_hash(b"test message")

    def test_sign_and_verify(self) -> None:
        """Alt tür: BİRİM — imza/doğrula round-trip.

        İmzalama ve doğrulama tutarlı olmalı.
        """
        sig = self.crypto.rsa_sign(
            self.crypto.alice_keys.private_key, self.msg_hash
        )
        result = self.crypto.rsa_verify(
            self.crypto.alice_keys.public_key, sig, self.msg_hash
        )
        self.assertTrue(result)

    def test_wrong_key_fails(self) -> None:
        """Alt tür: HATA YOLU — yanlış public key → doğrulama False.

        Yanlış açık anahtar ile doğrulama başarısız olmalı.
        """
        sig = self.crypto.rsa_sign(
            self.crypto.alice_keys.private_key, self.msg_hash
        )
        result = self.crypto.rsa_verify(
            self.crypto.bob_keys.public_key, sig, self.msg_hash
        )
        self.assertFalse(result)

    def test_tampered_hash_fails(self) -> None:
        """Alt tür: HATA YOLU — değiştirilmiş hash → doğrulama False.

        Değiştirilmiş hash ile doğrulama başarısız olmalı.
        """
        sig = self.crypto.rsa_sign(
            self.crypto.alice_keys.private_key, self.msg_hash
        )
        tampered_hash = self.crypto.sha256_hash(b"tampered message")
        result = self.crypto.rsa_verify(
            self.crypto.alice_keys.public_key, sig, tampered_hash
        )
        self.assertFalse(result)


class TestAESGCM(unittest.TestCase):
    """AES-256-GCM simetrik şifreleme testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()

    def test_encrypt_decrypt(self) -> None:
        """Alt tür: BİRİM — AES-GCM şifrele/çöz round-trip.

        Şifreleme ve çözme tutarlı olmalı.
        """
        key = os.urandom(32)
        plaintext = b"Secret message"
        nonce, ct = self.crypto.aes_gcm_encrypt(key, plaintext)
        pt = self.crypto.aes_gcm_decrypt(key, nonce, ct)
        self.assertEqual(pt, plaintext)

    def test_wrong_key_fails(self) -> None:
        """Alt tür: HATA YOLU — yanlış public key → doğrulama False.

        Yanlış anahtar ile çözme başarısız olmalı.
        """
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"Secret"
        nonce, ct = self.crypto.aes_gcm_encrypt(key1, plaintext)
        with self.assertRaises(Exception):
            self.crypto.aes_gcm_decrypt(key2, nonce, ct)

    def test_tampered_ciphertext_fails(self) -> None:
        """Alt tür: HATA YOLU — ciphertext bit-flip → GCM tag bozulur.

        Değiştirilmiş ciphertext ile çözme başarısız olmalı (GCM tag).
        """
        key = os.urandom(32)
        plaintext = b"Secret"
        nonce, ct = self.crypto.aes_gcm_encrypt(key, plaintext)
        tampered = bytearray(ct)
        tampered[0] ^= 0xFF
        with self.assertRaises(Exception):
            self.crypto.aes_gcm_decrypt(key, nonce, bytes(tampered))

    def test_session_key_generation(self) -> None:
        """Alt tür: BİRİM — 256-bit oturum anahtarı.

        Oturum anahtarı 32 byte olmalı.
        """
        key = self.crypto.generate_session_key()
        self.assertEqual(len(key), 32)

    def test_nonce_is_12_bytes(self) -> None:
        """Alt tür: BİRİM — GCM standart nonce boyutu.

        Nonce 12 byte olmalı.
        """
        key = os.urandom(32)
        nonce, _ = self.crypto.aes_gcm_encrypt(key, b"test")
        self.assertEqual(len(nonce), 12)

    def test_aad_roundtrip(self) -> None:
        """Alt tür: BİRİM — AAD (Additional Authenticated Data) doğrulama.

        AAD ile şifreleme + aynı AAD ile deşifre = orijinal metin.
        """
        key = os.urandom(32)
        aad = b"secure-email-auth/v1|from=abcdef0123456789|ts=0"
        nonce, ct = self.crypto.aes_gcm_encrypt(key, b"hello", aad)
        pt = self.crypto.aes_gcm_decrypt(key, nonce, ct, aad)
        self.assertEqual(pt, b"hello")

    def test_aad_mismatch_fails(self) -> None:
        """Alt tür: HATA YOLU — farklı AAD → InvalidTag.

        Farklı AAD ile deşifre InvalidTag fırlatmalı.
        """
        key = os.urandom(32)
        nonce, ct = self.crypto.aes_gcm_encrypt(key, b"hello", b"aad-A")
        with self.assertRaises(InvalidTag):
            self.crypto.aes_gcm_decrypt(key, nonce, ct, b"aad-B")

    def test_aad_none_vs_empty_compatible(self) -> None:
        """Alt tür: BİRİM — PyCA sözleşmesi: None ↔ b''.

        AAD=None ile AAD=b'' eşdeğer davranmalı (PyCA sözleşmesi).
        """
        key = os.urandom(32)
        nonce, ct = self.crypto.aes_gcm_encrypt(key, b"hello", None)
        # None ile yazıp boş bytes ile okuma kabul edilmeli
        pt = self.crypto.aes_gcm_decrypt(key, nonce, ct, b"")
        self.assertEqual(pt, b"hello")


class TestRSAKeyEncryption(unittest.TestCase):
    """RSA ile oturum anahtarı şifreleme testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_encrypt_decrypt_session_key(self) -> None:
        """Alt tür: BİRİM — RSA-OAEP key wrap round-trip.

        Oturum anahtarı şifrelenip çözülebilmeli.
        """
        session_key = os.urandom(32)
        enc = self.crypto.rsa_encrypt_key(
            self.crypto.bob_keys.public_key, session_key
        )
        dec = self.crypto.rsa_decrypt_key(
            self.crypto.bob_keys.private_key, enc
        )
        self.assertEqual(dec, session_key)

    def test_wrong_private_key_fails(self) -> None:
        """Alt tür: HATA YOLU — yanlış private key → OAEP başarısız.

        Yanlış gizli anahtar ile çözme başarısız olmalı.
        """
        session_key = os.urandom(32)
        enc = self.crypto.rsa_encrypt_key(
            self.crypto.bob_keys.public_key, session_key
        )
        with self.assertRaises(Exception):
            self.crypto.rsa_decrypt_key(
                self.crypto.alice_keys.private_key, enc
            )


class TestFullWorkflow(unittest.TestCase):
    """Tam Alice → Bob iş akışı testi."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_full_send_receive(self) -> None:
        """Alt tür: ENTEGRASYON — uçtan uca Alice → Bob akış.

        Tam iş akışı başarılı olmalı.
        """
        message = "Merhaba Bob, bu güvenli bir test mesajıdır!"
        packet, alice_steps = self.crypto.alice_send(message)

        self.assertEqual(len(alice_steps), 6)
        self.assertIsInstance(packet, EncryptedPacket)

        msg, valid, bob_steps = self.crypto.bob_receive(packet)

        self.assertEqual(len(bob_steps), 5)
        self.assertEqual(msg, message)
        self.assertTrue(valid)

    def test_unicode_message(self) -> None:
        """Alt tür: BİRİM — UTF-8 + emoji round-trip.

        Unicode mesaj desteği.
        """
        message = "Şifreli mesaj: çöğüışĞÜÖİ 🔐🔑"
        packet, _ = self.crypto.alice_send(message)
        msg, valid, _ = self.crypto.bob_receive(packet)
        self.assertEqual(msg, message)
        self.assertTrue(valid)

    def test_long_message(self) -> None:
        """Alt tür: BİRİM — 10000 karakter mesaj round-trip.

        Uzun mesaj desteği.
        """
        message = "A" * 10000
        packet, _ = self.crypto.alice_send(message)
        msg, valid, _ = self.crypto.bob_receive(packet)
        self.assertEqual(msg, message)
        self.assertTrue(valid)

    def test_keys_not_set_raises(self) -> None:
        """Alt tür: HATA YOLU — anahtar yok → RuntimeError (gönderici).

        Anahtar olmadan gönderim hatası.
        """
        fresh = CryptoCore()
        with self.assertRaises(RuntimeError):
            fresh.alice_send("test")

    def test_keys_not_set_receive_raises(self) -> None:
        """Alt tür: HATA YOLU — anahtar yok → RuntimeError (alıcı).

        Anahtar olmadan alım hatası.
        """
        fresh = CryptoCore()
        dummy_packet = EncryptedPacket(
            encrypted_message=b"",
            encrypted_session_key=b"",
            nonce=b"",
            associated_data=b"",
        )
        with self.assertRaises(RuntimeError):
            fresh.bob_receive(dummy_packet)

    def test_step_results_structure(self) -> None:
        """Alt tür: BİRİM — StepResult tip + alan kontratı.

        Adım sonuçları doğru yapıda olmalı.
        """
        packet, alice_steps = self.crypto.alice_send("Test")
        for step in alice_steps:
            self.assertIsInstance(step, StepResult)
            self.assertIsInstance(step.step_number, int)
            self.assertIsInstance(step.step_name, str)
            self.assertIsInstance(step.description, str)
            self.assertIsInstance(step.data, dict)


class TestSignatureSemantics(unittest.TestCase):
    """İmza semantiği (H(m) üzerinde Prehashed PSS) testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_sign_requires_32_byte_digest(self) -> None:
        """Alt tür: HATA YOLU — 32 olmayan byte → ValueError.

        rsa_sign yalnızca 32 byte (SHA-256 özeti) kabul etmeli.
        """
        # 32 byte olmayan bir girdi ValueError üretmeli
        with self.assertRaises(ValueError):
            self.crypto.rsa_sign(
                self.crypto.alice_keys.private_key, b"too short"
            )

    def test_signature_is_over_hash_not_double_hash(self) -> None:
        """Alt tür: BİRİM — Prehashed semantiği (H(m), H(H(m)) değil).

        İmza H(m) üzerinde olmalı; H(H(m)) üzerinde DEĞİL.
        Dolayısıyla imza H(m) ile doğrulanır, H(H(m)) ile doğrulanmaz.

        Not: Bu test tek başına "Prehashed kullanılıyor mu?" sorusunu
        ayırt edemez (hem Prehashed hem non-Prehashed yol bu iki
        koşulu sağlar). Kesin ayırt edici ispat için
        ``test_signature_is_definitively_prehashed`` testine bakın.
        """
        msg = "merhaba dünya".encode("utf-8")
        msg_hash = self.crypto.sha256_hash(msg)

        sig = self.crypto.rsa_sign(
            self.crypto.alice_keys.private_key, msg_hash
        )

        # H(m) ile doğrulanmalı
        self.assertTrue(self.crypto.rsa_verify(
            self.crypto.alice_keys.public_key, sig, msg_hash
        ))

        # H(H(m)) ile doğrulanmamalı (çift-hash değil)
        double_hash = self.crypto.sha256_hash(msg_hash)
        self.assertFalse(self.crypto.rsa_verify(
            self.crypto.alice_keys.public_key, sig, double_hash
        ))

    def test_signature_is_definitively_prehashed(self) -> None:
        """Alt tür: BİRİM — kesin Prehashed kanıtı (ayırt edici test).

        Kesin ayırt edici ispat: rsa_sign GERÇEKTEN Prehashed semantiğinde
        çalışıyor, yani verilen H(m)'i *yeniden hashlemiyor*, doğrudan
        imzalıyor.

        Yöntem:
          1. raw_msg → msg_hash = SHA256(raw_msg)
          2. sig = rsa_sign(priv, msg_hash)
          3. Kütüphanenin non-Prehashed verify'ı ile sig'i **ham mesaj**
             üzerinde doğrula (verify içinde SHA256(raw_msg) hesaplanır).

        Beklenen: Başarılı doğrulama.

        Neden ayırt edicidir:
          - Prehashed doğru çalışıyorsa: sig, msg_hash üzerinedir.
            non-Prehashed verify ham mesajı hashleyip msg_hash elde eder
            → eşleşir → SUCCESS.
          - rsa_sign içeride yanlışlıkla tekrar hashleseydi: sig,
            H(msg_hash) = H(H(raw_msg)) üzerinde olurdu. non-Prehashed
            verify yine msg_hash ile karşılaştırır → eşleşmez → FAIL.
        Dolayısıyla bu testin geçmesi Prehashed semantiğini kanıtlar.
        """
        raw_msg = b"ayirt edici Prehashed semantik kaniti"
        msg_hash = self.crypto.sha256_hash(raw_msg)

        sig = self.crypto.rsa_sign(
            self.crypto.alice_keys.private_key, msg_hash
        )

        try:
            self.crypto.alice_keys.public_key.verify(
                sig,
                raw_msg,                 # ham mesaj
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),         # non-Prehashed: kütüphane hashler
            )
        except InvalidSignature:
            self.fail(
                "Prehashed semantik bozulmuş: rsa_sign verilen H(m)'i "
                "tekrar hashliyor (imza beklenenin iki kat hash'i üzerinde)."
            )

    def test_verify_is_definitively_prehashed(self) -> None:
        """Alt tür: BİRİM — kesin Prehashed kanıtı (verify tarafı).

        Simetrik ayırt edici ispat: rsa_verify de Prehashed semantiğinde
        çalışıyor, yani verilen H(m)'i yeniden hashlemeden doğrudan
        imzaya karşı kontrol ediyor.

        Yöntem:
          1. raw_msg → msg_hash
          2. Kütüphanenin non-Prehashed sign'ı ile ham mesajı imzala
             (imza gerçekte msg_hash üzerinde oluşur).
          3. rsa_verify(sig, msg_hash) çağır.

        Beklenen: True (imza H(m) üzerindedir ve rsa_verify Prehashed
        olduğu için H(m)'i yeniden hashlemeyip doğrudan kullanır).

        Eğer rsa_verify içeride tekrar hashleseydi, sağlamayı H(H(m))'e
        karşı yapar ve False dönerdi.
        """
        raw_msg = b"rsa_verify Prehashed tarafi icin kanit"
        msg_hash = self.crypto.sha256_hash(raw_msg)

        sig = self.crypto.alice_keys.private_key.sign(
            raw_msg,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),             # non-Prehashed sign → imza H(raw_msg) üzerinde
        )

        self.assertTrue(
            self.crypto.rsa_verify(
                self.crypto.alice_keys.public_key, sig, msg_hash
            ),
            "rsa_verify Prehashed değil gibi davrandı: H(m)'i "
            "yeniden hashlemiş görünüyor.",
        )


class TestNegativeSecurityScenarios(unittest.TestCase):
    """
    Negatif güvenlik senaryoları — paket / nonce / tag / imza
    manipülasyonları beklenen hataları üretmeli, replay senaryosunun
    mevcut tasarımda engellenmediği açıkça belgelenir.
    """

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()
        self.packet, _ = self.crypto.alice_send("gizli mesaj")

    # --- Tamper: şifreli mesaj ------------------------------------------------

    def test_tamper_ciphertext_byte_raises_invalid_tag(self) -> None:
        """Alt tür: HATA YOLU / GÜVENLİK — ciphertext byte tamper → InvalidTag.

        Şifreli mesajın tek byte'ının değiştirilmesi GCM tag'ini bozmalı.
        """
        tampered_ct = bytearray(self.packet.encrypted_message)
        tampered_ct[0] ^= 0x01
        bad = EncryptedPacket(
            encrypted_message=bytes(tampered_ct),
            encrypted_session_key=self.packet.encrypted_session_key,
            nonce=self.packet.nonce,
            associated_data=self.packet.associated_data,
        )
        with self.assertRaises(InvalidTag):
            self.crypto.bob_receive(bad)

    def test_tamper_auth_tag_byte_raises_invalid_tag(self) -> None:
        """Alt tür: HATA YOLU / GÜVENLİK — tag tamper (son 16 byte) → InvalidTag.

        AES-GCM çıktısının son 16 byte'ı tag'tir; bu aralıkta
        yapılan tek bit'lik değişiklik kimlik doğrulamayı bozmalı.
        """
        tampered_ct = bytearray(self.packet.encrypted_message)
        # son byte (tag içi) bit-flip
        tampered_ct[-1] ^= 0x80
        bad = EncryptedPacket(
            encrypted_message=bytes(tampered_ct),
            encrypted_session_key=self.packet.encrypted_session_key,
            nonce=self.packet.nonce,
            associated_data=self.packet.associated_data,
        )
        with self.assertRaises(InvalidTag):
            self.crypto.bob_receive(bad)

    # --- Tamper: nonce --------------------------------------------------------

    def test_tamper_nonce_raises_invalid_tag(self) -> None:
        """Alt tür: HATA YOLU / GÜVENLİK — nonce tamper → InvalidTag.

        Nonce'un değiştirilmesi deşifre adımında başarısız olmalı.
        """
        tampered_nonce = bytearray(self.packet.nonce)
        tampered_nonce[0] ^= 0xFF
        bad = EncryptedPacket(
            encrypted_message=self.packet.encrypted_message,
            encrypted_session_key=self.packet.encrypted_session_key,
            nonce=bytes(tampered_nonce),
            associated_data=self.packet.associated_data,
        )
        with self.assertRaises(InvalidTag):
            self.crypto.bob_receive(bad)

    # --- Tamper: şifreli oturum anahtarı --------------------------------------

    def test_tamper_encrypted_session_key_raises(self) -> None:
        """Alt tür: HATA YOLU / GÜVENLİK — OAEP-sarılı anahtar tamper → exception.

        RSA-OAEP şifreli oturum anahtarının değiştirilmesi OAEP çözme
        aşamasında istisna üretmeli (ValueError tabanlı).
        """
        tampered_key = bytearray(self.packet.encrypted_session_key)
        tampered_key[0] ^= 0x01
        bad = EncryptedPacket(
            encrypted_message=self.packet.encrypted_message,
            encrypted_session_key=bytes(tampered_key),
            nonce=self.packet.nonce,
            associated_data=self.packet.associated_data,
        )
        # OAEP çözme başarısız olursa bir istisna (genelde ValueError) oluşur
        with self.assertRaises(Exception):
            self.crypto.bob_receive(bad)

    # --- Tamper: AAD (AES-GCM bütünlük bağı) ----------------------------------

    def test_tamper_associated_data_raises_invalid_tag(self) -> None:
        """Alt tür: HATA YOLU / GÜVENLİK — AAD tamper → InvalidTag (AAD korumalı).

        AAD'de yapılacak her türlü değişiklik GCM kimlik doğrulama
        etiketini bozmalı; ciphertext dokunulmamış olsa bile InvalidTag
        fırlatılmalı. Bu test AAD'nin şifrelenmese de tag ile bağlı
        olduğunu kanıtlar.
        """
        tampered_aad = bytearray(self.packet.associated_data)
        tampered_aad[-1] ^= 0x01  # örn. timestamp'in son byte'ını değiştir
        bad = EncryptedPacket(
            encrypted_message=self.packet.encrypted_message,
            encrypted_session_key=self.packet.encrypted_session_key,
            nonce=self.packet.nonce,
            associated_data=bytes(tampered_aad),
        )
        with self.assertRaises(InvalidTag):
            self.crypto.bob_receive(bad)

    def test_strip_associated_data_raises_invalid_tag(self) -> None:
        """Alt tür: HATA YOLU / GÜVENLİK — AAD silme → InvalidTag.

        AAD'yi tamamen silmek (boş bytes) de deşifreyi bozmalı.
        """
        bad = EncryptedPacket(
            encrypted_message=self.packet.encrypted_message,
            encrypted_session_key=self.packet.encrypted_session_key,
            nonce=self.packet.nonce,
            associated_data=b"",
        )
        with self.assertRaises(InvalidTag):
            self.crypto.bob_receive(bad)

    # --- Tamper: imza (AES altında bile) --------------------------------------

    def test_tamper_message_plaintext_before_encrypt_breaks_signature(
        self,
    ) -> None:
        """Alt tür: HATA YOLU / GÜVENLİK — imzanın H(m)'ye bağlılığı (ek byte → False).

        Aynı oturum anahtarıyla farklı bir mesaj imzalanıp eski paketin
        oturum anahtarıyla yeniden paketlense bile, imza mesaj özeti
        üzerinden oluştuğu için farklı mesajla doğrulanmamalı.
        Senaryo: Alice dürüst, saldırgan oturum anahtarını çözmüş
        varsayımı altında bile imza bütünlüğü korunmalı.
        """
        # Bob'un K_S'yi çözdüğünü varsayalım:
        session_key = self.crypto.rsa_decrypt_key(
            self.crypto.bob_keys.private_key,
            self.packet.encrypted_session_key,
        )
        combined = self.crypto.aes_gcm_decrypt(
            session_key,
            self.packet.nonce,
            self.packet.encrypted_message,
            self.packet.associated_data,
        )
        # Sabit-uzunluk ayrıştırma: son SIGNATURE_LEN byte imzadır.
        msg_bytes = combined[:-self.crypto.SIGNATURE_LEN]
        signature = combined[-self.crypto.SIGNATURE_LEN:]

        # Saldırgan: mesajı değiştir, imzayı aynı tutmaya çalışsın.
        forged_msg = msg_bytes + b" (ekleme)"
        forged_hash = self.crypto.sha256_hash(forged_msg)
        self.assertFalse(self.crypto.rsa_verify(
            self.crypto.alice_keys.public_key, signature, forged_hash
        ))

    # --- Replay: tasarımın sınırı ---------------------------------------------

    def test_replay_is_not_blocked_by_design(self) -> None:
        """Alt tür: BELGELEME — replay engellenmiyor (tasarım sınırı kanıtı).

        BELGELEME: Mevcut tasarımda durum/timestamp tutulmadığı için
        aynı paketin tekrar iletilmesi (replay) Bob tarafında yine
        başarıyla çözülür. Bu koruma için ayrıca bir replay cache /
        sıra numarası mekanizması eklenmelidir.
        """
        msg1, valid1, _ = self.crypto.bob_receive(self.packet)
        msg2, valid2, _ = self.crypto.bob_receive(copy.copy(self.packet))
        self.assertEqual(msg1, msg2)
        self.assertTrue(valid1)
        self.assertTrue(valid2)


class TestEncryptedPacketShape(unittest.TestCase):
    """EncryptedPacket veri modelinin yapısını doğrular."""

    def test_packet_has_expected_fields(self) -> None:
        """Alt tür: BİRİM — EncryptedPacket dataclass alanları.

        Paket tam olarak 4 alanı taşır:
          - encrypted_message   (ciphertext ‖ tag)
          - encrypted_session_key (RSA-OAEP ile sarılmış K_S)
          - nonce                (12-byte rastgele)
          - associated_data      (AAD — şifrelenmez, GCM tag ile korunur)

        GCM tag ayrı bir alan olarak taşınmaz (ciphertext içine gömülüdür).
        """
        from dataclasses import fields
        field_names = {f.name for f in fields(EncryptedPacket)}
        self.assertEqual(
            field_names,
            {
                "encrypted_message",
                "encrypted_session_key",
                "nonce",
                "associated_data",
            },
        )


class TestAADBuilder(unittest.TestCase):
    """``CryptoCore.build_aad`` davranışını doğrular."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_aad_starts_with_protocol_tag(self) -> None:
        """Alt tür: BİRİM — AAD prefix sabiti.

        AAD her zaman sabit protokol etiketiyle başlamalı.
        """
        aad = self.crypto.build_aad(self.crypto.alice_keys.public_key)
        self.assertTrue(aad.startswith(self.crypto.PROTOCOL_TAG))

    def test_aad_contains_sender_fingerprint(self) -> None:
        """Alt tür: BİRİM — AAD anahtar fingerprint'i içerir.

        AAD, gönderenin açık anahtarının SHA-256 özetinin ilk 8 byte'ının
        hex gösterimini içermeli — anahtar farklı olunca AAD da değişir.
        """
        aad_alice = self.crypto.build_aad(
            self.crypto.alice_keys.public_key, timestamp=1000
        )
        aad_bob = self.crypto.build_aad(
            self.crypto.bob_keys.public_key, timestamp=1000
        )
        self.assertNotEqual(aad_alice, aad_bob)
        self.assertIn(b"|from=", aad_alice)
        self.assertIn(b"|ts=1000", aad_alice)

    def test_aad_is_deterministic_for_same_inputs(self) -> None:
        """Alt tür: BİRİM — AAD üretimi deterministik.

        Aynı anahtar + aynı timestamp = aynı AAD.
        """
        a1 = self.crypto.build_aad(self.crypto.alice_keys.public_key, timestamp=42)
        a2 = self.crypto.build_aad(self.crypto.alice_keys.public_key, timestamp=42)
        self.assertEqual(a1, a2)

    def test_aad_timestamp_changes_value(self) -> None:
        """Alt tür: BİRİM — AAD timestamp duyarlı.

        Farklı timestamp farklı AAD üretmeli.
        """
        a1 = self.crypto.build_aad(self.crypto.alice_keys.public_key, timestamp=1)
        a2 = self.crypto.build_aad(self.crypto.alice_keys.public_key, timestamp=2)
        self.assertNotEqual(a1, a2)


class TestMessageSignatureFraming(unittest.TestCase):
    """m ∥ imza çerçeveleme (framing) testleri — ayraç çarpışmalarına
    karşı bağışık olduğunu doğrular."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_message_containing_old_separator_roundtrips(self) -> None:
        """Alt tür: REGRESYON — eski ayraç stringi içeren mesaj round-trip.

        REGRESYON: Kullanıcı mesajı eski SEPARATOR stringi içerse bile
        ayrıştırma bozulmamalı.

        Önceki tasarımda ``combined = msg || b'||SIGNATURE_BOUNDARY||' || sig``
        kullanılıyordu; kullanıcı mesajı bu ayracı içerirse ``split(..., 1)``
        mesajın içinden ayırır, imza bozulmuş görünür ve doğrulama
        yanlış-FAIL olurdu. Sabit-uzunluk (son 256 byte) kuralı bu
        riski ortadan kaldırır.
        """
        attack_msg = "hedef: ||SIGNATURE_BOUNDARY|| — saldirgan denemesi"
        packet, _ = self.crypto.alice_send(attack_msg)
        msg, valid, _ = self.crypto.bob_receive(packet)
        self.assertEqual(msg, attack_msg)
        self.assertTrue(valid)

    def test_short_combined_raises_readable_error(self) -> None:
        """Alt tür: HATA YOLU — SIGNATURE_LEN'den kısa combined → ValueError.

        İmzadan daha kısa bir paket geldiğinde okunabilir bir ValueError
        fırlatılmalı — sessizce yanlış yere bölmemeli.

        Bu durumu, çözülen birleşim 256 byte'tan kısa olacak şekilde
        direkt olarak simüle ediyoruz (alt-seviye çerçeveleme kontrolü).
        """
        # 100 byte'lık sahte "combined" ile deşifre öncesi durumu taklit:
        # Gerçek akışta bu, AES decrypt sonrası elde edilen combined'e
        # karşılık gelir; burada doğrudan ayrıştırma mantığını doğruluyoruz.
        short = b"A" * 100
        self.assertLess(len(short), self.crypto.SIGNATURE_LEN)
        # Paket seviyesinde çözülen combined'i simüle etmek için basit
        # bir kontrol: (msg, sig) ayrıştırması SIGNATURE_LEN'den kısa
        # girdide ValueError vermeli. Bu koşul bob_receive içinde
        # belirgin biçimde patlamalı.
        key = os.urandom(32)
        aad = self.crypto.build_aad(self.crypto.alice_keys.public_key)
        nonce, ct = self.crypto.aes_gcm_encrypt(key, short, aad)
        enc_session = self.crypto.rsa_encrypt_key(
            self.crypto.bob_keys.public_key, key
        )
        bad = EncryptedPacket(
            encrypted_message=ct,
            encrypted_session_key=enc_session,
            nonce=nonce,
            associated_data=aad,
        )
        with self.assertRaises(ValueError):
            self.crypto.bob_receive(bad)

    def test_signature_is_always_256_bytes(self) -> None:
        """Alt tür: BİRİM — RSA-2048 PSS imza sabit 256 byte.

        RSA-2048 PSS imzası sabit 256 byte üretir — framing varsayımını
        doğrular.
        """
        for raw in (b"a", b"x" * 1024, "çöğüışÇÖĞÜŞİ".encode("utf-8")):
            h = self.crypto.sha256_hash(raw)
            sig = self.crypto.rsa_sign(
                self.crypto.alice_keys.private_key, h
            )
            self.assertEqual(len(sig), self.crypto.SIGNATURE_LEN)


if __name__ == "__main__":
    unittest.main()
