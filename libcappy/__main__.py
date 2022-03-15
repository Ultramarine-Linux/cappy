from time import sleep
from tui.console import get_term_size
from tui.ui import Box, Interface, ListHdl, get_mid
from installer import Wizard

print("Press F11 to open in fullscreen.")
print("You might also need to press and hold Fn alongside.")
input("Press ENTER to get to the next screen.")

ui = Interface()
wizard = Wizard()

# x, y = get_term_size()
# box = Box(ui, 20, 60, *get_mid(y, x, 20, 60))
# ui.wait()

ui.draw("Welcome to Ultramarine Installer!", "This TUI wizard will guide you through the installation.")
ui.wait()

listhdl = ListHdl(ui)
locales = [v.split('|') for v in wizard.locales().splitlines()]
ui.draw("Select your locale", "blah blah blah")
listhdl.hdl([{"Locale": code, "Name": name} for code, name in locales])

# keyboard layout

# network/hostname (nmtui)

# disks
fields, lsblk = wizard.uniform_dict(wizard.lsblk())
ui.draw("Select a partition", "Use arrow keys to navigate and press ENTER to setup mounting")
listhdl.hdl(lsblk)

# user

# packages

# install...


