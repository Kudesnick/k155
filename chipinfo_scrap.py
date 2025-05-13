# -*- coding: utf-8 -*-

from gettext import find
import requests
from bs4 import BeautifulSoup
from pathlib import Path 
import sys
import re

enc = 'utf-8'
parser = 'html.parser'

base_url = 'http://www.chipinfo.ru/dsheets/ic/155/'
alt_content_path = Path('..').joinpath('kiloom')
replace_collect = 'img_replace.html'
allow_id = ['package', 'package1', 'package2', 'cscheme', 'cscheme1', 'cscheme2', 'elp', 'application', 'analog', 'literature']

# Пакетная замена подстрок 
def mrep(s: str, p):
    for i in p: s = s.replace(i[0], i[1])
    return s

# пакетная замена картинок на html символы
def srep(self: BeautifulSoup, imgname: str, sym: str):
    for i in self.find_all('img', {'src': f'img/{imgname}.gif'}): i.replace_with(BeautifulSoup(sym, parser))

# скачивание файла или извлечение его из кэша
def get_htm(url: str):
    global base_url, enc
    idx = 'htm'
    full_url = f'{base_url}{url}'
    if not Path(f'{url}.{idx}').is_file():
        req = requests.get(full_url)
        if req.status_code != 200:
            print(f'Error. Failed to download "{full_url}"', file = sys.stderr)
            return None
        else:
            print(f'Download "{full_url}"')
            req = req.text.encode(enc, errors = 'ignore').decode(enc, errors = 'ignore')
            Path(f'{url}.{idx}').write_text(req, encoding = enc)
    return Path(f'{url}.{idx}').read_text(encoding = enc)

def get_img(url: str):
    global base_url
    cache = Path(url).name
    if not Path(cache).is_file():
        full_url = f'{base_url}{url}'
        req = requests.get(full_url)
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

# добавляем к таблице <thead>, <caption>, <body>
def table_frmt(table, bs, caption = None):
    if not table.tbody:
        t = table.find_all('tr', recursive = False)
        table.append(bs.new_tag('tbody'))
        table.tbody.extend(t)
    if not table.thead and table.find('th'):
        table.insert(0, bs.new_tag('thead'))
        t = table.find('th').parent
        table.thead.append(t)
    if caption:
        if not table.caption:
            table.insert(0, bs.new_tag('caption'))
        table.caption.append(caption)

# Выдергиваем фразу о количестве интегральных элементов
def get_el_cnt(s: str):
    res = re.findall('Содерж\S+\s+\d+\s+интегральны\S+\s+элемент\S*\.', s)
    if len(res) > 0:
        return res[0].replace('  ', ' ')
    else:
        return ''

# заменяем содержимое секции, если нашли паттерн
def repl_section(section, repl_soup, url):
    repl_section = repl_soup.find('section', {'id': section['id'], 'name': url})
    if repl_section:
        del_tag = BeautifulSoup().new_tag('del')
        del_tag.extend(section.find_all(recursive = False))
        del_tag.extend(section.find_all(string = True, recursive = False))
        repl_section.name = 'ins'
        del repl_section.attrs['id']
        del repl_section.attrs['name']
        section.extend([del_tag, repl_section])
        print(f'Report: File "{url}" replace section "{section["id"]}" from manual pattern.')

# добавляем секцию, если её нет
def insert_section(template, repl_soup, url):
    template_sections = [i for i in template.find_all('section') if i['id'] in allow_id]
    insert_sections = [i for i in repl_soup.find_all('section', {'name': url}) if i['id'] in allow_id and i['id'] not in [ii['id'] for ii in template_sections]]
    for section in insert_sections:
        for prev in template_sections[::-1]:
            if (allow_id.index(prev['id']) < allow_id.index(section['id'])):
                ins_tag = BeautifulSoup().new_tag('ins')
                ins_tag.extend(section.find_all(recursive = False))
                ins_tag['cite'] = section['cite']
                section.append(ins_tag)
                del section.attrs['cite']
                del section.attrs['name']
                prev.insert_after(section)
                template.find('a', {'href': f'#{prev["id"]}'}).parent.insert_after(BeautifulSoup(f'<li><a href="#{section["id"]}">{section.h2.text}</a></li>', parser).li)
                print(f'Report: File "{url}" insert section "{section["id"]}" after "{prev["id"]}" from manual pattern.')
                break

