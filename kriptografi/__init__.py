# kriptografi/__init__.py
"""
Kriptografi çekirdeği — UI'dan bağımsız kripto ve iş katmanı.

İçindekiler:
    crypto_core    : RSA-2048 + AES-256-GCM + SHA-256 hibrit akış (cryptography lib)
    crypto_workers : QThread worker'ları (KeygenWorker, AliceSendWorker, BobReceiveWorker)
    utils          : Qt-bağımsız yardımcılar (exception formatlama, FRIENDLY_NAMES,
                     constant_time_equal). GUI yardımcıları arayuz/widget_utils.py'dedir.

Kullanım:
    from kriptografi.crypto_core import CryptoCore, EncryptedPacket
    from kriptografi.crypto_workers import KeygenWorker
"""
