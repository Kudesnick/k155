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

import time
start_time = time.time()
end_time = time.time()

def log(msg: str):
    global start_time, end_time
    end_time = time.time()
    elaps = end_time - start_time
    print(f' ({elaps:.2f}).')
    print(msg, end = '')
    start_time = time.time()

class Sitemap(list[str]):
    __parser = 'html.parser' # 'xml'
    def __init__(self, fname: str):
        self.__xml = BeautifulSoup(Path(fname).read_text('utf-8'), self.__parser)
        super().__init__()

    def save(self, fname: str, url: str):
        from datetime import datetime
        self.__lastmod = datetime.today().strftime('%Y-%m-%d')
        self.__changefreq = 'never'
        # Генерируем карту
        self.__xml.urlset.extend([BeautifulSoup(f'<url><loc>https://{url}/{i}</loc><lastmod>{self.__lastmod}</lastmod><changefreq>{self.__changefreq}</changefreq></url>', self.__parser) for i in self])
        # Генерируем список изображений
        for i in self.__xml.urlset:
            imgs = {}
            for img in readhtml(i.loc.text.strip().replace(f'https://{url}/', '')).find_all('img'):
                imgs[img['src']] = img.get('alt', None)
            for k, v in imgs.items():
                if v:
                    im = BeautifulSoup(f'<image:image><image:loc>https://{url}/{k}</image:loc><image:title>{v}</image:title></image:image>', self.__parser)
                else:
                    im = BeautifulSoup(f'<image:image><image:loc>https://{url}/{k}</image:loc></image:image>', self.__parser)
                i.loc.insert_after(im)
        # Сохраняем карту
        self.__xml.smooth()
        Path(fname).write_text(self.__xml.prettify(), 'utf-8')

log('Копирование файлов в релиз')
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

for i in Path('kozak').glob('*.gif'):
    shutil.copy(str(i), str(release))
for i in [f for f in Path('kozak').glob('*.html') if not 'index' in str(f)]:
    shutil.copy(str(i), str(release))

for i in Path('libqrz').glob('*.jpg'):
    shutil.copy(str(i), str(release))
for i in Path('libqrz').glob('*.html'):
    shutil.copy(str(i), str(release))

shutil.copy('k155.djvu', str(release))
shutil.copy('k155.pdf', str(release))
shutil.copy('styles.css', str(release))

log('Совмещение навигации')
# ==============================================================================

import os
os.chdir(release)

first_nav = readhtml('index.html').find('nav').find('ul').find_all('li')[1:]
second_nav = readhtml('ttl.html').find('nav').find('ul').find_all('li')[1:]

scnd_nav = [i.a.get('href') for i in second_nav]

global_nav = BeautifulSoup(f'<ul></ul>', parser)

for i in first_nav:
    src, title, text = i.a.get('href'), i.a.get('title'), i.a.text.strip().replace('К155', '')
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
            repl = {'a': 'а', 'g': 'г', 'p': 'п', 'i': 'и', 'v': 'в', 'd': 'д', 'e': 'е', 'm': 'м', 'r': 'р', 'l': 'л', 'n': 'н', 'u': 'у', 't': 'т', 'k': 'к', 'x': 'х'}
            text = Path(src).stem
            for k, v in repl.items():
                text = text.replace(k, v)
            text = f'{text}'.upper()

            global_nav.ul.append(BeautifulSoup(f'<li><a>{text}</a><a href="{src}">{text}</a></li>', parser))
        scnd_nav.remove(src)

# Ручное исправление исключений
for i in global_nav.ul:
    if i.find_all('a')[1].text.strip() == 'ИЕ6':
        a = i.find_all('a')[1]
        a.string = 'ИЕ6-7'

    if i.find_all('a')[1].text.strip() == 'ИЕ7':
        a = i.find_all('a')[1]
        a.string = 'ИЕ6-7'
        a['href'] = 'ie6.html'
        a['title'] = str(i.a['title'])

    if i.find_all('a')[1].text.strip() == 'РУ1':
        a = i.find_all('a')[1]
        a['href'] = 'ru1-3.html'
        a['title'] = str(i.a['title'])
        a.string = 'РУ1-3'

# Добавление ссылок на kozak
for li in global_nav.find_all('li'):
    link = [i for i in li.find_all('a') if i.get('href', False)][-1]
    kz = list(Path('.').glob(f'???{link["href"].replace("k155", "")}'))
    href = str(kz[0]) if len(kz) else None
    if href:
        li.append(BeautifulSoup(f'<a href="{href}">{link.text}</a>', parser))
    else:
        li.append(BeautifulSoup(f'<a>{link.text}</a>', parser))

log ('Обновление title и классов у ссылок основного меню')
# ==============================================================================
for li in global_nav.find_all('li'):
    a = li.find_all('a')
    a[0]['class'] = 'kzs'
    a[1]['class'] = 'msh'
    a[2]['class'] = 'kzk'
    for i in [i for i in a if i.get('href', None)]:
        i['title'] = ', '.join([i.text.strip() for i in readhtml(i['href']).find_all('h1')])

log('Решаем проблему дублирования аналога 74170')
# ==============================================================================

