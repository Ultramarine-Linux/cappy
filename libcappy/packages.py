from click import progressbar
import dnf
import os
import sys
import dnf.cli.progress
import dnf.callback
import dnf.cli.output
import logging
logger = logging.getLogger(__name__)
class Packages:
    # class for managing packages via DNF
    # Simply macros to quickly call DNF functions without writing long transactions manually.
    def __init__(self, installroot=None, opts=None):
        self.dnf = dnf.Base()
        self.conf = self.dnf.conf
        self.transdisplay = dnf.cli.output.CliTransactionDisplay()
        self.downprogress = dnf.cli.progress.MultiFileProgressMeter()
        if installroot:
            self.chroot = os.path.abspath(installroot)
            self.conf.set_or_append_opt_value('installroot', self.chroot)
            self.conf.set_or_append_opt_value('cachedir', os.path.join(self.chroot, 'var/cache/dnf'))
        else:
            self.chroot = os.path.abspath(os.sep)
        if opts:
            for opt in opts:
                match opt:
                    case 'arch':
                        self.conf.substitutions['arch'] = opts[opt]
                    case 'releasever':
                        self.conf.substitutions['releasever'] = str(opts[opt])
                    case 'basearch':
                        self.conf.substitutions['basearch'] = opts[opt]
                    case _:
                        self.conf._set_value(opt, opts[opt])
        # load the new configuration
        self.dnf.read_all_repos(opts=self.conf.substitutions)
        #print(self.dnf._repos)
        #self.dnf.setup_loggers()
        logger.info('Loading Repositories...')
        self.dnf.fill_sack()
    def install(self, pkgs: list):
        # install a list of packages
        self.dnf.install_specs(pkgs)
        try:
            self.dnf.resolve(allow_erasing=True)
        except dnf.exceptions.DepsolveError as e:
            logger.error(f'Transaction resolution failed: {e}')
            return False
        self.dnf.download_packages(self.dnf.transaction.install_set, self.downprogress)
        # Yes, we're stealing the progress bar from dnf's CLI.
        self.dnf.do_transaction(self.transdisplay)
    def remove(self, pkgs: list):
        # remove a list of packages
        for pkg in pkgs:
            try:
                self.dnf.remove(pkg)
            except dnf.exceptions.PackageNotFoundError:
                logger.warning('Package %s not found in repository' % pkg)
        self.dnf.resolve()
        self.dnf.download_packages(self.dnf.transaction.remove_set)
        self.dnf.do_transaction(self.transdisplay)
    def update(self):
        # update all packages
        self.dnf.upgrade_all()
        self.dnf.resolve()
        self.dnf.download_packages(self.dnf.transaction.install_set, self.downprogress)
        self.dnf.do_transaction(self.transdisplay)
    def updatePkg(self, pkgs: list):
        # update a list of packages
        for pkg in pkgs:
            try:
                self.dnf.upgrade(pkg)
            except dnf.exceptions.PackageNotFoundError:
                logger.warning('Package %s not found in repository' % pkg)
        self.dnf.resolve()
        self.dnf.download_packages(self.dnf.transaction.install_set)
        self.dnf.do_transaction(self.transdisplay)
