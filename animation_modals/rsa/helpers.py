# animation_modals/rsa/helpers.py
"""RSA demo paylaşılan yardımcıları ve modül-seviyesi cari demo durumu.

_reseed_demo() bu modülün global'lerini yeniden bağlar; widget'lar bu
değerlere helpers.<ad> ile erişerek her demo açılışında güncel (p,q,n,...)
değerleri görür.
"""
from __future__ import annotations
import base64
import random
from math import gcd

# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def _der_int(v: int) -> bytes:
    """Bir tam sayıyı DER INTEGER olarak kodlar."""
    b = v.to_bytes((v.bit_length() + 8) // 8, "big")
    if b[0] >= 0x80:
        b = b"\x00" + b
    return bytes([0x02, len(b)]) + b


def _eea_steps(a: int, b: int) -> list[tuple[int, int, int, int, int]]:
    """
    Genişletilmiş Öklid: a·s + b·t = gcd(a, b)
    Returns: list of (i, q_i, r_i, s_i, t_i)
    """
    r0, r1 = a, b
    s0, s1 = 1, 0
    t0, t1 = 0, 1
    rows = [(0, 0, r0, s0, t0), (1, 0, r1, s1, t1)]
    i = 2
    while r1 != 0:
        q = r0 // r1
        r0, r1 = r1, r0 - q * r1
        s0, s1 = s1, s0 - q * s1
        t0, t1 = t1, t0 - q * t1
        rows.append((i, q, r1, s1, t1))
        i += 1
    return rows


# ---------------------------------------------------------------------------
# Tez değerleri — tab:RSAExample ile birebir uyumlu (chapter1.tex)
# Tüm widget'lar bu sabitleri __init__'lerinde okur.
# ---------------------------------------------------------------------------

# Asal havuzu — RSAAnimationWindow her açıldığında bu havuzdan rastgele
# iki asal seçer (kullanıcı her demo'da farklı sayılar görür, eğitsel
# çeşitlilik). Tezdeki textbook örneği (p=61, q=53) bu havuzun bir alt
# kümesidir; rastgele seçim onu da içerir.
_PRIME_POOL: list[int] = [
    n for n in range(11, 100)
    if all(n % d for d in range(2, int(n ** 0.5) + 1))
]

# Modül seviyesi cari demo değerleri. Başlangıç değerleri tezdeki örnek;
# RSAAnimationWindow oluşturulurken _reseed_demo() bunları değiştirir.
_P:   int = 61
_Q:   int = 53
_N:   int = _P * _Q
_PHI: int = (_P - 1) * (_Q - 1)
_E:   int = 17
_D:   int = pow(_E, -1, _PHI)
# Şifrelenecek örnek mesaj. Eskiden sabit (65) idi; anahtarlar her açılışta
# değiştiği halde m sabit kaldığı için c/m' "hep aynı" görünüyordu. Artık
# _reseed_demo() m'yi de 2 ≤ m < n ve gcd(m,n)=1 koşuluyla rastgele seçer;
# böylece m → c → m' döngüsü her demo'da farklı sayılarla gözlemlenir.
_M:   int = 65

# Tam sayıyı Unicode üst-simgeye çevir (RSA formüllerinde m^e yerine mᵉ için)
_SUP_TRANS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

def _to_sup(n: int | str) -> str:
    return str(n).translate(_SUP_TRANS)

_DER_N:   bytes = _der_int(_N)
_DER_E:   bytes = _der_int(_E)
_DER_SEQ: bytes = bytes([0x30, len(_DER_N) + len(_DER_E)]) + _DER_N + _DER_E
_B64_DEMO: str  = base64.b64encode(_DER_SEQ).decode()


# Otomatik/elle her iki seçimde de geçerli açık üs e'nin aranacağı yaygın
# küçük adaylar. e: küçük ve gcd(e, ϕ) = 1 koşulunu sağlayan ilk değer.
_E_CANDIDATES: tuple[int, ...] = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def _recompute_from_pq(p: int, q: int, min_n: int = 143) -> bool:
    """Verilen (p, q) çiftinden tüm RSA demo global'lerini (n, ϕ, e, d, m,
    DER, b64) yeniden hesaplar ve bağlar.

    Hem `_reseed_demo` (rastgele çift) hem `_apply_custom_pq` (kullanıcı çifti)
    bu çekirdeği kullanır → seçim kuralları tek yerde tutulur.

    Geçerlilik koşulları:
      - n = p × q ≥ min_n
      - e: `_E_CANDIDATES` içinden gcd(e, ϕ) = 1 ve e < ϕ sağlayan ilk değer
      - d = e⁻¹ mod ϕ, (e × d) mod ϕ == 1 invariantı
      - m: 2 ≤ m < n, gcd(m, n) = 1 (RSA'nın bire-bir olması için)

    Başarılıysa global'leri set edip True; koşullardan biri sağlanmazsa
    global'lere DOKUNMADAN False döner.
    """
    global _P, _Q, _N, _PHI, _E, _D, _M
    global _DER_N, _DER_E, _DER_SEQ, _B64_DEMO

    n = p * q
    if n < min_n:
        return False
    phi = (p - 1) * (q - 1)
    e = next(
        (cand for cand in _E_CANDIDATES if cand < phi and gcd(cand, phi) == 1),
        None,
    )
    if e is None:
        return False
    try:
        d = pow(e, -1, phi)
    except ValueError:
        return False
    if (e * d) % phi != 1:
        return False

    # Mesaj m: n ile aralarında asal, 2 ≤ m < n. gcd=1 koşulu RSA'nın
    # doğru çalışması için gerekir (m, p veya q'nun katı olmamalı).
    m = random.randrange(2, n)
    while gcd(m, n) != 1:
        m = random.randrange(2, n)

    _P, _Q = p, q
    _N = n
    _PHI = phi
    _E = e
    _D = d
    _M = m
    _DER_N = _der_int(_N)
    _DER_E = _der_int(_E)
    _DER_SEQ = bytes([0x30, len(_DER_N) + len(_DER_E)]) + _DER_N + _DER_E
    _B64_DEMO = base64.b64encode(_DER_SEQ).decode()
    return True


def _reseed_demo() -> None:
    """Modül seviyesindeki RSA demo değerlerini rastgele bir küçük asal
    çiftiyle yeniden hesaplar. RSAAnimationWindow her açıldığında çağrılır,
    böylece kullanıcı her seferinde farklı (p, q, n, ϕ, e, d) görür.

    Seçim kuralları `_recompute_from_pq` içindedir; p, q ∈ _PRIME_POOL
    (11..97 asalları), p ≠ q olacak şekilde geçerli bir çift bulunana dek
    rastgele denenir.
    """
    while True:
        p, q = random.sample(_PRIME_POOL, 2)
        if _recompute_from_pq(p, q):
            break


def _apply_custom_pq(p: int, q: int) -> str | None:
    """Kullanıcının elle seçtiği (p, q) çiftini doğrular ve uygular.

    Otomatik moddaki kurallar aynen geçerlidir (n ≥ 143, geçerli e/d/m).
    Başarılıysa None; aksi halde kullanıcıya gösterilecek Türkçe hata mesajı
    döndürür. Hata durumunda global'ler değişmez (eski geçerli demo korunur).
    """
    if p == q:
        return "p ve q farklı asallar olmalı."
    if p not in _PRIME_POOL or q not in _PRIME_POOL:
        return "Yalnız 11–97 arası asallar seçilebilir."
    if _recompute_from_pq(p, q):
        return None
    return "Bu asallar geçerli bir RSA örneği üretmiyor; başka bir çift seçin."


def _generate_demo_b64(seed_int: int) -> str:
    """Eğitim amaçlı, (p,q,n,e) seed'ine bağlı deterministik fakat gerçekçi
    görünümlü bir RSA-2048 public key b64'ü üretir. Her demo açılışında
    farklı bir string oluşturur ki kullanıcı 'RSA üretimi rastgele' kavramını
    Alice'in panel anahtarında somut gözlemleyebilsin.

    Üretim: deterministik PRNG'den 256 byte rastgele veri → base64 → ilk 60
    karakter + '…'. Gerçek RSA-2048 üretiminden çok daha hızlıdır
    (microsaniye), eğitim amaçlı sahte b64 olarak yeterli.
    """
    rnd = random.Random(seed_int)
    raw = bytes(rnd.randrange(256) for _ in range(256))
    b64 = base64.b64encode(raw).decode()
    return b64[:60] + "…"