altname = '74170rp1.html'
shutil.copy('74170.html', altname)
html = readhtml('rp1.html')
for a in html.find_all('a', {'href': '74170.html'}):
    a['href'] = altname
savehtml(html, 'rp1.html')

log('Переписывание меню навигации и "хлебных крошек"')
# ==============================================================================

import copy

template = readhtml('../template.html')

global_nav.ul.insert(0, copy.copy(template.find('nav').find_all('li')[0]))
global_links = [a for a in global_nav.find_all('a') if a.get('href', 'index.html') != 'index.html']

def add_class(el, s: str):
    if isinstance(el['class'], str):
        el['class'] = [el['class']]
    el['class'].append(s)

prev_last = None
for i in global_nav.ul:
    if i.a.get('href', '') == 'index.html':
        continue

    # собираем "хлебные крошки"
    breadcrumb = BeautifulSoup(f'<ul></ul>', parser)
    brd = None
    for j in [x for x in i.find_all('a') if x.get('href', None) != None]:
        html = readhtml(j['href'])
        if html.find('nav', {'id': 'hor'}):
            brd = html.find('nav', {'id': 'hor'}).find_all('li')[1:]
        breadcrumb.ul.extend(BeautifulSoup(f'<li><a href=\"{j["href"]}\">{j.text.strip()}</a></li>', parser))
    if brd:
        breadcrumb.ul.extend(brd)

    # Классы и title "хлебных крошек"
    for a in breadcrumb.find_all('a'):
        donor = global_nav.find('a', {'href': a['href']})
        if donor:
            a['class'] = donor['class']
            a['title'] = donor['title']
            a_end = donor
        else:
            a['class'] = ['msh', 'analog']
            a['title'] = readhtml(a['href']).find('h1').text.strip()
    # Добавляем элементы "вперед/назад"
    a_end = global_links.index(global_nav.find('a', {'href': a_end['href']})) + 1
    if prev_last:
        prev_last.a.string = ''
        add_class(prev_last.a, 'prev')
        breadcrumb.ul.insert(0, prev_last)
    prev_last = copy.copy(breadcrumb.find_all('li')[-1])
    if a_end < len(global_links):
        li = BeautifulSoup().new_tag('li')
        li.insert(0, copy.copy(global_links[a_end]))
        li.a.string = ''
        add_class(li.a, 'next')
        breadcrumb.ul.insert(len(breadcrumb.find_all('li')), li)

    # переписываем "крошки" и боковое меню
    for i in [i for i in breadcrumb.ul if i.a.text.strip() != '']:
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
brd_custom = BeautifulSoup(f'<li><a href="7493.html" class="msh analog prev"></a></li><li><a href="k155ie6.html" class="kzs">ИЕ6</a></li><li><a href="k155ie7.html" class="kzs">ИЕ7</a></li><li><a href="ie6.html" class="msh">ИЕ6-7</a></li><li><a href="051ie6.html" class="kzk">ИЕ6-7</a></li><li><a href="74192.html" class="msh analog">74192</a></li><li><a href="74193.html" class="msh analog">74193</a></li><li><a href="k155ie8.html" class="kzs next"></a></li>', parser)
for a in brd_custom.find_all('a'):
    a['title'] = ', '.join([i.text.strip() for i in readhtml(a['href']).find_all('h1')])
for i in ['k155ie6', 'k155ie7', 'ie6', '051ie6', '74192', '74193']:
    html = readhtml(f'{i}.html')
    brd = html.find('nav', {'id': 'breadcrumb'}).ul
    brd.clear()
    brd.extend(copy.copy(brd_custom))
    if i == 'ie6' or i == '051ie6':
        brd = html.find_all('nav', {'id': 'breadcrumb'})[1]
        brd.extract()
    savehtml(html, f'{i}.html')

# log('Проверка уникальности аналогов')
# ==============================================================================
# Код запускался один раз. Выявлена проблема с аналогом 74170
# err = 0
# for f in Path('.').glob('74*.html'):
#     html = readhtml(str(f))
#     if len(html.find_all('nav', {'id': 'breadcrumb'})) != 1:
#         log(f'Error! Breadcrumb in "{str(f)}" not consistent.\n')
#         err += 1
# if err > 0:
#     exit(err)

log('Работа с многостраничным справочником')
# ==============================================================================

ttl = readhtml('5105.html').div
ttl.h1.name = 'h2'
ttl.h2.string = 'Микросхемы серии ТТЛ и их применение'
ttl.name = 'nav'
ttl['id'] = 'ttl'

log('Работа с дополнительными материалами')
# ==============================================================================

# Формирование дополнительных страниц
for fname in ['ln4']:
    html = readhtml(str(Path('..').joinpath(f'{fname}.html')))
    tmp = copy.copy(template)
    content = tmp.find('div', {'id': 'content'})
    content.clear()
    content.extend(html.find('div', {'id': 'content'}))
    savehtml(tmp, f'{fname}.html')

def row(link: str, linktxt: str, text: str):
    return BeautifulSoup(f'<tr><td><a href="{link}">{linktxt}</a></td><td>{text}</td></tr>', parser)

