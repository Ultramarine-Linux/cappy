import pytest
import subprocess
def test_installer():
    import libcappy.installer as installer
    inst = installer.Installer(config='tests/test_config.yml')
    inst.instRoot()
    inst.postInstall
    # assert that the install worked by running systemd-nspawn and checking if it's running
    # run as root
    assert subprocess.check_output([
        'sudo',
        'systemd-nspawn',
        '--quiet',
        '-D',
        'chroot',
        'echo "Hello World"'
    ])