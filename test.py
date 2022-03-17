from datetime import datetime
from libcappy.installer import Wizard


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


def build_table(ds: list[dict[str, str]]):cols = list(ds[0].keys());return "│".join(col+' '*((cw := [max(len(cols[n]), [max(len(d[cols[n]])for d in ds)for n in range(len(cols))][n])for n in range(len(cols))])[i]-len(col))for i, col in enumerate(cols))+'\n'+"\n".join("│".join(v+' '*(cw[i]-len(v))for i, v in enumerate(r))for r in [[d[col]for col in cols]for d in ds])


w = Wizard()
lsblk = w.lsblk()
_, lsblk = w.uniform_dict(lsblk)
lsblk = w.strip_lsblk(lsblk)
d = datetime.now()
print(build_table(lsblk))
print((datetime.now() - d).microseconds)
