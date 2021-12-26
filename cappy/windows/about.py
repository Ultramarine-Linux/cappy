import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gio


class aboutWindow():
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("cappy/ui/about.ui")
        self.window = self.builder.get_object("about_dialog")
        self.window.show_all()

if __name__ == "__main__":
    aboutWindow()
    Gtk.main()