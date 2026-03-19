<div align="center">

# 🔐 Secure Email Authentication & Message Integrity

### Güvenli E-posta Kimlik Doğrulama ve Mesaj Bütünlüğü Sistemi

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Cryptography](https://img.shields.io/badge/cryptography-44.0%2B-red?style=for-the-badge&logo=letsencrypt&logoColor=white)](https://cryptography.io/)
[![License](https://img.shields.io/badge/License-Academic-yellow?style=for-the-badge)](LICENSE)

**Erciyes Üniversitesi — Bilgisayar Mühendisliği Bölümü**
**Bitirme Projesi • 2025**

*Berkay Aydemir — 1030521387*
*Danışman: Prof. Dr. Serkan ÖZTÜRK*

---

</div>

## 📌 Proje Hakkında

Bu proje, **güvenli e-posta iletişiminde** üç temel kriptografik güvenlik özelliğini birleştiren eğitici bir hibrit şifreleme sistemidir. **Alice → Bob** iletişim senaryosu üzerinden, gerçek dünya uygulamalarında kullanılan kriptografik iş akışlarını adım adım görselleştirir.

### Güvenlik Özellikleri

| Özellik | Mekanizma | Algoritma |
|---------|-----------|-----------|
| 🔒 **Gizlilik** (Confidentiality) | Mesaj şifreleme | AES-256-GCM |
| ✅ **Bütünlük** (Integrity) | Özet + kimlik doğrulama etiketi | SHA-256 + GCM Auth Tag |
| 🪪 **Kimlik Doğrulama** (Authentication) | Dijital imza | RSA-2048 PSS |
| 📝 **İnkar Edememe** (Non-repudiation) | Özel anahtar ile imzalama | RSA-2048 PSS |

---

## 🏗️ Sistem Mimarisi

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
    ▼ Adım 5 ─── RSA Doğrulama (K⁺_A) ──────────────► ✅ GEÇERLİ  / ❌ GEÇERSİZ
```

---

## 📁 Proje Yapısı

```
bitirme_odevi/
├── crypto_core.py          # Kriptografik iş mantığı (backend)
├── main_gui.py             # PyQt6 GUI görselleştirme
├── test_crypto_core.py     # Birim testleri (26 test senaryosu)
├── requirements.txt        # Python bağımlılıkları
├── Thesis.pdf              # Bitirme tezi belgesi
└── .gitignore
```

---

## 🔬 Uygulanan Algoritmalar ve Kullanım Yerleri

### 1. SHA-256 — Mesaj Özeti

**Kullanıldığı Yer:** `crypto_core.py` — `sha256_hash()`, `sha256_hex()` metotları (satır 114–120)

```python
# crypto_core.py:116
return hashlib.sha256(data).digest()
```

SHA-256 (Güvenli Özet Algoritması), FIPS 180-4 standardında tanımlanmıştır. Herhangi bir boyuttaki girdi için sabit 256-bit (32 byte) özet değeri üretir. Bu projede:
- Alice tarafında mesajın parmak izi alınarak dijital imzanın oluşturulmasında
- Bob tarafında alınan mesajın bütünlüğünü doğrulamak için yeniden hesaplamada

kullanılmaktadır.

**Kaynak:** [NIST FIPS 180-4 — Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
**API Referansı:** [Python `hashlib` — `hashlib.sha256()`](https://docs.python.org/3/library/hashlib.html)

---

### 2. RSA-2048 Dijital İmza — PSS Dolgusu

**Kullanıldığı Yer:** `crypto_core.py` — `rsa_sign()`, `rsa_verify()` metotları (satır 126–155), `generate_rsa_keypair()` (satır 95–103)

```python
# crypto_core.py:128-135
private_key.sign(
    message_hash,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH,
    ),
    hashes.SHA256(),
)
```

RSA-2048, 2048-bit modulus uzunluğu ile güvenlik gücü 112-bit'e karşılık gelir (NIST SP 800-131A). **PSS (Probabilistic Signature Scheme)**, PKCS#1 v1.5'e göre daha güçlü bir güvenlik kanıtına sahiptir:
- Rastgele tuz (salt) kullanımı ile aynı mesajın her imzasının farklı olmasını sağlar
- `MGF1(SHA-256)` maske üretim fonksiyonu kullanılır
- `salt_length=MAX_LENGTH` maksimum güvenlik için tuz uzunluğunu en büyük değere ayarlar

**Kullanım:** `public_exponent=65537` (Fermat 4. sayısı, standart seçim), `key_size=2048`

**Kaynak:** [RFC 8017 — PKCS #1 v2.2: RSA Cryptography Specifications](https://www.rfc-editor.org/rfc/rfc8017.html)
**API Referansı:** [cryptography.io — RSA Signing](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/)
**Anahtar Boyutu:** [NIST SP 800-131A Rev. 2 — Key Length Recommendations](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar2.pdf)

---

### 3. AES-256-GCM — Kimlik Doğrulamalı Simetrik Şifreleme

**Kullanıldığı Yer:** `crypto_core.py` — `aes_gcm_encrypt()`, `aes_gcm_decrypt()`, `generate_session_key()` metotları (satır 161–174)

```python
# crypto_core.py:165-169
def aes_gcm_encrypt(self, key: bytes, plaintext: bytes) -> Tuple[bytes, bytes]:
    nonce = os.urandom(self.AES_NONCE_SIZE)   # 12 byte rastgele nonce
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ciphertext
```

AES-256-GCM (Galois/Counter Mode), NIST SP 800-38D standardında tanımlanmış **kimlik doğrulamalı şifreleme (AEAD)** modudur:
- **256-bit anahtar** (`AES_KEY_SIZE = 32 byte`) — NIST tarafından önerilen en yüksek güvenlik seviyesi
- **96-bit nonce** (`AES_NONCE_SIZE = 12 byte`) — NIST SP 800-38D'nin Bölüm 8.2.2'de önerilen optimal IV uzunluğu
- **128-bit kimlik doğrulama etiketi** — GCM şifreleme çıktısına otomatik eklenir
- Her mesaj için `os.urandom()` ile benzersiz nonce üretimi, nonce yeniden kullanımı güvenlik açığını önler

**Kaynak:** [NIST SP 800-38D — GCM and GMAC Block Cipher Modes](https://csrc.nist.gov/pubs/sp/800/38/d/final)
**API Referansı:** [cryptography.io — AESGCM](https://cryptography.io/en/latest/hazmat/primitives/aead/)

---

### 4. RSA-2048 OAEP — Oturum Anahtarı Şifreleme

**Kullanıldığı Yer:** `crypto_core.py` — `rsa_encrypt_key()`, `rsa_decrypt_key()` metotları (satır 180–200)

```python
# crypto_core.py:184-188
padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)
```

**OAEP (Optimal Asymmetric Encryption Padding)**, RSA şifreleme için RFC 8017 tarafından önerilen güvenli dolgu şemasıdır:
- PKCS#1 v1.5 dolgusuyla kıyaslandığında seçili şifreli metin saldırılarına (CCA) karşı güvenli
- Rastgele dolgu sayesinde aynı düz metin her seferinde farklı şifreli metin üretir
- `MGF1(SHA-256)` maske üretim fonksiyonu
- Yalnızca 32 byte'lık oturum anahtarı şifrelenir (RSA'nın büyük veri şifreleme dezavantajı minimize edilir)

**Kaynak:** [RFC 8017 — PKCS #1 v2.2, Section 7 (OAEP)](https://www.rfc-editor.org/rfc/rfc8017.html)
**API Referansı:** [cryptography.io — RSA Encryption](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/)

---

### 5. os.urandom() — Kriptografik Güvenli Rastgele Sayı Üretimi

**Kullanıldığı Yer:** `crypto_core.py` — `generate_session_key()` (satır 162), `aes_gcm_encrypt()` (satır 166)

```python
# crypto_core.py:162
self._session_key = os.urandom(self.AES_KEY_SIZE)   # 256-bit kriptografik anahtar
# crypto_core.py:166
nonce = os.urandom(self.AES_NONCE_SIZE)              # 96-bit GCM nonce
```

`os.urandom()`, işletim sistemi düzeyinde kriptografik güvenli sözde rasgele sayı üreteci (CSPRNG) kullanır:
- Windows'ta `CryptGenRandom` (BCrypt API)
- Linux/macOS'ta `/dev/urandom`

Her oturum için benzersiz `K_S` ve `nonce` üretilerek tekrar oynatma saldırıları önlenir.

**API Referansı:** [Python `os.urandom()` — Platform-level CSPRNG](https://docs.python.org/3/library/os.html#os.urandom)

---

### 6. PyQt6 — Masaüstü GUI Çerçevesi

**Kullanıldığı Yer:** `main_gui.py` — Tüm GUI bileşenleri (936 satır)

```python
# main_gui.py
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, ...)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
```

PyQt6, Qt6 C++ kütüphanesinin Python bağlantılarıdır. Bu projede:
- `QMainWindow` — Ana pencere ve kontrol düğmeleri
- `QSplitter` — Alice/Bob panellerini yan yana gösterme
- `QScrollArea` + `QTextEdit` — Adım adım kriptografik süreç görselleştirme
- Koyu tema (Catppuccin renk paleti, `#1e1e2e` arkaplan)
- Her kriptografik adım için ayrı görsel kutu (`_make_step_box()`)

