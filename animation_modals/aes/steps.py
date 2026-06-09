# animation_modals/aes/steps.py
"""AES round adım listesi oluşturucu."""
from __future__ import annotations
from .constants import _COLORS_OP

def _build_steps(rounds_data: list[dict]) -> list[dict]:
    steps: list[dict] = []
    for rd in rounds_data:
        rnd = rd["round"]
        if rnd == 0:
            steps.append({
                "round": 0, "operation": "AddRoundKey",
                "matrix": rd["after_add_round_key"],
                "color": _COLORS_OP["AddRoundKey"],
                "description": "Round 0 — Initial AddRoundKey\nPlaintext, ilk round anahtarı ile XOR'landı.",
            })
        elif rnd <= 13:
            for op, key, desc in [
                ("SubBytes",   "after_sub_bytes",    f"Round {rnd} — SubBytes\nHer byte S-Box'taki karşılığıyla değiştirildi."),
                ("ShiftRows",  "after_shift_rows",   f"Round {rnd} — ShiftRows\nSatır 1: sabit, 2: 1←, 3: 2←, 4: 3← kaydı."),
                ("MixColumns", "after_mix_columns",  f"Round {rnd} — MixColumns\nHer sütun GF(2⁸) matris çarpımıyla karıştırıldı."),
                ("AddRoundKey","after_add_round_key",f"Round {rnd} — AddRoundKey\nState, {rnd}. round anahtarı ile XOR'landı."),
            ]:
                steps.append({
                    "round": rnd, "operation": op,
                    "matrix": rd[key],
                    "color": _COLORS_OP[op],
                    "description": desc,
                })
        else:
            for op, key, desc in [
                ("SubBytes",   "after_sub_bytes",    "Round 14 — SubBytes  (Son round)"),
                ("ShiftRows",  "after_shift_rows",   "Round 14 — ShiftRows"),
                ("AddRoundKey","after_add_round_key","Round 14 — AddRoundKey  (MixColumns yok)"),
            ]:
                steps.append({
                    "round": rnd, "operation": op,
                    "matrix": rd[key],
                    "color": _COLORS_OP[op],
                    "description": desc,
                })
    return steps

