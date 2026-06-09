"""
test_utils.py — kriptografi/utils modülü birim testleri
====================================================

Test türü: BİRİM TESTİ (Unit Test)

Amaç:
    kriptografi/utils.py yardımcı fonksiyonlarının izole davranışını sınar.
    Bu fonksiyonlar üretici (Alice/Bob) panellerinde adım sonuçlarını
    okunaklı kullanıcı metinlerine çevirir; hata olursa kullanıcı
    yanıltıcı bilgi görür.

Kapsam:
    - format_crypto_exception: 5 istisna dalı (InvalidSignature, InvalidTag,
      ValueError, RuntimeError, jenerik Exception) için doğru başlık + gövde.
    - constant_time_equal: sabit-zamanlı eşitlik (hmac.compare_digest).
    - TestFriendlyNamesCoverage: gerçek bir uçtan-uca akış çalıştırıp
      üretilen TÜM anahtarların FRIENDLY_NAMES'te tanımlı olduğunu
      kontrol eder — yeni alan eklenirse dictionary güncellemesi unutulmasın.

    Not: Qt'ye bağımlı GUI yardımcılarının (truncate_hex, build_step_content)
    testleri test_widget_utils.py dosyasına taşınmıştır.

Strateji:
    - Bu modül artık Qt-bağımsızdır; kriptografi/utils.py PyQt6'ya
      bağımlı değildir. (GUI testleri test_widget_utils.py'dedir.)

Hata durumunda anlamı: Kullanıcı arayüzünde çiğ anahtar adı (örn.
'session_key_b64') görünür ya da hata kartında yanlış başlık çıkar.
"""
import unittest

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
    VerifyError,
)
from kriptografi.utils import (
    FRIENDLY_NAMES,
    constant_time_equal,
    format_crypto_exception,
)


class TestFormatCryptoException(unittest.TestCase):
    """format_crypto_exception() — beş dal için (title, body) çifti üretir."""

    def test_returns_tuple_of_two_strings(self) -> None:
        """Alt tür: BİRİM — tip kontratı — (title, body) string tuple."""
        result = format_crypto_exception(InvalidTag())
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        title, body = result
        self.assertIsInstance(title, str)
        self.assertIsInstance(body, str)

    def test_invalid_tag_returns_decryption_title(self) -> None:
        """Alt tür: BİRİM — InvalidTag → AES-GCM deşifreleme dalı.

        InvalidTag → AES-GCM kimlik doğrulama başarısız mesajı.
        """
        title, body = format_crypto_exception(InvalidTag())
        self.assertIn("Deşifreleme Başarısız", title)
        self.assertIn("AES-256-GCM", body)
        self.assertIn("InvalidTag", body)

    def test_invalid_signature_returns_signature_title(self) -> None:
        """Alt tür: BİRİM — InvalidSignature → imza doğrulama dalı.

        InvalidSignature → imza doğrulanamadı mesajı.
        """
        title, body = format_crypto_exception(InvalidSignature())
        self.assertIn("İmza Doğrulanamadı", title)
        self.assertIn("InvalidSignature", body)

    def test_value_error_returns_format_title(self) -> None:
        """Alt tür: BİRİM — ValueError → paket format dalı + exc mesajı.

        ValueError → paket format hatası, exc mesajı body'de yer almalı.
        """
        title, body = format_crypto_exception(ValueError("ayrıştırma çöktü"))
        self.assertIn("Paket Formatı", title)
        self.assertIn("ayrıştırma çöktü", body)
        self.assertIn("ValueError", body)

    def test_runtime_error_returns_flow_title(self) -> None:
        """Alt tür: BİRİM — RuntimeError → akış hatası dalı + exc mesajı.

        RuntimeError → akış hatası, exc mesajı body'de yer almalı.
        """
        title, body = format_crypto_exception(RuntimeError("önkoşul kayıp"))
        self.assertIn("Akış Hatası", title)
        self.assertIn("önkoşul kayıp", body)
        self.assertIn("RuntimeError", body)

    def test_generic_exception_returns_unexpected_title(self) -> None:
        """Alt tür: BİRİM — tanınmayan exc → beklenmeyen dal.

        Tanınmayan istisna → beklenmeyen hata dalı; teknik adı body'de.
        """
        title, body = format_crypto_exception(KeyError("foo"))
        self.assertIn("Beklenmeyen", title)
        self.assertIn("KeyError", body)

    def test_each_branch_includes_technical_class_name(self) -> None:
        """Alt tür: BİRİM — her dalda '(Teknik: ClassName)' satırı.

        Her dalın body'sinde teknik istisna sınıf adı parantez içinde olmalı.
        """
        for exc, expected_name in [
            (InvalidTag(), "InvalidTag"),
            (InvalidSignature(), "InvalidSignature"),
            (ValueError("x"), "ValueError"),
            (RuntimeError("x"), "RuntimeError"),
            (TypeError("x"), "TypeError"),
        ]:
            with self.subTest(exc_type=type(exc).__name__):
                _, body = format_crypto_exception(exc)
                self.assertIn(f"(Teknik: {expected_name})", body)


