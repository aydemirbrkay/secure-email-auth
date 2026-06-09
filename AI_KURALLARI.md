# AI Asistan Çalışma Kuralları

> Bu dosya, **Berkay Aydemir**'in Erciyes Üniversitesi Bilgisayar Mühendisliği bitirme projesi olan **"Güvenli E-posta Kimlik Doğrulama ve Mesaj Bütünlüğü Sistemi"** üzerinde yardım eden tüm yapay zeka asistanları için bağlayıcı kurallardır. Asistan, bu projede bir göreve başlamadan önce bu dosyayı **her zaman** okumalıdır.

---

## 1. Projenin Kimliği (Değişmez Temel)

- **Proje adı:** Secure Email Authentication and Message Integrity
- **Sahibi:** Berkay Aydemir — 1030521387
- **Danışman:** Prof. Dr. Serkan ÖZTÜRK
- **Kurum:** Erciyes Üniversitesi — Bilgisayar Mühendisliği Bölümü
- **Senaryo:** Alice (gönderici) → Bob (alıcı) hibrit şifreleme akışı
- **Çalışma Python sürümü:** **3.11** (conda veribilimi ortamında PyQt6 DLL sorunu yaşandı, kullanılmaz)
- **GUI çatısı:** PyQt6 (>=6.6.0)
- **Kripto kütüphanesi:** `cryptography` (>=44.0.0) — `os.urandom`, `cryptography.hazmat.primitives`

> ⚠️ **TEZ DURUMU (GÜNCEL DEĞİL):** Proje klasöründeki `Thesis.pdf` **eski/öneri sürümüdür**; projenin güncel halini yansıtmaz. Gerçek tez LaTeX kaynağındadır (`BM-LatexTemplate`) ve projenin son haline göre **kullanıcı tarafından ayrıca güncellenecektir**. Bu nedenle: hiçbir değerlendirme, puanlama veya karar `Thesis.pdf`'e dayandırılmaz; **tez/akademik-belge kapsamı şimdilik DİKKATE ALINMAZ**. İyileştirme çalışmaları yalnızca kod/UI/test üzerine odaklanır.

---

## 2. KESİNLİKLE DEĞİŞMEYECEK ÇEKİRDEK ALGORİTMALAR

Aşağıdaki algoritma seçimleri ve parametreleri projenin akademik temelidir. AI asistan **bu kararları sorgulayamaz, alternatif öneremez, modunu değiştiremez, parametresini değiştiremez**. Sadece sunum/animasyon/UI üzerinde değişiklik yapabilir.

### 2.1 SHA-256 — Mesaj Özeti
- **Algoritma:** SHA-256 (hashlib veya saf Python implementasyonu `animation_modals/sha256_pure.py`)
- **Çıktı:** 256-bit (32 byte) özet
- **Kullanım:** H(m), imza için ön-hash, AAD parmak izi

### 2.2 RSA-2048 — Asimetrik Şifreleme ve İmza
- **Anahtar boyutu:** 2048-bit (DEĞİŞMEZ)
- **Public exponent:** 65537
- **İmza:** RSA-PSS + `Prehashed(SHA256())` + `MGF1(SHA256())` + `PSS.MAX_LENGTH` salt
- **Anahtar şifreleme:** RSA-OAEP + `MGF1(SHA256())` + `algorithm=SHA256` + `label=None`
- **Anlatım notu:** İmza, H(m) zaten hesaplandığı için `Prehashed` ile yapılır; aksi hâlde anlatım ("H(m) imzalanır") çakışır. Bu nüans **korunmalıdır**.

### 2.3 AES-256-GCM — Simetrik AEAD Şifreleme
- **Mod:** GCM (Galois/Counter Mode) — DEĞİŞMEZ, ECB/CBC önerilemez
- **Anahtar:** 256-bit (`os.urandom(32)`)
- **Nonce:** 96-bit (`os.urandom(12)`) — her şifrelemede yeni rastgele
- **Çıktı biçimi:** `ciphertext || tag` (tek alanda birleşik)
- **AAD biçimi:** `secure-email-auth/v1|from=<fp16hex>|ts=<unix>` — protokol etiketi + gönderen public-key SHA-256 parmak izinin ilk 8 byte'ı (16 hex char) + Unix saniye

