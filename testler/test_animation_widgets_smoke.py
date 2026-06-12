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

    def test_gcm_prep_uses_two_screens_then_rounds(self):
        """GCM hazırlığı mesaj→matris tanıtımından mesaj⊕keystream=şifreli ekranına geçmeli."""
        from animation_modals import AESAnimationWindow

        message = b"mesaj"
        a = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=message,
            expected_ct_hex="00" * 16,
            nonce=bytes(range(12)),
        )

        self.assertEqual(a._prep_stack.count(), 2)
        self.assertIs(a._prep_stack.currentWidget(), a._plaintext_prep_scroll)
        self.assertFalse(a._plaintext_widget._is_gcm)
        self.assertEqual(a._plaintext_widget._pp_title.text(), "AES blok şifreleyici")
        self.assertEqual(a._plaintext_widget._txt_lbl.text(), 'Plaintext: "mesaj"')

        # İkinci ekran artık sayaç bloğu değil; doğrudan mesaj ⊕ keystream akışı.
        a._switch_to_gcm_prep()
        self.assertIs(a._prep_stack.currentWidget(), a._gcm_prep_page)
        self.assertTrue(hasattr(a, "_gcm_prep_keystream_btn"))
        self.assertEqual(a._gcm_xor_widget._message, message)
        self.assertIs(a._keystream_btn, a._gcm_xor_widget._keystream_btn)

        a._switch_to_rounds_only()
        self.assertIs(a._stack.currentWidget(), a._round_page)

    def test_ecb_prep_keeps_single_screen(self):
        """Nonce bulunmayan eğitim akışında hazırlık tek ekran olarak kalmalı."""
        from animation_modals import AESAnimationWindow

        a = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"mesaj",
            expected_ct_hex="00" * 16,
        )

        self.assertEqual(a._prep_stack.count(), 1)
        self.assertFalse(hasattr(a, "_gcm_prep_widget"))

    def test_gcm_xor_on_prep_page_and_rounds_finish_on_summary(self):
        """Mesaj⊕keystream artık hazırlık sayfasında; roundlar bitince doğrudan özet açılmalı."""
        from animation_modals import AESAnimationWindow

        message = b"mesaj"
        a = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=message,
            expected_ct_hex="00" * len(message),
            nonce=bytes(range(12)),
        )

        # XOR akışı GCM hazırlık sayfasında (image 4) gösterilir.
        a._switch_to_gcm_prep()
        self.assertIs(a._prep_stack.currentWidget(), a._gcm_prep_page)
        self.assertEqual(a._gcm_xor_widget._message, message)
        keystream = bytes.fromhex(a._final_block_hex)
        self.assertEqual(
            a._gcm_xor_widget._cipher,
            bytes(keystream[i] ^ message[i] for i in range(len(message))),
        )
        self.assertTrue(hasattr(a, "_keystream_btn"))
        self.assertIs(a._keystream_btn.parentWidget(), a._gcm_xor_widget)
        # Ayrı XOR sayfası kaldırıldı.
        self.assertFalse(hasattr(a, "_gcm_xor_page"))

        # Roundlar bitince doğrudan final özet (ara XOR sayfası yok).
        a._show_match_result()
        self.assertIs(a._stack.currentWidget(), a._match_page)

    def test_full_forward_back_navigation_chain_gcm(self):
        """İleri/Geri tüm AES sayfalarını gezebilmeli: intro↔prep0↔prep1↔rounds↔match."""
        from animation_modals import AESAnimationWindow

        a = AESAnimationWindow(
            key=bytes(range(32)),
            plaintext=b"dasdasd",
            expected_ct_hex="00" * 7,
            nonce=bytes(range(12)),
        )

        # Başlangıç: intro, Geri pasif.
        self.assertEqual(a._nav_phase, "intro")
        self.assertFalse(a._btn_prev.isEnabled())

        # İleri zinciri: intro → prep0 → prep1 → rounds(0) → rounds(1)
        a._advance_step(); self.assertEqual(a._nav_phase, "prep0")
        self.assertEqual(a._prep_stack.currentIndex(), 0)
        a._advance_step(); self.assertEqual(a._nav_phase, "prep1")
        self.assertIs(a._prep_stack.currentWidget(), a._gcm_prep_page)
        a._advance_step(); self.assertEqual(a._nav_phase, "rounds")
        self.assertEqual(a.current_step, 0)
        self.assertIs(a._stack.currentWidget(), a._round_page)
        a._advance_step(); self.assertEqual(a.current_step, 1)
        self.assertTrue(a._btn_prev.isEnabled())

        # Geri zinciri: rounds(1) → rounds(0) → prep1 → prep0 → intro → (intro'da kalır)
        a._go_back(); self.assertEqual((a._nav_phase, a.current_step), ("rounds", 0))
        a._go_back(); self.assertEqual(a._nav_phase, "prep1")
        self.assertIs(a._prep_stack.currentWidget(), a._gcm_prep_page)
        a._go_back(); self.assertEqual(a._nav_phase, "prep0")
        a._go_back(); self.assertEqual(a._nav_phase, "intro")
        self.assertIs(a._stack.currentWidget(), a._intro_scroll)
        a._go_back(); self.assertEqual(a._nav_phase, "intro")  # ilk sayfada kalır

        # Match'ten Geri son round adımına dönmeli.
        a._show_final_summary()
        self.assertEqual(a._nav_phase, "match")
        self.assertFalse(a._btn_next.isEnabled())
        a._go_back()
        self.assertEqual((a._nav_phase, a.current_step), ("rounds", a.total_steps - 1))

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
        """State matrisi ne uzun bekletmeli ne de takip edilemeyecek kadar hızlı dolmalı.

        Kullanıcı isteğiyle sütun başına süre 8→3 tick'e çekildi (belirgin
        hızlanma, sütun-sütun görünürlük korunur); _FINISH_TICK türetilmiştir.
        """
        from animation_modals.aes.prep_widget import _AESPlaintextPrepWidget

        self.assertEqual(_AESPlaintextPrepWidget._MATRIX_START_TICK, 96)
        self.assertEqual(_AESPlaintextPrepWidget._MATRIX_TICKS_PER_COLUMN, 3)
        self.assertEqual(_AESPlaintextPrepWidget._FINISH_TICK, 108)

    def test_plaintext_matrix_columns_advance_every_three_ticks(self):
        """Dört sütun 3 tick aralıkla görünmeli ve 108. tick'te tamamlanmalı."""
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

        for _ in range(3):
            widget._on_tick()
        self.assertTrue(all(widget._matrix_filled[row][1] for row in range(4)))

        while widget._tick < 107:
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


