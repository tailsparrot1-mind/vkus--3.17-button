#!/usr/bin/env python3
"""Launch the real VkusApp window for Exchange UI verification.
Selenium imports are stubbed only for this UI-only run; no browser operation is invoked.
"""
from pathlib import Path
import sys, types, tkinter as tk
from types import SimpleNamespace
from PIL import ImageGrab
from tkinter import messagebox, ttk

mods = [
    'selenium','selenium.webdriver','selenium.webdriver.firefox',
    'selenium.webdriver.firefox.options','selenium.webdriver.firefox.service',
    'selenium.webdriver.support','selenium.webdriver.support.ui',
    'selenium.webdriver.common','selenium.webdriver.common.by',
    'selenium.webdriver.common.keys','selenium.common',
    'selenium.common.exceptions'
]
for name in mods:
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules['selenium'].webdriver = sys.modules['selenium.webdriver']
sys.modules['selenium.webdriver.firefox.options'].Options = type('Options', (), {})
sys.modules['selenium.webdriver.firefox.service'].Service = type('Service', (), {})
sys.modules['selenium.webdriver.support.ui'].WebDriverWait = type('WebDriverWait', (), {})
sys.modules['selenium.webdriver.common.by'].By = type('By', (), {})
sys.modules['selenium.webdriver.common.keys'].Keys = type('Keys', (), {})
sys.modules['selenium.common.exceptions'].TimeoutException = type('TimeoutException', (Exception,), {})
sys.modules['selenium.common.exceptions'].WebDriverException = type('WebDriverException', (Exception,), {})

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vkus.exchange_visual import install_exchange_visuals
from vkus.app import VkusApp
install_exchange_visuals()

def main(out, geometry):
    app = VkusApp()
    app.lock.dispose()
    app.lock = None
    app.root.geometry(geometry + '+0+0')
    app._build_style()
    app._build_ui()
    app._show_exchange()
    app.root.update_idletasks()
    app.root.update()
    assert app.exchange_canvas.winfo_toplevel() is app.root
    assert not any(isinstance(w, tk.Toplevel) for w in app.root.winfo_children())
    scale, ox, oy, _rw, _rh = app.exchange_geometry
    def click(vx, vy):
        app._exchange_click(SimpleNamespace(
            x=int(ox + (vx-8)*scale), y=int(oy + (vy-8)*scale),
            x_root=0, y_root=0))
    # Exercise actual in-app controls, not only a detached canvas.
    click(650, 650)
    assert 'Avito' not in app.exchange_sources_selected
    click(650, 650)
    assert 'Avito' in app.exchange_sources_selected
    first_category = 'Потенциальные покупатели'
    click(1400, 447)
    assert first_category not in app.exchange_categories_selected
    click(1400, 447)
    assert first_category in app.exchange_categories_selected
    # KPI cards have no DEMO labels; the lower-right block follows the reference options card.
    texts = [app.exchange_canvas.itemcget(item, 'text') for item in app.exchange_canvas.find_all()
             if app.exchange_canvas.type(item) == 'text']
    assert 'ДЕМО' not in texts
    assert 'Опции анализа' in texts
    assert 'ГРАФИК АНАЛИЗА ГОРОДА' not in texts
    # The Exchange CTA opens the actual local-first demand/supply board.
    click(1480, 670)
    market_windows = [w for w in app.root.winfo_children()
                      if isinstance(w, tk.Toplevel) and w.title() == 'Vkus — Биржа объявлений']
    assert len(market_windows) == 1
    market_window = market_windows[0]
    assert any(isinstance(w, ttk.Treeview) for w in market_window.winfo_children()[0].winfo_children()
               for w in w.winfo_children()) or any(isinstance(w, ttk.Treeview)
               for w in market_window.winfo_children()[0].winfo_children())
    market_window.destroy()
    app.root.update_idletasks(); app.root.update()
    app._exchange_set_filter('Город', 'Орск')
    assert app.exchange_city == 'Орск'
    app._exchange_set_filter('Город', 'Оренбург')
    # Selected-source search captures exactly the chosen platform.
    app.exchange_query_var.set('цветочный магазин')
    captured.clear()
    click(1100, 460)
    assert app.exchange_search_request['scope'] == 'selected'
    assert app.exchange_search_request['sources'] == ['Avito']
    # Global search includes all six first-line sources at once.
    click(1250, 460)
    assert app.exchange_search_request['scope'] == 'all'
    assert app.exchange_search_request['sources'] == ['VK','Telegram','Avito','YouDo','Профи.ру','Форумы']
    # Lower-right settings action remains interactive.
    click(1485, 867)
    messagebox.showinfo = old_showinfo
    app.exchange_entry.delete(0, 'end')
    app.exchange_entry.insert(0, app.exchange_query_placeholder)
    app.exchange_entry.configure(fg='#9aaed6')
    app.root.update_idletasks(); app.root.update()
    # Verify the in-app shell can be restored and the Exchange can be reopened.
    app._restore_main_shell()
    app.root.update_idletasks(); app.root.update()
    assert app.app_header.winfo_ismapped() and app.body.winfo_ismapped() and app.app_footer.winfo_ismapped()
    app._show_messages()
    app.root.update_idletasks(); app.root.update()
    assert app.messages_page is not None and app.messages_page.winfo_exists()
    app._show_search()
    app.root.update_idletasks(); app.root.update()
    assert app.search_page is not None and app.search_page.winfo_exists()
    app._show_exchange()
    app.root.update_idletasks(); app.root.update()
    assert not app.app_footer.winfo_ismapped()
    x,y=app.root.winfo_rootx(),app.root.winfo_rooty()
    im=ImageGrab.grab(bbox=(x,y,x+app.root.winfo_width(),y+app.root.winfo_height())).convert('RGB')
    im.save(out)
    print(f'FULL_APP_UI_SCREENSHOT={out} SIZE={im.width}x{im.height}')
    print('FULL_APP_UI_CHECKS=real_VkusApp_window,source_toggle,category_toggle,city_filter,selected_source_audience_search,all_sources_audience_search,reference_analysis_options,messages_search_navigation,shell_restore_footer,TOPLEVELS=0 PASS')
    app.root.destroy()

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='/mnt/data/Vkus_3.21_FULL_APP_launch.png')
    p.add_argument('--geometry',default='1672x941')
    a=p.parse_args()
    main(a.output,a.geometry)
