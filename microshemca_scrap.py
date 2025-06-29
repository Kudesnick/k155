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
alt_content_path = Path('..').joinpath('chipinfo')

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

def menu_generator(id: str, menu: dict):
    firstkey = list(menu.keys())[0]
    if not 'К155' in menu[firstkey]:
        # формируем текст ссылки
        repl = {'a': 'а', 'g': 'г', 'p': 'п', 'i': 'и', 'v': 'в', 'd': 'д', 'e': 'е', 'm': 'м', 'r': 'р', 'l': 'л', 'n': 'н', 'u': 'у', 't': 'т', 'k': 'к', 'x': 'х'}
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
                (' <b>', ' '),
                ('</b> ', ' '),
                ('<strong>', ' '),
                ('</strong>', ' '),
                ('/>', '>'),
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
                ('комплимент', 'комплемент'),
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
    if url in ['7490', '7492', '74160']:
        patterns.append(('&bull; ', '</li><li>'))
    if url == '7497':
        patterns.append(('<ul compact tupe="disc">', '</p><ul compact tupe="disc"><li>'))
    if url in ['ID9', 'IP3']:
        patterns.append(('<table', '</p><table'))
        patterns.append(('<br />', ' '))
        patterns.append(('<br />', ' '))
    if url == 'IE8':
        patterns.append(('уравнению: <br/>', 'уравнению: </p><p>'))
        patterns.append(('). <br/>Здесь', ')</p><p>Здесь'))
    if url == 'IP4':    
        patterns.append(('Микросхема ', '<p>Микросхема '))
        patterns.append(('<br/>', ' '))
        patterns.append(('С<sub>n+y</sub> = ', '</p><p>С<sub>n+y</sub> = '))
        patterns.append(('С<sub>n+z</sub> = ', '</p><p>С<sub>n+y</sub> = '))
        patterns.append(('<p><span class=q>G</span>', '</p><p><span class=q>G</span>'))
    if url == 'IM2':    
        patterns.append(('воэможные', 'возможные'))
    if url == 'IR32':    
        patterns.append((';</td>', '</td>'))
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
    if url == '7414':
        patterns.append(('сигналов,формирователи', 'сигналов, формирователи'))
    if url == '7472':
        patterns.append(('74imp.jpg" ', '74imp.jpg" alt="Временная диаграмма тактового импульса" '))
    if url == 'LA6':
        patterns.append(('<td align=center> 15 </td>', '<td align=center> 14 </td>'))
    if url == 'LA7':
        patterns.append(('представляет собой', 'представляют собой'))
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
    if url == 'LN1':
        patterns.append(('представляет собой', 'представляют собой'))
    if url == 'LN5':
        patterns.append(('до 15 8', 'до 15 В'))
    if url == 'LP4':
        patterns.append(('imgLN4.jpg', 'imgLP4.jpg'))
    if url == 'LP9':
        patterns.append(('<td align=center> 7 </td>', '<tr><td align=center> 7 </td>'))
    if url == 'LR4':
        patterns.append(('<td align=center> 2 </td>', '<tr><td align=center> 2 </td>'))
    if url == 'RE3a':
        patterns.append(('При нажатии; кнопки SB1 &laguo;Запись&raguo;', 'При нажатии кнопки SB1 &laquo;Запись&raquo;'))
        patterns.append(('микросхемы <b>К155РЕ3</b> её', 'микросхемы К155РЕ3 её'))
    if url == 'RU1-3':
        patterns.append(('записи 1 и О', 'записи лог. "1" и лог. "0"'))
    if url in ['TM5', 'TM7']:
        patterns.append(('защелк', 'защёлк'))
        patterns.append(('ячёйку', 'ячейку'))
    if url == 'TW1':
        patterns.append(('<td><u>&nbsp;&nbsp;</u>&prod;<u>&nbsp;&nbsp;</u></td>', '<td>&#8645;</td>'))
    if url == 'statii/a1':
        patterns.append(('<a href="https://engars.ru/catalog/tsepi/">Цепь круглозвенная</a>', ''))
        patterns.extend([('22О', '220'), ('ЗООО','3000'), ('ЗОО','300'), ('О,З','0,3'), ('0СТ','ОСТ'),
                         ('К555 5,5','К555 — 5,5'), ('К1533 6','К1533 — 6'),
                         ('градусов С','&#8451;'), ('градусов.','&#8451;.'), ('20...30\' С','20...30 &#8451;'),  ('40\' С','40 &#8451;'),
                         ('(— 5,2 В)','(-5,2 В)'), ('(— 2 или —2,4 В)','(-2 или -2,4 В)'), ('—4,5 и —2 В','-4,5 и -2 В'),
                         ('K531, KI533','К531, К1533'),
                         ('токи).', 'токи).</p>'),
                         ('срабатывание ИС.', 'срабатывание ИС.</p>')])
    if url == 'statii/a2':
        patterns.append(('Р = 1/(2&pi;&radic;<span class=q>LC<sub>э</sub></span>', 'Р = 1/(2&pi;&radic;(LC<sub>э</sub>))')),
    if url == '74366':
        patterns.append(('<a href="https://www.microshemca.ru/74365"', '<a href="74365.html"')),
    if url == '74367':
        patterns.append(('<th colspan=3>Входы</th>', '<th colspan=2>Входы</th>')),    
    if url == '74368':
        patterns.append(('<a href="https://www.microshemca.ru/74367"', '<a href="74367.html"')),
    if url == '7481':
        patterns.append(('Q<sub>H</sub> подается напряжение низкого уровня.', 'Q<sub>H</sub> подается напряжение низкого уровня.</p>'))
    if url == '74175':
        patterns.append(('<th>Выходы</th>', '<th colspan=2>Выходы</th>'))
    if url == '74185':
        patterns.append(('<th colspan=5>Выходы ', '<th colspan=8>Выходы '))
    if url == '74172':
        patterns.append(('1WO/R0 и 2W2/R2.', '1WO/R0 и 2W2/R2.</li>'))
        patterns.append(('на <li>Выходы', 'на выходы данных.</li><li>Выходы'))
        patterns.append(('разрешенич', 'разрешения'))
    if url == 'index':
        patterns.append(('<td colspan=3>I<sup>0</sup><sub>вых</sub>= 20 мА</td>', '<td colspan=3>I<sup>0</sup><sub>вых</sub>= 20 мА</td><td colspan=2></td>'))
        patterns.append(('<td colspan=3>I<sup>1</sup><sub>вых</sub>= -1 мА</td>', '<td colspan=3>I<sup>1</sup><sub>вых</sub>= -1 мА</td><td colspan=2></td>'))
        patterns.append(('img1.jpg" ', 'img1.jpg" alt="Схема логического элемента ТТЛ"'))

    htm = mrep(htm, patterns)

    # парсим HTML файл
    soup = BeautifulSoup(htm, parser).find('div', {'class': 'b5a'})

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
        [br.unwrap() for br in capt.find_all('br')]
    del_attr(soup.find_all(['table', 'caption', 'tbody', 'tr', 'th', 'td', 'ul', 'ol']),
                           ['align', 'border', 'cellpadding', 'cellspacing', 'width', 'tupe', 'compact', 'type', 'start'])

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

    if url == 'ID3':
        tbl = soup.find('table').find('br').unwrap()
    
    if url == 'IE2':
        tbl = soup.find('table').find('br').unwrap()
        soup.find('table').unwrap()
        tbl = soup.find('table')

    # Чиним списки, не завернутые в ul 
    ul = None
    for li in soup.find_all('li'):
        if li.parent.name in ['ul', 'ol']:
            ul = None
        elif ul == None:
            ul = BeautifulSoup().new_tag('ul')
            li.wrap(ul)
        else:
            ul.append(li)

    # Убираем вложенность таблиц
    for tbl in soup.find_all('table'):
        for prnt in ['p', 'td', 'tr', 'tbody', 'table']:
            if tbl.parent.name == prnt:
                tbl.parent.unwrap()

    # Убираем абзацы внутри ячеек таблиц
    [p.unwrap() for p in soup.find_all('p') if p.parent.name in ['th', 'td']]
    
    # Фиксим незакрытые теги таблиц
    for tbl in soup.find_all('table'):
        tbl.extend(tbl.find_all('tr'))
        for tr in tbl.find_all('tr'):
            tr.extend(tr.find_all(['th', 'td']))

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

    # Нормализуем ширину последней ячейки в столбце
    def set_cols(tr: BeautifulSoup, cols: int) -> int:
        tds = tr.find_all(['td', 'th'])
        cols = max(sum([int(i.get('colspan', '1')) for i in tds]), cols)
        td = tds[-1]
        colspan = cols - sum([int(i.get('colspan', '1')) for i in tds[:-1]])
        if colspan > 1: td['colspan'] = colspan
        elif td.get('colspan'): del td.attrs['colspan']
        return cols
    
    if url in ['7492', '7493']:
        for tbl in soup.find_all('table'):
            cols = 0
            for tr in tbl.find_all('tr'):
                cols = set_cols(tr, cols)

    if url == 'LP10': # Исправление заголовка таблицы истинности
        tr = soup.table.find_all('tr')[1]
        tr.insert(3, tr.th)

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
    for h in soup.find_all('h2'):
        h.name = 'h1'
        h.string = h.text.strip('.')
    for h in soup.find_all('h4'): h.name = 'h2'

    soup.find('h1').insert_after(menu_generator('hor', hor_menu))

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), parser)

    content = template.find('div', id = "content")
    content.clear()

    # добавляем содержимое

    content.extend(soup)
    soup.unwrap()

    # удаляем <br>
    [br.unwrap() for br in template.find_all('br')]

    # глобальная навигация
    chip_ul = template.find(id = 'map').ul
    chip_ul.extend(glob_nav)

    # добавляем информацию об источниках
    template.footer.append(BeautifulSoup(f'<p>Scrapped from <a href="{base_url}{url}" title="Онлайн справочник microshemca.ru: {content.h1.text}">{base_url}{url}</a></p>', parser))

    # дополняем <title>
    template.title.string = template.h1.text

    # сохраняем результат в файл
    template.smooth()
    # Удаляем пустые абзацы и извлекаем списки из абзацев
    [p.unwrap() for p in template.find_all('p') if p.text.strip() == '']
    [ul.parent.unwrap() for ul in template.find_all(['ul', 'ol']) if ul.parent.name == 'p']
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(alt_name).write_text(template.prettify(), enc)
    print(f'File "{alt_name}" writed')

    return alt_name