# Переносим текст с основной страницы в 'param.html', но оставляем таблицу в index.html
param = readhtml('index.html')
index = copy.copy(template)
section = param.find('section', {'id': 'index'})
index.find('div', {'id': 'content'}).insert(-1, section)
savehtml(param, 'param.html')
# Меняем ссылки в таблице
table = section.table
for i in table.tbody.find_all('a'):
    i['href'] = f'k155{i["href"]}'
# Удаляем переносы
[br.extract() for br in table.find_all('br')]
# Добавляем контент в таблицу
table.tbody.insert(  8, row('iv3.html'  , 'К155ИВ3'  , 'Приоритетный шифратор 9 каналов в 4'))
table.tbody.insert( 16, row('id7.html'  , 'К155ИД7'  , 'Высокоскоростной дешифратор'))
table.tbody.insert( 30, row('id24.html' , 'К155ИД24' , 'Высоковольтный двоично-десятичный дешифратор с ОК'))
table.tbody.insert( 62, row('ip6-7.html', 'К155ИП6-7', '4 двунаправленных шинных усилителя'))
table.tbody.insert(122, row('li4.html'  , 'К155ЛИ4'  , '3 логических элемента 3И'))
table.tbody.insert(176, row('rp1.html'  , 'К155РП1'  , 'Матрица ОЗУ на 16 ячеек (4 x 4)'))
table.tbody.insert(204, row('xl1.html'  , 'К155ХЛ1'  , 'Универсальный элемент для ЦВМ'))
# Превращаем таблицу в словарь
table.caption.name = 'h2'
table.insert_before(table.h2)
table.thead.extract()
table.tbody.unwrap()
for tr in table.find_all('tr'):
    dt, dd = tr.find_all('td')
    dt.name = 'dt'
    dd.name = 'dd'
    tr.unwrap()
table.name = 'dl'
# Нормализуем ссылки
for a in table.find_all('a'):
    a.string = a.text.split()[0].replace('К155', '').strip()
    donor = global_nav.find('a', {'href': a['href']})
    a['class'] = donor['class']
    a['title'] = donor['title']
# Добавляем многостраничный справочник
index.find('nav', {'id': 'articles'}).insert_before(ttl)
savehtml(index, 'index.html')

# Собираем список страниц для редактирования
morelist = index.find('nav', {'id': 'articles'}).find_all('a')
morelist.extend(index.find('nav', {'id': 'ttl'}).find_all('a'))
morelist.append(global_nav.a)

# Обновляем боковое меню
for i in morelist:
    html = readhtml(i['href'])
    if not html.find('nav', {'id': 'map'}):
        html.body.insert(0, BeautifulSoup('<nav id="map"><ul></ul></nav>', parser))
    ul = html.find('nav', {'id': 'map'}).ul
    ul.clear()
    ul.extend(copy.copy(global_nav.ul))
    savehtml(html, i['href'])

log('Добавление "хлебных крошек" вниз')
# ==============================================================================
for i in Path('.').glob('*.html'):
    html = readhtml(str(i))
    fst_brd = html.find('nav', {'id': 'breadcrumb'})
    if fst_brd:
        fst_brd['class'] = 'breadcrumb'
        scn_brd = copy.copy(fst_brd)
        del scn_brd.attrs['id']
        html.div.insert_after(scn_brd)
        savehtml(html, str(i))

log('Генерация страницы 404')
# ==============================================================================

html = readhtml('index.html')
html.h1.string = html.h1.text.strip() + ' [404]'
html.h1.insert_after(BeautifulSoup('<p>Этой страницы не существует, но считайте, что вы на главной странице.</p>', parser))
savehtml(html, '404.html')

log('Добавляем тег canonical к дубликатам')
# ==============================================================================

canonical = {
    'index'  : '404',
    '74170'  : '74170rp1',
    '037id10': '037id24',
    '114kp5' : '114kp7',
    '126pr6' : '126pr7',
    '144tm5' : '144tm7',
}
for origin, cp in canonical.items():
    for i in [origin, cp]:
        html = readhtml(f'{i}.html')
        html.head.append(BeautifulSoup(f'<link rel="canonical" href="{origin}.html">', parser))
        savehtml(html, f'{i}.html')

log('Фильтация ссылок на самого себя и упаковка кода')
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
            link['style'] = f'--href:url({link["href"]})'
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

log('.htaccess, robots.txt и sitemap.xml')
# ==============================================================================

host = 'k155.su'
Path('.htaccess').write_text('AddDefaultCharset utf-8\nErrorDocument 404 /404.html\n', 'utf-8')
Path('robots.txt').write_text('User-agent: *\n' + ''.join([f'Disallow: /{i}.html\n' for i in canonical.values()]) + f'Sitemap: https://{host}/sitemap.xml\n', 'utf-8')
sitemap = Sitemap(Path('..').joinpath('sitemap.xml'))
sitemap.extend([str(i) for i in Path('').glob('*.html')])
[sitemap.remove(f'{i}.html') for i in canonical.values()]
sitemap.save('sitemap.xml', host)

log('complete\n')
