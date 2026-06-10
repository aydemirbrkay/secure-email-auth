"""
accessibility.py – Erişilebilirlik (a11y) Yardımcıları
=======================================================

Bu modül üç şey sağlar:
  * ``set_accessible`` — bir widget'a Türkçe erişilebilir ad/açıklama atar
    (ekran okuyucular ``accessibleName`` / ``accessibleDescription`` okur).
  * ``build_tab_order`` — verilen sırayla mantıksal Tab gezinme zinciri kurar.
  * ``ReduceMotionSettings`` — "Hareketi Azalt" tercihini ``QSettings`` ile
    kalıcı tutar; fotosensitif kullanıcılar için hızlı/titreşimli animasyonlar
    yavaşlatılır veya kapatılır.

Renk körü palet / yüksek kontrast kapsam dışıdır (mevcut palet yeterli).
"""
from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QWidget


def set_accessible(widget: QWidget, name: str, description: str = "") -> None:
    """Widget'a erişilebilir ad (ve isteğe bağlı açıklama) atar.
    Türkçe metin verilir; ekran okuyucu bu adı seslendirir."""
    widget.setAccessibleName(name)
    if description:
        widget.setAccessibleDescription(description)


def build_tab_order(*widgets: QWidget) -> None:
    """Verilen widget'ları sırayla Tab gezinme zincirine bağlar.
    İkiden az widget verilirse hiçbir şey yapmaz."""
    for current, nxt in zip(widgets, widgets[1:]):
        QWidget.setTabOrder(current, nxt)


class ReduceMotionSettings:
    """"Hareketi Azalt" tercihinin kalıcı durumunu yönetir.

    QSettings anahtarı: ``reduce_motion`` (bool). Açıkken animasyon tick'leri
    yavaşlatılır (bkz. ``arayuz.theme.get_animation_tick_ms``) ve titreşim/
    blink efektleri kapatılabilir (``motion_effects_enabled``)."""

    _KEY = "reduce_motion"

    def __init__(self) -> None:
        # INI formatı kayıt defteri erişimine bağlı değildir ve tüm
        # platformlarda aynı kalıcılık sözleşmesini sağlar.
        self._settings = QSettings(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            "ErciyesBM",
            "SecureEmail",
        )
        self._enabled: bool = self.load()

    def load(self) -> bool:
        """Kalıcı değeri okuyup belleğe alır ve döndürür."""
        self._enabled = self._settings.value(self._KEY, False, type=bool)
        return self._enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        """Tercihi günceller ve kalıcılaştırır."""
        self._enabled = bool(value)
        self._settings.setValue(self._KEY, self._enabled)
        self._settings.sync()


# Uygulama geneli tek örnek. theme.get_animation_tick_ms ve menü eylemi bunu
# paylaşır; böylece tercih tek yerden okunur/yazılır.
REDUCE_MOTION = ReduceMotionSettings()


def motion_effects_enabled() -> bool:
    """Titreşim/blink gibi dikkat dağıtıcı efektler açık mı?
    Hareket azaltma açıkken False döner."""
    return not REDUCE_MOTION.is_enabled()
