# -*- coding: utf-8 -*-

from gettext import find
import requests
from bs4 import BeautifulSoup
from pathlib import Path 
import sys
import re
import copy

enc = 'utf-8'
parser = 'html.parser'

base_url = 'https://www.inp.nsk.su/~kozak/ttl/'
alt_content_path = Path('..').joinpath('kozak')

# Пакетная замена подстрок 
def mrep(s: str, p):
    for i in p: s = s.replace(i[0], i[1])
    return s

# скачивание файла или извлечение его из кэша
def get_htm(url: str):
    global base_url, enc
    idx = 'htm'
    cache = Path(f'{url}.{idx}').name
    full_url = f'{base_url}ttlh{url}.{idx}'
    if not Path(cache).is_file():
        req = requests.get(full_url, headers = {'User-Agent': 'Chrome'})
        if req.status_code != 200:
            print(f'Error. Failed to download "{full_url}"', file = sys.stderr)
            return None
        else:
            print(f'Download "{full_url}"')
            text = req.content.decode('koi8-r')
            Path(cache).write_text(text.replace('charset=koi8-r', f'charset={enc}'), enc)
    return Path(cache).read_text(encoding = enc)

def get_img(url: str):
    global base_url
    cache = Path(url).name
    if not Path(cache).is_file():
        req = requests.get(url, headers = {'User-Agent': 'Chrome'})
        if req.status_code != 200:
            print(f'Error. Failed to download "{url}"', file = sys.stderr)
            return None
        else:
            print(f'Download "{url}"')
            Path(cache).write_bytes(req.content)
    return cache

# удалить все атрибуты из списка at в тэгах из списка tags
def del_attr(tags: list, at: list):
    for i in tags:
        for a in at:
            if a in i.attrs: del i.attrs[a]

glob_nav = None
articles = {}

def try_int(s: str) -> int:
    try:
        return int(s)
    except:
        None

def menu_generator(id: str, menu: dict):
    firstkey = list(menu.keys())[0]
    if not 'К155' in menu[firstkey]:
        # формируем текст ссылки
        repl = {'a': 'а', 'g': 'г', 'p': 'п', 'i': 'и', 'v': 'в', 'd': 'д', 'e': 'е', 'm': 'м', 'r': 'р', 'l': 'л', 'n': 'н', 'u': 'у', 't': 'т', 'k': 'к'}
        text = Path(menu[firstkey]).stem
        for k, v in repl.items():
            text = text.replace(k, v)
        menu[firstkey] = f'к155{text}'.upper()

    menu_list = ''.join([f'<li><a href="{k}">{v}</a></li>' for k, v in menu.items()])
    return BeautifulSoup(f'<nav id="{id}"><ul>{menu_list}</ul></nav>' if len(menu) > 1 else '', parser)

# копирование пользовательских картинок
def img_copy(patterns: list):
    for i in [f for f_ in [Path('..').glob(e) for e in patterns] for f in f_]:
        Path(i.name).write_bytes(i.read_bytes())

# скраппинг
def scrap(url: str, alt_name):
    global glob_nav
    htm = get_htm(url)
    if htm == None: return None

    # удаляем комментарии
    htm = re.sub(r'<!.*?>','', htm)

    # чиним сломанный HTML (незакрытые ссылки, опечатки и пр.)
    patterns = [
                (' ', ' '),
                ]
    if alt_name == 'index.html':
        patterns.append(('<p>', '</p><p>'))
    htm = mrep(htm, patterns)

    # парсим HTML файл
    soup = BeautifulSoup(htm, parser).find('div', {'align': 'left'})

    # Извлекаем данные для навигации
    if alt_name == 'index.html':
        soup = soup.find_all('p')[1]
        text = str(soup).replace('<br/>', '</li><li>').replace('<p>', '<ul><li>').replace('</p>', '</li></ul>')
        text = text.replace('ИВ1, ИВ2 - приоритетные кодеры 8 в 3</a>', 'ИВ1, ИВ2</a> - приоритетные кодеры 8 в 3').replace('30В', '30 В')
        soup = BeautifulSoup(text, parser)
        # Убираем ссылки, не относящиеся к серии 155
        soup.ul.li.extract()
        [li.extract() for li in soup.find_all('li') if not li.a['href'] in [f'ttlh{str(j).zfill(2)}.htm' for j in arglst]]
        glob_nav = copy.copy(soup.ul)
        for li in glob_nav.find_all('li'):
            txt = li.find_all(string = True)[2]
            li.a['title'] = txt.strip(' -')
            txt.extract()

    # предварительное форматирование текста
    soup.smooth()
    for i in soup.find_all(string = True):
        ii = ' '.join(i.replace('\r', ' ').replace('\n', ' ').split())
        if ii != '': i.replace_with(ii)
        else: i.extract()
    soup.smooth()

    # удаляем лишнее форматирование
    del_attr(soup.find_all(['table', 'div', 'tr', 'th', 'td', 'ul', 'ol']),
                           ['align', 'border', 'bgcolor', 'cellpadding', 'cellspacing', 'width', 'tupe', 'compact', 'type', 'start'])

    # загружаем изображения
    for img in soup.find_all('img'):
        img['src'] = get_img(img['src'])

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), parser)

    content = template.find('div', id = "content")
    content.clear()

    # добавляем содержимое
    content.extend(soup)

    # удаляем <br>
    [i.replace_with(' ') for i in template.find_all('br')]

    # глобальная навигация
    if glob_nav:
        chip_ul = template.find(id = 'map').ul
        chip_ul.extend(glob_nav)

    # сохраняем результат в файл
    template.smooth()
    # Удаляем пустые абзацы и извлекаем списки из абзацев
    [p.unwrap() for p in template.find_all('p') if p.text.strip() == '']
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(alt_name).write_text(template.prettify(), enc)
    print(f'File "{alt_name}" writed')

    return glob_nav

if __name__ == '__main__':
    arglst = [7, 8, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 42, 47, 48, 49, 50, 51, 52, 53, 55, 63, 64, 65, 69,
           70, 71, 73, 80, 86, 87, 89, 103, 112, 113, 114, 126, 128, 130, 131, 132, 139, 142, 143, 144, 145, 148]

    scrap('00', 'index.html')

    print('complete')

    # glob_nav = [BeautifulSoup(f'<li><a href = "{short_name(i)}">К155{Path(short_name(i)).stem}</a></li>', parser).li for i in childs if not i in articles.keys()]

    # for i in childs: scrap(i)
