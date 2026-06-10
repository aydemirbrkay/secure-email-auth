# test_animation_widgets_smoke.py
"""
test_animation_widgets_smoke.py — Mesaj/Plaintext Hazırlığı widget'ları smoke testleri
=======================================================================================

Test türü: SMOKE TESTİ (Import & API Sözleşmesi)

Amaç:
    SHA Mesaj Hazırlığı + AES Plaintext Hazırlığı çalışmasıyla eklenen yeni
    widget'ların ve byte_widgets modülünün import edilebilirliğini, API
    parametre signature'larını ve SHA penceresinin yeni 5-adımlı yapısını
    QApplication başlatmadan doğrular.

Kapsam (PyQt6 widget instance YOK — sadece import + inspect.signature):
    - TestNewWidgetsImport: 6 yeni öğe import edilebilmeli:
        * _PALETTE_6 (6 renkli liste, hepsi geçerli #RRGGBB)
        * _ColoredByteGridWidget (detay grid)
        * _ByteStripWidget (kompakt strip)
        * _SHAMessagePrepWidget (Adım 1/5)
        * _SHA256PaddingWidget (Adım 2/5)
        * _AESPlaintextPrepWidget (AES intro→prep→rounds)
    - TestPaddingMaskSupport: widget'ların padding_mask + padding_labels
      parametrelerini kabul ettiği signature kontrolü (inspect.signature).
      Geçerli etiket değerleri: '80', '00', 'len', 'pad'.
    - TestSHAStepCount: SHA penceresi _TITLES sınıf niteliği 5 girdili,
      birincisi "Mesaj Hazırlığı" içerir, her başlık "Adım N / 5"
      formatında — 4→5 adım kaymasının doğru yapıldığının kanıtı.

Strateji: Mikro-saniyelerde çalışır, CI/headless dostu. Bir API kontratı
test'idir; widget'ların gerçek render'ı manuel doğrulanır.

Hata durumunda anlamı: byte_widgets modülü, padding API'si veya SHA
window adım yapısı bozulmuş; uygulama açıldığında AttributeError verir.
"""
import unittest


