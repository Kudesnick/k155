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
    cache = Path(url).name.replace('(2)', '')
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

def short_name(s: str):
    return f'{s.lower().replace("w", "v")}.html'

def try_int(s: str) -> int:
    try:
        return int(s)
    except:
        None

def menu_generator(id: str, hor_menu: dict, name: str = ''):
    menu = ''.join([f'<li><a href="{k}">{v}</a></li>' if k != name else f'<li>{v}</li>' for k, v in hor_menu.items()])
    return BeautifulSoup(f'<nav id="{id}"><ul>{menu}</ul></nav>' if len(hor_menu) > 1 else '', 'html.parser')

# копирование пользовательских картинок
def img_copy(patterns: list):
    for i in [f for f_ in [Path('..').glob(e) for e in patterns] for f in f_]:
        Path(i.name).write_bytes(i.read_bytes())

# скраппинг
def scrap(url: str, alt_name = None, hor_menu = None):
    global glob_nav
    htm = get_htm(url)
    if htm == None: return None
    if not hor_menu: hor_menu = dict()

    if not alt_name:
        alt_name = short_name(url)

    hor_menu[alt_name] = Path(alt_name).stem

    # удаляем комментарии
    htm = re.sub(r'<!.*?>','', htm)

    # чиним сломанный HTML (незакрытые ссылки, опечатки и пр.)
    patterns = [
                ('<strong>', ' '),
                ('</strong>', ' '),
                # AG1
                ('<span class=q>Q.</span>', '<span class=q>Q</span>.'),
                ('(или <span class=q>А2)</span>', '(или <span class=q>А2</span>)'),
                ('пяти строкам <a><a href', 'пяти строкам <a href'),
                # AG3
                ('c6poea', 'сброса'),
                # AP1
                ('<u>+</u>', '&plusmn;'),
                # TM2
                ('<table/>', '</table>'),
                # ID1
                ('выхода отключены', 'выходы отключены'),
                # ID3
                ('alt="Детские товары"></a>', 'alt="Детские товары"/></a>'),
                ('cartion>', 'caption>'),
                # ID8
                ('<br>', '<br/>'),
                # IE9
                ('&bull; ', '</li><li>'),
                ('QO', 'Q0'),
                # IE14
                ('1. Входной ток низкого уровня	не более -1,6 мА,', '<ol><li>Входной ток низкого уровня не более -1,6 мА,</li>'),
                ('2. Входной ток высокого уровня	не более 0,04 мА,', '<li>Входной ток высокого уровня не более 0,04 мА,</li>'),
                ('3. Потребляемая статическая мощность &le; 310 мВт.', '<li>Потребляемая статическая мощность &le; 310 мВт.</li></ol>'),
                # IM1
                ('С<sub>n</sub></p>.', 'С<sub>n</sub>&nbsp;.</p>'),
                # IP3
                ('(+)', '&#8853;'),
                # KP1
                ('(О — 15)', '(0 — 15)'),
                ('(АО — А3)', '(А0 — А3)'),
                # KP5
                ('(DO — D7)', '(D0 — D7)'),
                ('(АО — А2)', '(А0 — А2)'),
                # LD1
                ('</p>.', '.</p>'),
                ]
    # забытые аналоги
    patterns.extend([
                    ('Зарубежным аналогом микросхемы К155ИД24 соответствует дешифратор 7445.'  , 'Зарубежным аналогом микросхемы К155ИД24 является дешифратор <a href="https://microshemca.ru/7445">7445</a>.'),
                    ('Зарубежным аналогом микросхемы КМ155ИЕ2 является микросхема 7490.'       , 'Зарубежным аналогом микросхемы КМ155ИЕ2 является микросхема <a href="https://microshemca.ru/7490">7490</a>.'),
                    ('Зарубежным аналогом микросхемы К155ЛП10 является микросхема 74365.'      , 'Зарубежным аналогом микросхемы К155ЛП10 является микросхема <a href="https://microshemca.ru/74365">74365</a>.'),
                    ('Зарубежным аналогом микросхемы К55ЛП11 является микросхема 74367.'       , 'Зарубежным аналогом микросхемы К55ЛП11 является микросхема <a href="https://microshemca.ru/74367">74367</a>.'),
                    ('Зарубежным аналогом микросхем К155ТМ5, КМ155ТМ5 являются микросхемы 7477', 'Зарубежным аналогом микросхем К155ТМ5, КМ155ТМ5 являются микросхемы <a href="https://microshemca.ru/7477">7477</a>'),
                    ('Зарубежным аналогом микросхемы К155ТВ15 являются микросхемы 74109'       , 'Зарубежным аналогом микросхемы К155ТВ15 являются микросхемы <a href="https://microshemca.ru/74109">74109</a>'),
                    ])
    if url == 'ID9':
        patterns.append(('<table', '</p><table'))
    if url == '74181':
        patterns.append(('<th>Арифметические (M = L, C<sub>n</sub> = L)</th>','<th>Арифметические <nobr>(M = L, C<sub>n</sub> = L)</nobr></th>'))
        patterns.append(('<th>Логические (M = H)</th>','<th>Логические <nobr>(M = H)</nobr></th>'))
        patterns.append(('<th>Арифметические (M = L, <span class=q>C<sub>n</sub></span> = L)</th>','<th>Арифметические <nobr>(M = L, <span class=q>C<sub>n</sub></span> = L)</nobr></th>'))
        patterns.append(('<th>Логические (M = H)</th></tr>','<th>Логические <nobr>(M = H)</th></nobr></tr>'))

        patterns.append(('(А + <span class=q>В</span></td>', '(А + <span class=q>В</span>)</td>'))
        patterns.append(('<span class=q>В)</span>', '<span class=q>В</span>)'))
        patterns.append(('Логич. 1', 'Лог. "1"'))
        patterns.append(('Логич. 0', 'Лог. "0"'))
        patterns.append(('(доп. до 2</td>', '(доп. до 2)</td>'))
        patterns.append(('А(2хА)', 'А (2&#10005;А)'))

        patterns.append(('Минус', '-'))
        patterns.append(('минус', '-'))
        patterns.append(('Плюс', '+'))
        patterns.append(('плюс', '+'))
    if url == '7430':
        patterns.append(('<th colspan=2>Входы</th>', '<th>Входы</th>'))
    if url == 'LA6':
        patterns.append(('<td align=center> 15 </td>', '<td align=center> 14 </td>'))
    if url == 'LA10':
        patterns.append(('<td align=center> 10 </td>', '<tr>'))
        patterns.append(('<td> 7 </td>', ''))
    if url in ['LA10', 'LA11', 'LA13']:
        patterns.extend([(f'<td align=center> {i} </td>', '') for i in range(1, 16)])
    if url == 'LA18':
        patterns.append(('<td align=center> 10 </td>', '<tr><td align=center> 10 </td>'))
    if url == 'LE1':
        patterns.append(('(B4)</th></tr>', '(B4)</th>'))
        patterns.append(('<span class=q>(A4B4)</span></th>', '<span class=q>(A4B4)</span></th></tr>'))
    if url == 'LE2':
        patterns.append(('<td align=center> 6 </td>', '<tr><td align=center> 6 </td>'))
        patterns.append(('2Q=<span class=q>', '</p><p align=center>2Q=<span class=q>'))
    if url == 'LI4':
        patterns.append(('(С3)</th></tr>', '(С3)</th>'))
        patterns.append(('<span class=q>(A3B3С3)</span></th>', '<span class=q>(A3B3С3)</span></th></tr>'))
    if url == 'LP9':
        patterns.append(('<td align=center> 7 </td>', '<tr><td align=center> 7 </td>'))
    if url == 'LR4':
        patterns.append(('<td align=center> 2 </td>', '<tr><td align=center> 2 </td>'))
    if url == 'RU1-3':
        patterns.append(('записи 1 и О', 'записи лог. "1" и лог. "0"'))
    if url == 'TW1':
        patterns.append(('<td><u>&nbsp;&nbsp;</u>&prod;<u>&nbsp;&nbsp;</u></td>', '<td>&#8645;</td>'))
    if url == 'a1':
        patterns.append(('<a href="https://engars.ru/catalog/tsepi/">Цепь круглозвенная</a>', ''))
        patterns.extend([('22О', '220'), ('ЗООО','3000'), ('ЗОО','300'), ('О,З','0,3'), ('0СТ','ОСТ'),
                         ('К555 5,5','К555 — 5,5'), ('К1533 6','К1533 — 6'),
                         ('градусов С','&#8451;'), ('градусов.','&#8451;.'), ('20...30\' С','20...30 &#8451;'),  ('40\' С','40 &#8451;'),
                         ('(— 5,2 В)','(-5,2 В)'), ('(— 2 или —2,4 В)','(-2 или -2,4 В)'), ('—4,5 и —2 В','-4,5 и -2 В'),
                         ('K531, KI533','К531, К1533')])
    if url == 'a2':
        patterns.append(('Р = 1/(2&pi;&radic;<span class=q>LC<sub>э</sub></span>', 'Р = 1/(2&pi;&radic;(LC<sub>э</sub>))')),
    if url == '74366':
        patterns.append(('<a href="https://www.microshemca.ru/74365"', '<a href="74365.html"')),
    if url == '74367':
        patterns.append(('<th colspan=3>Входы</th>', '<th colspan=2>Входы</th>')),    
    if url == '74368':
        patterns.append(('<a href="https://www.microshemca.ru/74367"', '<a href="74367.html"')),


    htm = mrep(htm, patterns)

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
    del_attr(soup.find_all(['table', 'caption', 'tbody', 'tr', 'th', 'td', 'ul']),
                           ['align', 'border', 'cellpadding', 'cellspacing', 'width', 'tupe'])
    
    # удаляем лишнее форматирование у прочих элементов
    del_attr(soup.find_all(['ul']),
                           ['compact','tupe'])

    # загружаем изображения
    del_attr(soup.find_all('img'), ["align", "hspace", "vspace", "width"])
    for img in soup.find_all('img'):
        if Path(img['src']).name == 'img.jpg':
            img.decompose()
        elif not img_to_symb(img):
            img['src'] = get_img(img['src'])
            for prnt in ['h4', 'th', 'td', 'tr', 'tbody', 'table', 'h4']:
                if img.parent.name == prnt:
                    img.parent.unwrap()
            img.wrap(BeautifulSoup().new_tag('figure'))
            fig = img.parent
            fig.append(BeautifulSoup().new_tag('figcaption'))
            if img.get('alt'):
                fig.figcaption.append(img['alt'])

    # Убираем вложенность таблиц
    for tbl in soup.find_all('table'):
        for prnt in ['p', 'td', 'tr', 'tbody', 'table']:
            if tbl.parent.name == prnt:
                tbl.parent.unwrap()

    # Убираем декорацию текста
    [b.unwrap() for b in soup.find_all(['b', 'i', 'strong'])]

    # Убираем столбец с порядковыми номерами строк
    for tbl in soup.find_all('table'):
        if len(tbl.find('tr').find_all(['td', 'th'])) > 2:
            cnt = 0
            for tr in tbl.find_all('tr'):
                if not tr.find('td') and cnt == 0: continue # таблица с заголовком
                if (cnt + 1) != try_int(tr.find('td').string):
                    break
                cnt += 1
            else:
                for tr in tbl.find_all('tr'):
                    tr.find(['td', 'th']).extract()

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
            a['href'] = scrap(Path(a['href']).name, hor_menu = hor_menu)

    # нормализация заголовков
    for h in soup.find_all('h2'): h.name = 'h1'
    for h in soup.find_all('h4'): h.name = 'h2'

    soup.find('h1').insert_after(menu_generator('hor', hor_menu, alt_name))

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), 'html.parser')

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
    
    # добавляем информацию об источниках
    new_link = BeautifulSoup(f'<section id="literature"><h2>Литература</h2><ul><li><a href="{base_url}{url}">Онлайн справочник microshemca.ru: {content.h1.text}</a></li></ul></section>', parser)
    template.find(id = 'content').append(new_link)

    # сохраняем результат в файл
    template.smooth()
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(alt_name).write_text(template.prettify(), enc)
    print(f'File "{alt_name}" writed')

    return alt_name

