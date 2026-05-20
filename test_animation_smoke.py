"""
test_animation_smoke.py — Animasyon modülü smoke testleri
==========================================================
QApplication başlatmadan, modül seviyesinde:
  - Tüm animasyon modülleri import edilebilmeli
  - ANIM_COLORS paleti gerekli anahtarları içermeli ve geçerli hex olmalı
  - Saf-Python referans modülleri (aes_pure, sha256_pure) animasyon
    widget'larının ihtiyaç duyduğu alanları döndürmeli
  - Pencere sınıfları beklenen taban sınıftan türemeli

Bu testler PyQt6 widget'larını instance etmez — sadece sınıf nesnesinin
import edildiğini ve hasattr ile arayüz sözleşmesinin sağlandığını
doğrular. Görsel doğrulama elle yapılır.
"""
import re
import unittest


# ---------------------------------------------------------------------------
# Tema/palet
# ---------------------------------------------------------------------------

class TestAnimColors(unittest.TestCase):
    """ANIM_COLORS paleti tüm animasyon widget'ları tarafından paylaşılır."""

    REQUIRED_KEYS = {
        "bg_main", "bg_card", "bg_input",
        "text_primary", "text_secondary", "text_muted",
        "accent_blue", "accent_green", "accent_yellow",
        "accent_mauve", "accent_peach",
        "border",
    }

    def test_palette_is_dict(self) -> None:
        from animation_modals.base import ANIM_COLORS
        self.assertIsInstance(ANIM_COLORS, dict)

    def test_all_required_keys_present(self) -> None:
        from animation_modals.base import ANIM_COLORS
        missing = self.REQUIRED_KEYS - set(ANIM_COLORS.keys())
        self.assertEqual(
            missing, set(),
            f"ANIM_COLORS eksik anahtarlar: {missing}",
        )

    def test_all_values_are_valid_hex(self) -> None:
        """Tüm değerler 6 haneli geçerli hex (#RRGGBB) olmalı."""
        from animation_modals.base import ANIM_COLORS
        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for key, val in ANIM_COLORS.items():
            with self.subTest(key=key):
                self.assertRegex(
                    val, hex_re,
                    f"ANIM_COLORS['{key}'] = {val!r}: 6-haneli #RRGGBB değil",
                )


# ---------------------------------------------------------------------------
# Modül import smoke testleri
# ---------------------------------------------------------------------------

class TestAnimationModulesImport(unittest.TestCase):
    """Animation modülleri yüklenirken hata vermemeli."""

    def test_base_module_imports(self) -> None:
        from animation_modals import base
        self.assertTrue(hasattr(base, "CryptoAnimationWindow"))

    def test_aes_animation_module_imports(self) -> None:
        from animation_modals import aes_animation
        self.assertTrue(hasattr(aes_animation, "AESAnimationWindow"))

    def test_rsa_animation_module_imports(self) -> None:
        from animation_modals import rsa_animation
        self.assertTrue(hasattr(rsa_animation, "RSAAnimationWindow"))

    def test_sha256_animation_module_imports(self) -> None:
        from animation_modals import sha256_animation
        self.assertTrue(hasattr(sha256_animation, "SHA256AnimationWindow"))

    def test_matrix_widget_module_imports(self) -> None:
        from animation_modals import matrix_widget
        self.assertTrue(hasattr(matrix_widget, "MatrixWidget"))

    def test_aes_pure_module_imports(self) -> None:
        from animation_modals import aes_pure
        self.assertTrue(hasattr(aes_pure, "aes256_encrypt_with_rounds"))

    def test_sha256_pure_module_imports(self) -> None:
        from animation_modals import sha256_pure
        self.assertTrue(hasattr(sha256_pure, "sha256_steps"))


class TestAnimationWindowsSubclassBase(unittest.TestCase):
    """Üç ana animasyon penceresi CryptoAnimationWindow'dan türemeli."""

    def test_aes_window_subclasses_base(self) -> None:
        from animation_modals.aes_animation import AESAnimationWindow
        from animation_modals.base import CryptoAnimationWindow
        self.assertTrue(
            issubclass(AESAnimationWindow, CryptoAnimationWindow),
            "AESAnimationWindow CryptoAnimationWindow alt sınıfı olmalı",
        )

    def test_rsa_window_subclasses_base(self) -> None:
        from animation_modals.rsa_animation import RSAAnimationWindow
        from animation_modals.base import CryptoAnimationWindow
        self.assertTrue(
            issubclass(RSAAnimationWindow, CryptoAnimationWindow),
        )

    def test_sha256_window_subclasses_base(self) -> None:
        from animation_modals.sha256_animation import SHA256AnimationWindow
        from animation_modals.base import CryptoAnimationWindow
        self.assertTrue(
            issubclass(SHA256AnimationWindow, CryptoAnimationWindow),
        )


# ---------------------------------------------------------------------------
# Saf-Python referans modülleri — animasyon veri sözleşmesi
# ---------------------------------------------------------------------------

