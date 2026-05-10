# Kripto Animasyonları — Tezle Hizalı Yeniden Tasarım

**Tarih:** 2026-05-10
**Hedef dosyalar:** `animation_modals/rsa_animation.py`, `animation_modals/sha256_animation.py`
**İlgili tez bölümleri:** `chapter1.tex` § Asimetrik Şifreleme ve RSA-2048 (Tablo `tab:RSAExample`, Eşitlik `Eq:RSAExample`, Algoritma `algo:EEA`); `chapter2.tex` § SHA-256.

## Motivasyon

Mevcut animasyonlarda dört nokta kullanıcı tarafından "anlaşılmıyor / fazla metin" olarak işaretlendi:

1. **EEA tablosu** (RSA Adım 5) satır satır beliriyor ama her satırın değerlerinin nereden geldiği görünmüyor.
2. **RSA demo değerleri** her açılışta rastgele küçük asal çiftiyle değişiyor; tezdeki Tablo `tab:RSAExample` (`p=61, q=53, n=3233, φ=3120, e=17, d=2753`) ile birebir uyuşmuyor. Tezde gösterilen `m=65 → c=2790 → m'=65` şifreleme/deşifreleme turu animasyonda yok.
3. **SHA-256 mesaj genişletmesi** (`W_i` sayfası) 16'dan fazla satırlık tek bloklu metin; σ0/σ1 fonksiyonlarının nasıl çalıştığı görselleşmemiş.
4. **SHA-256 final eşleşme** sayfası dev bir metin bloğu; "önceki H + çalışma değişkeni = yeni H" toplamı ile 8 yeni H'nin birleşip `crypto_core` çıktısıyla eşleşmesi animasyonsuz.

Bu spec, dört noktayı tezle birebir hizalı, animasyon ağırlıklı bir yeniden tasarıma çevirir.

## Kapsam

**İçerikte:**

- `_EEAWidget` yeniden yazımı (canlı hesaplama şeridi)
- `_reseed_demo()` kaldırımı, tez değerlerinin sabitlenmesi
- Yeni `_RSAEncryptDecryptWidget` (Adım 8 — şifreleme/deşifreleme turu)
- Yeni `_WExpansionWidget` (mesaj genişletme animasyonu)
- Yeni `_MatchAssemblyWidget` (final eşleşme animasyonu)

**Kapsam dışı:**

- AES animasyonu (değişmiyor)
- SHA-256 Padding sayfası (mevcut metin haliyle kalıyor)
- SHA-256 sıkıştırma fonksiyonu diyagramı (mevcut animasyon yeterli)
- RSA Adım 1–7'nin görsel düzeni (sadece sabit değerler değişiyor)
- RSA çift yön (imza yolu) animasyonu — gelecek bir spec'e bırakıldı
- SHA-256 saf Python referans uygulaması (`sha256_pure.py` değişmiyor; gerekli alanlar zaten dönüyor)

## Kısıtlar

- PyQt6, mevcut `CryptoAnimationWindow` ve `ANIM_COLORS` paleti kullanılır.
- Yeni dış bağımlılık eklenmez.
- Mevcut `manual_mode=True` davranışı (◀ / ▶ ile gezme) korunur.
- `sha256_pure.py` ve `_eea_steps()` çıktıları olduğu gibi tüketilir.
- Türkçe arayüz dili korunur.
- Toplam adım sayıları:
  - RSA: 7 → 8 (yeni Adım 8: şifreleme/deşifreleme turu)
  - SHA-256: değişmez

## Mimari Genel Bakış

İki dosya değişiyor; iki dosya da aynı kalıbı izliyor: yeni `QPainter`-tabanlı widget sınıfları, `QTimer`-tahrikli faz makineleri, `ANIM_COLORS` paleti.

```
animation_modals/
├── rsa_animation.py
│   ├── _EEAWidget                  ← REWRITE (canlı hesaplama şeridi)
│   ├── _reseed_demo / _PRIME_POOL  ← KALDIR
│   ├── _P, _Q, _N, _PHI, _E, _D    ← Sabit (61, 53, 3233, 3120, 17, 2753)
│   ├── _RSAEncryptDecryptWidget    ← YENİ (Adım 8)
│   └── RSAAnimationWindow          ← total_steps 7 → 8, _render_step yeni dal
└── sha256_animation.py
    ├── _WExpansionWidget           ← YENİ (mesaj genişletme animasyonu)
    ├── _MatchAssemblyWidget        ← YENİ (final eşleşme animasyonu)
    ├── _make_wexpand_page          ← _WExpansionWidget'a delege eder
    ├── _make_match_page            ← _MatchAssemblyWidget'a delege eder
    └── _show_match_result          ← _MatchAssemblyWidget.start_animation çağrısına indirgenir
```

