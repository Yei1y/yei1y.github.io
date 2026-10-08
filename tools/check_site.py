"""Static checks for the personal site pages.

Run from the repository root:

    python tools/check_site.py .

Checks, per page:
  1. element tag balance / nesting
  2. every container that labels in one language also labels in the other
     (bilingual pairing, container level; `name-flag` badges are exempt)
  3. no leftover inline *colour* styles (inline widths/offsets are data, allowed)
  4. local href/src targets exist
  5. no stale strings from earlier drafts
  6. figure files referenced by the pages are present and not absurdly large

Exit code 0 when everything passes, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr', 'path', 'line', 'rect',
        'circle', 'text', 'use', 'polyline', 'polygon'}

STALE = [
    ('按含金量 × 完成度 × 岗位匹配度排序', 'old ranking heading'),
    ('下面 6 个是主干项目', 'old meta commentary'),
    ('方法论严密度担当', 'resume-internal wording'),
    ('这个项目证明的不只是', 'meta self-commentary'),
    ('hero-curve', 'removed decorative svg'),
    ('class="swatch"', 'removed footer swatch'),
    ('<span class="given">', 'removed two-tone name'),
    ('25tjjm', 'stale repo slug'),
    ('26tjjm', 'stale repo slug'),
    ('localhost', 'local URL left in page'),
]

MAX_FIGURE_KB = 400


class Tree(HTMLParser):
    """Minimal parent/child tree with line numbers and class lists."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = {'tag': '#root', 'line': 0, 'classes': set(), 'children': [],
                     'text': '', 'style': '', 'attrs': {}}
        self.cur = self.root
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        node = {'tag': tag, 'line': self.getpos()[0],
                'classes': set((d.get('class') or '').split()),
                'children': [], 'text': '', 'style': d.get('style', ''), 'attrs': d}
        self.cur['children'].append(node)
        if tag not in VOID:
            node['parent'] = self.cur
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        node = self.cur
        if node is self.root or node['tag'] != tag:
            self.errors.append(f'line {self.getpos()[0]}: </{tag}> does not match '
                               f'<{node["tag"]}> opened at line {node["line"]}')
            return
        self.cur = node['parent']

    def handle_data(self, data):
        self.cur['text'] += data

    def finish(self):
        if self.cur is not self.root:
            self.errors.append(f'unclosed <{self.cur["tag"]}> opened at line {self.cur["line"]}')
        return self.root


def walk(node):
    yield node
    for c in node['children']:
        yield from walk(c)


def check_pairing(root):
    def labelled(node, side):
        return [k for k in node['children']
                if side in k['classes'] and 'name-flag' not in k['classes']]

    problems = []
    for node in walk(root):
        zh_kids, en_kids = labelled(node, 'zh'), labelled(node, 'en')
        if bool(zh_kids) == bool(en_kids):
            continue
        if zh_kids:
            problems.append((node['line'], node['tag'], 'zh only',
                             ''.join(k['text'] for k in zh_kids)[:34]))
        else:
            problems.append((node['line'], node['tag'], 'en only',
                             ''.join(k['text'] for k in en_kids)[:34]))
    return problems


def check_inline_colour(root):
    return [(n['line'], n['tag'], n['style'][:70])
            for n in walk(root)
            if n['style'] and ('color' in n['style'] or 'background' in n['style'])]


def check_assets(text, page, root):
    problems, figures = [], []
    for m in re.finditer(r'(?:href|src|data-zoom)="([^"]+)"', text):
        url = m.group(1)
        if url.startswith(('http', 'mailto:', 'data:', '#')):
            continue
        target = (page.parent / url.split('#')[0]).resolve()
        if not target.exists():
            problems.append(f'missing asset: {url}')
        elif '/figures/' in url.replace('\\', '/'):
            figures.append(target)
    return problems, sorted(set(figures))


def check_image_dims(text, root, page):
    """width/height attributes must match the real file, or the page will jump."""
    problems = []
    for m in re.finditer(r'<img\s+src="([^"]+)"[^>]*?width="(\d+)"\s+height="(\d+)"', text):
        url, w, h = m.group(1), int(m.group(2)), int(m.group(3))
        f = (page.parent / url).resolve()
        if not f.exists():
            continue
        try:
            from PIL import Image
            with Image.open(f) as im:
                rw, rh = im.size
        except Exception:
            continue
        if (rw, rh) != (w, h):
            problems.append(f'{url}: page says {w}x{h}, file is {rw}x{rh}')
    return problems


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    pages = [root / 'index.html', root / 'projects' / 'index.html']
    ok = True

    for page in pages:
        if not page.exists():
            print(f'[X] missing page: {page}')
            ok = False
            continue
        text = page.read_text(encoding='utf-8')
        print(f'\n=== {page.relative_to(root)}  ({len(text.splitlines())} lines) ===')

        t = Tree()
        t.feed(text)
        tree = t.finish()
        if t.errors:
            ok = False
            print('  [X] structure:')
            for e in t.errors[:12]:
                print('     ', e)
        else:
            print('  [OK] tag balance / nesting')

        pair = check_pairing(tree)
        if pair:
            ok = False
            print(f'  [X] bilingual pairing ({len(pair)} container(s)):')
            for line, tag, side, sample in pair[:20]:
                print(f'      line {line:>4} <{tag}> {side}: {sample}')
        else:
            print('  [OK] bilingual pairing (container level)')

        ic = check_inline_colour(tree)
        if ic:
            ok = False
            print('  [X] leftover inline colour:')
            for line, tag, s in ic[:10]:
                print(f'      line {line} <{tag}> style="{s}"')
        else:
            print('  [OK] no inline colour styles')

        assets, figures = check_assets(text, page, root)
        if assets:
            ok = False
            print('  [X] assets:')
            for a in assets:
                print('     ', a)
        else:
            print('  [OK] local assets resolve')

        dims = check_image_dims(text, root, page)
        if dims:
            ok = False
            print('  [X] image dimensions out of sync:')
            for d in dims:
                print('     ', d)
        else:
            print('  [OK] image dimensions match files')

        for f in figures:
            kb = f.stat().st_size / 1024
            if kb > MAX_FIGURE_KB:
                ok = False
                print(f'  [X] figure too heavy: {f.name} {kb:.0f} KB > {MAX_FIGURE_KB} KB')
        if figures:
            print(f'  [OK] {len(figures)} figure file(s), largest '
                  f'{max(f.stat().st_size for f in figures) / 1024:.0f} KB')

        hits = [f'{label}: "{s}"' for s, label in STALE if s in text]
        if hits:
            ok = False
            print('  [X] stale content:')
            for h in hits:
                print('     ', h)
        else:
            print('  [OK] no stale content')

        zh = len(re.findall(r'class="zh"', text))
        en = len(re.findall(r'class="en"', text))
        if zh != en:
            ok = False
        print(f'  [{"OK" if zh == en else "MISMATCH"}] .zh spans {zh} / .en spans {en}')

    css_path = root / 'assets' / 'css' / 'style.css'
    css = css_path.read_text(encoding='utf-8')
    print(f'\n=== assets/css/style.css ({len(css.splitlines())} lines) ===')
    required = ['--acc-tint', '.stats', '.bars', '.funnel', '.fml', '.box',
                '.fig', '.metric .num', '.media', '.viewer']
    for token in required:
        if token not in css:
            ok = False
            print(f'  [X] missing rule: {token}')
    if 'hero-curve' in css:
        ok = False
        print('  [X] hero-curve rules still present')
    if not [t for t in required if t not in css]:
        print('  [OK] component rules present')

    print('\nRESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
