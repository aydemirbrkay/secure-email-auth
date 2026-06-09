"""
errors.py – Tipli Kriptografi İstisna Hiyerarşisi
=================================================
Çekirdek kripto akışındaki hataları tek bir kök altında toplar.

Neden tipli hiyerarşi: UI/worker katmanı ham ``InvalidTag`` /
``InvalidSignature`` gibi kütüphane istisnalarını yakalamak yerine
``CryptoError`` ailesini yakalayabilir; böylece hata sınıflandırması
(bütünlük, imza, format, replay vb.) öğretici ve okunabilir kalır.
"""

from __future__ import annotations


class CryptoError(Exception):
    """Tüm kriptografi hatalarının kök sınıfı."""


class KeygenError(CryptoError):
    """Anahtar üretimi sırasında oluşan hata."""


class SignError(CryptoError):
    """Dijital imza üretimi sırasında oluşan hata."""


class VerifyError(CryptoError):
    """İmza doğrulamasının başarısız olduğu durum (geçersiz imza)."""


class EncryptError(CryptoError):
    """Şifreleme sırasında oluşan hata."""


class DecryptError(CryptoError):
    """Çözme (decrypt) sırasında oluşan hata; örn. RSA-OAEP başarısız."""


class IntegrityError(CryptoError):
    """Bütünlük/kimlik doğrulama hatası; örn. AES-GCM tag uyuşmazlığı."""


class PacketFormatError(CryptoError):
    """Paket yapısı / sürüm / uzunluk beklentisi ihlali."""


class ReplayDetectedError(CryptoError):
    """Aynı paketin tekrar alındığı (replay) tespiti. (Sonraki görevde kullanılacak.)"""


class StaleTimestampError(CryptoError):
    """Paketin zaman damgası kabul edilebilir aralığın dışında. (Sonraki görevde kullanılacak.)"""
