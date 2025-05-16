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

def readhtml(s: str):
    return BeautifulSoup(Path(s).read_text(encoding = enc), parser)

def savehtml(html, s: str):
    html.smooth()
    Path(s).write_text(html.prettify(), enc)

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
release.joinpath('more.html').write_bytes(Path('template.html').read_bytes())

# Совмещение навигации
# ==============================================================================

import os
os.chdir(release)

first_nav = readhtml('index.html').find('nav').find('ul').find_all('li')[1:-1]
second_nav = readhtml('ttl.html').find('nav').find('ul').find_all('li')[1:-1]

scnd_nav = [i.a.get('href') for i in second_nav]

global_nav = BeautifulSoup(f'<ul></ul>', parser)

for i in first_nav:
    src, title, text = i.a.get('href'), i.a.get('title'), i.a.text.strip()
    i.clear()
    if Path(src).exists():
        i.append(BeautifulSoup(f'<a href="k155{src}" title="{title}">{text}</a><a href="{src}" title="{title}">{text}</a>', parser))
        if src in scnd_nav: scnd_nav.remove(src)
    else:
        i.append(BeautifulSoup(f'<a href="k155{src}" title="{title}">{text}</a><a>{text}</a>', parser))
    global_nav.ul.append(i)
    while len(scnd_nav) and not Path('k155' + scnd_nav[0]).exists():
        src = scnd_nav[0]

        if src != "ru1-3.html":
            # формируем текст ссылки
            repl = {'a': 'а', 'g': 'г', 'p': 'п', 'i': 'и', 'v': 'в', 'd': 'д', 'e': 'е', 'm': 'м', 'r': 'р', 'l': 'л', 'n': 'н', 'u': 'у', 't': 'т', 'k': 'к'}
            text = Path(src).stem
            for k, v in repl.items():
                text = text.replace(k, v)
            text = f'к155{text}'.upper()

            global_nav.ul.append(BeautifulSoup(f'<li><a>{text}</a><a href="{src}">{text}</a></li>', parser))
        scnd_nav.remove(src)

# Ручное исправление исключений
for i in global_nav.ul:
    if i.find_all('a')[1].text.strip() == 'К155ИЕ7':
        a = i.find_all('a')[1]
        a['href'] = 'ie6.html'
        a['title'] = str(i.a['title'])

    if i.find_all('a')[1].text.strip() == 'К155РУ1':
        a = i.find_all('a')[1]
        a['href'] = 'ru1-3.html'
        a['title'] = str(i.a['title'])
        a.string = 'К155РУ1-3'

# Переписывание меню навигации и "хлебных крошек"
# ==============================================================================

import copy

template = readhtml('../template.html')

global_nav.ul.insert(0, copy.copy(template.find('nav').find_all('li')[0]))
global_nav.ul.append(copy.copy(template.find('nav').find_all('li')[1]))

for i in global_nav.ul:
    breadcrumb = BeautifulSoup(f'<ul></ul>', parser)
    for j in [x for x in i.find_all('a') if x.get('href', None) != None]:
        html = readhtml(j['href'])
        if html.find('nav', {'id': 'hor'}):
            breadcrumb.ul.extend(html.find('nav', {'id': 'hor'}).find_all('li'))
        else:
            breadcrumb.ul.extend(BeautifulSoup(f'<li><a href="{j['href']}">{j.text.strip()}</a></li>', parser))

    for i in breadcrumb.ul:
        html = readhtml(i.a['href'])        
        ul = html.find('nav', {'id': 'map'}).ul
        ul.clear()
        ul.extend(copy.copy(global_nav.ul))
        hor = html.find('nav', {'id': 'hor'})
        if hor:
            hor.clear()
            hor.unwrap()
        brd = BeautifulSoup(f'<nav id="breadcrumb"></nav>', parser)
        brd.append(copy.copy(breadcrumb))
        html.find('div', {'id': 'content'}).insert_before(brd)
        savehtml(html, i.a['href'])

# Отладка
# ==============================================================================

savehtml(global_nav, '../table.html')

print('complete')
