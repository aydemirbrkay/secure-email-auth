# arayuz/constants.py
"""Ana pencere yerleşim sabitleri.

main_gui.py içinde dağınık duran pencere boyutu / kenar boşluğu (margin) /
aralık (spacing) magic number'ları burada tek noktada isimlendirilir.
Yalnızca isimlendirme amaçlıdır; sayısal değerler ve davranış değişmez.
"""
from __future__ import annotations

# Ana pencere minimum boyutu (piksel).
MAIN_WINDOW_MIN_WIDTH = 1200
MAIN_WINDOW_MIN_HEIGHT = 750

# Merkez yerleşim kenar boşluğu (sol, üst, sağ, alt — hepsi eşit) ve dikey aralık.
MAIN_LAYOUT_MARGIN = 16
MAIN_LAYOUT_SPACING = 10

# Alice | Bob bölücüsü (splitter): tutamaç genişliği ve başlangıç panel boyutları.
SPLITTER_HANDLE_WIDTH = 3
SPLITTER_INITIAL_PANEL_WIDTH = 600

# Alt kontrol butonları satırının yatay aralığı.
CONTROLS_SPACING = 12
