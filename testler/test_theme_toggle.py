import unittest

# Headless/offscreen ortam ve tek QApplication örneği conftest.py'deki
# session kapsamlı autouse `qapp` fixture'ı tarafından sağlanır.


class TestThemeToggle(unittest.TestCase):
    def test_construct_and_click_toggles_mode(self):
        from arayuz import theme
        from arayuz.theme_toggle import ThemeToggle
        theme.MANAGER.set_mode("dark")
        tg = ThemeToggle()
        start = theme.MANAGER.mode
        tg.click()
        self.assertNotEqual(theme.MANAGER.mode, start)
        theme.MANAGER.set_mode("dark")
