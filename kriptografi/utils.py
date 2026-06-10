"""
utils.py – Yardımcı Fonksiyonlar ve Sabitler

Yalnızca Qt-bağımsız kripto yardımcılarını barındırır: kripto istisna
çevirisi (``format_crypto_exception``), kullanıcı dostu alan adları
(``FRIENDLY_NAMES``) ve sabit-zamanlı karşılaştırma (``constant_time_equal``).

GUI'ye (PyQt6) bağımlı yardımcılar ``arayuz/widget_utils.py`` modülüne
taşınmıştır; bu sayede ``kriptografi`` paketi Qt yüklü olmayan saf Python
ortamında da içe aktarılabilir.
"""
from __future__ import annotations

from hmac import compare_digest
from typing import NamedTuple

from cryptography.exceptions import InvalidSignature, InvalidTag

from kriptografi.errors import (
    CryptoError,
    DecryptError,
    EncryptError,
    IntegrityError,
    KeygenError,
    PacketFormatError,
    ReplayDetectedError,
    SignError,
    StaleTimestampError,
)

FRIENDLY_NAMES: dict[str, str] = {
    "nonce_hex":              "Rastgele Sayı (Nonce)",
    "session_key_hex":        "Oturum Anahtarı (K_S)",
    "hash_hex":               "SHA-256 Özet Değeri H(m)",
    "signature_hex":          "Dijital İmza",
    "encrypted_key_hex":      "RSA Şifreli Oturum Anahtarı",
    "ciphertext_hex_preview": "Şifreli Mesaj (Önizleme)",
    "verification_result":    "Doğrulama Sonucu",
    "key_info":               "Kullanılan Anahtar",
    "combined_size":          "Birleşik Veri Boyutu",
    "message_size":           "Mesaj Boyutu",
    "signature_size":         "İmza Boyutu",
    "ciphertext_size":        "Şifreli Veri Boyutu",
    "encrypted_key_size":     "RSA Şifreli Anahtar Boyutu",
    "total_packet_size":      "Toplam Paket Boyutu",
    "associated_data":        "AAD (Authenticated Metadata)",
    "associated_data_size":   "AAD Boyutu",
    "message":                "Mesaj İçeriği",
    "elapsed_ms":             "İşlem Süresi",
}


def constant_time_equal(a, b) -> bool:
    """Sabit-zamanlı eşitlik kontrolü. Zamanlama yan-kanalı (timing
    side-channel) saldırılarına karşı koruma sağlar. str → utf-8 bytes."""
    if isinstance(a, str):
        a = a.encode("utf-8")
    if isinstance(b, str):
        b = b.encode("utf-8")
    return compare_digest(a, b)


