# AES State Matrix — Byte-Hareket Animasyonu ve Before/After Karşılaştırma

**Tarih:** 2026-05-12
**Hedef dosyalar:**
- Yeni: `animation_modals/aes_matrix_view.py`
- Modify: `animation_modals/aes_animation.py`

**İlgili tasarım dokümanları:** [docs/specs/2026-05-10-kripto-animasyonlari-redesign-design.md](2026-05-10-kripto-animasyonlari-redesign-design.md)

## Motivasyon

Kullanıcı testinde dört ana eksiklik raporlandı (özet):

1. AES State Matrix kullanıcıya **statik bir snapshot** gibi geliyor — operasyonlar arasında baytların *nasıl* hareket ettiği görünmüyor.
2. ShiftRows sırasında "33 cb a0 35" baytlarının alt satır baytlarıyla *yer değişimi* sadece nihai sonuçtan anlaşılabiliyor; ara dönüşüm görünmüyor.
3. "Önceki" durumla "şimdiki" durumu aynı ekranda **doğrudan karşılaştırma** imkânı yok; sağ panel ÖNCEKİ→SONRAKI veriyor ama state matrisinin kendisinde bu karşılaştırma yok.
4. Hangi satır/sütunun aktif olduğu animasyon sırasında belirgin değil.

Bu spec, AES animasyon penceresinde state matrisinin tamamen yeniden tasarımını kapsar:
- QPainter tabanlı yeni matris widget'ı, byte sprite hareketleri, oklar
- Yan yana **iki** matris (Önceki / Şimdiki) — anlık karşılaştırma
- Operasyon başına **koreografi**: SubBytes, ShiftRows, MixColumns, AddRoundKey için tek tek tasarlanmış sahneler

## Kapsam

**İçinde:**

- Yeni `_AESMatrixView` (QPainter) ve `_AESStateCompareWidget` (yan-yana kapsayıcı) widget'ları
- AES penceresi yerleşim güncellemesi: mevcut `self._matrix = MatrixWidget(...)` → `self._matrix_pair = _AESStateCompareWidget(...)`
- 4 operasyon için tam animasyon koreografisi
- "⟲ Yeniden Oynat" butonu (aktif operasyonu baştan oynatır)
- Round bar'dan başka bir round'a geçildiğinde animasyonun temizlenip yeniden başlaması

**Dışında:**

