# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from pathlib import Path 
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
shutil.copy('styles.css', str(release))

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

    # собираем "хлебные крошки"
    breadcrumb = BeautifulSoup(f'<ul></ul>', parser)
    for j in [x for x in i.find_all('a') if x.get('href', None) != None]:
        html = readhtml(j['href'])
        if html.find('nav', {'id': 'hor'}):
            breadcrumb.ul.extend(html.find('nav', {'id': 'hor'}).find_all('li'))
        else:
            breadcrumb.ul.extend(BeautifulSoup(f'<li><a href="{j['href']}">{j.text.strip()}</a></li>', parser))

    # переписываем "крошки" и боковое меню
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
        brd.nav.append(copy.copy(breadcrumb))
        html.find('div', {'id': 'content'}).insert_before(brd)
        savehtml(html, i.a['href'])

morelist = [x for x in template.find('nav', {'id': 'articles'}).find_all('a') if x['href'] not in ['k155.djvu', 're3a.html']]
morelist.extend([global_nav.find_all('a')[0], global_nav.find_all('a')[-1]])

# Переписываем "хлебные крошки" для вспомогательных материалов
for i in morelist:
    html = readhtml(i['href'])        
    brd = html.find('nav', {'id': 'breadcrumb'})
    if brd:
        brd.clear()
        brd.unwrap()
    brd = BeautifulSoup(f'<nav id="breadcrumb"></nav>', parser)
    brd.nav.append(copy.copy(template.find('nav', {'id': 'map'}).ul))
    html.find('div', {'id': 'content'}).insert_before(brd)
    savehtml(html, i['href'])

# Фильтация ссылок на самого себя и упаковка кода
# ==============================================================================

import htmlmin
import re

for i in Path('.').glob('*.html'):
    fname = str(i.name)
    html = BeautifulSoup(i.read_text(encoding = enc), parser)
    for link in html.find_all('a'):
        if link.get('href', '') == fname:
            del link.attrs['href']
    html.smooth()
    html_compact = ' '.join(str(html).replace('\n', ' ').split()).replace(' </', '</')
    html_compact = html_compact.replace('<b>', '') # это для исправления косяка в la3.html. Больше нигде не встречается
    for t in ['tr', 'th', 'td', 'ul', 'li']:
        html_compact = html_compact.replace(' <' + t, '<' + t).replace(' </' + t, '</' + t).replace(t + '> ', t + '>')
    for t in ['a', 'span', 'sub', 'sup']:
        html_compact = html_compact.replace(' </' + t, '</' + t)
        html_compact = re.sub('(<' + t + ' [^>]+>) +', r'\1', html_compact)
    Path(fname).write_text(htmlmin.minify(html_compact), enc)

print('complete')
