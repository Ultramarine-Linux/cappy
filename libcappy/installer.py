# LibCappy System bootstrap libraries.
# libcappy's answer to Red Hat's Anaconda installer.
# Basically DNFStrap, but now in Python.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

import importlib.resources
import logging
import os
import re
import shutil
import subprocess
from urllib.request import urlopen

import yaml
from dnf import Base

from libcappy.common import DS
from libcappy.ui import Interface

from .packages import Packages
from .repository import Copr

logger = logging.getLogger(__name__)


class Config(object):
    # the class for reading and writing configuration files
    def __init__(self, configfile: str):
        # read the configuration YAML file
        with open(configfile, 'r') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)['install']
        # set the default values if not specified
        if 'installroot' not in self.config:
            self.config['installroot'] = '/mnt/sysimage'


class CfgParser(Config):
    """[summary]
    Parses specific parts of the DNFStrap configuration from YAML into readable data.

    Arguments:

    cfg = an instance of libcappy.installer.Config()
    """

    def __init__(self, config: Config):
        self.config = config

    def dump(self):
        return self.config

    def fstab(self) -> list[dict[str, str | bool]]:
        """Parses the volumes section of the install and returns it as a proper fstab dictionary.
        """
        volumes = self.config['volumes']
        entry_def = {
            'device': str,
            'mountpoint': str,
            'filesystem': str,
            'opts': str,
            'dump': bool,
            'fsck': bool,
        }
        entry_def.setdefault('opts', 'defaults')
        entry_def.setdefault('dump', False)
        entry_def.setdefault('fsck', False)
        # fstab will be a list of entries, we'll deal with it later
        fstab = []
        for volume in volumes:
            # copy the entry dictionary
            entry = entry_def.copy()
            # if uuid key exists, use it as device
            if 'uuid' in volume:
                entry['device'] = 'UUID=' + volume['uuid']
            elif 'label' in volume:
                entry['device'] = 'LABEL=' + volume['label']
            else:
                entry['device'] = volume['device']
            entry['mountpoint'] = volume['mountpoint']
            entry['filesystem'] = volume['filesystem']
            # very long if-else statement i know, you guys are welcome to improve it
            if 'opts' in volume:
                entry['opts'] = volume['opts']
            else:
                entry['opts'] = 'defaults'
            if 'dump' in volume:
                entry['dump'] = volume['dump']
            else:
                entry['dump'] = False
            if 'fsck' in volume:
                entry['fsck'] = volume['fsck']
            else:
                entry['fsck'] = False
            fstab.append(entry)
        return fstab