## Bileşen 1 — EEA Canlı Hesaplama Şeridi

### Mevcut davranış
`_EEAWidget` (`rsa_animation.py:838–1010`): `_eea_steps(_PHI, _E)` ile satırları oluşturur, 420 ms aralıkla `_reveal` sayacını artırarak satırları açar. Kullanıcı bir satırın `r, s, t` değerlerinin nereden geldiğini göremez.

### Yeni davranış

Faz makinesi her satır için iki aşamalıdır:

| Faz | Süre | Davranış |
| --- | --- | --- |
| `STRIP_SHOW` | 1100 ms | Yeni satırın tablo konumu boş bırakılır. Hemen altında bir hesaplama şeridi belirir. Şeritte 4 satırlık formül var (`q`, `r`, `s`, `t` formülleri sayısal değerleriyle). Önceki satırdaki `r₀, r₁, s₀, s₁, t₀, t₁` hücreleri kalın çerçeve + parlak renk vurgu alır. |
| `STRIP_FADE` | 400 ms | Şerit fade-out, hesaplanan değerler tabloya satır olarak yerleşir, vurgular sönmeye başlar. |
| `IDLE` | (sonraki satıra geçiş) | Tabloya yerleşmiş satır, normal renkleriyle kalır. Bir sonraki satıra geçilir. |

Şerit içeriği örneği (i=2 için, `_PHI=3120, _E=17`):

```
q = ⌊3120 / 17⌋ = 183
r = 3120 − 183·17 = 9
s = 1 − 183·0    = 1
t = 0 − 183·1    = −183
```

Tüm satırlar yerleştikten sonraki davranış (GCD=1 satırı vurgusu, "(durma satırı)" etiketi, `d = t mod φ` hesabı, `e × d mod φ = 1 ✓` doğrulaması) **mevcut hâliyle korunur**.

### Düzen değişikliği

- `setMinimumHeight(260) → 360` (şerit alanı için).
- Mevcut `_COL_WIDTHS` ve `annot_w` değişmiyor.
- Şerit, en son yerleştirilen satırın **altında**, tablo alanının solundan başlayarak `total_col_w + annot_w` genişliğinde çizilir.

### Etkilenen kod

- `_EEAWidget._reveal` tek sayaçtan `(_row_idx, _phase, _phase_tick)` üçlüsüne çıkar.
- `_EEAWidget._tick` faz makinesi olur.
- `paintEvent` üç bölüme ayrılır: tablo başlığı + yerleşmiş satırlar + (varsa) aktif şerit.

## Bileşen 2 — RSA Tez Değerleri Sabitlenmesi

### Kaldırılacaklar

`rsa_animation.py:87–139`:

- `_PRIME_POOL` listesi
- `_reseed_demo()` fonksiyonu
- `RSAAnimationWindow.__init__` içindeki `_reseed_demo()` çağrısı (`rsa_animation.py:1406`)

### Sabitlenecekler

```python
_P:   int   = 61
_Q:   int   = 53
_N:   int   = 3233
_PHI: int   = 3120
_E:   int   = 17
_D:   int   = 2753
```

`_DER_N`, `_DER_E`, `_DER_SEQ`, `_B64_DEMO` aynı şekilde modül seviyesinde, sabit `_N`, `_E`'den hesaplanır (mevcut formül).

### Asal eleği animasyonu

Adım 1 (asal eleği) sabit `(61, 53)` ile çalışır. Eleğin son aşamasında bu iki değer parlar.

### Değer doğrulama

Tezdeki Tablo `tab:RSAExample` ile spec'teki sabitlerin tam eşleştiği:

| Tez (`tab:RSAExample`) | Spec sabitleri |
| --- | --- |
| `p = 61, q = 53` | `_P=61, _Q=53` |
| `n = 3233` | `_N=3233` |
| `φ(n) = 3120` | `_PHI=3120` |
| `e = 17` | `_E=17` |
| `d = 2753` | `_D=2753` |

`(_E * _D) % _PHI == 1` runtime invariant olarak korunmalıdır (testle ya da `assert` ile).

## Bileşen 3 — RSA Adım 8: Şifreleme/Deşifreleme Turu