class TestFormatTypedCryptoException(unittest.TestCase):
    """format_crypto_exception() — tipli CryptoError ailesini Türkçe'ye çevirir."""

    def test_replay_detected_translation(self) -> None:
        """Alt tür: BİRİM — ReplayDetectedError → replay Türkçe metni."""
        title, body = format_crypto_exception(ReplayDetectedError())
        self.assertIn("Replay", title)
        self.assertIn("replay saldırısı tespit edildi", body)
        self.assertIn("ReplayDetectedError", body)

    def test_stale_timestamp_translation(self) -> None:
        """Alt tür: BİRİM — StaleTimestampError → zaman damgası Türkçe metni."""
        title, body = format_crypto_exception(StaleTimestampError())
        self.assertIn("Zaman Damgası", title)
        self.assertIn("kabul edilebilir aralığın dışında", body)
        self.assertIn("StaleTimestampError", body)

    def test_integrity_error_translation(self) -> None:
        """Alt tür: BİRİM — IntegrityError → bütünlük dalı + exc mesajı."""
        title, body = format_crypto_exception(IntegrityError("tag uyuşmadı"))
        self.assertIn("Bütünlük", title)
        self.assertIn("tag uyuşmadı", body)
        self.assertIn("IntegrityError", body)

    def test_verify_error_translation(self) -> None:
        """Alt tür: BİRİM — VerifyError → imza doğrulama dalı."""
        title, body = format_crypto_exception(VerifyError("imza geçersiz"))
        self.assertIn("İmza Doğrulanamadı", title)
        self.assertIn("imza geçersiz", body)
        self.assertIn("VerifyError", body)

    def test_decrypt_error_translation(self) -> None:
        """Alt tür: BİRİM — DecryptError → çözme dalı."""
        title, body = format_crypto_exception(DecryptError("OAEP başarısız"))
        self.assertIn("Çözme Başarısız", title)
        self.assertIn("OAEP başarısız", body)
        self.assertIn("DecryptError", body)

    def test_encrypt_error_translation(self) -> None:
        """Alt tür: BİRİM — EncryptError → şifreleme dalı."""
        title, body = format_crypto_exception(EncryptError("şifreleme hatası"))
        self.assertIn("Şifreleme Başarısız", title)
        self.assertIn("EncryptError", body)

    def test_sign_error_translation(self) -> None:
        """Alt tür: BİRİM — SignError → imzalama dalı."""
        title, body = format_crypto_exception(SignError("imza üretilemedi"))
        self.assertIn("İmzalama Başarısız", title)
        self.assertIn("SignError", body)

    def test_keygen_error_translation(self) -> None:
        """Alt tür: BİRİM — KeygenError → anahtar üretimi dalı."""
        title, body = format_crypto_exception(KeygenError("anahtar üretilemedi"))
        self.assertIn("Anahtar Üretimi", title)
        self.assertIn("KeygenError", body)

    def test_packet_format_error_translation(self) -> None:
        """Alt tür: BİRİM — PacketFormatError → paket format dalı + exc mesajı."""
        title, body = format_crypto_exception(PacketFormatError("paket kısa"))
        self.assertIn("Paket Formatı", title)
        self.assertIn("paket kısa", body)
        self.assertIn("PacketFormatError", body)

    def test_unknown_crypto_error_falls_back_to_root(self) -> None:
        """Alt tür: SINIR KOŞULU — tanımsız CryptoError alt tipi → kök dal.

        Hiyerarşiye sonradan eklenmiş ama özel dalı olmayan bir
        CryptoError alt tipi yine de kök 'Kriptografik Hata' dalına düşmeli.
        """
        class CustomCryptoError(CryptoError):
            pass

        title, body = format_crypto_exception(CustomCryptoError("özel"))
        self.assertIn("Kriptografik Hata", title)
        self.assertIn("CustomCryptoError", body)

    def test_typed_branches_include_technical_name(self) -> None:
        """Alt tür: BİRİM — tipli dallarda '(Teknik: ClassName)' satırı."""
        for exc, name in [
            (ReplayDetectedError(), "ReplayDetectedError"),
            (StaleTimestampError(), "StaleTimestampError"),
            (IntegrityError("x"), "IntegrityError"),
            (VerifyError("x"), "VerifyError"),
            (DecryptError("x"), "DecryptError"),
            (PacketFormatError("x"), "PacketFormatError"),
            (KeygenError("x"), "KeygenError"),
        ]:
            with self.subTest(exc_type=name):
                _, body = format_crypto_exception(exc)
                self.assertIn(f"(Teknik: {name})", body)


