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
    """Dijital imza üretimi (RSA-PSS) sırasında oluşan hata.
    ``rsa_sign`` ham kütüphane hatasını bu tipe sarar."""


class EncryptError(CryptoError):
    """Şifreleme (AES-256-GCM) sırasında oluşan hata.
    ``aes_gcm_encrypt`` ham kütüphane hatasını bu tipe sarar."""


class DecryptError(CryptoError):
    """Çözme (decrypt) sırasında oluşan hata; örn. RSA-OAEP başarısız."""


class IntegrityError(CryptoError):
    """Bütünlük/kimlik doğrulama hatası; örn. AES-GCM tag uyuşmazlığı."""


class PacketFormatError(CryptoError):
    """Paket yapısı / sürüm / uzunluk beklentisi ihlali."""


class ReplayDetectedError(CryptoError):
    """Aynı paketin tekrar alındığı (replay) tespiti.
    ``_check_freshness_and_replay`` tarafından fırlatılır."""


class StaleTimestampError(CryptoError):
    """Paketin zaman damgası kabul edilebilir aralığın dışında.
    ``_check_freshness_and_replay`` tarafından fırlatılır."""
