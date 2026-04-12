# Embedded Animation in Alice Panel — Design Spec

**Date:** 2026-04-12  
**Status:** Approved

## Problem

RSA, SHA-256 ve AES animasyon pencereleri şu an bağımsız üst-düzey pencereler olarak açılıyor (`Qt.WindowType.Window`), ekranın %82×%85'ini kaplıyor ve rastgele konumlanıyor. Kullanıcı, Bob panelindeki diyagram widget'ına benzer biçimde bu animasyonların Alice paneli alanında (ekranın sol yarısı) yerleşik olarak görünmesini istiyor. AES animasyonu ayrıca dar alanlarda içerik taşması yaşıyor.

---

## Hedef Davranış

- Bir animasyon tetiklendiğinde Alice panelinin normal içeriği (başlık, mesaj kutusu, adım scroll alanı, durum etiketi) gizlenir.
- Animasyon widget'ı Alice panelinin tamamını kaplar — tıpkı Bob panelindeki `DiagramWidget` gibi.
- Animasyon "Kapat" butonuna basılınca Alice panelinin normal içeriği geri döner.
- Sıfırlama (`_on_reset`) animasyonu zorla kapatır.
- Aynı anda yalnızca bir animasyon görünebilir; yeni bir animasyon eskisini otomatik olarak değiştirir.
- "Algoritmaları İzle" butonlarıyla yeniden açılan animasyonlar da aynı şekilde Alice panelinde görünür.

---

## Değiştirilecek Dosyalar

### 1. `animation_modals/base.py`

`CryptoAnimationWindow.__init__`'e `on_close: callable | None = None` opsiyonel parametresi eklenir.

**`on_close` verilirse (embedded mod):**
- `setWindowFlags(Qt.WindowType.Window)` uygulanmaz — widget bağımsız pencere olmaz.
- `setAttribute(WA_DeleteOnClose)` uygulanmaz — yaşam döngüsü parent tarafından yönetilir.
- Ekran boyutuna göre `resize()` yapılmaz.
- "Kapat" butonu `on_close` callback'ini çağırır.

**`on_close` verilmezse (standalone mod):**
- Mevcut davranış hiç değişmez (geriye dönük uyumluluk).

### 2. `alice_panel.py`

BobPanel'deki `_diagram_container` örüntüsü eklenir.

**Yeni alanlar:**
```python
_anim_container: QWidget       # başta gizli
_anim_scroll: QScrollArea      # içinde animasyon widget'ı yaşar
_normal_widgets: list[QWidget] # hide/show edilecek normal içerik
```

**Yeni metodlar:**
```python
def show_animation(self, widget: QWidget) -> None:
    """Normal içeriği gizle, animasyonu QScrollArea içinde göster."""

def hide_animation(self) -> None:
    """Animasyonu temizle, normal içeriği geri getir."""
```

`show_animation` çağrıldığında: başlık, mesaj kutusu, cumulative scroll alanı ve durum etiketi gizlenir; `_anim_container` görünür hale gelir. Zaten bir widget varsa önce kaldırılır.

`hide_animation` çağrıldığında: `_anim_container` gizlenir, scroll alanındaki widget kaldırılır, normal içerik yeniden gösterilir.

### 3. `main_gui.py`

`RSAAnimationWindow`, `SHA256AnimationWindow`, `AESAnimationWindow` oluşturma satırları güncellenir:

```python
# Eski
win = RSAAnimationWindow(alice_b64, bob_b64)
win.show()
self._anim_windows.append(win)

# Yeni
win = RSAAnimationWindow(alice_b64, bob_b64,
                         on_close=self._alice_panel.hide_animation)
self._alice_panel.show_animation(win)
```

`_reopen_rsa`, `_reopen_sha`, `_reopen_aes` metodları da aynı şekilde güncellenir.

`_on_reset`'e `self._alice_panel.hide_animation()` eklenir.

`_anim_windows` listesi ve `.clear()` çağrısı kaldırılır (artık gerekli değil).

### 4. `animation_modals/aes_animation.py` — AES Taşma Düzeltmesi

`_AESIntroWidget` dar alanlarda yatay taşma yaşıyor. `AlicePanel.show_animation` içindeki `QScrollArea` sarmalayıcısı hem yatay hem dikey kaydırmayı etkinleştirir (`setHorizontalScrollBarPolicy(ScrollBarAsNeeded)`). Bu, ek widget değişikliği gerektirmeden taşmayı çözer.

---

## Etkilenmeyen Dosyalar

- `animation_modals/rsa_animation.py` — `__init__` imzası değişmez; base class parametresini alır.
- `animation_modals/sha256_animation.py` — aynı şekilde.
- `bob_panel.py` — hiç değişmez.
- `theme.py`, `crypto_core.py`, `utils.py` — hiç değişmez.

---

## Veri Akışı

```
main_gui._on_keygen()
  → RSAAnimationWindow(..., on_close=alice_panel.hide_animation)
  → alice_panel.show_animation(win)
      • normal içerik gizlenir
      • win, scroll area'ya eklenir
      • _anim_container görünür

Kullanıcı "Kapat"a basar
  → win._on_close callback çağrılır (= alice_panel.hide_animation)
  → normal içerik geri gelir
```

---

## Kapsam Dışı

- Animasyon widget'larının iç içerik düzenini yeniden tasarlamak.
- Bob panelinde herhangi bir değişiklik.
- Birden fazla animasyonu aynı anda göstermek.