class TestConstantTimeEqual(unittest.TestCase):
    """constant_time_equal() — sabit-zamanlı eşitlik (hmac.compare_digest).

    Mesaj/hash karşılaştırması zamanlama yan-kanalına kapatılır; davranış
    (eşit→True, farklı→False) düz '==' ile aynı kalmalıdır.
    """

    def test_same_string_true(self) -> None:
        """Alt tür: BİRİM — aynı string → True."""
        self.assertTrue(constant_time_equal("merhaba", "merhaba"))

    def test_different_string_false(self) -> None:
        """Alt tür: BİRİM — farklı string → False."""
        self.assertFalse(constant_time_equal("merhaba", "merhab4"))

    def test_same_bytes_true(self) -> None:
        """Alt tür: BİRİM — aynı bytes → True."""
        self.assertTrue(constant_time_equal(b"\x01\x02\x03", b"\x01\x02\x03"))

    def test_different_bytes_false(self) -> None:
        """Alt tür: BİRİM — farklı bytes → False."""
        self.assertFalse(constant_time_equal(b"\x01\x02\x03", b"\x01\x02\x04"))

    def test_turkish_same_string_true(self) -> None:
        """Alt tür: BİRİM — Türkçe karakter içeren aynı string → True.

        utf-8 kodlaması ş/ğ/ı/ç/ö/ü içeren eşit metinlerde True döndürmeli.
        """
        s = "şifreli ğıçöü mesaj"
        self.assertTrue(constant_time_equal(s, s))

    def test_turkish_single_char_diff_false(self) -> None:
        """Alt tür: SINIR KOŞULU — Türkçe metinde tek karakter farkı → False.

        Yalnızca bir Türkçe karakter değişince (ş→s) eşitlik bozulmalı;
        unicode/utf-8 byte düzeyinde doğru karşılaştırılır.
        """
        self.assertFalse(
            constant_time_equal("şifreli mesaj", "sifreli mesaj")
        )

    def test_empty_strings_true(self) -> None:
        """Alt tür: SINIR KOŞULU — iki boş string → True."""
        self.assertTrue(constant_time_equal("", ""))

    def test_returns_bool(self) -> None:
        """Alt tür: BİRİM — dönüş tipi bool olmalı."""
        self.assertIsInstance(constant_time_equal("a", "a"), bool)


class TestFriendlyNamesCoverage(unittest.TestCase):
    """FRIENDLY_NAMES sözlüğü — alice_send / bob_receive'in ürettiği her
    anahtar için bir Türkçe karşılık olmalı."""

    def test_all_step_data_keys_have_friendly_names(self) -> None:
        """Alt tür: ENTEGRASYON — tam akış sonucu tüm anahtarlar FRIENDLY_NAMES'de.

        Tam iş akışı sonucunda üretilen anahtarların hepsi sözlükte
        tanımlı olmalı; aksi hâlde UI'da çiğ anahtar adı görünür.
        """
        from kriptografi.crypto_core import CryptoCore
        crypto = CryptoCore()
        crypto.setup_keys()
        _, alice_steps = crypto.alice_send("merhaba")
        _, _, bob_steps = crypto.bob_receive(
            crypto.alice_send("merhaba")[0]
        )

        missing: set[str] = set()
        for step in alice_steps + bob_steps:
            for key in step.data:
                if key.endswith("_bytes"):
                    continue  # binary alanlar UI'da gösterilmez
                if key not in FRIENDLY_NAMES:
                    missing.add(key)

        self.assertEqual(
            missing, set(),
            f"FRIENDLY_NAMES'de tanımsız adım anahtarları: {missing}"
        )


if __name__ == "__main__":
    unittest.main()
