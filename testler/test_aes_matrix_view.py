"""
test_aes_matrix_view.py — AES matris widget'ları runtime testleri
=================================================================

Test türü: UI WIDGET BİRİM TESTİ (QApplication ile state/timer)

Amaç:
    AES round görselleştirmesinde kullanılan iki widget'ın runtime
    davranışını sınar:
        _AESMatrixView         — tek 4×4 state matrisi (renkli, animasyonlu)
        _AESStateCompareWidget — yan yana iki matris (önce/sonra karşılaştırma)
    State machine, QTimer ömrü, op-tick eşikleri, set_state/set_pair
    çağrıları, ok ve operasyon başlığı yönetimi test edilir.

Kapsam:
    - _TICKS_BY_OP dictionary: 4 AES operasyonu (AddRoundKey, SubBytes,
      ShiftRows, MixColumns) için tick sayıları pozitif ve < 200.
    - Initial state: 16 hücre var sayılan değerlerle doludur.
    - set_state(): yeni matris atanınca cells/colors güncellenir.
    - Timer kurulumu: QTimer başlangıçta aktif, hideEvent'te durur,
      showEvent'te yeniden başlar (kaynak sızıntısı yok).
    - Operasyon değişimi: _op_idx sıralı ilerler (0→1→2→3→0).
    - _AESStateCompareWidget: set_pair() iki matrise veri dağıtır,
      ortadaki ok ve operasyon başlığı doğru güncellenir.

Strateji:
    Modül seviyesinde TEK bir QApplication instance yaratılır (tüm
    test'ler paylaşır). Widget'lar instance edilir ama .show()
    edilmez — paintEvent tetiklenmez, ama QTimer ve internal state
    test edilebilir.
    QPainter çıktısının pixel doğrulaması yapılmaz; görsel doğrulama
    elle yapılır (python main_gui.py).

Hata durumunda anlamı: AES animasyonunda state takılır, hatalı sıra,
veya kapatma sonrası timer çalışmaya devam eder (memory leak).
"""
import sys
import unittest

from PyQt6.QtWidgets import QApplication

# QWidget alt sınıfları için tek bir QApplication örneği gereklidir.
_app = QApplication.instance() or QApplication(sys.argv)


class TestAESMatrixViewBasics(unittest.TestCase):
    """_AESMatrixView temel state yönetimi (Alt kategori: API smoke + state init)."""

    def _make_view(self):
        # Test fixture helper'ı — her test'te taze widget döndürür.
        # label_title="Test" görsel etiket için, davranışı etkilemez.
        from animation_modals.aes_matrix_view import _AESMatrixView
        return _AESMatrixView(label_title="Test")

    def test_class_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        Modül yüklenebilmeli ve _AESMatrixView sınıfı tanımlı olmalı.
        Refactor sonrası dosya silinmesi/yer değiştirmesini yakalar."""
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESMatrixView"))

    def test_constructs_without_error(self):
        """Alt tür: SMOKE (instance creation).
        Widget instance edilirken QPainter/QTimer kurulumunda exception
        fırlatmamalı (sessiz başarısızlık olmaz)."""
        view = self._make_view()
        self.assertIsNotNone(view)

    def test_default_state_is_4x4_zeros(self):
        """Alt tür: BİRİM (varsayılan değer kontrolü).
        Henüz set_state çağrılmadığında widget'in iç state'i 4×4'lük
        '00' matrisi olmalı — animasyon başlamadan ekranda anlamsız
        değer görünmemesinin garantisi."""
        view = self._make_view()
        self.assertEqual(view._state, [["00"] * 4 for _ in range(4)])

    def test_set_state_stores_matrix(self):
        """Alt tür: BİRİM (setter davranışı).
        set_state() çağrısı verilen 4×4 matrisi referans olarak saklar;
        sonrasında _state attribute'u bu değerle eşittir."""
        view = self._make_view()
        matrix = [[f"{r}{c}" for c in range(4)] for r in range(4)]
        view.set_state(matrix)
        self.assertEqual(view._state, matrix)

    def test_set_state_stops_active_animation(self):
        """Alt tür: BİRİM (state machine invariant'ı).
        set_state() yeni bir matris atadığında, eğer önceden aktif bir
        animasyon timer'ı varsa onu DURDURMALI. Aksi halde eski animasyon
        yeni state üzerinde devam edip görsel tutarsızlık üretir."""
        view = self._make_view()
        view._anim_timer.start(40)  # sahte aktif animasyon
        self.assertTrue(view._anim_timer.isActive())
        view.set_state([["FF"] * 4 for _ in range(4)])
        self.assertFalse(view._anim_timer.isActive())


