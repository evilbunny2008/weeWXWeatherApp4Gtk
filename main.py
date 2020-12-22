#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import gi
import common

gi.require_version('Gtk', "3.0")
gi.require_version('WebKit2', '4.0')
gi.require_version('Handy', '0.0')

from gi.repository import Gtk, Gio
from gi.repository import WebKit2 as Webkit
from gi.repository import Handy

Handy.init()

INTERVALS = ["Manual Updates",
             "Every 5 Minutes",
             "Every 10 Minutes",
             "Every 15 Minutes",
             "Every 30 Minutes",
             "Every Hour"]

settings_url = "https://example.com/weewx/inigo-settings.txt"
indoor_readings = "0"
dark_theme = "0"
use_metric = "1"
show_radar = "1"
use_icons = "0"
saved = "0"
htmlheader = ""
ssheader = ""
htmlfooter = "</body></html>"
cachebase = "/tmp"
rad_type = "image"
radar_url = ""
fctype = "yahoo"
app_dir = ""
update_freq = "1"
wifidownload = "0"

class aboutScreen(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self, title="Test", application=app)
        self.set_default_size(400, 600)

        header = Gtk.HeaderBar(title="About weeWx Weather App")
        header.set_show_close_button(False)

        button = Gtk.Button(label="<")
        button.connect("clicked", self.on_button_clicked) 
        header.pack_start(button)

        self.set_titlebar(header)

        label = Gtk.Label()
        label.set_markup(common.getCredits())
        self.add(label)

    def on_button_clicked(self, widget):
        self.destroy()

