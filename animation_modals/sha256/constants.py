# animation_modals/sha256/constants.py
"""SHA-256 animasyonu paylaşılan sabitleri."""
from __future__ import annotations

# SHA-256 sıkıştırma fonksiyonu round sayısı (her 512-bit blok için).
SHA256_NUM_ROUNDS = 64  # FIPS 180-4 §6.2.2

_SNAPS_PER_BLOCK = 9  # rounds 1,9,17,25,33,41,49,57,64

# Renk eşlemesi — her register farklı renk
_REG_COLORS = [
    "#3B6FA0",  # A — blue
    "#7B5EA7",  # B — mauve
    "#4E8B60",  # C — green
    "#B8860B",  # D — yellow
    "#B87333",  # E — peach
    "#3D8B80",  # F — teal
    "#B94A4A",  # G — red
    "#2E86AB",  # H — sky
]
_REG_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H"]