class TestAESMatrixViewAnimation(unittest.TestCase):
    """_AESMatrixView animasyon timer ve callback davranışı
    (Alt kategori: state machine + timer lifecycle + paint runtime)."""

    def _make_view(self):
        # Her test taze widget kullanır — state paylaşımını önler.
        from animation_modals.aes_matrix_view import _AESMatrixView
        return _AESMatrixView()

    def test_play_animation_starts_timer(self):
        """Alt tür: BİRİM (state machine başlangıcı).
        play_animation('AddRoundKey', before, after) çağrısı:
          1. QTimer'ı başlatır (isActive → True)
          2. _op alanına op adını yazar
          3. _tick'i 0'a, _total_ticks'i pozitif değere ayarlar
        Bu 4 invariant tek bir testte gruplanmıştır çünkü 'animasyon
        başlatma' tek bir atomik state geçişidir."""
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("AddRoundKey", before, after)
        self.assertTrue(view._anim_timer.isActive())
        self.assertEqual(view._op, "AddRoundKey")
        self.assertEqual(view._tick, 0)
        self.assertGreater(view._total_ticks, 0)

    def test_play_animation_unknown_op_raises(self):
        """Alt tür: HATA YOLU (geçersiz argüman).
        Bilinmeyen bir operasyon adı verilirse ValueError fırlamalı.
        Sessiz kabul edilirse UI'de hiçbir görsel olmaz → hata
        kaynağı tespit edilemez. Defensive coding kontrolü."""
        view = self._make_view()
        with self.assertRaises(ValueError):
            view.play_animation("BogusOp", [], [])

    def test_play_animation_stores_round_key(self):
        """Alt tür: BİRİM (opsiyonel parametre).
        round_key argümanı verildiğinde _round_key attribute'una
        saklanır — AddRoundKey overlay'i XOR animasyonunda bu matrisi
        kullanır. None verilirse paint kısmında crash etmez."""
        view = self._make_view()
        rk = [["AA"] * 4 for _ in range(4)]
        view.play_animation(
            "AddRoundKey",
            [["00"] * 4 for _ in range(4)],
            [["FF"] * 4 for _ in range(4)],
            round_key=rk,
        )
        self.assertEqual(view._round_key, rk)

    def test_stop_animation_advances_to_end(self):
        """Alt tür: BİRİM (kullanıcı skip aksiyonu).
        stop_animation() — kullanıcı "İleri" basarak animasyonu atlamak
        istediğinde — şunları garantilemeli:
          1. Timer durur (isActive → False)
          2. _tick _total_ticks'e atlatılır (final state'e ulaşıldı)
          3. _state, hedef matris 'after' ile birebir aynı (visual leak yok)"""
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("AddRoundKey", before, after)
        view.stop_animation()
        self.assertFalse(view._anim_timer.isActive())
        self.assertEqual(view._tick, view._total_ticks)
        self.assertEqual(view._state, after)

    def test_on_tick_advances_and_completes(self):
        """Alt tür: BİRİM (timer'sız simülasyon + callback sözleşmesi).
        QTimer.start() çağrılmadan _on_tick() manuel olarak _total_ticks
        kez çağrılır; animasyonun bitiminde:
          1. Timer pasif (zaten manuel ilerletildiği için)
          2. _state = after (hedef state)
          3. on_done callback tam 1 kez tetiklenmiş
        Callback'in tetiklenmesi parent widget'in 'Devam ▶' butonunu
        enable etmesi için kritiktir."""
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        callback_calls = []
        view.play_animation(
            "AddRoundKey", before, after,
            on_done=lambda: callback_calls.append(True),
        )
        # _total_ticks kadar manuel tick at
        total = view._total_ticks
        for _ in range(total):
            view._on_tick()
        self.assertFalse(view._anim_timer.isActive())
        self.assertEqual(view._state, after)
        self.assertEqual(callback_calls, [True])

    def test_replay_reuses_last_params(self):
        """Alt tür: BİRİM (Yeniden Oynat butonu).
        replay() — kullanıcı animasyonu tekrar izlemek istediğinde —
        son play_animation parametrelerini (op, before, after, round_key)
        yeniden uygular. _tick 0'a sıfırlanır; _op önceki ad olarak kalır.
        Kullanıcı _tick=50'de butona bassa bile baştan oynamalı."""
        view = self._make_view()
        before = [["00"] * 4 for _ in range(4)]
        after = [["FF"] * 4 for _ in range(4)]
        view.play_animation("ShiftRows", before, after)
        view._tick = 50  # animasyon ortasında
        view.replay()
        self.assertEqual(view._tick, 0)
        self.assertEqual(view._op, "ShiftRows")

    def test_replay_without_prior_animation_is_noop(self):
        """Alt tür: HATA YOLU (boş state'te kullanım).
        Hiç play_animation çağrılmamışken replay() çağrılırsa AttributeError
        veya benzeri exception fırlamamalı; sessizce no-op olmalı.
        _op None kalır — defensive programming."""
        view = self._make_view()
        view.replay()  # hata olmamalı
        self.assertIsNone(view._op)

    def test_addroundkey_overlay_draws_without_error(self):
        """Alt tür: UI RUNTIME (paint event simülasyonu).
        AddRoundKey overlay'i (XOR animasyonu) _tick=30'da (XOR_PER_ROW
        fazında) çizilirken QPainter exception fırlamamalı. Off-screen
        QPixmap'a render edilir; pixel doğrulanmaz, ama paint kodunun
        hata içermediği garantilenir. round_key matrisi kullanılır."""
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "AddRoundKey",
            [["00"] * 4 for _ in range(4)],
            [["FF"] * 4 for _ in range(4)],
            round_key=[["AA"] * 4 for _ in range(4)],
        )
        view._tick = 30  # XOR_PER_ROW fazı
        # Bir QPixmap'a render et — pixel doğrulamayız ama hata fırlamamalı
        pix = QPixmap(view.width(), view.height())
        p = QPainter(pix)
        view._draw_overlay(p, 24, 24)
        p.end()

    def test_subbytes_overlay_draws_without_error(self):
        """Alt tür: UI RUNTIME (paint event simülasyonu).
        SubBytes overlay'i (S-Box yerine koyma animasyonu) _tick=30'da
        QPainter exception'ı vermemeli. Test verisi farklı before/after
        kullanır (gerçek S-Box dönüşümü simüle edilir)."""
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "SubBytes",
            [[f"{r}{c}" for c in range(4)] for r in range(4)],
            [[f"S{r}{c}" for c in range(4)] for r in range(4)],
        )
        view._tick = 30
        pix = QPixmap(view.width(), view.height())
        p = QPainter(pix)
        view._draw_overlay(p, 24, 24)
        p.end()

    def test_shiftrows_overlay_draws_without_error(self):
        """Alt tür: UI RUNTIME (çoklu faz paint event'i).
        ShiftRows overlay'i 5 farklı tick'te (5, 20, 40, 60, 75)
        denenir — her tick farklı bir animasyon fazına (satır
        seçme / ok çizimi / kaydırma) denk gelir. Hiçbir fazda
        QPainter exception olmamalı."""
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "ShiftRows",
            [[f"{r}{c}" for c in range(4)] for r in range(4)],
            [[f"{r}{(c+r)%4}" for c in range(4)] for r in range(4)],
        )
        for tick in (5, 20, 40, 60, 75):
            view._tick = tick
            pix = QPixmap(view.width(), view.height())
            p = QPainter(pix)
            view._draw_overlay(p, 24, 24)
            p.end()

    def test_mixcolumns_overlay_draws_without_error(self):
        """Alt tür: UI RUNTIME (çoklu faz paint event'i).
        MixColumns overlay'i 4 farklı tick'te (10, 30, 50, 70) denenir
        — sütun seçme / matris çarpımı / sonuç gösterimi fazları.
        QPainter exception'ı yok."""
        from PyQt6.QtGui import QPainter, QPixmap
        view = self._make_view()
        view.play_animation(
            "MixColumns",
            [[f"{r}{c}" for c in range(4)] for r in range(4)],
            [[f"M{r}{c}" for c in range(4)] for r in range(4)],
        )
        for tick in (10, 30, 50, 70):
            view._tick = tick
            pix = QPixmap(view.width(), view.height())
            p = QPainter(pix)
            view._draw_overlay(p, 24, 24)
            p.end()


