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
        # get the treeview repo_list
        self.repoListView = self.builder.get_object("repoListView")

        # get the repos from all the config files from /etc/yum.repos.d
        self.repos = []
        for repo in os.listdir("/etc/yum.repos.d"):
            if repo.endswith(".repo"):
                # read the config file
                config = configparser.ConfigParser()
                config.read("/etc/yum.repos.d/" + repo)
                # the section name is the repo name, there can be multiple sections (repos)
                for section in config.sections():
                    # get the name of the repo
                    # the repo name is the section name
                    name = section
                    # try and get the baseurl
                    try:
                        baseurl = config[section]["baseurl"]
                    except KeyError:
                        # try and get the mirrorlist instead
                        try:
                            baseurl = config[section]["metalink"]
                            # escape the ampersands
                            baseurl = baseurl.replace("&", "&amp;")
                        except KeyError:
                            # if we can't get either, just skip this repo
                            continue
                    # get the enabled status, which is a 1 or 0
                    try:
                        enabled_num = config[section]["enabled"]
                        # convert to a bool
                        enabled = True if enabled_num == "1" else False
                    except KeyError:
                        enabled = False
                    # now get the priority
                    try:
                        priority = config[section]["priority"]
                    except KeyError:
                        priority = ""
                    # now that we have the name and baseurl, add it to the liststore in the treeview
                    # get the liststore
                    liststore = self.repoListView.get_model()
                    # add the row
                    liststore.append([name, baseurl, 0, enabled])

        self.window.show_all()
    def about_dialog(self, widget, data=None):
        aboutWindow()
    def on_addRepo_clicked(self, widget, data=None):
        print("add repo")
    def remove_repo(self, widget, data=None):
        # get the selected row from the liststore
        selection = self.repoListView.get_selection()
        # it's a treeview so we need to get the model and the iter
        model, iter = selection.get_selected()
        # remove the row
        model.remove(iter)
    def on_repoListView_move_cursor(self, widget, data=None):
        # get the selected row from the liststore
        selection = self.repoListView.get_selection()
        # it's a treeview so we need to get the model and the iter
        model, iter = selection.get_selected()
        # now get the config files from /etc/yum.repos.d
        for repo in os.listdir("/etc/yum.repos.d"):
            # find the section that matches the name of the repo
            if repo.endswith(".repo"):
                # read the config file
                config = configparser.ConfigParser()
                config.read("/etc/yum.repos.d/" + repo)
                # find the section that matches the name in the liststore
                for section in config.sections():
                    # if the name matches, get the baseurl
                    if section == model[iter][0]:
                        try:
                            repo_url = self.builder.get_object("repoURLEntry")
                            repo_url.set_text(config[section]["baseurl"])
                        except KeyError:
                            repo_url.set_text("")
                        try:
                            repo_meta = self.builder.get_object("repoMetaEntry")
                            repo_meta.set_text(config[section]["metalink"])
                        except KeyError:
                            repo_meta.set_text("")
                        try:
                            repo_gpgpath = self.builder.get_object("GPGEntry")
                            repo_gpgpath.set_text(config[section]["gpgkey"])
                        except KeyError:
                            repo_gpgpath.set_text("")
                        try:
                            repo_gpg = self.builder.get_object("GPGCheck")
                            # get the gpgcheck value
                            gpgcheck_val = config[section]["gpgcheck"]
                            # convert to a bool
                            gpgcheck = True if gpgcheck_val == "1" else False
                            # set the checkbox
                            repo_gpg.set_active(gpgcheck)
                        except KeyError:
                            repo_gpg.set_active(False)
                        try:
                            repo_excludes = self.builder.get_object("repoExcludeEntry")
                            repo_excludes.set_text(config[section]["exclude"])
                        except KeyError:
                            repo_excludes.set_text("")
# start the program
# make the exit button work
if __name__ == "__main__":
    MainWindow()
    Gtk.main()