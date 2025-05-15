# -*- coding: utf-8 -*-

from gettext import find
import requests
from bs4 import BeautifulSoup
from pathlib import Path 
import sys
import re

enc = 'utf-8'
parser = 'html.parser'

base_url = 'http://www.junradio.com/'
alt_content_path = Path('..').joinpath('junradio')

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
            Path(cache).write_bytes(req.content)
    return Path(cache).read_text(encoding = enc)

def get_img(url: str):
    global base_url
    if '//' in url:
        return None
    
    cache = Path(url).name.replace('(2)', '')
    if not Path(cache).is_file():
        req = requests.get(base_url + url, headers = {'User-Agent': 'Chrome'})
        if req.status_code != 200:
            print(f'Error. Failed to download "{url}"', file = sys.stderr)
            return None
        else:
            print(f'Download "{url}"')
            Path(cache).write_bytes(req.content)
    return cache

# замена изображений на спецсимволы
def img_to_symb(img: BeautifulSoup) -> bool:
    repl_imgs = {'fr': '&#8593;', 'sp': '&#8595;', 'imp': '&#8645;', '-imp': '&#8693;', 'kr': ' &#8853; '}
    
    stem = Path(img['src']).stem
    if stem in repl_imgs.keys():
        img.replace_with(BeautifulSoup(repl_imgs[stem], parser))
        return True
    return False

# удалить все атрибуты из списка at в тэгах из списка tags
def del_attr(tags: list, at: list):
    for i in tags:
        for a in at:
            if a in i.attrs: del i.attrs[a]

glob_nav = None
articles = {}

def short_name(s: str):
    sn = s.lower().replace("w", "v")
    sn = articles.get(sn, sn)
    return f'{sn}.html'

def try_int(s: str) -> int:
    try:
        return int(s)
    except:
        None

def menu_generator(id: str, menu: dict, name: str = ''):
    menu_list = ''.join([f'<li><a href="{k}">{v}</a></li>' if k != name else f'<li>{v}</li>' for k, v in menu.items()])
    return BeautifulSoup(f'<nav id="{id}"><ul>{menu_list}</ul></nav>' if len(menu) > 1 else '', parser)

# копирование пользовательских картинок
def img_copy(patterns: list):
    for i in [f for f_ in [Path('..').glob(e) for e in patterns] for f in f_]:
        Path(i.name).write_bytes(i.read_bytes())

# скраппинг
def scrap(url: str, alt_name = None, hor_menu = None):
    global glob_nav
    htm = get_htm(url)
    if htm == None: return None

    # Обрезаем скрипты
    htm = htm[htm.index('<!-- /Yandex.Metrika counter -->'):htm.rindex('<!-- #EndEditable -->')]

    # удаляем комментарии
    htm = re.sub(r'<!.*?>','', htm)

    # чиним сломанный HTML
    patterns = [('</font>', '</font></p>'),
                ('<font face="Arial" size=2>', '<font face="Arial" size=2>&nbsp;')]
    htm = mrep(htm, patterns)

    # парсим HTML файл
    soup = BeautifulSoup(htm, parser).find('body')

    # предварительное форматирование текста
    soup.smooth()
    for i in soup.find_all(string = True):
        ii = i.replace('\r', ' ').replace('\n', ' ').strip(' ')
        if ii != '': i.replace_with(ii)
        else: i.extract()
    soup.smooth()

    # загружаем изображения
    del_attr(soup.find_all('img'), ["align", "hspace", "vspace", "width"])
    for img in soup.find_all('img'):
        if Path(img['src']).name == 'img.jpg':
            img.decompose()
        elif not img_to_symb(img):
            img['src'] = get_img(url[:url.rindex('/') + 1] + img['src'])
            for prnt in ['h4', 'th', 'td', 'tr', 'tbody', 'table', 'h4']:
                if img.parent.name == prnt:
                    img.parent.unwrap()
            img.wrap(BeautifulSoup().new_tag('figure'))
            fig = img.parent
            # if img.get('alt'):
            #     fig.append(BeautifulSoup().new_tag('figcaption'))
            #     fig.figcaption.append(img['alt'])

    # Убираем декорацию текста
    [b.unwrap() for b in soup.find_all(['b', 'i', 'strong', 'font', 'br', 'script', 'noscript', 'center'])]
    
    # Убираем лишние атрибуты
    del_attr(soup.find_all(['p']), ['align'])
    del_attr(soup.find_all(['img']), ['border'])
    del_attr(soup.find_all('table'), ['border', 'align'])

    # чистим таблицу
    table = soup.find('table')
    table.parent.unwrap()
    table.parent.unwrap()
    [p.unwrap() for p in table.find_all(['p'])]
    for tr in table.find_all(['tr'], limit = 3):
        for td in tr.find_all(['td']):
            td.name = 'th'
    for td in table.find_all(['td']):
        td.string = td.text.replace(' ', ' ')
        td.string = td.text.replace('?', ' ?')
        td.string = td.text.replace('Z[', 'Z [')
        td.string = td.text.replace('Р Q R S', 'P Q R S')
        td.string = td.text.replace('0 0 0\' 0', '0 0 0 0')
        td.string = td.text.replace('L М N 0', 'L M N O')
        td.string = td.text.replace('Н I J K', 'H I J K')
        td.string = td.text.replace('@ А В С', '@ A B C')

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), parser)

    content = template.find('div', id = "content")
    content.clear()

    # добавляем содержимое

    content.extend(soup)
    soup.unwrap()

    # добавляем информацию об источниках
    new_link = BeautifulSoup(f'<section id="literature"><h2>Литература</h2><ul><li><a href="{base_url}{url}">Научно-популярный образовательный ресурс junradio.com: {content.h1.text}</a></li></ul></section>', parser)
    template.find(id = 'content').append(new_link)

    # сохраняем результат в файл
    template.smooth()
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(alt_name).write_text(template.prettify(), enc)
    print(f'File "{alt_name}" writed')

    return alt_name

if __name__ == '__main__':
    url = 'nach/TTL/CHAPTER1/1-4-3.htm' if len(sys.argv) < 2 else sys.argv[1]
    name = 'dc.html' if len(sys.argv) < 3 else sys.argv[2]

    scrap(url, name)

    # подгружаем пользовательские картинки
    img_copy(['styles.css'])
