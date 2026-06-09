"""
test_animation_smoke.py — Animasyon modülü smoke testleri
==========================================================

Test türü: SMOKE TESTİ (Import & Sözleşme Kontratı)

Amaç:
    animation_modals/ paketinin tümünü PyQt6 widget'ı instance etmeden
    doğrular. CI/headless ortamda da çalışabilir; modül seviyesi temel
    sağlık kontrolüdür. Regression'da ilk yakalanan hata sınıfıdır.

Kapsam (QApplication BAŞLATMADAN):
    - TestAnimColors: ANIM_COLORS paleti gerekli 12 anahtarı içerir +
      tüm değerler 6-haneli geçerli hex (#RRGGBB) formatında.
    - TestAnimationModulesImport: rsa_animation, sha256_animation,
      aes_animation, matrix_widget, aes_pure, sha256_pure modülleri
      ImportError vermeden yüklenir; her birinin ana sınıf/fonksiyonu tanımlı.
    - TestAnimationWindowsSubclassBase: AESAnimationWindow,
      RSAAnimationWindow, SHA256AnimationWindow → CryptoAnimationWindow
      taban sınıfının alt sınıfıdır.
    - TestSHA256PureContract: sha256_steps() dönüşü animasyon widget'larının
      okuduğu TÜM alanları içerir (REQUIRED_KEYS set'i 12 anahtar).
      Yapısal invariantlar: final_h_parts birleşimi = final_hash, initial_h
      = 8 × 8-karakter hex, w_expansion = 16 satır.
    - TestAESPureContract: aes256_encrypt_with_rounds() rounds_data ve
      final_block_hex döndürür; 32 hex karakter (16 byte); 15 round_key
      (round 0..14).
    - TestRSAConstantsInvariants: cross-modül smoke — _N = _P × _Q,
      _PHI = (P-1)(Q-1), (E·D) mod PHI == 1.
    - TestAESMatrixViewIntegration: _AESMatrixView 4 AES operasyonunu
      (AddRoundKey, SubBytes, ShiftRows, MixColumns) destekler;
      tick sayıları makul aralıkta (0 < ticks < 200).

Strateji: Sınıf nesnesi import + hasattr ile arayüz sözleşmesini doğrular.
Pixel/visual doğrulama elle yapılır.

Hata durumunda anlamı: Animasyon paketinde bir refactor sözleşmeyi
bozdu (yeniden adlandırma, alan silme, vb.); UI muhtemelen çalışmaz.
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
        """Alt tür: SMOKE (tip kontrolü).
        ANIM_COLORS bir dict olmalı (list veya tuple değil); widget'lar
        ANIM_COLORS['key'] erişimi yapar."""
        from animation_modals.base import ANIM_COLORS
        self.assertIsInstance(ANIM_COLORS, dict)

    def test_all_required_keys_present(self) -> None:
        """Alt tür: SMOKE (sözleşme kümesi).
        ANIM_COLORS REQUIRED_KEYS'in tüm anahtarlarını içermeli
        (bg_main, accent_blue, text_primary, vb.). Eksik anahtar →
        widget paint sırasında KeyError → animasyon crash."""
        from animation_modals.base import ANIM_COLORS
        missing = self.REQUIRED_KEYS - set(ANIM_COLORS.keys())
        self.assertEqual(
            missing, set(),
            f"ANIM_COLORS eksik anahtarlar: {missing}",
        )

    def test_all_values_are_valid_hex(self) -> None:
        """Alt tür: SMOKE (değer format kontrolü).
        Tüm değerler 6 haneli #RRGGBB hex formatında. QColor regex'i
        geçmez ama görsel olarak siyah çıkar — bu test sessiz hatayı
        yakalar (subTest ile her anahtarı ayrı ayrı raporlar)."""
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
        """Alt tür: SMOKE (modül + temel sınıf varlığı).
        base.py yüklenir + CryptoAnimationWindow taban sınıfı tanımlı."""
        from animation_modals import base
        self.assertTrue(hasattr(base, "CryptoAnimationWindow"))

    def test_aes_animation_module_imports(self) -> None:
        """Alt tür: SMOKE (AES penceresi sınıfı).
        AESAnimationWindow sınıfı aes alt-paketinde tanımlı."""
        from animation_modals import aes
        self.assertTrue(hasattr(aes, "AESAnimationWindow"))

    def test_rsa_animation_module_imports(self) -> None:
        """Alt tür: SMOKE (RSA penceresi sınıfı).
        RSAAnimationWindow sınıfı rsa alt-paketinde tanımlı."""
        from animation_modals import rsa
        self.assertTrue(hasattr(rsa, "RSAAnimationWindow"))

    def test_sha256_animation_module_imports(self) -> None:
        """Alt tür: SMOKE (SHA penceresi sınıfı).
        SHA256AnimationWindow sınıfı sha256 alt-paketinde tanımlı."""
        from animation_modals import sha256
        self.assertTrue(hasattr(sha256, "SHA256AnimationWindow"))

    def test_matrix_widget_module_imports(self) -> None:
        """Alt tür: SMOKE (yardımcı modül).
        matrix_widget.MatrixWidget — animasyon dışında kullanılan
        genel matris görselleştirici (eski/legacy widget'ı)."""
        from animation_modals import matrix_widget
        self.assertTrue(hasattr(matrix_widget, "MatrixWidget"))

    def test_aes_pure_module_imports(self) -> None:
        """Alt tür: SMOKE (pure modül fonksiyon varlığı).
        aes_pure.aes256_encrypt_with_rounds fonksiyonu modülde tanımlı."""
        from animation_modals import aes_pure
        self.assertTrue(hasattr(aes_pure, "aes256_encrypt_with_rounds"))

    def test_sha256_pure_module_imports(self) -> None:
        """Alt tür: SMOKE (pure modül fonksiyon varlığı).
        sha256_pure.sha256_steps fonksiyonu modülde tanımlı."""
        from animation_modals import sha256_pure
        self.assertTrue(hasattr(sha256_pure, "sha256_steps"))


class TestAnimationWindowsSubclassBase(unittest.TestCase):
    """Üç ana animasyon penceresi CryptoAnimationWindow'dan türemeli."""

    def test_aes_window_subclasses_base(self) -> None:
        """Alt tür: SMOKE (sınıf hiyerarşi).
        AESAnimationWindow → CryptoAnimationWindow alt sınıfı. Taban
        sınıfın navigasyon/progress bar/timer altyapısını miras alır."""
        from animation_modals import AESAnimationWindow
        from animation_modals.base import CryptoAnimationWindow
        self.assertTrue(
            issubclass(AESAnimationWindow, CryptoAnimationWindow),
            "AESAnimationWindow CryptoAnimationWindow alt sınıfı olmalı",
        )

    def test_rsa_window_subclasses_base(self) -> None:
        """Alt tür: SMOKE (sınıf hiyerarşi).
        RSAAnimationWindow → CryptoAnimationWindow alt sınıfı."""
        from animation_modals import RSAAnimationWindow
        from animation_modals.base import CryptoAnimationWindow
        self.assertTrue(
            issubclass(RSAAnimationWindow, CryptoAnimationWindow),
        )

    def test_sha256_window_subclasses_base(self) -> None:
        """Alt tür: SMOKE (sınıf hiyerarşi).
        SHA256AnimationWindow → CryptoAnimationWindow alt sınıfı."""
        from animation_modals import SHA256AnimationWindow
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
        """Alt tür: SMOKE (veri sözleşmesi — 12 anahtar).
        sha256_steps() çıktısı REQUIRED_KEYS'in tüm anahtarlarını
        içermeli (initial_h, round_snapshots, w_expansion, vb. + yeni
        Mesaj Hazırlığı alanları). Eksik bir anahtar → animasyon
        sayfasında KeyError → çökme."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"abc")
        missing = self.REQUIRED_KEYS - set(result.keys())
        self.assertEqual(
            missing, set(),
            f"sha256_steps çıktısında eksik alanlar: {missing}",
        )

    def test_final_h_parts_concatenates_to_final_hash(self) -> None:
        """Alt tür: INVARIANT (yapısal tutarlılık).
        final_h_parts (8 × 8-karakter hex) birleştirilince tam final_hash'e
        (64 karakter hex) eşit olmalı. _MatchAssemblyWidget faz 3'te bu
        birleştirmeyi animasyonla gösterir — eşitlik bozulursa görsel
        hash, gerçek hash'ten farklı çıkar."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"test")
        joined = "".join(result["final_h_parts"])
        self.assertEqual(joined, result["final_hash"])

    def test_initial_h_is_eight_8char_hex(self) -> None:
        """Alt tür: INVARIANT (FIPS 180-4 sabitleri yapısı).
        initial_h tam 8 girdi içerir (H0..H7), her biri 8 karakterlik
        geçerli hex (32-bit register'lar). int(h,16) parse hatası vermez."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"x")
        self.assertEqual(len(result["initial_h"]), 8)
        for h in result["initial_h"]:
            self.assertEqual(len(h), 8)
            int(h, 16)  # geçerli hex

    def test_pre_final_h_and_final_working_are_eight_entries(self) -> None:
        """Alt tür: INVARIANT (final eşleşme animasyonu veri sözleşmesi).
        Eşleşme sayfası 8 satırda 'H_eski + working = H_yeni' formülünü
        gösterir; iki listenin de uzunluğu 8 OLMAK ZORUNDA. Uzunluk
        eşitsizliği → animasyonda eksik satır → görsel eksik."""
        from animation_modals.sha256_pure import sha256_steps
        result = sha256_steps(b"y")
        self.assertEqual(len(result["pre_final_h"]), 8)
        self.assertEqual(len(result["final_working"]), 8)

    def test_w_expansion_has_16_entries(self) -> None:
        """Alt tür: INVARIANT (W expansion sayısı).
        W[16..31] arası tam 16 satır — _WExpansionWidget'in ◀/▶
        navigasyonu için fixed-size. SHA-256 mesaj genişletme
        algoritmasının pedagojik kesidi."""
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
        """Alt tür: SMOKE (temel API alanları).
        aes256_encrypt_with_rounds çıktısında en az rounds_data ve
        final_block_hex bulunmalı."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        self.assertIn("rounds_data", result)
        self.assertIn("final_block_hex", result)

    def test_final_block_is_32_hex_chars(self) -> None:
        """Alt tür: INVARIANT (blok format).
        AES bloğu = 16 byte = 32 hex karakter. int(..., 16) parse
        hatası yoksa geçerli hex string. Animasyon eşleşme sayfası
        bu uzunluğu varsayar."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        self.assertEqual(len(result["final_block_hex"]), 32)
        int(result["final_block_hex"], 16)

    def test_round_keys_present(self) -> None:
        """Alt tür: INVARIANT (anahtar genişletme yapısı).
        AES-256 key expansion 15 round_key üretir (round 0..14). round_keys_hex
        opsiyonel olduğu için 'if in' ile koşullu kontrol — alan varsa
        boyut tam 15 olmalı, yoksa testi geçer."""
        from animation_modals.aes_pure import aes256_encrypt_with_rounds
        result = aes256_encrypt_with_rounds(self.KEY, self.PLAINTEXT)
        # Anahtar genişletme sonucu 15 round_key üretir (round 0..14)
        if "round_keys_hex" in result:
            self.assertEqual(len(result["round_keys_hex"]), 15)

    def test_plaintext_prep_fields_present(self):
        """Alt tür: SMOKE (yeni alanlar).
        Mesaj Hazırlığı çalışmasıyla eklenen 5 alan (plaintext_bytes,
        padded_plaintext, first_block, blocks_total, state_matrix)
        mevcut olmalı. _AESPlaintextPrepWidget bu alanları doğrudan okur."""
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
        """Alt tür: INVARIANT (RSA modülüs ve totient).
        n = p · q  VE  ϕ(n) = (p-1)(q-1). Random demo değerleriyle
        her açılışta bu temel RSA bağıtları sağlanmalı."""
        from animation_modals.rsa.helpers import _P, _Q, _N, _PHI
        self.assertEqual(_N, _P * _Q)
        self.assertEqual(_PHI, (_P - 1) * (_Q - 1))

    def test_invariant(self) -> None:
        """Alt tür: INVARIANT (RSA anahtar üretim ilkesi).
        e · d ≡ 1 (mod ϕ) — RSA özel üs (d) tanımının matematiksel
        temeli. Bu bozulursa şifreleme/deşifreleme tutarsız olur."""
        from animation_modals.rsa.helpers import _E, _D, _PHI
        self.assertEqual((_E * _D) % _PHI, 1)


class TestAESMatrixViewIntegration(unittest.TestCase):
    """AES penceresi yeni matris widget'ını kullanıyor mu?"""

    def test_module_imports(self):
        """Alt tür: SMOKE (matris widget modülü).
        aes_matrix_view modülünde _AESMatrixView (tek matris) ve
        _AESStateCompareWidget (önce/sonra ikili) sınıfları tanımlı."""
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESMatrixView"))
        self.assertTrue(hasattr(aes_matrix_view, "_AESStateCompareWidget"))

    def test_aes_window_imports_compare_widget(self):
        """Alt tür: SMOKE (modüller arası bağlantı — kaynak grep).
        aes window.py kaynak kodunda '_AESStateCompareWidget'
        referansı geçmeli. AST analizi yerine basit string arama
        (regex değil) — refactor'da unutulan import veya yanlış
        widget kullanımını yakalar."""
        from animation_modals.aes import window as aes_window
        # _AESStateCompareWidget veya aes_matrix_view referansı olmalı
        import inspect
        source = inspect.getsource(aes_window)
        self.assertIn("_AESStateCompareWidget", source)

    def test_aes_matrix_view_total_ticks_are_positive(self):
        """Alt tür: INVARIANT (animasyon zamanlama tablosu).
        _TICKS_BY_OP dictionary'sindeki her operasyon için tick sayısı
        0 < ticks < 200. 0 → animasyon hiç oynamaz, 200+ → makul olmayan
        derecede yavaş. subTest ile her operasyon ayrı raporlanır."""
        from animation_modals.aes_matrix_view import _AESMatrixView
        for op, ticks in _AESMatrixView._TICKS_BY_OP.items():
            with self.subTest(op=op):
                self.assertGreater(ticks, 0, f"{op}: tick sayısı pozitif olmalı")
                self.assertLess(ticks, 200, f"{op}: tick sayısı makul olmalı (<200)")

    def test_aes_matrix_view_supports_all_four_ops(self):
        """Alt tür: INVARIANT (operasyon kapsam kontrolü).
        4 AES operasyonunun (AddRoundKey, SubBytes, ShiftRows,
        MixColumns) tümü _TICKS_BY_OP içinde tanımlı olmalı. Birinin
        eksik olması → animasyon o operasyona geldiğinde KeyError."""
        from animation_modals.aes_matrix_view import _AESMatrixView
        for op in ("AddRoundKey", "SubBytes", "ShiftRows", "MixColumns"):
            with self.subTest(op=op):
                self.assertIn(op, _AESMatrixView._TICKS_BY_OP)


class TestAnimationSpeedEnum(unittest.TestCase):
    """base.AnimationSpeed Enum + Türkçe etiket haritası sözleşmesi.

    Magic number hız haritası ``{"Yavaş":2000,...}`` yerine isimli Enum
    kullanılır; UI'da gösterilen etiketler Türkçe kalır."""

    def test_enum_durations_unchanged(self) -> None:
        """Alt tür: INVARIANT (süre değerleri korunur).
        Enum üyelerinin ms değerleri eski sözlükle birebir aynı olmalı —
        davranış (otomatik oynatma hızı) değişmedi."""
        from animation_modals.base import AnimationSpeed
        self.assertEqual(AnimationSpeed.SLOW.value, 2000)
        self.assertEqual(AnimationSpeed.NORMAL.value, 1500)
        self.assertEqual(AnimationSpeed.FAST.value, 800)

    def test_turkish_labels_preserved(self) -> None:
        """Alt tür: INVARIANT (kullanıcıya görünen Türkçe etiketler).
        SPEED_LABELS_TR her Enum üyesini doğru Türkçe etikete eşler;
        UI etiketleri Türkçe kalmalı."""
        from animation_modals.base import AnimationSpeed, SPEED_LABELS_TR
        self.assertEqual(SPEED_LABELS_TR[AnimationSpeed.SLOW], "Yavaş")
        self.assertEqual(SPEED_LABELS_TR[AnimationSpeed.NORMAL], "Normal")
        self.assertEqual(SPEED_LABELS_TR[AnimationSpeed.FAST], "Hızlı")
        # Negatif/kapsam: her üye için bir etiket tanımlı (eksik eşleme yok).
        self.assertEqual(set(SPEED_LABELS_TR.keys()), set(AnimationSpeed))


class TestFipsRoundConstants(unittest.TestCase):
    """AES/SHA round sayısı sabitleri FIPS referans değerlerini taşır."""

    def test_aes_num_rounds(self) -> None:
        """Alt tür: INVARIANT (FIPS 197 §5.1).
        AES-256 round sayısı 14; final round indeksi de 14 olmalı."""
        from animation_modals.aes.constants import (
            AES_NUM_ROUNDS,
            AES_FINAL_ROUND_INDEX,
        )
        self.assertEqual(AES_NUM_ROUNDS, 14)
        self.assertEqual(AES_FINAL_ROUND_INDEX, 14)

    def test_sha256_num_rounds(self) -> None:
        """Alt tür: INVARIANT (FIPS 180-4 §6.2.2).
        SHA-256 sıkıştırma round sayısı 64 olmalı."""
        from animation_modals.sha256.constants import SHA256_NUM_ROUNDS
        self.assertEqual(SHA256_NUM_ROUNDS, 64)


if __name__ == "__main__":
    unittest.main()