- SHA-256 ve RSA animasyonları — bu turda dokunulmuyor. Kullanıcı *"sadece AES"* dedi.
- `MatrixWidget` kaldırılmıyor; modülde geriye dönük uyumluluk için kalır (test smoke'u referansı korur).
- Sağ paneldeki `_SubBytesAnimWidget`, `_ShiftRowsAnimWidget`, `_MixColumnsAnimWidget`, `_AddRoundKeyAnimWidget` widget'larına dokunulmuyor — bunlar matematik formüllerinin detaylı anlatımı olarak korunur. State matrisi onların "büyük resmini" sunar.
- Tüm AES akışını (R0..R14) tek seferde gösteren "Tüm Akış" sayfası bu spec dışı; orada animasyon yok.
- Otomatik oynatma / hız kayd ırıcısı / duraklatma — şimdilik yok (kullanıcı kararı).

## Kısıtlar

- PyQt6, mevcut `CryptoAnimationWindow` ve `ANIM_COLORS` paleti kullanılır.
- Yeni dış bağımlılık eklenmez.
- Mevcut `manual_mode=True` davranışı (◀ / ▶ ile round geçişi) korunur.
- `aes_pure.py`'nin döndürdüğü `steps_data` formatı olduğu gibi tüketilir.
- Türkçe arayüz dili korunur.

## Mimari Genel Bakış

```
animation_modals/
├── matrix_widget.py            (KORUNUR — AES kullanmaz olur, SHA için kalır)
├── aes_matrix_view.py          (YENİ)
│   ├── _AESMatrixView          ← Tek matris, QPainter, animasyon motoru
│   └── _AESStateCompareWidget  ← İki _AESMatrixView yan yana + Yeniden Oynat
└── aes_animation.py
    └── AESAnimationWindow._make_round_page  ← _matrix_pair ile değiştirilir
```

## Bileşen 1 — `_AESMatrixView` (Tek Matris)

QPainter ile çizilen 4×4 state matrisi. İki ana mod: **statik** (donmuş) ve **animasyonlu**.

### Public API

```python
class _AESMatrixView(QWidget):
    def __init__(
        self,
        *,
        label_title: str = "",        # üst başlık (ör. "Önceki", "Şimdiki")
        label_color: str = ANIM_COLORS["text_secondary"],
        parent: QWidget | None = None,
    ) -> None: ...

    # Donmuş matris atama — animasyonsuz
    def set_state(self, matrix: list[list[str]]) -> None: ...

    # Operasyon animasyonunu oynat
    def play_animation(
        self,
        operation: str,                          # "SubBytes" | "ShiftRows" | "MixColumns" | "AddRoundKey"
        before: list[list[str]],
        after: list[list[str]],
        *,
        round_key: list[list[str]] | None = None,    # AddRoundKey için
        on_done: Callable[[], None] | None = None,
    ) -> None: ...

    # En son play_animation çağrısını baştan oyna
    def replay(self) -> None: ...

    # Animasyonu durdur (round bar değiştiğinde)
    def stop_animation(self) -> None: ...
```

### Çizim Katmanları (z-order)

1. **Grid + etiketler**: 4×4 hücre çerçeveleri, r0..r3 (sol) ve c0..c3 (üst) etiketleri. Hep çizilir.
2. **Hücre içeriği**: arka plan rengi + 2-haneli hex değer. Animasyon sırasında değer veya renk değişebilir.
3. **Overlay** (sadece animasyon süresince):
   - Hareket eden bayt sprite'ları (eski → yeni pozisyon arası lerp)
   - Oklar (kaynak hücreden hedef hücreye)
   - Vurgu çerçevesi (aktif satır/sütun/hücre, 2 px parlak)
   - Sembol balonları (XOR ⊕, S-Box →, ⊕round_key)

### Boyut ve Yerleşim

- Hücre boyutu: 56 × 44 px
- Hücre boşluğu (gap): 4 px
- Etiket alanı: sol 18 px (r etiketleri), üst 16 px (c etiketleri)
- Toplam matris boyutu: ~260 × 200 px

### Faz Makinesi

`_animation_timer` (QTimer) ~40 ms aralıkla tick atar (25 fps). `_tick` instance değişkeni geçen tick sayısını sayar. Her operasyon kendi `_total_ticks` ve `_draw_overlay(tick)` fonksiyonunu tanımlar.

`play_animation`:
1. `_op`, `_before`, `_after`, `_round_key`, `_on_done` instance'a kaydedilir
2. `_tick = 0`, `_total_ticks = _TOTAL_TICKS_BY_OP[op]`
3. `_animation_timer.start(40)`
4. Her tick'te `_tick += 1`; `_tick >= _total_ticks` ise timer durur ve `_on_done()` çağrılır
5. `paintEvent` çizim katmanlarını sırayla çağırır; overlay sadece `0 < _tick < _total_ticks` aralığında çizilir

`stop_animation()`: timer'ı durdurur, `_tick = _total_ticks` yapar (overlay söner, son after state kalır).

`replay()`: aynı `(op, before, after, round_key)` parametreleriyle `play_animation`'ı yeniden çağırır.

## Bileşen 2 — Per-Operasyon Koreografisi

Her koreografi `_draw_overlay_<op>(painter, tick)` metodu olarak ayrı tanımlanır.

### AddRoundKey — `_TICKS = 60` (~2.4 s)

| Tick aralığı | Faz | İçerik |
|---|---|---|
| 0–15 | KEY_REVEAL | `round_key` 4×4 grid sağdan kayarak gelir (overlay olarak, matrisin sağ tarafına yerleşir). |
| 16–55 | XOR_PER_ROW | 4 satır × 10 tick: her satırda 4 hücreye ⊕ sembolü belirir, ardından sonuç değeri (`before[r][c] ^ rk[r][c]`) hücreye yerleşir, hücre yeşil pulse. |
| 56–59 | FADEOUT | round_key overlay'i fade-out olur, matris final after state'inde kalır. |

### SubBytes — `_TICKS = 64` (~2.6 s)

Her hücre row-major sırayla işlenir, 4 tick/hücre:

| Tick (her hücre) | İçerik |
|---|---|
| 0 | Hücre çerçevesi mavi parlar (aktif vurgu) |
| 1 | Hücrenin üstüne küçük balon: `S[xy]=zz` (S-Box indeksi) |
| 2 | Hücre değeri eski → yeni dönüşür (color flash: turuncu → yeşil) |
| 3 | Balon söner, hücre vurgusu söner |

### ShiftRows — `_TICKS = 80` (~3.2 s)

| Tick aralığı | İçerik |
|---|---|
| 0–9 | Satır 0 vurgulanır, "sabit" etiketi belirir, 5 tick sonra söner |
| 10–29 | Satır 1: 1 bayt sola kayma animasyonu (sprite hareketi + wrap iz) |
| 30–49 | Satır 2: 2 bayt sola kayma |
| 50–69 | Satır 3: 3 bayt sola kayma |
| 70–79 | Final after state, vurgu söner |

**Bir satırın kayma animasyonu (K bayt):**
- İlk yarı (10 tick): K bayt sol kenardan sola doğru kayar ve şeffaflaşır (alpha 1.0 → 0.0)
- Aynı zamanda sağ kenara K şeffaf sprite gelir (alpha 0.0 → 1.0); bunlar "wrap around" göstergesi
- Diğer (4-K) bayt K hücre kadar düz sola kayar
- İkinci yarı (10 tick): tüm baytlar yeni pozisyonlarında oturur, alpha 1.0

### MixColumns — `_TICKS = 80` (~3.2 s)

4 sütun sırayla, 20 tick/sütun:

| Tick (her sütun) | İçerik |
|---|---|
| 0–4 | Sütun vurgusu (4 hücre çerçevesi sütun rengi) |
| 5–14 | Sütun yanında küçük formül balonu belirir: `2·a₀ ⊕ 3·a₁ ⊕ a₂ ⊕ a₃` (sütunun 4 yeni baytı için 4 formül, tek tek) |
| 15–19 | Yeni byte hücreye yerleşir (color flash), balon söner |

## Bileşen 3 — `_AESStateCompareWidget`

Yan yana iki `_AESMatrixView` + üst kontroller.

```
┌──────────────────────────────────────────────────────────────┐
│  Round 1 — ShiftRows                       [⟲ Yeniden Oynat] │
├──────────────────────────────────────────────────────────────┤
│   ┌── ÖNCEKİ ──┐                ┌── ŞİMDİKİ (canlı) ──┐      │
│   │  matrix    │   →ShiftRows→  │  matrix              │      │
│   │  (donmuş)  │                │  (animasyonlu)       │      │
│   └────────────┘                └──────────────────────┘      │
│                                                              │
│                  İşlem bağlam alt yazısı                     │
└──────────────────────────────────────────────────────────────┘
```

### Public API

```python
class _AESStateCompareWidget(QWidget):
    def __init__(self, parent=None) -> None: ...

    def start_step(
        self,
        operation: str,
        before: list[list[str]],
        after: list[list[str]],
        op_color: str,
        *,
        round_key: list[list[str]] | None = None,
    ) -> None:
        """
        Önceki matrisi 'before' ile donmuş şekilde set_state'le.
        Şimdiki matrise play_animation(op, before, after, ...) gönder.
        Üst başlık ve ortadaki ok rengini op_color ile güncelle.
        """

    def show_final(self, final_state: list[list[str]]) -> None:
        """
        Round 14 sonrası final ciphertext gösterimi —
        her iki matris de final_state'e set edilir, animasyon yok.
        """
```

### Yerleşim Detayları

- QHBoxLayout: önceki matris + ok + şimdiki matris
- Ok: orta sütunda küçük QLabel — "→ ShiftRows →" formatında, font 11pt bold, op rengi
- Üst başlık: "Round N — Operasyon" — mevcut `_op_title`'ı dışarıdan kontrol ediyor
- Yeniden Oynat butonu: sağ üst köşede, sadece şimdiki matrisin `replay()` metodunu çağırır

## Bileşen 4 — AES Penceresi Entegrasyonu

### Mevcut yerleşim (`aes_animation.py:1467-1481`)

```python
mat_frame = QFrame()
...
self._matrix = MatrixWidget(parent=self, show_labels=True)
mat_lay.addWidget(self._matrix, ...)
```

### Yeni yerleşim

```python
self._matrix_pair = _AESStateCompareWidget(parent=self)
mat_lay.addWidget(self._matrix_pair, ...)
```

`mat_title`, `mat_lbl`, `_matrix_context` etiketleri `_AESStateCompareWidget` içinde yaşar (kapsayıcının üst kısmı). Mevcut `mat_frame` korunur ama içeriği değişir.

### `_render_step` değişiklikleri (`aes_animation.py:1684-1750`)

Mevcut akış:
```python
op = step["operation"]
before = self._steps_data[step_idx - 1]["matrix"] if step_idx > 0 else step["matrix"]
after = step["matrix"]

if op == "SubBytes":
    self._matrix.highlight_cells_sequential(...)
elif op == "ShiftRows":
    for row_idx, shift in enumerate(...): self._matrix.animate_row_shift(...)
    QTimer.singleShot(900, self._matrix.reset_colors)
elif op == "MixColumns":
    for col in range(4): self._matrix.update_cell(..., col_colors[col])
else:  # AddRoundKey
    self._matrix.set_matrix(after, step["color"])
    QTimer.singleShot(250, self._matrix.reset_colors)
```

Tek satıra inecek:
```python
rnd = step["round"]
rk = self._round_keys_hex[rnd] if op == "AddRoundKey" and rnd < len(self._round_keys_hex) else None
self._matrix_pair.start_step(op, before, after, step["color"], round_key=rk)
```

`_show_match_result` (round 14 sonrası):
```python
self._matrix_pair.show_final(self._steps_data[-1]["matrix"])
```

`_matrix_context` etiketi kaldırılır (artık `_AESStateCompareWidget` üst kısmında işlem-bağlam mesajı var; tek satıra inecek).

## Veri Akışı

`aes_pure.aes256_encrypt_with_rounds(key, plaintext)` çıktısı:
- `rounds_data[step_idx]["matrix"]` — bu step sonundaki state
- `rounds_data[step_idx]["operation"]` — "AddRoundKey" | "SubBytes" | "ShiftRows" | "MixColumns"
- `rounds_data[step_idx]["round"]` — 0..14
- `round_keys_hex[rnd]` — round_key matrisi (AddRoundKey için)

Yeni widget tükettiği alanlar:
- `before` ve `after` — 4×4 hex string listesi
- `round_key` — yalnızca AddRoundKey için, 4×4 hex string listesi
- `operation` — string, koreografi seçimi için
- `op_color` — operasyon teması, başlık ve ok rengi için

Yeni dış veri yapısı tanımlanmıyor; mevcut `steps_data` formatı yeterli.

## Hata Durumları

- **`round_key` AddRoundKey'de None gelirse:** uyarı log + animasyonsuz `set_state(after)` ile fallback. `_round_keys_hex` listesinin uzunluğu < 15 ise mevcut kod zaten None döndürüyor; widget bu durumda animasyonu atlar.
- **`before` ve `after` matris formatı bozuksa** (4×4 değil): widget construct sırasında değil, ilk `play_animation` çağrısında `ValueError` fırlatır.
- **Round bar'dan başka round'a geçilirse:** `start_step` çağrılmadan önce şimdiki matrisin `stop_animation()` çağrılır; eski animasyon temizlenir.

## Test ve Doğrulama Planı

### Otomatize edilebilir

- `_AESMatrixView.set_state` çağrısı sonrası `_state` instance değişkeninin doğru atandığı (birim testi)
- `play_animation` çağrısı sonrası `_op`, `_total_ticks`, timer aktif mi (birim testi)
- `stop_animation` sonrası timer durmuş mu, `_tick == _total_ticks` mı (birim testi)
- `replay()` aynı parametreleri yeniden geçerli mi (birim testi)
- Tamamlama callback'i `on_done` `_total_ticks` tick'inden sonra çağrılır mı (birim testi, QTimer.singleShot ile sahte tick'ler)

### Manuel (görsel)

Python 3.11 ortamında uygulamayı açıp:

1. AES animasyonunu başlat (Alice paneli)
2. Round 0 (AddRoundKey) — round_key sağdan kayarak gelmeli, 16 hücreye sırayla ⊕ sembolü ve sonuç görünmeli
3. Round 1 ▶ — SubBytes: 16 hücre row-major sırayla S-Box dönüşümü göstermeli
4. Round 1 ▶ — ShiftRows: r0 sabit, r1 1 bayt sola, r2 2 bayt sola, r3 3 bayt sola hareket etmeli; wrap baytları sağ kenardan şeffaf sprite olarak gelmeli
5. Round 1 ▶ — MixColumns: 4 sütun sırayla, her sütunda formül balonu ve sonuç byte yerleşimi görünmeli
6. Round 1 ▶ — AddRoundKey: round_key görünmeli, 16 hücre XOR ile güncellenmeli
7. ⟲ Yeniden Oynat butonu — son operasyonu baştan oynatmalı
8. Round bar'dan R5'e atla — önceki animasyon temizlenip yeni round başlamalı, "Önceki" matris R4'ün son state'i, "Şimdiki" matris R5 operasyonunu oynatmalı

### Regresyon kontrolü

- AES "Tüm Akış" sayfası açılmalı, mevcut görünüm değişmemiş olmalı
- SHA-256 ve RSA animasyonları açılmalı, hiçbir değişiklik olmamalı
- Tüm mevcut 132 test PASS kalmalı (smoke + birim testler)

## Açık Sorular

Yok — tüm temel kararlar brainstorming aşamasında alındı:
- Kapsam: sadece AES
- Teknoloji: QPainter
- Yerleşim: yan yana iki matris
- ShiftRows hareket stili: düz kayma + wrap şeffaf iz
- Kontrol: sadece Yeniden Oynat

## Sonraki Adım

Bu spec onaylandıktan sonra `superpowers:writing-plans` skill'i ile uygulama planı yazılacak. Plan, bileşenleri bağımsız ele alacak (her biri kendi commit'i ile uygulanabilir):

1. `_AESMatrixView` iskeleti — grid çizimi, set_state, statik mod
2. `_AESStateCompareWidget` kapsayıcısı — yan yana iki view, yeniden oynat butonu
3. AES penceresi entegrasyonu — mat_frame'i değiştir, `_render_step` indirgeme
4. AddRoundKey koreografisi
5. SubBytes koreografisi
6. ShiftRows koreografisi (en karmaşık — sprite hareketi + wrap)
7. MixColumns koreografisi
8. Test'ler ve manuel görsel doğrulama
