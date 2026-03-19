"""
crypto_core.py – Kriptografi İş Mantığı (Backend)
==================================================
Secure Email Authentication and Message Integrity projesi için
SHA-256, RSA-2048 ve AES-256-GCM tabanlı hibrit kriptografik iş akışı.

Erciyes Üniversitesi – Bilgisayar Mühendisliği Bitirme Projesi
Berkay Aydemir – 1030521387
Danışman: Prof. Dr. Serkan ÖZTÜRK
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateKey,
    RSAPublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ---------------------------------------------------------------------------
# Veri Sınıfları (Data Classes)
# ---------------------------------------------------------------------------

@dataclass
class RSAKeyPair:
    """RSA-2048 anahtar çifti."""

    private_key: RSAPrivateKey
    public_key: RSAPublicKey

    def private_pem(self) -> bytes:
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def public_pem(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )


@dataclass
class EncryptedPacket:
    """Alice → Bob iletimi için şifreli paket."""

    encrypted_message: bytes       # AES-256-GCM ile şifrelenmiş (mesaj ∥ imza)
    encrypted_session_key: bytes   # RSA ile şifrelenmiş oturum anahtarı K_S
    nonce: bytes                   # AES-GCM rastgele sayısı (12 byte)
    tag: bytes = b""               # GCM kimlik doğrulama etiketi


@dataclass
class StepResult:
    """Her kriptografik adımın ara sonuçlarını tutar."""

    step_number: int
    step_name: str
    description: str
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Ana Kriptografi Sınıfı
# ---------------------------------------------------------------------------

class CryptoCore:
    """Hibrit kriptografik iş akışını yöneten ana sınıf."""

    AES_KEY_SIZE: int = 32
    AES_NONCE_SIZE: int = 12
    RSA_KEY_SIZE: int = 2048
    SEPARATOR: bytes = b"||SIGNATURE_BOUNDARY||"

    def __init__(self) -> None:
        self.alice_keys: Optional[RSAKeyPair] = None
        self.bob_keys: Optional[RSAKeyPair] = None
        self._session_key: Optional[bytes] = None

    # ------------------------------------------------------------------
    # Anahtar Üretimi
    # ------------------------------------------------------------------

    def generate_rsa_keypair(self) -> RSAKeyPair:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.RSA_KEY_SIZE,
        )
        return RSAKeyPair(
            private_key=private_key,
            public_key=private_key.public_key(),
        )

    def setup_keys(self) -> Tuple[RSAKeyPair, RSAKeyPair]:
        self.alice_keys = self.generate_rsa_keypair()
        self.bob_keys = self.generate_rsa_keypair()
        return self.alice_keys, self.bob_keys

    # ------------------------------------------------------------------
    # SHA-256 Özet Hesaplama
    # ------------------------------------------------------------------

    @staticmethod
    def sha256_hash(data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    @staticmethod
    def sha256_hex(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    # ------------------------------------------------------------------
    # RSA Dijital İmza
    # ------------------------------------------------------------------

    @staticmethod
    def rsa_sign(private_key: RSAPrivateKey, message_hash: bytes) -> bytes:
        return private_key.sign(
            message_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

    @staticmethod
    def rsa_verify(
        public_key: RSAPublicKey,
        signature: bytes,
        message_hash: bytes,
    ) -> bool:
        try:
            public_key.verify(
                signature,
                message_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # AES-256-GCM Simetrik Şifreleme
    # ------------------------------------------------------------------

    def generate_session_key(self) -> bytes:
        self._session_key = os.urandom(self.AES_KEY_SIZE)
        return self._session_key

    def aes_gcm_encrypt(self, key: bytes, plaintext: bytes) -> Tuple[bytes, bytes]:
        nonce = os.urandom(self.AES_NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce, ciphertext

    @staticmethod
    def aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    # ------------------------------------------------------------------
    # RSA ile Oturum Anahtarı Şifreleme
    # ------------------------------------------------------------------

    @staticmethod
    def rsa_encrypt_key(public_key: RSAPublicKey, session_key: bytes) -> bytes:
        return public_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    @staticmethod
    def rsa_decrypt_key(private_key: RSAPrivateKey, encrypted_key: bytes) -> bytes:
        return private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    # ------------------------------------------------------------------
    # Tam İş Akışı — Gönderici (Alice) Tarafı
    # ------------------------------------------------------------------

    def alice_send(self, message: str) -> Tuple[EncryptedPacket, list[StepResult]]:
        """Alice'in tam gönderim iş akışını gerçekleştirir (zamanlama ile)."""
        if not self.alice_keys or not self.bob_keys:
            raise RuntimeError(
                "Anahtarlar oluşturulmadı. Önce setup_keys() çağrılmalı."
            )

        steps: list[StepResult] = []
        msg_bytes = message.encode("utf-8")

        # Adım 1: SHA-256 özet hesaplama — H(m)
        t0 = time.perf_counter()
        msg_hash = self.sha256_hash(msg_bytes)
        elapsed_1 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=1,
            step_name="SHA-256 Özet Hesaplama",
            description="Mesaj içeriğinden 256-bit özet değeri H(m) üretildi.",
            data={
                "message": message,
                "hash_hex": msg_hash.hex(),
                "hash_bytes": msg_hash,
                "elapsed_ms": f"{elapsed_1:.4f} ms",
            },
        ))

        # Adım 2: RSA dijital imza — K⁻_A(H(m))
        t0 = time.perf_counter()
        signature = self.rsa_sign(self.alice_keys.private_key, msg_hash)
        elapsed_2 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=2,
            step_name="RSA-2048 Dijital İmza",
            description=(
                "Özet değeri H(m), Alice'in RSA gizli anahtarı (K⁻_A) ile "
                "imzalanarak dijital imza oluşturuldu."
            ),
            data={
                "signature_hex": signature.hex(),
                "signature_bytes": signature,
                "key_info": "Alice RSA-2048 Gizli Anahtar (K⁻_A)",
                "elapsed_ms": f"{elapsed_2:.2f} ms",
            },
        ))

        # Adım 3: Mesaj ve imzanın birleştirilmesi — m ∥ K⁻_A(H(m))
        t0 = time.perf_counter()
        combined = msg_bytes + self.SEPARATOR + signature
        elapsed_3 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=3,
            step_name="Mesaj ve İmza Birleştirme",
            description=(
                "Orijinal mesaj (m) ile dijital imza K⁻_A(H(m)) "
                "birleştirildi: m ∥ İmza"
            ),
            data={
                "combined_size": f"{len(combined)} byte",
                "message_size": f"{len(msg_bytes)} byte",
                "signature_size": f"{len(signature)} byte",
                "elapsed_ms": f"{elapsed_3:.4f} ms",
            },
        ))

        # Adım 4: AES-256-GCM simetrik şifreleme
        t0 = time.perf_counter()
        session_key = self.generate_session_key()
        nonce, ciphertext = self.aes_gcm_encrypt(session_key, combined)
        elapsed_4 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=4,
            step_name="AES-256-GCM Şifreleme",
            description=(
                "Birleştirilmiş veri, yeni üretilen simetrik oturum "
                "anahtarı (K_S) ile AES-256-GCM kullanılarak şifrelendi."
            ),
            data={
                "session_key_hex": session_key.hex(),
                "nonce_hex": nonce.hex(),
                "ciphertext_size": f"{len(ciphertext)} byte",
                "ciphertext_hex_preview": ciphertext[:32].hex() + "...",
                "elapsed_ms": f"{elapsed_4:.4f} ms",
            },
        ))

        # Adım 5: Oturum anahtarını RSA ile şifrele — K⁺_B(K_S)
        t0 = time.perf_counter()
        encrypted_session_key = self.rsa_encrypt_key(
            self.bob_keys.public_key, session_key
        )
        elapsed_5 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=5,
            step_name="RSA Oturum Anahtarı Şifreleme",
            description=(
                "Oturum anahtarı (K_S), Bob'un RSA açık anahtarı (K⁺_B) "
                "ile şifrelenerek güvenli biçimde iletilmeye hazırlandı."
            ),
            data={
                "encrypted_key_hex": encrypted_session_key.hex(),
                "encrypted_key_size": f"{len(encrypted_session_key)} byte",
                "key_info": "Bob RSA-2048 Açık Anahtar (K⁺_B)",
                "elapsed_ms": f"{elapsed_5:.2f} ms",
            },
        ))

        # Adım 6: Paket oluştur ve gönder
        packet = EncryptedPacket(
            encrypted_message=ciphertext,
            encrypted_session_key=encrypted_session_key,
            nonce=nonce,
        )
        total_size = len(ciphertext) + len(encrypted_session_key) + len(nonce)
        steps.append(StepResult(
            step_number=6,
            step_name="Paket Gönderimi",
            description=(
                "Şifreli mesaj K_S(m ∥ K⁻_A(H(m))) ve şifreli oturum "
                "anahtarı K⁺_B(K_S) birlikte Bob'a iletildi."
            ),
            data={
                "total_packet_size": f"{total_size} byte",
                "nonce_hex": nonce.hex(),
            },
        ))

        return packet, steps

    # ------------------------------------------------------------------
    # Tam İş Akışı — Alıcı (Bob) Tarafı
    # ------------------------------------------------------------------

    def bob_receive(
        self, packet: EncryptedPacket
    ) -> Tuple[str, bool, list[StepResult]]:
        """Bob'un tam alım ve doğrulama iş akışını gerçekleştirir (zamanlama ile)."""
        if not self.alice_keys or not self.bob_keys:
            raise RuntimeError(
                "Anahtarlar oluşturulmadı. Önce setup_keys() çağrılmalı."
            )

        steps: list[StepResult] = []

        # Adım 1: RSA ile oturum anahtarını çöz — K⁻_B(K⁺_B(K_S)) = K_S
        t0 = time.perf_counter()
        session_key = self.rsa_decrypt_key(
            self.bob_keys.private_key, packet.encrypted_session_key
        )
        elapsed_1 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=1,
            step_name="RSA Oturum Anahtarı Çözme",
            description=(
                "Bob, kendi RSA gizli anahtarı (K⁻_B) ile şifreli oturum "
                "anahtarını çözerek K_S değerini elde etti."
            ),
            data={
                "session_key_hex": session_key.hex(),
                "key_info": "Bob RSA-2048 Gizli Anahtar (K⁻_B)",
                "elapsed_ms": f"{elapsed_1:.2f} ms",
            },
        ))

        # Adım 2: AES-256-GCM ile deşifrele
        t0 = time.perf_counter()
        combined = self.aes_gcm_decrypt(
            session_key, packet.nonce, packet.encrypted_message
        )
        elapsed_2 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=2,
            step_name="AES-256-GCM Deşifreleme",
            description=(
                "Elde edilen K_S ile şifreli veri çözülerek orijinal mesaj "
                "(m) ve dijital imza K⁻_A(H(m)) ayrıştırıldı."
            ),
            data={
                "combined_size": f"{len(combined)} byte",
                "elapsed_ms": f"{elapsed_2:.4f} ms",
            },
        ))

        # Adım 3: Mesaj ve imzayı ayır
        parts = combined.split(self.SEPARATOR, 1)
        if len(parts) != 2:
            raise ValueError("Mesaj ve imza ayrıştırılamadı.")
        msg_bytes, signature = parts[0], parts[1]
        message = msg_bytes.decode("utf-8")
        steps.append(StepResult(
            step_number=3,
            step_name="Mesaj ve İmza Ayrıştırma",
            description="Mesaj (m) ve dijital imza birbirinden ayrıştırıldı.",
            data={
                "message": message,
                "signature_hex": signature.hex(),
                "message_size": f"{len(msg_bytes)} byte",
                "signature_size": f"{len(signature)} byte",
            },
        ))

        # Adım 4: SHA-256 özetini yeniden hesapla — H(m)
        t0 = time.perf_counter()
        msg_hash = self.sha256_hash(msg_bytes)
        elapsed_4 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=4,
            step_name="SHA-256 Özet Yeniden Hesaplama",
            description=(
                "Bob, aldığı mesajdan bağımsız olarak SHA-256 özetini "
                "yeniden hesapladı: H(m)."
            ),
            data={
                "hash_hex": msg_hash.hex(),
                "hash_bytes": msg_hash,
                "elapsed_ms": f"{elapsed_4:.4f} ms",
            },
        ))

        # Adım 5: RSA ile imza doğrula — K⁺_A ile doğrulama
        t0 = time.perf_counter()
        is_valid = self.rsa_verify(
            self.alice_keys.public_key, signature, msg_hash
        )
        elapsed_5 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=5,
            step_name="RSA İmza Doğrulama ve Bütünlük Kontrolü",
            description=(
                "Bob, Alice'in RSA açık anahtarı (K⁺_A) ile dijital imzayı "
                "doğruladı. "
                + ("✅ İmza GEÇERLİ — Kimlik ve bütünlük doğrulandı!"
                   if is_valid
                   else "❌ İmza GEÇERSİZ — Kimlik veya bütünlük ihlali!")
            ),
            data={
                "message": message,
                "hash_hex": msg_hash.hex(),
                "verification_result": is_valid,
                "key_info": "Alice RSA-2048 Açık Anahtar (K⁺_A)",
                "elapsed_ms": f"{elapsed_5:.2f} ms",
            },
        ))

        return message, is_valid, steps
