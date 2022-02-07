import pytest
import subprocess
import os
import json
def test_copr():
    import libcappy.repository as repository
    repo = repository.Copr()
    repos = repo.list_projects()
    repos = json.dumps(repos, indent=4)
    # write repos to file
    with open('repos.json', 'w') as f:
        f.write(repos)
    # assert by checking if repos.json exists
    assert os.path.isfile('repos.json')