### Yeni widget: `_RSAEncryptDecryptWidget`

Tezdeki `Eq:RSAExample`'ın görsel karşılığı: `m = 65 → c = 65¹⁷ mod 3233 = 2790 → m' = 2790²⁷⁵³ mod 3233 = 65`.

### Düzen

```
┌──────────────────────────────────────────────────────────────────┐
│           Adım 8 / 8 — Şifreleme / Deşifreleme Turu              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌────────┐         ┌──────────────────┐         ┌────────┐     │
│   │ m = 65 │  ─────▶ │  c = m^e mod n   │ ─────▶  │ c=2790 │     │
│   └────────┘         │  = 65^17 mod 3233│         └────────┘     │
│                      │  = 2790          │                        │
│                      └──────────────────┘                        │
│                          ▲                                       │
│                          │ Açık anahtar (n=3233, e=17)           │
│                                                                  │
│   ┌────────┐         ┌──────────────────┐         ┌────────┐     │
│   │ c=2790 │  ─────▶ │  m' = c^d mod n  │ ─────▶  │m' = 65 │     │
│   └────────┘         │  = 2790^2753     │         │  = m ✓ │     │
│                      │  mod 3233 = 65   │         └────────┘     │
│                      └──────────────────┘                        │
│                          ▲                                       │
│                          │ Gizli anahtar (n=3233, d=2753)        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Faz makinesi

| Faz | Süre | Davranış |
| --- | --- | --- |
| `PLAINTEXT_IN` | 400 ms | `m = 65` kutusu sol üstte belirir. |
| `ENC_FORMULA` | 800 ms | Şifreleme kutusu satır satır yazılır. Açık anahtar `(n, e)` kartı sağda parlar. |
| `CIPHER_OUT` | 400 ms | `c = 2790` kutusu sağda belirir, ok dolar. |
| `CIPHER_IN` | 200 ms | Aynı `c` değeri alt yola düşer (alt sıradaki sol kutu). |
| `DEC_FORMULA` | 800 ms | Deşifreleme kutusu satır satır yazılır. Gizli anahtar `(n, d)` kartı sağda parlar. |
| `PLAINTEXT_OUT` | 400 ms | `m' = 65` kutusu belirir. |
| `MATCH` | 600 ms | `m' = m ✓` etiketi yeşil pulse, kutu yeşil çerçeve. |

Toplam: ~3.6 sn.

### `RSAAnimationWindow` entegrasyonu

- `total_steps`: 7 → 8.
- Adım başlık listesinde 8. sıraya: `"Adım 8 / 8 — Şifreleme / Deşifreleme Turu"`.
- `_render_step` yeni dal: step 8 → `_RSAEncryptDecryptWidget` sayfasını göster, `start_animation()` çağır.
- Anahtar İnşa Paneli adım 8'de değişmez (zaten `d` doldurulmuş durumda).

## Bileşen 4 — SHA-256 Mesaj Genişletme Animasyonu

### Mevcut davranış

`_make_wexpand_page` (`sha256_animation.py:807–870`): `QLabel` içinde 16+ satırlık tek bloklu metin. Tüm `W[16..31]` listesi statik olarak yazılıyor.

### Yeni widget: `_WExpansionWidget`

`sha256_pure.py`'nin döndürdüğü `w_expansion` listesini (16 entry, `i`, `w_i16`, `w_i15`, `w_i7`, `w_i2`, `s0`, `s1`, `result`) tüketir.

### Düzen

```
┌──────────────────────────────────────────────────────────────────┐
│   Adım 2 — Mesaj Genişletme (Message Schedule)                   │
├──────────────────────────────────────────────────────────────────┤
│   σ0(x) = ROTR(x,7)  ⊕ ROTR(x,18) ⊕ SHR(x,3)                     │
│   σ1(x) = ROTR(x,17) ⊕ ROTR(x,19) ⊕ SHR(x,10)                    │
├──────────────────────────────────────────────────────────────────┤
│                          i = 17 / 63                              │
│   W[i] = σ1(W[i−2]) + W[i−7] + σ0(W[i−15]) + W[i−16]  (mod 2³²)  │
│                                                                  │
│  ┌─────────────┐  ┌──────────────────┐                           │
│  │ W[i−16]     │  │ σ0(W[i−15])      │                           │
│  │  61800000   │  │  σ0(00000000)    │                           │
│  └──────┬──────┘  │  → 00000000      │                           │
│         │         └────────┬─────────┘                           │
│         │                  │                                     │
│         │        ┌─────────▼──────────┐                          │
│         └───────▶│        ⊕ +         │◀──────┐                  │
│                  └─────────┬──────────┘       │                  │
│                            │                  │                  │
│  ┌─────────────┐           │     ┌───────────────────┐           │
│  │ W[i−7]      │───────────┘     │ σ1(W[i−2])        │           │
│  │  00000000   │                 │  σ1(00000000)     │           │
│  └─────────────┘                 │  → 00000000       │           │
│                                  └───────────────────┘           │
│                            │                                     │
│                            ▼                                     │
│                  ┌──────────────────┐                            │
│                  │  W[17] = 00050000│                            │
│                  └──────────────────┘                            │
│                                                                  │
│              [◀ Önceki i]    [Sonraki i ▶]                       │
└──────────────────────────────────────────────────────────────────┘
```

