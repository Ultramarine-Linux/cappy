import pytest
import subprocess
def test_pkg():
    import libcappy.packages as packages
    pkgs = packages.Packages()
    pkgs.install(['powertop'])
    # assert by checking dnf if powertop is installed
    assert subprocess.check_output([
        'dnf',
        '--quiet',
        'list',
        'powertop'
    ])

