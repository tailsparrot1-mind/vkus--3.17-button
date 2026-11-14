#!/usr/bin/env python3
from pathlib import Path
import sys, types, tkinter as tk
from PIL import ImageGrab
mods=['selenium','selenium.webdriver','selenium.webdriver.firefox','selenium.webdriver.firefox.options','selenium.webdriver.firefox.service','selenium.webdriver.support','selenium.webdriver.support.ui','selenium.webdriver.common','selenium.webdriver.common.by','selenium.webdriver.common.keys','selenium.common','selenium.common.exceptions']
for n in mods: sys.modules.setdefault(n,types.ModuleType(n))
sys.modules['selenium'].webdriver=sys.modules['selenium.webdriver']
sys.modules['selenium.webdriver.firefox.options'].Options=type('Options',(),{})
sys.modules['selenium.webdriver.firefox.service'].Service=type('Service',(),{})
sys.modules['selenium.webdriver.support.ui'].WebDriverWait=type('WebDriverWait',(),{})
sys.modules['selenium.webdriver.common.by'].By=type('By',(),{})
sys.modules['selenium.webdriver.common.keys'].Keys=type('Keys',(),{})
sys.modules['selenium.common.exceptions'].TimeoutException=type('TimeoutException',(Exception,),{})
sys.modules['selenium.common.exceptions'].WebDriverException=type('WebDriverException',(Exception,),{})
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from vkus.exchange_visual import install_exchange_visuals
from vkus.app import VkusApp
install_exchange_visuals()
app=VkusApp(); app.lock.dispose(); app.lock=None; app.root.geometry('1672x941+0+0'); app._build_style(); app._build_ui(); app._show_exchange(); app.root.update()
scale,ox,oy,rw,rh=app.exchange_geometry
app._exchange_click(type('E',(),{'x':int(ox+(1264-8)*scale),'y':int(oy+(650-8)*scale),'x_root':0,'y_root':0})())
app.root.update(); wins=[w for w in app.root.winfo_children() if isinstance(w,tk.Toplevel)]
assert len(wins)==1
win=wins[0]
labels=[]
def walk(w):
    for c in w.winfo_children():
        if isinstance(c,tk.Label): labels.append(c.cget('text'))
        walk(c)
walk(win)
for name in ['Яндекс','Google','Одноклассники','Юла','Ещё одна площадка','В разработке']:
    assert name in labels, (name,labels)
box=(win.winfo_rootx(),win.winfo_rooty(),win.winfo_rootx()+win.winfo_width(),win.winfo_rooty()+win.winfo_height())
ImageGrab.grab(bbox=box).convert('RGB').save('/mnt/data/Vkus_3.23_MORE_SOURCES.png')
print('MORE_SOURCES_POPUP=button_click, 5_cards, all_expected_labels PASS')
app.root.destroy()
