# LibCappy System bootstrap libraries.
# libcappy's answer to Red Hat's Anaconda installer.
# Basically DNFStrap, but now in Python.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

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
    def postInstall(self):
        """postInstall
        Runs the post-installation commands.
        """
        self.logger.info('Running post-installation commands')
        for command in self.config['postinstall']:
            self.nspawn(command)
    def fstab(self, table: dict):
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
