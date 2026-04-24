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
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidSignature


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
    """Alice → Bob iletimi için şifreli paket.

    AES-GCM çıktısı ``ciphertext || tag`` biçiminde tek alanda
    taşınır (PyCA ``AESGCM`` API'si bu şekilde döndürür); ayrı bir
    ``tag`` alanı tutulmaz.

    ``associated_data`` alanı AES-GCM'in AAD (Additional Authenticated
    Data) girdisidir: şifrelenmez ama GCM tag'i tarafından kimlik
    doğrulaması altına alınır. Böylece protokol sürümü / gönderen
    kimliği / zaman damgası gibi bağlam paketin bütünlüğüne
    bağlanmış olur; bu alandaki herhangi bir değişiklik deşifrelemeyi
    başarısız kılar (InvalidTag).
    """

    encrypted_message: bytes       # AES-256-GCM ile şifrelenmiş (mesaj ∥ imza) + 16 byte auth tag
    encrypted_session_key: bytes   # RSA-OAEP ile şifrelenmiş oturum anahtarı K_S
    nonce: bytes                   # AES-GCM rastgele sayısı (12 byte)
    associated_data: bytes         # AES-GCM AAD — şifrelenmez, ama tag ile bütünlüğü korunur


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
    # RSA-2048 PSS imzası her zaman sabit 256 byte üretir; bu nedenle
    # mesaj ∥ imza birleşiminde ayraç (delimiter) kullanmak yerine
    # "son 256 byte = imza, kalanı = mesaj" kuralı uygulanır. Böylece
    # kullanıcı mesajının ayraç string'ini içermesi durumunda oluşan
    # ayrıştırma bozulması riski tamamen ortadan kalkar.
    SIGNATURE_LEN: int = 256
    # Protokol kimliği — AAD'nin sabit ön eki olarak kullanılır; sürüm
    # değişirse bu etiket değişir ve eski alıcılar paketi reddeder.
    PROTOCOL_TAG: bytes = b"secure-email-auth/v1"

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
    # Not: Mesajın özeti H(m) zaten hesaplanmış olarak geldiği için
    # ``Prehashed(SHA256())`` kullanılır; aksi hâlde kütüphane aldığı
    # H(m)'i yeniden hashler ve anlatımla ("H(m) imzalanır") çakışır.

    @staticmethod
    def rsa_sign(private_key: RSAPrivateKey, message_hash: bytes) -> bytes:
        if len(message_hash) != 32:
            raise ValueError("message_hash 32 byte (SHA-256) olmalı.")
        return private_key.sign(
            message_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            Prehashed(hashes.SHA256()),
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
                Prehashed(hashes.SHA256()),
            )
            return True
        except InvalidSignature:
            return False

    # ------------------------------------------------------------------
    # AES-256-GCM Simetrik Şifreleme
    # ------------------------------------------------------------------

    def generate_session_key(self) -> bytes:
        self._session_key = os.urandom(self.AES_KEY_SIZE)
        return self._session_key

    def aes_gcm_encrypt(
        self,
        key: bytes,
        plaintext: bytes,
        associated_data: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes]:
        """AES-256-GCM ile şifreleme.

        ``associated_data`` (AAD) verilirse, şifrelenmez ancak GCM tag'i
        tarafından kimlik doğrulaması altına alınır. Aynı AAD'nin
        decrypt çağrısında verilmesi zorunludur; aksi hâlde
        ``InvalidTag`` hatası oluşur.
        """
        nonce = os.urandom(self.AES_NONCE_SIZE)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce, ciphertext

    @staticmethod
    def aes_gcm_decrypt(
        key: bytes,
        nonce: bytes,
        ciphertext: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """AES-256-GCM ile deşifre.

        Eğer şifreleme sırasında AAD kullanıldıysa deşifrede de aynısı
        verilmelidir; AAD'de herhangi bir değişiklik ``InvalidTag``
        fırlatır.
        """
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, associated_data)

    # ------------------------------------------------------------------
    # AAD İnşası — protokol sürümü + gönderen parmak izi + zaman damgası
    # ------------------------------------------------------------------

    @classmethod
    def build_aad(
        cls,
        sender_public_key: RSAPublicKey,
        timestamp: Optional[int] = None,
    ) -> bytes:
        """Pakete bağlanacak AAD'yi inşa eder.

        Biçim (ASCII, okunabilir):
            ``secure-email-auth/v1|from=<fp16hex>|ts=<unix>``

        - ``fp16hex``: gönderen açık anahtarının DER kodlu PEM'inin
          SHA-256 özetinin ilk 8 byte'ının hex gösterimi (16 karakter).
        - ``unix``: Unix zaman damgası (saniye).

        AAD şifrelenmez ama GCM tag ile korunur; böylece protokol
        sürümü, gönderen kimliği ve zaman bağlamı ciphertext'e bağlanır.
        """
        if timestamp is None:
            timestamp = int(time.time())
        pem = sender_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        fingerprint = hashlib.sha256(pem).digest()[:8].hex()
        return (
            cls.PROTOCOL_TAG
            + b"|from="
            + fingerprint.encode("ascii")
            + b"|ts="
            + str(timestamp).encode("ascii")
        )

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
        # RSA-2048 PSS imzası sabit 256 byte olduğu için ayraç (delimiter)
        # gerekmez; Bob ayrıştırmada son 256 byte'ı imza olarak alır.
        t0 = time.perf_counter()
        if len(signature) != self.SIGNATURE_LEN:
            raise ValueError(
                f"Beklenmedik imza uzunluğu: {len(signature)} byte "
                f"(beklenen: {self.SIGNATURE_LEN} byte)."
            )
        combined = msg_bytes + signature
        elapsed_3 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=3,
            step_name="Mesaj ve İmza Birleştirme",
            description=(
                "Orijinal mesaj (m) ile dijital imza K⁻_A(H(m)) "
                "birleştirildi: m ∥ İmza. İmza her zaman sabit "
                f"{self.SIGNATURE_LEN} byte (RSA-2048 PSS) olduğu için "
                "ayıraç (delimiter) kullanılmaz; Bob deşifre ettikten "
                "sonra son 256 byte'ı imza olarak alır."
            ),
            data={
                "combined_size": f"{len(combined)} byte",
                "message_size": f"{len(msg_bytes)} byte",
                "signature_size": f"{len(signature)} byte",
                "elapsed_ms": f"{elapsed_3:.4f} ms",
            },
        ))

        # Adım 4: AES-256-GCM simetrik şifreleme (AAD ile bağlamsal bağlama)
        # AAD: protokol sürümü + Alice'in açık anahtar parmak izi + zaman
        # damgası. Şifrelenmez ama GCM tag bu veriyi de imzalar; paket
        # üstünden AAD değiştirilirse Bob InvalidTag alır.
        t0 = time.perf_counter()
        session_key = self.generate_session_key()
        aad = self.build_aad(self.alice_keys.public_key)
        nonce, ciphertext = self.aes_gcm_encrypt(session_key, combined, aad)
        elapsed_4 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=4,
            step_name="AES-256-GCM Şifreleme",
            description=(
                "Birleştirilmiş veri, yeni üretilen simetrik oturum "
                "anahtarı (K_S) ile AES-256-GCM kullanılarak şifrelendi. "
                "AAD (Additional Authenticated Data) olarak protokol "
                "sürümü, Alice'in açık anahtar parmak izi ve zaman "
                "damgası pakete bağlandı; bu alan şifrelenmez ama "
                "GCM kimlik doğrulama etiketi ile bütünlüğü korunur."
            ),
            data={
                "session_key_hex": session_key.hex(),
                "nonce_hex": nonce.hex(),
                "ciphertext_size": f"{len(ciphertext)} byte",
                "ciphertext_hex_preview": ciphertext[:32].hex() + "...",
                "associated_data": aad.decode("ascii"),
                "associated_data_size": f"{len(aad)} byte",
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
            associated_data=aad,
        )
        total_size = (
            len(ciphertext)
            + len(encrypted_session_key)
            + len(nonce)
            + len(aad)
        )
        steps.append(StepResult(
            step_number=6,
            step_name="Paket Gönderimi",
            description=(
                "Şifreli mesaj K_S(m ∥ K⁻_A(H(m))), şifreli oturum "
                "anahtarı K⁺_B(K_S), rastgele nonce ve AAD (bağlamsal "
                "metadata) birlikte Bob'a iletildi."
            ),
            data={
                "total_packet_size": f"{total_size} byte",
                "nonce_hex": nonce.hex(),
                "associated_data": aad.decode("ascii"),
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

        # Adım 2: AES-256-GCM ile deşifrele (AAD doğrulaması ile birlikte)
        # AAD paketle birlikte gelir ve aynı değer decrypt'e verilir;
        # AAD üzerinde herhangi bir değişiklik tag doğrulamasını bozar
        # ve InvalidTag fırlatılır.
        t0 = time.perf_counter()
        combined = self.aes_gcm_decrypt(
            session_key,
            packet.nonce,
            packet.encrypted_message,
            packet.associated_data,
        )
        elapsed_2 = (time.perf_counter() - t0) * 1000
        steps.append(StepResult(
            step_number=2,
            step_name="AES-256-GCM Deşifreleme",
            description=(
                "Elde edilen K_S ile şifreli veri çözüldü. Bu adımda "
                "AAD de (paket üstünde açık gelen bağlamsal veri) "
                "GCM kimlik doğrulama etiketiyle birlikte kontrol "
                "edildi; AAD üzerinde en ufak bir değişiklik olsaydı "
                "deşifreleme InvalidTag hatası verirdi."
            ),
            data={
                "combined_size": f"{len(combined)} byte",
                "associated_data": packet.associated_data.decode(
                    "ascii", errors="replace"
                ),
                "elapsed_ms": f"{elapsed_2:.4f} ms",
            },
        ))

        # Adım 3: Mesaj ve imzayı ayır
        # Sabit-uzunluk kuralı: son SIGNATURE_LEN byte imza, kalanı mesajdır.
        # Bu yaklaşım ayraç (delimiter) çarpışmalarına karşı bağışıktır:
        # kullanıcı mesajı herhangi bir bayt dizisi içerebilir.
        if len(combined) < self.SIGNATURE_LEN:
            raise ValueError(
                f"Deşifre edilen paket çok kısa ({len(combined)} byte); "
                f"en az {self.SIGNATURE_LEN} byte imza bekleniyor."
            )
        msg_bytes = combined[:-self.SIGNATURE_LEN]
        signature = combined[-self.SIGNATURE_LEN:]
        message = msg_bytes.decode("utf-8")
        steps.append(StepResult(
            step_number=3,
            step_name="Mesaj ve İmza Ayrıştırma",
            description=(
                "Mesaj (m) ve dijital imza birbirinden ayrıştırıldı. "
                f"İmza sabit {self.SIGNATURE_LEN} byte olduğu için ayıraç "
                "aranmadı; son 256 byte imza, kalanı mesajdır."
            ),
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
