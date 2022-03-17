import curses
from time import sleep
import traceback
from typing import Any, Callable
from .tui.console import get_term_size
from .tui.ui import Box, Entry, Interface, ScrollList, get_mid, new_box
from .installer import Wizard

wizard = Wizard()

locales = [v.split('|') for v in wizard.locales().splitlines()]
locales = [{'*': '', "Locale": code, "Name": name} for code, name in locales]
get_locale = lambda: locales
def locale_keyhdl(k: str, sel: int):
    if k == ' ':
        for d in locales:
            d['*'] = ''
        locales[sel]['*'] = '*'
def parse_locale_result():
    for d in locales:
        if d['*']:
            return d['Locale']
    return ''
keymaps = wizard.keymaps()
get_keymap = lambda: keymaps
def keymap_keyhdl(k: str, sel: int):
    if k == ' ':
        for d in keymaps:
            d['*'] = ''
        keymaps[sel]['*'] = '*'
def parse_keymap_result():
    for d in keymaps:
        if d['*']:
            return d['Keymap']
    return ''
lsblk = wizard.strip_lsblk(wizard.tidy_lsblk(wizard.lsblk())[1])
get_lsblk = lambda: lsblk

def scrollList_hdl(ui: Interface, dsFn: Callable[[], list[dict[str, str]]], keyFn: Callable[[str, int], Any], parseFn: Callable[[], str], msg: str) -> str:
    x, y = get_term_size()
    cw, table = ScrollList.build_table(dsFn())
    y, _x = min(table.count('\n'), y), min(cw, x)
    box = Box(ui, y-5, _x, 3, max((x-_x)//2-1, 0))
    listhdl = ScrollList(box)
    ui.draw(msg, "")
    ui.window.refresh()
    listhdl.hdl(dsFn, keyFn)
    res = parseFn()
    while not res:
        Box(ui, 10, 40, *get_mid(y, x, 10, 40)).write('A selection is required!\nPress SPACE to try again.')
        ui.wait(show=False)
        listhdl.hdl(dsFn, keyFn)
        res = parseFn()
    return res

def hostnamehdl(ui: Interface) -> str:
    ui.draw("Configure hostname", '')
    box = new_box(ui, 4, 50)
    en = box.add_entry(48)
    ui.window.refresh()
    box.write()
    while True:
        en.show(1, 1)
        en.activate()
        if en.text:
            return en.text
        box.text = "You can't leave that blank!"
        box.write()
        box.w.getkey()

def add_user(ui: Interface) -> tuple[str, str]:
    global curEn
    ui.draw("Add a user")
    box = new_box(ui, 6, 50)
    box.write('Username: \nPassword: \nRetype: ')
    usernameEn = box.add_entry(38)
    passwordEn = box.add_entry(38)
    retypeEn = box.add_entry(40)
    usernameEn.show(1, 11)
    passwordEn.show(2, 11)
    retypeEn.show(3, 9)
    ens = [usernameEn, passwordEn, retypeEn]
    curEn = ens[0]
    def keyhdl(en: Entry, key: str):
        global curEn
        if key == '\t':
            i = ens.index(en)+1
            curEn = ens[0 if i > 2 else i]
            return 'deactivate'
        if key == '\n':
            curEn = None
            return 'deactivate'
        return ''
    while True:
        if curEn:
            curEn.activate(keyhdl, invisible=curEn!=usernameEn)
            continue
        if not usernameEn.text:
            box = new_box(ui, 4, 38).write("You can't leave your username blank.")
            box.w.getkey()
            curEn = ens[0]
            continue
        if not passwordEn.text:
            box = new_box(ui, 4, 38).write("You can't leave you password blank.")
            box.w.getkey()
            curEn = ens[1]
            continue
        if not retypeEn.text:
            box = new_box(ui, 4, 30).write("Please retype your password.")
            box.w.getkey()
            curEn = ens[2]
            continue
        if passwordEn.text != retypeEn.text:
            box = new_box(ui, 4, 27).write("Password is not the same.")
            box.w.getkey()
            curEn = ens[1]
            continue
        return usernameEn.text, passwordEn.text


def lsblk_hdl(ui: Interface):
    def lsblk_keyhdl(k: str, sel: int):
        if k == ' ':
            global curEn
            box = new_box(ui, 5, 100)
            f = f"mount {lsblk[sel]['name']} "
            box.write(f'{f}\n-o ')
            newMpEn = box.add_entry(100 - len(f) - 2)
            optionEn = box.add_entry(95)
            newMpEn.text = lsblk[sel]['NEW MOUNTPOINT']
            optionEn.text = lsblk[sel]['OPTIONS']
            newMpEn.show(1, 1+len(f))
            optionEn.show(2, 5)
            ens = [newMpEn, optionEn]
            curEn = ens[0]

            def keyhdl(en: Entry, key: str):
                global curEn
                if key == '\t':
                    i = ens.index(en)+1
                    curEn = ens[0 if i > 2 else i]
                    return 'deactivate'
                if key == '\n':
                    curEn = None
                    return 'deactivate'
                return ''
            while True:
                if curEn:
                    curEn.activate(keyhdl)
                    continue
                if not newMpEn.text:
                    box = new_box(ui, 4, 30).write("Please specify a mountpoint.")
                    box.w.getkey()
                    curEn = ens[0]
                    continue
                lsblk[sel]['NEW MOUNTPOINT'] = newMpEn.text
                lsblk[sel]['OPTIONS'] = optionEn.text

    x, y = get_term_size()
    cw, table = ScrollList.build_table(get_lsblk())
    y, _x = min(table.count('\n'), y), min(cw, x)
    box = Box(ui, y-5, _x, 3, max((x-_x)//2-1, 0))
    listhdl = ScrollList(box)
    ui.draw("Set mountpoints", "Press SPACE to set mountpoint and options.\nPress ENTER when you're done.")
    ui.window.refresh()
    listhdl.hdl(get_lsblk, lsblk_keyhdl)
    ds = [d for d in lsblk if d['NEW MOUNTPOINT']]
    has_root = [d for d in ds if d['NEW MOUNTPOINT'] == '/']
    while not any(has_root):
        new_box(ui, 5, 27).write('A selection is required!\nPress SPACE to try again.')
        ui.wait(show=False)
        listhdl.hdl(get_lsblk, lsblk_keyhdl)
        ds = [d for d in lsblk if d['NEW MOUNTPOINT']]
        has_root = [d for d in ds if d['NEW MOUNTPOINT'] == '/']
    return ds


def main(window: 'curses._CursesWindow'):
    ui = Interface(window)

    ui.draw("Welcome to Ultramarine Installer!", "This TUI wizard will guide you through the installation.")
    ui.wait()

    # locales
    locale = scrollList_hdl(ui, get_locale, locale_keyhdl, parse_locale_result, 'Select your locale\npress SPACE to select, and press ENTER to continue.')

    # keyboard layout
    keymap = scrollList_hdl(ui, get_keymap, keymap_keyhdl, parse_keymap_result, 'Select your keymap\npress SPACE to select, and press ENTER to continue.')

    # network/hostname (nmtui)
    wizard.nmtui(ui)
    hostname = hostnamehdl(ui)

    # user
    username, password = add_user(ui)

    # packages

    # disks
    disks = lsblk_hdl(ui)

    # install...


print("Press F11 to open in fullscreen.")
print("You might also need to press and hold Fn alongside.")
input("Press ENTER to get to the next screen.")


curses.wrapper(main)
# try:
#     curses.wrapper(main)
# except Exception as err:
#     traceback.print_exc()
# finally:
#     input('Press ENTER to exit')
