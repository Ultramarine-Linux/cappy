from importlib.metadata import entry_points
import os
import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install

# LibCappy, a DNF-based system configuration library for Ultramarine Linux.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

# Get the long description from the README file
with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

class BuildRust(install):
    """
    Build the embedded Rust library.
    """
    def run(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(dir_path, 'libcappy', 'parse_locales')
        install.run(self)
        # get --root option from install command
        root = self.get_finalized_command('install').root
        if root is None:
            root = '/usr'
        subprocess.run(['cargo', 'install', '--path', path, '--root', root])
        # clean up crates file
        subprocess.run(['rm', '-f', os.path.join(root, '.crates.toml'), os.path.join(root, '.crates2.json')])
setup(
    name='libcappy',
    version='0.1.0',
    description='A DNF-based system configuration library for Ultramarine Linux.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='ultramarine-linux.org',
    author='Cappy Ishihara',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers :: System Administrators :: End Users/Desktop',
        'Topic :: Utilities :: System :: Installation/Setup',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.10',
        'Operating System :: POSIX :: Linux',
    ],
    keywords='dnf yast system-configuration configuration-management',
    packages=find_packages(),
    install_requires=[
        'dnf',
        'pyyaml',
        'requests',
        'urllib3',
        'dnf-plugins-core',
    ],
    entry_points = {
        'console_scripts': [
            'cappy = libcappy.cli.__main__:main',
            'ultramarine-install-tui = libcappy.__main__:main',
        ]
    },
    cmdclass={
        'install': BuildRust,
    },
    package_data={
        "libcappy.templates": ["grub.cfg"]
    },
)
