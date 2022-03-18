import atexit
import os
import curses
from typing import Any, Optional, Callable

from .console import get_term_size
from .keyhdl import keys

os.environ.setdefault('ESCDELAY', '10')

class Interface:
    def __init__(self, window: 'curses._CursesWindow'):
        atexit.register(self.end)
        self.c = os.get_terminal_size().columns
        self.l = os.get_terminal_size().lines
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        self.window = window
        self.window.keypad(True)

    def mid(self, text: str) -> str:
        return (
            " " * int((os.get_terminal_size().columns - len(text)) / 2)
            + text
            # + " " * int((self.c - len(text)) / 2)
        )

    def draw(self, title: str, desc: str = ''):
        self.title = title
        self.desc = desc
        self.window.clear()
        self.window.move(0, 0)
        for line in title.splitlines():
            self.window.addstr('\n' + self.mid(line))
        self.window.addstr('\n')
        for line in desc.splitlines():
            self.window.addstr("\n  " + line)
        self.window.refresh()

    def wait(self, wait_for: str = 'SPACE', show: bool = True):
        if show:
            self.window.addstr(self.l - 2, 0, self.mid(f"--- Press {wait_for} to continue ---"))
        while self.window.getkey() != keys[wait_for]:
            pass

    def redraw(self):
        x, y = get_term_size()
        self.window.addstr(0, 0, ' '*(x*y-1))
        self.draw(self.title, self.desc)
        self.window.refresh()

    def end(self):
        return
        curses.nocbreak()
        self.window.keypad(False)
        curses.echo()
        curses.endwin()
        print("UI: Program exited.")


class Box:
    text: str = ""
    def __init__(self, ui: Interface, height: int, width: int, y: int, x: int):
        self.height = height
        self.width = width
        self.w = ui.window.subwin(height, width, y, x)
        self.ui = ui
        self.w.keypad(True)

    def write(self, text: str = '', attr: int = 0):
        self.text += text
        self.w.addstr(0, 0, '╔' + '═'*(self.width-2) + '╗')
        rows: list[str] = []
        for row in self.text.splitlines():
            rows.extend(splitstr(row, self.width-2))
        row = rows.pop(0) if any(rows) else ''
        self.w.addstr('║' + row + ' '*(self.width-2-len(row)) + '║', attr)
        i = 2
        while i < self.height-2:
            row = rows.pop(0) if any(rows) else ''
            self.w.addstr("║" + row + ' '*(self.width-2-len(row)) + '║', attr)
            i += 1
        self.w.addstr('╚' + '═'*(self.width-2) + '╝')
        return self

    def add_entry(self, length: int):
        return Entry(self, length)
    
    def resize(self, h: int, w: int):
        self.height = h
        self.width = w
        self.w.resize(h, w)
        self.write()


class Toggle:
    def __init__(self, container: Box):
        self.contain = container
        curses.start_color()
        curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
    
    def show(self, y: int, x: int, default: bool = False):
        self.contain.w.addstr(y, x, '🗹' if default else '🗷')
        self.pos = y, x
        self.state = default

    def activate(self, keyhdl: Optional[Callable[['Toggle', str], str]] = None):
        curses.curs_set(1)
        while True:
            y, x = self.pos
            self.contain.w.move(y, x+1)
            key = self.contain.w.getkey()
            if keyhdl:
                ret = keyhdl(self, key)
                if ret == 'deactivate': break
                if ret: continue
            match key:
                case '\x1b': break
                case '\n': break
                case 'KEY_ENTER': break
                case ' ': self.show(*self.pos, not self.state)
                case _: pass

