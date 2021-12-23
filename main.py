import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gio
import os
import configparser

class MainWindow(Gtk.Window):
    def __init__(self):
        # Import the window from glade
        self.builder = Gtk.Builder()
        self.builder.add_from_file("main.glade")
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("main_window")
        self.window.connect("destroy", Gtk.main_quit)
        # connect action1 to GtkAboutDialog
        #self.action1.connect("activate", lambda x: self.on_action1_activate())
        self.window.show_all()
    def on_action1_activate(self, widget):
        # activate the aboiut dialog
        about = self.builder.get_object("about_dialog")
        #self.action1 = self.builder.get_object("action1")
        about.connect("destroy", lambda x: about.destroy())
        about.run()
        about.show()

# start the program
# make the exit button work
if __name__ == "__main__":
    MainWindow()
    Gtk.main()