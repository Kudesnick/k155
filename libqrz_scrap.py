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

    # удаляем комментарии
    htm = re.sub(r'<!.*?>','', htm)

    # парсим HTML файл
    soup = BeautifulSoup(htm, parser).find('div', {'class': 'section-3'})

    # Удаляем br, b, i
    [br.extract() for br in soup.find_all(['br', 'b', 'i'])]

    # загружаем изображения
    for img in soup.find_all('img'):
        img['src'] = get_img(img['src'])

    # Преобразуем ссылки на описание картинок в подписи к картинкам
    for s4 in soup.find_all('div', {'class': 'section-4'}):
        for link in [i for i in s4.find_all('a') if i.find('img') != None]:
            id = link['href'].replace('/node/', '')
            div = s4.find('div', {'id': f'node-{id}'})
            link.append(div.h1)
            link.name = 'figure'
            link.img['alt'] = link.h1.text.strip()
            link.h1.name = 'figcaption'
            del link.attrs['href']
            div.extract()
            if link.parent.name == 'p': link.parent.unwrap()
            if 'Рис. ' in link.img['alt']:
                link['id'] = 'pic-' + re.findall('[0-9]+', link.img['alt'])[0]
            if 'Таблица ' in link.img['alt']:
                link['id'] = 'tab-' + re.findall('[0-9]+', link.img['alt'])[0]

    # Устанавливаем id для таблиц
    table = soup.find_all('table')
    table[0]['id'] = 'tab-4'
    table[0].insert(0, BeautifulSoup('<caption>Таблица 4. Получение различных K</caption>', parser))
    table[1]['id'] = 'tab-5'
    table[1].insert(0, BeautifulSoup('<caption>Таблица 5. Индицируемы знаки</caption>', parser))
    table[2]['id'] = 'tab-6'
    table[2].insert(0, BeautifulSoup('<caption>Таблица 6. Таблица истинности сумматора</caption>', parser))

    # Разворачиваем вложенность div
    [div.unwrap() for div in soup.find_all('div') if len(set(['section-4', 'section-5']) & set(div.get('class', []))) == 0]

    def section(div, h):
        if div.p.get('align', '') == 'center':
           div.p.extract()
        div.name = 'section'
        div.h1.name = h

    # Приводим в порядок заголовки
    for div in soup.find_all('div', {'class': 'section-4'}):
        section(div, 'h2')

    for div in soup.find_all('div', {'class': 'section-5'}):
        section(div, 'h3')

    for h in soup.find_all(['h1', 'h2', 'h3']):
        h.string = h.text.strip(' \r\n.')

    # Удаляем пустые абзацы и абзацы из ячеек таблицы
    [p.unwrap() for p in soup.find_all('p') if (p.text.strip() == '') or (p.parent.name in ['td', 'th'])]

    # склеиваем переносы по абзацам
    for p in reversed(soup.find_all('p')):
        text = p.text.strip('\r\n ')
        if text[-1] != '.':
            if text[-1] == '-' and text[-2] != ' ':
                text = text[:-1]
            else:
                text = text + ' '
            next_p = p.find_next_siblings('p', limit=1)[0]
            p.string = text + next_p.text.strip()
            next_p.extract()

    # Приводим в порядок таблицы
    for td in soup.find_all(['td', 'th']):
        td.string = ' '.join(td.text.replace('\r', ' ').replace('\n', ' ').split(' ')).strip()

    # Убираем лишние атрибуты
    del_attr(soup.find_all(['p', 'img', 'table', 'figcaption', 'div', 'section', 'h1', 'h2', 'h3']), ['align', 'border', 'hspace', 'vspace', 'class', 'height'])

    repl = [
        ('&lt;&lt;П&gt;&gt;', '«П»'),
        ('&lt;&lt;Ъ&gt;&gt;', '«Ъ»'),
        ('+-;', '&plusmn;'),
        ('+-', '&plusmn;'),
        ('ЛА13КР1533ЛА23'      ,'ЛА13, КР1533ЛА23'      ),
        ('КР1533ЛА21КР1533ЛА24','КР1533ЛА21, КР1533ЛА24'),
        ('К155ЛЕ2К155ЛЕЗ'      ,'К155ЛЕ2, К155ЛЕЗ'      ),
        ('ЛЕ1ЛЕ4КР531ЛЕ7'      ,'ЛЕ1, ЛЕ4, КР531ЛЕ7'    ),
        ('К555КП 11'           ,'К555КП11'              ),
        ('КМ155ИД8АКМ155ИД8БКМ155ИД9', 'КМ155ИД8А, КМ155ИД8Б, КМ155ИД9'),
        ('К155РЕ23К155РЕ2','К155РЕ23 К155РЕ2'),
        ('с- неиспользуемыми', 'с неиспользуемыми'),
        ('-инвертирующие', '- инвертирующие'),
        ('^м', '<sup>м</sup>'),
        ('^2', '<sup>2</sup>'),
        ('^i', '<sup>i</sup>'),
        ('^n', '<sup>n</sup>'),
        ('вь1ходы', 'выходы'),
        ('К Все', 'К. Все'),
    ]
    string = mrep(str(soup), repl)
    string = re.sub(r'([а-я,\(]+)([А-Я0-9]{2,})', r'\1 \2', string)
    string = re.sub(r'([А-Я0-9]{2,})([^,\.\-\: \'\"А-Я0-9\)]+)', r'\1 \2', string)
    string = string.replace('МО м', 'МОм')
    # ссылки на рисунки
    string = re.sub(r'(рис\. )([0-9]+)', r'<a href="#pic-\2">\1\2</a>', string)
    string = re.sub(r'(табл\. )([0-9]+)', r'<a href="#tab-\2">\1\2</a>', string)
    soup = BeautifulSoup(string, parser)

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), parser)

    content = template.find('div', id = "content")
    content.clear()

    # добавляем содержимое
    content.extend(soup.div)

    # сохраняем результат в файл
    template.smooth()
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(alt_name).write_text(template.prettify(), enc)
    print(f'File "{alt_name}" writed')

if __name__ == '__main__':
    scrap('index.html')

    print('complete')
