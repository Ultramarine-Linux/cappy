import libcappy.installer as installer
cfg = installer.Config('example.yml')

inst = installer.Installer('example.yml')
inst.instRoot()
inst.postInstall()