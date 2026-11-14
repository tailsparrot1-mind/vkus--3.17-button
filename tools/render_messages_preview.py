#!/usr/bin/env python3
"""Render the actual Vkus Messages page under Xvfb without starting Firefox."""
from pathlib import Path
import sys, types, argparse
import tkinter as tk
from PIL import ImageGrab

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# UI-only smoke tests do not need Selenium or a browser. Provide import-time
# placeholders; no browser method is invoked by this preview.
def module(name):
    m = types.ModuleType(name); sys.modules[name] = m; return m
selenium = module('selenium')
webdriver = module('selenium.webdriver'); selenium.webdriver = webdriver
common = module('selenium.webdriver.common')
by = module('selenium.webdriver.common.by'); by.By = type('By', (), {'ID':'id','XPATH':'xpath','CSS_SELECTOR':'css selector','TAG_NAME':'tag name'})
keys = module('selenium.webdriver.common.keys'); keys.Keys = type('Keys', (), {'ENTER':'ENTER','CONTROL':'CONTROL'})
firefox = module('selenium.webdriver.firefox')
opts = module('selenium.webdriver.firefox.options'); opts.Options = type('Options', (), {})
service = module('selenium.webdriver.firefox.service'); service.Service = type('Service', (), {})
support = module('selenium.webdriver.support'); ui = module('selenium.webdriver.support.ui'); ui.WebDriverWait = type('WebDriverWait', (), {})
exc = module('selenium.common.exceptions'); exc.TimeoutException = type('TimeoutException', (Exception,), {}); exc.WebDriverException = type('WebDriverException', (Exception,), {})

from vkus.app import VkusApp, BG


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='/mnt/data/Vkus_3.17_Messages.png')
    args = parser.parse_args()
    root = tk.Tk(); root.title('Vkus — Сообщения'); root.geometry('1672x941+0+0'); root.configure(bg=BG)
    app = VkusApp.__new__(VkusApp)
    # An honest empty-state preview: no invented leads or fake message history.
    app.message_contacts = []
    app.chat_history = {}
    app._messages_page(root)
    root.update_idletasks(); root.update()
    def capture():
        root.update_idletasks(); root.update()
        image = ImageGrab.grab(bbox=(0, 0, 1672, 941)).convert('RGB')
        if image.size != (1672, 941):
            raise RuntimeError(f'Unexpected screenshot size: {image.size}')
        # Verify the title and both major work areas have visible non-background pixels.
        title_region = image.crop((300, 65, 900, 170))
        chat_region = image.crop((620, 180, 1650, 850))
        if len(title_region.getcolors(1000000) or []) < 8 or len(chat_region.getcolors(1000000) or []) < 8:
            raise RuntimeError('Messages UI did not render expected content regions')
        output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output)
        print(f'SCREENSHOT={output.resolve()} SIZE=1672x941 BYTES={output.stat().st_size}')
        root.destroy()
    root.after(1000, capture)
    root.mainloop()

if __name__ == '__main__': main()
