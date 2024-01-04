# -*- coding: utf-8 -*-

from gettext import find
import requests
from bs4 import BeautifulSoup
from pathlib import Path 
import sys
import re

enc = 'utf-8'

base_url = 'https://kiloom.ru/spravochnik-radiodetalej/microsxema/'

# Пакетная замена подстрок 
def mrep(s: str, p):
    for i in p: s = s.replace(i[0], i[1])
    return s

# скачивание файла или извлечение его из кэша
def get_htm(url: str):
    global base_url, enc
    idx = 'htm'
    cache = Path(f'{url}.{idx}').name
    full_url = f'{base_url}{url}'
    if not Path(cache).is_file():
        req = requests.get(full_url, headers = {'User-Agent': 'Chrome'})
        if req.status_code != 200:
            print(f'Error. Failed to download "{full_url}"', file = sys.stderr)
            return None
        else:
            print(f'Download "{full_url}"')
            req = req.text.encode(enc, errors = 'ignore').decode(enc, errors = 'ignore')
            Path(cache).write_text(req, encoding = enc)
    return Path(cache).read_text(encoding = enc)

def get_img(url: str):
    global base_url
    cache = Path(url).name
    if not Path(cache).is_file():
        full_url = f'{base_url}{url}'
        req = requests.get(full_url, headers = {'User-Agent': 'Chrome'})
        if req.status_code != 200:
            print(f'Error. Failed to download "{full_url}"', file = sys.stderr)
            return None
        else:
            print(f'Download "{full_url}"')
            Path(cache).write_bytes(req.content)
    return cache

# удалить все атрибуты из списка at в тэгах из списка tags
def del_attr(tags: list, at: list):
    for i in tags:
        for a in at:
            if a in i.attrs: del i.attrs[a]

# превращаем форматированный текст в таблицу
def table_create(table: BeautifulSoup):
    # парсинг заголовка
    caption = table.strong.extract()
    caption.string = caption.text.strip(' \n:').replace('  ', ' ')
    caption.name = 'caption'
    # парсинг данных
    text = mrep(str(table), [
        ('\t', ' '),
        ('\n', ' '),
        (u'\xa0', ''),
        ('<p><br/>', ''),
        ('</p><p>', '<br/>'),
        ('<p><p>', ''),
        ('</p></p>', '</p>')
    ])
    text = ' '.join(text.split())
    text = re.sub('[ \.]{4,}(.+?)(<br/>|</p>)', r'~~\1<~~>', text).replace(':<br/>', ':<~~>').replace('<br/>', ' ').split('<~~>')
    text = [i.split('~~') for i in text if i]
    # генерация таблицы
    table.name = 'table'
    table.clear()
    table.append(caption)
    # заполняем таблицу
    for tr in text:
        if 'К155' in tr[0] or 'КМ155' in tr[0]: tr[0] = ' ' + tr[0]
        if (tr != text[0] and len(tr) == 1) or tr[0][0] != ' ':
            tbody = BeautifulSoup('<tbody></tbody>', 'html.parser').tbody
            table.append(tbody)
        if len(tr) == 1:
            tbody.append(BeautifulSoup(f'<tr><th colspan="2">{tr[0]}</th></tr>', 'html.parser').tr)
        else:
            tbody.append(BeautifulSoup(f'<tr><td>{tr[0].strip()}</td><td>{tr[1]}</td></tr>', 'html.parser').tr)
        
    return table

glob_nav = None
true_files = []

def short_name(name: str):
    return name.split('.', 2)[0].split('-', 2)[0].replace('k155', '').replace('id8a', 'id8') + Path(name).suffix

