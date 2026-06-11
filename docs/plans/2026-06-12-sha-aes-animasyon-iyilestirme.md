# SHA ve AES Animasyon İyileştirme Planı

## Amaç

SHA-256 padding anlatımını okunabilir bir tempoya taşımak, uzunluk alanının
neden son 8 baytta bulunduğunu açıklamak ve AES-256-GCM akışında blok
şifreleyici, keystream üretimi ve mesaj XOR işlemini birbirinden ayrılan
eğitsel adımlar halinde göstermek.

## Aşama 1: SHA açıklama temposu

- `_SHAMessagePrepWidget` ve `_SHA256PaddingWidget` faz geçişleri yaklaşık
  beş saniyelik okunma süresi sağlayacak sabitlerle ifade edilecek.
- Erişilebilirlik hız ölçeğini uygulayan `get_animation_tick_ms` kullanımı
  korunacak.
- Faz eşikleri ve gerçek süre karşılığı birim testlerle doğrulanacak.

## Aşama 2: SHA uzunluk alanı açıklaması

- Padding faz metni; mesajın başta, `0x80` ve `0x00` dolgusunun ortada,
  gerçek mesaj uzunluğunun ise son 8 baytta olduğunu açıkça anlatacak.
- Son konumun, bloğu 64 bayta tamamlama ve gerçek mesaj uzunluğunu hash
  girdisine dahil etme amacı açıklanacak.
- Metin, `_padding_breakdown` tarafından hesaplanan gerçek bit uzunluğu ve
  son 8 bayt değeriyle tutarlı kalacak.

## Aşama 3: AES hazırlığını iki ekrana ayırma

- GCM modunda ilk ekran AES'i tanıdık bir blok şifreleyici olarak, kullanıcının
  ilk mesaj bloğu ve 4x4 state matrisiyle tanıtacak.
- İkinci ekran gerçek GCM akışını gösterecek: sayaç bloğu AES'ten geçer,
  keystream üretilir ve mesaj bu keystream ile XOR'lanır.
- İlk ekranın devam düğmesi ikinci hazırlık ekranına, ikinci ekranın devam
  düğmesi round görünümüne geçecek.
- ECB modunda mevcut tek hazırlık ekranı davranışı korunacak.

## Aşama 4: Keystream XOR adımı

- Round'lardan sonra ayrı bir GCM XOR sayfası gösterilecek.
- Sayfa `mesaj bloğu XOR keystream bloğu = şifreli metin` işlemini bayt bayt
  canlandıracak ve yalnızca mevcut mesaj baytları için sonuç iddiasında
  bulunacak.
- Match sayfasındaki tekrar eden XOR gösterimi kaldırılacak; match sayfası
  column-major dizilim ve kısa dürüst özet için kullanılacak.
- Üstteki `keystream` düğmesi açıklama diyaloğunu açacak.

## Aşama 5: Keystream ve GCM diyaloğu

- S-Box referans penceresi deseninde, tema değişimine duyarlı bir
  `_KeystreamReferenceDialog` oluşturulacak.
- Diyalog gerçek keystream baytlarını ve üretim yolunu gösterecek:
  `nonce || sayaç` bloğu AES-256 ile şifrelenir.
- Gizlilik için XOR, nonce tekrarının tehlikesi, GCM'in AEAD yapısı, GHASH
  etiketi, 12 bayt nonce, 16 bayt tag ve AAD rolü açıklanacak.

## Doğrulama

- Her davranış değişikliğinde önce başarısız test yazılacak, sonra en küçük
  uygulama değişikliğiyle test geçirilecek.
- Tam paket `python -B -m pytest -q -p no:cacheprovider` komutuyla çalıştırılacak.
- Değişen widget'lar Qt offscreen ortamında kurulup render edilerek taşma ve
  bağlantı hatalarına karşı kontrol edilecek.
- Kriptografik çekirdek ve AES-256-GCM parametreleri değiştirilmeyecek.
