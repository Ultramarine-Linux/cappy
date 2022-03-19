import curses
from typing import Any, Callable, Optional

from .common import DS


class Interface:
    def __init__(self, w: 'curses._CursesWindow'):
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        w.keypad(True)
        self.w = w

    def mid(self, text: str) -> str:
        return " " * int((self.w.getmaxyx()[1] - len(text)) / 2) + text

    def draw(self, title: str, desc: str = ''):
        self.title = title
        self.desc = desc
        self.w.clear()
        self.w.move(0, 0)
        [self.w.addstr('\n' + self.mid(l)) for l in title.splitlines()]
        self.w.addstr('\n')
        [self.w.addstr('\n  ' + l) for l in desc.splitlines()]
        self.w.refresh()

    def wait(self, show: bool = True):
        if show:
            self.w.addstr(self.w.getmaxyx()[0] - 2, 0, self.mid(f"--- Press SPACE to continue ---"))
        while self.w.getkey() != ' ':
            pass

    def redraw(self):
        y, x = self.w.getmaxyx()
        self.w.addstr(0, 0, ' '*(x*y-1))
        self.draw(self.title, self.desc)
        self.w.refresh()


class Box:
    t: str = ""

    def __init__(self, ui: Interface, h: int, w: int, y: int, x: int):
        curses.update_lines_cols()
        self.l = h
        self.c = w
        self.w = mkwin(ui.w, h, w, y, x)
        self.ui = ui
        self.w.keypad(True)

    def write(self, text: str = '', attr: int = 0):
        self.t += text
        self.w.addstr(0, 0, '╔' + '═'*(self.c-2) + '╗')
        rows: list[str] = []
        for row in self.t.splitlines():
            rows.extend(splitstr(row, self.c-2))
        i = 1
        while i < self.l-2:
            row = rows.pop(0) if any(rows) else ''
            self.w.addstr("║" + row + ' '*(self.c-2-len(row)) + '║', attr)
            i += 1
        self.w.addstr('╚' + '═'*(self.c-2) + '╝')
        return self

    def add_entry(self, length: int):
        return Entry(self, length)

    def resize(self, h: int, w: int):
        self.l = h
        self.c = w
        self.w.resize(h, w)
        self.write()


class Toggle:
    def __init__(self, box: Box):
        self.box = box
        curses.start_color()
        curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_MAGENTA)

    def show(self, y: int, x: int, default: bool = False):
        self.box.w.addstr(y, x, '🗹' if default else '🗷')
        self.pos = y, x
        self.state = default

    def activate(self, keyhdl: Optional[Callable[['Toggle', str], str]] = None):
        curses.curs_set(1)
        while True:
            y, x = self.pos
            self.box.w.move(y, x+1)
            k = self.box.w.getkey()
            if keyhdl:
                if (ret := keyhdl(self, k)) == 'deactivate':
                    break
                if ret:
                    continue
            match k:
                case '\x1b': break
                case '\n': break
                case 'KEY_ENTER': break
                case ' ': self.show(*self.pos, not self.state)
                case _: pass


class Entry:
    t = ''
    invis = False

    def __init__(self, box: Box, length: int):
        curses.update_lines_cols()
        self.length = length
        self.box = box
        curses.start_color()
        curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
        box.w.keypad(True)

    def show(self, y: int = -1, x: int = -1):
        if y == -1:
            y = self.p[0]
        if x == -1:
            x = self.p[1]
        self.box.w.addstr(y, x, ('*'*len(self.t) if self.invis else self.t) + ' '*(self.length-len(self.t)), curses.color_pair(11))
        self.p = y, x

    def activate(self, keyhdl: Optional[Callable[['Entry', str], str]] = None, invis: bool = False):
        curses.curs_set(1)
        tp = len(self.t)
        self.invis = invis
        y, x = self.p
        self.box.w.move(y, x)
        while True:
            k = self.box.w.getkey()
            if keyhdl:
                ret = keyhdl(self, k)
                if ret == 'deactivate':
                    break
                if ret:
                    continue
            match k:
                case '\n': break
                case 'KEY_ENTER': break
                case '\t': continue
                case 'KEY_LEFT': tp = max(tp - 1, 0)
                case 'KEY_RIGHT': tp = min(tp + 1, len(self.t))
                case 'KEY_BACKSPACE':
                    if tp == 0:
                        continue
                    self.t = self.t[:tp-1] + self.t[tp:]
                    tp -= 1
                case '\x7f':
                    if tp == 0:
                        continue
                    self.t = self.t[:tp-1] + self.t[tp:]
                    tp -= 1
                case 'KEY_DC':
                    if tp == len(self.t):
                        continue
                    self.t = self.t[:tp] + self.t[tp+1:]
                case _:
                    if len(k) > 1:
                        continue
                    if len(self.t) == self.length:
                        continue
                    self.t = self.t[:tp] + k + self.t[tp:]
                    tp += 1
            self.box.w.addstr(*self.p, ('*'*len(self.t) if invis else self.t) + ' '*(self.length-len(self.t)), curses.color_pair(11))
            self.box.w.move(y, x+tp)
            self.box.w.refresh()
        curses.curs_set(0)


