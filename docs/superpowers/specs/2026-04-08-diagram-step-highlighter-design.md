# Spec: Diagram Step Highlighter — Bob Paneli Diyagram Animasyonu

**Tarih:** 2026-04-08  
**Proje:** Secure Email Authentication and Message Integrity  

---

## Genel Bakış

Alice'in 6 gönderme adımının her biri için Bob panelinin üstünde kriptografi diyagramı (`alice and bob.png`) gösterilir. Aktif adıma karşılık gelen diyagram bloğunun etrafı 1 sn aralıkla kırmızı çerçeveli yanıp söner. Tamamlanan adımlar yeşil dolgu ile işaretlenir. Alice'in 6. adımı gösterildikten sonra "Kapat" butonu aktif olur ve kullanıcı tıklayınca diyagram gizlenir, Bob'un deşifreleme ekranı açılır.

---

## Mimari

### Yeni widget: `DiagramWidget` (`bob_panel.py` içinde)

`QWidget` alt sınıfı. Sorumlulukları:
- `alice and bob.png` dosyasını `QPixmap` olarak yükler, 623×283 sabit boyutunda gösterir.
- `_active_step: int` (0-5) — şu an yanıp sönen adımın indeksi (-1 = hiçbiri).
- `_completed_steps: set[int]` — tamamlanmış adımların indeksleri.
- `QTimer` (1000 ms) ile `_blink_on: bool` toggle edilir; her toggle `update()` tetikler.
- `paintEvent`: önce pixmap'i çizer, sonra tamamlanan adımlar için yeşil dolgu, ardından aktif adım için kırmızı kenarlık + `_blink_on` durumuna göre kırmızı dolgu overlay çizer.
- `set_active_step(idx)`: aktif adımı günceller, timer'ı başlatır.
- `mark_step_done(idx)`: adımı tamamlandı olarak işaretler, yeşil dolgu için.
- `stop_blink()`: timer durdurur, `_active_step = -1`.

### `BobPanel` değişiklikleri

- `_diagram_widget: DiagramWidget` — `_init_ui()` içinde `layout`'un en üstüne eklenir, başlangıçta `setVisible(False)`.
- `_btn_close_diagram: QPushButton` — "✖ Kapat" butonu, `DiagramWidget`'ın içinde en altta yer alır, başlangıçta `setEnabled(False)`.
- `show_diagram()`: `_diagram_widget.setVisible(True)` çağırır.
- `set_diagram_step(step_idx: int)`: `mark_step_done(step_idx - 1)` + `set_active_step(step_idx)` zinciri.
- `finish_diagram()`: `stop_blink()` + `_btn_close_diagram.setEnabled(True)`.
- `_on_close_diagram()` (slot): `_diagram_widget.setVisible(False)`.

### `main_gui.py` değişiklikleri

`_on_next_step()` içinde `alice` fazı bloğunun başına eklenir:

```python
# Gösterilecek adımın indeksi (show_next_step() çağrısından ÖNCE okunur)
step_idx = self._alice_panel._current_step  # 0..5

# İlk adımda diyagramı göster
if step_idx == 0:
    self._bob_panel.show_diagram()

# ... mevcut SHA/AES animasyon penceresi kodları ...

self._alice_has_more = self._alice_panel.show_next_step()

# Diyagramda bu adımı vurgula
self._bob_panel.set_diagram_step(step_idx)

# Son adımsa Kapat butonunu aktif et (yanıp sönme devam eder, kullanıcı kapatır)
if not self._alice_has_more:
    self._bob_panel.enable_close_button()
    self._phase = "transit"
    self._btn_next.setText("📨 Paketi Bob'a Gönder")
```

`set_diagram_step(idx)` içi: `mark_step_done(idx - 1)` (idx > 0 ise) + `set_active_step(idx)`.  
`enable_close_button()`: yalnızca `_btn_close_diagram.setEnabled(True)` — blink ve highlight devam eder, kullanıcı "Kapat"a tıklayana kadar.

---

## Adım → Koordinat Haritası

Koordinatlar `alice and bob.png` görseli 623×283 boyutunda gösterildiğinde geçerlidir.  
`QRect(x, y, genişlik, yükseklik)` formatında (piksel, sol-üst köşe referanslı).

| İndeks | Alice Adımı | Diyagram Bloğu | QRect |
|--------|-------------|----------------|-------|
| 0 | SHA-256 Özet | m → H(·) bloğu | `QRect(95, 78, 95, 38)` |
| 1 | RSA Dijital İmza | K_A^-(·) bloğu | `QRect(195, 78, 80, 38)` |
| 2 | Mesaj+İmza Birleştir | (+) sol birleştirici | `QRect(268, 108, 44, 44)` |
| 3 | AES-256-GCM Şifre | K_S(·) bloğu | `QRect(330, 90, 85, 38)` |
| 4 | RSA Anahtar Şifre | K_B^+(·) bloğu | `QRect(330, 155, 85, 38)` |
| 5 | Paket Gönderimi | Sağ (+) + Internet | `QRect(408, 118, 158, 62)` |

> **Not:** Koordinatlar ön tahmindir. Implementasyon sonrası görsel üzerinde piksel kalibrasyon yapılacak.

---

## Görsel Stil

| Öğe | Değer |
|-----|-------|
| Aktif kenarlık rengi | `#E53935` (kırmızı), 3px kalınlık |
| Aktif dolgu | `rgba(229, 57, 53, 64)` (%25 şeffaf kırmızı), `_blink_on=True` iken |
| Dolgu `_blink_on=False` | Şeffaf (kenarlık görünür kalır) |
| Tamamlanmış dolgu | `rgba(76, 175, 80, 51)` (%20 şeffaf yeşil), kenarlıksız |
| Blink interval | 1000 ms |
| Kapat butonu stili | Mevcut `theme.py` COLORS ile uyumlu, kırmızı kenarlıklı |

---

## Dosya Etki Alanı

| Dosya | Değişiklik |
|-------|-----------|
| `bob_panel.py` | `DiagramWidget` sınıfı + `BobPanel` metodları eklenir |
| `main_gui.py` | `_on_next_step()` alice fazına 5-6 satır eklenir |
| `alice and bob.png` | Sadece okunur, değişiklik yok |

---

## Kenar Durumları

- `alice and bob.png` bulunamazsa: `DiagramWidget` hata vermeden gizli kalır, konsola uyarı yazdırılır.
- Sıfırla (`_on_reset`) çağrıldığında: `_diagram_widget.setVisible(False)`, timer durdurulur, `_completed_steps` temizlenir.
- Pencere yeniden boyutlandırıldığında: `DiagramWidget` sabit 623×283 boyutunu korur, scroll area içinde değil layout'ta sabit tutulur.
