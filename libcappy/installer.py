# LibCappy System bootstrap libraries.
# libcappy's answer to Red Hat's Anaconda installer.
# Basically DNFStrap, but now in Python.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

from dataclasses import field
import re
import shutil
from typing import Any, Tuple
from dnf.exceptions import TransactionCheckError
from libcappy.packages import Packages
from libcappy.repository import Copr
import logging
logger = logging.getLogger(__name__)
import os
import yaml
import json
import platform
import subprocess
import importlib.resources
class Config(object):
    # the class for reading and writing configuration files
    def __init__(self, configfile):
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
    def __init__(self,config):
        self.config = config

    def dump(self):
        return self.config

    def fstab(self):
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

    def nspawn(self,command: str):
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
    def fstab(self, table: list[dict[str, str|bool]]):
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
    def grubGen(self, root: str, boot: str=None):
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
    def systemdBoot(self, root: str, boot: str=None):
        # make /efi
        os.makedirs(os.path.join(self.chroot_path, 'boot', 'efi'), exist_ok=True)
        self.nspawn('bootctl install --boot-path=/boot --esp-path=/boot')
        self.nspawn(f'kernel-install add $(uname -r) /lib/modules/$(uname -r)/vmlinuz')
        self.nspawn('dnf reinstall $(rpm -qa|grep kernel-core)')
    def mount(self, table: list[dict[str, str|bool]]):
        for entry in table:
            self.nspawn(f"mount {entry['device']} {entry['mountpoint']}" + f"-o {entry['opts']}" if entry['opts'] else '')


class Wizard:
    def lsblk(self):
        parts: list[dict[str, str]] = []
        lines = subprocess.getoutput("lsblk -l").splitlines()
        lines.pop(0)
        for l in lines:
            if l[0] == ' ':
                parts.append(parts[-1].copy())
                parts[-1]['MOUNTPOINTS'] = l.strip()
                continue
            ls = l.split()
            ls.append('') # in case no mp
            parts.append({
                'NAME': ls[0],
                'SIZE': ls[3],
                'TYPE': ls[5],
                'MOUNTPOINTS': ls[6]  # mountpoint
            })

        lines = subprocess.getoutput("lsblk -lf").splitlines()
        fields = re.findall(r'\S+\s*', lines.pop(0), re.RegexFlag.M)
        i: int = 0
        for l in lines:
            left = 0
            cur: dict[str, str] = {}
            for field in fields:
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

                assert any(cur)
                if not v: continue
                cur[f] = v
            if any(cur):
                parts[i] = cur
        return parts

    @staticmethod
    def uniform_dict(dicts: list[dict[str, Any]], dummy='') -> Tuple[set[str], list[dict[str, Any]]]:
        fields: set[str] = [f for d in dicts for f in d]
        newDicts: list[dict[str, Any]] = []
        default = {k: dummy for k in fields}
        for d in dicts:
            new = default.copy()
            new.update(d)
            newDicts.append(new)
        return fields, newDicts

    def strip_lsblk(self, parts: list[dict[str, str]]):
        # we don't allow users to select their installation media as the target
        return [d for d in parts if d['MOUNTPOINTS'] not in ['/', '/boot/efi', '/boot']]

    def localectl(self):
        return subprocess.getoutput("localectl list-locales --no-pager").splitlines()

    def locales(self):
        #! fix when build
        return subprocess.getoutput(os.path.join(os.path.dirname(__file__), 'parse_locales/target/release/cappy_parse_locales'))