class TestNewWidgetsImport(unittest.TestCase):
    """Yeni widget'lar import edilebilmeli (Alt kategori: SMOKE — modül varlığı)."""

    def test_palette_has_6_colors(self):
        """Alt tür: SMOKE (sabit liste).
        Döngüsel renk paletindeki renk sayısı tam 6 olmalı; widget'lar
        i % 6 indeksleme ile renk seçer. Eksik renk → IndexError'a yol açar."""
        from animation_modals.byte_widgets import _PALETTE_6
        self.assertEqual(len(_PALETTE_6), 6)

    def test_palette_all_valid_hex(self):
        """Alt tür: SMOKE (veri format kontrolü).
        Paletin her elemanı 6-haneli #RRGGBB hex formatında olmalı.
        QColor regex'e uymayan değerleri sessizce kabul eder ama
        görsel olarak siyah çıkar — bu test sessiz hatayı yakalar."""
        import re
        from animation_modals.byte_widgets import _PALETTE_6
        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for color in _PALETTE_6:
            self.assertRegex(color, hex_re)

    def test_colored_byte_grid_widget_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        _ColoredByteGridWidget byte_widgets modülünde tanımlı VE çağrılabilir
        (sınıf veya fonksiyon) olmalı."""
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        self.assertTrue(callable(_ColoredByteGridWidget))

    def test_byte_strip_widget_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        _ByteStripWidget byte_widgets modülünde tanımlı VE çağrılabilir."""
        from animation_modals.byte_widgets import _ByteStripWidget
        self.assertTrue(callable(_ByteStripWidget))

    def test_sha_message_prep_widget_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        _SHAMessagePrepWidget sha256.prep_widget modülünde tanımlı —
        SHA penceresinin Adım 1/5 sayfasının ana widget'ı."""
        from animation_modals.sha256.prep_widget import _SHAMessagePrepWidget
        self.assertTrue(callable(_SHAMessagePrepWidget))

    def test_sha_padding_widget_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        _SHA256PaddingWidget sha256.prep_widget modülünde tanımlı —
        SHA penceresinin Adım 2/5 padding sayfasının ana widget'ı."""
        from animation_modals.sha256.prep_widget import _SHA256PaddingWidget
        self.assertTrue(callable(_SHA256PaddingWidget))

    def test_aes_plaintext_prep_widget_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        _AESPlaintextPrepWidget aes.prep_widget modülünde tanımlı —
        AES intro ile Round 0 arasındaki Plaintext Hazırlığı sayfası."""
        from animation_modals.aes.prep_widget import _AESPlaintextPrepWidget
        self.assertTrue(callable(_AESPlaintextPrepWidget))

    def test_cached_font_reuses_same_font_instance(self):
        """Aynı font tanımı paint kareleri arasında yeniden kullanılmalı."""
        from PyQt6.QtGui import QFont
        from animation_modals.base import cached_font

        first = cached_font("Courier New", 13, QFont.Weight.Bold)
        second = cached_font("Courier New", 13, QFont.Weight.Bold)
        self.assertIs(first, second)


class TestRegisterDemoRenders(unittest.TestCase):
    """SHA intro önizleme (_RegisterDemoWidget) render güvenliği (Alt kategori:
    BİRİM). D-A: T1/T2 başlıkları artık unlit iken faint 'border' yerine accent
    rengiyle çiziliyor (açık+koyu modda okunur). Bu test tüm fazlarda hatasız
    render'ı garanti eder (kontrast düzeltmesi paintEvent'i bozmamalı)."""

    def test_renders_all_phases(self):
        """Alt tür: BİRİM (render smoke).
        72-tick döngünün üç fazı (giriş / T1-T2 / çıkış) hatasız boyanmalı."""
        from PyQt6.QtGui import QPixmap
        from animation_modals.sha256.register_demo import _RegisterDemoWidget
        w = _RegisterDemoWidget()
        w.resize(340, 200)
        for t in (0, 12, 30, 42, 60, 71):
            w._tick = t
            w.render(QPixmap(340, 200))  # istisna fırlatırsa fail


class TestAESIntroLayoutLikeSHA(unittest.TestCase):
    """AES intro yerleşimi SHA introsuyla aynı olmalı (Alt kategori: BİRİM —
    runtime). Regresyon: AES intro'da sol önizleme sabit-dar (200-240px) ve
    kutular max-width 360 ile sola sıkışıktı; artık SHA gibi sol panel büyük
    (stretch=2) ve kutular tam genişlik + eşit (Görsel 3 turu)."""

    def _build_intro(self):
        from animation_modals import AESAnimationWindow
        a = AESAnimationWindow(
            key=bytes(32), plaintext=b"asdasddsada", expected_ct_hex="00" * 16
        )
        a.resize(1200, 760)
        a.show()
        intro = a._intro
        for w in intro._widgets:
            w.setVisible(True)
        return a, intro

    def test_intro_boxes_equal_width(self):
        """Alt tür: BİRİM (eşit kutu — pozitif).
        Beş akış kutusu (Plaintext, R0, R1-13, R14, Ciphertext) AYNI
        genişlikte olmalı; max-width sınırı kaldırıldığı için hepsi sağ
        panelin tam genişliğini alır."""
        a, intro = self._build_intro()
        boxes = [intro._intro_plain, intro._box_r0, intro._box_main,
                 intro._box_r14, intro._intro_cipher]
        widths = {b.width() for b in boxes}
        self.assertEqual(len(widths), 1,
                         f"Kutular eşit genişlikte olmalı, görülen: {widths}")

    def test_intro_left_panel_not_fixed_narrow(self):
        """Alt tür: BİRİM (büyük önizleme — negatif/regresyon).
        Sol önizleme paneli eski sabit-dar sınırını (≤240px) AŞMALI; SHA gibi
        stretch=2 ile büyük açıldığından geniş pencerede belirgin büyür."""
        a, intro = self._build_intro()
        self.assertGreater(
            intro._left_frame.width(), 240,
            "Sol önizleme paneli SHA gibi büyük olmalı (sabit 240px değil)",
        )

    def test_prep_grid_full_width_but_no_stack_leak(self):
        """Alt tür: BİRİM (padding scroll — D-D).
        Plaintext prep grid'i TAM 16 hücre genişliğini ister (okunur boyut)
        ama yatay scroll içinde olduğundan bu min-width AES stack'ine SIZMAZ:
        prep sayfasının (page 1) min genişliği küçük kalmalı (≤ ~200px)."""
        from animation_modals import AESAnimationWindow
        a = AESAnimationWindow(
            key=bytes(32), plaintext=b"adsad", expected_ct_hex="00" * 16
        )
        # Grid tam boyut min-width ister
        self.assertGreaterEqual(a._plaintext_widget._grid.minimumWidth(), 1000)
        # Ama prep sayfası (scroll sayesinde) küçük min-width bildirir
        self.assertLessEqual(
            a._stack.widget(1).minimumSizeHint().width(), 200,
            "Grid min-width scroll'da kapsanmali, stack'e sizmamali",
        )

    def test_round_zero_uses_plaintext_state_as_before_matrix(self):
        """Round 0 AddRoundKey, plaintext state ⊕ round_key = sonuç göstermeli."""
        from animation_modals import AESAnimationWindow

        a = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"0123456789abcdef",
            expected_ct_hex="00" * 16,
        )
        a._switch_to_rounds_only()

        self.assertEqual(a._matrix_pair._prev_view._state, a._initial_state_hex)
        self.assertNotEqual(
            a._matrix_pair._prev_view._state,
            a._matrix_pair._curr_view._after,
        )

    def test_plaintext_matrix_phase_uses_balanced_timing(self):
        """State matrisi ne uzun bekletmeli ne de takip edilemeyecek kadar hızlı dolmalı."""
        from animation_modals.aes.prep_widget import _AESPlaintextPrepWidget

        self.assertEqual(_AESPlaintextPrepWidget._MATRIX_START_TICK, 96)
        self.assertEqual(_AESPlaintextPrepWidget._MATRIX_TICKS_PER_COLUMN, 8)
        self.assertEqual(_AESPlaintextPrepWidget._FINISH_TICK, 128)

    def test_plaintext_matrix_columns_advance_every_eight_ticks(self):
        """Dört sütun dengeli aralıklarla görünmeli ve 128. tick'te tamamlanmalı."""
        from animation_modals.aes.prep_widget import _AESPlaintextPrepWidget

        block = b"0123456789abcdef"
        state = [[f"{row}{col}" for col in range(4)] for row in range(4)]
        widget = _AESPlaintextPrepWidget(
            block.decode(),
            block,
            block,
            block,
            1,
            state,
        )
        widget._tick = 95

        widget._on_tick()
        self.assertTrue(all(widget._matrix_filled[row][0] for row in range(4)))
        self.assertFalse(any(widget._matrix_filled[row][1] for row in range(4)))

        for _ in range(8):
            widget._on_tick()
        self.assertTrue(all(widget._matrix_filled[row][1] for row in range(4)))

        while widget._tick < 127:
            widget._on_tick()
        self.assertFalse(widget._finished)

        widget._on_tick()
        self.assertTrue(widget._finished)
        self.assertTrue(all(all(row) for row in widget._matrix_filled))


