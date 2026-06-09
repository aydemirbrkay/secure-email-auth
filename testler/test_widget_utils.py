"""
test_widget_utils.py — arayuz/widget_utils modülü birim testleri
=================================================================

Test türü: BİRİM TESTİ (Unit Test)

Amaç:
    arayuz/widget_utils.py içindeki Qt'ye bağımlı GUI yardımcılarının
    izole davranışını sınar. Bu fonksiyonlar üretici (Alice/Bob)
    panellerinde adım sonuçlarını okunaklı kullanıcı metinlerine çevirir;
    hata olursa kullanıcı yanıltıcı bilgi görür.

Kapsam:
    - truncate_hex: uzun hex string'i okunabilir biçimde kırpma kuralı
      (varsayılan 48 karakter + '…').
    - build_step_content: StepResult tipini panellerde gösterilen
      anahtar–değer satırlarına dönüştürme; FRIENDLY_NAMES sözlüğü
      üzerinden her veri alanının kullanıcıya gösterilen Türkçe karşılığı.

Strateji:
    - PyQt6 bağımlılığı vardır (widget_utils üst düzeyinde theme.COLORS
      ve QtWidgets yüklenir). PyQt6 yoksa testler import aşamasında hata
      verir; bu mevcut test suite'iyle tutarlı davranıştır.

Hata durumunda anlamı: Kullanıcı arayüzünde çiğ anahtar adı (örn.
'session_key_b64') görünür ya da uzun hex değerleri kutuya sığmaz.
"""
import unittest

from kriptografi.crypto_core import StepResult, StepType
from kriptografi.utils import FRIENDLY_NAMES
from arayuz.widget_utils import (
    build_step_content,
    png_icon_pixmap,
    svg_pixmap,
    truncate_hex,
)


class TestTruncateHex(unittest.TestCase):
    """truncate_hex() — uzun hex değerlerini max_len + … şeklinde keser."""

    def test_short_string_unchanged(self) -> None:
        """Alt tür: BİRİM — ≤ 48 karakter değişmez.

        Varsayılan eşik 48 karakter; 48 ve altında değişiklik yok.
        """
        s = "ab" * 24  # 48 karakter
        self.assertEqual(truncate_hex(s), s)

    def test_short_string_no_ellipsis(self) -> None:
        """Alt tür: BİRİM — kısa string'de '…' yok."""
        s = "deadbeef"
        self.assertNotIn("…", truncate_hex(s))

    def test_long_string_truncated_with_ellipsis(self) -> None:
        """Alt tür: BİRİM — 100 karakter → 48 + '…' = 49.

        100 karakter → ilk 48 + tek karakter ellipsis (49 toplam).
        """
        s = "a" * 100
        result = truncate_hex(s)
        self.assertEqual(len(result), 49)
        self.assertTrue(result.endswith("…"))
        self.assertTrue(result.startswith("a" * 48))

    def test_custom_max_len(self) -> None:
        """Alt tür: BİRİM — özel max_len parametresi.

        Özel max_len ile kesim noktası değişmeli.
        """
        s = "x" * 100
        result = truncate_hex(s, max_len=10)
        self.assertEqual(len(result), 11)
        self.assertEqual(result, "x" * 10 + "…")

    def test_exact_boundary_length_unchanged(self) -> None:
        """Alt tür: SINIR KOŞULU — tam 48 karakter — kesin sınır.

        Tam max_len kadar uzunlukta değişiklik olmamalı (kesin sınır).
        """
        s = "a" * 48
        self.assertEqual(truncate_hex(s), s)

    def test_one_over_boundary_is_truncated(self) -> None:
        """Alt tür: SINIR KOŞULU — 49 karakter — sınırın 1 üstü kesilir.

        max_len+1 karakter → kesilir.
        """
        s = "a" * 49
        result = truncate_hex(s)
        self.assertTrue(result.endswith("…"))
        self.assertEqual(len(result), 49)  # 48 + 1 ellipsis


