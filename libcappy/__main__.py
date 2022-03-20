import argparse
import curses
import multiprocessing as mp
import os
import re
import sys
from typing import Any, Callable

import yaml

from .common import DS, Q_T
from .install import install
from .installer import Wizard
from .ui import Box, Entry, Interface, ScrollList, Toggle, get_mid, new_box, popup

ap = argparse.ArgumentParser()
ap.add_argument('-c', '--chroot', type=str, help="Set custom chroot (must ends with /)", default='/mnt', dest='chroot')
ap.add_argument('-d', '--skip-disk', action='store_true', help='Skip disk selection', dest='sd')
ap.add_argument('-t', '--timeout', type=float, help="Set network timeout in seconds", default=10, dest='timeout')
ap.add_argument('-w', '--skip-wizard', action='store_true', help='Skip the wizard. You need to have /tmp/cappyinstall.yml', dest='sw')
args = ap.parse_args()
chroot:str = args.chroot
skipdisk = args.sd
timeout = args.timeout
skipwizard = args.sw


class DummyFile(object):
    def write(self, _: Any): pass


def th_envs_grps(q: Q_T):
    save_stdout = sys.stdout
    sys.stdout = DummyFile()
    q.put(Wizard.fetch_envs_grps())
    sys.stdout = save_stdout


q: Q_T = mp.Queue()
p = mp.Process(target=th_envs_grps, args=(q, ))


wizard = Wizard()

locales = [v.split('|') for v in wizard.locales().splitlines()]
locales = [{'*': '', "Locale": code, "Name": name} for code, name in locales]
keymaps = wizard.keymaps()


def gen_scrollList_hdl(ds: DS, retName: str, multisel: bool = False):
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