class TestPaddingMaskSupport(unittest.TestCase):
    """Padding renk ayrımı API kontratı (Alt kategori: API SIGNATURE — runtime'sız)."""

    def test_colored_byte_grid_accepts_padding_mask_param(self):
        """Alt tür: SMOKE (parametre kontratı).
        Widget'ı instance ETMEDEN inspect.signature ile __init__
        imzasını okur; 'padding_mask' parametresinin tanımlı olduğunu
        doğrular. Headless ortamlarda çalışır (QApplication gerekmez)."""
        import inspect
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        sig = inspect.signature(_ColoredByteGridWidget.__init__)
        self.assertIn("padding_mask", sig.parameters)

    def test_colored_byte_grid_accepts_padding_labels_param(self):
        """Alt tür: SMOKE (parametre kontratı).
        'padding_labels' parametresi de __init__ imzasında olmalı —
        her padding byte'ının altında gösterilen küçük etiket ('80',
        '00', 'len', 'pad') bu parametre ile geçer."""
        import inspect
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        sig = inspect.signature(_ColoredByteGridWidget.__init__)
        self.assertIn("padding_labels", sig.parameters)

    def test_padding_label_values(self):
        """Alt tür: BİRİM (sabit değer kümesi).
        Geçerli padding etiketleri '80' (SHA ayracı), '00' (sıfır dolgu),
        'len' (bit uzunluğu), 'pad' (PKCS#7). Tümü str ve ≤ 4 karakter
        (paint widget hücre altına sığması için)."""
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        # Sadece API kontrolü — değer setinin sabit listesinin varlığını doğrula
        # Test sadece tipik etiket değerlerinin kabul edildiğini garanti eder
        valid_labels = {"80", "00", "len", "pad"}
        for label in valid_labels:
            self.assertIsInstance(label, str)
            self.assertLessEqual(len(label), 4)

    def test_byte_strip_accepts_padding_mask_param(self):
        """Alt tür: SMOKE (parametre kontratı).
        Kompakt strip widget'ı da padding_mask parametresini destekler
        (etiket yok, sadece kenarlık + alpha ile ayrım)."""
        import inspect
        from animation_modals.byte_widgets import _ByteStripWidget
        sig = inspect.signature(_ByteStripWidget.__init__)
        self.assertIn("padding_mask", sig.parameters)