class ScrollList:
    sels: list[str] = []

    def __init__(self, box: Box):
        curses.update_lines_cols()
        self.box = box
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLUE)

    @staticmethod
    def build_table(ds: DS):
        cols = list(ds[0].keys())
        cw = [max(len(cols[n]), [max(len(d[cols[n]])for d in ds)for n in range(len(cols))][n])for n in range(len(cols))]
        rows = [[d[col]for col in cols]for d in ds]
        f = "│".join(col+' '*(cw[i]-len(col))for i, col in enumerate(cols))+'\n'
        return sum(cw)+len(cols)-3, f+"\n".join("│".join(v+' '*(cw[i]-len(v))for i, v in enumerate(r))for r in rows)

    def write(self, ls: list[str], sel: int = 0):
        w = self.box.w
        y = 1
        w.addstr(y, 1, ls.pop(0)[0:self.box.c-2], curses.color_pair(1))
        while any(ls):
            y += 1
            w.addstr(y, 1, ls.pop(0), curses.color_pair(2 if y-2 == sel else 0))
        w.refresh()

    def find(self, ds: DS, sel: int) -> int:
        curses.update_lines_cols()
        box = Box(self.box.ui, 4, 50, *get_mid(*self.box.ui.w.getmaxyx(), 4, 50))
        box.write("FIND: ")
        en = box.add_entry(42)
        en.show(1, 7)
        en.activate()
        found: list[int] = []
        for i, d in enumerate(ds):
            for v in d.values():
                if en.t in v:
                    if i > sel:
                        return i
                    found.append(i)
        if any(found):
            return found[0]
        else:
            box.t = "Not found!"
            box.write()
            box.w.getkey()
            return sel

    def hdl(self, dsFn: Callable[[], DS], keyFn: Callable[[str, int], Any], h: Optional[int] = 0, w: Optional[int] = 0):
        """This includes showing it. No you can't sep them."""
        self.box.ui.redraw()
        self.box.write()
        h = h or self.box.l - 2
        w = w or self.box.c - 2
        ds = dsFn()
        cw, table = self.build_table(ds)
        ls = table.splitlines()
        self.sels = ls[1:]
        sy: int = 0
        sx: int = 0
        self.write([l[sx:sx+w] for l in ls[sy:sy+h-1]])
        sel = 0
        while True:
            k = self.box.w.getkey()
            match k:
                case 'KEY_PPAGE': sel -= h - 3
                case 'KEY_NPAGE': sel += h - 3
                case 'KEY_HOME': sx = 0
                case 'KEY_END': sx = cw-w+2
                case 'KEY_UP': sel -= 1
                case 'KEY_DOWN': sel += 1
                case 'KEY_LEFT': sx -= 1
                case 'KEY_RIGHT': sx += 1
                case '\n': return
                case '\x06': sel = self.find(ds, sel)
                case _: keyFn(k, sel)
            if sel >= len(self.sels):
                sel = 0
            if sel < 0:
                sel = len(self.sels)-1
            if sy + h - 3 < sel:
                sy = sel - h + 3
            if sy > sel:
                sy = sel
            if sx > cw-w+2:
                sx = 0
            if sx < 0:
                sx = cw-w+2
            ds = dsFn()
            cw, table = self.build_table(ds)
            ls = table.splitlines()
            self.sels = ls[1:]
            self.box.ui.redraw()
            self.box.write()
            self.write([ls[0][sx:sx+w]] + [l[sx:sx+w] for l in ls[sy+1:sy+h-1]], sel-sy)


def get_mid(y: int, x: int, h: int, w: int) -> tuple[int, int]:
    return max((y-h)//2-1, 0), max((x-w)//2-1, 0)


def new_box(ui: Interface, h: int, w: int):
    return Box(ui, h, w, *get_mid(*ui.w.getmaxyx(), h, w))


def splitstr(s: str, n: int):
    return [s[i:i + n] for i in range(0, len(s), n)]

def mkwin(win: 'curses._CursesWindow', h: int, w: int, y: int, x: int):
    try:
        return win.subwin(h, w, y, x)
    except BaseException as err:
        curses.endwin()
        if type(err).__name__ == 'error':  # _curses.error
            if str(err) == 'curses function returned NULL':
                term_size = win.getmaxyx()
                raise ValueError(f"Failed to create window:\n{h, w, y, x=}\nMaybe {term_size=} is too small?") from err
        raise

def popup(ui: Interface, s: str):
    h = len(s.splitlines()) + 3
    w = max(len(l) for l in s.splitlines()) + 2
    new_box(ui, h, w).write(s).w.getkey()
