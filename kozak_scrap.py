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
        req = requests.get(base_url + url, headers = {'User-Agent': 'Chrome'})
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
    patterns = [('~\\_', '&#8595;'), ('_/~', '&#8593;'), ('/~\\', '&#8645;'), ('\\_/', '&#8693;')]
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
        [li.extract() for li in soup.find_all('li') if not li.a['href'] in [f'ttlh{str(j).zfill(2)}.htm' for j in args.keys()]]
        glob_nav = copy.copy(soup.ul)
        for li in glob_nav.find_all('li'):
            txt = li.find_all(string = True)[2]
            li.a['title'] = txt.strip(' -')
            txt.extract()
            href = li.a['href'].replace('ttlh', '').replace('.htm', '')
            v = args[int(href)]
            if not isinstance(v,str): v = v[0]
            li.a['href'] = f'{href.zfill(3)}{v}.html'

    # предварительное форматирование текста
    soup.smooth()
    for i in soup.find_all(string = True):
        ii = ' '.join(i.replace('\r', ' ').replace('\n', ' ').split())
        if ii != '': i.replace_with(ii)
        else: i.extract()
    soup.smooth()

    # удаляем лишнее форматирование
    del_attr(soup.find_all(['table', 'div', 'tr', 'th', 'td', 'ul', 'ol', 'img']),
                           ['align', 'border', 'bgcolor', 'cellpadding', 'cellspacing', 'width', 'height', 'tupe', 'compact', 'type', 'start'])

    # загружаем изображения
    for img in soup.find_all('img'):
        img['src'] = get_img(img['src'])
        img.wrap(BeautifulSoup().new_tag('figure'))
        img.parent.append(BeautifulSoup().new_tag('figcaption'))

    # удаляем ненужные теги
    [i.unwrap() for i in soup.find_all(string = False) if i.name in ['center']]

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), parser)

    content = template.find('div', id = "content")
    content.clear()

    if alt_name != 'index.html':
        # Извлекаем заголовки
        hdrs = soup.table.find_all('tt')
        if not hdrs: hdrs = [soup.table.find('div', {'class': 'td1'})]
        for i in hdrs:
            i.name = 'h1'
        content.extend(hdrs)
        soup.table.extract()
        # Избавляемся от <tt> и <span class="txtjust">
        for i in soup.find_all('span', {'class': 'txtjust'}):
            i.name = 'tt'
            del i.attrs['class']
        [i.unwrap() for i in soup.find_all('tt') if i.parent.name in ['tt', 'td', 'th']]
        for i in soup.find_all('tt'): i.name = 'p'

        # Чиним оформление таблиц
        for tr in soup.find_all('tr', {'class': 'row'}):
            for td in tr.find_all(['td', 'th']):
                td.name = 'th'
            del tr.attrs['class']
        for td in soup.find_all(['td', 'th'], {'class': 'row'}):
            td.name = 'th'
            del td.attrs['class']
        for td in soup.find_all(['td', 'th']):
            [i.unwrap() for i in td.find_all(['div', 'tt', 'center', 'p'])]


    # добавляем содержимое
    content.extend(soup)

    # удаляем <br>
    [i.replace_with(' ') for i in template.find_all('br')]

    # глобальная навигация
    if glob_nav:
        chip_ul = template.find(id = 'map').ul
        chip_ul.extend(copy.copy(glob_nav))

    if url != '00':
        # добавляем информацию об источниках
        template.footer.append(BeautifulSoup(f'<p>Scrapped from <a href="{base_url}ttlh{url}.htm" title="Справочник по стандартным цифровым ТТЛ микросхемам. Козак Виктор Романович, Новосибирск, 11-июня-2014 г.: {template.h1.text.strip()}">{base_url}ttlh{url}.htm</a></p>', parser))
        # дополняем <title>
        template.title.string = 'К155' + template.h1.text.strip()

    # сохраняем результат в файл
    template.smooth()
    # Удаляем пустые абзацы и извлекаем вложенные абзацы
    [p.unwrap() for p in template.find_all('p') if p.text.strip() == '']
    [p.parent.unwrap() for p in template.find_all('p') if p.parent.name == 'p']
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(alt_name).write_text(template.prettify(), enc)
    print(f'File "{alt_name}" writed')