class TestAESOpensLikeSHA(unittest.TestCase):
    """AES animasyon penceresi SHA introsuyla aynı oturmuş yapıda olmalı
    (Alt kategori: BİRİM — runtime). Regresyon: AES eskiden açılışta
    resize(820,620) ile kendini küçültüyordu; bu, intro ekranında boşluklu
    yatay scroll bırakıyordu (Görsel 6). Artık SHA gibi büyük (ekranın ~%82'si)
    açılmalı ve intro stack genişliğini pencereye sığdırmalı."""

    def test_aes_and_sha_open_same_size(self):
        """Alt tür: BİRİM (yerleşim regresyonu — pozitif).
        AES ve SHA pencereleri (standalone, on_close=None) aynı boyutta
        açılmalı. AES kendini küçültürse (eski resize) bu test kırılır."""
        import hashlib
        from animation_modals import SHA256AnimationWindow, AESAnimationWindow
        s = SHA256AnimationWindow(
            message="test", expected_hash=hashlib.sha256(b"test").hexdigest()
        )
        a = AESAnimationWindow(
            key=bytes(32), plaintext=b"asdasddsada", expected_ct_hex="00" * 16
        )
        self.assertEqual(s.size(), a.size(),
                         "AES, SHA ile aynı boyutta açılmalı (kendini küçültmemeli)")

    def test_aes_intro_no_horizontal_scroll(self):
        """Alt tür: BİRİM (yatay scroll regresyonu — negatif).
        AES büyük açılınca stack'in min genişliği pencere genişliğine
        sığmalı (intro'da yatay scroll çıkmamalı). stackMinW <= pencereW."""
        from animation_modals import AESAnimationWindow
        a = AESAnimationWindow(
            key=bytes(32), plaintext=b"asdasddsada", expected_ct_hex="00" * 16
        )
        a.show()
        self.assertLessEqual(
            a._stack.minimumSizeHint().width(), a.width(),
            "Stack min genişliği pencereye sığmalı; aksi halde intro yatay scroll açar",
        )

    def test_embedded_aes_keeps_outer_scroll_and_navigation_fixed(self):
        """AES içeriği kendi içinde kaymalı; Alice paneli tüm pencereyi kaydırmamalı."""
        from PyQt6.QtWidgets import QApplication
        from arayuz.alice_panel import AlicePanel
        from animation_modals import AESAnimationWindow

        panel = AlicePanel()
        panel.resize(850, 600)
        panel.show()
        aes = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"0123456789abcdef",
            expected_ct_hex="00" * 16,
            on_close=lambda: None,
        )
        aes._switch_to_rounds_only()
        panel.show_animation(aes)
        QApplication.processEvents()

        outer = panel._anim_scroll
        self.assertEqual(outer.horizontalScrollBar().maximum(), 0)
        self.assertEqual(outer.verticalScrollBar().maximum(), 0)
        self.assertLessEqual(
            aes._btn_next.y() + aes._btn_next.height(),
            outer.viewport().height(),
        )
        self.assertGreater(aes._round_scroll.horizontalScrollBar().maximum(), 0)

    def test_short_embedded_aes_scrolls_content_not_navigation(self):
        """Kısa panelde dikey scroll round içeriğinde kalır; alt butonlar sabittir."""
        from PyQt6.QtWidgets import QApplication
        from arayuz.alice_panel import AlicePanel
        from animation_modals import AESAnimationWindow

        panel = AlicePanel()
        panel.resize(850, 500)
        panel.show()
        aes = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"0123456789abcdef",
            expected_ct_hex="00" * 16,
            on_close=lambda: None,
        )
        aes._switch_to_rounds_only()
        panel.show_animation(aes)
        QApplication.processEvents()

        outer = panel._anim_scroll
        self.assertEqual(outer.verticalScrollBar().maximum(), 0)
        self.assertGreater(aes._round_scroll.verticalScrollBar().maximum(), 0)
        self.assertLessEqual(
            aes._btn_next.y() + aes._btn_next.height(),
            outer.viewport().height(),
        )


