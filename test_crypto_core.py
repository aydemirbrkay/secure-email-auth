"""
test_crypto_core.py – Kriptografi Modülü Test Dosyası
=====================================================
SHA-256, RSA-2048 ve AES-256-GCM tabanlı hibrit kriptografik
iş akışının birim testleri.
"""

import copy
import os
import unittest

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

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


class TestSignatureSemantics(unittest.TestCase):
    """İmza semantiği (H(m) üzerinde Prehashed PSS) testleri."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_sign_requires_32_byte_digest(self) -> None:
        """rsa_sign yalnızca 32 byte (SHA-256 özeti) kabul etmeli."""
        # 32 byte olmayan bir girdi ValueError üretmeli
        with self.assertRaises(ValueError):
            self.crypto.rsa_sign(
                self.crypto.alice_keys.private_key, b"too short"
            )

    def test_signature_is_over_hash_not_double_hash(self) -> None:
        """
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
        """
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
        """
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
        """Şifreli mesajın tek byte'ının değiştirilmesi GCM tag'ini bozmalı."""
        tampered_ct = bytearray(self.packet.encrypted_message)
        tampered_ct[0] ^= 0x01
        bad = EncryptedPacket(
            encrypted_message=bytes(tampered_ct),
            encrypted_session_key=self.packet.encrypted_session_key,
            nonce=self.packet.nonce,
        )
        with self.assertRaises(InvalidTag):
            self.crypto.bob_receive(bad)

    def test_tamper_auth_tag_byte_raises_invalid_tag(self) -> None:
        """
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
        )
        with self.assertRaises(InvalidTag):
            self.crypto.bob_receive(bad)

    # --- Tamper: nonce --------------------------------------------------------

    def test_tamper_nonce_raises_invalid_tag(self) -> None:
        """Nonce'un değiştirilmesi deşifre adımında başarısız olmalı."""
        tampered_nonce = bytearray(self.packet.nonce)
        tampered_nonce[0] ^= 0xFF
        bad = EncryptedPacket(
            encrypted_message=self.packet.encrypted_message,
            encrypted_session_key=self.packet.encrypted_session_key,
            nonce=bytes(tampered_nonce),
        )
        with self.assertRaises(InvalidTag):
            self.crypto.bob_receive(bad)

    # --- Tamper: şifreli oturum anahtarı --------------------------------------

    def test_tamper_encrypted_session_key_raises(self) -> None:
        """
        RSA-OAEP şifreli oturum anahtarının değiştirilmesi OAEP çözme
        aşamasında istisna üretmeli (ValueError tabanlı).
        """
        tampered_key = bytearray(self.packet.encrypted_session_key)
        tampered_key[0] ^= 0x01
        bad = EncryptedPacket(
            encrypted_message=self.packet.encrypted_message,
            encrypted_session_key=bytes(tampered_key),
            nonce=self.packet.nonce,
        )
        # OAEP çözme başarısız olursa bir istisna (genelde ValueError) oluşur
        with self.assertRaises(Exception):
            self.crypto.bob_receive(bad)

    # --- Tamper: imza (AES altında bile) --------------------------------------

    def test_tamper_message_plaintext_before_encrypt_breaks_signature(
        self,
    ) -> None:
        """
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
            session_key, self.packet.nonce, self.packet.encrypted_message
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
        """
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
    """EncryptedPacket veri modelinin sadeleştirilmiş hâlini doğrular."""

    def test_packet_has_no_tag_field(self) -> None:
        """GCM tag ayrı alan olarak taşınmıyor — sadece 3 alan olmalı."""
        from dataclasses import fields
        field_names = {f.name for f in fields(EncryptedPacket)}
        self.assertEqual(
            field_names,
            {"encrypted_message", "encrypted_session_key", "nonce"},
        )


class TestMessageSignatureFraming(unittest.TestCase):
    """m ∥ imza çerçeveleme (framing) testleri — ayraç çarpışmalarına
    karşı bağışık olduğunu doğrular."""

    def setUp(self) -> None:
        self.crypto = CryptoCore()
        self.crypto.setup_keys()

    def test_message_containing_old_separator_roundtrips(self) -> None:
        """
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
        """
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
        nonce, ct = self.crypto.aes_gcm_encrypt(key, short)
        enc_session = self.crypto.rsa_encrypt_key(
            self.crypto.bob_keys.public_key, key
        )
        bad = EncryptedPacket(
            encrypted_message=ct,
            encrypted_session_key=enc_session,
            nonce=nonce,
        )
        with self.assertRaises(ValueError):
            self.crypto.bob_receive(bad)

    def test_signature_is_always_256_bytes(self) -> None:
        """RSA-2048 PSS imzası sabit 256 byte üretir — framing varsayımını
        doğrular."""
        for raw in (b"a", b"x" * 1024, "çöğüışÇÖĞÜŞİ".encode("utf-8")):
            h = self.crypto.sha256_hash(raw)
            sig = self.crypto.rsa_sign(
                self.crypto.alice_keys.private_key, h
            )
            self.assertEqual(len(sig), self.crypto.SIGNATURE_LEN)


if __name__ == "__main__":
    unittest.main()
