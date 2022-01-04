import dnf
import os
import sys


class Packages:
    # class for managing packages via DNF
    # Simply macros to quickly call DNF functions without writing long transactions manually.
    def __init__(self):
        self.base = dnf.Base()
        self.base.read_all_repos()
        self.base.read_comps()
        self.base.fill_sack(load_system_repo=False, load_available_repos=True)


    def install(self,packages:list, opts:dict=None):

        """
        [summary]
        Installs packages via DNF.

        Arguments:
        packages: list, packages to install
        opts: dict, DNF options
        """
        #apply all the keys in opts to the base config
        for key in opts:
            self.base.conf.set_or_append_opt_value(key, opts[key])
        # add the packages to the sack
        self.base.fill_sack(load_system_repo=False, load_available_repos=True)
        # install the packages
        for package in packages:
            self.base.install(package)
        # commit the transaction
        self.base.resolve()
        self.base.do_transaction()

    def remove(self,packages:list, opts:dict=None):

            """
            [summary]
            Removes packages via DNF.

            Arguments:
            packages: list, packages to remove
            opts: dict, DNF options
            """
            #apply all the keys in opts to the base config
            for key in opts:
                self.base.conf.set_or_append_opt_value(key, opts[key])
            # add the packages to the sack
            self.base.fill_sack(load_system_repo=False, load_available_repos=True, load_enabled_repos=True)
            # remove the packages
            for package in packages:
                self.base.remove(package)
            # commit the transaction
            self.base.resolve()
            self.base.do_transaction()
    def update(self,packages:list=None, opts:dict=None):
            """
            [summary]
            Updates packages via DNF.

            Arguments:
            packages: list, packages to update
            opts: dict, DNF options
            """
            #apply all the keys in opts to the base config
            for key in opts:
                self.base.conf.set_or_append_opt_value(key, opts[key])
            # add the packages to the sack
            self.base.fill_sack(load_system_repo=False, load_available_repos=True, load_enabled_repos=True)
            # update the packages
            if packages == None:
                self.base.upgrade_all()
            else:
                for package in packages:
                    self.base.upgrade(package)
            # commit the transaction
            self.base.resolve()
            self.base.do_transaction()