class settingsScreen(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self, title="weeWx App Settings", application=app)
        self.set_default_size(400, 600)

        header = Gtk.HeaderBar(title="weeWx App Settings")
        header.set_show_close_button(False)

        button = Gtk.Button(label="<")
        button.connect("clicked", self.on_button_clicked) 
        header.pack_start(button)

        save_button = Gtk.Button(label="Save")
        save_button.connect("clicked", self.on_save_button_clicked)

        header.pack_end(save_button)

        self.set_titlebar(header)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.add(vbox)

        label = Gtk.Label(label="Enter the URL to your settings.txt file")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(label, False, True, 0)

        vbox.pack_start(hbox, False, True, 0)

        self.url = Gtk.Entry()
        self.url.set_text(settings_url)
        vbox.pack_start(self.url, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Show Indoor Readings?")
        hbox.pack_start(label, False, False, 0)

        self.indoor = Gtk.Switch()
        if indoor_readings == "1":
            self.indoor.set_active(True)
        hbox.pack_end(self.indoor, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Use Dark Theme? (requires restart)")
        hbox.pack_start(label, False, False, 0)

        self.dark_theme = Gtk.Switch()
        if dark_theme == "1":
            self.dark_theme.set_active(True)
        hbox.pack_end(self.dark_theme, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Use Metric in Forecasts?")
        hbox.pack_start(label, False, False, 0)

        self.metric = Gtk.Switch()
        if use_metric == "1":
            self.metric.set_active(True)
        hbox.pack_end(self.metric, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Use icons instead of glyphs?")
        hbox.pack_start(label, False, False, 0)

        self.icons = Gtk.Switch()
        if use_icons == "1":
            self.icons.set_active(True)
        hbox.pack_end(self.icons, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Only update on Wifi?")
        hbox.pack_start(label, False, False, 0)

        self.wifi = Gtk.Switch()
        if wifidownload == "1":
            self.wifi.set_active(True)
        hbox.pack_end(self.wifi, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Update Frequency:")
        hbox.pack_start(label, False, False, 0)

        self.interval = Gtk.ComboBoxText()
        self.interval.set_entry_text_column(0)
        for interval in INTERVALS:
            self.interval.append_text(interval)

        self.interval.set_active(int(update_freq))
        hbox.pack_end(self.interval, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Radar on Main Screen")
        hbox.pack_start(label, False, False, 0)

        self.radar = Gtk.RadioButton.new_with_label_from_widget(None, "Show Radar")
        vbox.pack_start(self.radar, False, False, 0)

        self.forecast = Gtk.RadioButton.new_with_label_from_widget(self.radar, "Show Forecast")
        vbox.pack_start(self.forecast, False, False, 0)

        if show_radar == "0":
            self.forecast.set_active(True)

    def on_button_clicked(self, widget):
        self.destroy()

    def on_save_button_clicked(self, widget):
        url = self.url.get_text()
        indoor = self.indoor.get_active()
        dark = self.dark_theme.get_active()
        metric = self.metric.get_active()
        radar = self.radar.get_active()
        icons = self.icons.get_active()
        wifi = self.wifi.get_active()
        update = self.interval.get_active()

        ret = common.save_config(url, indoor, dark, metric, radar, icons, update, wifi)
        if ret[0] == False:
            # TODO: notify user about ret[1] and skip saving
            return

        saved = '1'
        settings_url = url
        if indoor:
            indoor_readings = '1'
        else:
            indoor_readings = '0'
        if dark:
            dark_theme = '1'
        else:
            dark_theme = '0'
        if metric:
            use_metric = '1'
        else:
            use_metric = '0'
        if radar:
            show_radar = '1'
        else:
            show_radar = '0'
        if icons:
            use_icons = '1'
        else:
            use_icons = '0'
        update_freq = str(update)
        if wifi:
            wifidownload = '1'
        else:
            wifidownload = '0'

        rad_type = ret[2]
        radar_url = ret[3]
        fctype = ret[4]

        self.destroy()

# https://developer.gnome.org/gnome-devel-demos/unstable/menubutton.py.html.en
# https://www.youtube.com/watch?v=10C-vihKDLs
class mainScreen(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self, title="weeWX App", application=app)
        self.set_default_size(400, 600)

        iw = "18"
        base_uri = "file:///"

        htmlheader = common.htmlheader()
        htmlfooter = common.htmlfooter()

        content = htmlheader
        content += "<div style='text-align:center;vertical-align:middle;font-size:12pt;'>"
        content += "Data is still loading.</div>" + htmlfooter

        header = Gtk.HeaderBar(title="weeWX App")
        header.set_show_close_button(False)

        button = Gtk.MenuButton()
        header.pack_end(button)

        menumodel = Gio.Menu()
        menumodel.append("Settings", "win.settings")
        menumodel.append("About", "win.about")
        menumodel.append("Quit", "win.quit")
        button.set_menu_model(menumodel)

        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self.settings_callback)
        self.add_action(settings_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.about_callback)
        self.add_action(about_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.quit_callback)
        self.add_action(quit_action)

        self.set_titlebar(header)
        # header.set_subtitle("Sample FlowBox app")

        hbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.webview1 = Webkit.WebView()
        self.webview1.load_html(content, base_uri)

        self.webview2 = Webkit.WebView()
        self.webview2.load_html(content, base_uri)

        self.webview3 = Webkit.WebView()
        self.webview3.load_html(content, base_uri)

        hbox1.pack_start(self.webview1, True, True, 0)
        hbox1.pack_start(self.webview2, True, True, 0)

        content = common.loadCurrentConditions(iw)
        content = htmlheader + content + htmlfooter
        self.webview1.load_html(content, base_uri)

        if show_radar == '1':
            content = common.loadRadar()
        else:
            content = common.loadForecast(iw)

        content = htmlheader + content + htmlfooter
        self.webview2.load_html(content, base_uri)

        content = htmlheader + common.getStats(iw) + htmlfooter
        self.webview3.load_html(content, base_uri)

        hbox2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox2.pack_start(self.webview3, True, True, 0)

        hbox3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox4 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox5 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.wlabel = Gtk.Label(label="Weather")
        self.slabel = Gtk.Label(label="Stats")
        self.frlabel = Gtk.Label(label="Forecast")
        if show_radar == '0':
            self.frlabel.set_label("Radar")
        self.wclabel = Gtk.Label(label="Webcam")
        self.clabel = Gtk.Label(label="Custom")

        self.notebook.append_page(hbox1, self.wlabel)
        self.notebook.append_page(hbox2, self.slabel)
        self.notebook.append_page(hbox3, self.frlabel)
        self.notebook.append_page(hbox4, self.wclabel)
        self.notebook.append_page(hbox5, self.clabel)
        self.add(self.notebook)

    # callback functions for the actions related to the application
    def settings_callback(self, action, parameter):
        settings = settingsScreen(app)
        settings.show_all()

    def about_callback(self, action, parameter):
        about = aboutScreen(app)
        about.show_all()

    def quit_callback(self, action, parameter):
        app.quit()

class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self)

    def do_activate(self):
        win = mainScreen(self)
        win.show_all()
        if saved == '0':
            settings = settingsScreen(self)
            settings.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)

if __name__ == "__main__":
    ret = common.get_config()
    settings_url = ret[0]
    indoor_readings = ret[1]
    dark_theme = ret[2]
    use_metric = ret[3]
    show_radar = ret[4]
    use_icons = ret[5]
    saved = ret[6]
    cachebase = ret[7]
    rad_type = ret[8]
    radar_url = ret[9]
    fctype = ret[10]
    app_dir = ret[11]
    update_freq = ret[12]
    wifidownload = ret[13]
    app = Application()
    app.run()