if __name__ == '__main__':
    for file in [i for i in Path('.').glob('*.html') if str(i) != 'index.html']:
        htm = file.read_text(encoding = enc)
        htm = htm.replace('--&gt;', '&#8594;')
        soup = BeautifulSoup(htm, parser)
        # добавляем информацию об источниках
        soup.footer.p.extract()
        url = f'{base_url}ttlh{str(int(str(file)[0:3])).zfill(2)}.htm'
        soup.footer.append(BeautifulSoup(f'<p>Scrapped from <a href="{url}" title="Справочник по стандартным цифровым ТТЛ микросхемам. Козак Виктор Романович, Новосибирск, 11-июня-2014 г.: {soup.h1.text.strip()}">{url}</a></p>', parser))
        if soup.div.find('aside'): soup.div.aside.extract()
        # удаляем лишние тире в параметрах
        for table in [i for i in soup.find_all('table') if (i.find('th') and ('Параметр' in i.th.text)) or ('Задержки распространения (нс)' in i.caption.text)]:
            for td in table.find_all('td'):
                td.string = td.text.strip('\r\n -')
            if not table.find('caption'):
                table.insert(0, BeautifulSoup('<caption>Электрические параметры</caption>', parser))
        # Добавляем описание к рисунку
        if len(soup.find_all('img')) == 1 and soup.img.get('alt', '') == '':
            soup.img['alt'] = soup.h1.text.strip('\r\n ') + '. Условное графическое обозначение'
            soup.figcaption.string = soup.img['alt']
        # дополняем <title>
        soup.title.string = 'К155' + soup.h1.text.strip()
        # Разделяем столбцы, согласно ручной разметке
        for table in soup.find_all('table'):
            split = False
            for tr in table.find_all('tr'):
                if tr.get('class', [''])[0] == 'split':
                    split = True
                elif tr.get('class', [''])[0] == 'nosplit':
                    split - False
                for td in tr.find_all(['td', 'th']):
                    curr_split = split
                    if td.get('class', [''])[0] == 'split':
                        curr_split = True
                    elif td.get('class', [''])[0] == 'nosplit':
                        curr_split - False
                    items = td.text.strip('\r\n ').split() if curr_split else []
                    if len(items) > 1:
                        td.string = items[0]
                        for i in reversed(items[1:]):
                            new_td = BeautifulSoup().new_tag(td.name)
                            new_td.string = i
                            td.insert_after(new_td)
            for i in [i for i in table.find_all(['tr', 'td', 'th']) if i.get('class', False)]:
                del i.attrs['class']
        # удаляем устаревший атрибут cols
        for table in [i for i in soup.find_all('table') if i.get('cols', False)]:
            del table.attrs['cols']
        # сохраняем результат
        soup.smooth()
        file.write_text(soup.prettify(), enc)
        print(f'File "{str(file)}" writed')

    print('complete')
    exit(0)

# Превичная обработка (после неё были ручные правки)
    args = {7: 'ag1', 8: 'ag3', 28: 'iv1', 29: 'iv3', 30: 'id1', 31: 'id3', 32: 'id4', 34: 'id7',
        35: 'id8', 36: 'id9', 37: ['id10', 'id24'], 38: 'id11', 39: 'id12', 40: 'id13', 42: 'id15',
        47: 'ie1', 48: 'ie2', 49: 'ie4', 50: 'ie5', 51: 'ie6', 52: 'ie8', 53: 'ie9', 55: 'ie14',
        63: 'im1', 64: 'im2', 65: 'im3', 69: 'ip2', 70: 'ip3', 71: 'ip4', 73: 'ip6-7', 80: 'ir1',
        86: 'ir13', 87: 'ir15', 89: 'ir17', 103: 'ir32', 112: 'kp1', 113: 'kp2',
        114: ['kp5', 'kp7'], 126: ['pr6', 'pr7'], 128: 're3', 130: 'rp1', 131: 'rp3', 132: 'ru2',
        139: 'tv1', 142: 'tv15', 143: 'tm2', 144: ['tm5', 'tm7'], 145: 'tm8', 148: 'xl1'}

    # подгружаем пользовательские картинки
    img_copy(['styles.css'])

    scrap('00', 'index.html')

    for k, v in args.items():
        val = [v] if isinstance(v,str) else v
        [scrap(str(k).zfill(2), f'{str(k).zfill(3)}{i}.html') for i in val]

    print('complete')
