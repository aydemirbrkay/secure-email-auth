# Tasarım: main_gui.py Parçalama Refaktörü

**Tarih:** 2026-04-06  
**Proje:** Secure Email Authentication and Message Integrity  
**Yazar:** Berkay Aydemir

---

## Amaç

`main_gui.py` (1220 satır) içinde iç içe geçmiş 4 farklı sorumluluğu ayrı dosyalara taşımak. Mantık, isimlendirme veya davranış değiştirilmez — sadece kod taşıma.

---

## Hedef Dosya Yapısı

```
bitirme_odevi/
├── main_gui.py          # MainWindow + main()             ~270 satır
├── theme.py             # Stil sabitleri                  ~80 satır
├── utils.py             # Yardımcı fonksiyonlar           ~55 satır
├── alice_panel.py       # AlicePanel widget sınıfı        ~115 satır
├── bob_panel.py         # BobPanel widget sınıfı          ~140 satır
├── toast.py             # VerificationToast widget        ~110 satır
├── crypto_core.py       # Değişmez
└── animation_modals/    # Değişmez
```

---

## Her Dosyanın Sorumluluğu

### `theme.py`
- `COLORS` sözlüğü (renk paleti)
- `GLOBAL_STYLESHEET` (uygulama geneli QSS)
- `STEP_COLORS_ALICE` listesi
- `STEP_COLORS_BOB` listesi

### `utils.py`
- `FRIENDLY_NAMES` sözlüğü (teknik terimlerin Türkçe karşılıkları)
- `_make_step_box(title, content, border_color) -> QGroupBox`
- `_truncate_hex(hex_str, max_len) -> str`
- `_build_step_content(step: StepResult) -> str`

### `alice_panel.py`
- `AlicePanel(QWidget)` sınıfı — gönderici (Alice) sol panel

### `bob_panel.py`
- `BobPanel(QWidget)` sınıfı — alıcı (Bob) sağ panel

### `toast.py`
- `VerificationToast(QWidget)` sınıfı — doğrulama bildirimi

### `main_gui.py` (sadeleştirilmiş)
- `MainWindow(QMainWindow)` sınıfı
- `main()` giriş noktası

---

## Import Zinciri

```
theme.py          ← hiçbir şeyi import etmez
utils.py          ← theme, PyQt6, crypto_core.StepResult
alice_panel.py    ← theme, utils, PyQt6, crypto_core.StepResult
bob_panel.py      ← theme, utils, PyQt6, crypto_core.EncryptedPacket + StepResult
toast.py          ← theme, PyQt6
main_gui.py       ← theme, utils, alice_panel, bob_panel, toast,
                     crypto_core, animation_modals
```

Döngüsel bağımlılık yoktur.

---

## Yürütme Yaklaşımı

Tek seferde (all-at-once): 5 yeni dosya oluşturulur, `main_gui.py` güncellenir, tek commit atılır.

**Neden:** Refaktör saf mekanik (mantık değişmiyor). Import bağımlılıkları belirli ve az. Mevcut testler (`test_crypto_core.py`, `test_sha256_pure.py`) kripto katmanını kapsamakta; UI taşıma sırasında bozulacak iş mantığı yok.

---

## Başarı Kriterleri

- `python main_gui.py` komutu uygulama başlatır, davranış değişmez.
- Her yeni dosya tek bir sınıf veya sorumluluk içerir.
- `main_gui.py` 300 satırın altına iner.
- Döngüsel import yoktur.
- Mevcut testler geçmeye devam eder.