# копирование пользовательских картинок
def img_copy(patterns: list):
    for i in [f for f_ in [Path('..').glob(e) for e in patterns] for f in f_]:
        Path(i.name).write_bytes(i.read_bytes())

# скраппинг
def scrap(url: str):
    global glob_nav
    htm = get_htm(url)
    if htm == None: return None

    # парсим HTML файл
    soup = BeautifulSoup(htm, parser).find('div', {'id': 'content'})

    # извлекаем ссылки на элементы контента
    anchors = [i for i in soup.find_all('a') if i.get('href') != None and i.get('href').find('#') == 0]

    # чиним сломанный HTML (незакрытые ссылки)
    patterns = [('<div id="smo_line">', '</a><div id="smo_line">'),
                ('<p>\n<a name="cscheme">', '<a name="cscheme">'), # special for kp1.html
                ('</p>\n\n<a name="elp">', '<a name="elp">')]      # special for kp1.html
    patterns.append(('мощность</td>\n<td><br>', 'мощность</td>\n<td>'))
    def add_pattern1(s: str):
        return (f'<a name="{s}">', f'</a><a name="{s}">')
    def add_pattern2(s: str):
        return (f'<a name="{s}"></a>', f'<a name="{s}">')
    patterns.extend([add_pattern1(i.get('href')[1:]) for i in anchors[1:]])
    patterns.extend([add_pattern2(i.get('href')[1:]) for i in anchors[:]])
    patterns.append(('не более <br>\n', '&le; '))
    patterns.append(('не менее <br>\n', '&ge; '))
    patterns.append(('не более<br>\n', '&le; '))
    patterns.append(('не менее<br>\n', '&ge; '))
    patterns.append(('не более<br> \n', '&le; '))
    patterns.append(('не менее<br> \n', '&ge; '))
    patterns.append(('не более', '&le;'))
    patterns.append(('не менее', '&ge;'))
    patterns.append(('&nbsp;', ''))
    patterns.append(('итнегральных', 'интегральных'))
    patterns.append(('коллктор', 'коллектор'))
    patterns.append(('Приорететный', 'Приоритетный'))
    patterns.append(('</b> Справочник', '</b>: Справочник'))
    if 'ie' in url:
        patterns.append(('К155ИД4', 'К155ИЕ1'))
        patterns.append(('КМ155ИД', 'КМ155ИЕ'))
    if 'im2.' in url:
        patterns.append(('одноразрядный', '<del>одноразрядный</del><ins>двухразрядный</ins>'))
    if 'la18.' in url:
        patterns.append(('с открытым коллектором', 'с <ins>мощным</ins> открытым коллектором'))
    if 'le6.' in url:
        patterns.append(('представляет собой ', 'представляет собой <ins cite="kiloom.ru">магистральный усилитель — </ins>'))
    if 'lp11.' in url:
        patterns.append(('lp10.gif', 'lp11.gif'))
    if 'pr7.' in url:
        patterns.append(('двоично-десятичного кода в\nдвоичный', '<del>двоично-десятичного кода в двоичный</del><ins>двоичного кода в двоично-десятичный</ins>'))
    if 'tv1.' in url:
        patterns.append(('Микросхема представляет собой два независимых тактируемых J-K триггера с\nустановкой в 0 и 1.', 'Микросхема представляет собой <del>два независимых тактируемых J-K триггера с установкой в 0 и 1.</del><ins>универсальный многоцелевой JK-триггер с элементами 3-И по входам J и K.</ins>'))
    htm = mrep(htm, patterns)
    ss = BeautifulSoup(htm, parser)
    soup = ss.find('div', {'id': 'content'})

    # исправление ошибок форматирования для kp1.html
    kp1 = soup.find(string = 'Корпус ИМС К155КП1')
    if kp1:
        kp = kp1.parent.parent.parent.parent.parent
        kp.tr.td.unwrap()
        kp.tr.unwrap()
        kp.name = 'a'
        kp['name'] = 'package'
        del kp.attrs['border']

    # исправляем имя секции
    sch = soup.find('a', {'href': '#scheme'})
    if sch:
        sch['href'] = '#cscheme'
        soup.find('a', {'name': 'scheme'})['name'] = 'cscheme'

    # обновляем ссылки на элементы контента
    anchors = [i for i in soup.find_all('a') if i.get('href') != None and i.get('href').find('#') == 0]

    # исправление ошибок форматирования для kp1.html
    if kp1:
        kp = ss.new_tag('a')
        kp['href'] = '#package'
        kp.append('Корпус ИМС К155КП1')
        anchors.insert(0, kp)

    # заменяем изображения на спецсимволы HTML
    srep(soup, 'leq2', '&le;')
    srep(soup, 'geq2', '&ge;')
    srep(soup, 'pem2', '&plusmn;')

    # предварительное форматирование текста
    soup.smooth()
    for i in soup.find_all(string = True):
        ii = i.replace('\r', ' ').replace('\n', ' ').strip()
        if ii != '': i.replace_with(ii)
        else: i.extract()
    soup.smooth()

    # подгружаем шаблон
    template = BeautifulSoup(Path('../template.html').read_text(enc), parser)

    # подгружаем файл с паттернами для замены
    replace_soup = BeautifulSoup(Path('..').joinpath(replace_collect).read_text(enc), parser)

    # подгружаем альтернативу с kiloom.ru
    alt_content = None
    alt_file = alt_content_path.joinpath(url)
    if alt_file.is_file():
        alt_content = BeautifulSoup(alt_file.read_text(enc), parser)

    content = template.find(id = "content")

    # добавляем краткое описание
    content.append(template.new_tag('h1'))
    content.h1.append(ss.find('div', {'class': 'menu-link-text'}).text.replace('Чипинфо', '').strip(' .'))
    p = soup.find('p', recursive = False or url == 'kp1.html')
    if p:
        content.append(template.new_tag('section'))
        content.section.append(p)
        content.section['id'] = 'preamble'
        # поиск картинок в описании (код запускался один раз для диагностики)
        # imgs = p.find_all('img')
        # if imgs:
        #     print(f'Warning! File "{url}" contains images: {", ".join([i["src"] for i in imgs])}.')
        # Warning! File "le2.html" contains images: img/le2-2.gif, img/le2-3.gif
        # Warning! File "tv1.html" contains images: img/tv1-2.gif
        # Warning! File "tv15.html" contains images: img/tv15-2.gif
        # Warning! File "tm2.html" contains images: img/tm2-2.gif
        
        # если отсутствует информация о количестве интегралных элементов, пытаемся её добавить
        if get_el_cnt(p.text) == '':
            if alt_content:
                el_cnt = get_el_cnt(alt_content.find('div', {'class': 'entry-content'}).p.text).replace('Содержат', 'Содержит')
                if el_cnt != '':
                    for k, v in enumerate(p.contents):
                        if 'Корпус' in v:
                            p.contents[k].replace_with(BeautifulSoup(v.replace('Корпус', f'<ins cite="kiloom.ru">{el_cnt}</ins> Корпус'), parser))
                            print(f'Report: File "{url}" append count of integration elements from kiloom.ru.')
                            break

        repl_section(content.section, replace_soup, url)

    # собираем оглавление
    nav = BeautifulSoup('<nav><ul></ul></nav>', parser)
    for i in anchors:
        a = BeautifulSoup('<li></li>', parser)
        a.li.append(i)
        nav.ul.append(a)
    content.append(nav)

    # чистим таблицу главной страницы, если она найдена
    center = soup.find('center')
    if center != None:
        for i in center.find_all('br'):
            i.name = 'wbr'
        center.name = 'section'
        center['id'] = 'index'
        del_attr(center.find_all('table'), ['border', 'cellpadding', 'cellspacing'])

        # Добавляем информацию о к155лр4
        center.next.insert(77, BeautifulSoup('<tr><td><a href="lr4.html">К155ЛР4<br> КМ155ЛР4</a></td><td>Логический элемент 4-4И-2ИЛИ-НЕ с возможностью расширения по ИЛИ</td></tr>', parser))

        content.append(center)

        glob_nav = [BeautifulSoup('<li><a href = "index.html">&lt;&lt; Домой</a></li>', parser).li]
        glob_nav.extend([BeautifulSoup(f'<li><a href = "{tr.td.a["href"]}" title = "{str(tr.td.next_sibling.text)}">{tr.td.a.find(string = True)}</a></li>', parser).li for tr in center.find_all('tr') if tr.td])

        # добавляем к таблице <thead>, <caption>, <body>
        if center.table: table_frmt(center.table, template, 'Перечень микросхем серии 155')

    # добавляем найденные разделы
    for a in anchors:
        section = soup.find('a', {'name': a.get('href')[1:]})
        del_attr(section.find_all('font'), ['size'])
        if not section.i.font:
            # чиним "перевернутую вложенность"
            section.font.i.name = 'font'
            section.font.name = 'i'
        section.i.font.unwrap()
        section.i.name = 'h2'
        del_attr(section.find_all('h2'), ['align'])
        section['id'] = section['name']
        del section.attrs['name']
        section.name = 'section'
        content.append(section)

        # заменяем содержимое секции, если нашли паттерн
        repl_section(section, replace_soup, url)

        # форматируем таблицу
        if section.table:
            del_attr(section.find_all('table'), ['border', 'cellpadding', 'cellspacing'])
            table_frmt(section.table, template, section.find('h2').text)

        # подгружаем изображения
        if section.img:
            img = section.img
            fig = section.img.wrap(template.new_tag('figure'))
            fig.append(BeautifulSoup(f'<figcaption>{section.find("h2").text}</figcaption>', parser))
            del_attr([img], ['align', 'border', 'height', 'width', 'hspace'])
            img['src'] = get_img(img['src'])

        # преобразуем картинки с верхним подчеркиванием в спецсимволы
        for img in section.find_all('img', recursive = False):
            text = BeautifulSoup(f'<span class="q">{Path(img["src"]).stem[:-1].upper()}</span>', parser)
            img.replace_with(text)

        # преобразуем список выводов в таблицу
        if section['id'] in ['cscheme', 'cscheme1', 'cscheme2']:
            [i.extract() for i in section.find_all('br')]
            section.smooth()
            h2 = section.h2.extract()
            figure = section.figure.extract()
            s = ''.join([str(i) for i in section.contents])
            # чиним форматирование для ИД3
            if url == 'id3.html':
                for r in ['1 - 11', '13 - 17', '20 - 23', 'Y1 - Y11', 'Y12 - Y16']:
                    s = s.replace(r, r.replace(' ', ''))
            pins = {i.split(' - ')[0].strip(): i.split(' - ')[1].strip() for i in s.split(';') if i.find(' - ') >= 0}
            section.clear()
            section.append(h2)
            section.append(figure)
            if len(pins) > 0:
                table = BeautifulSoup('<table><caption>Назначение выводов</caption><thead><tr><th>№ вывода</th><th>Назначение</th></tr></thead><tbody></tbody></table>', parser)
                table.tbody.extend([BeautifulSoup(f'<tr><td>{k}</td><td>{v}</td></tr>', parser) for k, v in pins.items()])
                section.append(table)
        
        # форматируем таблицу параметров или предельно допустимых значений
        if section['id'] in ['limits', 'elp']:
            section.table.tbody.unwrap()
            tr_list = [i for i in section.table.find_all('tr')]
            for tr in tr_list:
                tbody = template.new_tag('tbody')
                tbody.append(tr.extract())
                section.table.append(tbody)
                tbody.tr.td.decompose()
                while (tbody.find('br')):
                    param = tbody.find('br').parent
                    param_arr = str(''.join([str(i) for i in param.contents])).split('<br/>')
                    param.clear()
                    value = param.next_sibling
                    value_arr = str(''.join([str(i) for i in value.contents])).split('<br/>')
                    value.clear()
                    if value_arr[0] != '':
                        param.append(BeautifulSoup(param_arr.pop(0), parser))
                        value.append(BeautifulSoup(value_arr.pop(0), parser))
                    else:
                        value.decompose()
                        param.append(BeautifulSoup(param_arr.pop(0), parser))
                        value_arr.pop(0)
                        param['colspan'] = '2'
                        param.name = 'th'
                    for i in range(len(value_arr)):
                        tr_new = BeautifulSoup(f'<tr><td>{param_arr[i]}</td><td>{value_arr[i]}</td></tr>', parser)
                        tbody.append(tr_new)
            # сравниваем таблицу с тем, что предоставляет kiloom.ru
            if alt_content:
                alt_section = alt_content.find('section', id = section['id'])
                if alt_section and len(section.find_all('tr')) < len(alt_section.find_all('tr')):
                    del_tag = BeautifulSoup().new_tag('del')
                    ins_tag = BeautifulSoup().new_tag('ins')
                    ins_tag['cite'] = 'kiloom.ru'
                    section.extend([del_tag, ins_tag])
                    section.table.wrap(del_tag)
                    alt_section.table.wrap(ins_tag)
                    section.append(alt_section.ins)
                    print(f'Report: File "{url}" replace table "{section["id"]}" from kiloom.ru.')

        # форматируем список аналогов
        if section['id'] == 'analog':
            context = section.dir.p.b.text.split(',')
            section.dir.p.b.unwrap()
            section.dir.p.unwrap()
            section.dir.name = 'ul'
            section.ul.clear()
            section.ul.extend([BeautifulSoup(f'<li>{i.strip()}</li>', parser) for i in context])
        
        # форматируем список литературы
        if section['id'] == 'literature':
            for i in section.dir.find_all('p'):
                i.name = 'li'
            section.dir.name = 'ul'
            [b.unwrap() for b in section.ul.find_all('b')]

            # добавляем информацию об источниках
            if url != 'lr4.html':
                new_link = BeautifulSoup(f'<li><a href="{base_url}{url}">Онлайн справочник chipinfo.ru: {content.h1.text}</a></li>', parser)
                section.ul.append(new_link)

            if alt_content:
                new_link = BeautifulSoup(f'<li><a href="{alt_content.body["href"]}">Онлайн справочник kiloom.ru: {alt_content.body["name"]}</a></li>', parser)
            section.ul.append(new_link)

            # добавляем пользовательские элементы в информацию об источниках
            for li in [i for i in replace_soup.find('ul', id = 'source_append').find_all('li') if url in i['name'].split(' ')]:
                del li.attrs['name']
                section.ul.append(li)

    # добавляем целые разделы
    insert_section(template, replace_soup, url)

    # заменяем картинки на заранее набранные фрагменты
    for i in template.find_all('img'):
        pattern = replace_soup.find('div', id = i['src'])
        if pattern:
            print (f'Report: File "{url}" replace image "{pattern["id"]}" from "{replace_collect}".')
            template.append(pattern)
            i.replace_with(pattern)
            # убираем обертку параграфа
            pp = pattern.parent
            if pp.name == 'p':
                np = template.new_tag('p')
                pp.insert_after(np)
                np.extend(pp.contents[pp.contents.index(pattern) + 1:])
                pp.insert_after(pattern)
            pattern.unwrap()

    # дополняем <title>
    if url != 'index.html':
        repl = {'a': 'а', 'g': 'г', 'p': 'п', 'i': 'и', 'v': 'в', 'd': 'д', 'e': 'е', 'm': 'м',
                'r': 'р', 'l': 'л', 'n': 'н', 'u': 'у', 't': 'т', 'k': 'к'}
        s = Path(url).stem
        for k, v in repl.items():
            s = s.replace(k, v)
        template.find('title').clear()
        template.find('title').append(f'к155{s}')

    del_attr(template.find_all('td'), ['valign'])

    # удаляем <br>
    [i.extract() for i in template.find_all('br')]
    for i in template.find_all('wbr'):
        i.name = 'br'

    # глобальная навигация
    map = template.find(id = 'map')
    map.append(template.new_tag('ul'))
    for li in glob_nav:
        map.ul.append(li)

    # сохраняем результат в файл
    template.smooth()
    # for release used 'str(template)' instead of 'template.prettify()'
    Path(url).write_text(template.prettify(), enc)
    print(f'Report: File "{url}" is writed.')

    return center

if __name__ == '__main__':
    childs = [i['href'] for i in scrap('index.html').find_all('a')]
    if len(sys.argv) > 1:
        childs = [i for i in childs if i in sys.argv[1:]]
    else:
        childs.append('lr4.html')

    # подгружаем пользовательские картинки
    img_copy(['*.jpg', '*.png', '*.gif', 'styles.css', '*.html.htm'])

    for i in childs: scrap(i)
