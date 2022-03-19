import os
from libcappy.installer import Installer


def install():
    print("Initialising...")
    installer = Installer('/tmp/cappyinstall.yml')
    fstab = installer.cfgparse.fstab()
    print("Mounting partitions...")
    installer.mount(fstab)
    print("Installing to chroot...")
    installer.instRoot()
    print("genfstab...")
    installer.fstab(fstab)
    print("Installing bootloader...")
    chroot: str = installer.cfgparse.config['installroot']
    bootloader: str = installer.cfgparse.config['bootloader']
    if bootloader == 'grub':
        installer.grubGen(chroot)
    elif bootloader == 'systemd-boot':
        installer.systemdBoot(chroot)
    else:
        print(f"ERROR: Bootloader '{bootloader}' not supported")
        print(f"ERROR: You have to install one to boot Ultramarine Linux!")
    print("Running post-install scripts...")
    installer.postInstall()
    os.remove(os.path.join(chroot, 'machine-id'))

    print("Ultramarine Linux has been installed.")
