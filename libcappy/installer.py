# LibCappy System bootstrap libraries.
# libcappy's answer to Red Hat's Anaconda installer.
# Basically DNFStrap, but now in Python.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

from libcappy.packages import Packages
import libcappy.logger as logger
import dnf
import os
import yaml
import blivet
from blivet.size import Size

class Bootstrap(object):
    """[summary]
    Bootstrap class for installing an entire Ultramarine/Fedora system from scratch, using only DNF.
    Args:
        chroot=None/str: path to the desired chroot.
        dev=None/str: path to the desired target device.

        ^^

        Either of the above must be declared.

        config=None/str: path to the config.yml file.
    """
    def __init__(self, config, chroot=None, dev=None,):
        logger.debug('Bootstrap class called')
        self.pkgs = Packages()
        self.dnf = dnf.Base()
        if config:
            with open(config, 'r') as f:
                self.config = yaml.load(f, Loader=yaml.Loader)
        if chroot:
            self.config['install']['chroot'] = chroot
        if dev:
            self.config['install']['device']['path'] = dev
        logger.debug(self.config)
    def setup_partitions(self):
        """
        [summary]
        Initializes the partitions on the target device. (Phase 0)
        Arguments are to be passed when the class is instantiated. It will load the config.yml file.
        """
        if not self.config['install']['chroot']:
            self.config['install']['chroot'] = '/mnt/sysimage'
        if not self.config['install']['device']['path'] and not self.config['install']['device']['path']:
            raise Exception('No device or chroot specified.')

        # check if there's a partition with the type EFI
        # partitions are an array with a dict
        # we must find the type key within it
        if self.config['install']['device']['partitions']:
            for partition in self.config['install']['device']['partitions']:
                if partition['type'] == 'EFI':
                    self.has_efi_partition = True
                    self.efi_partition = partition
                    break
                else:
                    self.has_efi_partition = False
        if self.config['install']['efi'] == True and self.has_efi_partition == False:
            raise Exception('No EFI partition found, but EFI boot is enabled.')

        # Time to set up the partitions.
        if self.config['install']['device']['partitions']:
            self.partitions = self.config['install']['device']['partitions']
            b = blivet.Blivet()
            b.reset()
            for partition in self.partitions:
                # check if the device path already exists
                if os.path.exists(partition['path']):
                    part = b.device_get_device_by_name(partition['path'])
                    if partition['delete'] == True or not partition['delete']:
                        b.destroy_format(part)
                        b.resize_device(part, Size(partition['size']))
                        fmt = blivet.formats.get_format(partition['format'], device=part.path)