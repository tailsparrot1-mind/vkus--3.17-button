#!/usr/bin/env python3
"""UI behavior smoke test; uses fake records and never contacts VK."""
from pathlib import Path
import sys, types, tkinter as tk
PROJECT_ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(PROJECT_ROOT))
def module(name):
    m=types.ModuleType(name); sys.modules[name]=m; return m
selenium=module('selenium'); webdriver=module('selenium.webdriver'); selenium.webdriver=webdriver
module('selenium.webdriver.common')
by=module('selenium.webdriver.common.by'); by.By=type('By',(),{'ID':'id','XPATH':'xpath','CSS_SELECTOR':'css selector','TAG_NAME':'tag name'})
keys=module('selenium.webdriver.common.keys'); keys.Keys=type('Keys',(),{'ENTER':'ENTER','CONTROL':'CONTROL'})
module('selenium.webdriver.firefox'); opts=module('selenium.webdriver.firefox.options'); opts.Options=type('Options',(),{})
svc=module('selenium.webdriver.firefox.service'); svc.Service=type('Service',(),{})
module('selenium.webdriver.support'); ui=module('selenium.webdriver.support.ui'); ui.WebDriverWait=type('WebDriverWait',(),{})
exc=module('selenium.common.exceptions'); exc.TimeoutException=type('TimeoutException',(Exception,),{}); exc.WebDriverException=type('WebDriverException',(Exception,),{})
from vkus.app import VkusApp, BG
root=tk.Tk(); root.geometry('1200x800'); root.configure(bg=BG)
app=VkusApp.__new__(VkusApp)
app.message_contacts=[
 {'name':'Анна Смирнова','preview':'Настройка рекламы','stamp':'Сегодня','interest':'Заявка'},
 {'name':'Илья Петров','preview':'Ремонт ноутбука','stamp':'Вчера','interest':'Горячий интерес'},
]
app.chat_history={}
app._messages_page(root); root.update_idletasks(); root.update()
assert len(app.message_contact_buttons)==2
app.message_list_filter_var.set('петров'); app._filter_message_contacts()
root.update_idletasks()
assert app.message_contact_buttons['Илья Петров'].winfo_manager()=='pack'
assert app.message_contact_buttons['Анна Смирнова'].winfo_manager()==''
app.message_list_filter_var.set(''); app._filter_message_contacts(); root.update_idletasks()
assert all(card.winfo_manager()=='pack' for card in app.message_contact_buttons.values())
app._select_conversation('Илья Петров'); root.update_idletasks()
assert app.chat_name.cget('text')=='Илья Петров'
print('PASS: contact list, text filter, clear filter, conversation selection')
root.destroy()
