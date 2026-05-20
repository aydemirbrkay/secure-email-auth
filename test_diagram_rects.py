# test_diagram_rects.py
"""DIAGRAM_RECTS listesinin geçerliliğini test eder — display gerektirmez."""

DIAGRAM_W = 623
DIAGRAM_H = 283

# bob_panel.py _STEP_RECTS ile senkron tutulmalı — piksel kalibrasyonu 2752×1536 görselinden
DIAGRAM_RECTS_RAW = [
    (178, 100, 39, 19),   # 0: SHA-256 H(.)
    (223, 100, 39, 18),   # 1: RSA İmza K_A^-(.)
    (250, 124, 34, 23),   # 2: Birleştir sol ⊕
    (363, 124, 39, 19),   # 3: AES K_S(.)
    (363, 174, 40, 22),   # 4: RSA Anahtar K_B^+(.)
    (437, 133, 178, 52),  # 5: Gönder sağ ⊕ + Internet
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
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "görseller", "alice and bob.png",
    )
    assert os.path.isfile(path), f"Görsel dosyası bulunamadı: {path}"
