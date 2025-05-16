# -*- coding: utf-8 -*-

from gettext import find
import requests
from bs4 import BeautifulSoup
from pathlib import Path 
import sys
import re
import subprocess
import shutil

enc = 'utf-8'
parser = 'html.parser'

release=Path('release')
first_src=Path('chipinfo')
second_src=Path('microshemca')

# Скраппинг
# ==============================================================================

# subprocess.run(["python", f'kiloom_scrap.py'])
# subprocess.run(["python", f'{first_src}_scrap.py'])
# subprocess.run(["python", f'{second_src}_scrap.py'])

# Копирование файлов в релиз
# ==============================================================================

release.mkdir(parents=True, exist_ok=True)

src = [i for i in first_src.glob('*') if not '.html.htm' in str(i)]
for i in src:
    if (str(i.name) == 'index.html') or (not '.html' in str(i.name)):
        shutil.copy(str(i), str(release))
    else:
        release.joinpath(f'k155{i.name}').write_bytes(i.read_bytes())

src = [i for i in second_src.glob('*') if not '.htm' in str(i) or '.html' in str(i)]
for i in src:
    shutil.copy(str(i), str(release))

shutil.copy('dc.html', str(release))
shutil.copy('k155.djvu', str(release))

# Совмещение навигации
# ==============================================================================

import os
os.chdir(release)

first_nav = BeautifulSoup(Path('index.html').read_text(encoding = enc), parser).find('nav').find('ul').find_all('li')[1:-1]
second_nav = BeautifulSoup(Path('ttl.html').read_text(encoding = enc), parser).find('nav').find('ul').find_all('li')[1:-1]

scnd_nav = [i.a.get('href') for i in second_nav]

table = BeautifulSoup(f'<table></table>', parser)

for i in first_nav:
    src, title, text = i.a.get('href'), i.a.get('title'), i.a.text.strip()
    i.clear()
    if Path(src).exists():
        i.append(BeautifulSoup(f'<td><a href="k155{src}" title="{title}">{text}</a></td><td><a href="{src}" title="{title}">{text}</a></td>', parser))
        if src in scnd_nav: scnd_nav.remove(src)
    else:
        i.append(BeautifulSoup(f'<td><a href="k155{src}" title="{title}">{text}</a></td><td>{text}</td>', parser))
    i.name = 'tr'
    table.table.append(i)
    while len(scnd_nav) and not Path('k155' + scnd_nav[0]).exists():
        src = scnd_nav[0]

        if src != "ru1-3.html":
            # формируем текст ссылки
            repl = {'a': 'а', 'g': 'г', 'p': 'п', 'i': 'и', 'v': 'в', 'd': 'д', 'e': 'е', 'm': 'м', 'r': 'р', 'l': 'л', 'n': 'н', 'u': 'у', 't': 'т', 'k': 'к'}
            text = Path(src).stem
            for k, v in repl.items():
                text = text.replace(k, v)
            text = f'к155{text}'.upper()
            
            table.table.append(BeautifulSoup(f'<tr><td>{text}</td><td><a href="{src}">{text}</a></td></tr>', parser))
        scnd_nav.remove(src)

# Ручне исправление исключений
for i in table.table:
    if i.find_all('td')[1].text.strip() == 'К155ИЕ7':
        td = i.find_all('td')[1]
        td.clear()
        td.append(BeautifulSoup(f'<a href="ie6.html" title="{i.td.a.get('title')}">К155ИЕ7</a>', parser))

    if i.find_all('td')[1].text.strip() == 'К155РУ1':
        td = i.find_all('td')[1]
        td.clear()
        td.append(BeautifulSoup(f'<a href="ru1-3.html" title="{i.td.a.get('title')}">К155РУ1-3</a>', parser))

# Отладка

table.smooth()
Path('../table.html').write_text(table.prettify(), enc)

print('complete')