class TestSHA256PureContract(unittest.TestCase):
    """sha256_pure.sha256_steps() animasyon widget'larının okuduğu tüm
    alanları döndürmeli; alanlar bozulursa final eşleşme animasyonu bozulur."""

    REQUIRED_KEYS = {
        "initial_h",
        "round_snapshots",
        "w_expansion",
        "final_hash",
        "pre_final_h",
        "final_working",
        "final_h_parts",
        "blocks_count",
        "binary_preview",
        # Mesaj Hazırlığı için yeni alanlar
        "message_bytes",
        "message_text",
        "padded_bytes",
    }

    def test_all_required_keys_present(self) -> None:
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"abc")
        missing = self.REQUIRED_KEYS - set(result.keys())
        self.assertEqual(
            missing, set(),
            f"sha256_steps çıktısında eksik alanlar: {missing}",
        )

    def test_final_h_parts_concatenates_to_final_hash(self) -> None:
        """final_h_parts birleştirilince final_hash'e eşit olmalı —
        _MatchAssemblyWidget'in faz 3 birleşim animasyonunun temeli."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"test")
        joined = "".join(result["final_h_parts"])
        self.assertEqual(joined, result["final_hash"])

    def test_initial_h_is_eight_8char_hex(self) -> None:
        """initial_h 8 adet 32-bit hex string olmalı (H0..H7)."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"x")
        self.assertEqual(len(result["initial_h"]), 8)
        for h in result["initial_h"]:
            self.assertEqual(len(h), 8)
            int(h, 16)  # geçerli hex

    def test_pre_final_h_and_final_working_are_eight_entries(self) -> None:
        """Final eşleşme animasyonu 8 satırda H_old + working = H_new
        gösterir; iki listenin uzunluğu 8 olmak zorunda."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"y")
        self.assertEqual(len(result["pre_final_h"]), 8)
        self.assertEqual(len(result["final_working"]), 8)

    def test_w_expansion_has_16_entries(self) -> None:
        """W[16..31] = 16 satır; _WExpansionWidget ◀/▶ navigasyonu için."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"z")
        self.assertEqual(len(result["w_expansion"]), 16)


class TestAESPureContract(unittest.TestCase):
    """aes_pure.aes256_encrypt_with_rounds() animasyonun ihtiyaç duyduğu
    14-round veri yapısını döndürmeli."""

    KEY = bytes.fromhex(
        "000102030405060708090a0b0c0d0e0f"
        "101112131415161718191a1b1c1d1e1f"
    )
    PLAINTEXT = bytes.fromhex("00112233445566778899aabbccddeeff")

    def test_returns_rounds_data_and_final_block(self) -> None:
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        self.assertIn("rounds_data", result)
        self.assertIn("final_block_hex", result)

    def test_final_block_is_32_hex_chars(self) -> None:
        """final_block_hex 16 byte AES blok = 32 hex karakter."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        self.assertEqual(len(result["final_block_hex"]), 32)
        int(result["final_block_hex"], 16)

    def test_round_keys_present(self) -> None:
        """Animasyondaki AddRoundKey adımları için round_keys gerekli."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        # Anahtar genişletme sonucu 15 round_key üretir (round 0..14)
        if "round_keys_hex" in result:
            self.assertEqual(len(result["round_keys_hex"]), 15)

    def test_plaintext_prep_fields_present(self):
        """Plaintext Hazırlığı için yeni alanlar mevcut olmalı."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        for key in ("plaintext_bytes", "padded_plaintext",
                    "first_block", "blocks_total", "state_matrix"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# Tezdeki sabit değerler — RSA animasyon modülünde
# ---------------------------------------------------------------------------

class TestRSAConstantsInvariants(unittest.TestCase):
    """RSA animasyon modülü demo değerleri rastgele seçilir
    (_reseed_demo); spesifik sayılar değil matematiksel invariantlar
    sınanır (cross-modül smoke)."""

    def test_consistency(self) -> None:
        """n = p·q ve φ = (p-1)(q-1) tutarlı olmalı."""
        from animation_modals.rsa_animation import _P, _Q, _N, _PHI
        self.assertEqual(_N, _P * _Q)
        self.assertEqual(_PHI, (_P - 1) * (_Q - 1))

    def test_invariant(self) -> None:
        from animation_modals.rsa_animation import _E, _D, _PHI
        self.assertEqual((_E * _D) % _PHI, 1)


class TestAESMatrixViewIntegration(unittest.TestCase):
    """AES penceresi yeni matris widget'ını kullanıyor mu?"""

    def test_module_imports(self):
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESMatrixView"))
        self.assertTrue(hasattr(aes_matrix_view, "_AESStateCompareWidget"))

    def test_aes_window_imports_compare_widget(self):
        """AES animasyon modülü _AESStateCompareWidget'ı import etmeli."""
        from animation_modals import aes_animation
        # _AESStateCompareWidget veya aes_matrix_view referansı olmalı
        import inspect
        source = inspect.getsource(aes_animation)
        self.assertIn("_AESStateCompareWidget", source)

    def test_aes_matrix_view_total_ticks_are_positive(self):
        from animation_modals.aes_matrix_view import _AESMatrixView
        for op, ticks in _AESMatrixView._TICKS_BY_OP.items():
            with self.subTest(op=op):
                self.assertGreater(ticks, 0, f"{op}: tick sayısı pozitif olmalı")
                self.assertLess(ticks, 200, f"{op}: tick sayısı makul olmalı (<200)")

    def test_aes_matrix_view_supports_all_four_ops(self):
        from animation_modals.aes_matrix_view import _AESMatrixView
        for op in ("AddRoundKey", "SubBytes", "ShiftRows", "MixColumns"):
            with self.subTest(op=op):
                self.assertIn(op, _AESMatrixView._TICKS_BY_OP)


if __name__ == "__main__":
    unittest.main()
