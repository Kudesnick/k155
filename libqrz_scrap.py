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

base_url = 'https://lib.qrz.ru/book/export/html/5105'
alt_content_path = Path('..').joinpath('libqrz')

# Пакетная замена подстрок 
def mrep(s: str, p):
    for i in p: s = s.replace(i[0], i[1])
    return s

# скачивание файла или извлечение его из кэша
def get_htm():
    global base_url, enc
    cache = 'index.htm'
    if not Path(cache).is_file():
        req = requests.get(base_url, headers = {'User-Agent': 'Chrome'})
        if req.status_code != 200:
            print(f'Error. Failed to download "{base_url}"', file = sys.stderr)
            return None
        else:
            print(f'Download "{base_url}"')
            text = req.content.decode(enc)
            Path(cache).write_text(text.replace('charset=koi8-r', f'charset={enc}'), enc)
    return Path(cache).read_text(encoding = enc)

def get_img(url: str):
    global base_url
    cache = Path(url).name
    if not Path(cache).is_file():
        url = 'https://lib.qrz.ru/files/images/reference/book1/chapter1/'+ cache
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
def scrap(alt_name):
    global glob_nav
    htm = get_htm()
    if htm == None: return None

    # парсим HTML файл
    soup = BeautifulSoup(htm, parser).find('div', {'class': 'section-3'})

    # загружаем изображения
    for img in soup.find_all('img'):
        img['src'] = get_img(img['src'])

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), parser)

    content = template.find('div', id = "content")
    content.clear()

    # добавляем содержимое
    content.extend(soup)

    # сохраняем результат в файл
    template.smooth()
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(alt_name).write_text(template.prettify(), enc)
    print(f'File "{alt_name}" writed')

if __name__ == '__main__':
    scrap('index.html')

    print('complete')
