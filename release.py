# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from pathlib import Path 
import shutil
import subprocess

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

# subprocess.run(["python", f'kiloom_scrap.py'], cwd = 'kiloom')
# subprocess.run(["python", f'{first_src}_scrap.py'], cwd = first_src)
# subprocess.run(["python", f'junradio_scrap.py'], cwd = 'junradio')
# subprocess.run(["python", f'{second_src}_scrap.py'], cwd = second_src)

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

for i in Path('junradio').glob('*.jpg'):
    shutil.copy(str(i), str(release))

shutil.copy('k155.djvu', str(release))
shutil.copy('styles.css', str(release))

# Совмещение навигации
# ==============================================================================

import os
os.chdir(release)

first_nav = readhtml('index.html').find('nav').find('ul').find_all('li')[1:]
second_nav = readhtml('ttl.html').find('nav').find('ul').find_all('li')[1:]

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
    if i.find_all('a')[1].text.strip() == 'К155ИЕ6':
        a = i.find_all('a')[1]
        a.string = 'К155ИЕ6-7'

    if i.find_all('a')[1].text.strip() == 'К155ИЕ7':
        a = i.find_all('a')[1]
        a.string = 'К155ИЕ6-7'
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

for i in global_nav.ul:

    # собираем "хлебные крошки"
    breadcrumb = BeautifulSoup(f'<ul></ul>', parser)
    for j in [x for x in i.find_all('a') if x.get('href', None) != None]:
        html = readhtml(j['href'])
        if html.find('nav', {'id': 'hor'}):
            breadcrumb.ul.extend(html.find('nav', {'id': 'hor'}).find_all('li'))
        else:
            breadcrumb.ul.extend(BeautifulSoup(f'<li><a href=\"{j["href"]}\">{j.text.strip()}</a></li>', parser))

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

# Кастомные хлебные крошки
for i in ['k155ie6', 'k155ie7', 'ie6', '74192', '74193']:
    html = readhtml(f'{i}.html')
    brd = html.find('nav', {'id': 'breadcrumb'}).ul
    brd.clear()
    brd.extend(BeautifulSoup(f'<li><a href="k155ie6.html">К155ИЕ6</a></li><li><a href="k155ie7.html">К155ИЕ7</a></li><li><a href="ie6.html">К155ИЕ6-7</a></li><li><a href="74192.html">74192</a></li><li><a href="74193.html">74193</a></li>', parser))
    if i == 'ie6':
        brd = html.find_all('nav', {'id': 'breadcrumb'})[1]
        brd.clear()
        brd.unwrap()
    savehtml(html, f'{i}.html')

# Работа с дополнительными материалами
# ==============================================================================

# Формирование страницы dc.html
html = readhtml(str(Path('..').joinpath('dc.html')))
dc = copy.copy(template)
content = dc.find('div', {'id': 'content'})
content.clear()
content.extend(html.find('div', {'id': 'content'}))
savehtml(dc, 'dc.html')

def row(link: str, linktxt: str, text: str):
    return BeautifulSoup(f'<tr><td><a href="{link}">{linktxt}</a></td><td>{text}</td></tr>', parser)

# Переносим текст с основной страницы в 'param.html', но оставляем таблицу в index.html
param = readhtml('index.html')
index = copy.copy(template)
table = param.find('section', {'id': 'index'})
index.find('div', {'id': 'content'}).insert(-1, table)
brd = param.find('nav', {'id': 'breadcrumb'})
brd.clear()
brd.unwrap()
savehtml(param, 'param.html')
# Меняем ссылки в таблице
for i in table.table.tbody.find_all('a'):
    i['href'] = f'k155{i['href']}'
# Добавляем контент в таблицу
table.table.tbody.insert(  8, row('iv3.html'  , 'К155ИВ3'  , 'Приоритетный шифратор 9 каналов в 4'))
table.table.tbody.insert( 16, row('id7.html'  , 'К155ИД7'  , 'Высокоскоростной дешифратор'))
table.table.tbody.insert( 30, row('id24.html' , 'К155ИД24' , 'Высоковольтный двоично-десятичный дешифратор с ОК'))
table.table.tbody.insert( 62, row('ip6-7.html', 'К155ИП6-7', '4 ДНШУ'))
table.table.tbody.insert(122, row('li4.html'  , 'К155ЛИ4'  , '3 логических элемента 3И'))
table.table.tbody.insert(136, row('ln4.html'  , 'К155ЛН4'  , '6 буферных элементов без инверсии'))
table.table.tbody.insert(176, row('rp1.html'  , 'К155РП1'  , 'Матрица ОЗУ на 16 ячеек (4 x 4)'))
table.table.tbody.insert(206, row('xl1.html'  , 'К155ХЛ1'  , 'Универсальный элемент для ЦВМ'))
savehtml(index, 'index.html')

