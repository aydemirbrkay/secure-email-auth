# test_diagram_rects.py
"""DIAGRAM_RECTS listesinin geçerliliğini test eder — display gerektirmez."""

DIAGRAM_W = 623
DIAGRAM_H = 283

# Spec'ten koordinatlar — bob_panel.py ile senkron tutulmalı
DIAGRAM_RECTS_RAW = [
    (97, 127, 102, 22),   # 0: SHA-256
    (200, 127, 42, 22),   # 1: RSA İmza
    (231, 149, 26, 24),   # 2: Birleştir (+)
    (306, 123, 52, 22),   # 3: AES
    (303, 175, 54, 22),   # 4: RSA Anahtar
    (385, 142, 138, 36),  # 5: Gönder / Internet
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