class Entry:
    text = ''
    invisible = False
    def __init__(self, container: Box, length: int):
        self.length = length
        self.contain = container
        curses.start_color()
        curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
        container.w.keypad(True)

    def show(self, y: int = -1, x: int = -1):
        if y == -1: y = self.pos[0]
        if x == -1: x = self.pos[1]
        self.contain.w.addstr(y, x, ('*'*len(self.text) if self.invisible else self.text) + ' '*(self.length-len(self.text)), curses.color_pair(11))
        self.pos = y, x

    def activate(self, keyhdl: Optional[Callable[['Entry', str], str]] = None, invisible: bool = False):
        curses.curs_set(1)
        tpos = len(self.text)
        self.invisible = invisible
        y, x = self.pos
        self.contain.w.move(y, x)
        while True:
            key = self.contain.w.getkey()
            if keyhdl:
                ret = keyhdl(self, key)
                if ret == 'deactivate':
                    break
                if ret:
                    continue
            match key:
                case '\n':
                    break
                case 'KEY_ENTER':
                    break
                case 'KEY_LEFT':
                    tpos = max(tpos - 1, 0)
                case 'KEY_RIGHT':
                    tpos = min(tpos + 1, len(self.text))
                case 'KEY_BACKSPACE':
                    if tpos == 0:
                        continue
                    self.text = self.text[:tpos-1] + self.text[tpos:]
                    tpos -= 1
                case '\x7f':
                    if tpos == 0:
                        continue
                    self.text = self.text[:tpos-1] + self.text[tpos:]
                    tpos -= 1
                case 'KEY_DC':
                    if tpos == len(self.text):
                        continue
                    self.text = self.text[:tpos] + self.text[tpos+1:]
                case _:
                    if len(key) > 1:
                        continue
                    if len(self.text) == self.length:
                        continue
                    self.text = self.text[:tpos] + key + self.text[tpos:]
                    tpos += 1
            if invisible:
                self.contain.w.addstr(*self.pos, '*'*len(self.text) + ' '*(self.length-len(self.text)), curses.color_pair(11))
            else:
                self.contain.w.addstr(*self.pos, self.text + ' '*(self.length-len(self.text)), curses.color_pair(11))
            self.contain.w.move(y, x+tpos)
            self.contain.w.refresh()
        curses.curs_set(0)


class ScrollList:
    sels: list[str] = []

    def __init__(self, box: Box):
        self.box = box
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLUE)

    @staticmethod
    def build_table(ds: list[dict[str, str]]):
        cols = list(ds[0].keys())
        cw = [max(len(cols[n]), [max(len(d[cols[n]])for d in ds)for n in range(len(cols))][n])for n in range(len(cols))]
        rows = [[d[col]for col in cols]for d in ds]
        f = "│".join(col+' '*(cw[i]-len(col))for i, col in enumerate(cols))+'\n'
        return sum(cw)+len(cols)-3, f+"\n".join("│".join(v+' '*(cw[i]-len(v))for i, v in enumerate(r))for r in rows)

    def write(self, ls: list[str], sel: int = 0):
        a = self.box.w.addstr
        y = 1
        a(y, 1, ls.pop(0)[0:self.box.width-2], curses.color_pair(1))
        while any(ls):
            y += 1
            if y - 2 == sel:
                a(y, 1, ls.pop(0), curses.color_pair(2))
            else:
                a(y, 1, ls.pop(0))
        self.box.w.refresh()        

    def find(self, ds: list[dict[str, str]], sel: int) -> int:
        x, y = get_term_size()
        box = Box(self.box.ui, 4, 50, *get_mid(y, x, 4, 50))
        box.write("FIND: ")
        en = box.add_entry(42)
        en.show(1, 7)
        en.activate()
        found: list[int] = []
        for i, d in enumerate(ds):
            for v in d.values():
                if en.text in v:
                    if i <= sel:
                        found.append(i)
                        continue
                    return i
        if any(found):
            del box
            return found[0]
        else:
            box.text = "Can't find that one!"
            box.write()
            box.w.getkey()
            return sel

    def hdl(self, dsFn: Callable[[], list[dict[str, str]]], keyFn: Callable[[str, int], Any], h: Optional[int] = 0, w: Optional[int] = 0):
        """This includes showing it. No you can't sep them."""
        self.box.ui.redraw()
        self.box.write()
        h = h or self.box.height - 2
        w = w or self.box.width - 2
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
                # case '\x1b': return  # ESC
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


# while True:
#     w = curses.initscr()
#     w.keypad(True)
#     print([w.getkey()])


def get_mid(y: int, x: int, height: int, width: int) -> tuple[int, int]:
    return max((y-height)//2-1, 0), max((x-width)//2-1, 0)

def new_box(ui: Interface, h: int, w: int):
    x, y = get_term_size()
    return Box(ui, h, w, *get_mid(y, x, h, w))

def splitstr(s: str, n: int):
    return [s[i:i + n] for i in range(0, len(s), n)]
