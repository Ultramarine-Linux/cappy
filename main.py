import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gio
import os
import configparser

class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Ultramarine Repository Manager")
        self.set_border_width(10)
        # make window resizable
        self.set_resizable(False)
        # set window size
        self.set_default_size(800, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        # set window icon
        # now we need to add a box to the window
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.box)
        # add header
        self.header = Gtk.HeaderBar()
        # use a GNOME style CSD header
        self.header.set_show_close_button(True)
        self.header.props.title = "Ultramarine Repository Manager"
        self.set_titlebar(self.header)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.about)
        #self.add_action(about_action)

        # add a menu dropdown
        self.menu_button = Gtk.MenuButton()
        # make the menu dropdown
        self.menu = Gio.Menu()
        # add items to the menu
        menuAbout = Gio.MenuItem.new("About", "app.about")
        self.menu.append_item(menuAbout)
        self.menu_button.set_menu_model(self.menu)
        # add the menu button to the header
        self.header.pack_end(self.menu_button)


        # The main content is a treeview
        self.treeview = Gtk.TreeView()
        self.treeview.set_hexpand(True)
        self.treeview.set_vexpand(True)
        self.treeview.set_grid_lines(Gtk.TreeViewGridLines.BOTH)
        self.box.pack_start(self.treeview, True, True, 0)
        # set sizes of the columns

        # create a liststore
        store = Gtk.ListStore(str, str, bool)
        # add some data to the liststore

        # create the TreeViewColumns to display the data
        self.treeview.set_model(store)
        self.treeview.append_column(Gtk.TreeViewColumn('Repository', Gtk.CellRendererText(), text=0))
        self.treeview.append_column(Gtk.TreeViewColumn('URL', Gtk.CellRendererText(), text=1))
        # Enabled column is a checkbox that is toggled by clicking on the column
        self.treeview.append_column(Gtk.TreeViewColumn('Enabled', Gtk.CellRendererToggle(), active=2))
        # make the column headers clickable
        self.treeview.set_headers_visible(True)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(False)
        # allow checking of checkboxes
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)


        # liststore rows in JSON format
        placeholder_repos = [
            {
                "repo": "fedora-updates",
                "url": "https://updates.ultramarine-linux.org/fedora/updates/",
                "enabled": True
            },
            {
                "repo": "fedora-updates-testing",
                "url": "https://updates.ultramarine-linux.org/fedora/updates-testing/",
                "enabled": False
            },
        ]
        # add rows to the liststore
        for repo in placeholder_repos:
            print(repo)
            store.append([repo["repo"], repo["url"], repo["enabled"]])


        # add a box to split the window in half
        self.box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.box.pack_start(self.box2, True, True, 0)

        # make another box to hold the buttons in the bottom 1/6th of the window
        self.box3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.box2.pack_start(self.box3, True, True, 0)
        # add about button to end of box3
        self.about_button = Gtk.Button(label="About")
        self.about_button.connect("clicked", lambda x: self.about())
        self.box3.pack_end(self.about_button, False, False, 0)





        self.show_all()
    def about(self):
        self.about_dialog = Gtk.AboutDialog()
        self.about_dialog.set_program_name("Ultramarine Repository Manager")
        self.about_dialog.set_version("0.1")
        self.about_dialog.set_copyright("MIT License (c) 2022")
        self.about_dialog.set_comments("A DNF configration frontend for Ultramarine Linux")
        self.about_dialog.set_website("https://ultramarine-linux.org")
        self.about_dialog.set_website_label("Website")
        self.about_dialog.set_authors(["Cappy Ishihara"])
        self.about_dialog.set_logo_icon_name("ultramarine-repo-manager")
        self.about_dialog.run()
        self.about_dialog.destroy()
        self.show_all()
# start main loop
win = MainWindow()
win.connect("delete-event", Gtk.main_quit)
Gtk.main()