# Собираем список страниц для редактирования
morelist = [x for x in template.find('nav', {'id': 'articles'}).find_all('a') if x['href'] not in ['k155.djvu', 're3a.html']]
morelist.append(global_nav.find_all('a')[0])

# Обновляем боковое меню
for i in morelist:
    html = readhtml(i['href'])        
    ul = html.find('nav', {'id': 'map'}).ul
    ul.clear()
    ul.extend(copy.copy(global_nav.ul))
    savehtml(html, i['href'])

# Фильтация ссылок на самого себя и упаковка кода
# ==============================================================================

import htmlmin
import re

for i in Path('.').glob('*.html'):
    fname = str(i.name)
    html = BeautifulSoup(i.read_text(encoding = enc), parser)
    for link in html.find_all('a'):
        # Удаляем ссылки на самого себя
        if link.get('href', '') == fname:
            del link.attrs['href']
        # Ищем ссылки на локальные изображения и добавляем переменную
        elif '.jpg' in link.get('href', ''):
            link['style'] = f'--href:url({link['href']})'
    html.smooth()
    # savehtml(html, fname)
    # Компактифицируем код
    html_compact = ' '.join(str(html).replace('\n', ' ').split()).replace(' </', '</')
    html_compact = html_compact.replace('<b>', '').replace('&lt;b&gt;', '') # это для исправления косяка в la3.html. Больше нигде не встречается
    for t in ['tr', 'th', 'td', 'ul', 'li']:
        html_compact = html_compact.replace(' <' + t, '<' + t).replace(' </' + t, '</' + t).replace(t + '> ', t + '>')
    for t in ['sub', 'sup']:
        html_compact = html_compact.replace(' <' + t, '<' + t).replace(' </' + t, '</' + t).replace('<' + t + '> ', '<' + t + '>')
    for t in ['a', 'span']:
        html_compact = html_compact.replace(' </' + t, '</' + t)
        html_compact = re.sub('(<' + t + ' [^>]+>) +', r'\1', html_compact)
    # Дополнительные точечные правки
    for i in ',.;:!)':
        html_compact = html_compact.replace(' ' + i, i) # Убрать пробелы перед знаками препинания
    for i in '(':
        html_compact = html_compact.replace(i + ' ', i) # Убрать пробелы после открывающих скобок
    html_compact = re.sub(r'\.([А-Я])', r'. \1', html_compact) # Добавить пробел после точки
    html_compact = re.sub(r'([^l\s])(\()', r'\1 (', html_compact)  # Добавить пробел перед открывающими скобками
    # точечные опечатки в отдельных файлах
    if (fname == '74121.html'): html_compact = html_compact.replace('(74L121 ', '(74L121) ')
    html_compact = html_compact.replace('Все выхода отключены', 'Все выходы отключены')
    if (fname == 'id10.html'): html_compact = html_compact.replace('ДешифраторыК155ИД10иКМ155ИД10', 'Дешифраторы К155ИД10 и КМ155ИД10')
    if (fname == 'k155id12.html'): html_compact = html_compact.replace('Микросхем представляет', 'Микросхема представляет')
    html_compact = html_compact.replace('133 интегральных элементов', '33 интегральных элемента')
    html_compact = html_compact.replace('Микросхемы представляет', 'Микросхема представляет')
    html_compact = html_compact.replace('МикросхемаК155ИЕ8', 'Микросхема К155ИЕ8')
    html_compact = html_compact.replace('77 интегральный элемент', '77 интегральных элементов')
    html_compact = html_compact.replace('для арифметико-логическое устройсво', 'для арифметико-логического устройства')
    if (fname == 'k155ir13.html'): html_compact = html_compact.replace('четырехразрядный', 'восьмиразрядный')
    if (fname == 'ld1.html'): html_compact = html_compact.replace('МикросхемаК155ЛД1', 'Микросхема К155ЛД1')
    html_compact = html_compact.replace('⊕', '&#8853;').replace('🠕', '&#8593;').replace('↑', '&#8593;').replace('↓', '&#8595;').replace('⇅', '&#8645;').replace('⇵', '&#8693;')
    # Финальная упаковка
    Path(fname).write_text(htmlmin.minify(html_compact), enc)

print('complete')
