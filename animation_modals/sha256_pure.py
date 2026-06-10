# animation_modals/sha256_pure.py
"""
Saf Python SHA-256 implementasyonu.
Animasyon için ara round state verilerini döndürür.
Final hash, hashlib.sha256() ile birebir aynıdır.

EĞİTİM AMAÇLIDIR — manuel round uygulaması gerçek güvenlik kodunda
KULLANILMAMALIDIR; üretim akışı standart hashlib.sha256() kullanır.
"""
from __future__ import annotations
import struct

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
      round_snapshots : her blok için 9 snapshot — round
                        1, 9, 17, 25, 33, 41, 49, 57 ve 64'teki
                        A-H register değerleri ve ara terimler
                        (W, K, T1, T2)
      w_expansion     : ilk blok için W[16..31] tablosu — her satırda
                        operand (W[i-15], W[i-2]) ve σ0/σ1 sonuçları
                        ayrı alanlar olarak döner
      final_hash      : 64 karakterlik hex özet (hashlib ile aynı)
      pre_final_h     : son bloğun eklenmesinden önceki H[0..7]
      final_working   : son bloğun çalışma değişkenleri (A..H)
      final_h_parts   : final H[0..7] (hex string listesi)
    """
    msg_len_bits = len(message) * 8
    padded = bytearray(message)
    padded.append(0x80)
    while len(padded) % 64 != 56:
        padded.append(0x00)
    padded += struct.pack(">Q", msg_len_bits)

    preview_bytes = bytes(padded[:8])
    binary_preview = " ".join(f"{b:08b}" for b in preview_bytes)

    blocks = [bytes(padded[i:i + 64]) for i in range(0, len(padded), 64)]

    h = list(H0)
    round_snapshots: list[dict] = []

    w_expansion_sample: list[dict] | None = None

    for block in blocks:
        w = list(struct.unpack(">16I", block))
        for i in range(16, 64):
            s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
            s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
            w.append((w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF)

        if w_expansion_sample is None:  # ilk blok, henüz snapshot yok
            w_expansion_sample = []
            for i in range(16, 32):
                s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
                s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
                w_expansion_sample.append({
                    "i": i,
                    "w_i16": f"{w[i-16]:08x}",
                    "w_i15": f"{w[i-15]:08x}",   # σ0 için operand
                    "s0": f"{s0:08x}",           # σ0(W[i-15]) sonucu
                    "w_i7": f"{w[i-7]:08x}",
                    "w_i2": f"{w[i-2]:08x}",     # σ1 için operand
                    "s1": f"{s1:08x}",           # σ1(W[i-2]) sonucu
                    "result": f"{w[i]:08x}",
                })

        a, b, c, d, e, f, g, hh = h

        for i in range(64):  # 64 sıkıştırma round'u (FIPS 180-4 §6.2.2)
            s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
            ch = ((e & f) ^ (~e & g)) & 0xFFFFFFFF
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

            # i değerleri 0,8,16,...,56 ve 63 → round numaraları
            # 1, 9, 17, 25, 33, 41, 49, 57, 64 (toplam 9 snapshot)
            if i % 8 == 0 or i == 63:
                round_snapshots.append({
                    "round": i + 1,
                    "a": f"{a:08x}",
                    "e": f"{e:08x}",
                    "registers": [f"{v:08x}" for v in [a, b, c, d, e, f, g, hh]],
                    "w": f"{w[i]:08x}",
                    "k": f"{K[i]:08x}",
                    "t1": f"{temp1:08x}",
                    "t2": f"{temp2:08x}",
                })

        h_before = list(h)  # son bloğun eklenmesinden önceki H değerleri
        last_working = [a, b, c, d, e, f, g, hh]  # son bloğun çalışma değişkenleri
        h = [(x + y) & 0xFFFFFFFF for x, y in zip(h, last_working)]

    final_hash = "".join(f"{v:08x}" for v in h)

    return {
        "binary_preview": binary_preview,
        "padded_len": len(padded),
        "blocks_count": len(blocks),
        "initial_h": [f"{v:08x}" for v in H0],
        "round_snapshots": round_snapshots,
        "w_expansion": w_expansion_sample,
        "final_hash": final_hash,
        # Son blok toplama adımı için
        "pre_final_h":      [f"{v:08x}" for v in h_before],
        "final_working":    [f"{v:08x}" for v in last_working],
        "final_h_parts":    [f"{v:08x}" for v in h],
        # Mesaj Hazırlığı sayfası için (yeni alanlar)
        "message_bytes":    bytes(message),
        "message_text":     message.decode("utf-8", errors="replace"),
        "padded_bytes":     bytes(padded),
    }