### Faz makinesi (her i değiştiğinde baştan oynar)

| Faz | Süre | Davranış |
| --- | --- | --- |
| `INPUTS_REVEAL` | 1200 ms | 4 girdi kutusu 300 ms aralıkla sırayla doğar. |
| `ARROWS_FLOW` | 600 ms | 4 girdi kutusundan `+` düğümüne ok animasyonu. |
| `RESULT_OUT` | 400 ms | `W[i]` sonuç kutusu yeşil pulse. |
| `IDLE` | — | ◀ / ▶ tıklamasını bekler. |

Toplam: ~2.2 sn.

### Etkileşim

- Sayfanın **kendi** ◀ / ▶ butonları. Sadece o sayfanın `i` değerini 16…31 arasında değiştirir (mevcut `w_expansion` listesi 16 entry içeriyor).
- Pencerenin alt navigasyon ◀ / ▶ butonları **etkilenmez**; mevcut adım geçişine devam eder.
- Üstte küçük gösterge: `i = 17 / 31`.

### Etkilenen kod

- `_make_wexpand_page` → tek satırlık fonksiyon: `_WExpansionWidget(self._data["w_expansion"])` döndürür.
- Yeni sınıf: `_WExpansionWidget(QWidget)` — `QPainter`-tabanlı çizim + iki `QPushButton`.

## Bileşen 5 — SHA-256 Final Eşleşme Animasyonu

### Mevcut davranış

`_show_match_result` (`sha256_animation.py:981–1048`): bir `QLabel`'in metnini `assembly_lines` listesinden oluşturulan dev bir bloka set eder. Hiç animasyon yok.

### Yeni widget: `_MatchAssemblyWidget`

Dört faz, hepsi `QPainter`-tabanlı:

#### Faz 1 — Round özeti (~1500 ms)

Üst bantta:
- Sol: 8 H başlangıç kutusu (`H0..H7`), her biri 100 ms aralıkla parlar.
- Orta: `→ 64 round →` kayan etiket.
- Sağ: 8 çalışma değişkeni kutusu (`A..H`), 100 ms aralıkla parlar.

#### Faz 2 — Toplama (~1600 ms, 8 satır × 200 ms)

Üç sütunlu hizalı toplama tablosu:

```
   Önceki H        + Çalışma     = Yeni H
   H0=6a09e667     + A=608d9aab  = ca978112    ← parlar
   H1=bb67ae85     + B=0eb40f45  = ca1bbdca    ← parlar
   H2=3c6ef372     + C=be533e41  = fac231b3    ← parlar
   ...
```

Her satırda:
- 0 ms: `Önceki H` hücresi belirir.
- 60 ms: `+ Çalışma` hücresi belirir.
- 120 ms: `=` ve sonuç hücresi yeşil pulse.

200 ms sonra sonraki satıra geçilir.

#### Faz 3 — Birleşim (~800 ms)

8 yeni H kutusu yatayda kayar (`QPropertyAnimation` ya da paint-time interpolation), tek bir 256-bit hash şeridine dönüşür: `ca978112ca1bbdca…afee48bb` (64 hex karakter).

#### Faz 4 — Eşleşme doğrulaması (~800 ms)

Şerit altında `crypto_core çıktısı:` etiketi belirir. 64 hex karakter sol→sağ taranır (12.5 ms/karakter); eşleşen karakterler yeşile döner. Tarama bitince:

- Tüm karakterler eşleşti → büyük yeşil `✅ Eşleşme: Başarılı` kartı.
- Eşleşmeyen karakter var → ilk eşleşmeyen karakter kırmızı kalır + `❌ HATA` kartı.

