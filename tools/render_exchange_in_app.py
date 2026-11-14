#!/usr/bin/env python3
"""Render Биржа inside the existing Vkus main window (no Toplevel)."""
from pathlib import Path
import sys, tkinter as tk
from types import MethodType
from PIL import ImageGrab
# The visual harness does not exercise Selenium; provide import-only stubs.
import types
mods = ['selenium','selenium.webdriver','selenium.webdriver.firefox','selenium.webdriver.firefox.options','selenium.webdriver.firefox.service','selenium.webdriver.support','selenium.webdriver.support.ui','selenium.webdriver.common','selenium.webdriver.common.by','selenium.webdriver.common.keys','selenium.common','selenium.common.exceptions']
for name in mods: sys.modules.setdefault(name, types.ModuleType(name))
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
from vkus.app import VkusApp
from vkus.exchange_visual import install_exchange_visuals

class Harness:
    def __init__(self, geometry='1600x920'):
        self.root = tk.Tk()
        self.root.title('Vkus — in-app Биржа smoke test')
        self.root.geometry(geometry + '+0+0')
        self.root.configure(bg='#00030a')
        self.app_header = tk.Frame(self.root, bg='#07162f', height=72)
        self.app_header.pack(fill='x'); self.app_header.pack_propagate(False)
        tk.Label(self.app_header, text='Vkus', bg='#07162f', fg='#cf74ff',
                 font=('DejaVu Sans', 22, 'bold')).pack(side='left', padx=20)
        body=tk.Frame(self.root,bg='#00030a'); self.body=body; body.pack(fill='both',expand=True)
        body.grid_rowconfigure(0,weight=1); body.grid_columnconfigure(1,weight=1)
        self.sidebar=tk.Frame(body,bg='#061226',width=190); self.sidebar.grid(row=0,column=0,sticky='ns'); self.sidebar.grid_propagate(False)
        for name in ('Первичная настройка','Поиск','Сообщения','Биржа','О программе'):
            tk.Label(self.sidebar,text=name,bg='#061226',fg='#eef5ff',anchor='w',padx=14,pady=13).pack(fill='x')
        self.main=tk.Frame(body,bg='#030817'); self.main.grid(row=0,column=1,sticky='nsew',padx=10,pady=10)
        self.right=None; self.nav_buttons={}; self.exchange_page=None
        self._set_nav_active=MethodType(VkusApp._set_nav_active,self)
        self._clear_main=MethodType(VkusApp._clear_main,self)
        for name in ('_show_exchange','_exchange_redraw','_exchange_click','_exchange_entry_focus_in','_exchange_entry_focus_out','_exchange_find','_exchange_menu','_exchange_set_filter','_exchange_info'):
            setattr(self,name,MethodType(getattr(VkusApp,name),self))
        install_exchange_visuals()
    def run(self,out):
        self._show_exchange(); self.root.update_idletasks(); self.root.update()
        assert self.exchange_page.winfo_exists()
        assert (ROOT / 'vkus/assets/exchange_neon_background.png').exists()
        assert (ROOT / 'vkus/assets/russia_activity_map.png').exists()
        assert self.exchange_canvas.winfo_toplevel() is self.root
        assert not any(isinstance(w, tk.Toplevel) for w in self.root.winfo_children())
        # Exercise the in-page source/category hitboxes and filter state.
        from types import SimpleNamespace
        scale, ox, oy, _rw, _rh = self.exchange_geometry
        def click_virtual(vx, vy):
            self._exchange_click(SimpleNamespace(x=int(ox + (vx-8)*scale),
                                                  y=int(oy + (vy-8)*scale),
                                                  x_root=0, y_root=0))
        click_virtual(365, 650)  # VK source on
        assert 'VK' in self.exchange_sources_selected
        click_virtual(365, 650)  # VK source off
        assert 'VK' not in self.exchange_sources_selected
        click_virtual(1400, 447)  # first category toggle
        assert 'Заявки на услуги и ремонт' not in self.exchange_categories_selected
        click_virtual(1400, 447)  # restore default
        assert 'Заявки на услуги и ремонт' in self.exchange_categories_selected
        self._exchange_set_filter('Город', 'Орск')
        assert self.exchange_city == 'Орск'
        self._exchange_set_filter('Город', 'Оренбург')
        self.exchange_chart_period = 'Неделя'
        click_virtual(1505, 760)
        assert self.exchange_chart_period == 'Месяц'
        click_virtual(1565, 760)
        assert self.exchange_chart_period == 'Год'
        self.exchange_chart_period = 'Неделя'
        self._exchange_redraw()
        visible_text = [self.exchange_canvas.itemcget(item, 'text')
                        for item in self.exchange_canvas.find_all()
                        if self.exchange_canvas.type(item) == 'text']
        assert 'ГРАФИК АНАЛИЗА ГОРОДА' in visible_text
        assert all(name in visible_text for name in ('VK', 'Telegram', 'Avito', 'YouDo', 'Профи.ру'))
        self.root.update_idletasks(); self.root.update()
        print('INTERACTION_CHECKS=source_toggle,category_toggle,filter_change,chart_period_week_month_year,platform_kpis PASS')
        self.root.after(500, lambda: self.capture(out))
        self.root.mainloop()
    def capture(self,out):
        self.root.update_idletasks(); self.root.update()
        x,y=self.root.winfo_rootx(),self.root.winfo_rooty()
        im=ImageGrab.grab(bbox=(x,y,x+self.root.winfo_width(),y+self.root.winfo_height())).convert('RGB')
        im.save(out)
        print(f'IN_APP_SCREENSHOT={out} SIZE={im.width}x{im.height} TOPLEVELS=0')
        self.root.destroy()
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default='/mnt/data/Vkus_3.21_Birzha_launch.png'); ap.add_argument('--geometry',default='1600x920'); args=ap.parse_args()
    Harness(args.geometry).run(args.output)
