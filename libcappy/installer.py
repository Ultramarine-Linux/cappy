# LibCappy System bootstrap libraries.
# libcappy's answer to Red Hat's Anaconda installer.
# Basically DNFStrap, but now in Python.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

from dnf.exceptions import TransactionCheckError
from libcappy.packages import Packages
from libcappy.repository import Copr
import libcappy.logger as logger
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
        self.chroot_path = self.config['installroot']
        self.packages = Packages(installroot=self.chroot_path, opts={'releasever': self.config['releasever']})
        self.copr = Copr()
        self.logger = logger.logger
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