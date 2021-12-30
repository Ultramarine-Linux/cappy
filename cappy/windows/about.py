import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gio


class aboutWindow():
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("cappy/ui/about.ui")
        self.window = self.builder.get_object("about_dialog")
        buttons = self.builder.get_object("buttons")
        buttons.foreach(self.conf_close_button)
        self.builder.connect_signals(self)
        self.window.show_all()


    def conf_close_button(self, button):
        if button.props.label == "_Close":
            button.connect("clicked", lambda _: self.window.destroy())
        if button.props.label == "_License":
            button.destroy()

if __name__ == "__main__":
    aboutWindow()
    Gtk.main()
