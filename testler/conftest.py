"""
conftest.py — Headless (display'siz) GUI test desteği
=====================================================

Bu dosya, PyQt6 widget testlerinin görüntü sunucusu (X/Wayland/Windows
masaüstü) olmadan koşabilmesini sağlar. İki sorumluluğu vardır:

1. **Offscreen platform ayarı:** Herhangi bir PyQt6 modülü import edilmeden
   ÖNCE ``QT_QPA_PLATFORM=offscreen`` ortam değişkenini ayarlar. Böylece
   testler ``QT_QPA_PLATFORM`` env'i elle verilmeden de headless koşar.
   ``setdefault`` kullanıldığı için kullanıcı dışarıdan başka bir platform
   verdiyse (örn. CI'da farklı bir backend) ona dokunulmaz.

2. **Tek QApplication örneği:** ``qapp`` session fixture'ı, tüm test oturumu
   için tek bir ``QApplication`` instance'ı garanti eder. ``autouse`` olduğu
   için ``unittest.TestCase`` tabanlı testler dahil her test başlamadan önce
   QApplication hazır olur (bu testler fixture parametresi alamaz).
"""
from __future__ import annotations

import os
import tempfile

# PyQt6 import'larından ÖNCE çalışmalı: QPA platform eklentisi QApplication
# ilk oluşturulduğunda seçilir; sonradan değiştirilemez.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

# Testler kullanıcı kayıt defterine/ayar dizinine dokunmadan kalıcılığı sınar.
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(
    QSettings.Format.IniFormat,
    QSettings.Scope.UserScope,
    tempfile.mkdtemp(prefix="secure-email-qsettings-"),
)


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Tüm oturum için tek QApplication örneği sağlar.

    Zaten bir instance varsa onu yeniden kullanır; yoksa oluşturur. Qt,
    süreç başına tek QApplication'a izin verir; bu yüzden session kapsamı
    ve paylaşımlı instance zorunludur. ``autouse`` sayesinde pytest
    fonksiyon-stili testler ``qapp`` parametresi almasa da, ve
    ``unittest.TestCase`` testleri de QApplication'lı bir ortamda koşar.
    """
    app = QApplication.instance() or QApplication([])
    yield app
    # Teardown: süreç sonunda Qt kendi temizliğini yapar; instance'ı burada
    # quit/exit etmek diğer testleri etkileyebileceğinden bilinçli olarak
    # kapatmıyoruz.
