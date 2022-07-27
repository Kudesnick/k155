# -*- coding: utf-8 -*-

from gettext import find
import requests
from bs4 import BeautifulSoup
from pathlib import Path 
import sys
import re

enc = 'utf-8'
parser = 'html.parser'

base_url = 'https://microshemca.ru/'

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

# замена изображений на спецсимволы
def img_to_symb(img: BeautifulSoup) -> bool:
    repl_imgs = {'fr': '&#8593;', 'sp': '&#8595;', 'imp': '&#8645;', '-imp': '&#8693;'}
    
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

def short_name(s: str):
    return f'{s.lower()}.html'

# скраппинг
def scrap(url: str, alt_name = None):
    global glob_nav
    htm = get_htm(url)
    if htm == None: return None

    if not alt_name:
        alt_name = short_name(url)

    # удаляем комментарии
    htm = re.sub(r'<!.*?>','', htm)

    # парсим HTML файл
    soup = BeautifulSoup(htm, 'html.parser').find('div', {'class': 'b5a'})

    # предварительное форматирование текста
    soup.smooth()
    for i in soup.find_all(string = True):
        ii = i.replace('\r', ' ').replace('\n', ' ').strip(' ')
        if ii != '': i.replace_with(ii)
        else: i.extract()
    soup.smooth()

    # удаляем заголовок на ветку КМОП
    if url == 'index':
        soup.find('h2').decompose()

    # удаляем лишнее форматирование из таблиц
    for capt in soup.find_all('caption'):
        if capt.find('h4'): capt.h4.unwrap()
        [br.decompose() for br in capt.find_all('br')]
    del_attr(soup.find_all(['table', 'caption', 'tbody', 'tr', 'th', 'td']),
                           ['align', 'border', 'cellpadding', 'cellspacing', 'width'])

    # загружаем изображения
    del_attr(soup.find_all('img'), ["align", "hspace", "vspace", "width"])
    for img in soup.find_all('img'):
        if Path(img['src']).name == 'img.jpg':
            img.decompose()
        elif not img_to_symb(img):
            img['src'] = get_img(img['src'])
            if img.parent.name == 'td':
                del_attr([img.parent], ['width'])
                img.parent.name = 'figure'
            else:
                img.wrap(BeautifulSoup().new_tag('figure'))
            fig = img.parent
            for p in ['tr', 'tbody', 'table', 'h4']:
                if fig.parent.name == p:
                    fig.parent.unwrap()
            fig.append(BeautifulSoup().new_tag('figcaption'))
            if img.get('alt'):
                fig.figcaption.append(img['alt'])

    
    for a in soup.find_all('a'):
        if a.get('target'): del a.attrs['target']
        # пустые ссылки
        if not a.get('href'):
            a.string = str(a.string).join([' ', ' '])
            a.unwrap()
        # подгружаем изображения, зафиксированные в виде ссылок
        elif '.jpg' in a['href'] or '.gif' in a['href']:
            a['href'] = get_img(a['href'])
        # поиск ссылок на другие страницы сайта
        elif 'microshemca.ru' in a['href']:
            a['href'] = scrap(Path(a['href']).name)

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), 'html.parser')
    template.footer.clear()

    content = template.find('div', id = "content")

    # добавляем содержимое
    content.extend(soup)
    soup.unwrap()

    # удаляем <br>
    [i.replace_with(' ') for i in template.find_all('br')]

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

    return alt_name

if __name__ == '__main__':
    childs = 'index.AG1.AG3.AP1.ID1.ID3.ID4.ID8.ID9.ID10.ID11.ID12.ID13.ID15.IE1.IE2.IE4.IE5.IE6.IE7.IE8.IE9.IE14.IM1.IM2.IM3.IP2.IP3.IP4.IR1.IR13.IR15.IR17.IR32.IV1.KP1.KP2.KP5.KP7.LA1.LA2.LA3.LA4.LA6.LA7.LA8.LA10.LA11.LA12.LA13.LA18.LD1.LD3.LE1.LE2.LE3.LE4.LE5.LE6.LI1.LI5.LL1.LL2.LN1.LN2.LN3.LN5.LN6.LP4.LP5.LP7.LP8.LP9.LP10.LP11.LR1.LR3.PP5.PR6.PR7.RE3.RE21.RE22.RE23.RE24.RP3.RU1.RU2.RU5.RU7.TL1.TL2.TL3.TM2.TM5.TM7.TM8.TV1.TV15'.split('.')
    childs = [i for i in childs if i not in 'IE7.IM3.IV1.KP2.RU1.TV1.TV15'.split('.')]
    if len(sys.argv) > 1:
        childs = [i for i in childs if i in sys.argv[1:]]

    glob_nav = [BeautifulSoup(f'<li><a href = "{short_name(i)}">к155{i.lower()}</a></li>', 'html.parser').li for i in childs]

    for i in childs: scrap(i)
