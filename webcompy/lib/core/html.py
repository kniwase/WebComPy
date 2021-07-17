from typing import List, Literal, Tuple
from itertools import zip_longest
from browser import window, load
from javascript import RegExp, String


self_closing_tag_pattern = RegExp.new(r'<([a-zA-Z0-9-]+)([^<>]*?)/>', 'g')


def self_closing_tag_replacer(_: str, *p: str):
    return f'<{p[0]}{p[1]}></{p[0]}>'


def conv_self_closing_tags(html_text: str) -> str:
    return String.new(html_text).replace(
        self_closing_tag_pattern, self_closing_tag_replacer)


def cleanse_html(html_text: str) -> str:
    lines = (line.strip() for line in html_text.split('\n'))
    lines = (line for line in lines if line)
    html_text = (' '.join(lines)).replace('> ', '>')
    html_text = conv_self_closing_tags(html_text)
    return html_text


def parse_markdown(markdown_text: str) -> str:
    if not hasattr(window, 'marked'):
        load('https://cdn.jsdelivr.net/npm/marked/marked.min.js')
    html_text: str = window.marked(markdown_text.strip())
    return html_text


mustache_pattern = RegExp.new(r'\{{2,2}.+?\}{2,2}', 'g')


def search_first_mustache(text: str) -> int:
    return String.new(text).search(mustache_pattern)


def find_all_text(text: str) -> List[str]:
    return String.new(text).split(mustache_pattern)


def find_all_mustaches(text: str) -> List[str]:
    return [it.strip('{').strip('}')
            for it in String.new(text).match(mustache_pattern)]


def split_text_nodes(
        text: str) -> List[Tuple[Literal['text', 'mustache'], str]]:
    text = ''.join(line.strip() for line in text.split('\n'))
    fisrt_mustache = search_first_mustache(text)

    if fisrt_mustache == -1:
        return [('text', text)]
    else:
        normal_text = [('text', it)
                       for it in find_all_text(text)]
        mustaches = [('mustache', it)
                     for it in find_all_mustaches(text)]
        if fisrt_mustache == 0:
            zipped = zip_longest(mustaches, normal_text)
        else:
            zipped = zip_longest(normal_text, mustaches)
        return [it for z in zipped for it in z if it is not None]
