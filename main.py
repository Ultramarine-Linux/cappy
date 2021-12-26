import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gio
import os
import configparser

from cappy.windows.about import aboutWindow
class MainWindow(Gtk.ApplicationWindow):
    def __init__(self):
        # Import the window from glade
        self.builder = Gtk.Builder()
        self.builder.add_from_file("cappy/ui/main.ui")
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("main_window")
        self.window.connect("destroy", Gtk.main_quit)
        # connect action1 to GtkAboutDialog
        #self.action1.connect("activate", lambda x: self.on_action1_activate()

        # get the RepoList treeview
        RepoListView = self.builder.get_object("repoListView")

        # make a repolist
        repo_list = self.builder.get_object("repo_list")
        # repo_list is a treeview
        # make a liststore
        liststore = Gtk.ListStore(str, str, str, str)
        # add the liststore to the treeview

        self.window.show_all()
    def about_dialog(self, widget, data=None):
        aboutWindow()
    def on_addRepo_clicked(self, widget, data=None):
        print("add repo")
# start the program
# make the exit button work
if __name__ == "__main__":
    MainWindow()
    Gtk.main()