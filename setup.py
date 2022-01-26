from importlib.metadata import entry_points
import os
from setuptools import setup, find_packages

# LibCappy, a DNF-based system configuration library for Ultramarine Linux.
# Copyright (C) 2022 Cappy Ishihara and contributors under the MIT License.

# Get the long description from the README file
with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

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
        ]
    }
)