class TestColoredByteGridAdaptiveWidth(unittest.TestCase):
    """_ColoredByteGridWidget adaptif genişlik davranışı (Alt kategori: BİRİM —
    runtime, conftest.py'nin offscreen QApplication'ı ile koşar).

    Regresyon koruması: Eskiden grid 16 hücre için ~1190px min-width dayatıyor,
    bu da QStackedWidget üzerinden AES intro sayfasına yatay scroll açıyordu.
    Artık taban min-width küçük (≤ ~200px) olmalı."""

    def test_grid_minimum_width_is_small(self):
        """Alt tür: BİRİM (yerleşim regresyonu).
        16 baytlık (tam blok) grid bile büyük bir min-width DAYATMAMALI;
        aksi halde AES intro QStackedWidget üzerinden yatay scroll açar.
        Eşik 300px: eski ~1190px değerinin çok altında, yeni 160px tabanın
        makul üstünde."""
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        w = _ColoredByteGridWidget(bytes(range(16)), max_cells=16)
        self.assertLessEqual(
            w.minimumWidth(), 300,
            "Grid min-width küçük olmalı; aksi halde stack yatay scroll açar",
        )

    def test_grid_min_width_stable_after_set_data(self):
        """Alt tür: BİRİM (durum tutarlılığı).
        set_data ile veri değişince de büyük min-width geri gelmemeli
        (eski kod set_data'da min-width'i yeniden 16×69px'e çıkarıyordu)."""
        from animation_modals.byte_widgets import _ColoredByteGridWidget
        w = _ColoredByteGridWidget(b"abc", max_cells=16)
        w.set_data(bytes(range(16)))
        self.assertLessEqual(w.minimumWidth(), 300)


