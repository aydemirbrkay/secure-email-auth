"""
test_crypto_core.py – Kriptografi Modülü Test Dosyası
=====================================================
SHA-256, RSA-2048 ve AES-256-GCM tabanlı hibrit kriptografik
iş akışının birim testleri.
"""

import os
import unittest

from crypto_core import CryptoCore, EncryptedPacket, RSAKeyPair, StepResult


class TestSHA256(unittest.TestCase):
    """SHA-256 özet fonksiyonu testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()

    def test_hash_deterministic(self) -> None:
        """Aynı girdi her zaman aynı özeti üretmeli."""
        data = b"Hello World"
        h1 = self.crypto.sha256_hash(data)
        h2 = self.crypto.sha256_hash(data)
        self.assertEqual(h1, h2)

    def test_hash_length(self) -> None:
        """SHA-256 özeti 32 byte (256 bit) olmalı."""
        h = self.crypto.sha256_hash(b"test")
        self.assertEqual(len(h), 32)

    def test_hash_different_inputs(self) -> None:
        """Farklı girdiler farklı özetler üretmeli."""
        h1 = self.crypto.sha256_hash(b"message1")
        h2 = self.crypto.sha256_hash(b"message2")
        self.assertNotEqual(h1, h2)

    def test_hash_hex(self) -> None:
        """Hex formatı 64 karakter olmalı."""
        hex_hash = self.crypto.sha256_hex(b"test")
        self.assertEqual(len(hex_hash), 64)
        # Hex karakterleri doğrula
        int(hex_hash, 16)

    def test_hash_empty_input(self) -> None:
        """Boş girdi bile geçerli özet üretmeli."""
        h = self.crypto.sha256_hash(b"")
        self.assertEqual(len(h), 32)


class TestRSAKeyGeneration(unittest.TestCase):
    """RSA-2048 anahtar üretimi testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()

    def test_generate_keypair(self) -> None:
        """Anahtar çifti üretilebilmeli."""
        kp = self.crypto.generate_rsa_keypair()
        self.assertIsInstance(kp, RSAKeyPair)
        self.assertIsNotNone(kp.private_key)
        self.assertIsNotNone(kp.public_key)

    def test_key_size(self) -> None:
        """Anahtar boyutu 2048 bit olmalı."""
        kp = self.crypto.generate_rsa_keypair()
        self.assertEqual(kp.private_key.key_size, 2048)

    def test_setup_keys(self) -> None:
        """Alice ve Bob anahtarları üretilebilmeli."""
        alice, bob = self.crypto.setup_keys()
        self.assertIsNotNone(alice)
        self.assertIsNotNone(bob)
        self.assertIsNotNone(self.crypto.alice_keys)
        self.assertIsNotNone(self.crypto.bob_keys)

    def test_pem_export(self) -> None:
        """PEM dışa aktarımı çalışmalı."""
        kp = self.crypto.generate_rsa_keypair()
        priv_pem = kp.private_pem()
        pub_pem = kp.public_pem()
        self.assertTrue(priv_pem.startswith(b"-----BEGIN PRIVATE KEY-----"))
        self.assertTrue(pub_pem.startswith(b"-----BEGIN PUBLIC KEY-----"))

    def test_different_keys_per_call(self) -> None:
        """Her çağrı farklı anahtar üretmeli."""
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
        """İmzalama ve doğrulama tutarlı olmalı."""
        sig = self.crypto.rsa_sign(
            self.crypto.alice_keys.private_key, self.msg_hash
        )
        result = self.crypto.rsa_verify(
            self.crypto.alice_keys.public_key, sig, self.msg_hash
        )
        self.assertTrue(result)

    def test_wrong_key_fails(self) -> None:
        """Yanlış açık anahtar ile doğrulama başarısız olmalı."""
        sig = self.crypto.rsa_sign(
            self.crypto.alice_keys.private_key, self.msg_hash
        )
        result = self.crypto.rsa_verify(
            self.crypto.bob_keys.public_key, sig, self.msg_hash
        )
        self.assertFalse(result)

    def test_tampered_hash_fails(self) -> None:
        """Değiştirilmiş hash ile doğrulama başarısız olmalı."""
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
        """Şifreleme ve çözme tutarlı olmalı."""
        key = os.urandom(32)
        plaintext = b"Secret message"
        nonce, ct = self.crypto.aes_gcm_encrypt(key, plaintext)
        pt = self.crypto.aes_gcm_decrypt(key, nonce, ct)
        self.assertEqual(pt, plaintext)

    def test_wrong_key_fails(self) -> None:
        """Yanlış anahtar ile çözme başarısız olmalı."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"Secret"
        nonce, ct = self.crypto.aes_gcm_encrypt(key1, plaintext)
        with self.assertRaises(Exception):
            self.crypto.aes_gcm_decrypt(key2, nonce, ct)

    def test_tampered_ciphertext_fails(self) -> None:
        """Değiştirilmiş ciphertext ile çözme başarısız olmalı (GCM tag)."""
        key = os.urandom(32)
        plaintext = b"Secret"
        nonce, ct = self.crypto.aes_gcm_encrypt(key, plaintext)
        tampered = bytearray(ct)
        tampered[0] ^= 0xFF
        with self.assertRaises(Exception):
            self.crypto.aes_gcm_decrypt(key, nonce, bytes(tampered))

    def test_session_key_generation(self) -> None:
        """Oturum anahtarı 32 byte olmalı."""
        key = self.crypto.generate_session_key()
        self.assertEqual(len(key), 32)

    def test_nonce_is_12_bytes(self) -> None:
        """Nonce 12 byte olmalı."""
        key = os.urandom(32)
        nonce, _ = self.crypto.aes_gcm_encrypt(key, b"test")
        self.assertEqual(len(nonce), 12)


class TestRSAKeyEncryption(unittest.TestCase):
    """RSA ile oturum anahtarı şifreleme testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_encrypt_decrypt_session_key(self) -> None:
        """Oturum anahtarı şifrelenip çözülebilmeli."""
        session_key = os.urandom(32)
        enc = self.crypto.rsa_encrypt_key(
            self.crypto.bob_keys.public_key, session_key
        )
        dec = self.crypto.rsa_decrypt_key(
            self.crypto.bob_keys.private_key, enc
        )
        self.assertEqual(dec, session_key)

    def test_wrong_private_key_fails(self) -> None:
        """Yanlış gizli anahtar ile çözme başarısız olmalı."""
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
        """Tam iş akışı başarılı olmalı."""
        message = "Merhaba Bob, bu güvenli bir test mesajıdır!"
        packet, alice_steps = self.crypto.alice_send(message)

        self.assertEqual(len(alice_steps), 6)
        self.assertIsInstance(packet, EncryptedPacket)

        msg, valid, bob_steps = self.crypto.bob_receive(packet)

        self.assertEqual(len(bob_steps), 5)
        self.assertEqual(msg, message)
        self.assertTrue(valid)

    def test_unicode_message(self) -> None:
        """Unicode mesaj desteği."""
        message = "Şifreli mesaj: çöğüışĞÜÖİ 🔐🔑"
        packet, _ = self.crypto.alice_send(message)
        msg, valid, _ = self.crypto.bob_receive(packet)
        self.assertEqual(msg, message)
        self.assertTrue(valid)

    def test_long_message(self) -> None:
        """Uzun mesaj desteği."""
        message = "A" * 10000
        packet, _ = self.crypto.alice_send(message)
        msg, valid, _ = self.crypto.bob_receive(packet)
        self.assertEqual(msg, message)
        self.assertTrue(valid)

    def test_keys_not_set_raises(self) -> None:
        """Anahtar olmadan gönderim hatası."""
        fresh = CryptoCore()
        with self.assertRaises(RuntimeError):
            fresh.alice_send("test")

    def test_keys_not_set_receive_raises(self) -> None:
        """Anahtar olmadan alım hatası."""
        fresh = CryptoCore()
        dummy_packet = EncryptedPacket(
            encrypted_message=b"", encrypted_session_key=b"", nonce=b""
        )
        with self.assertRaises(RuntimeError):
            fresh.bob_receive(dummy_packet)

    def test_step_results_structure(self) -> None:
        """Adım sonuçları doğru yapıda olmalı."""
        packet, alice_steps = self.crypto.alice_send("Test")
        for step in alice_steps:
            self.assertIsInstance(step, StepResult)
            self.assertIsInstance(step.step_number, int)
            self.assertIsInstance(step.step_name, str)
            self.assertIsInstance(step.description, str)
            self.assertIsInstance(step.data, dict)


if __name__ == "__main__":
    unittest.main()