def format_crypto_exception(exc: BaseException) -> tuple[str, str]:
    """Kriptografik istisnayı kullanıcıya gösterilecek (başlık, gövde) metnine çevirir.

    UI katmanı yakaladığı her Exception'ı doğrudan `str(exc)` olarak
    göstermek yerine bu çevirmeni kullanmalıdır. Böylece:
      - Kullanıcıya anlaşılır Türkçe bir neden verilir.
      - Tekniği merak eden için orijinal istisna adı parantez içinde
        eklenir (sessiz bilgi kaybı olmaz).
      - Teknik detaylar tek bir yerden güncellenir.

    Dönüş: (başlık, gövde) — QMessageBox.critical gibi yerlerde
    doğrudan kullanılabilir.
    """
    exc_name = type(exc).__name__

    # --- Tipli kripto hiyerarşisi (CryptoError) — ham kütüphane
    # istisnalarından önce kontrol edilir, çünkü artık çekirdek bunları
    # fırlatıyor. ---

    if isinstance(exc, ReplayDetectedError):
        return (
            "Replay Saldırısı Tespit Edildi",
            "Bu paket daha önce alınmış (replay saldırısı tespit edildi).\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, StaleTimestampError):
        return (
            "Zaman Damgası Geçersiz",
            "Paketin zaman damgası kabul edilebilir aralığın dışında.\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, IntegrityError):
        return (
            "Bütünlük Doğrulanamadı",
            "Paketin bütünlüğü/kimlik doğrulaması başarısız oldu. "
            "AES-256-GCM etiketi (tag) uyuşmadı ya da özet (H(m)) "
            "beklenen formatta değil.\n\n"
            "  • Şifreli mesaj, nonce veya AAD iletim sırasında "
            "değiştirilmiş olabilir.\n"
            "  • Oturum anahtarı uyuşmuyor olabilir.\n\n"
            "Bu tasarlanmış bir güvenlik davranışıdır.\n\n"
            f"Detay: {exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, DecryptError):
        return (
            "Çözme Başarısız",
            "Şifreli veri çözülemedi. RSA-OAEP ile sarılmış oturum "
            "anahtarı bozulmuş ya da yanlış gizli anahtarla çözülmeye "
            "çalışılmış olabilir.\n\n"
            f"Detay: {exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, EncryptError):
        return (
            "Şifreleme Başarısız",
            "Şifreleme işlemi tamamlanamadı.\n\n"
            f"Detay: {exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, SignError):
        return (
            "İmzalama Başarısız",
            "Dijital imza üretilemedi.\n\n"
            f"Detay: {exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, KeygenError):
        return (
            "Anahtar Üretimi Başarısız",
            "RSA anahtar çifti üretilemedi.\n\n"
            f"Detay: {exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, PacketFormatError):
        return (
            "Paket Formatı Hatası",
            "Şifreli paketteki bir alan beklenen formatta değil. "
            "Birleşik veri (mesaj ‖ imza) beklenen 256 byte'lık imza "
            "alanını taşıyamayacak kadar kısa ya da sürüm/uzunluk "
            "beklentisi ihlal edilmiş olabilir.\n\n"
            f"Detay: {exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    # Yeni tanımlanmamış bir CryptoError alt tipi gelirse yine de
    # kök sınıfa düşülerek anlamlı bir mesaj verilir.
    if isinstance(exc, CryptoError):
        return (
            "Kriptografik Hata",
            f"Kriptografik işlem sırasında bir hata oluştu:\n\n{exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, InvalidTag):
        return (
            "Deşifreleme Başarısız — Kimlik Doğrulama Hatası",
            "AES-256-GCM kimlik doğrulama etiketi (tag) doğrulanamadı. "
            "Bu genellikle şu sebeplerden biriyle olur:\n\n"
            "  • Şifreli mesaj, nonce veya AAD (authenticated metadata) "
            "iletim sırasında değiştirilmiş olabilir.\n"
            "  • Bob'un çözdüğü oturum anahtarı ile Alice'in kullandığı "
            "anahtar uyuşmuyor olabilir.\n\n"
            "Paketin bütünlüğü bozulduğu için içerik güvenle "
            "çözülemez — bu tasarlanmış güvenlik davranışıdır.\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, InvalidSignature):
        return (
            "İmza Doğrulanamadı",
            "Dijital imza, Alice'in açık anahtarıyla doğrulanamadı. "
            "Olası nedenler:\n\n"
            "  • Mesaj imzalandıktan sonra değiştirilmiş.\n"
            "  • İmza, başka bir gizli anahtarla üretilmiş.\n"
            "  • İmzanın bağlı olduğu özet (H(m)) farklı bir mesaja ait.\n\n"
            "Kimlik veya bütünlük doğrulanamadığı için mesaj "
            "kabul edilmemelidir.\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, ValueError):
        # OAEP çözme hatası, uzunluk kontrolü, vb. — genellikle veri
        # formatı bozukluğu.
        return (
            "Paket Formatı Hatası",
            "Şifreli paketteki bir alan beklenen formatta değil. "
            "Olası nedenler:\n\n"
            "  • RSA-OAEP ile sarılmış oturum anahtarı bozulmuş ya da "
            "yanlış gizli anahtarla çözülmeye çalışılmış olabilir.\n"
            "  • Birleşik veri (mesaj ‖ imza) beklenen 256 byte'lık "
            "imza alanını taşıyamayacak kadar kısa olabilir.\n\n"
            f"Detay: {exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    if isinstance(exc, RuntimeError):
        return (
            "Akış Hatası",
            f"İşlem akışı bir önkoşulu karşılamadı:\n\n{exc}\n\n"
            f"(Teknik: {exc_name})"
        )

    # Beklenmeyen tipte istisna — yine de kullanıcıya bir şey göster.
    return (
        "Beklenmeyen Hata",
        f"İşlem sırasında ele alınmamış bir hata oluştu:\n\n{exc}\n\n"
        f"(Teknik: {exc_name})"
    )


class CryptoExplanation(NamedTuple):
    """Bir kripto istisnasının öğrenci diline çevrilmiş, 3 bölümlü açıklaması.

    UI diyaloğu (``CryptoErrorDialog``) bu yapıyı doğrudan render eder:
      * ``title``     → kısa özet (başlık)
      * ``meaning``   → "Bu ne demek?" (pedagojik açıklama)
      * ``action``    → "Ne yapabilirim?" (öneri)
      * ``technical`` → açılır teknik detay (istisna adı + ham mesaj)
    """

    title: str
    meaning: str
    action: str
    technical: str


# İstisna tipi → (başlık, "bu ne demek", "ne yapabilirim"). isinstance
# sırasıyla en özelden genele kontrol edilir. Teknik detay ayrıca eklenir.
def explain_crypto_exception(exc: BaseException) -> CryptoExplanation:
    """Kripto istisnasını 3 bölümlü pedagojik açıklamaya çevirir.

    ``format_crypto_exception`` tek bir (başlık, gövde) verir; bu fonksiyon
    aynı bilgiyi öğrenciye yönelik üç ayrı bölüme ayırır ve teknik detayı
    açılır gösterim için ayrı tutar.
    """
    technical = f"{type(exc).__name__}: {exc}"

    if isinstance(exc, ReplayDetectedError):
        return CryptoExplanation(
            "Replay Saldırısı Tespit Edildi",
            "Bu paket daha önce alınmıştı. Sistem, aynı (gönderen parmak izi, "
            "nonce) çiftini ikinci kez görünce bunu bir tekrar (replay) "
            "saldırısı olarak işaretler; saldırgan, daha önce yakaladığı "
            "geçerli bir paketi olduğu gibi yeniden gönderebilir.",
            "Bu, tasarlanmış bir güvenlik davranışıdır. Taze bir paket (yeni "
            "nonce ve zaman damgası) üretmek için yeni bir mesaj gönderin.",
            technical,
        )

    if isinstance(exc, StaleTimestampError):
        return CryptoExplanation(
            "Zaman Damgası Geçersiz",
            "Paketin AAD'sindeki Unix zaman damgası, kabul edilebilir tazelik "
            "penceresinin dışında. Çok eski (ya da geleceğe ait) paketler, "
            "tekrar/oynatma riskini azaltmak için reddedilir.",
            "Sistem saatinin doğru olduğundan emin olun ve mesajı yeniden "
            "gönderin.",
            technical,
        )

    if isinstance(exc, IntegrityError):
        return CryptoExplanation(
            "Bütünlük Doğrulanamadı",
            "AES-256-GCM kimlik doğrulama etiketi (tag) uyuşmadı veya özet "
            "beklenen biçimde değil. Bu, şifreli mesajın, nonce'ın ya da "
            "AAD'nin iletim sırasında değiştirildiği veya çözen taraftaki "
            "oturum anahtarının (K_S) farklı olduğu anlamına gelir.",
            "Bu tasarlanmış bir güvenlik davranışıdır; bütünlüğü bozulmuş bir "
            "paket güvenle çözülemez. Paketin değiştirilmediğinden emin olun.",
            technical,
        )

    if isinstance(exc, DecryptError):
        return CryptoExplanation(
            "Çözme Başarısız",
            "RSA-OAEP ile sarılmış oturum anahtarı (K_S) çözülemedi. Bu "
            "genellikle ek alanının iletimde bozulduğu ya da yanlış gizli "
            "anahtarla çözülmeye çalışıldığı durumlarda olur.",
            "Doğru anahtar çiftini ve değiştirilmemiş bir paket kullandığınızdan "
            "emin olun, sonra yeniden deneyin.",
            technical,
        )

    if isinstance(exc, PacketFormatError):
        return CryptoExplanation(
            "Paket Formatı Hatası",
            "Şifreli paketteki bir alan beklenen formatta değil. Örneğin "
            "birleşik veri (mesaj ‖ imza), 256 byte'lık imza alanını "
            "taşıyamayacak kadar kısa olabilir ya da AAD'nin sürüm/uzunluk "
            "beklentisi ihlal edilmiş olabilir.",
            "Paketin eksiksiz ve değiştirilmemiş olduğundan emin olun; gerekirse "
            "mesajı yeniden oluşturup gönderin.",
            technical,
        )

    if isinstance(exc, (SignError, EncryptError, KeygenError)):
        op = {
            "SignError": "Dijital imza üretimi",
            "EncryptError": "Şifreleme işlemi",
            "KeygenError": "RSA anahtar çifti üretimi",
        }[type(exc).__name__]
        return CryptoExplanation(
            f"{op} Başarısız",
            f"{op} tamamlanamadı. Bu adım, çekirdek kripto kütüphanesinin "
            "(cryptography) beklenen çıktıyı üretememesi durumunda oluşur.",
            "İşlemi yeniden deneyin; sorun sürerse Python/cryptography kurulumunu "
            "ve sistem ortamını kontrol edin.",
            technical,
        )

    # Bilinmeyen CryptoError alt tipi ya da ham istisnalar: mevcut tek-parça
    # çevirmenin gövdesini "bu ne demek" bölümüne koy, genel öneri ver.
    title, body = format_crypto_exception(exc)
    return CryptoExplanation(
        title,
        body,
        "İşlemi yeniden deneyin; sorun sürerse paketin ve anahtarların "
        "doğruluğunu kontrol edin.",
        technical,
    )
