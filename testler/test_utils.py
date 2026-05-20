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
    - _truncate_hex: uzun hex string'i okunabilir biçimde kırpma kuralı
      (varsayılan 48 karakter + '…').
    - _build_step_content: StepResult tipini panellerde gösterilen
      anahtar–değer satırlarına dönüştürme; FRIENDLY_NAMES sözlüğü
      üzerinden her veri alanının kullanıcıya gösterilen Türkçe karşılığı.
    - TestFriendlyNamesCoverage: gerçek bir uçtan-uca akış çalıştırıp
      üretilen TÜM anahtarların FRIENDLY_NAMES'te tanımlı olduğunu
      kontrol eder — yeni alan eklenirse dictionary güncellemesi unutulmasın.

Strateji:
    - PyQt6 bağımlılığı vardır (utils üst düzeyinde theme.COLORS yüklenir).
      PyQt6 yoksa testler import aşamasında hata verir; bu mevcut test
      suite'iyle (test_crypto_core.py vb.) tutarlı davranıştır.

Hata durumunda anlamı: Kullanıcı arayüzünde çiğ anahtar adı (örn.
'session_key_b64') görünür ya da hata kartında yanlış başlık çıkar.
"""
import unittest

from cryptography.exceptions import InvalidSignature, InvalidTag

from kriptografi.crypto_core import StepResult
from kriptografi.utils import (
    FRIENDLY_NAMES,
    _build_step_content,
    _truncate_hex,
    format_crypto_exception,
)


class TestFormatCryptoException(unittest.TestCase):
    """format_crypto_exception() — beş dal için (title, body) çifti üretir."""

    def test_returns_tuple_of_two_strings(self) -> None:
        result = format_crypto_exception(InvalidTag())
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        title, body = result
        self.assertIsInstance(title, str)
        self.assertIsInstance(body, str)

    def test_invalid_tag_returns_decryption_title(self) -> None:
        """InvalidTag → AES-GCM kimlik doğrulama başarısız mesajı."""
        title, body = format_crypto_exception(InvalidTag())
        self.assertIn("Deşifreleme Başarısız", title)
        self.assertIn("AES-256-GCM", body)
        self.assertIn("InvalidTag", body)

    def test_invalid_signature_returns_signature_title(self) -> None:
        """InvalidSignature → imza doğrulanamadı mesajı."""
        title, body = format_crypto_exception(InvalidSignature())
        self.assertIn("İmza Doğrulanamadı", title)
        self.assertIn("InvalidSignature", body)

    def test_value_error_returns_format_title(self) -> None:
        """ValueError → paket format hatası, exc mesajı body'de yer almalı."""
        title, body = format_crypto_exception(ValueError("ayrıştırma çöktü"))
        self.assertIn("Paket Formatı", title)
        self.assertIn("ayrıştırma çöktü", body)
        self.assertIn("ValueError", body)

    def test_runtime_error_returns_flow_title(self) -> None:
        """RuntimeError → akış hatası, exc mesajı body'de yer almalı."""
        title, body = format_crypto_exception(RuntimeError("önkoşul kayıp"))
        self.assertIn("Akış Hatası", title)
        self.assertIn("önkoşul kayıp", body)
        self.assertIn("RuntimeError", body)

    def test_generic_exception_returns_unexpected_title(self) -> None:
        """Tanınmayan istisna → beklenmeyen hata dalı; teknik adı body'de."""
        title, body = format_crypto_exception(KeyError("foo"))
        self.assertIn("Beklenmeyen", title)
        self.assertIn("KeyError", body)

    def test_each_branch_includes_technical_class_name(self) -> None:
        """Her dalın body'sinde teknik istisna sınıf adı parantez içinde olmalı."""
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


class TestTruncateHex(unittest.TestCase):
    """_truncate_hex() — uzun hex değerlerini max_len + … şeklinde keser."""

    def test_short_string_unchanged(self) -> None:
        """Varsayılan eşik 48 karakter; 48 ve altında değişiklik yok."""
        s = "ab" * 24  # 48 karakter
        self.assertEqual(_truncate_hex(s), s)

    def test_short_string_no_ellipsis(self) -> None:
        s = "deadbeef"
        self.assertNotIn("…", _truncate_hex(s))

    def test_long_string_truncated_with_ellipsis(self) -> None:
        """100 karakter → ilk 48 + tek karakter ellipsis (49 toplam)."""
        s = "a" * 100
        result = _truncate_hex(s)
        self.assertEqual(len(result), 49)
        self.assertTrue(result.endswith("…"))
        self.assertTrue(result.startswith("a" * 48))

    def test_custom_max_len(self) -> None:
        """Özel max_len ile kesim noktası değişmeli."""
        s = "x" * 100
        result = _truncate_hex(s, max_len=10)
        self.assertEqual(len(result), 11)
        self.assertEqual(result, "x" * 10 + "…")

    def test_exact_boundary_length_unchanged(self) -> None:
        """Tam max_len kadar uzunlukta değişiklik olmamalı (kesin sınır)."""
        s = "a" * 48
        self.assertEqual(_truncate_hex(s), s)

    def test_one_over_boundary_is_truncated(self) -> None:
        """max_len+1 karakter → kesilir."""
        s = "a" * 49
        result = _truncate_hex(s)
        self.assertTrue(result.endswith("…"))
        self.assertEqual(len(result), 49)  # 48 + 1 ellipsis


