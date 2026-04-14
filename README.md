<div align="center">

# Güvenli E-posta Kimlik Doğrulama ve Mesaj Bütünlüğü Sistemi

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Cryptography](https://img.shields.io/badge/cryptography-44.0%2B-red?style=for-the-badge&logo=letsencrypt&logoColor=white)](https://cryptography.io/)
[![License](https://img.shields.io/badge/Lisans-Akademik-yellow?style=for-the-badge)](LICENSE)

**Erciyes Üniversitesi — Bilgisayar Mühendisliği Bölümü**
**Bitirme Projesi • 2025**

*Berkay Aydemir — 1030521387*
*Danışman: Prof. Dr. Serkan ÖZTÜRK*

---

</div>

## Proje Hakkında

Bu proje, **güvenli e-posta iletişiminde** üç temel kriptografik güvenlik özelliğini birleştiren eğitici bir hibrit şifreleme sistemidir. **Alice → Bob** iletişim senaryosu üzerinden, gerçek dünya uygulamalarında kullanılan kriptografik iş akışlarını adım adım görselleştirir ve her algoritmanın iç işleyişini animasyonlu şekilde sunar.

### Güvenlik Özellikleri

| Özellik | Mekanizma | Algoritma |
|---------|-----------|-----------|
| **Gizlilik** (Confidentiality) | Mesaj şifreleme | AES-256-GCM |
| **Bütünlük** (Integrity) | Özet + kimlik doğrulama etiketi | SHA-256 + GCM Auth Tag |
| **Kimlik Doğrulama** (Authentication) | Dijital imza | RSA-2048 PSS |
| **İnkar Edememe** (Non-repudiation) | Özel anahtar ile imzalama | RSA-2048 PSS |

---

## Sistem Mimarisi

Proje, **hibrit şifreleme** paradigmasını uygular: RSA'nın asimetrik gücü ile AES'in simetrik hızı birleştirilerek hem güvenli hem de verimli bir iletişim kanalı oluşturulur.

### Alice (Gönderici) — 6 Adım

```
Mesaj (m)
    │
    ▼ Adım 1 ─── SHA-256 ──────────────────────────► H(m)  [256-bit özet]
    │                                                    │
    ▼ Adım 2 ─── RSA-2048 PSS (K⁻_A) ──────────────► K⁻_A(H(m))  [Dijital İmza]
    │
    ▼ Adım 3 ─── Birleştirme ────────────────────────► m ∥ K⁻_A(H(m))
    │
    ▼ Adım 4 ─── AES-256-GCM (K_S) ─────────────────► Şifreli Veri + Auth Tag
    │
    ▼ Adım 5 ─── RSA-2048 OAEP (K⁺_B) ──────────────► K⁺_B(K_S)  [Şifreli Oturum Anahtarı]
    │
    ▼ Adım 6 ─── Paket Gönderimi ────────────────────► { Şifreli Mesaj, K⁺_B(K_S), Nonce }
```

### Bob (Alıcı) — 5 Adım

```
{ Şifreli Mesaj, K⁺_B(K_S), Nonce }
    │
    ▼ Adım 1 ─── RSA-2048 OAEP (K⁻_B) ──────────────► K_S  [Oturum Anahtarı]
    │
    ▼ Adım 2 ─── AES-256-GCM Deşifre (K_S) ─────────► m ∥ K⁻_A(H(m))
    │
    ▼ Adım 3 ─── Ayrıştırma ─────────────────────────► m  &  İmza
    │
    ▼ Adım 4 ─── SHA-256 (m) ───────────────────────► H(m)  [Yeniden hesaplama]
    │
    ▼ Adım 5 ─── RSA Doğrulama (K⁺_A) ──────────────► GEÇERLI  / GEÇERSIZ
```

---

## Proje Yapısı

```
bitirme_odevi/
├── main_gui.py                     # Ana uygulama penceresi ve iş akışı yöneticisi
├── alice_panel.py                  # Alice (gönderici) paneli ve animasyon konteyneri
├── bob_panel.py                    # Bob (alıcı) paneli ve diyagram bileşeni
├── crypto_core.py                  # Kriptografik iş mantığı (backend)
├── theme.py                        # Renk paleti ve tema sabitleri
├── toast.py                        # Doğrulama bildirimi bileşeni (VerificationToast)
├── utils.py                        # Yardımcı fonksiyonlar (adım kutusu, renk hesaplama)
├── animation_modals/
│   ├── base.py                     # CryptoAnimationWindow temel sınıfı
│   ├── matrix_widget.py            # AES durum matrisi görselleştirme bileşeni
│   ├── aes_animation.py            # AES-256 adım adım animasyon penceresi
│   ├── aes_pure.py                 # Saf Python AES-256 (14 turlu durum verisi)
│   ├── rsa_animation.py            # RSA animasyon penceresi (7 eğitim adımı)
│   ├── sha256_animation.py         # SHA-256 animasyon penceresi (diyagram + blok zinciri)
│   └── sha256_pure.py              # Saf Python SHA-256 (adım verisi)
├── icons/                          # SVG ve PNG ikon dosyaları
├── crypto_core.py                  # Kriptografik arka uç
├── test_crypto_core.py             # Birim testleri (26 test senaryosu)
├── test_aes_pure.py                # Saf AES implementasyonu testleri
├── test_sha256_pure.py             # Saf SHA-256 implementasyonu testleri
├── test_diagram_rects.py           # Diyagram dikdörtgen sınır testleri
├── requirements.txt                # Python bağımlılıkları
└── Thesis.pdf                      # Bitirme tezi belgesi
```

---

## Animasyon Modülleri

Proje, her kriptografik algoritmanın iç işleyişini görselleştiren bağımsız animasyon pencereleri içerir. Bu pencereler Alice panelinin içine gömülü olarak çalışır.

### AES-256 Animasyonu (`animation_modals/aes_animation.py`)
- Giriş animasyonu ve tıklanabilir tur çubuğu
- 14 tura ait durum matrisi görselleştirmesi (`MatrixWidget`)
- ShiftRows ve MixColumns adımları için ok gösterimi
- İleri/geri manuel navigasyon

### RSA Animasyonu (`animation_modals/rsa_animation.py`)
- 7 adımlı manuel eğitim akışı
- Anahtar üretimi, imzalama ve doğrulama adımları
- Her adımda matematiksel formül gösterimi

### SHA-256 Animasyonu (`animation_modals/sha256_animation.py`)
- QPainter tabanlı sıkıştırma diyagramı
- W, K, T1, T2 değerleriyle tur anlık görüntüleri
- Blok zinciri görünümü

---

## Uygulanan Algoritmalar

### 1. SHA-256 — Mesaj Özeti

**Kullanıldığı Yer:** `crypto_core.py` — `sha256_hash()`, `sha256_hex()`

```python
return hashlib.sha256(data).digest()
```

FIPS 180-4 standardında tanımlı SHA-256, herhangi bir boyuttaki girdi için sabit 256-bit özet üretir. Projede hem imza oluşturma hem de bütünlük doğrulamasında kullanılır.

**Kaynak:** [NIST FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)

---

### 2. RSA-2048 Dijital İmza — PSS Dolgusu

**Kullanıldığı Yer:** `crypto_core.py` — `rsa_sign()`, `rsa_verify()`

```python
private_key.sign(
    message_hash,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH,
    ),
    hashes.SHA256(),
)
```

PSS (Probabilistic Signature Scheme) dolgusu, rastgele tuz kullanarak aynı mesajın her imzasını farklı kılar. 2048-bit modulus 112-bit güvenlik gücüne karşılık gelir (NIST SP 800-131A).

**Kaynak:** [RFC 8017 — PKCS #1 v2.2](https://www.rfc-editor.org/rfc/rfc8017.html)

---

### 3. AES-256-GCM — Kimlik Doğrulamalı Simetrik Şifreleme

**Kullanıldığı Yer:** `crypto_core.py` — `aes_gcm_encrypt()`, `aes_gcm_decrypt()`

```python
nonce = os.urandom(12)   # 96-bit rastgele nonce
aesgcm = AESGCM(key)
ciphertext = aesgcm.encrypt(nonce, plaintext, None)
```

AES-256-GCM, NIST SP 800-38D standardında tanımlı AEAD (Authenticated Encryption with Associated Data) modudur. 256-bit anahtar, 96-bit nonce ve 128-bit kimlik doğrulama etiketi kullanır.

**Kaynak:** [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final)

---

### 4. RSA-2048 OAEP — Oturum Anahtarı Şifreleme

**Kullanıldığı Yer:** `crypto_core.py` — `rsa_encrypt_key()`, `rsa_decrypt_key()`

```python
padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)
```

OAEP dolgusu seçili şifreli metin saldırılarına (CCA) karşı güvenlidir. Yalnızca 32 byte'lık oturum anahtarı şifrelenerek RSA'nın büyük veri dezavantajı ortadan kaldırılır.

**Kaynak:** [RFC 8017 — PKCS #1 v2.2, Bölüm 7](https://www.rfc-editor.org/rfc/rfc8017.html)

---

## Güvenlik Analizi

| Güvenlik Özelliği | Mekanizma | Saldırı Koruması |
|---|---|---|
| **Gizlilik** | AES-256-GCM | Pasif dinleme |
| **Bütünlük** | GCM Auth Tag + SHA-256 | Mesaj manipülasyonu |
| **Kimlik Doğrulama** | RSA-2048 PSS | Kimlik sahteciliği |
| **İnkar Edememe** | RSA özel anahtar imzası | Gönderici inkarı |
| **Tekrar Saldırısı Koruması** | Rastgele nonce (96-bit) | Replay attack |
| **İletme Gizliliği** | Her mesajda yeni oturum anahtarı | Anahtar ifşasında geçmiş mesaj güvenliği |

### Kriptografik Parametreler

```
RSA Anahtar Boyutu       : 2048-bit (112-bit güvenlik gücü, NIST SP 800-131A)
RSA Açık Üs (e)          : 65537 (F4 – Fermat 4. sayısı)
RSA İmza Dolgusu         : PSS (RFC 8017 §9.1)
RSA Şifreleme Dolgusu    : OAEP (RFC 8017 §7.1)
Simetrik Anahtar         : AES-256 (256-bit, NIST FIPS 197)
Şifreleme Modu           : GCM (Galois/Counter Mode, NIST SP 800-38D)
Nonce Uzunluğu           : 96-bit / 12 byte
Kimlik Doğrulama Etiketi : 128-bit
Özet Fonksiyonu          : SHA-256 (FIPS 180-4)
Maske Üretim Fonksiyonu  : MGF1(SHA-256) (RFC 8017 §B.2.1)
```

---

## Kurulum ve Çalıştırma

### Gereksinimler

- Python 3.9+
- pip

### Kurulum

```bash
# Repoyu klonlayın
git clone https://github.com/aydemirbrkay/secure-email-auth.git
cd secure-email-auth

# Sanal ortam oluşturun (önerilir)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Bağımlılıkları yükleyin
pip install -r requirements.txt
```

### Çalıştırma

```bash
python main_gui.py
```

### Testleri Çalıştırma

```bash
python -m pytest test_crypto_core.py test_aes_pure.py test_sha256_pure.py test_diagram_rects.py -v
```

---

## Test Kapsamı

| Test Dosyası | Test Sayısı | Kapsam |
|---|---|---|
| `test_crypto_core.py` | 26 | SHA-256, RSA, AES-GCM, uçtan uca iş akışı |
| `test_aes_pure.py` | — | Saf Python AES-256 implementasyonu |
| `test_sha256_pure.py` | — | Saf Python SHA-256 implementasyonu |
| `test_diagram_rects.py` | — | Diyagram dikdörtgen sınır kontrolleri |

---

## Bağımlılıklar

| Paket | Versiyon | Kullanım Amacı |
|---|---|---|
| [PyQt6](https://pypi.org/project/PyQt6/) | ≥ 6.6.0 | Masaüstü GUI ve animasyon çerçevesi |
| [cryptography](https://pypi.org/project/cryptography/) | ≥ 44.0.0 | RSA, AES-GCM kriptografik primitifler |

---

## Kaynakça

### Kriptografik Standartlar

| No | Standart | Kullanım Yeri |
|---|---|---|
| [1] | [NIST FIPS 180-4 — SHA-256](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) | `crypto_core.py` — `sha256_hash()`, `sha256_hex()` |
| [2] | [NIST SP 800-38D — AES-GCM](https://csrc.nist.gov/pubs/sp/800/38/d/final) | `crypto_core.py` — `aes_gcm_encrypt()`, `aes_gcm_decrypt()` |
| [3] | [RFC 8017 — PKCS #1 v2.2 (RSA)](https://www.rfc-editor.org/rfc/rfc8017.html) | `crypto_core.py` — `rsa_sign()`, `rsa_verify()`, `rsa_encrypt_key()` |
| [4] | [NIST SP 800-131A — Anahtar Uzunlukları](https://csrc.nist.gov/pubs/sp/800/131/a/r2/final) | `crypto_core.py` — `RSA_KEY_SIZE = 2048` |
| [5] | [NIST FIPS 197 — AES](https://csrc.nist.gov/pubs/fips/197/final) | `crypto_core.py` — `AES_KEY_SIZE = 32`, `AESGCM(key)` |

### Python Kütüphaneleri

| No | Kütüphane | Kullanım Yeri |
|---|---|---|
| [6] | [PyCA cryptography](https://cryptography.io/en/latest/) | `crypto_core.py` — tüm kriptografik işlemler |
| [7] | [Python hashlib](https://docs.python.org/3/library/hashlib.html) | `crypto_core.py` — `hashlib.sha256()` |
| [8] | [Python os.urandom](https://docs.python.org/3/library/os.html#os.urandom) | `crypto_core.py` — oturum anahtarı ve nonce üretimi |
| [9] | [PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/) | `main_gui.py`, `alice_panel.py`, `bob_panel.py`, `animation_modals/` |

---

## Lisans

Bu proje **Erciyes Üniversitesi Bilgisayar Mühendisliği Bitirme Projesi** kapsamında hazırlanmıştır. Akademik kullanım için serbesttir.

---

<div align="center">

**Erciyes Üniversitesi — Bilgisayar Mühendisliği Bölümü**

*Berkay Aydemir — Prof. Dr. Serkan ÖZTÜRK — 2025*

</div>