### 2.4 İş Akışı (Adımların Sırası DEĞİŞMEZ)

**Alice (6 adım):**
1. `H(m) = SHA-256(m)`
2. `σ = RSA-PSS_signKpriv_A(H(m))`
3. `payload = m || σ`
4. `(nonce, ct||tag) = AES-GCM_KS(payload, AAD)`
5. `ek = RSA-OAEP_Kpub_B(KS)`
6. Paket gönder: `{ct||tag, ek, nonce, AAD}`

**Bob (5 adım):**
1. `KS = RSA-OAEP_decryptKpriv_B(ek)`
2. `payload = AES-GCM_decryptKS(ct||tag, nonce, AAD)`
3. `m, σ = ayrıştır(payload)`
4. `H'(m) = SHA-256(m)`
5. `geçerli? = RSA-PSS_verifyKpub_A(σ, H'(m))`

### 2.5 Bilinen ve Belgelenmiş Sınırlar (Bunlar BUG değildir)
- Replay koruması yok (kabul edilmiş akademik sınır).
- Forward secrecy yok (RSA-OAEP uzun ömürlü anahtarla key wrap).
- Bu iki sınır README'de açıkça belirtilmiştir; AI bunları "kritik bug" olarak rapor edemez.

---

## 3. PAKET / DOSYA YAPISI (Mimari İskelet)

```
BİTİRME PROJESİ/
├── main_gui.py                 # MainWindow, akış orkestratörü
├── kriptografi/                # Saf kripto iş mantığı (UI yok)
│   ├── crypto_core.py          # SHA/RSA/AES + alice_send/bob_receive
│   ├── crypto_workers.py       # QThread worker'ları (UI thread'i bloklamaz)
│   └── utils.py                # Yardımcılar (ikon, hata formatı)
├── arayuz/                     # PyQt6 panel ve tema motoru
│   ├── alice_panel.py          # Gönderici paneli
│   ├── bob_panel.py            # Alıcı paneli
│   ├── theme.py                # DARK/LIGHT palet, ThemeManager, ANIM_COLORS
│   ├── theme_toggle.py         # Ay/güneş tema geçiş butonu
│   └── toast.py                # Doğrulama toast bildirimi
├── animation_modals/           # Algoritma animasyon pencereleri
│   ├── base.py                 # CryptoAnimationWindow + paylaşılan stiller
│   ├── rsa_animation.py        # RSA görsel anlatımı
│   ├── sha256_animation.py     # SHA-256 görsel anlatımı + sha256_pure.py
│   ├── aes_animation.py        # AES görsel anlatımı + aes_pure.py
│   ├── aes_matrix_view.py      # 4×4 state matrix widget
│   ├── matrix_widget.py        # Genel matrix widget
│   └── byte_widgets.py         # Renkli byte grid/strip
├── testler/                    # pytest test paketi (213+ test, %100 geçer)
├── görseller/                  # Kullanılan görseller: alice and bob.png, bob-tarafi-sifre-cozme.png, secure-email-simge.png, gear.svg
└── docs/                       # Tüm .md belgeleri (plans/, specs/, raporlar) — yeni belgeler buraya açılır (bkz. 5.6)
```

**Bu sorumluluk ayrımı korunur (klasör adları sabit değildir, sorumluluklar sabittir):**
- Kripto kodu **asla** UI paketlerine kaçırılmaz; saf kripto `kriptografi/` benzeri bir paketin içinde kalır.
- UI thread'inde uzun süren kripto çağrısı **yapılmaz** — `crypto_workers.py` kullanılır.
- Yeni dosya açmadan önce mevcut bir modüle eklenebilir mi sorgulanır.
- Klasör veya dosya adı (Türkçe/İngilizce) bağlayıcı değildir; bir yeniden adlandırma istendiğinde sadece referansların güncellenmesi gerekir.

---

## 4. HEDEF KULLANICI (Tüm Tasarım Kararlarının Pusulası)

Hedef kullanıcı **kriptografi algoritmalarını ilk kez öğrenen lisans öğrencisidir**. Bu, her teknik kararı etkiler:

- Animasyonlar **adım adım** ilerlemeli, atlamamalı.
- Her adımda öğrenci "şu an ne oluyor?" sorusuna **görsel** bir cevap görmeli.
- Notasyon **akademik standartlarla uyumlu** olmalı (örn. `ϕ` Euler totient, `H(m)`, `K⁻_A`, `K⁺_B`).
- UI metinleri/etiketleri Türkçedir; UTF-8 desteği **bozulamaz** (ş, ğ, ı, ç, ö, ü düzgün gözükmeli).
- Renk paleti hem aydınlık hem karanlık temada okunaklı olmalı.
- Yeni özellik eklerken sorulması gereken tek soru: **"Bu, öğrencinin algoritmayı daha iyi anlamasına yardım ediyor mu?"** Cevap "hayır" ise eklenmez.

---

## 5. AI'IN ÇALIŞMA KURALLARI (BU PROJEYE ÖZGÜ)

### 5.1 İzinler ve Yetki Sınırı
- **Okuma:** Tüm proje dosyalarını okuyabilirsin.
- **Yazma/değiştirme:** Sadece kullanıcının açıkça istediği görev kapsamında. Görev belirsizse önce sor.
- **Asla dokunma:** `kriptografi/crypto_core.py` içindeki algoritma parametreleri (RSA modu, AES modu, hash seçimi, anahtar boyutları). Bunlar kullanıcı **açıkça** istemedikçe değiştirilmez.
- **Asla silme:** Test dosyalarını veya `görseller/` içindeki kaynakları sebepsiz silme.

### 5.2 Görev Başlangıcı (Kısa, Token Tasarruflu)
1. Önce **bu dosyayı (`AI_KURALLARI.md`) ve `README.md`** oku.
2. Görev hangi modülü ilgilendiriyor? Sadece o dosyayı ve doğrudan importlarını oku — **tüm projeyi tarama**.
3. Test gerekiyorsa sadece ilgili `testler/test_*.py` dosyasını oku.
4. Sonra kullanıcıya 1-2 cümlelik **plan** sun. Onay almadan büyük değişiklik yapma.

### 5.3 Kod Yazım Stili
- Mevcut dosyaların stiline uy: `from __future__ import annotations`, type hints, Türkçe docstring.
- Yorumlar **kısa ve "neden"** anlatır, "ne" anlatmaz.
- Yeni dosya açmaktan kaçın; mevcut modüle ekle. Ancak **büyük animasyon dosyaları** (örn. `rsa_animation.py`, `sha256_animation.py`, `aes_animation.py` gibi tek dosyada ~1000+ satıra ulaşan modüller) **alt-pakete bölünür**: ilgili modül için `animation_modals/<algoritma>/` klasörü açılır, içine `__init__.py` + mantıksal alt modüller (örn. `steps.py`, `widgets.py`, `pure.py`, `view.py`) konur ve dış import yüzeyi (`animation_modals/__init__.py`) korunur. Bölme sırasında public API kırılmamalıdır.
- Emoji **ölçülü** kullanılır: vurgu/durum/ikon yerine (örn. ✓, ⚠, →, ✗) yerinde ve seyrek. Süs amaçlı toplu emoji **kullanılmaz**.

### 5.4 Test ve Doğrulama
- Test suite'i **213+ test** içeriyor ve %100 geçiyor. Hiçbir değişiklik bu sayıyı kıramaz.
- **Yeni eklenen veya değiştirilen her davranış için uygun test kodu yazılır.** Yeni fonksiyon/sınıf/akış → ilgili `testler/test_*.py` dosyasına en az bir pozitif + bir negatif (hata/kenar durum) test eklenir. Test eklenmeden değişiklik tamamlanmış sayılmaz.
- Test dosyası adlandırması mevcut kalıba uyar: `testler/test_<modul>.py`. Yeni bir paket için yeni `test_*.py` dosyası açılabilir.
- Kod değişikliği yapıldıysa **en azından ilgili `testler/test_*.py` dosyalarını çalıştır**:
  ```
  python -B -m pytest testler/test_<modul>.py -q
  ```
- Tüm suite için:
  ```
  python -B -m pytest -q -p no:cacheprovider
  ```