if __name__ == '__main__':
    childs = 'index.AG1.AG3.AP1.ID1.ID3.ID4.ID7.ID8.ID9.ID10.ID11.ID12.ID13.ID15.ID24.IE1.IE2.IE4.IE5.IE6.IE7.IE8.IE9.IE14.IM1.IM2.IM3.IP2.IP3.IP4.IP6-7.IR1.IR13.IR15.IR17.IR32.IW1.IW3.KP1.KP2.KP5.KP7.LA1.LA2.LA3.LA4.LA6.LA7.LA8.LA10.LA11.LA12.LA13.LA18.LD1.LD3.LE1.LE2.LE3.LE4.LE5.LE6.LI1.LI4.LI5.LL1.LL2.LN1.LN2.LN3.LN4.LN5.LN6.LP4.LP5.LP7.LP8.LP9.LP10.LP11.LR1.LR3.LR4.PP5.PR6.PR7.RE3.RE21.RE22.RE23.RE24.RP1.RP3.RU1-3.RU2.RU5.RU7.TL1.TL2.TL3.TM2.TM5.TM7.TM8.TW1.TW15.XL1'.split('.')
    # фактически отсутствующие страницы
    # IE7 объединена с IE6
    # IM3 отсутствует
    # KP2 отсутствует
    childs = [i for i in childs if i not in 'IE7.IM3.KP2'.split('.')]
    # дополнительные статьи
    childs.extend(['a1', 'a2'])
    # статьи
    articles = 'index.re3a.a1.a2'.split('.')
    if len(sys.argv) > 1:
        childs = [i for i in sys.argv[1:]]

    glob_nav = [BeautifulSoup(f'<li><a href = "{short_name(i)}">К155{Path(short_name(i)).stem}</a></li>', 'html.parser').li for i in childs]

    for i in childs: scrap(i)

    # подгружаем пользовательские картинки
    img_copy(['styles.css'])