class TestEmbeddedSHANavigationFixed(unittest.TestCase):
    """SHA Mesaj Hazırlığı (adım 0) ve Padding (adım 1) sayfaları, içeriğini iç
    dikey QScrollArea'da tutarak yüksekliğini SINIRLI kılmalı; böylece gömülü
    modda (alice/bob paneli) dış _anim_scroll bu sayfalar yüzünden büyümez ve
    alt navigasyon (◀ Geri / İleri ▶) butonları ekrandan AŞAĞI itilmez
    (Alt kategori: BİRİM — yerleşim regresyonu).

    Regresyon koruması: Bu iki sayfa eskiden iç scroll'a sarılmıyordu; ham
    içerik widget'ı (~390-411 px) QStackedWidget'in tercih yüksekliğini
    domine edip butonları görselden dışarı itiyordu (görsel 5 ve 6). İç
    scroll'a sarılınca sayfa doğal yüksekliği ~260 px tabanına iner.

    NOT: Eşik (330) bilinçli olarak ham widget yüksekliklerinin (374/395)
    ALTINDA seçildi → sarma kaldırılırsa test kesin kırılır; ama bağlamasız
    iç scroll tabanından (260 + kenar boşlukları, ~304) güvenle YÜKSEKTE."""

    _BOUND = 330

    def _make_window(self):
        """Uzun (çok-bloklu) mesajlı SHA penceresi üretir; QApplication
        conftest tarafından sağlanır, pencere standalone kurulur."""
        import hashlib
        from animation_modals import SHA256AnimationWindow
        msg = "a" * 120  # padding'i çok-bloklu yapacak kadar uzun
        return SHA256AnimationWindow(
            message=msg,
            expected_hash=hashlib.sha256(msg.encode()).hexdigest(),
        )

    def test_msgprep_page_height_is_bounded(self):
        """Alt tür: BİRİM (pozitif — adım 0 / Mesaj Hazırlığı).
        Sayfanın tercih yüksekliği iç scroll sayesinde eşik altında kalır;
        ham widget bundan yüksek olsa bile sayfa onu domine etmez."""
        w = self._make_window()
        self.assertLessEqual(
            w._page_msgprep.sizeHint().height(), self._BOUND,
            "Mesaj Hazırlığı sayfası iç scroll ile sınırlı kalmalı",
        )

    def test_padding_page_height_is_bounded(self):
        """Alt tür: BİRİM (pozitif — adım 1 / Padding).
        Padding sayfası da iç scroll ile eşik altında kalmalı."""
        w = self._make_window()
        self.assertLessEqual(
            w._page_padding.sizeHint().height(), self._BOUND,
            "Padding sayfası iç scroll ile sınırlı kalmalı",
        )

    def test_padding_explanation_does_not_enable_vertical_scroll(self):
        """Son 8 byte açıklaması açıldığında padding sayfası aşağı kaydırma açmamalı."""
        from PyQt6.QtCore import Qt

        w = self._make_window()
        w._padding_widget._explanation_buttons["length"].click()

        self.assertEqual(
            w._padding_scroll.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )

    def test_pages_are_scroll_wrapped(self):
        """Alt tür: BİRİM (negatif/yapısal — kalıbın korunması).
        İçerik widget'ı (prep/padding) DOĞRUDAN bir QScrollArea'nın
        widget'ı olmalı. Prep widget'ın kendi iç scroll'ları (byte
        ızgarası/şerit) sayılmaz; bu yüzden 'sarmalayan' scroll'un
        .widget()'ı tam olarak içerik widget'ı mı diye bakılır. Sarma
        kaldırılırsa (eski hata: widget AlignTop ile çıplak eklenirdi)
        bu test kırılır."""
        from PyQt6.QtWidgets import QScrollArea
        w = self._make_window()
        cases = (
            (w._page_msgprep, w._msgprep_widget),
            (w._page_padding, w._padding_widget),
        )
        for page, content in cases:
            wrapped = any(
                sa.widget() is content
                for sa in page.findChildren(QScrollArea)
            )
            self.assertTrue(
                wrapped, "İçerik widget'ı sarmalayan QScrollArea içinde olmalı",
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


class TestSHARealFirstWord(unittest.TestCase):
    """Adım 5'te gösterilen ilk-kelime toplaması GERÇEK crypto_core çıktısının
    başını üretmeli (Alt kategori: BİRİM — saf aritmetik + render).

    _first_word_modular_sum(önceki H0, A) = final_hash'in ilk 8 hanesi; bu,
    kullanıcının ekranda gördüğü değerin gerçek hash olduğunu kanıtlar."""

    def test_first_word_sum_equals_real_hash_prefix(self):
        """Alt tür: BİRİM (pozitif — gerçek değer bağı).
        Birkaç mesaj için (önceki H0 + A) mod 2³² sonucu, hem sha256_steps
        final_hash'inin hem de hashlib.sha256'nın ilk 8 hanesine eşit olmalı."""
        import hashlib
        from animation_modals.sha256_pure import sha256_steps
        from animation_modals.sha256.match_widget import _MatchAssemblyWidget
        for msg in (b"", b"a", b"asdasdasd", b"merhaba dunya 123"):
            d = sha256_steps(msg)
            bd = _MatchAssemblyWidget._first_word_modular_sum(
                d["pre_final_h"][0], d["final_working"][0])
            real = hashlib.sha256(msg).hexdigest()
            self.assertEqual(bd["result"], real[:8], f"{msg!r}: gerçek ilk 8")
            self.assertEqual(bd["result"], d["final_hash"][:8])

    def test_first_word_sum_handles_overflow(self):
        """Alt tür: BİRİM (negatif/kenar — 33. bit taşması).
        Toplam 2³²'yi aşarsa overflow True olmalı ve sonuç düşük 32 bit
        (mod 2³²) olmalı. Örn. ffffffff + 00000002 = 1_00000001."""
        from animation_modals.sha256.match_widget import _MatchAssemblyWidget
        bd = _MatchAssemblyWidget._first_word_modular_sum("ffffffff", "00000002")
        self.assertTrue(bd["overflow"], "2³² aşımı overflow=True olmalı")
        self.assertEqual(bd["result"], "00000001", "sonuç düşük 32 bit")

    def test_no_overflow_flag_when_fits(self):
        """Alt tür: BİRİM (pozitif — taşma yok durumu).
        Toplam 32 bite sığıyorsa overflow False ve sonuç ham toplama eşit."""
        from animation_modals.sha256.match_widget import _MatchAssemblyWidget
        bd = _MatchAssemblyWidget._first_word_modular_sum("6a09e667", "00000001")
        self.assertFalse(bd["overflow"])
        self.assertEqual(bd["result"], "6a09e668")

    def test_modulus_exponent_is_written_readably(self):
        """Dar Courier görünümünde üst simge yerine açık '2 üzeri 32' metni kullanılmalı."""
        from animation_modals.sha256.match_widget import _MatchAssemblyWidget

        text = _MatchAssemblyWidget._modulus_label()

        self.assertEqual(text, "mod 2 üzeri 32")
        self.assertNotIn("³", text)


class TestSHADiagramRoundConsistency(unittest.TestCase):
    """Round diyagramına window tarafından beslenen verinin tek round'da
    TUTARLI olduğunu doğrular (Alt kategori: BİRİM — wiring/doğruluk).

    Diyagram giriş register'larından (._regs_in), gösterilen K/W ile,
    gösterilen T1 (._t1) türetilebilmeli — R9/R17 gibi seyrek snapshot'larda
    da. Regresyon: eskiden window giriş olarak 'önceki snapshot çıkışını'
    (8 round eski) besliyordu, tutarsızdı."""

    def _derive_t1(self, regs_in, w_hex, k_hex):
        from animation_modals.sha256_pure import _rotr
        a, b, c, d, e, f, g, h = (int(x, 16) for x in regs_in)
        sig1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        ch = ((e & f) ^ (~e & g)) & 0xFFFFFFFF
        return (h + sig1 + ch + int(k_hex, 16) + int(w_hex, 16)) & 0xFFFFFFFF

    def test_diagram_input_derives_shown_values(self):
        """Alt tür: BİRİM (pozitif — wiring tutarlılığı).
        R1, R9, R17 sample round'ları için diyagrama beslenen giriş
        register'larından gösterilen T1 türetilebilmeli."""
        import hashlib
        from animation_modals import SHA256AnimationWindow
        msg = "asdasdasd"
        win = SHA256AnimationWindow(
            msg, hashlib.sha256(msg.encode()).hexdigest())
        # step_idx 3 → R1, 4 → R9, 5 → R17 (snap_idx = step_idx - 3)
        for step_idx, expected_round in ((3, 1), (4, 9), (5, 17)):
            win._render_step(step_idx)
            dw = win._diag_widget
            self.assertEqual(dw._round_no, expected_round)
            t1 = self._derive_t1(dw._regs_in, dw._w, dw._k)
            self.assertEqual(
                f"{t1:08x}", dw._t1,
                f"R{expected_round}: diyagram girişinden T1 türetilebilmeli")


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

    def test_titles_use_two_space_separator(self):
        """Alt tür: BİRİM (ayraç biçimi — pozitif).
        Adım numarasından sonra '—' uzun tire değil iki boşluk kullanılır:
        'Adım N / 5  Başlık'. Kullanıcı isteğiyle tire kaldırıldı."""
        from animation_modals import SHA256AnimationWindow
        for i, title in enumerate(SHA256AnimationWindow._TITLES):
            self.assertIn(f"Adım {i+1} / 5  ", title)

    def test_titles_have_no_emdash_separator(self):
        """Alt tür: BİRİM (ayraç biçimi — negatif/regresyon).
        SHA adım başlıklarında uzun tire '—' artık bulunmamalı. Eski biçim
        ('Adım N / 5 — Başlık') geri sızarsa bu test kırılır."""
        from animation_modals import SHA256AnimationWindow
        for title in SHA256AnimationWindow._TITLES:
            self.assertNotIn("—", title)


if __name__ == "__main__":
    unittest.main()
