# animation_modals/aes/constants.py
"""AES animasyonu paylaşılan sabitleri."""
from __future__ import annotations
from ..base import ANIM_COLORS

# AES-256 round sayısı (Nr). Final round MixColumns içermez.
AES_NUM_ROUNDS = 14  # FIPS 197 §5.1
# Final round indeksi (rounds_data 0..AES_NUM_ROUNDS şeklinde indekslenir).
AES_FINAL_ROUND_INDEX = AES_NUM_ROUNDS

_COLORS_OP = {
    "SubBytes":    ANIM_COLORS["accent_yellow"],
    "ShiftRows":   ANIM_COLORS["accent_blue"],
    "MixColumns":  ANIM_COLORS["accent_mauve"],
    "AddRoundKey": ANIM_COLORS["accent_peach"],
}

