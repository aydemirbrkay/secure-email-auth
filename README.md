<div align="center">

# Güvenli E-posta Kimlik Doğrulama ve Mesaj Bütünlüğü Sistemi

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Cryptography](https://img.shields.io/badge/cryptography-44.0%2B-red?style=for-the-badge&logo=letsencrypt&logoColor=white)](https://cryptography.io/)

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

Proje **paket bazlı klasör düzeniyle** organize edilmiştir — arayüz, kriptografik çekirdek, animasyon modülleri ve testler ayrı paketlere bölünmüştür:

```
secure-email-auth/
├── main_gui.py                     # Ana uygulama penceresi ve iş akışı yöneticisi
├── arayuz/                         # Kullanıcı arayüzü paneller ve görsel bileşenler
│   ├── alice_panel.py              # Alice (gönderici) paneli ve animasyon konteyneri
│   ├── bob_panel.py                # Bob (alıcı) paneli ve deşifre diyagram bileşeni
│   ├── theme.py                    # Renk paleti ve tema sabitleri
│   └── toast.py                    # Doğrulama bildirimi bileşeni (VerificationToast)
├── kriptografi/                    # Kriptografik iş mantığı (backend)
│   ├── crypto_core.py              # Hibrit şifreleme/imzalama API'ı (cryptography lib)
│   ├── crypto_workers.py           # QThread tabanlı asenkron worker'lar (UI donmasın)
│   └── utils.py                    # Yardımcı fonksiyonlar (adım kutusu, renk hesaplama)
├── animation_modals/               # Pedagojik animasyon pencereleri
│   ├── base.py                     # CryptoAnimationWindow temel sınıfı
│   ├── matrix_widget.py            # AES durum matrisi görselleştirme bileşeni
│   ├── byte_widgets.py             # Paylaşılan byte ızgara/strip widget'ları (UTF-8 aware)
│   ├── aes_animation.py            # AES-256 animasyon penceresi (tıklanabilir round bar)
│   ├── aes_pure.py                 # Saf Python AES-256 (14 turlu durum verisi)
│   ├── rsa_animation.py            # RSA-2048 animasyon penceresi (8 eğitim adımı)
│   ├── sha256_animation.py         # SHA-256 animasyon penceresi (padding, W_i, sıkıştırma)
│   └── sha256_pure.py              # Saf Python SHA-256 (adım ve W_i verisi)
├── testler/                        # Birim ve smoke testleri (200+ test senaryosu)
│   ├── test_crypto_core.py         # Kriptografik API testleri
│   ├── test_crypto_workers.py      # Worker thread testleri
│   ├── test_aes_pure.py            # Saf AES implementasyonu testleri
│   ├── test_sha256_pure.py         # Saf SHA-256 implementasyonu testleri
│   ├── test_diagram_rects.py       # Diyagram dikdörtgen sınır testleri
│   ├── test_aes_matrix_view.py     # AES matris görünüm testleri
│   ├── test_animation_smoke.py     # Animasyon penceresi smoke testleri
│   ├── test_animation_widgets_smoke.py  # Widget instantiation testleri
│   ├── test_message_prep_animation.py   # Mesaj hazırlığı animasyon testleri
│   ├── test_rsa_animation.py       # RSA animasyon adım testleri
│   └── test_utils.py               # Yardımcı fonksiyon testleri
├── görseller/                      # Tüm görsel kaynaklar (SVG ikonlar + PNG akış diyagramları)
│   ├── alice and bob.png           # Alice tarafı şifreleme akış diyagramı
│   ├── bob-tarafi-sifre-cozme.png  # Bob tarafı deşifre akış diyagramı
│   ├── secure-email-simge.png      # Uygulama ana ikonu
│   └── *.svg                       # Tema simgeleri (gear, network, shield, vb.)
├── requirements.txt                # Python bağımlılıkları (çalışma zamanı)
├── requirements-dev.txt            # Test ve geliştirme bağımlılıkları
└── Thesis.pdf                      # Bitirme tezi belgesi
```

---

## Animasyon Modülleri

Proje, her kriptografik algoritmanın iç işleyişini adım adım görselleştiren bağımsız animasyon pencereleri içerir. Bu pencereler Alice panelinin içine gömülü olarak çalışır ve her pencere **kriptografik standartlara uygun, pedagojik olarak doğru** gösterimler sunar.

### AES-256-GCM Animasyonu (`animation_modals/aes_animation.py`)
- Giriş animasyonu ve **tıklanabilir tur çubuğu** (Round 0 – Round 14, R0–R14 butonları)
- Sayfa düzeni viewport'a oranlı genişler (matris ~%40 / akış şeması ~%60), yatay scroll çıkmaz
- 14 tura ait durum matrisi görselleştirmesi (`MatrixWidget`)
- **SubBytes**: S-Box ile byte değiştirme, hücre hücre animasyon
- **ShiftRows**: Satır kaydırma (0, 1, 2, 3 bayt sola) için renkli ok gösterimi
- **MixColumns**: GF(2⁸) sabit matris çarpımı `[[02,03,01,01],[01,02,03,01],[01,01,02,03],[03,01,01,02]]` ve her sütun için formül gösterimi (`02·s₀ ⊕ 03·s₁ ⊕ s₂ ⊕ s₃` …)
- **AddRoundKey**: XOR ile tur anahtarı karıştırma
- Eşleşme ekranı: ECB blok çıktısı ile GCM şifreli metninin neden farklı olduğunu açıklar (CTR sayacı + keystream ⊕ plaintext)

### RSA-2048 Animasyonu (`animation_modals/rsa_animation.py`)
- **8 adımlı** manuel eğitim akışı: asal sayılar → n → φ(n) → e → d (EEA) → DER/Base64 → gerçek anahtar eşleşmesi → şifreleme/deşifreleme turu
- Her adımda matematiksel formül gösterimi
- **Adım 5 — Genişletilmiş Öklid Algoritması**: İleri Öklid ve geri iz adımları kaynak satır referansları ile açıklanır
  (ör. `← satır 3'ten: 9 = 1×8 + 1 → 1 = 9 − 8`)
- **Adım 6 — DER / Base64**: Bölüm 2'de sayı → bayt dönüşümü narratif (örn. `n = 2291: 2291 ÷ 256 = 8 kalan 243 → 08 F3`); Bölüm 3'te ASN.1 / DER yapısı 3 mantıksal blokta — SEQUENCE başlığı, n için INTEGER kaydı, e için INTEGER kaydı; `0x02 = INTEGER etiketi` kavramı net biçimde açıklanır
- **Adım 8 — Şifreleme / Deşifreleme**: Demo değerler üzerinde `m=65 → c = 65¹⁷ mod 3233 = 2790 → m = 2790²⁷⁵³ mod 3233 = 65`; `m'` kutusu efektsiz açılır (pulse/renk geçişi yok), diğer kutularla tutarlı
- Gerçek DER→Base64 dönüşümü demo değerleriyle, demo ve gerçek 2048-bit anahtar farkı vurgulanır

### SHA-256 Animasyonu (`animation_modals/sha256_animation.py`)
- **Adım 1 — Mesaj Hazırlığı**: Kullanıcının tam metni (uzun mesajlarda word-wrap ile alt satıra inerek) gösterilir; byte detay tablosu **tüm baytları** içerir (16-byte kapasitesi kaldırıldı), uzun mesajda yatay scroll ile gezilir
- **UTF-8 / Türkçe karakter desteği**: Karakter satırı `ş, ğ, ü, ö, ç, ı` gibi çok-baytlı UTF-8 karakterleri her iki bayt hücresinde de doğru gösterir; padding-aware decoding ile padding baytları (0x80, 0x00, length) decode'u kırmaz
- **Adım 2 — Padding Görselleştirmesi**: Aynı mesaj etiketi simetrik olarak gösterilir; 0x80 biti + 0 bitleri + 64-bit uzunluk; çok-bloklu mesajlarda kompakt blok navigasyonu (◀ Önceki / Sonraki ▶) yatay scrollbar'ın hemen altında
- **Adım 3 — Mesaj Genişletme (Message Schedule)**: W[0..15] bloktan, W[16..63] için `σ0(x) = ROTR(x,7) ⊕ ROTR(x,18) ⊕ SHR(x,3)` ve `σ1(x) = ROTR(x,17) ⊕ ROTR(x,19) ⊕ SHR(x,10)` formülleri ile ilk bloğun W[16..31] tablosu
- **Adım 4 — Sıkıştırma Diyagramı**: AES tarzı **tıklanabilir round bar** (R1, R9, R17, R25, R33, R41, R49, R57, R64) ile snapshot'lar arası serbest navigasyon; çok bloklu mesajlarda ◀ Blok / Blok ▶ butonları
  - 8 register (A–H) giriş ve çıkış kutuları
  - T1 = Σ1(E) + Ch(E,F,G) + H + K + W ve T2 = Σ0(A) + Maj(A,B,C) kutuları
  - D → E' bağlantısı ve kaydırma legend'i (`B'=A  C'=B  D'=C  F'=E  G'=F  H'=G`)
- **Adım 5 — Final Hash Eşleşmesi**: Önceki H + Çalışma → Yeni H; 256-bit hash şeridi; crypto_core çıktısıyla karakter karakter eşleme + sonuç kartı
- Manuel ◀ Geri / İleri ▶ butonları her sayfada görünür kalır (uzun sayfa içerikleri kendi dikey scroll'larına alındı)

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
# rsa_sign: zaten hesaplanmış H(m) (32 byte) imzalanır
private_key.sign(
    message_hash,                       # önceden hesaplanmış SHA-256 özeti
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH,
    ),
    Prehashed(hashes.SHA256()),         # "H(m) ver, tekrar hashleme"
)
```

PSS (Probabilistic Signature Scheme) dolgusu, rastgele tuz kullanarak aynı mesajın her imzasını farklı kılar. 2048-bit modulus 112-bit güvenlik gücüne karşılık gelir (NIST SP 800-131A).

> **İmza girdisi hakkında not:** `rsa_sign(...)` fonksiyonuna mesaj değil, *önceden hesaplanmış* `H(m)` (32 byte) geçilir. Bu yüzden PyCA `cryptography` kütüphanesinde `Prehashed(SHA256())` ile imzalama yapılır; aksi hâlde kütüphane verilen 32 byte'lık özeti tekrar hashleyip **H(H(m))** imzalardı. Projedeki akış ve animasyon metinleri "H(m) imzalanır" şeklindedir; `rsa_sign` girdisinin uzunluğu 32 byte olarak doğrulanır (aksi hâlde `ValueError`). Sign ve verify birebir aynı `Prehashed(SHA256())` semantiğini kullanır; testler (`test_signature_is_over_hash_not_double_hash`) imzanın `H(m)` üzerinde olduğunu ve `H(H(m))` ile doğrulanmadığını garanti eder.

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
| **Nonce Benzersizliği** | 96-bit rastgele nonce (AES-GCM) | Aynı anahtar altında nonce çakışması |

> **Tekrar Saldırısı (Replay) Hakkında Not:** Projede taşınan paket
> yalnızca rastgele bir nonce içerir; paketin zaten görülmüş olup
> olmadığını belirlemek için **timestamp / sıra numarası / tek kullanımlık
> nonce kayıt defteri** gibi durum (state) tutan bir mekanizma yoktur.
> Bu nedenle sistem, pasif dinleyicinin daha önce yakaladığı geçerli
> bir paketi yeniden göndermesini (*replay*) **tek başına engelleyemez**.
> Rastgele nonce yalnızca AES-GCM'in aynı anahtarla aynı nonce'ı bir
> daha üretmemesini sağlar; bu **semantik güvenlik** için gerekli ama
> replay saldırılarına karşı yeterli değildir.
>
> **İletme Gizliliği (Forward Secrecy) Hakkında Not:** Bu hibrit şemada
> oturum anahtarı `K_S`, Bob'un uzun ömürlü RSA **açık anahtarı** ile
> sarmalanır (`K⁺_B(K_S)`). Bob'un RSA **gizli anahtarı** ileride ifşa
> olursa, saldırgan geçmişte kaydedilmiş tüm paketlerdeki `K⁺_B(K_S)`
> değerini çözüp oturum anahtarını ve dolayısıyla mesajı elde
> edebilir. Yani bu mimari **forward secrecy sağlamaz**. Gerçek
> anlamda forward secrecy için RSA-KEM yerine (geçici) Diffie-Hellman
> tabanlı bir anahtar değişimi (ör. ECDHE) kullanılmalıdır.

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

- Python 3.9 – 3.12 (PyQt6 6.6+ ile uyumlu)
- pip
- Masaüstü ortamı (GUI için)

> **Not:** Proje yerel olarak Python 3.11 üzerinde geliştirilmiş ve doğrulanmıştır.

### Kurulum

**1. Repoyu klonlayın**

```bash
git clone https://github.com/aydemirbrkay/secure-email-auth.git
cd secure-email-auth
```

**2. Sanal ortam oluşturun (önerilir)**

Windows (PowerShell / CMD):

```bat
python -m venv .venv
.venv\Scripts\activate
```

Linux / macOS (bash / zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Bağımlılıkları yükleyin**

```bash
# Sadece uygulamayı çalıştırmak için:
pip install -r requirements.txt

# Testleri de çalıştırmak istiyorsanız:
pip install -r requirements-dev.txt
```

### Çalıştırma

```bash
python main_gui.py
```

### Testleri Çalıştırma

Tüm test dosyalarını tek seferde çalıştırmak için:

```bash
python -m pytest -v
```

Yalnızca belirli test dosyalarını çalıştırmak için:

```bash
python -m pytest test_crypto_core.py test_aes_pure.py test_sha256_pure.py test_diagram_rects.py -v
```

### Olası Sorunlar

- **PyQt6 DLL / kütüphane hatası:** Anaconda / Miniconda ortamlarında PyQt6 binaries çakışması yaşanabilir. Bu durumda resmi **python.org** dağıtımı ile oluşturulmuş bir `venv` kullanmak sorunu çözer.
- **Linux'ta eksik Qt bağımlılıkları:** Bazı dağıtımlarda `libxcb-xinerama0`, `libxkbcommon-x11-0` gibi sistem paketlerinin kurulması gerekebilir.

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

<div align="center">

**Erciyes Üniversitesi — Bilgisayar Mühendisliği Bölümü**

*Berkay Aydemir — Prof. Dr. Serkan ÖZTÜRK — 2025*

</div>