Toplam: ~4.7 sn.

### `_show_match_result` indirgemesi

```python
def _show_match_result(self) -> None:
    self._stack.setCurrentWidget(self._page_match)
    self._match_widget.start_animation(
        pre_h=self._data["pre_final_h"],
        working=self._data["final_working"],
        parts=self._data["final_h_parts"],
        computed=self._data["final_hash"],
        expected=self._expected_hash,
    )
```

Bütün metin oluşturma kodu `_MatchAssemblyWidget`'a taşınır.

### Etkilenen kod

- `_make_match_page` → `_MatchAssemblyWidget` örneği döndürür.
- `_show_match_result` küçülür (yukarıdaki blok kadar).
- Eski `_match_lbl` ve `assembly_lines` mantığı kaldırılır.

## Veri Akışı

`sha256_pure.py`'nin döndürdüğü `dict` yeni widget'lar tarafından şu şekilde tüketilir:

| Widget | Tükettiği alanlar |
| --- | --- |
| `_WExpansionWidget` | `w_expansion` (16 entry) |
| `_MatchAssemblyWidget` | `pre_final_h`, `final_working`, `final_h_parts`, `final_hash` |

Hiçbir yeni alan eklenmesi gerekmiyor.

## Hata Durumları

- **`w_expansion` 16 entry'den az dönerse:** `_WExpansionWidget` mevcut entry sayısına göre çalışır; ◀ / ▶ butonları sınır kontrolü yapar.
- **`final_h_parts != final_hash`'in karakter karakter eşleşmesi başarısız olursa:** Faz 4 kırmızı kart ile bitirir. Bu zaten mevcut davranış (`icon = "❌"`).
- **`_E * _D % _PHI != 1`:** Modül yüklenirken `assert` patlatır. Bu sabit değerlerle çalışma zamanı hatası imkânsız ama defansif olarak konur.

## Test ve Doğrulama Planı

### Otomatize edilebilir

- `_eea_steps(3120, 17)` çıktısının ilk satırlarının `(0, 0, 3120, 1, 0)` ve `(1, 0, 17, 0, 1)` olduğu — mevcut davranış, regresyon testi yazılabilir.
- `(_E * _D) % _PHI == 1` invariant'ı.
- `sha256_pure.sha256_steps(b"abc")["final_hash"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"` (NIST FIPS 180-4 referans değeri).

### Manuel (görsel)

Python 3.11 ortamında uygulamayı açıp:

1. **EEA:** RSA Adım 5'e gel; satırların altında hesaplama şeridinin belirip kaybolduğunu, önceki satır vurgularının çalıştığını doğrula. Son satırın altında `d = 2753` ve doğrulama satırının çıktığını gör.
2. **RSA değerleri:** Anahtar İnşa Paneli'nde `p=61, q=53, n=3233, φ=3120, e=17, d=2753` görünmesi. Birden çok kez animasyonu açıp kapat — değerler sabit kalmalı.
3. **RSA Adım 8:** İleri ▶ ile gel; `m=65 → c=2790 → m'=65` turunun her fazını gör; yeşil ✓ ile bittiğini doğrula.
4. **SHA-256 mesaj genişletme:** SHA Adım 2'ye gel; ◀ / ▶ ile `i = 16 → 17 → … → 31` arasında gez; her tıklamada animasyonun baştan oynadığını gör.
5. **SHA-256 final eşleşme:** SHA son adımına gel; faz 1–4'ün sırayla oynadığını gör; `crypto_core` ile karakter-karakter eşleşmenin tamamen yeşil olduğunu doğrula.

### Regresyon kontrolü

- AES animasyonu açılıyor, herhangi bir bozulma yok.
- SHA-256 Padding sayfası (Adım 1) açılıyor, mevcut metin görüntüsü değişmemiş.
- SHA-256 sıkıştırma diyagramı sayfaları (Adım 3..) açılıyor, mevcut animasyon çalışıyor.
- RSA Adım 1–7 (asal eleği, n, φ, e seçimi, EEA dışındaki kısımlar, DER kodlaması, eşleşme) açılıyor, sadece sabit değerler değişmiş.

## Açık Sorular

Yok — tüm kararlar brainstorming aşamasında alındı.

## Sonraki Adım

Bu spec onaylandıktan sonra `superpowers:writing-plans` skill'i ile uygulama planı yazılacak. Plan, beş bileşeni bağımsız olarak ele alacak (her biri kendi commit'i ile uygulanabilir).
