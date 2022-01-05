# LibCappy System bootstrap libraries.
# libcappy's answer to Red Hat's Anaconda installer.
# Basically DNFStrap, but now in Python.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

from dnf.exceptions import TransactionCheckError
from libcappy.packages import Packages
import libcappy.logger as logger
import dnf
import os
import yaml
import blivet
from blivet.size import Size
import json
import logging

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
            devices = [] # devices list
            for partition in self.partitions:
                if partition['type'] == 'EFI':
                    # create a new EFI partition
                    efipart = b.devicetree.get_device_by_name(partition['path'])
                    if not partition['delete']:
                        pass
                    if efipart and partition['delete'] == True:
                        fmt = blivet.formats.get_format('efi', device=efipart.path)
                        b.format_device(efipart, fmt)

                else:
                    # check if the partition already exists
                    # if it does, check if the delete flag is set
                    # if it is, delete the partition
                    # if it doesn't, skip it and add the device to the list

                    # check if it's a btrfs partition
                    if partition['type'] == 'btrfs':
                        logger.warning('Btrfs partitions are not supported at this time. If you\'d like to help us implement this feature, please submit a merge request at https://gitlab.ultramarine-linux.org/src/cappy/.')
                        subvolumes = partition['subvolumes']
                        # check if this btrfs partition is already created
                        # find btrfs volumes that has a parent of the partition path
                        # if it's not found, create it
                        for volume in b.btrfs_volumes:
                            logger.debug(f"Parent of {volume.name}: {volume.dict['parents']}")
                        # I can't be bothered to make a case for multiple parents at the moment, so just assume it's dad went for some milk.
                            if partition['path'] in volume.dict['parents']:
                                logger.debug(f'volume {volume.name} has parent {partition["path"]}')
                                # then check if the subvolume name matches the subvolume name in the config
                                for subvolume in subvolumes:
                                    if subvolume['subvolume'] == volume.name:
                                        logger.debug(f'volume {volume.name} has subvolume {subvolume["subvolume"]}')
                                        # if it does, check if the delete flag is set
                                        # if it is, delete the subvolume
                                        # if it doesn't, skip it
                                        try:
                                            subvolume['delete']
                                        except KeyError:
                                            subvolume['delete'] = True
                                        if subvolume['delete'] == True:
                                            logger.debug(f'Deleting subvolume {subvolume["subvolume"]}')
                                            b.destroy_device(volume)
                                            fmt = blivet.formats.get_format('btrfs', device=volume.path, label=subvolume['subvolume'])
                                            #if subvolume['mount']['point']:
                                            #    subvolume['mount']['point'] = self.config['install']['chroot'] + subvolume['mount']['point']
                                            new_subvol = b.new_btrfs_sub_volume(fmt, subvolume['mount']['point'])
                                            b.create_device(new_subvol)
                                        else:
                                            logger.debug(f"Adding subvolume {subvolume['subvolume']} to the list of devices to mount.")
                                            devices.append(volume)
                                            continue
                                    else:
                                        logger.debug(f"Subvolume {subvolume['subvolume']} not found on volume {volume.name}")
                                        # create the subvolume on the parent volume
                                        # then add the subvolume to the list of devices to mount
                    else:
                        # if it's not a btrfs partition, skip all this hell and just do the usual thing
                        try:
                            partition['delete']
                        except KeyError:
                            partition['delete'] = True
                        if partition['delete'] == True:
                            # get partition path
                            part = b.devicetree.get_device_by_name(partition['path'])
                            # if it exists, delete it
                            if part:
                                fmt = blivet.formats.get_format('ext4', device=part.path)
                                b.format_device(part, fmt)
                        else:
                            # if it doesn't exist, create it
                            device = b.devicetree.get_device_by_name(partition['path'])
                            if not device:
                                fmt = blivet.formats.get_format(partition['type'], device=partition['path'], label=partition['label'], mountpoint=partition['mount']['point'], mountopts=partition['mount']['options'])
                                b.create_device(fmt)


            # return the actions list as a readable string
            actions = b.devicetree.actions
            return actions
        # this literally makes my head hurt please help partitioning is pain

    def phase_1(self, chroot=None):
        """[Phase 1]
        Installs base packages in a chroot along with extra packages provided in the settings
        """
        phase1 = self.config['install']['phase1']
        print(phase1)
        if chroot == None:
            chroot = self.config['install']['chroot']
        # fuck it, call DNF directly
        ts = dnf.Base()
        ts.read_all_repos()
        # turn chroot into an absolute path
        chroot = os.path.abspath(chroot)
        ts.conf.installroot = chroot
        ts.conf.releasever = self.config['install']['releasever']
        ts.conf.substitutions['releasever'] = self.config['install']['releasever']
        # add extra repos
        # shit solution but hey, it kind of works
        try:
            phase1['extra_repos']
        except KeyError:
            phase1['extra_repos'] = [] # make it an empty list if it doesn't exist
        if phase1['extra_repos']:
            reponum = 0
            for repo in phase1['extra_repos']:
                repos = dnf.repo.Repo(f'libcappy-extra-repo-{reponum}')
                repos.baseurl = repo
                ts.repos.add(repos)
                reponum += 1
        ts.fill_sack(load_system_repo=False, load_available_repos=True)
        for pkg in phase1['packages']:
            if pkg.startswith('@'):
                # expand the group
                group = ts.comps.group_by_pattern(pkg[1:])
                try:
                    for p in group.mandatory_packages:
                        ts.install(p.name)
                    for p in group.default_packages:
                        ts.install(p.name)
                except dnf.exceptions.PackageNotFoundError:
                    logger.error(f'Package {p.name} not found in the group {pkg[1:]}')
            else:
                # if it doesn't, it's a package
                # install the package
                try:
                    ts.install(pkg)
                except dnf.exceptions.PackageNotFoundError:
                    logger.error(f'Package {pkg} not found')

        # run the transaction
        ts.resolve()
        ts.download_packages(ts.transaction.install_set)
        try:
            ts.do_transaction()
        except TransactionCheckError as e:
            logger.error(f'Transaction failed: {e}')
            return None
        return ts