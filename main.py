import gi

gi.require_version("Gtk", "3.0")
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
        self.loadRepoList()

        self.window.show_all()
    def loadRepoList(self=None,widget=None,data=None):
        # get the treeview repo_list
        self.repoListView = self.builder.get_object("repoListView")
        # clear all the entries in the treeview
        liststore = self.repoListView.get_model()
        liststore.clear()

        # get the repos from all the config files from /etc/yum.repos.d
        self.repos = []
        for repo in os.listdir("/etc/yum.repos.d"):
            if repo.endswith(".repo"):
                # get the liststore
                liststore = self.repoListView.get_model()
                # read the config file
                config = configparser.ConfigParser()
                config.read("/etc/yum.repos.d/" + repo)
                # the section name is the repo name, there can be multiple sections (repos)
                for id in config.sections():
                    # get name
                    try:
                        name = config[id]["name"]
                    except KeyError:
                        continue  # skip
                    # get baseurl
                    try:
                        baseurl = config[id]["baseurl"]
                    except KeyError:
                        # try and get the mirrorlist instead
                        try:
                            baseurl = config[id]["metalink"]
                            # escape the ampersands
                            baseurl = baseurl.replace("&", "&amp;")
                        except KeyError:
                            # if we can't get either, just skip this repo
                            continue
                    # get the enabled status, which is a 1 or 0
                    try:
                        enabled_num = config[id]["enabled"]
                        # convert to a bool
                        enabled = enabled_num == "1"
                    except KeyError:
                        enabled = False
                    # now get the priority
                    try:
                        priority = int(config[id]["priority"])
                    except KeyError:
                        priority = 0
                    # now that we have the name and baseurl, add it to the liststore in the treeview
                    liststore.append([id, name, baseurl, priority, enabled])

        self.window.show_all()

    def about_dialog(self, widget, data=None):
        aboutWindow()

    def on_addRepo_clicked(self, widget, data=None):
        url = self.builder.get_object("repoURLEntry").props.text
        name = self.builder.get_object("repoNameEntry").props.text
        excl = self.builder.get_object("repoExcludeEntry").props.text
        meta = self.builder.get_object("repoMetaEntry").props.text
        gpg = self.builder.get_object("GPGEntry").props.text
        check = self.builder.get_object("GPGCheck").props.active

        if not (url and name):
            return  # or err msg

        newcfg = {
            name: {  # TODO: id instead of name????
                "name": name,
                "baseurl": url,
                "metalink": meta,
                "gpgkey": gpg,
                "gpgcheck": check,
                "exclude": excl
            }
        }

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
                for id in config.sections():
                    # if the id matches, get the baseurl
                    if id == model[iter][0]:
                        try:
                            repo_name = self.builder.get_object("repoNameEntry")
                            repo_name.set_text(config[id]["name"])
                        except KeyError:
                            repo_url.set_text("")
                        try:
                            repo_url = self.builder.get_object("repoURLEntry")
                            repo_url.set_text(config[id]["baseurl"])
                        except KeyError:
                            repo_url.set_text("")
                        try:
                            repo_meta = self.builder.get_object("repoMetaEntry")
                            repo_meta.set_text(config[id]["metalink"])
                        except KeyError:
                            repo_meta.set_text("")
                        try:
                            repo_gpgpath = self.builder.get_object("GPGEntry")
                            repo_gpgpath.set_text(config[id]["gpgkey"])
                        except KeyError:
                            repo_gpgpath.set_text("")
                        try:
                            repo_gpg = self.builder.get_object("GPGCheck")
                            # get the gpgcheck value
                            gpgcheck_val = config[id]["gpgcheck"]
                            # convert to a bool
                            gpgcheck = gpgcheck_val == "1"
                            # set the checkbox
                            repo_gpg.set_active(gpgcheck)
                        except KeyError:
                            repo_gpg.set_active(False)
                        try:
                            repo_excludes = self.builder.get_object("repoExcludeEntry")
                            repo_excludes.set_text(config[id]["exclude"])
                        except KeyError:
                            repo_excludes.set_text("")


# start the program
# make the exit button work
if __name__ == "__main__":
    MainWindow()
    Gtk.main()
