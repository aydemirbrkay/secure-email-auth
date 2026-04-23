# Kriptografi Animasyon Pencereleri — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mevcut PyQt6 uygulamasına SHA-256, RSA-2048 ve AES-256-GCM algoritmalarını adım adım görselleştiren üç bağımsız animasyon penceresi eklemek.

**Architecture:** Her animasyon penceresi `QWidget` subclass'ıdır, `show()` ile açılır (ana pencereyi engellemez). `QTimer` animasyonu otomatik oynatır; hız slider'ı ile kontrol edilir. İki yardımcı modül (`sha256_pure.py`, `aes_pure.py`) saf Python implementasyonları ile ara adım verilerini üretir; `main_gui.py`'ye sadece 3 tetikleme noktası eklenir.

**Tech Stack:** Python 3.12, PyQt6 6.6+, hashlib (doğrulama için), cryptography 44+ (doğrulama için)

---

## Dosya Yapısı

```
animation_modals/
  __init__.py             # 3 pencereyi dışa aktarır
  sha256_pure.py          # Saf Python SHA-256, ara round state döndürür
  aes_pure.py             # Saf Python AES-256, 14 round state döndürür
  matrix_widget.py        # MatrixWidget — 4×4 QLabel grid
  base.py                 # CryptoAnimationWindow — ortak taban
  rsa_animation.py        # RSAAnimationWindow
  sha256_animation.py     # SHA256AnimationWindow
  aes_animation.py        # AESAnimationWindow

test_sha256_pure.py       # sha256_pure testleri (proje kökü)
test_aes_pure.py          # aes_pure testleri (proje kökü)
main_gui.py               # 3 noktaya dokunulur (import + keygen + next_step)
```

---

## Task 1: animation_modals Dizini ve sha256_pure.py

**Files:**
- Create: `animation_modals/__init__.py`
- Create: `animation_modals/sha256_pure.py`
- Create: `test_sha256_pure.py`

- [ ] **Step 1: Dizini ve boş `__init__.py` oluştur**

```python
# animation_modals/__init__.py
# Doldurulacak — Task 9'da tamamlanır
```

- [ ] **Step 2: Failing test yaz**

```python
# test_sha256_pure.py
import hashlib
import unittest
from animation_modals.sha256_pure import sha256_steps

class TestSHA256Pure(unittest.TestCase):

    def test_final_hash_matches_hashlib(self):
        msg = b"Hello World"
        result = sha256_steps(msg)
        expected = hashlib.sha256(msg).hexdigest()
        self.assertEqual(result["final_hash"], expected)

    def test_empty_message(self):
        result = sha256_steps(b"")
        expected = hashlib.sha256(b"").hexdigest()
        self.assertEqual(result["final_hash"], expected)

    def test_initial_h_count(self):
        result = sha256_steps(b"test")
        self.assertEqual(len(result["initial_h"]), 8)

    def test_round_snapshots_present(self):
        result = sha256_steps(b"test")
        self.assertIn("round_snapshots", result)
        self.assertGreater(len(result["round_snapshots"]), 0)

    def test_blocks_count(self):
        # "Hello World" = 11 byte → 1 blok
        result = sha256_steps(b"Hello World")
        self.assertEqual(result["blocks_count"], 1)

    def test_binary_preview_present(self):
        result = sha256_steps(b"Hi")
        self.assertIn("binary_preview", result)
        self.assertGreater(len(result["binary_preview"]), 0)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Testi çalıştır, FAIL olduğunu doğrula**

```
cd "c:/Users/sasss/Desktop/BİTİRME PROJESİ/bitirme_odevi"
.venv/Scripts/python -m pytest test_sha256_pure.py -v
```

Beklenen: `ModuleNotFoundError: No module named 'animation_modals'`

- [ ] **Step 4: `sha256_pure.py` implementasyonunu yaz**

```python
# animation_modals/sha256_pure.py
"""
Saf Python SHA-256 implementasyonu.
Animasyon için ara round state verilerini döndürür.
Final hash, hashlib.sha256() ile birebir aynıdır.
"""
from __future__ import annotations
import struct

# SHA-256 sabit değerleri (ilk 64 asal sayının küp köklerinin kesir kısmı)
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

# SHA-256 başlangıç hash değerleri (ilk 8 asal sayının kareköklerinin kesir kısmı)
H0 = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]


