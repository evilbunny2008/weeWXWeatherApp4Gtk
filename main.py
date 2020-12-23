#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import gi
import common

gi.require_version('Gtk', "3.0")
gi.require_version('WebKit2', '4.0')
gi.require_version('Handy', '0.0')

from gi.repository import Gtk, Gio, GLib, GObject
from gi.repository import WebKit2 as Webkit
from gi.repository import Handy

Handy.init()

INTERVALS = ["Manual Updates",
             "Every 5 Minutes",
             "Every 10 Minutes",
             "Every 15 Minutes",
             "Every 30 Minutes",
             "Every Hour"]

iw = "18"
base_uri = "file:///"

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
        self.url.set_text(common.get_string("settings_url", ""))
        vbox.pack_start(self.url, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Show Indoor Readings?")
        hbox.pack_start(label, False, False, 0)

        self.indoor = Gtk.Switch()
        if common.get_string("indoor_readings", "0") == "1":
            self.indoor.set_active(True)
        hbox.pack_end(self.indoor, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Use Dark Theme? (requires restart)")
        hbox.pack_start(label, False, False, 0)

        self.dark_theme = Gtk.Switch()
        if common.get_string("dark_theme", "0") == "1":
            self.dark_theme.set_active(True)
        hbox.pack_end(self.dark_theme, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Use Metric in Forecasts?")
        hbox.pack_start(label, False, False, 0)

        self.metric = Gtk.Switch()
        if common.get_string("use_metric", "1") == "1":
            self.metric.set_active(True)
        hbox.pack_end(self.metric, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Use icons instead of glyphs?")
        hbox.pack_start(label, False, False, 0)

        self.icons = Gtk.Switch()
        if common.get_string("use_icons", "0") == "1":
            self.icons.set_active(True)
        hbox.pack_end(self.icons, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Only update on Wifi?")
        hbox.pack_start(label, False, False, 0)

        self.wifi = Gtk.Switch()
        if common.get_string("wifidownload", "0") == "1":
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

        self.interval.set_active(int(common.get_string("update_freq", "1")))
        hbox.pack_end(self.interval, False, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        label = Gtk.Label(label="Radar on Main Screen")
        hbox.pack_start(label, False, False, 0)

        self.radar = Gtk.RadioButton.new_with_label_from_widget(None, "Show Radar")
        vbox.pack_start(self.radar, False, False, 0)

        self.forecast = Gtk.RadioButton.new_with_label_from_widget(self.radar, "Show Forecast")
        vbox.pack_start(self.forecast, False, False, 0)

        if common.get_string("show_radar", "1") == "0":
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
        if ret[0] is False:
            return ret[1]

        app.win.refresh_data()

        self.destroy()

# https://developer.gnome.org/gnome-devel-demos/unstable/menubutton.py.html.en
# https://www.youtube.com/watch?v=10C-vihKDLs
class mainScreen(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self, title="weeWX App", application=app)
        self.set_default_size(400, 600)

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
        # header.set_subtitle("Sample app")

        self.webview1 = Webkit.WebView()
        self.webview1.load_html(content, base_uri)

        self.webview2 = Webkit.WebView()
        self.webview2.load_html(content, base_uri)

        self.webview3 = Webkit.WebView()
        self.webview3.load_html(content, base_uri)

        self.webview4 = Webkit.WebView()
        self.webview4.load_html(content, base_uri)

        self.webview5 = Webkit.WebView()
        self.webview5.load_html(content, base_uri)

        self.webview6 = Webkit.WebView()
        self.webview6.load_html(content, base_uri)

        hbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox1.pack_start(self.webview1, True, True, 0)
        hbox1.pack_start(self.webview2, True, True, 0)

        hbox2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox2.pack_start(self.webview3, True, True, 0)

        hbox3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox3.pack_start(self.webview4, True, True, 0)

        hbox4 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox4.pack_start(self.webview5, True, True, 0)

        hbox5 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox5.pack_start(self.webview6, True, True, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.wlabel = Gtk.Label(label="Weather")
        self.slabel = Gtk.Label(label="Stats")
        self.frlabel = Gtk.Label(label="Forecast")
        if common.get_string("show_radar", "1") == '0':
            self.frlabel.set_label("Radar")
        self.wclabel = Gtk.Label(label="Webcam")
        self.clabel = Gtk.Label(label="Custom")

        self.notebook.append_page(hbox1, self.wlabel)
        self.notebook.append_page(hbox2, self.slabel)
        self.notebook.append_page(hbox3, self.frlabel)
        self.notebook.append_page(hbox4, self.wclabel)
        self.notebook.append_page(hbox5, self.clabel)
        self.add(self.notebook)
        self.refresh_data()

    def refresh_data(self):
        update_freq = int(common.get_string("update_freq", "1"))
        if update_freq == 0:
            timer = 0
        elif update_freq == 2:
            timer = 600000
        elif update_freq == 3:
            timer = 900000
        elif update_freq == 4:
            timer = 1800000
        elif update_freq == 5:
            timer = 3600000
        else:
            timer = 300000

        if timer > 0:
            GLib.timeout_add(timer, self.refresh_data)

        show_radar = common.get_string("show_radar", "1")
        rad_type = common.get_string("rad_type", "image")
        radar_url = common.get_string("radar_url", "")
        custom_url = common.get_string("custom_url", "")

        content = common.loadCurrentConditions(iw)
        content = common.htmlheader() + content + common.htmlfooter()
        self.webview1.load_html(content, base_uri)

        if show_radar == "1" and rad_type == "image":
            content = common.loadRadar1()
            self.webview2.load_html(content, base_uri)
        elif show_radar == "1" and rad_type != "image":
            self.webview2.load_uri(radar_url)
        else:
            content = common.loadForecast()
            self.webview2.load_html(content, base_uri)

        content = common.htmlheader() + common.getStats(iw) + common.htmlfooter()
        self.webview3.load_html(content, base_uri)

        if show_radar == "0" and rad_type == "image":
            content = common.loadRadar2()
            self.webview4.load_html(content, base_uri)
        elif show_radar == "0" and rad_type != "image":
            self.webview4.load_uri(radar_url)
        else:
            content = common.loadForecast()
            self.webview4.load_html(content, base_uri)

        ret = common.webcam()
        self.webview5.load_html(ret, base_uri)

        if custom_url != "":
            self.webview6.load_uri(custom_url)

    def custom_signal1_method(self, *args):
        print('Custom signal')
        print(args)

    # callback functions for the actions related to the application
    def settings_callback(self, action, parameter):
        self.settings = settingsScreen(app)
        self.settings.show_all()

    def about_callback(self, action, parameter):
        about = aboutScreen(app)
        about.show_all()

    def quit_callback(self, action, parameter):
        app.quit()

class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self)

    def do_activate(self):
        self.win = mainScreen(self)
        self.win.show_all()
        if common.get_string("saved", "0") == '0':
            self.settings = settingsScreen(self)
            self.settings.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)

if __name__ == "__main__":
    app = Application()
    app.run()