class Installer:
    """
    [summary]
    Libcappy installer module. This class is used to bootstrap a minimal Fedora/Ultramarine chroot from scratch,
    Similar to the likes of Arch Linux's pacstrap.
    """

    def __init__(self, config):
        """
        Initializes the Installer class.

        Arguments:
        chroot_path {[type]} -- [description]
        """
        self.config = Config(config).config
        self.cfgparse = CfgParser(self.config)
        self.chroot_path = self.config['installroot']
        self.packages = Packages(installroot=self.chroot_path, opts=self.config['dnf_options'])
        self.copr = Copr()
        self.logger = logger
        self.logger.debug('Initializing Installer class')

    def nspawn(self, command: str):
        """Calls systemd-nspawn to do the bidding

        Args:
            command ([type]): command
        """
        self.logger.info(f'Running command: "{command}" on chroot')
        subprocess.run([
            'systemd-nspawn',
            '--quiet',
            '-D',
            self.chroot_path,
            '/bin/bash',
            '-c',
            '--capability=CAP_SYS_ADMIN,CAP_SYS_RAWIO',
            command
        ])

    def instRoot(self):
        """instRoot
        Initializes the chroot directory.
        """
        if not os.path.exists(self.chroot_path):
            os.makedirs(self.chroot_path)
        self.logger.debug('Created chroot directory')
        self.logger.info('Initializing chroot directory')
        self.packages.install(self.config['packages'])
        # create /.autorelabel
        with open(os.path.join(self.chroot_path, '.autorelabel'), 'w') as f:
            f.write('1')
        self.logger.info('Installed packages')

    def postInstall(self):
        """postInstall
        Runs the post-installation commands.
        """
        self.logger.info('Running post-installation commands')
        for command in self.config['postinstall']:
            self.nspawn(command)

    def fstab(self, table: list[dict[str, str | bool]]):
        """fstab
        Generates a Filesystem Table (fstab)

        Arguments:
            table {[table]} -- [description]

        """
        self.logger.info('Writing fstab')
        with open(os.path.join(self.chroot_path, 'etc/fstab'), 'w') as f:
            f.write('# /etc/fstab: static file system information. Auto-Generated by libcappy installer.\n')
            f.write('# <file system> <mount point>   <type>  <options>       <dump>  <pass>\n')
            for entry in table:
                f.write(f'{entry["device"]}\t')
                f.write(f'{entry["mountpoint"]}\t')
                f.write(f'{entry["filesystem"]}\t')
                f.write(f'{entry["opts"]}\t')
                if entry['dump'] == True:
                    entry['dump'] = '1'
                else:
                    entry['dump'] = '0'
                f.write(f'{entry["dump"]}\t')
                if entry['fsck'] == True:
                    entry['fsck'] = '1'
                else:
                    entry['fsck'] = '0'
                f.write(f'{entry["fsck"]}\n')
        self.logger.debug('Wrote fstab')

    def grubGen(self, root: str, boot: str = None):
        """[summary]
        Configures GRUB for the chroot.
        """
        self.logger.info('Configuring GRUB')
        # use importlib.resources to load templates/grub.cfg
        with importlib.resources.path('libcappy', 'templates/grub.cfg') as template:
            with open(os.path.join(self.chroot_path, 'boot/efi/EFI/fedora/grub.cfg'), 'w') as f:
                # replace @UUID@ with the UUID of the root partition then write to file
                f.write(template.read().replace('@UUID@', root))

        # copy boot/efi/EFI/fedora/grub.cfg to boot/efi/EFI/BOOT/grub.cfg
        shutil.copy(os.path.join(self.chroot_path, 'boot/efi/EFI/fedora/grub.cfg'), os.path.join(self.chroot_path, 'boot/efi/EFI/BOOT/grub.cfg'))
        self.nspawn(f'grubby --remove-args="rd.live.image" --update-kernel ALL')
        self.nspawn(f'grubby --remove-args="root" --update-kernel=ALL --copy-default')
        self.nspawn(f'grubby --add-args="root={root}" --update-kernel=ALL --copy-default')

    def systemdBoot(self, root: str, boot: str = None):
        # make /efi
        os.makedirs(os.path.join(self.chroot_path, 'boot', 'efi'), exist_ok=True)
        self.nspawn('bootctl install --boot-path=/boot --esp-path=/boot')
        self.nspawn(f'kernel-install add $(uname -r) /lib/modules/$(uname -r)/vmlinuz')
        self.nspawn('dnf reinstall $(rpm -qa|grep kernel-core)')

    def mount(self, table: list[dict[str, str | bool]]):
        for entry in table:
            self.nspawn(f"mount {entry['device']} {entry['mountpoint']}" + f"-o {entry['opts']}" if entry['opts'] else '')