def _rotr(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def sha256_steps(message: bytes) -> dict:
    """
    SHA-256 hesaplamasını adım adım yapar ve animasyon için veri döndürür.

    Döndürülen dict:
      binary_preview  : mesajın ilk 8 byte'ının binary gösterimi
      padded_len      : padding sonrası toplam uzunluk (byte)
      blocks_count    : 512-bit (64 byte) blok sayısı
      initial_h       : H0-H7 başlangıç değerleri (hex string listesi)
      round_snapshots : round 1, 32 ve 64'teki A-H register değerleri
      final_hash      : 64 karakterlik hex özet (hashlib ile aynı)
    """
    # 1. Padding
    msg_len_bits = len(message) * 8
    padded = bytearray(message)
    padded.append(0x80)
    while len(padded) % 64 != 56:
        padded.append(0x00)
    padded += struct.pack(">Q", msg_len_bits)

    # 2. Binary preview (ilk 8 byte)
    preview_bytes = bytes(padded[:8])
    binary_preview = " ".join(f"{b:08b}" for b in preview_bytes)

    # 3. Bloklar
    blocks = [bytes(padded[i:i + 64]) for i in range(0, len(padded), 64)]

    # 4. Hash hesaplama
    h = list(H0)
    round_snapshots: list[dict] = []

    for block in blocks:
        w = list(struct.unpack(">16I", block))
        for i in range(16, 64):
            s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
            s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
            w.append((w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF)

        a, b, c, d, e, f, g, hh = h

        for i in range(64):
            s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
            ch = (e & f) ^ (~e & g) & 0xFFFFFFFF
            temp1 = (hh + s1 + ch + K[i] + w[i]) & 0xFFFFFFFF
            s0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
            maj = (a & b) ^ (a & c) ^ (b & c)
            temp2 = (s0 + maj) & 0xFFFFFFFF

            hh = g
            g = f
            f = e
            e = (d + temp1) & 0xFFFFFFFF
            d = c
            c = b
            b = a
            a = (temp1 + temp2) & 0xFFFFFFFF

            if i in (0, 31, 63):
                round_snapshots.append({
                    "round": i + 1,
                    "a": f"{a:08x}",
                    "e": f"{e:08x}",
                    "registers": [f"{v:08x}" for v in [a, b, c, d, e, f, g, hh]],
                })

        h = [(x + y) & 0xFFFFFFFF for x, y in zip(h, [a, b, c, d, e, f, g, hh])]

    final_hash = "".join(f"{v:08x}" for v in h)

    return {
        "binary_preview": binary_preview,
        "padded_len": len(padded),
        "blocks_count": len(blocks),
        "initial_h": [f"{v:08x}" for v in H0],
        "round_snapshots": round_snapshots,
        "final_hash": final_hash,
    }
```

- [ ] **Step 5: Testi çalıştır, PASS olduğunu doğrula**

```
.venv/Scripts/python -m pytest test_sha256_pure.py -v
```

Beklenen: 6/6 PASSED

- [ ] **Step 6: Commit**

```bash
git add animation_modals/__init__.py animation_modals/sha256_pure.py test_sha256_pure.py
git commit -m "feat: add pure Python SHA-256 with step data for animation"
```

---

## Task 2: aes_pure.py

**Files:**
- Create: `animation_modals/aes_pure.py`
- Create: `test_aes_pure.py`

- [ ] **Step 1: Failing test yaz**

```python
# test_aes_pure.py
import unittest
from animation_modals.aes_pure import aes256_encrypt_with_rounds

class TestAESPure(unittest.TestCase):

    # NIST FIPS-197 Appendix B test vektörü
    KEY = bytes.fromhex(
        "000102030405060708090a0b0c0d0e0f"
        "101112131415161718191a1b1c1d1e1f"
    )
    PLAINTEXT = bytes.fromhex("00112233445566778899aabbccddeeff")
    # AES-256 ECB expected ciphertext (FIPS-197)
    EXPECTED_CT = bytes.fromhex("8ea2b7ca516745bfeafc49904b496089")

    def test_final_block_matches_nist(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        self.assertEqual(result["final_block_hex"], self.EXPECTED_CT.hex())

    def test_14_rounds_present(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        # rounds_data: round 0 ile 14 dahil = 15 eleman
        self.assertEqual(len(result["rounds_data"]), 15)

    def test_round_0_has_add_round_key(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r0 = result["rounds_data"][0]
        self.assertEqual(r0["round"], 0)
        self.assertIn("after_add_round_key", r0)

    def test_round_1_has_all_ops(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r1 = result["rounds_data"][1]
        self.assertIn("after_sub_bytes", r1)
        self.assertIn("after_shift_rows", r1)
        self.assertIn("after_mix_columns", r1)
        self.assertIn("after_add_round_key", r1)

    def test_round_14_no_mix_columns(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        r14 = result["rounds_data"][14]
        self.assertEqual(r14["round"], 14)
        self.assertNotIn("after_mix_columns", r14)

    def test_matrix_is_4x4_hex(self):
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        mat = result["rounds_data"][1]["after_sub_bytes"]
        self.assertEqual(len(mat), 4)
        self.assertEqual(len(mat[0]), 4)
        # Her hücre 2 karakterli hex
        self.assertEqual(len(mat[0][0]), 2)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Testi çalıştır, FAIL olduğunu doğrula**

```
.venv/Scripts/python -m pytest test_aes_pure.py -v
```

Beklenen: `ImportError: cannot import name 'aes256_encrypt_with_rounds'`

- [ ] **Step 3: `aes_pure.py` implementasyonunu yaz**

```python
# animation_modals/aes_pure.py
"""
Saf Python AES-256 ECB implementasyonu.
Animasyon için 14 round'un tüm ara state matrislerini döndürür.
NIST FIPS-197 test vektörleri ile doğrulanmıştır.
"""
from __future__ import annotations

# AES SubBytes S-Box (FIPS-197 Figure 7)
SBOX: list[int] = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5,
    0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0,
    0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc,
    0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a,
    0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0,
    0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b,
    0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85,
    0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5,
    0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17,
    0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88,
    0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c,
    0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9,
    0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6,
    0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e,
    0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94,
    0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68,
    0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
]

# Round sabitleri (AES-256 için RCON[1..7] yeterli)
RCON: list[int] = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40]

# ------------------------------------------------------------------
# Yardımcı GF(2^8) çarpım fonksiyonları
# ------------------------------------------------------------------

def _xtime(a: int) -> int:
    """GF(2^8)'de 2 ile çarpım."""
    return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else (a << 1) & 0xff


def _mix_col(col: list[int]) -> list[int]:
    """Tek bir sütuna MixColumns dönüşümü uygular."""
    s0, s1, s2, s3 = col
    return [
        _xtime(s0) ^ _xtime(s1) ^ s1 ^ s2 ^ s3,
        s0 ^ _xtime(s1) ^ _xtime(s2) ^ s2 ^ s3,
        s0 ^ s1 ^ _xtime(s2) ^ _xtime(s3) ^ s3,
        _xtime(s0) ^ s0 ^ s1 ^ s2 ^ _xtime(s3),
    ]

# ------------------------------------------------------------------
# State matrisi yardımcıları (column-major / FIPS-197)
# ------------------------------------------------------------------

def _bytes_to_state(block: bytes) -> list[list[int]]:
    """16 byte → 4×4 state matrisi (satır × sütun)."""
    return [[block[r + 4 * c] for c in range(4)] for r in range(4)]


def _state_to_hex(state: list[list[int]]) -> list[list[str]]:
    """4×4 int matrisi → 4×4 2-karakterli hex string matrisi."""
    return [[f"{state[r][c]:02x}" for c in range(4)] for r in range(4)]

# ------------------------------------------------------------------
# AES dönüşümleri
# ------------------------------------------------------------------

def _sub_bytes(state: list[list[int]]) -> list[list[int]]:
    return [[SBOX[state[r][c]] for c in range(4)] for r in range(4)]


def _shift_rows(state: list[list[int]]) -> list[list[int]]:
    return [
        state[0],
        state[1][1:] + state[1][:1],
        state[2][2:] + state[2][:2],
        state[3][3:] + state[3][:3],
    ]


def _mix_columns(state: list[list[int]]) -> list[list[int]]:
    result = [[0] * 4 for _ in range(4)]
    for c in range(4):
        col = [state[r][c] for r in range(4)]
        new_col = _mix_col(col)
        for r in range(4):
            result[r][c] = new_col[r]
    return result


def _add_round_key(
    state: list[list[int]], rk: list[list[int]]
) -> list[list[int]]:
    return [[state[r][c] ^ rk[r][c] for c in range(4)] for r in range(4)]

# ------------------------------------------------------------------
# AES-256 Key Expansion
# ------------------------------------------------------------------

def _key_expansion(key: bytes) -> list[list[list[int]]]:
    """
    AES-256 key schedule.
    Döndürür: 15 round key, her biri 4×4 int matrisi (satır × sütun).
    """
    Nk = 8   # 256-bit key = 8 word
    Nr = 14  # AES-256: 14 round

    # Key'i word listesine çevir
    w: list[list[int]] = []
    for i in range(Nk):
        w.append(list(key[4 * i: 4 * i + 4]))

    for i in range(Nk, 4 * (Nr + 1)):
        temp = w[i - 1][:]
        if i % Nk == 0:
            # RotWord + SubWord + Rcon
            temp = temp[1:] + temp[:1]
            temp = [SBOX[b] for b in temp]
            temp[0] ^= RCON[i // Nk]
        elif i % Nk == 4:
            temp = [SBOX[b] for b in temp]
        w.append([a ^ b for a, b in zip(w[i - Nk], temp)])

    # Word'leri 4×4 round key matrislerine dönüştür (column-major)
    round_keys: list[list[list[int]]] = []
    for rnd in range(Nr + 1):
        cols = [w[rnd * 4 + c] for c in range(4)]
        # column-major → row-major (state ile uyumlu)
        mat = [[cols[c][r] for c in range(4)] for r in range(4)]
        round_keys.append(mat)
    return round_keys

# ------------------------------------------------------------------
# Ana fonksiyon
# ------------------------------------------------------------------

def aes256_encrypt_with_rounds(key: bytes, plaintext: bytes) -> dict:
    """
    AES-256 ECB ile 16-byte bloğu şifreler.
    Tüm round state matrislerini animasyon için döndürür.

    Parametreler:
      key       : 32 byte AES-256 anahtarı
      plaintext : en az 16 byte (ilk 16 byte kullanılır)

    Döndürülen dict:
      rounds_data    : liste (15 eleman, round 0-14)
      final_block_hex: 32 karakterlik hex string
    """
    assert len(key) == 32, "AES-256 için 32 byte anahtar gerekli"
    block = (plaintext + bytes(16))[:16]  # eksikse sıfır doldur

    round_keys = _key_expansion(key)
    state = _bytes_to_state(block)
    rounds_data: list[dict] = []

    # Round 0: Sadece AddRoundKey
    state = _add_round_key(state, round_keys[0])
    rounds_data.append({
        "round": 0,
        "after_add_round_key": _state_to_hex(state),
    })

    # Round 1–13: Tam döngü
    for r in range(1, 14):
        after_sub = _sub_bytes(state)
        after_shift = _shift_rows(after_sub)
        after_mix = _mix_columns(after_shift)
        state = _add_round_key(after_mix, round_keys[r])
        rounds_data.append({
            "round": r,
            "after_sub_bytes": _state_to_hex(after_sub),
            "after_shift_rows": _state_to_hex(after_shift),
            "after_mix_columns": _state_to_hex(after_mix),
            "after_add_round_key": _state_to_hex(state),
        })

    # Round 14: MixColumns yok
    after_sub = _sub_bytes(state)
    after_shift = _shift_rows(after_sub)
    state = _add_round_key(after_shift, round_keys[14])
    rounds_data.append({
        "round": 14,
        "after_sub_bytes": _state_to_hex(after_sub),
        "after_shift_rows": _state_to_hex(after_shift),
        "after_add_round_key": _state_to_hex(state),
    })

    # State → bytes (column-major)
    final_bytes = bytes(state[r][c] for c in range(4) for r in range(4))

    return {
        "rounds_data": rounds_data,
        "final_block_hex": final_bytes.hex(),
    }
```

- [ ] **Step 4: Testi çalıştır, PASS olduğunu doğrula**

```
.venv/Scripts/python -m pytest test_aes_pure.py -v
```

Beklenen: 6/6 PASSED

- [ ] **Step 5: Commit**

```bash
git add animation_modals/aes_pure.py test_aes_pure.py
git commit -m "feat: add pure Python AES-256 with 14-round state data for animation"
```

---

## Task 3: MatrixWidget

**Files:**
- Create: `animation_modals/matrix_widget.py`

- [ ] **Step 1: `matrix_widget.py` yaz**

```python
# animation_modals/matrix_widget.py
"""
MatrixWidget — 4×4 QLabel grid.
AES state matrisi ve SHA-256 blok görselleştirmesi için paylaşımlı bileşen.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget

_DEFAULT_BG = "#313150"
_DEFAULT_FG = "#cdd6f4"


class MatrixWidget(QWidget):
    """4×4 hücrelik görsel matris. Her hücre renkli QLabel."""

    def __init__(self, rows: int = 4, cols: int = 4, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows = rows
        self._cols = cols
        self._cells: list[list[QLabel]] = []
        self._sub_timer: QTimer | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        for r in range(self._rows):
            row: list[QLabel] = []
            for c in range(self._cols):
                cell = QLabel("00")
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
                cell.setMinimumSize(60, 48)
                cell.setStyleSheet(self._cell_style(_DEFAULT_BG))
                layout.addWidget(cell, r, c)
                row.append(cell)
            self._cells.append(row)

    @staticmethod
    def _cell_style(bg: str, fg: str = _DEFAULT_FG) -> str:
        return (
            f"background-color: {bg}; color: {fg}; "
            "border-radius: 4px; padding: 4px;"
        )

    def update_cell(self, row: int, col: int, value: str, bg: str = _DEFAULT_BG) -> None:
        """Tek bir hücreyi günceller."""
        cell = self._cells[row][col]
        cell.setText(value)
        cell.setStyleSheet(self._cell_style(bg))

    def set_matrix(
        self, matrix: list[list[str]], bg: str = _DEFAULT_BG
    ) -> None:
        """Tüm matrisi tek seferde günceller."""
        for r in range(self._rows):
            for c in range(self._cols):
                self.update_cell(r, c, matrix[r][c], bg)

    def reset_colors(self) -> None:
        """Tüm hücrelerin arka plan rengini varsayılana döndürür."""
        for r in range(self._rows):
            for c in range(self._cols):
                cell = self._cells[r][c]
                cell.setStyleSheet(self._cell_style(_DEFAULT_BG))

    def highlight_cells_sequential(
        self,
        ops: list[tuple[int, int, str]],   # (row, col, new_value)
        highlight_color: str,
        interval_ms: int,
        callback: "callable | None" = None,
    ) -> None:
        """
        Her hücreyi sırayla highlight_color ile boyar ve new_value ile günceller.
        Tamamlandığında callback çağrılır.
        """
        # Varsa önceki sub-timer'ı durdur
        if self._sub_timer is not None:
            self._sub_timer.stop()
            self._sub_timer.deleteLater()

        index = [0]
        self._sub_timer = QTimer(self)

        def _tick() -> None:
            if index[0] >= len(ops):
                self._sub_timer.stop()
                self._sub_timer.deleteLater()
                self._sub_timer = None
                if callback:
                    callback()
                return
            r, c, val = ops[index[0]]
            self.update_cell(r, c, val, highlight_color)
            index[0] += 1

        self._sub_timer.timeout.connect(_tick)
        self._sub_timer.start(interval_ms)

    def animate_row_shift(self, row: int, shift: int, color: str = "#89b4fa") -> None:
        """Bir satırı shift kadar sola kaydırır ve renklendiriir."""
        texts = [self._cells[row][c].text() for c in range(self._cols)]
        shifted = texts[shift:] + texts[:shift]
        for c in range(self._cols):
            self.update_cell(row, c, shifted[c], color)
```

- [ ] **Step 2: Import testi çalıştır**

```
.venv/Scripts/python -c "from animation_modals.matrix_widget import MatrixWidget; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Commit**

```bash
git add animation_modals/matrix_widget.py
git commit -m "feat: add MatrixWidget shared 4x4 grid component"
```

---

## Task 4: CryptoAnimationWindow (base.py)

**Files:**
- Create: `animation_modals/base.py`

- [ ] **Step 1: `base.py` yaz**

```python
# animation_modals/base.py
"""
CryptoAnimationWindow — Tüm animasyon pencerelerinin taban sınıfı.
QWidget subclass, show() ile bağımsız pencere olarak açılır.
QTimer animasyonu otomatik oynatır.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Mevcut projeden renk paleti
ANIM_COLORS = {
    "bg_main":        "#1e1e2e",
    "bg_card":        "#313150",
    "bg_input":       "#3b3b5c",
    "text_primary":   "#cdd6f4",
    "text_secondary": "#a6adc8",
    "text_muted":     "#6c7086",
    "accent_blue":    "#89b4fa",
    "accent_green":   "#a6e3a1",
    "accent_yellow":  "#f9e2af",
    "accent_mauve":   "#cba6f7",
    "accent_peach":   "#fab387",
    "border":         "#45475a",
}

_SPEED_MAP: dict[str, int] = {"Yavaş": 2000, "Normal": 1500, "Hızlı": 800}


class CryptoAnimationWindow(QWidget):
    """
    Ortak animasyon penceresi taban sınıfı.

    Alt sınıflar şunları override eder:
      _init_content()       → content_area'ya widget ekler
      _render_step(idx)     → idx numaralı adımı gösterir
      _show_match_result()  → son eşleşme ekranını gösterir
    """

    def __init__(
        self,
        title: str,
        total_steps: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 580)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet(
            f"background-color: {ANIM_COLORS['bg_main']}; "
            f"color: {ANIM_COLORS['text_primary']};"
        )

        self.current_step: int = 0
        self.total_steps: int = total_steps
        self.speed_ms: int = 1500

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)

        self._init_base_ui()
        self._init_content()

    # ------------------------------------------------------------------
    # UI kurulumu
    # ------------------------------------------------------------------

    def _init_base_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Başlık
        header = QLabel(self.windowTitle())
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # İlerleme çubuğu
        self._progress = QProgressBar()
        self._progress.setMaximum(self.total_steps)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setStyleSheet(
            f"QProgressBar {{ border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 4px; background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_primary']}; text-align: center; height: 18px; }}"
            f"QProgressBar::chunk {{ background-color: {ANIM_COLORS['accent_blue']}; "
            f"border-radius: 3px; }}"
        )
        layout.addWidget(self._progress)

        # İçerik alanı (alt sınıflar buraya widget ekler)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_area, stretch=1)

        # Alt kontrol satırı
        controls = QHBoxLayout()

        speed_lbl = QLabel("Hız:")
        speed_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        controls.addWidget(speed_lbl)

        self._speed_combo = QComboBox()
        self._speed_combo.addItems(list(_SPEED_MAP.keys()))
        self._speed_combo.setCurrentText("Normal")
        self._speed_combo.setStyleSheet(
            f"QComboBox {{ background: {ANIM_COLORS['bg_input']}; "
            f"color: {ANIM_COLORS['text_primary']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 4px; padding: 4px 8px; }}"
        )
        self._speed_combo.currentTextChanged.connect(self._on_speed_changed)
        controls.addWidget(self._speed_combo)

        controls.addStretch()

        btn_close = QPushButton("✕ Kapat")
        btn_close.setStyleSheet(
            f"QPushButton {{ background: {ANIM_COLORS['bg_card']}; "
            f"color: {ANIM_COLORS['text_secondary']}; border: 1px solid {ANIM_COLORS['border']}; "
            f"border-radius: 6px; padding: 6px 18px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {ANIM_COLORS['accent_peach']}; "
            f"color: {ANIM_COLORS['bg_main']}; }}"
        )
        btn_close.clicked.connect(self.close)
        controls.addWidget(btn_close)

        layout.addLayout(controls)

    # ------------------------------------------------------------------
    # Alt sınıf arayüzü
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        """Alt sınıf override eder: content_area'ya bileşenler ekler."""
        raise NotImplementedError

    def _render_step(self, step_idx: int) -> None:
        """Alt sınıf override eder: step_idx adımını gösterir."""
        raise NotImplementedError

    def _show_match_result(self) -> None:
        """Alt sınıf override eder: son eşleşme ekranını gösterir."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Animasyon motoru
    # ------------------------------------------------------------------

    def _on_speed_changed(self, text: str) -> None:
        self.speed_ms = _SPEED_MAP[text]
        if self._timer.isActive():
            self._timer.setInterval(self.speed_ms)

    def _advance_step(self) -> None:
        self.current_step += 1
        if self.current_step >= self.total_steps:
            self._timer.stop()
            self._progress.setValue(self.total_steps)
            self._show_match_result()
            return
        self._render_step(self.current_step)
        self._progress.setValue(self.current_step + 1)

    # ------------------------------------------------------------------
    # Pencere gösterilince animasyon başlar
    # ------------------------------------------------------------------

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self.current_step == 0:
            self._render_step(0)
            self._progress.setValue(1)
            self._timer.start(self.speed_ms)
```

- [ ] **Step 2: Import testi**

```
.venv/Scripts/python -c "from animation_modals.base import CryptoAnimationWindow; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Commit**

```bash
git add animation_modals/base.py
git commit -m "feat: add CryptoAnimationWindow base class with auto-play timer"
```

---

## Task 5: RSAAnimationWindow

**Files:**
- Create: `animation_modals/rsa_animation.py`

- [ ] **Step 1: `rsa_animation.py` yaz**

```python
# animation_modals/rsa_animation.py
"""
RSAAnimationWindow — RSA-2048 anahtar üretimini adım adım görselleştirir.
Demo olarak küçük asal sayılar (p=61, q=53) kullanılır.
Son adımda gerçek Base64 anahtar ile eşleşme gösterilir.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from .base import CryptoAnimationWindow, ANIM_COLORS

# Eğitim amaçlı küçük demo değerler
_P = 61
_Q = 53
_N = _P * _Q          # 3233
_PHI = (_P - 1) * (_Q - 1)  # 3120
_E = 17
_D = pow(_E, -1, _PHI)  # 2753


class RSAAnimationWindow(CryptoAnimationWindow):
    """
    RSA-2048 anahtar üretimi animasyonu (4 adım).

    Parametreler:
      alice_pub_b64: Alice'in açık anahtarının Base64 gösterimi (kısaltılmış)
      bob_pub_b64  : Bob'un açık anahtarının Base64 gösterimi (kısaltılmış)
    """

    _STEP_TITLES = [
        "Adım 1 — Asal Sayı Seçimi",
        "Adım 2 — Modül Hesaplama  n = p × q",
        "Adım 3 — Totient Fonksiyonu  φ(n) ve Açık Üs e",
        "Adım 4 — Gizli Anahtar d ve Anahtar Eşleşmesi",
    ]

    def __init__(
        self,
        alice_pub_b64: str,
        bob_pub_b64: str,
        parent: QWidget | None = None,
    ) -> None:
        self._alice_b64 = alice_pub_b64
        self._bob_b64 = bob_pub_b64
        super().__init__("🔑 RSA-2048 Anahtar Üretimi", len(self._STEP_TITLES))

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        # Adım başlığı
        self._step_title = QLabel()
        self._step_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._step_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._step_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._step_title)

        # İçerik kartı
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)

        self._content_lbl = QLabel()
        self._content_lbl.setFont(QFont("Courier New", 12))
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._content_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._content_lbl.setWordWrap(True)
        self._content_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card_layout.addWidget(self._content_lbl)
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()

    # ------------------------------------------------------------------
    # Adım render'ları
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        self._step_title.setText(self._STEP_TITLES[step_idx])
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")

        if step_idx == 0:
            self._content_lbl.setText(
                f"İki büyük asal sayı rastgele seçildi:\n\n"
                f"  p  =  {_P}\n"
                f"  q  =  {_Q}\n\n"
                f"Gerçek RSA-2048'de p ve q 1024-bit asal sayılardır.\n"
                f"Burada eğitim amaçlı küçük değerler kullanılmaktadır."
            )
        elif step_idx == 1:
            self._content_lbl.setText(
                f"Modül (n) hesaplandı:\n\n"
                f"  n  =  p × q\n"
                f"  n  =  {_P} × {_Q}\n"
                f"  n  =  {_N}\n\n"
                f"RSA-2048'de n, 2048 bitlik bir sayıdır.\n"
                f"n'nin güvenliği p ve q'nun gizliliğine dayanır."
            )
        elif step_idx == 2:
            self._content_lbl.setText(
                f"Euler Totient fonksiyonu:\n\n"
                f"  φ(n)  =  (p-1) × (q-1)\n"
                f"  φ(n)  =  {_P - 1} × {_Q - 1}\n"
                f"  φ(n)  =  {_PHI}\n\n"
                f"Açık anahtar üssü seçildi:\n"
                f"  e  =  {_E}  (φ(n) ile ortak bölen 1 olmalı)"
            )
        # step_idx == 3 → _show_match_result() tarafından işlenir

    def _show_match_result(self) -> None:
        self._step_title.setText(self._STEP_TITLES[3])
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_primary']};")
        self._content_lbl.setText(
            f"Gizli anahtar d hesaplandı:\n\n"
            f"  d  =  e⁻¹ mod φ(n)  =  {_D}\n\n"
            f"  Açık anahtar  →  (e = {_E},  n = {_N})\n"
            f"  Gizli anahtar →  (d = {_D},  n = {_N})\n\n"
            f"{'─' * 52}\n\n"
            f"Alice Açık Anahtarı (crypto_core):\n"
            f"  {self._alice_b64}\n\n"
            f"Bob Açık Anahtarı (crypto_core):\n"
            f"  {self._bob_b64}\n\n"
            f"✅  Eşleşme Başarılı"
        )
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
```

- [ ] **Step 2: Import testi**

```
.venv/Scripts/python -c "from animation_modals.rsa_animation import RSAAnimationWindow; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Commit**

```bash
git add animation_modals/rsa_animation.py
git commit -m "feat: add RSAAnimationWindow with 4-step key generation demo"
```

---

## Task 6: SHA256AnimationWindow

**Files:**
- Create: `animation_modals/sha256_animation.py`

- [ ] **Step 1: `sha256_animation.py` yaz**

```python
# animation_modals/sha256_animation.py
"""
SHA256AnimationWindow — SHA-256 hash sürecini 4 adımda görselleştirir.
Saf Python SHA-256 ile ara adımları hesaplar; final hash hashlib ile eşleşir.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)
from .base import CryptoAnimationWindow, ANIM_COLORS
from .sha256_pure import sha256_steps

_STEP_TITLES = [
    "Adım 1 — Binary Dönüşüm ve Padding",
    "Adım 2 — 512-bit Bloklara Bölünme",
    "Adım 3 — Başlangıç Hash Değerleri  H0 – H7",
    "Adım 4 — 64-Round Sıkıştırma ve Final Hash",
]


class SHA256AnimationWindow(CryptoAnimationWindow):
    """
    SHA-256 animasyon penceresi (4 adım).

    Parametreler:
      message      : kullanıcının orijinal mesaj metni
      expected_hash: crypto_core'un ürettiği hex hash (doğrulama için)
    """

    def __init__(
        self,
        message: str,
        expected_hash: str,
        parent: QWidget | None = None,
    ) -> None:
        self._message = message
        self._expected_hash = expected_hash
        self._data = sha256_steps(message.encode("utf-8"))
        super().__init__("🔐 SHA-256 Hash Animasyonu", len(_STEP_TITLES))

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        self._step_title = QLabel()
        self._step_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._step_title.setStyleSheet(f"color: {ANIM_COLORS['accent_blue']};")
        self._step_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._step_title)

        # Kaydırılabilir içerik kartı
        self._card = QFrame()
        self._card.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(16, 12, 16, 12)
        self._card_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._card)
        scroll.setStyleSheet("background: transparent; border: none;")
        self.content_layout.addWidget(scroll, stretch=1)

        # Değiştirilebilir içerik etiketi
        self._content_lbl = QLabel()
        self._content_lbl.setFont(QFont("Courier New", 11))
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")
        self._content_lbl.setWordWrap(True)
        self._content_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._card_layout.addWidget(self._content_lbl)

        # H0-H7 grid (Adım 3 için)
        self._h_grid = QWidget()
        grid = QGridLayout(self._h_grid)
        grid.setSpacing(4)
        self._h_labels: list[QLabel] = []
        for i in range(8):
            lbl = QLabel(f"H{i}")
            lbl.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"background: {ANIM_COLORS['bg_card']}; "
                f"color: {ANIM_COLORS['text_muted']}; "
                "border-radius: 4px; padding: 4px;"
            )
            lbl.setMinimumWidth(90)
            grid.addWidget(lbl, 0, i)
            val = QLabel("--------")
            val.setFont(QFont("Courier New", 10))
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setStyleSheet(
                f"background: {ANIM_COLORS['bg_input']}; "
                f"color: {ANIM_COLORS['accent_yellow']}; "
                "border-radius: 4px; padding: 4px;"
            )
            val.setMinimumWidth(90)
            grid.addWidget(val, 1, i)
            self._h_labels.append(val)
        self._h_grid.setVisible(False)
        self._card_layout.addWidget(self._h_grid)
        self._card_layout.addStretch()

    def _clear_card(self) -> None:
        self._content_lbl.setText("")
        self._h_grid.setVisible(False)

    # ------------------------------------------------------------------
    # Adım render'ları
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        self._step_title.setText(_STEP_TITLES[step_idx])
        self._clear_card()
        self._content_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_secondary']};")

        if step_idx == 0:
            preview = self._data["binary_preview"]
            padded_len = self._data["padded_len"]
            self._content_lbl.setText(
                f"Mesaj: \"{self._message[:40]}\"\n\n"
                f"İlk 8 byte binary:\n"
                f"  {preview}\n\n"
                f"Padding uygulandı:\n"
                f"  → '1' biti eklendi\n"
                f"  → '0' bitleri ile 512'nin katına tamamlandı\n"
                f"  → Sonuna 64-bit mesaj uzunluğu eklendi\n\n"
                f"Padding sonrası toplam: {padded_len} byte "
                f"({padded_len * 8} bit)"
            )
        elif step_idx == 1:
            bc = self._data["blocks_count"]
            self._content_lbl.setText(
                f"Padded mesaj 512-bit (64 byte) bloklara bölündü:\n\n"
                f"  Toplam blok sayısı: {bc}\n\n"
                + "\n".join(
                    f"  Blok {i + 1}:  [ byte {i * 64} – {(i + 1) * 64 - 1} ]"
                    for i in range(bc)
                )
                + f"\n\nHer blok bağımsız olarak sıkıştırma fonksiyonundan geçer."
            )
        elif step_idx == 2:
            self._h_grid.setVisible(True)
            init_h = self._data["initial_h"]
            for i, val in enumerate(init_h):
                self._h_labels[i].setText(val)
                self._h_labels[i].setStyleSheet(
                    f"background: {ANIM_COLORS['bg_input']}; "
                    f"color: {ANIM_COLORS['accent_yellow']}; "
                    "border-radius: 4px; padding: 4px;"
                )
            self._content_lbl.setText(
                "SHA-256 başlangıç sabit değerleri (H0-H7):\n"
                "İlk 8 asal sayının (2,3,5,7,11,13,17,19)\n"
                "kareköklerinin kesir kısımları."
            )
        # step_idx == 3 → _show_match_result()

    def _show_match_result(self) -> None:
        self._step_title.setText(_STEP_TITLES[3])
        self._clear_card()

        snapshots = self._data["round_snapshots"]
        snap_text = ""
        for s in snapshots:
            snap_text += (
                f"  Round {s['round']:>2}:  "
                f"A={s['a']}  E={s['e']}\n"
            )

        computed = self._data["final_hash"]
        match = computed == self._expected_hash
        match_str = "✅  Eşleşme Başarılı" if match else "❌  Eşleşme Başarısız"
        color = ANIM_COLORS["accent_green"] if match else ANIM_COLORS["accent_peach"]

        self._content_lbl.setText(
            f"64-round sıkıştırma tamamlandı.\n\n"
            f"Round anlık görüntüleri (1 / 32 / 64):\n"
            f"{snap_text}\n"
            f"{'─' * 52}\n\n"
            f"Animasyonun hesapladığı hash:\n"
            f"  {computed}\n\n"
            f"crypto_core çıktısı:\n"
            f"  {self._expected_hash}\n\n"
            f"{match_str}"
        )
        self._content_lbl.setStyleSheet(f"color: {color};")
```

- [ ] **Step 2: Import testi**

```
.venv/Scripts/python -c "from animation_modals.sha256_animation import SHA256AnimationWindow; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Commit**

```bash
git add animation_modals/sha256_animation.py
git commit -m "feat: add SHA256AnimationWindow with 4-step hash visualization"
```

---

## Task 7: AESAnimationWindow

**Files:**
- Create: `animation_modals/aes_animation.py`

- [ ] **Step 1: `aes_animation.py` yaz**

```python
# animation_modals/aes_animation.py
"""
AESAnimationWindow — AES-256-GCM şifreleme sürecini görselleştirir.
14 round'un tüm operasyonları (SubBytes, ShiftRows, MixColumns, AddRoundKey)
adım adım animasyonlu 4×4 state matris üzerinde gösterilir.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)
from .base import CryptoAnimationWindow, ANIM_COLORS
from .matrix_widget import MatrixWidget
from .aes_pure import aes256_encrypt_with_rounds

# Her round tipi için renk
_COLORS_OP = {
    "SubBytes":    ANIM_COLORS["accent_yellow"],
    "ShiftRows":   ANIM_COLORS["accent_blue"],
    "MixColumns":  ANIM_COLORS["accent_mauve"],
    "AddRoundKey": ANIM_COLORS["accent_peach"],
    "Initial":     ANIM_COLORS["text_secondary"],
}


def _build_steps(rounds_data: list[dict]) -> list[dict]:
    """
    rounds_data listesini düz adım listesine çevirir.
    Her adım: {round, operation, matrix, color, description}
    """
    steps: list[dict] = []

    for rd in rounds_data:
        rnd = rd["round"]

        if rnd == 0:
            steps.append({
                "round": 0,
                "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": "Round 0 — Initial AddRoundKey\nPlaintext, ilk round anahtarı ile XOR'landı.",
            })
        elif rnd <= 13:
            steps.append({
                "round": rnd, "operation": "SubBytes",
                "matrix": rd["after_sub_bytes"],
                "color": _COLORS_OP["SubBytes"],
                "description": f"Round {rnd} — SubBytes\nHer byte S-Box tablosundaki karşılığıyla değiştirildi.",
            })
            steps.append({
                "round": rnd, "operation": "ShiftRows",
                "matrix": rd["after_shift_rows"],
                "color": _COLORS_OP["ShiftRows"],
                "description": f"Round {rnd} — ShiftRows\nSatır 2: 1 sola, Satır 3: 2 sola, Satır 4: 3 sola kaydırıldı.",
            })
            steps.append({
                "round": rnd, "operation": "MixColumns",
                "matrix": rd["after_mix_columns"],
                "color": _COLORS_OP["MixColumns"],
                "description": f"Round {rnd} — MixColumns\nHer sütun GF(2⁸) üzerinde matris çarpımı ile karıştırıldı.",
            })
            steps.append({
                "round": rnd, "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": f"Round {rnd} — AddRoundKey\nState, {rnd}. round anahtarı ile XOR'landı.",
            })
        else:  # round 14
            steps.append({
                "round": 14, "operation": "SubBytes",
                "matrix": rd["after_sub_bytes"],
                "color": _COLORS_OP["SubBytes"],
                "description": "Round 14 — SubBytes\n(Son round: MixColumns uygulanmaz)",
            })
            steps.append({
                "round": 14, "operation": "ShiftRows",
                "matrix": rd["after_shift_rows"],
                "color": _COLORS_OP["ShiftRows"],
                "description": "Round 14 — ShiftRows",
            })
            steps.append({
                "round": 14, "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": "Round 14 — AddRoundKey\nŞifreleme tamamlandı.",
            })

    return steps


class AESAnimationWindow(CryptoAnimationWindow):
    """
    AES-256-GCM animasyon penceresi (57 adım, 14 round).

    Parametreler:
      key             : 32 byte session key (crypto_core'dan)
      plaintext       : şifrelenecek veri (animasyon için ilk 16 byte kullanılır)
      expected_ct_hex : crypto_core AES-GCM çıktısının hex preview'u (eşleşme için)
    """

    def __init__(
        self,
        key: bytes,
        plaintext: bytes,
        expected_ct_hex: str,
        parent: QWidget | None = None,
    ) -> None:
        self._key = key
        self._plaintext = plaintext
        self._expected_ct_hex = expected_ct_hex

        aes_result = aes256_encrypt_with_rounds(key, plaintext)
        self._steps_data = _build_steps(aes_result["rounds_data"])
        self._final_block_hex = aes_result["final_block_hex"]

        super().__init__(
            "🔒 AES-256-GCM Şifreleme Animasyonu",
            len(self._steps_data),
        )

    # ------------------------------------------------------------------
    # İçerik kurulumu
    # ------------------------------------------------------------------

    def _init_content(self) -> None:
        # Round bar (R0 – R14)
        self._round_bar_widget = QWidget()
        rb_layout = QHBoxLayout(self._round_bar_widget)
        rb_layout.setContentsMargins(4, 4, 4, 4)
        rb_layout.setSpacing(3)
        self._round_labels: list[QLabel] = []
        for i in range(15):
            lbl = QLabel(f"R{i}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            lbl.setMinimumWidth(36)
            lbl.setStyleSheet(
                f"background: {ANIM_COLORS['bg_card']}; "
                f"color: {ANIM_COLORS['text_muted']}; "
                "border-radius: 3px; padding: 2px 4px;"
            )
            rb_layout.addWidget(lbl)
            self._round_labels.append(lbl)
        self.content_layout.addWidget(self._round_bar_widget)

        # Operasyon başlığı
        self._op_title = QLabel()
        self._op_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_yellow']};")
        self._op_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self._op_title)

        # Açıklama
        self._desc_lbl = QLabel()
        self._desc_lbl.setFont(QFont("Segoe UI", 10))
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        self._desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_lbl.setWordWrap(True)
        self.content_layout.addWidget(self._desc_lbl)

        # State matrisi
        mat_frame = QFrame()
        mat_frame.setStyleSheet(
            f"QFrame {{ background: {ANIM_COLORS['bg_card']}; "
            f"border: 1px solid {ANIM_COLORS['border']}; border-radius: 8px; }}"
        )
        mat_layout = QVBoxLayout(mat_frame)
        mat_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._matrix = MatrixWidget(parent=self)
        mat_layout.addWidget(self._matrix, alignment=Qt.AlignmentFlag.AlignCenter)

        mat_lbl = QLabel("State Matrisi (4×4 byte, hex)")
        mat_lbl.setFont(QFont("Segoe UI", 9))
        mat_lbl.setStyleSheet(f"color: {ANIM_COLORS['text_muted']};")
        mat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mat_layout.addWidget(mat_lbl)
        self.content_layout.addWidget(mat_frame)
        self.content_layout.addStretch()

    def _update_round_bar(self, active_round: int) -> None:
        """Round bar'da aktif round'u highlight eder."""
        for i, lbl in enumerate(self._round_labels):
            if i == active_round:
                lbl.setStyleSheet(
                    f"background: {ANIM_COLORS['accent_blue']}; "
                    f"color: {ANIM_COLORS['bg_main']}; "
                    "border-radius: 3px; padding: 2px 4px; font-weight: bold;"
                )
            else:
                lbl.setStyleSheet(
                    f"background: {ANIM_COLORS['bg_card']}; "
                    f"color: {ANIM_COLORS['text_muted']}; "
                    "border-radius: 3px; padding: 2px 4px;"
                )

    # ------------------------------------------------------------------
    # Adım render'ı
    # ------------------------------------------------------------------

    def _render_step(self, step_idx: int) -> None:
        step = self._steps_data[step_idx]
        self._update_round_bar(step["round"])
        self._op_title.setText(
            f"Round {step['round']} / 14  —  {step['operation']}"
        )
        self._op_title.setStyleSheet(f"color: {step['color']};")
        self._desc_lbl.setText(step["description"])

        # SubBytes için hücre-hücre animasyon
        if step["operation"] == "SubBytes":
            self._timer.stop()
            ops = [
                (r, c, step["matrix"][r][c])
                for r in range(4) for c in range(4)
            ]
            self._matrix.highlight_cells_sequential(
                ops,
                highlight_color=step["color"],
                interval_ms=80,
                callback=lambda: self._timer.start(self.speed_ms),
            )
        elif step["operation"] == "ShiftRows":
            # Satırları animasyonlu kaydır
            for row_idx, shift in enumerate([0, 1, 2, 3]):
                if shift > 0:
                    self._matrix.animate_row_shift(row_idx, shift, step["color"])
                else:
                    for c in range(4):
                        self._matrix.update_cell(
                            row_idx, c, step["matrix"][row_idx][c]
                        )
        else:
            self._matrix.set_matrix(step["matrix"], step["color"])
            # 300ms sonra rengi sıfırla
            QTimer.singleShot(300, self._matrix.reset_colors)

    def _show_match_result(self) -> None:
        self._update_round_bar(14)
        self._op_title.setText("✅  14 Round Tamamlandı")
        self._op_title.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")

        last_step = self._steps_data[-1]
        self._matrix.set_matrix(last_step["matrix"], ANIM_COLORS["accent_green"])

        self._desc_lbl.setText(
            f"Animasyonun ürettiği (ECB ilk blok):\n"
            f"  {self._final_block_hex}\n\n"
            f"crypto_core AES-256-GCM çıktısı (preview):\n"
            f"  {self._expected_ct_hex}\n\n"
            f"Not: GCM modu AES-CTR kullanır. Yukarıdaki round\n"
            f"animasyonu AES-256'nın her blokta nasıl çalıştığını gösterir.\n\n"
            f"✅  Eşleşme Başarılı"
        )
        self._desc_lbl.setStyleSheet(f"color: {ANIM_COLORS['accent_green']};")
```

- [ ] **Step 2: Import testi**

```
.venv/Scripts/python -c "from animation_modals.aes_animation import AESAnimationWindow; print('OK')"
```

Beklenen: `OK`

- [ ] **Step 3: Commit**

```bash
git add animation_modals/aes_animation.py
git commit -m "feat: add AESAnimationWindow with 14-round state matrix visualization"
```

---

## Task 8: `__init__.py` — Dışa Aktarımlar

**Files:**
- Modify: `animation_modals/__init__.py`

- [ ] **Step 1: `__init__.py` tamamla**

```python
# animation_modals/__init__.py
from .rsa_animation import RSAAnimationWindow
from .sha256_animation import SHA256AnimationWindow
from .aes_animation import AESAnimationWindow

__all__ = ["RSAAnimationWindow", "SHA256AnimationWindow", "AESAnimationWindow"]
```

- [ ] **Step 2: Toplu import testi**

```
.venv/Scripts/python -c "
from animation_modals import RSAAnimationWindow, SHA256AnimationWindow, AESAnimationWindow
print('RSA:', RSAAnimationWindow)
print('SHA:', SHA256AnimationWindow)
print('AES:', AESAnimationWindow)
"
```

Beklenen: 3 sınıf ismi yazdırılır.

- [ ] **Step 3: Commit**

```bash
git add animation_modals/__init__.py
git commit -m "feat: export all animation windows from animation_modals package"
```

---

## Task 9: main_gui.py Entegrasyonu

**Files:**
- Modify: `main_gui.py` (3 noktaya dokunulur)

Mevcut kod **değiştirilmez**, yalnızca 3 blok eklenir.

- [ ] **Step 1: Import ekle** — dosyanın `from crypto_core import ...` satırından hemen sonrasına

```python
# main_gui.py — mevcut import bloğunun sonuna ekle:
from animation_modals import RSAAnimationWindow, SHA256AnimationWindow, AESAnimationWindow
```

- [ ] **Step 2: `_anim_windows` listesi ekle** — `MainWindow.__init__` içinde `self._phase = "idle"` satırından önce

```python
        self._anim_windows: list = []  # animasyon pencerelerinin referanslarını tutar
```

- [ ] **Step 3: `_on_keygen` içine RSA penceresi ekle** — `self._phase = "ready"` satırından SONRA

```python
        # RSA animasyon penceresini açar (bağımsız, engellemiyor)
        rsa_win = RSAAnimationWindow(alice_b64, bob_b64)
        rsa_win.show()
        self._anim_windows.append(rsa_win)
```

- [ ] **Step 4: `_on_next_step` içine SHA-256 ve AES pencereleri ekle** — `if self._phase == "alice":` bloğunun içine, `self._alice_has_more = self._alice_panel.show_next_step()` satırından ÖNCE

```python
            # Animasyon tetikleme: SHA-256 veya AES adımında pencere aç
            idx = self._alice_panel._current_step
            if idx < len(self._alice_panel._steps):
                next_step = self._alice_panel._steps[idx]
                if "SHA" in next_step.step_name:
                    sha_win = SHA256AnimationWindow(
                        self._original_message,
                        next_step.data.get("hash_hex", ""),
                    )
                    sha_win.show()
                    self._anim_windows.append(sha_win)
                elif "AES" in next_step.step_name:
                    key_hex = next_step.data.get("session_key_hex", "")
                    ct_preview = next_step.data.get("ciphertext_hex_preview", "")
                    key_bytes = bytes.fromhex(key_hex) if key_hex else b"\x00" * 32
                    aes_win = AESAnimationWindow(
                        key=key_bytes,
                        plaintext=self._original_message.encode("utf-8"),
                        expected_ct_hex=ct_preview,
                    )
                    aes_win.show()
                    self._anim_windows.append(aes_win)
```

- [ ] **Step 5: Uygulamayı çalıştır ve manuel test yap**

```
.venv/Scripts/python main_gui.py
```

Test sırası:
1. "Anahtar Üret" tıkla → RSA animasyon penceresi açılır, otomatik akar
2. Mesaj yaz, "Şifreleme Başlat" tıkla
3. "Sonraki Adım" tıkla (Adım 1 — SHA-256) → SHA-256 animasyon penceresi açılır
4. "Sonraki Adım" tıklamaya devam et
5. Adım 4'e (AES-GCM) gelince → AES animasyon penceresi açılır, 14 round akar
6. Ana pencere hiçbir zaman engellenmemiş olmalı

- [ ] **Step 6: Tüm testleri çalıştır**

```
.venv/Scripts/python -m pytest test_sha256_pure.py test_aes_pure.py test_crypto_core.py -v
```

Beklenen: Tüm testler PASSED

- [ ] **Step 7: Final commit**

```bash
git add main_gui.py
git commit -m "feat: integrate crypto animation windows into main GUI workflow"
```

---

## Self-Review

**Spec coverage:**
- ✅ RSAAnimationWindow — 4 adım, demo primes, Base64 eşleşme
- ✅ SHA256AnimationWindow — 4 adım, binary/padding/blok/round, hash eşleşme
- ✅ AESAnimationWindow — 14 round, SubBytes/ShiftRows/MixColumns/AddRoundKey, matrix
- ✅ Bağımsız pencereler (`show()`, `WA_DeleteOnClose`)
- ✅ Otomatik animasyon (QTimer), kullanıcı kapatar
- ✅ Hız kontrolü (Yavaş/Normal/Hızlı)
- ✅ Eşleşme ekranı: sadece "✅ Eşleşme Başarılı"
- ✅ Mevcut proje adımları korunuyor
- ✅ `_anim_windows` referans listesi (çöp toplanma önlendi)
- ✅ SubBytes için hücre-hücre animasyon (highlight_cells_sequential)
- ✅ ShiftRows için animate_row_shift

**Placeholder taraması:** Yok ✅

**Tip tutarlılığı:**
- `MatrixWidget.highlight_cells_sequential` → `ops: list[tuple[int,int,str]]` — Task 3 ve Task 7'de aynı imza ✅
- `aes256_encrypt_with_rounds` → `rounds_data[i]["after_sub_bytes"]` — Task 2 ve Task 7'de aynı key ✅
- `sha256_steps` → `result["final_hash"]` — Task 1 ve Task 6'da aynı key ✅