if __name__ == '__main__':
    childs = 'AG1.AG3.AP1.IW1.IW3.ID1.ID3.ID4.ID7.ID8.ID9.ID10.ID11.ID12.ID13.ID15.ID24.IE1.IE2.IE4.IE5.IE6.IE7.IE8.IE9.IE14.IM1.IM2.IM3.IP2.IP3.IP4.IP6-7.IR1.IR13.IR15.IR17.IR32.KP1.KP2.KP5.KP7.LA1.LA2.LA3.LA4.LA6.LA7.LA8.LA10.LA11.LA12.LA13.LA18.LD1.LD3.LE1.LE2.LE3.LE4.LE5.LE6.LI1.LI4.LI5.LL1.LL2.LN1.LN2.LN3.LN5.LN6.LP4.LP5.LP7.LP8.LP9.LP10.LP11.LR1.LR3.LR4.PP5.PR6.PR7.RE3.RE21.RE22.RE23.RE24.RP1.RP3.RU1-3.RU2.RU5.RU7.TW1.TW15.TL1.TL2.TL3.TM2.TM5.TM7.TM8.XL1'.split('.')
    # фактически отсутствующие страницы
    # IE7 объединена с IE6
    # IM3 отсутствует
    # KP2 отсутствует
    childs = [i for i in childs if i not in 'IE7.IM3.KP2'.split('.')]
    
    # дополнительные статьи
    articles = {
        'index'    : 'ttl',
        'RE3a'     : 're3a',
        'statii/a1': 'appl',
        'statii/a2': 'gen'
        }

    childs.extend(articles.keys())

    if len(sys.argv) > 1:
        childs = [i for i in sys.argv[1:]]

    glob_nav = [BeautifulSoup(f'<li><a href = "{short_name(i)}">К155{Path(short_name(i)).stem}</a></li>', parser).li for i in childs if not i in articles.keys()]

    # подгружаем пользовательские картинки
    img_copy(['imgLP4.jpg', 'styles.css'])

    for i in childs: scrap(i)
