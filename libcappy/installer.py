# LibCappy System bootstrap libraries.
# libcappy's answer to Red Hat's Anaconda installer.
# Basically DNFStrap, but now in Python.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

from dnf.exceptions import TransactionCheckError
from libcappy.packages import Packages
from libcappy.repository import Copr
import libcappy.logger as logger
import dnf
import dnf.cli
import os
import yaml
import blivet
from blivet.size import Size
import json
import logging
import platform
import subprocess


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
    def phase_2(self, chroot=None):
        """[Phase 2]
        Installs the base packages in a chroot along with extra packages provided in the settings
        """
        phase2 = self.config['install']['phase2']
        phase1 = self.config['install']['phase1']
        # check platform
        if platform.machine() != 'x86_64':
            logger.warning('Non-x86_64 platform detected. Bootloader setup for Phase 2 is not supported at this time. Please manually set up your bootloader configuration.')
        if chroot == None:
            chroot = self.config['install']['chroot']
        chroot = os.path.abspath(chroot)
        # install the bootloader
        # check if the bootloader is in the phase2 list
        try:
            phase2['bootloader']
        except KeyError:
            if self.config['install']['efi']:
                # if it's an EFI system, assume it's going to be grub2
                logger.info('EFI system selected and no bootloader specified, assuming grub.')
                phase2['bootloader'] = 'grub'
            else:
                # if it's not an EFI system, assume it wont have a bootloader
                logger.warning('No bootloader specified. Will not install any bootloader.')
                phase2['bootloader'] = None
        packages = []
        if phase2['bootloader'] == 'grub':
            logger.info('Installing grub...')
            packages += ['grub2-pc', 'grub2-tools-extra', 'grub2-common', 'grub2-tools', 'grubby']
            if self.config['install']['efi'] and platform.machine() == 'x86_64':
                packages += ['grub2-efi-x64', 'grub2-efi-x64-modules', 'grub2-tools-efi', 'grub2-tools-extra', 'shim', ]

        elif phase2['bootloader'] == 'systemd-boot':
            logger.info('Installing systemd-boot... Please make sure your EFI partition is mounted to /efi.')
            packages += ['systemd-boot-loaders', 'systemd-boot', 'systemd-boot-generator']

        commands = [] # list of lists for subprocess.run

        # commit the bootloader install first
        spcpkg = ' '.join(packages)
        commands.append(['dnf', 'install', '-y', spcpkg])

        # We're not using the dnf module anymore becuase we're working in a chroot
        try:
            phase2['kernel']['copr-project']
            # I'm stupid why don't we just use the copr function?
            # I'm so dumb
            copr = Copr()
            repofile = copr.get_repo(phase2['kernel']['copr-project'], phase2['kernel']['chroot'])
            # write the repo file to the chroot
            with open(os.path.join(chroot, 'etc/yum.repos.d/libcappy-kernel.repo'), 'w') as f:
                f.write(repofile)
        except KeyError:
            # shit solution but works. the try/pass of doom
            pass
        # install the kernel
        commands.append(['dnf', 'install', '-y', phase2['kernel']['kernel-package']])

        # setup fstab
        partitions = self.config['install']['device']['partitions']
        fstab_entries = []
        for partition in partitions:
            # add partitions to fstab
            # assume we already mounted the partitions
            uuid = subprocess.run(['blkid', '-s', 'UUID','-o', 'value', '/dev/' + partition['path']], stdout=subprocess.PIPE).stdout.decode('utf-8').split(' ')[-1].strip()
            fstab_entries.append(f'UUID={uuid} {partition["mount"]["point"]} {partition["mount"]["type"]} {partition["mount"]["options"]} 0 0')
            # now write the fstab
            # create /etc/fstab if it doesn't exist
            if not os.path.exists(chroot + '/etc/fstab'):
                os.makedirs(chroot + '/etc', exist_ok=True)
            with open(chroot + '/etc/fstab', 'w') as f:
                logger.debug(f"fstab sample: {fstab_entries}")
                f.write('\n'.join(fstab_entries))

        # enter chroot
        # set up mounts first
        logger.info('Setting up mounts...') # This is the really risky part
        os.makedirs(chroot + '/dev', exist_ok=True)
        os.system(f'mount -t devtmpfs {chroot}/dev {chroot}/dev')
        os.system(f'mount -t proc {chroot}/proc {chroot}/proc')
        os.makedirs(chroot + '/proc', exist_ok=True)
        os.system(f'mount --rbind /sys {chroot}/sys')
        os.makedirs(chroot + '/sys', exist_ok=True)
        os.system(f"touch {chroot}/etc/resolv.conf")
        os.system(f'mount --rbind /etc/resolv.conf {chroot}/etc/resolv.conf')
        # enter chroot
        os.chroot(chroot)
        for command in commands:
            cmd = ' '.join(command)
            os.system(cmd)
        # set up the bootloader
        
        if phase2['bootloader'] == 'grub':
            if self.config['install']['efi']:
                # if it's an EFI system, assume it's going to be grub2
                logger.info('EFI system selected and no bootloader specified, assuming grub.')
                #subprocess.run(['grub2-install', '--target=x86_64-efi', '/boot/efi'])
            else:
                # if it's not an EFI system, assume it wont have a bootloader
                logger.warning('No bootloader specified. Will not install any bootloader.')
                subprocess.run(['grub2-install', '/boot'])
        elif phase2['bootloader'] == 'systemd-boot':
            logger.info('Installing systemd-boot... Please make sure your EFI partition is mounted to /efi.')
            subprocess.run(['bootctl', 'install'])
        # too dangerous to test for this right now
        # exit chroot
        os.system(f'umount {chroot}/sys')
        os.system(f'umount {chroot}/proc')
        os.system(f'umount {chroot}/dev')
        os.system(f'umount {chroot}/etc/resolv.conf')
        os.chdir('/')
        os.system('exit')
        return True
    def phase_3(self, chroot=None):
        """[Phase 3]
        Installs the rest of the system
        """
        # and we're back to using the dnf module
        phase1 = self.config['install']['phase1']
        phase3 = self.config['install']['phase3']
        if chroot == None:
            chroot = self.config['install']['chroot']
        chroot = os.path.abspath(chroot)
        # run the transaction
        command = ['dnf', 'install', '-y']
        for package in phase3['packages']:
            command.append(package)
        # now time to do some systemd stuff
        os.system(f'mount --rbind /etc/resolv.conf {chroot}/etc/resolv.conf')
        # enter chroot
        os.chroot(chroot)
        for service in phase3['services']:
            subprocess.run(['systemctl', 'enable', service])
            subprocess.run(['systemctl', 'start', service])
        # exit the chroot
        subprocess.run(command)


        # User configuration
        # comments for copilot becuase I'm not going to literally type out everything manually, fuck GPL
        for user in phase3['users']:
            # The user schema as username, password, groups, home, uid, gid, and shell so we have to do all of this in one go
            # create the user
            subprocess.run(['useradd', '-m', '-s', user['shell'], '-u', user['uid'],  user['name']])
            # set the password with the password provided
            # the password is in plain text, so we have to use the passwd command
            subprocess.run(['passwd', user['name']], input=user['password'].encode('utf-8'))
            # add the user to the groups
            for group in user['groups']:
                subprocess.run(['usermod', '-a', '-G', group, user['name']])
            # set the home directory
            subprocess.run(['chown', '-R', f'{user["uid"]}:{user["gid"]}', user['home']])
            # set the shell
            subprocess.run(['chsh', '-s', user['shell'], user['name']])
            # if auth exists, set it
            if 'auth' in user:
                if 'public-key' in user['auth']:
                    # this should always be a list of strings (public keys)
                    for key in user['auth']['public-key']:
                        subprocess.run(['mkdir', '-p', f'{user["home"]}/.ssh'])
                        subprocess.run(['touch', f'{user["home"]}/.ssh/authorized_keys'])
                        subprocess.run(['chmod', '700', f'{user["home"]}/.ssh'])
                        subprocess.run(['chmod', '600', f'{user["home"]}/.ssh/authorized_keys'])
                        subprocess.run(['echo', key, '>>', f'{user["home"]}/.ssh/authorized_keys'])

            #postinstall tasks
            if 'postinstall-scripts' in phase3:
                for command in phase3['postinstall-scripts']:
                    subprocess.run(['bash', '-c', command])
            if 'risiscript' in phase3:
                # something something risiscript here, blame pizzanerd for not releasing it yet
                pass

        os.chdir('/')
        os.system('exit')

    # finally, we're done
    # if you run all the phases, you'll get a fully installed system
    # if you run phase 1, you'll get a minimal chroot. useful for mock and containers
    # if you run phase 2, you'll get a bootable system
    # if you run phase 3, you get everything else
    # for partitioning, my head still hurts, but I'll get to it eventually. blivet is pain

    # Maybe I'll also make a yaml generator for on-the-fly configuration when you're not using unattended install

class ConfigGenerator:
    def __init__(self, config):
        self.config = config

    def generate_config(self):
        # this is where we'll generate the config
        # for now, just return the config
        return self.config