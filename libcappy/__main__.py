import subprocess
import curses
import multiprocessing as mp
from typing import Any, Callable

from .install import install
from .tui.console import get_term_size
from .tui.ui import Box, Entry, Interface, ScrollList, Toggle, get_mid, new_box
from .installer import Wizard
import contextlib
import sys
import yaml
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('-c', '--chroot', type=str, help="Set custom chroot", default='/mnt', dest='chroot')
ap.add_argument('-d', '--skip-disk', action='store_true', help='Skip disk selection', dest='sd')
args = ap.parse_args()
chroot = args.chroot
skipdisk = args.sd

class DummyFile(object):
    def write(self, _: Any): pass


def th_envs_grps(q: 'mp.Queue[tuple[list[dict[str, str]], list[dict[str, str]]]]'):
    save_stdout = sys.stdout
    sys.stdout = DummyFile()
    q.put(Wizard().fetch_envs_grps())
    sys.stdout = save_stdout


q: 'mp.Queue[tuple[list[dict[str, str]], list[dict[str, str]]]]' = mp.Queue()
p = mp.Process(target=th_envs_grps, args=(q, ))
p.start()


wizard = Wizard()

locales = [v.split('|') for v in wizard.locales().splitlines()]
locales = [{'*': '', "Locale": code, "Name": name} for code, name in locales]
keymaps = wizard.keymaps()


def gen_scrollList_hdl(ds: list[dict[str, str]], retName: str, multisel: bool = False):
    def getFn(): return ds

    def keyhdl(k: str, sel: int):
        if k == ' ':
            if multisel:
                ds[sel]['*'] = '' if ds[sel]['*'] else '*'
                return
            for d in ds:
                d['*'] = ''
            ds[sel]['*'] = '*'

    def parse():
        if multisel:
            return [d[retName] for d in ds if d['*']]
        for d in ds:
            if d['*']:
                return d[retName]
        return ''
    return getFn, keyhdl, parse


lsblk = wizard.strip_lsblk(wizard.tidy_lsblk(wizard.lsblk())[1])
def get_lsblk(): return lsblk


def scrollList_hdl(ui: Interface, dsFn: Callable[[], list[dict[str, str]]], keyFn: Callable[[str, int], None], parseFn: Callable[[], str | list[str]], msg: str):
    y, x = ui.window.getmaxyx()
    cw, table = ScrollList.build_table(dsFn())
    y, _x = min(table.count('\n'), y), min(cw, x)
    box = Box(ui, y-5, _x, 3, max((x-_x)//2-1, 0))
    listhdl = ScrollList(box)
    ui.draw(msg, "")
    ui.window.refresh()
    listhdl.hdl(dsFn, keyFn)
    res = parseFn()
    while not any(res):
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
            curEn.activate(keyhdl, invisible=curEn != usernameEn)
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
            box = new_box(ui, 7, 100)
            f = f"mount {lsblk[sel]['name']} "
            box.write(f'{f}\n-o \ndump: \nfsck: ')
            newMpEn = box.add_entry(100 - len(f) - 2)
            optionEn = box.add_entry(95)
            newMpEn.text = lsblk[sel]['NEW MOUNTPOINT']
            optionEn.text = lsblk[sel]['OPTIONS']
            newMpEn.show(1, 1+len(f))
            optionEn.show(2, 5)
            dumpCh = Toggle(box)
            fsckCh = Toggle(box)
            dumpCh.show(3, 7)
            fsckCh.show(4, 7)
            ens = [newMpEn, optionEn, dumpCh, fsckCh]
            curEn = ens[0]

            def keyhdl(en: Entry | Toggle, key: str):
                global curEn
                if key == '\t':
                    i = ens.index(en)+1
                    curEn = ens[0 if i > 4 else i]
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
                lsblk[sel]['FSCK'] = '*' if fsckCh.state else ''
                lsblk[sel]['DUMP'] = '*' if dumpCh.state else ''

    x, y = get_term_size()
    cw, table = ScrollList.build_table(get_lsblk())
    y, _x = min(table.count('\n'), y), min(cw, x)
    box = Box(ui, y-5, _x, 3, max((x-_x)//2-1, 0))
    listhdl = ScrollList(box)
    ui.draw("Set mountpoints", f"Press SPACE to set mountpoint and options.\nPress ENTER when you're done.\n(it starts with {chroot})")
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

    locale = scrollList_hdl(ui, *gen_scrollList_hdl(locales, 'Locale'), 'Select your locale\npress SPACE to select, and press ENTER to continue.')
    keymap = scrollList_hdl(ui, *gen_scrollList_hdl(keymaps, 'Keymap'), 'Select your keymap\npress SPACE to select, and press ENTER to continue.')
    wizard.nmtui(ui)
    hostname = hostnamehdl(ui)
    username, password = add_user(ui)
    disks = [] if skipdisk else lsblk_hdl(ui)
    ui.draw("Waiting for dnf to finish...", "This will take a while!")
    ui.window.refresh()
    envirns, agroups = q.get()
    envirn = scrollList_hdl(ui, *gen_scrollList_hdl(envirns, 'NAME'), 'Select your environment\npress SPACE to select, and press ENTER to continue.')
    groups = scrollList_hdl(ui, *gen_scrollList_hdl(agroups, 'NAME', True), 'Select your groups\npress SPACE to select, and press ENTER to continue. (You may select multiple ones.)')
    bootloader = scrollList_hdl(ui, *gen_scrollList_hdl([{'NAME': 'grub'}, {'NAME': 'systemd-boot'}], 'NAME'), 'Select your bootloader\npress SPACE to select, and press ENTER to continue.')

    ui.draw("Generating and saving configurations...")
    ui.window.refresh()
    d = {
        "install": {
            "installroot": chroot,
            "volumes": [{'uuid': disk['UUID'], 'mountpoint': disk['NEW MOUNTPOINT'], 'filesystem': disk['FSTYPE'], 'dump': bool(disk['DUMP']), 'fsck': bool(disk['FSCK'])} for disk in disks],
            "packages": ([f"@^{envirn}"] if envirn else []) + [f"@{g}" for g in groups] + ['@core', 'nano', 'dnf', 'kernel', 'grub2-efi-x64', 'shim', 'grub2-tools-efi', 'grub2-pc'],
            "dnf_options": {
                "install_weak_deps": True,
                "releasever": 36,
                "user_agent": 'libcappy-libdnf/0.1',
                "exclude": 'fedora-release-common'
            },
            "postinstall": [
                f'localectl set-locale {locale}',
                f'localectl set-keymap {keymap}',
                f'hostnamectl hostname {hostname}',
                f'useradd {username} -p $(mkpasswd {password}) -m'
            ],
            "bootloader": bootloader
        }
    }
    yaml.dump(d, open('/tmp/cappyinstall.yml', 'w+'))
    
    ui.draw("You will see your Cappy configuration file", "If you want to edit anything, just edit it.\nWhen you finish reviewing the file, press CTRL+X, Y, then ENTER to save the file.")
    ui.wait()


print("Press F11 to open in fullscreen.")
print("You might also need to press and hold Fn alongside.")
input("Press ENTER to get to the next screen.")


curses.wrapper(main)
subprocess.run('nano /tmp/cappyinstall.yml')
if input("You've reached the end of the wizard. Ready to install? [y/N]") in 'Yy':
    print("!! THIS WILL ERASE YOUR DATA IF NOT CONFIGURED PROPERLY!!")
    if input("Still continue? [yes]") == 'yes':
        install()