class TestBuildStepContent(unittest.TestCase):
    """_build_step_content() — StepResult'ı kullanıcıya gösterilecek Türkçe metne çevirir."""

    def _make_step(self, data: dict, description: str = "Açıklama") -> StepResult:
        return StepResult(
            step_number=1,
            step_name="Test Adımı",
            description=description,
            data=data,
        )

    def test_description_appears_first(self) -> None:
        step = self._make_step({}, description="Bu adım çalıştı")
        content = _build_step_content(step)
        self.assertTrue(content.startswith("Bu adım çalıştı"))

    def test_friendly_name_used_when_available(self) -> None:
        """FRIENDLY_NAMES'de tanımlı anahtar Türkçe etiketle yazılmalı."""
        step = self._make_step({"hash_hex": "abc123"})
        content = _build_step_content(step)
        self.assertIn(FRIENDLY_NAMES["hash_hex"], content)
        self.assertIn("abc123", content)

    def test_raw_key_used_when_no_friendly_name(self) -> None:
        """FRIENDLY_NAMES'de olmayan bir anahtar ham haliyle gösterilmeli."""
        step = self._make_step({"custom_field": "deger"})
        content = _build_step_content(step)
        self.assertIn("custom_field", content)
        self.assertIn("deger", content)

    def test_bytes_suffix_keys_are_skipped(self) -> None:
        """_bytes ile biten anahtarlar (binary veri) UI'a sızmamalı."""
        step = self._make_step({
            "hash_bytes": b"\x01\x02\x03",
            "hash_hex": "010203",
        })
        content = _build_step_content(step)
        self.assertNotIn("hash_bytes", content)
        self.assertIn("010203", content)

    def test_verification_result_true_renders_checkmark(self) -> None:
        step = self._make_step({"verification_result": True})
        content = _build_step_content(step)
        self.assertIn("✅", content)
        self.assertIn("DOĞRULANDI", content)

    def test_verification_result_false_renders_cross(self) -> None:
        step = self._make_step({"verification_result": False})
        content = _build_step_content(step)
        self.assertIn("❌", content)
        self.assertIn("DOĞRULANAMADI", content)

    def test_long_string_values_are_truncated(self) -> None:
        """64 karakterden uzun string değerler kısaltılmalı."""
        long_hex = "a" * 200
        step = self._make_step({"signature_hex": long_hex})
        content = _build_step_content(step)
        self.assertIn("…", content)
        # Tüm 200 karakter satıra düşmemeli
        self.assertNotIn("a" * 100, content)

    def test_short_string_values_not_truncated(self) -> None:
        """64 karakter ve altında değer değişmemeli."""
        short_val = "abc"
        step = self._make_step({"key_info": short_val})
        content = _build_step_content(step)
        self.assertIn(short_val, content)
        self.assertNotIn("…", content)

    def test_non_string_values_rendered_as_is(self) -> None:
        """int veya bool gibi non-string değerler doğrudan str() ile yazılmalı."""
        step = self._make_step({"message_size": 1024})
        content = _build_step_content(step)
        self.assertIn("1024", content)

    def test_empty_data_renders_only_description(self) -> None:
        step = self._make_step({}, description="Boş adım")
        content = _build_step_content(step)
        # Açıklama + boş satır (description sonrası "")
        self.assertEqual(content.strip(), "Boş adım")


class TestFriendlyNamesCoverage(unittest.TestCase):
    """FRIENDLY_NAMES sözlüğü — alice_send / bob_receive'in ürettiği her
    anahtar için bir Türkçe karşılık olmalı."""

    def test_all_step_data_keys_have_friendly_names(self) -> None:
        """Tam iş akışı sonucunda üretilen anahtarların hepsi sözlükte
        tanımlı olmalı; aksi hâlde UI'da çiğ anahtar adı görünür."""
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
