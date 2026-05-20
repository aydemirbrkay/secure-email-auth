# cekirdek/__init__.py
"""
Kriptografi çekirdeği — UI'dan bağımsız kripto ve iş katmanı.

İçindekiler:
    crypto_core    : RSA-2048 + AES-256-GCM + SHA-256 hibrit akış (cryptography lib)
    crypto_workers : QThread worker'ları (KeygenWorker, AliceSendWorker, BobReceiveWorker)
    utils          : Yardımcılar (icon/svg yükleme, exception formatlama, step content)

Kullanım:
    from cekirdek.crypto_core import CryptoCore, EncryptedPacket
    from cekirdek.crypto_workers import KeygenWorker
"""
