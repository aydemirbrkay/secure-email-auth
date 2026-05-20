# animation_modals/aes_pure.py
"""
Saf Python AES-256 ECB implementasyonu.
Animasyon için 14 round'un tüm ara state matrislerini döndürür.
NIST FIPS-197 test vektörleri ile doğrulanmıştır.
"""
from __future__ import annotations

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

RCON: list[int] = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40]


def _xtime(a: int) -> int:
    return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else (a << 1) & 0xff


def _mix_col(col: list[int]) -> list[int]:
    s0, s1, s2, s3 = col
    return [
        _xtime(s0) ^ _xtime(s1) ^ s1 ^ s2 ^ s3,
        s0 ^ _xtime(s1) ^ _xtime(s2) ^ s2 ^ s3,
        s0 ^ s1 ^ _xtime(s2) ^ _xtime(s3) ^ s3,
        _xtime(s0) ^ s0 ^ s1 ^ s2 ^ _xtime(s3),
    ]


def _bytes_to_state(block: bytes) -> list[list[int]]:
    return [[block[r + 4 * c] for c in range(4)] for r in range(4)]


def _state_to_hex(state: list[list[int]]) -> list[list[str]]:
    return [[f"{state[r][c]:02x}" for c in range(4)] for r in range(4)]


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


def _add_round_key(state: list[list[int]], rk: list[list[int]]) -> list[list[int]]:
    return [[state[r][c] ^ rk[r][c] for c in range(4)] for r in range(4)]


def _key_expansion(key: bytes) -> list[list[list[int]]]:
    Nk = 8
    Nr = 14
    w: list[list[int]] = []
    for i in range(Nk):
        w.append(list(key[4 * i: 4 * i + 4]))

    for i in range(Nk, 4 * (Nr + 1)):
        temp = w[i - 1][:]
        if i % Nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [SBOX[b] for b in temp]
            temp[0] ^= RCON[i // Nk]
        elif i % Nk == 4:
            temp = [SBOX[b] for b in temp]
        w.append([a ^ b for a, b in zip(w[i - Nk], temp)])

    round_keys: list[list[list[int]]] = []
    for rnd in range(Nr + 1):
        cols = [w[rnd * 4 + c] for c in range(4)]
        mat = [[cols[c][r] for c in range(4)] for r in range(4)]
        round_keys.append(mat)
    return round_keys


def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    """PKCS#7 padding: padding miktarı = block_size - (len(data) % block_size).
    Tam blok durumunda bir tam blok padding (16 × 0x10) eklenir."""
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)


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
    block = (plaintext + bytes(16))[:16]

    round_keys = _key_expansion(key)
    state = _bytes_to_state(block)
    rounds_data: list[dict] = []

    state = _add_round_key(state, round_keys[0])
    rounds_data.append({"round": 0, "after_add_round_key": _state_to_hex(state)})

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

    after_sub = _sub_bytes(state)
    after_shift = _shift_rows(after_sub)
    state = _add_round_key(after_shift, round_keys[14])
    rounds_data.append({
        "round": 14,
        "after_sub_bytes": _state_to_hex(after_sub),
        "after_shift_rows": _state_to_hex(after_shift),
        "after_add_round_key": _state_to_hex(state),
    })

    final_bytes = bytes(state[r][c] for c in range(4) for r in range(4))

    # Round flow görünümü için: tüm round_key'ler ve ilk state matrisi
    round_keys_hex = [_state_to_hex(rk) for rk in round_keys]
    initial_state_hex = _state_to_hex(_bytes_to_state(block))

    # Plaintext Hazırlığı sayfası için yeni alanlar
    padded = _pkcs7_pad(plaintext, 16)
    first_block = padded[:16]
    blocks_total = len(padded) // 16
    state_matrix = [
        [f"{first_block[c * 4 + r]:02x}" for c in range(4)]
        for r in range(4)
    ]

    return {
        "rounds_data": rounds_data,
        "final_block_hex": final_bytes.hex(),
        "round_keys_hex": round_keys_hex,
        "initial_state_hex": initial_state_hex,
        # Plaintext Hazırlığı (yeni)
        "plaintext_bytes": bytes(plaintext),
        "plaintext_text": plaintext.decode("utf-8", errors="replace"),
        "padded_plaintext": padded,
        "first_block": first_block,
        "blocks_total": blocks_total,
        "state_matrix": state_matrix,
    }
