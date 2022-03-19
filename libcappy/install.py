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
    bootloader = installer.cfgparse.config['bootloader']
    if bootloader == 'grub':
        installer.grubGen(installer.cfgparse.config['installroot'])
    elif bootloader == 'systemd-boot':
        installer.systemdBoot(installer.cfgparse.config['installroot'])
    else:
        print(f"ERROR: Bootloader '{bootloader}' not supported")
        print(f"ERROR: You have to install one to boot Ultramarine Linux!")
    print("Running post-install scripts...")
    installer.postInstall()

    print("Ultramarine Linux has been installed.")
