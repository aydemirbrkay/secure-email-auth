---
title: Kriptografi Animasyon Pencereleri
date: 2026-04-01
project: Secure Email Authentication and Message Integrity
author: Berkay Aydemir
---

# Kriptografi Animasyon Pencereleri — Tasarım Dokümanı

## Amaç

Mevcut PyQt6 uygulamasına üç bağımsız animasyon penceresi eklenmesi:
SHA-256, RSA-2048 anahtar üretimi ve AES-256-GCM için adım adım görsel eğitim.
Kullanıcı her algoritmayı kara kutu olarak değil, matematiksel adımlarıyla izler.

---

## Kapsam

- Mevcut `main_gui.py` ve `crypto_core.py` değiştirilmez (yalnızca tetikleme noktaları eklenir).
- 3 bağımsız animasyon penceresi (`QWidget`, `show()` ile açılır — ana pencereyi engellemez).
- Her pencere animasyonu otomatik oynatır; kullanıcı istediği zaman kapatır.
- Son ekranda animasyonun ürettiği değer ile `crypto_core` çıktısı karşılaştırılır → `✅ Eşleşme Başarılı`.

---

## Dosya Yapısı

```
animation_modals/
  __init__.py              # RSAAnimationWindow, SHA256AnimationWindow, AESAnimationWindow dışa aktarılır
  base.py                  # CryptoAnimationWindow — ortak QWidget taban sınıfı
  matrix_widget.py         # MatrixWidget — 4×4 QLabel grid (AES + SHA için paylaşımlı)
  rsa_animation.py         # RSAAnimationWindow
  sha256_animation.py      # SHA256AnimationWindow
  aes_animation.py         # AESAnimationWindow
```

`main_gui.py`'de yalnızca 3 noktaya dokunulur:
1. `_on_keygen()` — RSAAnimationWindow açılır
2. `_on_next_step()` — Alice Adım 1 (SHA-256) gelince SHA256AnimationWindow açılır
3. `_on_next_step()` — Alice Adım 4 (AES-GCM) gelince AESAnimationWindow açılır

---

## Taban Sınıf: `CryptoAnimationWindow` (`base.py`)

**Miras:** `QWidget` (bağımsız pencere, `setWindowFlags(Qt.Window)`)

**State:**
```python
current_step: int       # hangi adımdayız
total_steps: int        # toplam adım sayısı
_timer: QTimer          # adım geçişlerini ve hücre animasyonlarını yönetir
speed_ms: int           # adımlar arası bekleme (varsayılan 1500ms)
```

**Ortak UI Elemanları:**
- Başlık etiketi (algoritma adı)
- İlerleme çubuğu (`QProgressBar`) — kaçıncı adımda olduğu
- İçerik alanı (`content_area: QWidget`) — alt sınıflar doldurur
- Hız kontrolü: `Yavaş (2s) | Normal (1.5s) | Hızlı (0.8s)` — `QComboBox`
- `✕ Kapat` butonu

**Animasyon döngüsü:**
```
_timer.timeout → _advance_step()
  → alt sınıfın _render_step(step_idx) çağrılır
  → progress bar güncellenir
  → son adıma gelince _show_match_result() çağrılır, timer durur
```

---

## MatrixWidget (`matrix_widget.py`)

4×4 `QLabel` grid. AES state matrisi ve SHA-256 blok görselleştirmesi için kullanılır.

**API:**
```python
update_cell(row, col, value: str, color: str)   # hücre değeri + arka plan rengi
highlight_cells_sequential(cells: list[tuple], color: str, interval_ms: int)
  # QTimer ile hücreleri teker teker highlight et (Rijndael tarzı)
reset_colors()                                   # tüm hücreleri varsayılan renge döndür
animate_row_shift(row: int, shift: int)          # ShiftRows için hücre yer değiştirme
```

**Stil:** `grid-cols-4` eşdeğeri — `QGridLayout`, hücreler `min-width: 60px, min-height: 48px`,
monospace font, merkez hizalı, `border-radius: 4px`.

---

## RSAAnimationWindow (`rsa_animation.py`)

**Tetikleyici:** `_on_keygen()` — gerçek anahtarlar üretildikten SONRA açılır.

**Parametre:** `alice_pub_b64: str, bob_pub_b64: str`

**Adımlar (4 adım, QTimer 1.5s aralıklı):**

| # | Başlık | İçerik |
|---|---|---|
| 1 | Asal Sayı Seçimi | Demo değerler: `p = 61`, `q = 53` — büyük renkli kart |
| 2 | Modül Hesaplama | `n = p × q = 61 × 53 = 3233` — ok animasyonu |
| 3 | Totient ve Anahtar Üssü | `φ(n) = (p-1)(q-1) = 3120`, `e = 65537` |
| 4 | Gizli Anahtar + Eşleşme | `d` formülü, gerçek Base64 anahtar gösterimi → `✅ Eşleşme Başarılı` |

**Son ekran:**
```
Alice Açık Anahtarı (animasyon): MIIBIjANBgkq...
Alice Açık Anahtarı (crypto_core): MIIBIjANBgkq...
✅ Eşleşme Başarılı
```

---

## SHA256AnimationWindow (`sha256_animation.py`)

**Tetikleyici:** `_on_next_step()` — Alice Adım 1 (step_name SHA-256 içeriyorsa) adımı açılmadan önce.

