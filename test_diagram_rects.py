# test_diagram_rects.py
"""DIAGRAM_RECTS listesinin geçerliliğini test eder — display gerektirmez."""

DIAGRAM_W = 623
DIAGRAM_H = 283

# Spec'ten koordinatlar — bob_panel.py ile senkron tutulmalı
DIAGRAM_RECTS_RAW = [
    (95, 78, 95, 38),    # 0: SHA-256
    (195, 78, 80, 38),   # 1: RSA İmza
    (268, 108, 44, 44),  # 2: Birleştir (+)
    (330, 90, 85, 38),   # 3: AES
    (330, 155, 85, 38),  # 4: RSA Anahtar
    (408, 118, 158, 62), # 5: Gönder / Internet
]


def test_rect_count():
    assert len(DIAGRAM_RECTS_RAW) == 6, "Alice'in 6 adımına karşılık 6 rect olmalı"


def test_rects_positive_dimensions():
    for i, (x, y, w, h) in enumerate(DIAGRAM_RECTS_RAW):
        assert w > 0 and h > 0, f"Rect {i}: genişlik ve yükseklik pozitif olmalı"


def test_rects_within_image_bounds():
    for i, (x, y, w, h) in enumerate(DIAGRAM_RECTS_RAW):
        assert x >= 0 and y >= 0, f"Rect {i}: koordinatlar negatif olamaz"
        assert x + w <= DIAGRAM_W, f"Rect {i}: sağ kenar ({x+w}) görsel genişliğini ({DIAGRAM_W}) aşıyor"
        assert y + h <= DIAGRAM_H, f"Rect {i}: alt kenar ({y+h}) görsel yüksekliğini ({DIAGRAM_H}) aşıyor"


def test_image_file_exists():
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alice and bob.png")
    assert os.path.isfile(path), f"Görsel dosyası bulunamadı: {path}"
