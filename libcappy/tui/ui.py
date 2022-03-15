import atexit
import os
import curses
from time import sleep
from .keyhdl import keys, syek
from .pyTableMaker import CustomTable


class Interface:
    def __init__(self):
        atexit.register(self.end)
        self.c = os.get_terminal_size().columns
        self.l = os.get_terminal_size().lines
        self.window = curses.initscr()
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        self.window.keypad(True)

    def mid(self, text: str) -> str:
        return (
            " " * int((self.c - len(text)) / 2)
            + text
            # + " " * int((self.c - len(text)) / 2)
        )

    def draw(self, title: str, desc: str, wait_for: str = 'SPACE'):
        self.window.clear()
        self.window.addstr('\n' + self.mid(title) + '\n\n')
        for line in desc.split('\n'):
            self.window.addstr("  " + line)

    def wait(self, wait_for: str = 'SPACE'):
        self.window.addstr(self.l - 2, 0, self.mid(f"--- Press {wait_for} to continue ---"))
        while self.window.getkey() != keys[wait_for]:
            pass

    def end(self):
        curses.nocbreak()
        self.window.keypad(False)
        curses.echo()
        curses.endwin()
        print("UI: Program exited.")


class ListHdl:
    selectables: list[str] = []

    def __init__(self, ui: Interface):
        self.ui = ui
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLUE)
        # self.w = curses.newwin(5, 5)

    def build_table(self, ds: list[dict[str, str]]):
        t = CustomTable(["▄", "▄", "▄", "▄", "▄", "▄", "▄", "▄", "╚", "═", "╝", "╩", " "])
        [t.add_col(f) for f in ds[0].keys()]
        for d in ds:
            t.insert(*(v for v in d.values()))
        return t.get()

    def print_table(self, text: str, sel: int = -1):
        w = self.ui.window
        rows = text.splitlines()
        w.addstr(rows.pop(0) + "\n", curses.color_pair(2))
        w.addstr(rows.pop(0) + "\n", curses.color_pair(1))
        w.addstr(rows.pop(0) + '\n', curses.color_pair(1 if sel else 5))
        i = 0
        while len(rows) > 2:
            if sel == i:
                w.addstr(rows.pop(0) + '\n', curses.color_pair(4))
                w.addstr(rows.pop(0) + '\n', curses.color_pair(4))
            else:
                w.addstr(rows.pop(0) + '\n')
                if sel == i + 1:
                    w.addstr(rows.pop(0) + '\n', curses.color_pair(3))
                else:
                    w.addstr(rows.pop(0).replace('▄', ' ') + '\n')
            i += 1

    def hdl(self, table: list[dict[str, str]]):
        w = self.ui.window
        w.refresh()
        w.clear()
        w.addstr(4, 0, '')
        text = self.build_table(table)
        for i, row in enumerate(text.splitlines()):
            if i % 2 == 1 and i > 1:
                self.selectables.append(row)
            w.addstr(row + "\n")
        w.refresh()
        w.clear()
        self.print_table(text, 0)
        w.refresh()
        sel = 0
        while True:
            old = sel
            match syek[w.getkey()]:
                case 'UP':
                    sel -= 1
                case 'DOWN':
                    sel += 1
                case 'ENTER':
                    break
                case _: continue
            if old == sel:
                continue
            if sel == len(self.selectables) - 1:
                sel = 0
            if sel == -1:
                sel = len(self.selectables) - 2
            w.clear()
            self.print_table(text, sel)
            w.refresh()


class Box:
    def __init__(self, ui: Interface, height, width, y, x):
        self.w = ui.window.subwin(height, width, y, x)
        self.w.refresh()
        self.w.addstr('╔' + '═'*(width-3) + '╗\n')
        for _ in range(height-3):
            self.w.addstr('║' + ' '*(width-3) + '║\n')
        self.w.addstr('╚' + '═'*(width-3) + '╝\n')
        self.w.refresh()


class Entry:
    def __init__(self, container: Box, text: str, length: int):
        self.text = text
        self.length = length
        self.contain = container
    
    # def activate(self):
    #     while True:



def get_mid(y: int, x: int, height: int, width: int) -> tuple[int, int]:
    return (y-height)//2-1, (x-width)//2-1