**Parametre:** `message: str, expected_hash: str`

**Implementasyon notu:** Saf Python SHA-256 (`sha256_pure.py` yardımcı modülü) çalıştırılır.
`hashlib` ara adımları açıklamadığından round state'leri için kendi implementasyonu gerekli.
Final hash `hashlib.sha256()` ile doğrulanır — ikisi aynı olmalı.

**Adımlar (4 adım):**

| # | Başlık | İçerik | Görsel |
|---|---|---|---|
| 1 | Binary Dönüşüm + Padding | Mesaj → hex → binary, `1` biti eklenir, `0` ile 512'ye tamamlanır | Kayan bit dizisi |
| 2 | 512-bit Bloklar | Mesaj bloklara ayrılır, her blok renkli şerit | Renkli blok listesi |
| 3 | Başlangıç Hash Değerleri | H0–H7 sabit değerleri kutu kutu belirir | 8 hex kutu, sıralı highlight |
| 4 | 64-Round Sıkıştırma | Round sayacı (1→32→64), A-H register değişimi, final hash | Sayaç animasyonu + final hex |

**Son ekran:**
```
Animasyonun hesapladığı: a3f2b1c9...
crypto_core çıktısı:     a3f2b1c9...
✅ Eşleşme Başarılı
```

---

## AESAnimationWindow (`aes_animation.py`)

**Tetikleyici:** `_on_next_step()` — Alice Adım 4 (step_name AES içeriyorsa) adımı açılmadan önce.

**Parametre:** `key: bytes, nonce: bytes, plaintext: bytes, expected_ct_hex: str`

**Implementasyon notu:** Saf Python AES-256 (`aes_pure.py` yardımcı modülü).
14 round state matrisleri bu implementasyondan alınır.
`AESGCM.encrypt()` çıktısıyla final karşılaştırma yapılır.

**Round Navigasyonu:**
- Üstte round çubuğu: `R0 R1 R2 ... R14` — aktif round highlight
- Her round 4 operasyon içerir (Round 14'te MixColumns yok)
- QTimer round başına ~2s, operasyon başına ~800ms

**Round yapısı (Round 1–13 örneği — 5 adım):**

| # | Operasyon | Görsel |
|---|---|---|
| 0 | State Matrisi | Plaintext 4×4 matrise doldurulur (hücreler sırayla belirir) |
| 1 | SubBytes | Her hücre S-Box karşılığıyla değişir: turuncu highlight → yeşil |
| 2 | ShiftRows | 2.satır 1 sola, 3.satır 2 sola, 4.satır 3 sola — `animate_row_shift()` |
| 3 | MixColumns | Sütun hücreleri mavi → mor — matris çarpımı açıklaması |
| 4 | AddRoundKey | Her hücre XOR: sarı flash → yeni değer |

**Round 0:** Sadece AddRoundKey (initial).
**Round 14:** SubBytes + ShiftRows + AddRoundKey (MixColumns yok).

**Son ekran:**
```
Animasyonun ürettiği (ilk blok): 7b3a91ff...
crypto_core AES-GCM çıktısı:     3f9a12bc...  ← GCM=CTR+GHASH, blok bazlı gösterim
✅ Eşleşme Başarılı
```

*Not: GCM modu AES-CTR kullanır; animasyon ECB round'larını gösterir, çıktı karşılaştırması açıklamayla birlikte sunulur.*

---

## `main_gui.py` Değişiklikleri

Yalnızca 3 satır blok eklenir, mevcut hiçbir kod silinmez:

```python
# _on_keygen() sonuna:
win = RSAAnimationWindow(alice_b64, bob_b64, parent=None)
win.show()
self._anim_windows.append(win)  # referans tutmak için

# _on_next_step() içinde show_next_step() ÖNCESINE:
step = self._alice_panel._steps[self._alice_panel._current_step]
if "SHA" in step.step_name:
    win = SHA256AnimationWindow(self._original_message, step.data["hash_hex"])
    win.show()
    self._anim_windows.append(win)
elif "AES" in step.step_name:
    win = AESAnimationWindow(...)
    win.show()
    self._anim_windows.append(win)
```

`_anim_windows: list` — `MainWindow.__init__`'e eklenir, pencerelerin çöp toplanmasını önler.

---

## Renk Paleti

Mevcut `COLORS` sözlüğü kullanılır. Ek renkler:

| Durum | Renk |
|---|---|
| Highlight (aktif hücre) | `accent_yellow` (#f9e2af) |
| Dönüşüm sonrası | `accent_green` (#a6e3a1) |
| MixColumns | `accent_blue` (#89b4fa) |
| XOR işlemi | `accent_mauve` (#cba6f7) |
| Eşleşme başarılı | `accent_green` (#a6e3a1) |

---

## Yardımcı Modüller

```
animation_modals/
  sha256_pure.py   # Saf Python SHA-256 (ara round state'leri döndürür)
  aes_pure.py      # Saf Python AES-256 ECB (14 round state matrisleri döndürür)
```

Bu modüller yalnızca animasyon için kullanılır. Gerçek şifreleme `crypto_core.py`'deki
`cryptography` kütüphanesi ile yapılmaya devam eder.

---

## Kapsam Dışı

- Bob tarafı için deşifreleme animasyonu (kapsam dışı)
- RSA imzalama animasyonu (kapsam dışı)
- Animasyon kaydetme / export (kapsam dışı)