**Kaynak:** [PyQt6 — Riverbank Computing](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
**PyPI:** [PyQt6 · PyPI](https://pypi.org/project/PyQt6/)

---

## 🛡️ Güvenlik Analizi

### Sağlanan Güvenlik Özellikleri

| Güvenlik Özelliği | Mekanizma | Saldırı Koruması |
|---|---|---|
| **Gizlilik** | AES-256-GCM | Pasif dinleme (eavesdropping) |
| **Bütünlük** | GCM Auth Tag + SHA-256 | Mesaj manipülasyonu |
| **Kimlik Doğrulama** | RSA-2048 PSS | Kimlik sahteciliği (spoofing) |
| **İnkar Edememe** | RSA özel anahtar imzası | Gönderici inkarı |
| **Tekrar Saldırısı Koruması** | Rastgele nonce (96-bit) | Replay attack |
| **İletme Gizliliği** | Her mesajda yeni K_S | Anahtar ifşasında geçmiş mesaj güvenliği |

### Kriptografik Parametreler

```
RSA Anahtar Boyutu    : 2048-bit (112-bit güvenlik gücü, NIST SP 800-131A)
RSA Açık Üs (e)       : 65537 (F4 – Fermat 4. sayısı)
RSA İmza Dolgusu      : PSS (Probabilistic Signature Scheme, RFC 8017 §9.1)
RSA Şifreleme Dolgusu : OAEP (Optimal Asymmetric Encryption Padding, RFC 8017 §7.1)
Simetrik Anahtar      : AES-256 (256-bit, NIST FIPS 197)
Şifreleme Modu        : GCM (Galois/Counter Mode, NIST SP 800-38D)
Nonce Uzunluğu        : 96-bit / 12 byte (NIST önerisi)
Kimlik Doğrulama Etiketi : 128-bit (NIST SP 800-38D §5.2.1.2)
Özet Fonksiyonu       : SHA-256 (FIPS 180-4)
Maske Üretim Fonksiyonu : MGF1(SHA-256) (RFC 8017 §B.2.1)
```

---

## 🖥️ Ekran Görüntüleri

> GUI, **adım adım** kriptografik süreci iki panel halinde görselleştirir:
> - **Sol Panel (Alice):** Şifreleme adımları iç içe sarmallar şeklinde gösterilir
> - **Sağ Panel (Bob):** Şifre çözme adımları iç içe sarmallar şeklinde açılır
> - **Alt Panel:** Orijinal ve alınan mesaj karşılaştırması, SHA-256 özeti kontrolü

---

## ⚙️ Kurulum ve Çalıştırma

### Gereksinimler

- Python 3.9+
- pip

### Kurulum

```bash
# Repoyu klonlayın
git clone https://github.com/<KULLANICI_ADI>/secure-email-auth.git
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
python -m pytest test_crypto_core.py -v
```

---

## 🧪 Test Kapsamı

Proje **26 birim testi** içermekte olup tüm kritik kriptografik işlemleri kapsar:

| Test Sınıfı | Test Sayısı | Kapsam |
|---|---|---|
| `TestSHA256` | 5 | Deterministik hash, uzunluk, boş girdi |
| `TestRSAKeyGeneration` | 5 | Anahtar üretimi, boyut, PEM formatı, teklilik |
| `TestRSASignature` | 3 | İmza doğrulama, yanlış anahtar reddi |
| `TestAESGCM` | 5 | Şifreleme/çözme, yanlış anahtar, manipülasyon tespiti |
| `TestRSAKeyEncryption` | 2 | Oturum anahtarı şifreleme/çözme |
| `TestFullWorkflow` | 6 | Uçtan uca iş akışı, Türkçe karakter, uzun mesaj |

---

## 📦 Bağımlılıklar

| Paket | Versiyon | Kullanım Amacı |
|---|---|---|
| [PyQt6](https://pypi.org/project/PyQt6/) | ≥ 6.6.0 | Masaüstü GUI çerçevesi |
| [cryptography](https://pypi.org/project/cryptography/) | ≥ 44.0.0 | RSA, AES-GCM kriptografik primitifler |

---

## 📚 Kaynakça

Projede kullanılan standartlar, algoritmalar ve kütüphanelerin kaynakları; **hangi kod/bileşende kullanıldıkları** ile birlikte aşağıda listelenmiştir.

---

### Kriptografik Standartlar ve RFC'ler

#### [1] NIST FIPS 180-4 — Secure Hash Standard (SHS)
> *National Institute of Standards and Technology. (2015). FIPS PUB 180-4: Secure Hash Standard (SHS). U.S. Department of Commerce.*

**Kullanıldığı yer:** `crypto_core.py` — `sha256_hash()` (satır 115–116), `sha256_hex()` (satır 119–120), RSA PSS ve OAEP dolgu fonksiyonlarında `hashes.SHA256()` parametresi (satır 131, 134, 148, 151, 185–187)

SHA-256 algoritmasının matematiksel tanımını sağlayan standart. Proje boyunca özet hesaplama ve şifreleme dolgularında kullanılmıştır.

- 🔗 [NIST CSRC: FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
- 🔗 [PDF: nvlpubs.nist.gov](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.180-4.pdf)

---

#### [2] NIST SP 800-38D — Recommendation for Block Cipher Modes of Operation: GCM and GMAC
> *Dworkin, M. (2007). NIST Special Publication 800-38D: Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC. NIST.*

**Kullanıldığı yer:** `crypto_core.py` — `aes_gcm_encrypt()` (satır 165–169), `aes_gcm_decrypt()` (satır 172–174)

AES-GCM modunun tam teknik tanımını içerir. Projede kullanılan 12-byte nonce uzunluğu bu standardın Bölüm 8.2.2'sinden gelir.

- 🔗 [NIST CSRC: SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final)
- 🔗 [PDF: nvlpubs.nist.gov](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-38d.pdf)

---

#### [3] RFC 8017 — PKCS #1: RSA Cryptography Specifications Version 2.2
> *Moriarty, K., Kaliski, B., Jonsson, J., & Rusch, A. (2016). RFC 8017: PKCS #1: RSA Cryptography Specifications Version 2.2. IETF.*

**Kullanıldığı yer:** `crypto_core.py`
- PSS dolgusu: `rsa_sign()`, `rsa_verify()` (satır 126–155) — RFC 8017 §9.1
- OAEP dolgusu: `rsa_encrypt_key()`, `rsa_decrypt_key()` (satır 180–200) — RFC 8017 §7.1
- MGF1 maske üretim fonksiyonu: tüm dolgu fonksiyonlarında — RFC 8017 Ek B.2.1
- `public_exponent=65537` (F4) seçimi — RFC 8017 Ek C

RSA şifrelemenin, dijital imza ve dolgu şemalarının tam matematiksel tanımını sağlar.

- 🔗 [IETF RFC Editor: RFC 8017](https://www.rfc-editor.org/rfc/rfc8017.html)
- 🔗 [IETF Datatracker: RFC 8017](https://datatracker.ietf.org/doc/html/rfc8017)

---

#### [4] NIST SP 800-131A Rev. 2 — Transitioning the Use of Cryptographic Algorithms and Key Lengths
> *Barker, E., & Roginsky, A. (2019). NIST SP 800-131A Revision 2: Transitioning the Use of Cryptographic Algorithms and Key Lengths. NIST.*

**Kullanıldığı yer:** `crypto_core.py` — `CryptoCore.RSA_KEY_SIZE = 2048` (satır 83)

RSA-2048'in 2030 sonrası için onaylı minimum anahtar boyutu olduğunu, 112-bit güvenlik gücüne karşılık geldiğini belirtir.

- 🔗 [NIST CSRC: SP 800-131A](https://csrc.nist.gov/pubs/sp/800/131/a/r2/final)
- 🔗 [PDF: nvlpubs.nist.gov](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar2.pdf)

---

#### [5] NIST FIPS 197 — Advanced Encryption Standard (AES)
> *National Institute of Standards and Technology. (2001, revised 2023). FIPS PUB 197: Advanced Encryption Standard (AES). U.S. Department of Commerce.*

**Kullanıldığı yer:** `crypto_core.py` — `CryptoCore.AES_KEY_SIZE = 32` (satır 81), `AESGCM(key)` çağrısı (satır 167, 173)

AES blok şifresinin temel tanımını içerir. GCM modunun üzerine inşa edildiği temel algoritma.

- 🔗 [NIST CSRC: FIPS 197](https://csrc.nist.gov/pubs/fips/197/final)
- 🔗 [PDF: nvlpubs.nist.gov](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.197-upd1.pdf)

---

### Python Kütüphaneleri

#### [6] PyCA cryptography Kütüphanesi
> *Python Cryptographic Authority (PyCA). (2024). cryptography: Cryptographic primitives and recipes for Python. PyPI.*

**Kullanıldığı yer:** `crypto_core.py` — import ifadeleri (satır 20–26); `rsa.generate_private_key()` (satır 96), `AESGCM` (satır 167, 173), `padding.PSS` (satır 130, 147), `padding.OAEP` (satır 184, 195)

PyCA'nın `cryptography` paketi bu projenin tüm şifreleme işlemlerinin temelini oluşturur. OpenSSL üzerine kurulu endüstri standardı Python kütüphanesidir.

- 🔗 [Resmi Dokümantasyon: cryptography.io](https://cryptography.io/en/latest/)
- 🔗 [PyPI: cryptography](https://pypi.org/project/cryptography/)
- 🔗 [GitHub: pyca/cryptography](https://github.com/pyca/cryptography)
- 🔗 [RSA API: cryptography.io/rsa](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/)
- 🔗 [AESGCM API: cryptography.io/aead](https://cryptography.io/en/latest/hazmat/primitives/aead/)

---

#### [7] Python hashlib — Güvenli Hash ve Mesaj Özetleri
> *Python Software Foundation. (2024). hashlib — Secure hashes and message digests. Python Standard Library.*

**Kullanıldığı yer:** `crypto_core.py` — `import hashlib` (satır 14), `hashlib.sha256(data).digest()` (satır 116), `hashlib.sha256(data).hexdigest()` (satır 120)

FIPS 180-4 tanımlı SHA-256 algoritmasının Python standart kütüphanesi implementasyonu.

- 🔗 [Python Docs: hashlib](https://docs.python.org/3/library/hashlib.html)

---

#### [8] Python os.urandom() — Kriptografik Güvenli Rastgele Bayt
> *Python Software Foundation. (2024). os.urandom() — Miscellaneous operating system interfaces. Python Standard Library.*

**Kullanıldığı yer:** `crypto_core.py` — `generate_session_key()` (satır 162), `aes_gcm_encrypt()` (satır 166)

İşletim sistemi düzeyinde kriptografik güvenli rastgele sayı üreteci. Windows'ta `CryptGenRandom`, Linux/macOS'ta `/dev/urandom` kullanır.

- 🔗 [Python Docs: os.urandom](https://docs.python.org/3/library/os.html#os.urandom)

---

#### [9] PyQt6 — Python Qt6 Bağlantıları
> *Riverbank Computing Limited. (2024). PyQt6: Python bindings for Qt v6. Riverbank Computing.*

**Kullanıldığı yer:** `main_gui.py` — Tüm GUI sınıfları; `MainWindow`, `AlicePanel`, `BobPanel` (936 satır); `QApplication`, `QMainWindow`, `QSplitter`, `QScrollArea`, `QTextEdit`, `QFont`, `QColor`, vb.

Adım adım kriptografik görselleştirme için kullanılan masaüstü GUI çerçevesi.

- 🔗 [Resmi Dokümantasyon: riverbankcomputing.com/PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- 🔗 [PyPI: PyQt6](https://pypi.org/project/PyQt6/)
- 🔗 [Riverbank Computing: PyQt Giriş](https://riverbankcomputing.com/software/pyqt/intro)

---

### Kavramsal Kaynaklar

#### [10] Hibrit Şifreleme — RSA + AES Kombinasyonu
> *Demonstrates hybrid encryption using symmetric encryption and public key encryption (AES-GCM + RSA). GitHub Gist.*

**Kullanıldığı yer:** `crypto_core.py` — `alice_send()` ve `bob_receive()` metodlarındaki genel iş akışı tasarımı (satır 206–449)

RSA ile oturum anahtarı şifreleyip AES ile asıl veriyi şifreleme paradigması.

- 🔗 [GitHub Gist: AES-GCM + RSA Hybrid Encryption](https://gist.github.com/ace0/6cf36a6bc92a8d83ced843efb5461539)
- 🔗 [PyCryptodome — Hybrid Encryption Examples](https://pycryptodome.readthedocs.io/en/latest/src/examples.html)

---

#### [11] RSA Dijital İmza — SHA ile Hash
> *GeeksforGeeks. (2023). RSA Digital Signature Scheme using Python.*

**Kullanıldığı yer:** `crypto_core.py` — `rsa_sign()`, `rsa_verify()` metodlarının tasarım prensibi (satır 126–155)

RSA dijital imza şemasının Python ile implementasyonu için referans.

- 🔗 [GeeksforGeeks: RSA Digital Signature Scheme using Python](https://www.geeksforgeeks.org/rsa-digital-signature-scheme-using-python/)

---

#### [12] Galois/Counter Mode — Wikipedia
> *Wikipedia contributors. (2024). Galois/Counter Mode. Wikipedia, The Free Encyclopedia.*

**Kullanıldığı yer:** Projenin teorik altyapısında GCM'nin çalışma prensiplerini anlamak için.

- 🔗 [Wikipedia: Galois/Counter Mode](https://en.wikipedia.org/wiki/Galois/Counter_Mode)

---

#### [13] SHA-2 — Wikipedia
> *Wikipedia contributors. (2024). SHA-2. Wikipedia, The Free Encyclopedia.*

**Kullanıldığı yer:** SHA-256'nın algoritma yapısını anlamak için genel referans.

- 🔗 [Wikipedia: SHA-2](https://en.wikipedia.org/wiki/SHA-2)

---

## 📄 Lisans

Bu proje **Erciyes Üniversitesi Bilgisayar Mühendisliği Bitirme Projesi** kapsamında hazırlanmıştır. Akademik kullanım için serbesttir.

---

<div align="center">

**Erciyes Üniversitesi — Bilgisayar Mühendisliği Bölümü**
*Berkay Aydemir — Prof. Dr. Serkan ÖZTÜRK*
*2025*

</div>
