def cappy_test():
    import sys
    import os
    import json
    args = sys.argv[1:]
    print(args)
    match args[0]:
        case 'install':
            import libcappy.installer as installer
            inst = installer.Installer(config='example.yml')
            inst.instRoot()
            inst.postInstall()
        case 'copr':
            import libcappy.repository as repository
            repo = repository.Copr()
            repos = repo.list_projects()
            repos = json.dumps(repos, indent=4)
            # write repos to file
            with open('repos.json', 'w') as f:
                f.write(repos)
        case 'dnf':
            # This is a test to see if we can install packages from a dnf repo, ON YOUR LOCAL SYSTEM
            # Don't worry, it just installs powertop, which is a pretty harmless package. Might be useful if you wanted to know your power usage though.
            import libcappy.packages as packages
            pkgs = packages.Packages()
            pkgs.install(['powertop'])

def wboy_test():
    from libcappy.installer import Wizard
    from libcappy.tui.console import style
    w = Wizard()
    print(w.locales())

wboy_test()