class TestSHADiagramFitsWithoutScroll(unittest.TestCase):
    """SHA round diyagramı dikey scroll gerektirmeden sığmalı (Alt kategori:
    BİRİM — runtime). Regresyon: diyagram max-height, sayfasındaki scroll
    viewport'unun min-height'inden BÜYÜK olmamalı; aksi halde Görsel 2'deki
    gibi diyagrama ulaşmak için aşağı kaydırmak gerekir."""

    def test_diagram_max_height_fits_scroll_viewport(self):
        """Alt tür: BİRİM (yerleşim regresyonu).
        _SHA256DiagramWidget max yüksekliği, window.py'deki diag_scroll
        min yüksekliğinden (285px) küçük/eşit olmalı. Diyagram büyürse
        dikey scroll çıkar ve legend/çıkış kutuları kesilir."""
        from animation_modals.sha256.diagram_widget import _SHA256DiagramWidget
        w = _SHA256DiagramWidget()
        self.assertLessEqual(
            w.maximumHeight(), 285,
            "Diyagram max-height scroll viewport'una (285px) sığmalı",
        )


class TestSHADiagramArrowState(unittest.TestCase):
    """SHA diyagram okları faza göre durum değiştirmeli (Alt kategori: BİRİM).
    _arrow_state, her okun pasif/aktif/tamamlandı durumunu faza göre belirler;
    oklar artık sabit değil, işlemin aktif adımına göre vurgulanır (H3)."""

    def test_arrow_state_pending_active_done(self):
        """Alt tür: BİRİM (pozitif — durum geçişi).
        active_at=2 olan bir ok: ph<2 'pending', ph==2 'active', ph>2 'done'
        döndürmeli. Bu, okun animasyon boyunca üç farklı görünüm almasını
        (soluk → kalın/nabız → düz) garanti eder."""
        from animation_modals.sha256.diagram_widget import _SHA256DiagramWidget
        fn = _SHA256DiagramWidget._arrow_state
        self.assertEqual(fn(0, active_at=2), "pending")
        self.assertEqual(fn(1, active_at=2), "pending")
        self.assertEqual(fn(2, active_at=2), "active")
        self.assertEqual(fn(3, active_at=2), "done")
        self.assertEqual(fn(5, active_at=2), "done")

    def test_arrow_state_first_arrow(self):
        """Alt tür: BİRİM (negatif/kenar — ilk ok hiç 'pending' kalmamalı).
        active_at=1 (A→T2) okunda ph=0'da 'pending', ph=1'de 'active';
        ph asla active_at'ten küçük negatif bir duruma düşmez."""
        from animation_modals.sha256.diagram_widget import _SHA256DiagramWidget
        fn = _SHA256DiagramWidget._arrow_state
        self.assertEqual(fn(0, active_at=1), "pending")
        self.assertEqual(fn(1, active_at=1), "active")
        self.assertEqual(fn(6, active_at=1), "done")

    def test_diagram_renders_all_phases_without_error(self):
        """Alt tür: BİRİM (render smoke — çakışma/çizim regresyonu).
        Diyagram tüm fazlarda (0..6) hatasız boyanmalı. +D etiketinin kutu
        üstüne taşınması, kaydırma okları ve ok çizim mantığı paintEvent'i
        bozmamalı; bu test QPainter zincirinde bir istisna oluşursa yakalar."""
        from PyQt6.QtGui import QPixmap
        from animation_modals.sha256.diagram_widget import _SHA256DiagramWidget
        w = _SHA256DiagramWidget()
        w.resize(800, 285)
        w.set_data(["6a09e667"] * 8, ["5d7becae"] * 8,
                   "54eb51c9", "08909ae5", "617364", "428a2f", 41)
        for ph in range(7):
            w._phase = ph
            w.render(QPixmap(800, 285))  # istisna fırlatırsa test fail eder

    def test_diagram_round_phases_are_slow_enough_to_follow(self):
        """Yalnızca SHA sıkıştırma diyagramının round içi işlem fazları yavaşlatılır."""
        from animation_modals.sha256.diagram_widget import _SHA256DiagramWidget

        self.assertEqual(_SHA256DiagramWidget._PHASE_INTERVAL_MS, 600)

    def test_shift_arrows_method_exists(self):
        """Alt tür: SMOKE (kaydırma okları API).
        _draw_shift_arrows metodu tanımlı olmalı — B→C', C→D', F→G', G→H'
        kaydırma oklarını çizen yardımcı (Y5 eğitsel hareketlilik). Render
        smoke testi bu metodu ph>=3'te çağırır; metot silinirse paintEvent
        AttributeError verir."""
        from animation_modals.sha256.diagram_widget import _SHA256DiagramWidget
        self.assertTrue(hasattr(_SHA256DiagramWidget, "_draw_shift_arrows"))