### 5.5 Docstring Zorunluluğu (KRİTİK)

- **Yeni eklenen veya değiştirilen HER fonksiyon/metot/sınıf için açıklamalı ve detaylı bir docstring yazılır.** Docstring olmadan bir fonksiyon tamamlanmış sayılmaz.
- Docstring **Türkçe** yazılır ve fonksiyonun **ne işe yaradığını** açık biçimde anlatır; sadece imzayı tekrar etmez.
- Detaylı docstring şunları içerir (uygun olduğunda):
  - **Amaç:** Fonksiyonun ne yaptığı ve neden var olduğu (1-2 cümle).
  - **Parametreler:** Her parametrenin anlamı, beklenen tip/biçim ve varsa kısıtları.
  - **Dönüş değeri:** Ne döndüğü ve biçimi (ör. `ciphertext || tag`, `(nonce, ct)`).
  - **Yan etkiler / istisnalar:** Fırlatabileceği hatalar, UI/thread etkileri, durum değişiklikleri.
  - **Kripto/algoritma notu:** Çekirdek algoritmaya dokunan fonksiyonlarda ilgili adım (ör. "Alice 2. adım: H(m) imzalanır") belirtilir.
- Mevcut bir fonksiyona **dokunulduğunda** (refactor, düzeltme, parametre değişimi) docstring de güncel hale getirilir; eski/yanlış docstring bırakılmaz.
- Tek satırlık trivial yardımcılar için bile en az bir cümlelik özet docstring bulunur.
- Biçim olarak mevcut dosyaların kalıbına uyulur (üç tırnak `"""..."""`, ilk satır kısa özet).

### 5.6 Dokümantasyon Konumu (.md Dosyaları)

- **Yeni oluşturulacak tüm `.md` belgeleri `docs/` klasörü altında oluşturulur** (planlar, tasarım/spec notları, raporlar, prompt listeleri, kılavuzlar vb.). Proje kökü `.md` dosyalarıyla doldurulmaz.
  - Plan belgeleri → `docs/plans/`
  - Tasarım/spec belgeleri → `docs/specs/`
  - Rapor / değerlendirme / diğer belgeler → doğrudan `docs/` altına.
- **İstisna (kökte kalır):** Yalnızca `README.md` (depo ana sayfası), `AI_KURALLARI.md` (bu sözleşme, kökten okunur) ve `LICENSE`. Bunların dışındaki hiçbir `.md` proje köküne konmaz.
- Mevcut bir belgeyi taşırken ona verilen bağlantılar (README rozetleri, çapraz referanslar) güncellenir.

---

## 6. GİT COMMİT KURALLARI (KRİTİK)

### 6.1 YASAK
- Commit mesajında, branch adında, dosya adında veya kod içinde **"Claude", "Anthropic", "AI", "GPT", "ChatGPT", "Copilot", "yapay zeka tarafından", "AI generated"** geçmez.
- `Co-Authored-By: Claude ...` satırı **asla** eklenmez.
- `🤖 Generated with Claude Code` veya benzeri imza/footer **asla** eklenmez.
- `--no-verify`, `--no-gpg-sign` kullanılmaz (kullanıcı açıkça istemedikçe).
- `git push --force` ana dala yapılmaz.

### 6.2 ZORUNLU
- Commit mesajı **Türkçe** ve mevcut prefix-stiline uyumlu olur. Mevcut prefix ailesi:
  - `kripto:` — kripto/algoritma/animasyon davranışı değiştiğinde
  - `tema:` — `arayuz/theme.py` veya tema entegrasyonu değiştiğinde
  - `arayüz:` veya `ux:` — Panel/widget/yerleşim/etkileşim değiştiğinde
  - `test:` veya `testler:` — Sadece test eklendi/güncellendiyse
  - `yapı:` — Klasör/paket yapısı değiştiğinde
  - `belge:` — README/dokümantasyon değiştiğinde
  - `düzelt:` — Bug fix
- Mesaj **özne fiil** biçiminde, **kısa** (ilk satır ≤ 72 karakter), olabildiğince spesifik. Örnek:
  - ✅ `kripto: SHA-256 round diyagramı W satırı çakışması düzeltildi`
  - ❌ `update sha256` / `Fix bug` / `İyileştirmeler`
