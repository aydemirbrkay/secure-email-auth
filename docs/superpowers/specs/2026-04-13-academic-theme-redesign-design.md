# Academic Theme Redesign — Tasarim Dokumani

**Tarih:** 2026-04-13
**Proje:** Secure Email Authentication and Message Integrity
**Amac:** Mevcut Catppuccin Mocha koyu temadan acik, akademik bir temaya gecis; emoji azaltma; serif+sans-serif tipografi

---

## 1. Renk Paleti

### 1.1 Ana Renkler (`theme.py` — COLORS)

| Rol | Anahtar | Hex | Aciklama |
|-----|---------|-----|----------|
| Ana arka plan | `bg_main` | `#FAFAF5` | Sicak fildisi |
| Panel arka plan | `bg_panel` | `#FFFFFF` | Beyaz |
| Kart arka plan | `bg_card` | `#F0F1ED` | Acik bej-gri |
| Input arka plan | `bg_input` | `#E8E9E4` | Hafif gri |
| Birincil metin | `text_primary` | `#1F2937` | Koyu antrasit |
| Ikincil metin | `text_secondary` | `#4B5563` | Orta gri |
| Soluk metin | `text_muted` | `#9CA3AF` | Acik gri |
| Kenarlık | `border` | `#D1D5DB` | Notr gri |
| Focus kenarlık | `border_highlight` | `#3B6FA0` | Celik mavisi |
| Vurgu mavi | `accent_blue` | `#3B6FA0` | Celik mavisi |
| Vurgu yesil | `accent_green` | `#4E8B60` | Adacayi yesili |
| Vurgu kirmizi | `accent_red` | `#B94A4A` | Tugla kirmizisi |
| Vurgu sari | `accent_yellow` | `#B8860B` | Antik altin |
| Vurgu mor | `accent_mauve` | `#7B5EA7` | Lavanta moru |
| Vurgu turkuaz | `accent_teal` | `#3D8B80` | Koyu turkuaz |
| Vurgu seftali | `accent_peach` | `#B87333` | Bakir |

### 1.2 Adim Renkleri

Mevcut siralama korunur, sadece tonlar degisir:

**STEP_COLORS_ALICE** (icten disa):
1. `accent_blue` (#3B6FA0) — SHA-256
2. `accent_mauve` (#7B5EA7) — RSA Imza
3. `accent_yellow` (#B8860B) — Birlestirme
4. `accent_green` (#4E8B60) — AES-GCM
5. `accent_peach` (#B87333) — RSA Anahtar Sifreleme
6. `accent_teal` (#3D8B80) — Gonderim

**STEP_COLORS_BOB** (distan ice):
1. `accent_peach` (#B87333) — RSA Anahtar Cozme
2. `accent_green` (#4E8B60) — AES-GCM Desifreleme
3. `accent_yellow` (#B8860B) — Ayristirma
4. `accent_blue` (#3B6FA0) — SHA-256 Yeniden Hesaplama
5. `accent_mauve` (#7B5EA7) — Imza Dogrulama

### 1.3 Animasyon Renkleri (`animation_modals/base.py` — ANIM_COLORS)

ANIM_COLORS sozlugu COLORS ile senkronize edilecek. Tum animasyon pencereleri ayni acik tema renklerini kullanacak.

### 1.4 SHA-256 Register Renkleri (`sha256_animation.py` — _REG_COLORS)

8 register icin acik tema uyumlu tonlar:

| Register | Mevcut | Yeni |
|----------|--------|------|
| A | `#89b4fa` | `#3B6FA0` (celik mavisi) |
| B | `#cba6f7` | `#7B5EA7` (lavanta) |
| C | `#a6e3a1` | `#4E8B60` (adacayi) |
| D | `#f9e2af` | `#B8860B` (antik altin) |
| E | `#fab387` | `#B87333` (bakir) |
| F | `#94e2d5` | `#3D8B80` (turkuaz) |
| G | `#f38ba8` | `#B94A4A` (tugla) |
| H | `#74c7ec` | `#2E86AB` (acik celik mavisi) |

### 1.5 AES Operasyon Renkleri (`aes_animation.py` — _COLORS_OP)

| Operasyon | Mevcut | Yeni |
|-----------|--------|------|
| SubBytes | `#f9e2af` | `#B8860B` (antik altin) |
| ShiftRows | `#89b4fa` | `#3B6FA0` (celik mavisi) |
| MixColumns | `#cba6f7` | `#7B5EA7` (lavanta) |
| AddRoundKey | `#fab387` | `#B87333` (bakir) |

### 1.6 DiagramWidget Overlay Renkleri (`bob_panel.py`)

Mevcut kirmizi/yesil overlay renkleri acik arka plan uzerinde gorunur olmali:

| Rol | Mevcut | Yeni |
|-----|--------|------|
| Aktif adim kenarligi | `#E53935` (kirmizi) | `#C62828` (koyu kirmizi — acik arka planda daha net) |
| Aktif adim dolgu | `rgba(229,57,53,64)` | `rgba(198,40,40,50)` |
| Tamamlanan adim dolgu | `rgba(76,175,80,51)` | `rgba(78,139,96,50)` (adacayi tonu) |

---

## 2. Tipografi

### 2.1 Baslik Fontu (Serif)
- **Font ailesi:** `"Georgia", "Palatino Linotype", "Palatino", serif`
- **Kullanim yerleri:**
  - Ana pencere basligi (main_gui.py header QLabel)
  - Panel basliklari ("Gonderici — Alice", "Alici — Bob")
  - GroupBox basliklari (QGroupBox::title)
  - Animasyon pencere basliklari (base.py header QLabel)
  - Toast basligi ("DOGRULAMA BASARILI" / "DOGRULAMA BASARISIZ")

### 2.2 Govde Fontu (Sans-serif)
- **Font ailesi:** `"IBM Plex Sans", "Inter", "Segoe UI", sans-serif`
- **Kullanim yerleri:**
  - GLOBAL_STYLESHEET'te QWidget varsayilan font
  - Buton metinleri
  - Adim icerikleri (step content label'lari)
  - Durum mesajlari (status_label)
  - Input alanlari
  - Alt bilgi / aciklama metinleri
  - Anahtar bilgileri, karsilastirma metinleri

### 2.3 Monospace (degisiklik yok)
- **Font ailesi:** `"Courier New", monospace`
- Hex degerleri, hash ciktilari, Base64 gibi teknik veriler

### 2.4 GLOBAL_STYLESHEET Guncelleme
```css
QWidget {
    color: #1F2937;
    font-family: "IBM Plex Sans", "Inter", "Segoe UI", sans-serif;
}
```
Baslik label'lari kod icinde `QFont("Georgia", ...)` ile ayrica ayarlanacak.

---

## 3. Emoji Temizligi

### 3.1 Kaldirilacaklar (butonlar ve basliklar)

**main_gui.py:**
- Header: `"Secure Email Authentication and Message Integrity"` (emoji yok)
- Butonlar: `"Anahtar Uret"`, `"Sifreleme Baslat"`, `"Sonraki Adim"`, `"Sifirla"`
- Transit buton: `"Paketi Bob'a Gonder"`
- Tamamlandi buton: `"Tamamlandi"`
- GroupBox: `"RSA-2048 Anahtar Bilgileri"`, `"Orijinal Mesaj <-> Alinan Mesaj Karsilastirmasi"`
- Algo panel: `"Algoritmalari Izle"`
- Algo butonlari: `"RSA-2048\nAnahtar Sifreleme"`, `"SHA-256\nHash Hesaplama"`, `"AES-256-GCM\nSimetrik Sifreleme"`
- Toggle label: emoji onekleri kaldirilacak
- Anahtar bilgi header: `"Anahtarlar Basariyla Uretildi"` (emoji yok)
- Anahtar etiketleri: `"Alice Acik Anahtari (K+_A):"`, `"Bob Acik Anahtari (K+_B):"` (emoji yok)
- Karsilastirma etiketleri: `"Alice'in Gonderdigi"`, `"Bob'un Aldigi"` (emoji yok)

**alice_panel.py:**
- Baslik: `"Gonderici — Alice"` (emoji yok)
- Durum: `"Mesajinizi yazin ve sifreleme surecini baslatin."` (emoji yok)

**bob_panel.py:**
- Baslik: `"Alici — Bob"` (emoji yok)
- Durum: `"Alice'den paket bekleniyor..."` (emoji yok)
- Bekleme: `"Henuz bir paket alinmadi."` (emoji yok)

**animation_modals/rsa_animation.py:**
- Pencere basligi: `"RSA-2048 Anahtar Uretimi"` (emoji yok)

**toast.py:**
- Baslik icon label: kaldirilacak (renk + metin yeterli)

### 3.2 Kalacaklar (adim icerikleri ve bilgilendirme)

- `utils.py`: `"DOGRULANDI"` / `"DOGRULANAMADI"` emojileri
- `alice_panel.py`: adim durum mesajindaki `"Adim X/Y tamamlandi"` emojisi
- `bob_panel.py`: paket bilgisindeki emojiler (`"Sifreli mesaj boyutu"`, `"Sifreli oturum anahtari"`, `"Rastgele Sayi"`)
- `main_gui.py`: karsilastirma icerigindeki emojiler
- `toast.py`: dogrulama listesindeki `"ok"` / `"x"` simgeleri
- `rsa_animation.py`: adim iceriklerindeki egitim emojileri
- `base.py`: `"Kapat"` butonundaki `"x"` simgesi — KALACAK
- `bob_panel.py`: `"Kapat"` butonundaki `"x"` simgesi — KALACAK

---

## 4. Etkilenen Dosyalar

### 4.1 Degisecek Dosyalar

| Dosya | Degisiklik Kapsamı |
|-------|-------------------|
| `theme.py` | COLORS, GLOBAL_STYLESHEET, STEP_COLORS_ALICE/BOB — tam yeniden yazilacak |
| `main_gui.py` | Font tanimlari, emoji kaldirma, hardcoded renk referanslari |
| `alice_panel.py` | Baslik fontu, emoji kaldirma |
| `bob_panel.py` | Baslik fontu, emoji kaldirma, DiagramWidget overlay renkleri, _btn_close_diagram hardcoded renkleri |
| `toast.py` | Font tanimlari, baslik emoji kaldirma |
| `utils.py` | Font boyutu/stili guncellemesi |
| `animation_modals/base.py` | ANIM_COLORS sozlugu, font tanimlari |
| `animation_modals/rsa_animation.py` | Pencere basligi emoji kaldirma, font guncelleme |
| `animation_modals/sha256_animation.py` | _REG_COLORS acik tema tonlari, font guncelleme |
| `animation_modals/aes_animation.py` | _COLORS_OP acik tema tonlari, font guncelleme |

### 4.2 Ek: matrix_widget.py

`matrix_widget.py` hardcoded renkler iceriyor ve dogrudan degisiklik gerekiyor:

| Mevcut | Yeni | Aciklama |
|--------|------|----------|
| `_DEFAULT_BG = "#313150"` | `_DEFAULT_BG = "#F0F1ED"` | Kart arka plan (acik tema) |
| `_DEFAULT_FG = "#cdd6f4"` | `_DEFAULT_FG = "#1F2937"` | Birincil metin (acik tema) |
| `animate_row_shift` default `"#89b4fa"` | `"#3B6FA0"` | Celik mavisi |

**Not:** Animasyon mekanizmasi (highlight_cells_sequential, animate_row_shift mantigi, QTimer) DOKUNULMAYACAK. Sadece renk degerleri degisecek.

### 4.3 Degismeyecekler

- `crypto_core.py` — saf kriptografi, UI yok
- `animation_modals/sha256_pure.py` — saf hesaplama
- `animation_modals/aes_pure.py` — saf hesaplama
- Test dosyalari

---

## 5. Kritik Kisit: Animasyon Gorselleştirme Butunlugu

**KIRMIZI CIZGI — BU KURALLAR IHLAL EDILEMEZ:**

1. `_SHA256DiagramWidget` (register kutulari A-H, oklar, T1/T2 hesaplama alanlari): **SADECE renk degerleri** guncellenecek. Cizim mantigi (paintEvent, koordinatlar, dikdortgen boyutlari, ok yonleri) **KESINLIKLE DEGISMEYECEK**.

2. `MatrixWidget` (AES 4x4 matris, hucre highlight, satir kaydirma animasyonu): **SADECE renk degerleri**. Animasyon mekanizmasi **DOKUNULMAYACAK**.

3. `_MatrixDemoWidget` (AES intro canli demo): Ayni kural.

4. `DiagramWidget` (alice and bob.png overlay): Ayni kural.

5. Her animasyon dosyasinda degisiklik yapildiktan sonra **o ekranin calismasi ayrica test edilecek**.

### 5.1 Guvenli Degisiklik Sartlari

Animasyon dosyalarinda yapilacak degisiklikler su sinirlarla kisitlidir:
- Renk hex degerlerinin degistirilmesi (ornegin `"#89b4fa"` -> `"#3B6FA0"`)
- Font ailesi ve boyutu degisiklikleri (ornegin `"Segoe UI"` -> `"Georgia"`)
- Stylesheet string'lerindeki renk degerleri

Su islemler **YASAKTIR**:
- paintEvent icerisindeki cizim mantigi degisiklikleri
- Koordinat, dikdortgen boyutu veya ok yonu degisiklikleri
- QTimer araliklari veya animasyon zamanlama degisiklikleri
- Widget layout yapisi degisiklikleri
- Signal/slot baglantilari degisiklikleri

---

## 6. Test Stratejisi

1. Tema degisikliginden sonra uygulamayi calistir, ana pencereyi kontrol et
2. Alice panelinde mesaj yaz, sifreleme baslatigini dogrula
3. Tum 6 Alice adimini ilerle — her adimin renk cercevesini kontrol et
4. Bob panelindeki diyagram overlay'ini kontrol et (kirmizi blink, yesil tamamlandi)
5. Bob'a paket gonder, tum 5 Bob adimini ilerle
6. Dogrulama toast'unu kontrol et
7. **RSA animasyon ekranini ac** — 7 adimin tamaminin dogru gorundugunu dogrula
8. **SHA-256 animasyon ekranini ac** — register diyagraminin dogru cizildigini, renklerin okunabilir oldugunu dogrula
9. **AES animasyon ekranini ac** — intro animasyonu, round bar, matris gorunumunun dogru calistigini dogrula
10. Sifirla butonuyla tum sistemi resetle, tekrar baslat