def scrollList_hdl(ui: Interface, dsFn: Callable[[], DS], keyFn: Callable[[str, int], None], parseFn: Callable[[], str | list[str]], msg: str, req: bool = True):
    y, x = ui.w.getmaxyx()
    cw, table = ScrollList.build_table(dsFn())
    _y, _x = min(len(table.splitlines())+3, y-3), min(cw+4, x)
    box = Box(ui, _y, _x, 3, max((x-_x)//2-1, 0))
    listhdl = ScrollList(box)
    ui.draw(msg)
    listhdl.hdl(dsFn, keyFn)
    res = parseFn()
    if req:
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
    ui.w.refresh()
    box.write()
    while True:
        en.show(1, 1)
        en.activate()
        if re.match(r'[^a-zA-Z]', en.t):
            box.t = "Hostname can only contain a-z, A-Z."
            box.write()
            box.w.getkey()
            continue
        if en.t:
            return en.t
        box.t = "You can't leave that blank!"
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
        box.write()
        for en in ens:
            en.show()
        if curEn:
            curEn.activate(keyhdl, invis=curEn != usernameEn)
            continue
        if not usernameEn.t:
            popup(ui, "You can't leave your username blank.")
            curEn = ens[0]
            continue
        if not re.match(r'[a-z][-a-z0-9_]*$', usernameEn.t):
            popup(ui, "Invalid username.")
            curEn = ens[0]
            continue
        if not passwordEn.t:
            popup(ui, "You can't leave you password blank.")
            curEn = ens[1]
            continue
        if not retypeEn.t:
            popup(ui, "Please retype your password.")
            curEn = ens[2]
            continue
        if passwordEn.t != retypeEn.t:
            popup(ui, "Password is not the same.")
            curEn = ens[1]
            continue
        return usernameEn.t, passwordEn.t


def lsblk_hdl(ui: Interface) -> list[dict[str, str]]:
    def lsblk_keyhdl(k: str, sel: int):
        if k == ' ':
            global curEn
            width = min(ui.w.getmaxyx()[1], 100)
            box = new_box(ui, 7, width)
            f = f"mount /dev/{lsblk[sel]['NAME']} {chroot}"
            box.write(f'{f}\n-o \ndump: \nfsck: ')
            newMpEn = box.add_entry(width - len(f) - 2)
            optionEn = box.add_entry(width-6)
            newMpEn.t = lsblk[sel]['NEW MOUNTPOINT']
            optionEn.t = lsblk[sel]['OPTIONS']
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
                    if i == 0:
                        if newMpEn.t == '/boot/efi':
                            if not optionEn.t:
                                optionEn.t = 'umask=0077,shortname=winnt'
                    curEn = ens[0 if i > 3 else i]
                    return 'deactivate'
                if key == '\n':
                    curEn = None
                    return 'deactivate'
                return ''
            while True:
                if curEn:
                    curEn.activate(keyhdl)
                    continue
                if not newMpEn.t:
                    box = new_box(ui, 4, 30).write("Please specify a mountpoint.")
                    box.w.getkey()
                    curEn = ens[0]
                    continue
                lsblk[sel]['NEW MOUNTPOINT'] = newMpEn.t
                lsblk[sel]['OPTIONS'] = optionEn.t
                lsblk[sel]['FSCK'] = '*' if fsckCh.state else ''
                lsblk[sel]['DUMP'] = '*' if dumpCh.state else ''
                return

    y, x = ui.w.getmaxyx()
    cw, table = ScrollList.build_table(get_lsblk())
    _y, _x = min(len(table.splitlines())+3, y-7), min(cw+4, x)
    box = Box(ui, _y, _x, 7, max((x-_x)//2-1, 0))
    listhdl = ScrollList(box)
    ui.draw("Set mountpoints", f"Press SPACE to set mountpoint and options.\nPress ENTER when you're done.\n(it starts with {chroot})")
    listhdl.hdl(get_lsblk, lsblk_keyhdl)
    ds = [d for d in lsblk if d['NEW MOUNTPOINT']]
    has_root = [d for d in ds if d['NEW MOUNTPOINT'] == '/']
    has_boot_efi = [d for d in ds if d['NEW MOUNTPOINT'] == '/boot/efi']
    while not any(has_root) and any(has_boot_efi):
        popup(ui, f'One of them has to be mounted at {chroot}/ and {chroot}/boot/efi!')
        listhdl.hdl(get_lsblk, lsblk_keyhdl)
        ds = [d for d in lsblk if d['NEW MOUNTPOINT']]
        has_root = [d for d in ds if d['NEW MOUNTPOINT'] == '/']
    return ds


def main(window: 'curses._CursesWindow'):
    ui = Interface(window)

    ui.draw("Welcome to Ultramarine Installer!", "This TUI wizard will guide you through the installation.")
    ui.wait()

    selstr = 'Select your {}\npress SPACE to select, and press ENTER to continue.'

    locale = scrollList_hdl(ui, *gen_scrollList_hdl(locales, 'Locale'), selstr.format('locale'))
    keymap = scrollList_hdl(ui, *gen_scrollList_hdl(keymaps, 'Keymap'), selstr.format('keymap'))
    wizard.nmtui(ui, timeout)
    hostname = hostnamehdl(ui)
    username, password = add_user(ui)
    disks = [] if skipdisk else lsblk_hdl(ui)
    ui.draw("Waiting for dnf to finish...", "This will take a while!")
    envirns, agroups = q.get()
    envirn: list[str] = ["@"+scrollList_hdl(ui, *gen_scrollList_hdl(envirns, 'ID'), selstr.format('environment'))]
    groups = ["@"+s for s in scrollList_hdl(ui, *gen_scrollList_hdl(agroups, 'ID', True), selstr.format('groups')+' (You may select multiple ones.)', False)]
    bootloader = scrollList_hdl(ui, *gen_scrollList_hdl([{'*': '', 'NAME': 'grub'}, {'*': '', 'NAME': 'systemd-boot'}], 'NAME'), selstr.format('bootloader'))


    ui.draw("You will see your Cappy configuration file", "If you want to edit anything, just edit it.\nWhen you finish reviewing the file, press CTRL+X, Y, then ENTER to save the file.")
    ifgrub = ['grub2-efi-x64', 'shim', 'grub2-tools-efi', 'grub2-pc'] if bootloader == 'grub' else []
    password = password.replace('"', '\\"').replace('$', '\\$')  # just in case they try to inject
    yaml.dump({
        "install": {
            "installroot": chroot,
            "volumes": [{'uuid': disk['UUID'], 'mountpoint': disk['NEW MOUNTPOINT'], 'filesystem': disk['FSTYPE'], 'dump': bool(disk['DUMP']), 'fsck': bool(disk['FSCK'])} for disk in disks],
            "packages": envirn + groups + ['@core', 'nano', 'dnf', 'kernel'] + ifgrub,
            "dnf_options": {
                "install_weak_deps": True,
                "releasever": 36,
                "user_agent": 'libcappy-libdnf/0.1',
                "exclude": 'fedora-release-common'
            },
            "postinstall": [
                f'useradd {username} -p $(mkpasswd "{password}") -m'
            ],
            "bootloader": bootloader,
            "locale": locale,
            "keymap": keymap,
            "hostname": hostname
        }
    }, open('/tmp/cappyinstall.yml', 'w+'))
    ui.wait()


res = 'y'
if not skipwizard:
    p.start()
    print("This program requires a terminal with size >= x=84, y=10")
    size = os.get_terminal_size()
    print(f"The current size is: x={size.columns}, y={size.lines}")
    print("Press Ctrl+C to stop and try again.")
    print("Press F11 to open in fullscreen.")
    print("You might also need to press and hold Fn alongside.")
    try:
        input("Press ENTER to get to the next screen.")
    except KeyboardInterrupt:
        exit()
    main(curses.initscr())  #? curses.wrap() will handle some error, which we don't like
    curses.endwin()
    os.system('nano /tmp/cappyinstall.yml')  # subprocess will run it in the bg unfortunately
    res = input("You've reached the end of the wizard. Ready to install? [y/N] ")
    p.join()
if res and res in 'Yy':
    print("!! THIS WILL ERASE YOUR DATA IF NOT CONFIGURED PROPERLY !!")
    if input("Still continue? [yes] ") == 'yes':
        install()