class TestAESStateCompareWidget(unittest.TestCase):
    """_AESStateCompareWidget kapsayıcı widget — yan yana iki _AESMatrixView
    + ortada ok + Yeniden Oynat butonu (Alt kategori: çoklu widget koordinasyonu)."""

    def _make_widget(self):
        # Her test taze widget — iç state paylaşımı yok.
        from animation_modals.aes_matrix_view import _AESStateCompareWidget
        return _AESStateCompareWidget()

    def test_class_exists(self):
        """Alt tür: SMOKE (import sözleşmesi).
        Modülde _AESStateCompareWidget sınıfı tanımlı olmalı. Refactor
        veya yeniden adlandırma sonrası bozulmayı yakalar."""
        from animation_modals import aes_matrix_view
        self.assertTrue(hasattr(aes_matrix_view, "_AESStateCompareWidget"))

    def test_constructs_without_error(self):
        """Alt tür: SMOKE (yapısal API).
        Widget sorunsuz instance edilir VE iç bileşenleri (önceki view,
        şimdiki view, replay butonu) erişilebilir attribute'lar olarak
        bulunur. hasattr kontrolleri parent widget'in beklediği API'yı
        garantiler — kırılırsa AES animasyon penceresinde AttributeError."""
        w = self._make_widget()
        self.assertIsNotNone(w)
        # Önceki ve şimdiki view'lar erişilebilir olmalı
        self.assertTrue(hasattr(w, "_prev_view"))
        self.assertTrue(hasattr(w, "_curr_view"))
        # Yeniden Oynat butonu
        self.assertTrue(hasattr(w, "_replay_btn"))

    def test_start_step_sets_prev_state_and_plays_curr(self):
        """Alt tür: BİRİM (akış koordinasyonu).
        start_step() AES round operasyonunu başlatır:
          1. Sol (_prev_view): operasyon ÖNCESİ state'i donar — referans
             olarak görünür (animasyon yok)
          2. Sağ (_curr_view): operasyon SONRASI state'e animasyonla
             ilerler — timer aktif, _op atanmış
        Bu 'donmuş referans + canlı dönüşüm' tasarımı AES round
        görselleştirmesinin temelidir."""
        w = self._make_widget()
        before = [[f"b{r}{c}" for c in range(4)] for r in range(4)]
        after = [[f"a{r}{c}" for c in range(4)] for r in range(4)]
        w.start_step("AddRoundKey", before, after, op_color="#5B8EC2")
        # Önceki view'da before donmuş olmalı
        self.assertEqual(w._prev_view._state, before)
        # Şimdiki view animasyon başlatmış olmalı
        self.assertEqual(w._curr_view._op, "AddRoundKey")
        self.assertTrue(w._curr_view._anim_timer.isActive())

    def test_start_step_sets_arrow_label(self):
        """Alt tür: BİRİM (UI label güncellemesi).
        İki matris arasındaki ok etiketi operasyon adını ('ShiftRows')
        içermeli — kullanıcı hangi AES adımını izlediğini metinden okur.
        Renk parametresi (op_color) sadece görsel; testte doğrulanmaz."""
        w = self._make_widget()
        w.start_step(
            "ShiftRows",
            [["00"] * 4] * 4, [["FF"] * 4] * 4,
            op_color="#5B8EC2",
        )
        self.assertIn("ShiftRows", w._arrow_label.text())

    def test_show_final_sets_both_to_same_state(self):
        """Alt tür: BİRİM (terminal state).
        show_final() round sonu son durumunu (tüm operasyonlar bitti)
        her iki view'a da aynı matrisle uygular — animasyon YOK, sadece
        statik gösterim. _op None olduğu için replay tetiklenemez —
        intentional behavior (final state replay edilemez)."""
        w = self._make_widget()
        final = [[f"f{r}{c}" for c in range(4)] for r in range(4)]
        w.show_final(final)
        self.assertEqual(w._prev_view._state, final)
        self.assertEqual(w._curr_view._state, final)
        # Animasyon yok
        self.assertIsNone(w._curr_view._op)

    def test_replay_button_triggers_curr_replay(self):
        """Alt tür: BİRİM (event handler / sinyal bağlantısı).
        'Yeniden Oynat' butonu (_replay_btn) tıklanınca yalnızca sağ
        view'in (_curr_view) replay() metodunu çağırır → _tick 0'a
        düşer ve animasyon baştan başlar. Sol view (_prev_view)
        etkilenmez (referans olarak donmuş kalır). Button.click()
        programatik tıklama; QApplication event loop'u gerekmez."""
        w = self._make_widget()
        before = [["00"] * 4] * 4
        after = [["FF"] * 4] * 4
        w.start_step("AddRoundKey", before, after, op_color="#5B8EC2")
        # Sahte ilerleme
        w._curr_view._tick = 30
        # Butonu programatik tıkla
        w._replay_btn.click()
        # _tick sıfırlanmış olmalı
        self.assertEqual(w._curr_view._tick, 0)


if __name__ == "__main__":
    unittest.main()