- Türkçe karakter (`ş, ğ, ı, ç, ö, ü`) kullanmak serbest; ASCII tercih edilirse de tutarlı kalınmalı (mevcut commit'lerde her ikisi de var).

### 6.3 Otomatik Yükleme Akışı
Kullanıcı "GitHub'a yükle" / "commit at" / "push et" dediğinde AI şu sırayı izler:

1. `git status` ile değişiklikleri göster (kullanıcıya).
2. `git diff` ile farkı incele.
3. Mesajı yukarıdaki kurallara göre **HEREDOC** ile hazırla. Örnek:
   ```
   git commit -m "$(cat <<'EOF'
   kripto: AES MixColumns sütun vurgusu hız ayarı

   Öğrencinin dönüşümü takip edebilmesi için sütun geçişi 600ms'ye
   çekildi; önceki 300ms'de animasyon atlanıyor gibi görünüyordu.
   EOF
   )"
   ```
   — Bu mesajda **hiçbir AI imzası yok**, bu doğru biçimdir.
4. Sadece kullanıcının istediği dosyaları `git add <yol>` ile ekle. `git add -A` / `git add .` **kullanma** (gizli/hassas dosya kaçışı riski).
5. Commit sonrası `git status` ile doğrula.
6. Push, kullanıcı açıkça isterse yapılır: `git push origin main`.

---

## 7. TOKEN TASARRUFU KURALLARI (Maliyet → Kazanç)

> Bu projeyi geliştirirken kullanıcının AI maliyeti minimum olmalıdır. AI bu kuralları uygular:

### 7.1 Okuma Disiplini
- **Tüm projeyi tarama** alışkanlığı yasak. Sadece görevin dokunduğu dosyayı ve doğrudan importlarını oku.
- `git log --oneline -10` çoğu zaman tüm `git log` tarama ihtiyacını ortadan kaldırır.
- `Grep` ile spesifik sembol araması, dosya açıp gezmekten **çok daha ucuzdur**.
- Bir dosyayı **birden fazla kez okuma** — Read tool'u durumu zaten takip eder.
- Büyük dosyada sadece ilgili satır aralığını `offset/limit` ile oku.

### 7.2 Yanıt Disiplini
- Cevaplar **kısa** olur. Tek cümle yetiyorsa paragraf yazma.
- "Şunu yaptım, şunu yaptım, şunu yaptım…" özetleri yazma — kullanıcı diff'i görüyor.
- Tablolar, başlıklar, emoji ile şişirme yapma.
- Plan/tartışma istenmedikçe **direkt uygula**.

### 7.3 Subagent / Paralel Çalışma
- Tek dosyalık iş için subagent **açma**.
- Sadece 3+ bağımsız araştırma sorgusu varsa `Explore` agent kullan.
- Asistan tabanlı maliyetli işlemleri (örn. `/ultrareview`) **AI kendisi başlatmaz** — kullanıcı tetikler.

### 7.4 Kullanıcıdan Soru Sorma
- Soru sormadan önce 1 dakikalık `Grep` denemesi yap. Cevabı kodda bulabiliyorsan **sorma**.
- Soru gerekiyorsa **spesifik** sor: "X dosyasında Y mı, Z mi?" — "Ne yapmamı istersin?" gibi açık uçlu sorular **maliyetlidir**.

### 7.5 Bağlam Hatırlatması
- Kullanıcının Python sürümü **3.11** (auto-memory'de kayıtlı). Conda ortamından kaçın.
- Kullanıcı PyQt6 DLL sorunu yaşamış — paket önerirken bunu hatırla.
- Test suite zaten **yeşil** — yeni bir bug avına çıkma; sadece dokunduğun yere odaklan.

---

## 8. ANİMASYON / UI DEĞİŞİKLİKLERİ İÇİN ÖZEL KURALLAR

- Animasyon **durumunu bozmadan** tema değişimi yapılır (`_restyle_content` kalıbı — bkz. mevcut commit'ler).
- `ANIM_COLORS` paleti `arayuz/theme.py` üzerinden okunur, hex değer **hardcode edilmez**.
- Yeni renk eklenecekse hem DARK hem LIGHT varyantı tanımlanır.
- Adım kutuları, ok rozetleri, formül kutuları **mevcut stil sınıfları** ile kurulur.
- Türkçe karakterleri **ASCII'ye düşürme** — UTF-8 korunur.
- Round/adım navigasyonu butonları **görünür kalmalı** (mevcut `ux: round nav görünürlüğü` commit'i bu konuyu çözmüş, bozma).

---

## 9. YASAKLI DAVRANIŞLAR (Kısa Liste)

1. ❌ Algoritma parametrelerini değiştirmek (anahtar boyutu, mod, hash).
2. ❌ Commit mesajına AI ismi/imzası eklemek.
3. ❌ Yeni davranış/fonksiyon eklerken test yazmamak (her değişiklik için uygun `testler/test_*.py` testi zorunludur).
4. ❌ Tüm projeyi okumadan değişiklik yapmadan önce **tüm projeyi okumak** (token israfı).
5. ❌ Test çalıştırmadan "tamam, bitti" demek.
6. ❌ `git add -A` veya `git add .`.
7. ❌ UI thread'inde kripto çağrısı yapmak.
8. ❌ Mevcut animasyon mantığını sebepsiz refactor etmek.
9. ❌ İngilizce commit mesajı veya İngilizce `.md` dosyası yazmak (commit mesajları ve dokümantasyon Türkçedir — klasör/dosya/değişken adlandırması bu kuralın kapsamı **dışındadır**).
10. ❌ Belgelenmiş sınırları (replay, forward secrecy) "bug" olarak raporlamak.
11. ❌ Aşırı/süs emoji kullanmak (ölçülü, durum/ikon vurgusu serbesttir; başlık şişirme veya her satıra emoji yasaktır).
12. ❌ Yeni eklenen veya değiştirilen bir fonksiyonu **detaylı docstring olmadan** bırakmak (bkz. 5.5).
13. ❌ Yeni `.md` belgesini `docs/` dışında, proje köküne oluşturmak (izinli istisnalar: `README.md`, `AI_KURALLARI.md`, `LICENSE` — bkz. 5.6).

---

## 10. GÖREV BAŞLAMA KONTROL LİSTESİ

AI bu projede her göreve başlarken kendisine şu soruları sorar:

- [ ] Bu görev hangi pakete dokunuyor? (`kriptografi/`, `arayuz/`, `animation_modals/`, `testler/`)
- [ ] Çekirdek algoritma değişiyor mu? → Hayır olmalı. Evet ise kullanıcıya açıkça onay sor.
- [ ] Hangi dosyaları okumam yeterli? (Tümünü değil, sadece ilgili olanları.)
- [ ] Yeni dosya açmak gerekiyor mu, yoksa mevcut bir modüle eklenebilir mi?
- [ ] Dokunduğum animasyon dosyası 1000+ satıra ulaştıysa, bu görev kapsamında alt-pakete bölme fırsatı var mı?
- [ ] Yeni davranış/fonksiyon eklediysem, ilgili `test_*.py` dosyasına test ekledim mi? (En az bir pozitif + bir negatif.)
- [ ] Commit mesajı hangi prefix ile başlayacak? (`kripto:`, `tema:`, `ux:` ...)
- [ ] Mesajda AI imzası yok mu? (Olmamalı.)

---

## 11. KISA REFERANS — Sık Kullanılan Komutlar

```
# Tek test dosyası
python -B -m pytest testler/test_crypto_core.py -q

# Tüm suite
python -B -m pytest -q -p no:cacheprovider

# Uygulamayı çalıştır (Python 3.11 ile)
python main_gui.py

# Son 10 commit (stil için)
git log --oneline -10

# Sadece belirli dosyayı stage'le
git add main_gui.py

# Türkçe commit (HEREDOC ile)
git commit -m "$(cat <<'EOF'
kripto: <konu>

<gerekirse 1-2 satır neden>
EOF
)"
```

---

**Son söz:** Bu dosya bir sözleşmedir. Kullanıcı her seansta seni bunu okumaya zorlar; sen her seansta buna uyarsın. Şüpheye düştüğünde — yapma, sor.