# скраппинг
def scrap(url: str, alt_name = None):
    global glob_nav
    global true_files
    htm = get_htm(url)
    if htm == None: return None

    if not alt_name:
        alt_name = short_name(url)

    # исправляем битую разметку
    patterns = [('</p>\n<p>&nbsp;</td>', '</td>')]
    htm = mrep(htm, patterns)

    # парсим HTML файл
    soup = BeautifulSoup(htm, 'html.parser')
    title = BeautifulSoup(htm, 'html.parser').title.text
    soup = soup.find('div', {'class': 'entry-content'})

    [i.extract() for i in soup.find_all(attrs = {'class', 'entry-meta'})]
    [i.extract() for i in soup.find_all('noscript')]
    [i.extract() for i in soup.find_all('div', id = 'crp_related')]
    [i.extract() for i in soup.find_all(attrs = {'class', 'code-block'})]
    [i.extract() for i in soup.find_all(attrs = {'class', 'clearfix'})]

    # предварительное форматирование текста
    soup.smooth()
    for i in soup.find_all(string = True):
        ii = i.replace('\r', ' ').replace('\n', ' ').strip(' ')
        if ii != '': i.replace_with(ii)
        else: i.extract()
    soup.smooth()

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), 'html.parser')
    template.body['href'] = f'{base_url}{url}'
    template.body['name'] = title

    content = template.find('div', id = "content")

    # чистим таблицу главной страницы, если она найдена
    center = soup.find('table')
    if not glob_nav and center:
        for i in center.find_all('br'):
            i.name = 'wbr'
        del_attr(center.find_all('table'), ['border', 'cellpadding', 'cellspacing', 'width'])
        content.append(center)

        # чиним ссылки и превращаем их в локальные
        for tr in center.find_all('tr'):
            if tr.td and tr.td.a:
                if tr.td.a['href'] == '':
                    tr.td.a.unwrap()
                else:
                    href = Path(tr.td.a['href']).name
                    true_files.append(href)
                    tr.td.a['href'] = short_name(href)

        glob_nav = [BeautifulSoup('<li><a href = "index.html">Домой</a></li>', 'html.parser').li]
        glob_nav.extend([BeautifulSoup(f'<li><a href = "{tr.td.a["href"]}" title = "{str(tr.td.next_sibling.text)}">{tr.td.a.find(string = True)}</a></li>', 'html.parser').li for tr in center.find_all('tr') if tr.td and tr.td.a])

    # удаляем табличную обертку, которая есть на некоторых страницах
    elif soup.table:
        del_attr(soup.table.find_all('td'), ['colspan', 'style'])
        # [i.unwrap() for i in soup.table.find_all('td') if i.p]
        for i in soup.table.find_all('td'): i.name = 'p'
        [i.unwrap() for i in soup.table.find_all('tr')]
        [i.unwrap() for i in soup.table.find_all('tbody')]

    # загружаем изображения
    for img in soup.find_all('img'):
        img['src'] = get_img('../..' + img['data-src'])
    
    # собираем таблицу параметров и предельных режимов эксплуатации
    tables = [i.parent for i in soup.find_all('strong') if 'Электрические' in i.text or 'Предельно' in i.text]
    if tables:
        for t in tables:
            section = table_create(t).wrap(BeautifulSoup().new_tag('section'))
            section.insert(0, BeautifulSoup().new_tag('h2'))
            section.h2.string = section.table.caption.string
            section['id'] = 'elp' if 'Электрические' in section.h2.string else 'limits'

    # добавляем содержимое
    content.append(soup)

    # глобальная навигация
    map = template.find(id = 'map')
    map.append(template.new_tag('ul'))
    for li in glob_nav:
        map.ul.append(li)

    # сохраняем результат в файл
    template.smooth()
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(alt_name).write_text(template.prettify(), enc)
    print(f'File "{alt_name}" writed')

    return true_files

if __name__ == '__main__':
    childs = [i for i in scrap('mikrosxemy-serii-k155.html', 'index.html')]
    childs.append('k155lr4-km155lr4-kb155lr4-4.html')
    if len(sys.argv) > 1:
        childs = [i for i in childs if i in sys.argv[1:]]
    for i in childs: scrap(i)