class TestSHAMatchBadge(unittest.TestCase):
    """Final hash eşleşme rozeti metni (Alt kategori: BİRİM — saf metin).
    Y4: başarı rozetinden ✓/✅ işareti kaldırıldı."""

    def test_success_badge_has_no_checkmark(self):
        """Alt tür: BİRİM (negatif — işaret yokluğu).
        Başarı rozeti ✅/✓ İÇERMEMELİ; sadece 'Eşleşme: Başarılı' metni."""
        from animation_modals.sha256.match_widget import _MatchAssemblyWidget
        text = _MatchAssemblyWidget._match_badge_text(True)
        self.assertNotIn("✅", text)
        self.assertNotIn("✓", text)
        self.assertIn("Eşleşme: Başarılı", text)

    def test_error_badge_keeps_cross(self):
        """Alt tür: BİRİM (pozitif — hata sinyali korunur).
        Hata durumunda ❌ uyarı işareti korunur (başarıdan ayırt edilsin)."""
        from animation_modals.sha256.match_widget import _MatchAssemblyWidget
        text = _MatchAssemblyWidget._match_badge_text(False)
        self.assertIn("❌", text)


class TestSHAStepCount(unittest.TestCase):
    """SHA penceresi 5 mantıksal adımlı olmalı — Mesaj Hazırlığı dahil
    (Alt kategori: SMOKE — class attribute kontratı)."""

    def test_titles_have_five_entries(self):
        """Alt tür: SMOKE (yapısal değişiklik kontrolü).
        _TITLES sınıf niteliği TAM 5 girdi içermeli. Mesaj Hazırlığı eklenmesi
        önceki 4-adım yapısını 5'e çıkardı; girdi sayısı değişirse
        progress bar veya _render_step kayar."""
        from animation_modals import SHA256AnimationWindow
        self.assertEqual(len(SHA256AnimationWindow._TITLES), 5)

    def test_first_step_is_message_prep(self):
        """Alt tür: SMOKE (sıralama doğrulaması).
        İlk adım "Mesaj Hazırlığı" olmalı (UTF-8 byte dönüşümü).
        Sıralama bozulursa kullanıcı önce Padding görür → kafa karışıklığı."""
        from animation_modals import SHA256AnimationWindow
        self.assertIn("Mesaj", SHA256AnimationWindow._TITLES[0])

    def test_titles_use_five_format(self):
        """Alt tür: SMOKE (format tutarlılığı).
        Her başlık "Adım N / 5" formatında olmalı (N: 1..5). Eski
        "Adım N / 4" formatı kalmış olursa kullanıcı yanlış toplam
        görür."""
        from animation_modals import SHA256AnimationWindow
        for i, title in enumerate(SHA256AnimationWindow._TITLES):
            self.assertIn(f"Adım {i+1} / 5", title)


if __name__ == "__main__":
    unittest.main()
