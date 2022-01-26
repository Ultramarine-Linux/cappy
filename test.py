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