# arayuz/__init__.py
"""
Kullanıcı arayüzü katmanı.

İçindekiler:
    alice_panel : Alice gönderim paneli (e-posta + RSA imza + AES şifreleme akışı)
    bob_panel   : Bob alım paneli (AES çözme + RSA imza doğrulama akışı)
    theme       : Renk paleti, tipografi, global stylesheet
    toast       : Doğrulama/hata bildirim widget'ları

Kullanım:
    from arayuz.alice_panel import AlicePanel
    from arayuz.theme import COLORS
"""
