import dnf
import os
import sys
from libcappy.logger import logger

class Packages:
    # class for managing packages via DNF
    # Simply macros to quickly call DNF functions without writing long transactions manually.
    def __init__(self, installroot=None, opts=None):
        self.dnf = dnf.Base()
        self.dnf.read_all_repos()
        if installroot:
            self.chroot = os.path.abspath(installroot)
            self.dnf.conf.set_or_append_opt_value('installroot', self.chroot)
            self.dnf.conf.set_or_append_opt_value('cachedir', os.path.join(self.chroot, 'var/cache/dnf'))
        else:
            self.chroot = os.path.abspath(os.sep)
        if opts:
            if opts['releasever']:
                self.dnf.conf.substitutions['releasever'] = opts['releasever']
            for option in opts:
                try:
                    self.dnf.conf.set_or_append_opt_value(option, opts[option])
                except:
                    pass
        self.dnf.setup_loggers()
        self.dnf.fill_sack()
    def install(self, pkgs: list):
        # install a list of packages
        for pkg in pkgs:
            try:
                if pkg.startswith('@'):
                    pkggroup = self.dnf.comps.group_by_pattern(pkg[1:])
                    self.dnf.group_install(pkggroup._i.id, dnf.const.GROUP_PACKAGE_TYPES)
                else:
                    self.dnf.install(pkg)
            except dnf.exceptions.PackageNotFoundError:
                logger.warning('Package %s not found in repository' % pkg)
        self.dnf.resolve()
        self.dnf.download_packages(self.dnf.transaction.install_set)
        self.dnf.do_transaction()
    def remove(self, pkgs: list):
        # remove a list of packages
        for pkg in pkgs:
            try:
                self.dnf.remove(pkg)
            except dnf.exceptions.PackageNotFoundError:
                logger.warning('Package %s not found in repository' % pkg)
        self.dnf.resolve()
        self.dnf.download_packages(self.dnf.transaction.remove_set)
        self.dnf.do_transaction()
    def update(self):
        # update all packages
        self.dnf.upgrade_all()
        self.dnf.resolve()
        self.dnf.download_packages(self.dnf.transaction.install_set)
        self.dnf.do_transaction()
    def updatePkg(self, pkgs: list):
        # update a list of packages
        for pkg in pkgs:
            try:
                self.dnf.upgrade(pkg)
            except dnf.exceptions.PackageNotFoundError:
                logger.warning('Package %s not found in repository' % pkg)
        self.dnf.resolve()
        self.dnf.download_packages(self.dnf.transaction.install_set)
        self.dnf.do_transaction()