class Wizard:
    @staticmethod
    def lsblk():
        parts: DS = []
        lines = subprocess.getoutput("lsblk -l").splitlines()
        lines.pop(0)
        for l in lines:
            if l[0] == ' ':
                parts.append(parts[-1].copy())
                parts[-1]['MOUNTPOINTS'] = l.strip()
                continue
            ls = l.split()
            ls.append('')  # in case no mp
            parts.append({
                'NAME': ls[0],
                'SIZE': ls[3],
                'TYPE': ls[5],
                'MOUNTPOINTS': ls[6]  # mountpoint
            })

        lines = subprocess.getoutput("lsblk -lf").splitlines()
        fields = re.findall(r'\S+\s*', lines.pop(0), re.RegexFlag.M)
        last_field = fields[-1]
        i: int = 0
        for l in lines:
            left = 0
            cur: dict[str, str] = {}
            for field in fields:
                if last_field == field:
                    value = l[left:]
                else:
                    length = len(field)
                    value = l[left:left+length]
                    left += length
                v = value.strip()
                # first field
                if (f := field.rstrip().upper()) == 'NAME':
                    if not v:  # v == ''
                        assert ' ' not in (mp := l.strip())  # make sure it's only 1 col
                        p = parts[i].copy()
                        p['MOUNTPOINTS'] = mp
                        found = False
                        for n, part in enumerate(parts):
                            if part['MOUNTPOINTS'] == mp:
                                found = True
                                break
                        if found:
                            parts[n].update(p)
                        break  # just a thing with a different mountpoint
                    for n, part in enumerate(parts):
                        if part['NAME'] == v:
                            cur = part
                            i = n
                            break
                if not v:
                    continue
                cur[f] = v
            if any(cur):
                parts[i] = cur
        return parts

    @staticmethod
    def tidy_lsblk(dicts: DS, dummy: str = '') -> tuple[set[str], DS]:
        fields: set[str] = set([f for d in dicts for f in d] + ['NEW MOUNTPOINT', 'OPTIONS', 'FSCK', 'DUMP'])
        newDicts: DS = []
        default = {k: dummy for k in fields}
        for d in dicts:
            new = default.copy()
            new.update(d)
            newDicts.append(new)
        return fields, newDicts

    @staticmethod
    def strip_lsblk(parts: DS):
        # we don't allow users to select their installation media as the target
        lsblk = [d for d in parts if d['MOUNTPOINTS'] not in ['/', '/boot/efi', '/boot']]
        s = ['NAME', 'TYPE', 'FSTYPE', 'FSVER', 'LABEL', 'SIZE', 'MOUNTPOINTS', 'NEW MOUNTPOINT', 'OPTIONS', 'DUMP', 'FSCK', 'UUID', 'FSAVAIL', 'FSUSE%']
        ds: DS = []
        for d in lsblk:
            new = {}
            for ss in s:
                new[ss] = d[ss]
            ds.append(new)
        return ds

    def localectl(self):
        return subprocess.getoutput("localectl list-locales --no-pager").splitlines()

    def locales(self):
        #! fix when build
        return subprocess.getoutput(os.path.join(os.path.dirname(__file__), 'parse_locales/target/release/cappy_parse_locales'))

    def keymaps(self):
        return [{"*": '', "Keymap": v} for v in subprocess.getoutput("localectl list-keymaps --no-pager").splitlines()]

    def nmtui(self, ui: Interface, timeout: float):
        while True:
            try:
                ui.draw("Checking Internet connection...", 'Trying to connect to https://getfedora.org/')
                urlopen('https://getfedora.org/', timeout=timeout)
                return
            except:
                ui.draw("Failed to connect!", "Do you want to open nmtui to connect to a wireless network? [y/n]")
                while True:
                    k = ui.w.getkey()
                    if k in 'yY':
                        subprocess.run('nmtui')  #! requires dnf install NetworkManager-tui
                        break
                    elif k in 'nN':
                        ui.draw("Connecting to the Internet by yourself", "We will check if we can successfully connect to the Internet after you press SPACE.")
                        ui.wait()
                        break

    @staticmethod
    def fetch_envs_grps() -> tuple[DS, DS]:
        with Base() as base:
            # TODO: Option to load local repo for offline mode
            base.read_all_repos()
            base.fill_sack()
            comps = base.comps
            assert comps != None, "dnf.Base().comps failed miserably ;("  # might be None
            return [{'*': '', 'NAME': env.ui_name, 'DESCRIPTION': env.ui_description or ''} for env in comps.environments_iter()], [{'*': '', 'NAME': grp.ui_name, 'DESCRIPTION': grp.ui_description or ''} for grp in comps.groups_iter()]