class TestBuildStepContent(unittest.TestCase):
    """build_step_content() — StepResult'ı kullanıcıya gösterilecek Türkçe metne çevirir."""

    def _make_step(self, data: dict, description: str = "Açıklama") -> StepResult:
        return StepResult(
            step_number=1,
            step_name="Test Adımı",
            description=description,
            step_type=StepType.HASH,
            data=data,
        )

    def test_description_appears_first(self) -> None:
        """Alt tür: BİRİM — description çıktının başında."""
        step = self._make_step({}, description="Bu adım çalıştı")
        content = build_step_content(step)
        self.assertTrue(content.startswith("Bu adım çalıştı"))

    def test_friendly_name_used_when_available(self) -> None:
        """Alt tür: BİRİM — FRIENDLY_NAMES'de varsa Türkçe etiket.

        FRIENDLY_NAMES'de tanımlı anahtar Türkçe etiketle yazılmalı.
        """
        step = self._make_step({"hash_hex": "abc123"})
        content = build_step_content(step)
        self.assertIn(FRIENDLY_NAMES["hash_hex"], content)
        self.assertIn("abc123", content)

    def test_raw_key_used_when_no_friendly_name(self) -> None:
        """Alt tür: BİRİM — FRIENDLY_NAMES'de yoksa ham anahtar.

        FRIENDLY_NAMES'de olmayan bir anahtar ham haliyle gösterilmeli.
        """
        step = self._make_step({"custom_field": "deger"})
        content = build_step_content(step)
        self.assertIn("custom_field", content)
        self.assertIn("deger", content)

    def test_bytes_suffix_keys_are_skipped(self) -> None:
        """Alt tür: BİRİM — binary alanlar (_bytes) UI'a sızmaz.

        _bytes ile biten anahtarlar (binary veri) UI'a sızmamalı.
        """
        step = self._make_step({
            "hash_bytes": b"\x01\x02\x03",
            "hash_hex": "010203",
        })
        content = build_step_content(step)
        self.assertNotIn("hash_bytes", content)
        self.assertIn("010203", content)

    def test_verification_result_true_renders_checkmark(self) -> None:
        """Alt tür: BİRİM — True → ✅ DOĞRULANDI."""
        step = self._make_step({"verification_result": True})
        content = build_step_content(step)
        self.assertIn("✅", content)
        self.assertIn("DOĞRULANDI", content)

    def test_verification_result_false_renders_cross(self) -> None:
        """Alt tür: BİRİM — False → ❌ DOĞRULANAMADI."""
        step = self._make_step({"verification_result": False})
        content = build_step_content(step)
        self.assertIn("❌", content)
        self.assertIn("DOĞRULANAMADI", content)

    def test_long_string_values_are_truncated(self) -> None:
        """Alt tür: BİRİM — uzun string değerler '…' ile kesilir.

        64 karakterden uzun string değerler kısaltılmalı.
        """
        long_hex = "a" * 200
        step = self._make_step({"signature_hex": long_hex})
        content = build_step_content(step)
        self.assertIn("…", content)
        # Tüm 200 karakter satıra düşmemeli
        self.assertNotIn("a" * 100, content)

    def test_short_string_values_not_truncated(self) -> None:
        """Alt tür: BİRİM — kısa string değerler değişmez.

        64 karakter ve altında değer değişmemeli.
        """
        short_val = "abc"
        step = self._make_step({"key_info": short_val})
        content = build_step_content(step)
        self.assertIn(short_val, content)
        self.assertNotIn("…", content)

    def test_non_string_values_rendered_as_is(self) -> None:
        """Alt tür: BİRİM — int/bool → str() ile yazılır.

        int veya bool gibi non-string değerler doğrudan str() ile yazılmalı.
        """
        step = self._make_step({"message_size": 1024})
        content = build_step_content(step)
        self.assertIn("1024", content)

    def test_empty_data_renders_only_description(self) -> None:
        """Alt tür: SINIR KOŞULU — boş data → sadece description."""
        step = self._make_step({}, description="Boş adım")
        content = build_step_content(step)
        # Açıklama + boş satır (description sonrası "")
        self.assertEqual(content.strip(), "Boş adım")


class TestAssetLoadLogging(unittest.TestCase):
    """Eksik görsel yüklemesi exception fırlatmaz; logger.warning ile bildirilir."""

    def test_svg_missing_file_logs_warning_no_raise(self) -> None:
        """Alt tür: HATA DURUMU — olmayan SVG → warning loglanır, pixmap döner.

        Üretim kodunda print yerine logging kullanıldığının kanıtı: hatalı
        yükleme sessizce değil, WARNING seviyesinde kayda geçer.
        """
        with self.assertLogs("arayuz.widget_utils", level="WARNING") as cm:
            pix = svg_pixmap("__yok__.svg", "#ffffff", size=16)
        self.assertFalse(pix.isNull())  # şeffaf placeholder pixmap döner
        self.assertTrue(any("__yok__.svg" in msg for msg in cm.output))

    def test_png_missing_file_logs_warning_no_raise(self) -> None:
        """Alt tür: HATA DURUMU — olmayan PNG → warning loglanır, raise yok."""
        with self.assertLogs("arayuz.widget_utils", level="WARNING") as cm:
            png_icon_pixmap("__yok__.png", "#ffffff", size=16)
        self.assertTrue(any("__yok__.png" in msg for msg in cm.output))


if __name__ == "__main__":
    unittest.main()
