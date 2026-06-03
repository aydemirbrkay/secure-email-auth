import re
import unittest


class TestThemeEngine(unittest.TestCase):
    HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

    def test_both_palettes_have_same_keys(self):
        from arayuz import theme
        self.assertEqual(set(theme._DARK.keys()), set(theme._LIGHT.keys()))

    def test_all_values_hex(self):
        from arayuz import theme
        for pal in (theme._DARK, theme._LIGHT):
            for k, v in pal.items():
                self.assertRegex(v, self.HEX, f"{k}={v!r}")

    def test_set_mode_mutates_in_place(self):
        from arayuz import theme
        colors_obj = theme.COLORS
        anim_obj = theme.ANIM_COLORS
        theme.MANAGER.set_mode("light")
        self.assertIs(colors_obj, theme.COLORS)
        self.assertIs(anim_obj, theme.ANIM_COLORS)
        self.assertEqual(theme.COLORS["bg_main"], theme._LIGHT["bg_main"])
        theme.MANAGER.set_mode("dark")

    def test_anim_colors_is_full_palette(self):
        from arayuz import theme
        self.assertEqual(set(theme.ANIM_COLORS.keys()), set(theme.COLORS.keys()))

    def test_anim_colors_has_legacy_required_keys(self):
        from arayuz import theme
        required = {
            "bg_main", "bg_card", "bg_input", "text_primary", "text_secondary",
            "text_muted", "accent_blue", "accent_green", "accent_yellow",
            "accent_mauve", "accent_peach", "border",
        }
        self.assertTrue(required.issubset(set(theme.ANIM_COLORS.keys())))

    def test_step_colors_update_in_place(self):
        from arayuz import theme
        lst = theme.STEP_COLORS_ALICE
        theme.MANAGER.set_mode("light")
        self.assertIs(lst, theme.STEP_COLORS_ALICE)
        self.assertEqual(lst[0], theme.COLORS[theme._ALICE_KEYS[0]])
        theme.MANAGER.set_mode("dark")

    def test_global_stylesheet_rebuilds(self):
        from arayuz import theme
        theme.MANAGER.set_mode("dark")
        dark_ss = theme.build_global_stylesheet()
        theme.MANAGER.set_mode("light")
        light_ss = theme.build_global_stylesheet()
        self.assertNotEqual(dark_ss, light_ss)
        theme.MANAGER.set_mode("dark")

    def test_alice_identity_is_mauve(self):
        from arayuz import theme
        self.assertEqual(theme._ALICE_KEYS[0], "accent_mauve")
