# -*- coding: utf-8 -*-

import configparser
import datetime
from ftplib import FTP
import os
import json
import zipfile
import socket
import time
import requests
from PIL import Image
import forecasts
import meteofrance
import wca
import wgov
import yahoo

CONFIGBASE = os.environ.get("HOME", "/tmp") + "/.config/weewxapp/"
CACHEBASE = os.environ.get("HOME", "/tmp") + "/.cache/weewxapp/"
# TODO: set this to /usr/share/weewxapp/
APPBASE = os.environ.get("HOME", "/tmp") + "/weeWXWeatherApp4Gtk/"

HEADERS = {}
HEADERS['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 "
HEADERS['User-Agent'] += "(KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36"

SESSION = requests.Session()
SESSION.headers = HEADERS

INIGO_VERSION = 4000

ICON_VERSION = 8
ICON_URL = "https://github.com/evilbunny2008/weeWXWeatherApp/releases/download/0.8.21/icons.zip"

def download(url):
    """ Download json string from server based on a bounding box """

    if url.startswith("http"):
        try:
            ret = SESSION.get(url)
        except Exception as error:
            return [False, str(error)]

        if ret.ok:
            if 'aemet' in url.lower():
                content = ret.content.decode('iso-8859-15').encode('utf8')
            else:
                content = ret.content

            return [True, content]

        return [False, "Failed to download " + url + ", error status: " + str(ret.status_code)]
    elif url.startswith("ftp"):
        url = url[6:]
        hostname, url = url.split('/', 1)
        url = "/" + url
        filename = os.path.basename(url)
        url = url[:-1 * len(filename)]

        ftp = FTP(hostname)
        ftp.login()
        ftp.cwd(url)

        with open(CACHEBASE + "/tempfile.txt", 'wb') as file_name:
            def callback(data):
                """ Write FTP response to localfile """
                file_name.write(data)

            ftp.retrbinary('RETR %s' % filename, callback)

        ret = read_file("/tempfile.txt", CACHEBASE)
        ret[1] = ret[1].encode("utf8")
        os.remove(CACHEBASE + "/tempfile.txt")
        return ret
    else:
        return [False, "Unknown URL handle, can't continue, url: '" + url + "'"]

def check_paths():
    """ check and make directories as needed. """

    os.makedirs(CONFIGBASE, exist_ok=True)
    os.makedirs(CACHEBASE, exist_ok=True)

def get_string(key, defval):
    """ Get key value pair from config.ini """

    check_paths()

    config = configparser.ConfigParser()
    try:
        config.read(CONFIGBASE + "/config.ini")
        val = config['DEFAULT'][key]
        if val.strip() != "":
            return val.strip()
    except Exception:
        pass

    return defval

def set_string(key, val):
    """ Save key value pair to config.ini """

    check_paths()

    config = configparser.ConfigParser()
    try:
        config.read(CONFIGBASE + "/config.ini")
        config['DEFAULT'][key] = val
        with open(CONFIGBASE + '/config.ini', 'w') as configfile:
            config.write(configfile)
        return True
    except Exception as e:
        pass

    return False

def read_file(filename, directory=CONFIGBASE):
    """ Read content from a file """

    check_paths()

    try:
        filename = directory + "/" + filename
        my_file = open(filename, "r")
        ret = my_file.read()
        try:
            ret = ret.decode('utf8')
        except Exception as error:
            pass

        my_file.close()
    except Exception as error:
        return [False, str(error)]

    return [True, ret]

def write_file(filename, mydata, directory=CONFIGBASE):
    """ save data to a file """

    check_paths()
    filename = directory + "/" + filename
    my_file = open(filename, "w")
    try:
        my_file.write(mydata)
    except TypeError:
        my_file.write(mydata.decode('utf8'))
    my_file.close()
    print("Wrote to: " + filename)

def write_binary(filename, binary, directory=CONFIGBASE):
    """ save data to a file """

    check_paths()
    filename = directory + "/" + filename
    my_file = open(filename, "wb")
    my_file.write(binary)
    my_file.close()
    print("Wrote to: " + filename)

def download_data(data_url="", force_download=False):
    """ download and save data to local file """

    if data_url is False or data_url == "":
        data_url = get_string("data_url", "")

    if data_url is False or data_url == "":
        return [False, "Data URL is not set"]

    if os.path.exists(CONFIGBASE + "/data.txt"):
        if time.time() - os.path.getmtime(CONFIGBASE + "/data.txt") > 270:
            force_download = True

    if force_download is True or not os.path.exists(CONFIGBASE + "/data.txt"):
        data = download(data_url)
        if data[0] is False:
            data[1] = str(data[1])
            return data

        if data[1] == "":
            return [False, "Failed to download data.txt from " + data_url]

        bits = data[1].decode('utf8').strip().split("|")
        if int(bits[0]) < INIGO_VERSION:
            return [False, "This app has been updated but the server you are connecting to " + \
                    "hasn't updated the Inigo Plugin for weeWX. Fields may not show up " + \
                    "properly until weeWX is updated."]

        data = ""
        del bits[0]
        for bit in bits:
            if data != "":
                data += "|"
            data += bit

        write_file("data.txt", data)
        return [True, data.encode('utf8')]

    data = read_file("data.txt")
    return [data[0], data[1].encode('utf8')]

def check_for_icons():
    """ Check to see if the icons already exists in the cache dir """

    files = ["aemet_11_g.png", "apixu_113.png", "bom1.png", "bom2clear.png", "dwd_pic_0_8.png",
             "i1.png", "met0.png", "mf_j_w1_0_n_2.png", "ms_cloudy.png", "smn_wi_cloudy.png",
             "wca00.png", "wgovbkn.jpg", "wzclear.png", "y01d.png", "yrno01d.png", 'yahoo0.gif',
             "yahoo-clear_day@2x.png"]

    for my_file in files:
        if not os.path.isfile(CACHEBASE + "/" + my_file):
            return [False, "One or more icons was missing, will download again"]

    return [True, "Icons were found and will be used."]

def get_radar(radar_url="", rad_type="", force_download=False):
    """ Get the radar image and display it """

    width = height = 0

    if radar_url == "":
        radar_url = get_string("radar_url", "")

    if rad_type == "":
        rad_type = get_string("rad_type", "")

    if radar_url == "":
        return [False, "Radar URL is not set."]

    if rad_type == "image":

        if os.path.exists(CACHEBASE + "/radar.gif"):
            if time.time() - os.path.getmtime(CACHEBASE + "/radar.gif") > 570:
                force_download = True

        if force_download is True or not os.path.exists(CACHEBASE + "/radar.gif"):
            dled = download(radar_url)
            if dled[0] is False:
                dled[1] = str(dled[1])
                return dled
            write_binary("radar.gif", dled[1], CACHEBASE)

        picture = Image.open(CACHEBASE + '/radar.gif')
        width, height = picture.size
    else:
        dled = download(radar_url)
        if dled[0] is False:
            dled[1] = str(dled[1])
            return dled

    return [True, "Radar URL was ok", width, height]

def get_forecast(forecast_url="", force_download=False):
    """ Get a forecast and display it """

    if forecast_url == "":
        forecast_url = get_string("forecast_url", "")

    if forecast_url == "":
        return [False, "Forecast URL is not set"]

    if os.path.exists(CONFIGBASE + "/forecast.txt"):
        if time.time() - os.path.getmtime(CONFIGBASE + "/forecast.txt") > 7170:
            force_download = True

    if force_download is True or not os.path.exists(CONFIGBASE + "/forecast.txt"):
        data = download(forecast_url)
        if data[0] is False:
            data[1] = str(data[1])
            return data

        if data[1].strip() == "":
            return [False, "Failed to download forecast from " + forecast_url]

        write_file("forecast.txt", data[1])

        return [True, data[1]]

    data = read_file("forecast.txt")
    return [True, data]

def process_forecast(force_download=False):
    """ Process forecast data ready to display """

    if os.path.exists(CONFIGBASE + "/forecast.txt"):
        if time.time() - os.path.getmtime(CONFIGBASE + "/forecast.txt") > 7170:
            force_download = True

    if force_download is True or not os.path.exists(CONFIGBASE + "/forecast.txt"):
        ret = get_forecast(force_download=True)
        if ret[0] is False:
            return ret

    ftime = os.path.getmtime(CONFIGBASE + "/forecast.txt")
    ftime = datetime.datetime.fromtimestamp(ftime)
    ftime = ftime.strftime("%d %b %Y %H:%M")

    data = read_file("forecast.txt")
    if data[0] is False:
        data[1] = str(data[1])
        return data

    fctype = get_string("fctype", "yahoo")

    if fctype == "yahoo":
        ret = yahoo.process_yahoo(data[1])
    elif fctype == "weatherzone":
        ret = forecasts.process_wz(data[1])
    elif fctype == "yr.no":
        ret = forecasts.process_yrno(data[1])
    elif fctype == "bom.gov.au":
        ret = forecasts.process_bom1(data[1])
    elif fctype == "wmo.int":
        ret = forecasts.process_wmo(data[1])
    elif fctype == "weather.gov":
        ret = wgov.process_wgov(data[1])
    elif fctype == "weather.gc.ca":
        ret = wca.process_wca(data[1])
    elif fctype == "weather.gc.ca-fr":
        ret = wca.process_wcafr(data[1])
    elif fctype == "metoffice.gov.uk":
        ret = forecasts.process_metoffice(data[1])
    elif fctype == "bom2":
        ret = forecasts.process_bom2(data[1])
    elif fctype == "aemet.es":
        ret = forecasts.process_aemet(data[1])
    elif fctype == "dwd.de":
        ret = forecasts.process_dwd(data[1])
    elif fctype == "metservice.com":
        ret = forecasts.process_metservice(data[1])
    elif fctype == "meteofrance.com":
        ret = meteofrance.process_mf(data[1])
    elif fctype == "darksky.net":
        ret = forecasts.process_darksky(data[1])
    elif fctype == "openweathermap.org":
        ret = forecasts.process_owm(data[1])
    elif fctype == "apixu.com":
        ret = forecasts.process_apixu(data[1])
    elif fctype == "weather.com":
        ret = forecasts.process_wcom(data[1])
    elif fctype == "met.ie":
        ret = forecasts.process_metie(data[1])
    else:
        ret = [False, "fctype is '" + fctype + "' which is invalid or not coded yet.", ""]

    if ret[0] is False:
        ret[1] = str(ret[1])

    return ret[0], ret[1], fctype, ftime, ret[2]

def refresh_forecast():
    """ Deal with refreshes from the GUI """

    ret = get_forecast()
    if ret[0] is False:
        return ret

    ret = process_forecast()
    return ret

def get_custom():
    """ Get the custom url from config """

    url = get_string('custom_url', '')
    return [True, url]

def deal_with_url(url):
    """ Split the URL into host, port and file path """

    if url.startswith("http://"):
        proto = "http"
    elif url.startswith("https://"):
        return [False, "https isn't supported atm...", "", "", ""]
    else:
        return [False, "Invalid URL for webcam, please check your settings...", "", "", ""]

    hostname, rest = url.split("://", 1)[1].split("/", 1)
    hostname, port = hostname.strip().split(":")
    rest = "/" + rest.strip()

    return [True, proto, hostname, port, rest]

def get_webcam(webcam_url="", force_download=True):
    """ download webcam image """

    width = height = 0

    if webcam_url == "":
        webcam_url = get_string('webcam_url', '')

    if webcam_url == "":
        return [False, "Webcam URL is not set"]

    if os.path.exists(CACHEBASE + "/webcam.jpg"):
        if time.time() - os.path.getmtime(CACHEBASE + "/webcam.jpg") > 270:
            force_download = True

    if force_download is True or not os.path.exists(CACHEBASE + "/webcam.jpg"):
        if webcam_url.lower().endswith('mjpg') or webcam_url.lower().endswith('mjpeg'):
            data = b""

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                ret = deal_with_url(webcam_url)
                if ret is False:
                    return ret

                print(webcam_url)
                print(ret)
                sock.connect((ret[2], int(ret[3])))
                ret[4] = 'GET ' + ret[4] + ' HTTP/1.0\r\n\r\n'
                sock.sendall(ret[4].encode('utf8'))
                data = sock.recv(1024)
                lines = data.split(b"\r\n")
                file_size = lines[len(lines) - 3].decode('utf8')
                file_size = file_size.split(':', 1)[1].strip()
                file_size = int(file_size)
                data = lines[len(lines) - 1]
                while len(data) < file_size:
                    req_size = file_size - len(data)
                    if req_size > 1024:
                        req_size = 1024
                    data += sock.recv(req_size)

                sock.close()
                write_binary('webcam.jpg', data, CACHEBASE)
                im1 = Image.open(CACHEBASE + "/webcam.jpg")
                im2 = im1.transpose(Image.ROTATE_270)
                im2.save(CACHEBASE + "/webcam.jpg")
        else:
            dled = download(webcam_url)
            if dled[0] is False:
                dled[1] = str(dled[1])
                return dled

            write_binary("webcam.jpg", dled[1], CACHEBASE)
            im1 = Image.open(CACHEBASE + "/webcam.jpg")
            im2 = im1.transpose(Image.ROTATE_270)
            im2.save(CACHEBASE + "/webcam.jpg")

    picture = Image.open(CACHEBASE + '/webcam.jpg')
    width, height = picture.size

    return [True, "Webcam URL was ok", width, height]

def get_config():
    """ open and parse the config file """

    settings_url = get_string('settings_url', 'https://example.com/weewx/inigo-settings.txt')
    indoor_readings = get_string('indoor_readings', '0')
    dark_theme = get_string('dark_theme', '0')
    metric = get_string('metric', '1')
    update_freq = get_string('update_freq', '1')
    show_radar = get_string('show_radar', '1')
    use_icons = get_string('use_icons', '0')
    saved = get_string('saved', '0')
    rad_type = get_string('rad_type', 'image')
    radar_url = get_string('radar_url', '')
    fctype = get_string('fctype', 'yahoo')
    wifidownload = get_string('wifidownload', '0')

    return [settings_url, indoor_readings, dark_theme, metric, show_radar, use_icons, saved,
            CACHEBASE, rad_type, radar_url, fctype, APPBASE, update_freq, wifidownload]

def save_config(settings_url, indoor_readings, dark_theme, metric,
                show_radar, use_icons, update_freq, wifidownload):
    """ Save config variables to ini file """

    if indoor_readings:
        indoor_readings = "1"
    else:
        indoor_readings = "0"

    if dark_theme:
        dark_theme = "1"
    else:
        dark_theme = "0"

    if metric:
        metric = "1"
    else:
        metric = "0"

    if show_radar:
        show_radar = "1"
    else:
        show_radar = "0"

    if use_icons:
        use_icons = "1"
    else:
        use_icons = "0"

    if wifidownload:
        wifidownload = "1"
    else:
        wifidownload = "0"

    if update_freq < 0 or update_freq > 5:
        update_freq = "1"
    else:
        update_freq = str(update_freq)

    set_string('settings_url', settings_url)
    set_string('indoor_readings', indoor_readings)
    set_string('dark_theme', dark_theme)
    set_string('metric', metric)
    set_string('show_radar', show_radar)
    set_string('use_icons', use_icons)
    set_string('saved', '1')
    set_string('update_freq', update_freq)
    set_string('wifidownload', wifidownload)

    olddata = get_string('data_url', '')
    oldradar = get_string('radar_url', '')
    oldforecast = get_string('forecast_url', '')
    oldwebcam = get_string('webcam_url', '')
    oldcustom = get_string('custom_url', '')

    data_url = ""
    rad_type = ""
    radar_url = ""
    fctype = "image"
    forecast_url = ""
    webcam_url = ""
    custom_url = ""

    settings = download(settings_url)
    if settings[0] is False:
        settings[1] = str(settings[1])
        return settings

    for line in settings[1].decode('utf8').strip().split("\n"):
        if line.split("=", 1)[0] == "data":
            data_url = line.split("=", 1)[1].strip()
        if line.split("=", 1)[0] == "radtype":
            rad_type = line.split("=", 1)[1].strip().lower()
        if line.split("=", 1)[0] == "radar":
            radar_url = line.split("=", 1)[1].strip()
        if line.split("=", 1)[0] == "fctype":
            fctype = line.split("=", 1)[1].strip().lower()
        if line.split("=", 1)[0] == "forecast":
            forecast_url = line.split("=", 1)[1].strip()
        if line.split("=", 1)[0] == "webcam":
            webcam_url = line.split("=", 1)[1].strip()
        if line.split("=", 1)[0] == "custom":
            custom_url = line.split("=", 1)[1].strip()

    if data_url[0] == "":
        return [False, "Data file url not found."]

    if fctype is False or fctype == "":
        fctype = "yahoo"

    if rad_type != "webpage":
        rad_type = "image"

    if data_url == "" or data_url == "https://example.com/weewx/inigo-data.txt":
        return [False, "Invalid data URL supplied. Please check the URL before trying again."]

    if data_url != olddata:
        data = download_data(data_url, True)
        if data[0] is False:
            data[1] = str(data[1])
            return data

    if radar_url != "" and radar_url != oldradar:
        ret = get_radar(radar_url, rad_type, True)
        if ret[0] is False:
            ret[1] = str(ret[1])
            return ret

    bomtown = metierev = ""
    lat = lon = "0.0"

    if forecast_url != "" and forecast_url != oldforecast:
        if fctype == "yahoo":
            if not forecast_url.startswith("http"):
                return [False, "Yahoo API recently changed, you need to update your settings."]
        elif fctype == "weatherzone":
            forecast_url = "https://rss.weatherzone.com.au/?u=12994-1285&lt=aploc&lc=" + \
                           forecast_url + "&obs=0&fc=1&warn=0"
        elif fctype == "yr.no":
            pass
        elif fctype == "bom.gov.au":
            bomtown = forecast_url.split(",", 1)[1].strip()
            forecast_url = "ftp://ftp.bom.gov.au/anon/gen/fwo/" + \
                           forecast_url.split(",", 1)[0].strip() + ".xml"
            set_string("bomtown", bomtown)
        elif fctype == "wmo.int":
            if not forecast_url.startswith("http"):
                forecast_url = "https://worldweather.wmo.int/en/json/" + forecast_url.strip() + \
                               "_en.xml"
        elif fctype == "weather.gov":
            if "?" in forecast_url:
                forecast_url = forecast_url.split("?", 1)[1]
                if "lat" not in forecast_url or "lon" not in forecast_url:
                    return [False, "Failed to get a valid url or coordinates."]

                for bit in forecast_url.split("&"):
                    if bit.startswith("lat="):
                        lat = bit[4:].strip()
                    if bit.startswith("lon="):
                        lon = bit[4:].strip()

            else:
                lat = forecast_url.split(",", 1)[0]
                lon = forecast_url.split(",", 1)[1]

            if lat == "0.0" and lon == "0.0":
                return [False, "Longitude or Latitude was not specified for weather.gov forecasts"]

            forecast_url = "https://forecast.weather.gov/MapClick.php?lat=" + lat + "&lon=" + \
                            lon + "&unit=0&lg=english&FcstType=json"
        elif fctype == "weather.gc.ca":
            pass
        elif fctype == "weather.gc.ca-fr":
            pass
        elif fctype == "metoffice.gov.uk":
            pass
        elif fctype == "bom2":
            pass
        elif fctype == "aemet.es":
            pass
        elif fctype == "dwd.de":
            pass
        elif fctype == "metservice.com":
            forecast_url = "https://www.metservice.com/publicData/localForecast" + forecast_url
        elif fctype == "meteofrance.com":
            pass
        elif fctype == "darksky.net":
            forecast_url += "?exclude=currently,minutely,hourly,alerts,flags&lang=en"
            if metric == "1":
                forecast_url += "&units=ca"
        elif fctype == "openweathermap.org":
            if metric:
                forecast_url += "&units=metric"
            else:
                forecast_url += "&units=imperial"
        elif fctype == "apixu.com":
            forecast_url += "&days=10"
        elif fctype == "weather.com":
            forecast_url = "https://api.weather.com/v2/turbo/vt1dailyForecast?apiKey=d522" + \
                           "aa97197fd864d36b418f39ebb323&format=json&geocode=" + forecast_url + \
                           "&language=en-US"
            if metric:
                forecast_url += "&units=m"
            else:
                forecast_url += "&units=e"
        elif fctype == "met.ie":
            metierev = "https://prodapi.metweb.ie/location/reverse/" + \
                       forecast_url.replace(",", "/")
            forecast_url = "https://prodapi.metweb.ie/weather/daily/" + \
                           forecast_url.replace(",", "/") + "/10"

            metierev = download(metierev)
            metierev[1] = metierev[1].decode('utf8')
            if metierev[0] is False:
                metierev[1] = str(metierev[1])
                return metierev

            jobj = json.loads(metierev[1].strip())
            metierev = jobj["city"] + ", Ireland"
            set_string("metierev", metierev)
        else:
            return [False, "Forecast type '" + fctype + "' isn't a valid option."]

        data = get_forecast(forecast_url, True)
        if data[0] is False:
            data[1] = str(data[1])
            return data

    if (fctype == "weather.gov" or fctype == "yahoo") and use_icons != "1":
        return [False, "Forecast type '" + fctype + "' needs to have icons available, " + \
                       "Please switch to using icons and try again."]

    if use_icons == "1" and \
        (check_for_icons()[0] is False or int(get_string("icon_version", 0)) < ICON_VERSION):
        binfile = download(ICON_URL)
        if not binfile[0]:
            binfile[1] = str(binfile[1])
            return binfile

        write_binary("icons.zip", binfile[1], CACHEBASE)
        zip_ref = zipfile.ZipFile(CACHEBASE + "/icons.zip", 'r')
        zip_ref.extractall(CACHEBASE + "/")
        zip_ref.close()
        set_string('icon_version', str(ICON_VERSION))

    if webcam_url != "" and webcam_url != oldwebcam:
        dled = get_webcam(webcam_url, True)
        if dled[0] is False:
            dled[1] = str(dled[1])
            return dled

    if custom_url != "" and custom_url != oldcustom:
        dled = download(custom_url)
        if dled[0] is False:
            dled[1] = str(dled[1])
            return dled

    set_string('data_url', data_url)
    set_string('rad_type', rad_type)
    set_string('radar_url', radar_url)
    set_string('fctype', fctype)
    set_string('forecast_url', forecast_url)
    set_string('webcam_url', webcam_url)
    set_string('custom_url', custom_url)

    return [True, "Everything looks a-ok...", rad_type, radar_url, fctype]

def loadCurrentConditions(iw):
    try:
        bits = download_data()[1].decode('utf8').split('|')
    except Exception as e:
        return "<div style='text-align:center;vertical-align:middle;font-size:12pt;'>Data is " + \
            "unavailable</div>"

    content = "<div style='text-align:center;font-size:20pt'>" + bits[56] + "</div><br/>"
    content += "<div style='text-align:center;font-size:12pt''>" + bits[54] + " " + bits[55]
    content += "</div>"
    content += "<table style='width:100%;border:0px;'>"
    content += "<tr><td style='font-size:36pt;text-align:right;'>" + bits[0] + bits[60] + "</td>"

    if len(bits) > 204:
        content += "<td style='font-size:" + iw + "pt;text-align:right;vertical-align:bottom;'>AT: "
        content += bits[203] + bits[60] +"</td></tr></table>"
    else:
        content += "<td>&nbsp</td></tr></table>"

    content += "<table style='width:100%;border:0px;'>"
    content += "<tr><td><i style='font-size:16pt;' class='flaticon-windy'></i></td><td>" + bits[25]
    content += bits[61] + "</td>"
    content += "<td style='text-align:right;'>" + bits[37] + bits[63]
    content += "</td><td style='text-align:right;'>"
    content += "<i style='font-size:" + iw + "pt;' class='wi wi-barometer'></i></td></tr>"

    content += "<tr><td><i style='font-size:" + iw + "pt;' class='wi wi-wind wi-towards-"
    content += bits[30].lower() + "'></i></td><td>" + bits[30] + "</td>"
    content += "<td style='text-align:right;'>" + bits[6] + bits[64]
    content += "</td><td style='text-align:right'>"
    content += "<i style='font-size:" + iw + "pt;' class='wi wi-humidity'></i></td></tr>"

    rain = bits[20] + bits[62] + " since mn"
    if len(bits) > 160 and bits[160] != "":
        rain = bits[158] + bits[62] + " since " + bits[160]

    content += "<tr><td><i style='font-size:" + iw + "pt;' class='wi wi-umbrella'></i></td><td>"
    content += rain + "</td>"
    content += "<td style='text-align:right;'>" + bits[12] + bits[60]
    content += "</td><td style='text-align:right'>"
    content += "<i style='font-size:" + str(float(iw) * 1.4)
    content += "pt;' class='wi wi-raindrop'></i></td></tr>"

    content += "<tr><td><i style='font-size:" + iw
    content += "pt;' class='flaticon-women-sunglasses'></i></td><td>"
    content += bits[45] + "UVI</td>"
    content += "<td style='text-align:right;'>" + bits[43]
    content += "W/m\u00B2</td><td style='text-align:right'>"
    content += "<i style='font-size:" + iw + "pt;' class='flaticon-women-sunglasses'></i></td></tr>"

    if len(bits) > 202 and get_string("indoor_readings", "0") == '1':
        content += "<tr><td><i style='font-size:" + iw
        content += "pt;' class='flaticon-home-page'></i></td><td>"
        content += bits[161] + bits[60] + "</td>"
        content += "<td style='text-align:right;'>" + bits[166] + bits[64]
        content += "</td><td style='text-align:right'>"
        content += "<i style='font-size:" + iw + "pt;' class='flaticon-home-page'></i></td></tr>"

    content += "</table>"

    content += "<table style='width:100%;border:0px;'>"

    content += "<tr><td><i style='font-size:" + iw + "pt;' class='wi wi-sunrise'></i></td>"
    content += "<td style='font-size:10pt'>" + bits[57] + "</td>"
    content += "<td><i style='font-size:" + iw
    content += "pt;' class='wi wi-sunset'></i></td><td style='font-size:10pt'>"
    content += bits[58] + "</td>"
    content += "<td><i style='font-size:" + iw
    content += "pt;' class='wi wi-moonrise'></i></td><td style='font-size:10pt'>"
    content += bits[47] + "</td>"
    content += "<td><i style='font-size:" + iw
    content += "pt;' class='wi wi-moonset'></i></td><td style='font-size:10pt'>"
    content += bits[48] + "</td></tr>"

    content += "</table>"

    return content

def htmlheader():
    ssheader = "<link rel='stylesheet' type='text/css' href='" + APPBASE
    ssheader += "assets/weathericons.css'>"
    ssheader += "<link rel='stylesheet' type='text/css' href='" + APPBASE
    ssheader += "assets/weathericons_wind.css'>"
    ssheader += "<link rel='stylesheet' type='text/css' href='" + APPBASE
    ssheader += "assets/flaticon.css'>"

    header = "<html><head><meta charset='utf-8'/><style>"
    header += "html { overflow: scroll; overflow-x: hidden; }"
    header += "table tbody tr td {font-size:11.5pt}</style>" + ssheader + "</head><body>"
    if get_string('dark_theme', '0') == '1':
        header = "<html><head><meta charset='utf-8'/><style>body { color: #fff; background-color:"
        header += " #000;}"
        header += "html { overflow: scroll; overflow-x: hidden; } table tbody tr td {font-size:"
        header += "12pt}</style>" + ssheader + "</head><body>"

    return header

def htmlfooter():
    return "</body></html>"

def loadForecast(iw):
    results = process_forecast()
    if results[0] == False:
        return results[1]

    fctype = results[2]
    ftime = results[3]
    desc = results[4]

    html = htmlheader()

    html += doForecastBanner(fctype, ftime, desc, True)

    i = 0
    for JsonObject in json.loads(results[1]):
        if i != 0:
            html += doForecastRow(JsonObject)
        else:
            html += "<table style='width:100%;border:0px;'>"

            if JsonObject['max'] == "&deg;C" or JsonObject['max'] == "&deg;F":
                html += "<tr><td style='width:50%;font-size:48pt;'>&nbsp;</td>"
            else:
                html += "<tr><td style='width:50%;font-size:48pt;'>" + JsonObject['max'] + "</td>"

            if get_string('use_icons', '0') == "1" and get_string('fctype', 'yahoo') != "wmo.int":
                if JsonObject['icon'][0:10] != "data:image" and JsonObject['icon'][0:4] != "http":
                    html += "<td style='width:50%;text-align:right;'><img width='80"
                    html += "pt' src='file://" + CACHEBASE + "/" + JsonObject['icon']
                    html += "'></td></tr>"
                else:
                    html += "<td style='width:50%;text-align:right;'><img width='80pt' src='"
                    html += JsonObject['icon'] + "'></td></tr>"
            else:
                html += "<td style='width:50%;text-align:right;'><i style='font-size:80pt;'"
                html += " class='" + JsonObject['icon'] + "'></i></td></tr>"

            if JsonObject['min'] == "&deg;C" or JsonObject['min'] == "&deg;F":
                html += "<tr><td style='text-align:right;16pt;' colspan='2'>"
                html += JsonObject['text'] + "</td></tr></table><br />"
            else:
                html += "<tr><td style='font-size:16pt;'>" + JsonObject['min'] + "</td>"
                html += "<td style='text-align:right;font-size:16pt;'>" + JsonObject['text']
                html += "</td></tr></table><br />"

            html += "<table style='width:100%;border:0px;'>"
        i += 1

    html += "</table>"

    html += htmlfooter()
    return html

def loadRadar1():
    ret = get_radar()
    if ret[0] == False:
        return ret[1]

    if get_string("rad_type", "image") == "image":
        html = htmlheader() + "<div style='position:absolute;top:0px;left:0px;width:100%'>" 
        html += "<img style='max-width:100%;width:1300px;' src='file://" + CACHEBASE + "/radar.gif'>"
        html += "</div>" + htmlfooter()

        return html
    
    return

def loadRadar2():
    ret = get_radar()
    if ret[0] == False:
        return ret[1]

    if get_string("rad_type", "image") == "image":
        html = htmlheader() + "<div style='position:absolute;top:300px;left:-100px;width:100%'>" 
        html += "<img style='transform:rotate(90deg);width:1300px;'"
        html += " src='file://" + CACHEBASE + "/radar.gif'>"
        html += "</div>" + htmlfooter()

        return html

    return

def doForecastBanner(fctype, ftime, desc, showHeader):
    html = ""

    if fctype == "yahoo":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/purple.png'/></div></br>"
    elif fctype == "weatherzone":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/wz.png'/></div></br>"
    elif fctype == "yr.no":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/yrno.png'/></div></br>"
    elif fctype == "bom.gov.au":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/bom.png'/></div></br>"
    elif fctype == "wmo.int":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/wmo.png'/></div></br>"
    elif fctype == "weather.gov":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/wgov.png'/></div></br>"
    elif fctype == "weather.gc.ca":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/wca.png'/></div></br>"
    elif fctype == "weather.gc.ca-fr":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/wca.png'/></div></br>"
    elif fctype == "metoffice.gov.uk":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/met.png'/></div></br>"
    elif fctype == "bom2":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/bom.png'/></div></br>"
    elif fctype == "aemet.es":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/aemet.jpg'/></div></br>"
    elif fctype == "dwd.de":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/dwd.jpg'/></div></br>"
    elif fctype == "metservice.com":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/metservice.png'/></div></br>"
    elif fctype == "meteofrance.com":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/mf.png'/></div></br>"
    elif fctype == "darksky.net":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/darksky.png'/></div></br>"
    elif fctype == "openweathermap.org":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/owm.png'/></div></br>"
    elif fctype == "apixu.com":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/apixu.png'/></div></br>"
    elif fctype == "weather.com":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/weather_com.png'/></div></br>"
    elif fctype == "met.ie":
        html = "<div style='text-align:center;'><img style='display:block;margin:0 auto;' "
        html += "height='29px' src='file://" + APPBASE + "/assets/met_ie.png'/></div></br>"
    else:
        html = "<div style='text-align:center;font-size:16pt;'>Error occured...</div><br>"

    if showHeader:
        html += "<div style='text-align:center;font-size:18pt;'>" + desc + "</div><br>"
    else:
        html += "<div style='text-align:center;font-size:12pt;'>" + ftime + "</div><br>"

    return html

def doForecastRow(JsonObject):
    html = ""
    if get_string('use_icons', '0') == "1" and get_string('fctype', 'yahoo') != "wmo.int" and \
        get_string('fctype', 'yahoo') != "darksky.net" and \
        get_string('fctype', 'yahoo') != "openweathermap.org":
        if JsonObject['icon'] is None:
            html = "<tr><td style='width:10%;vertical-align:top;' rowspan='2'>"
            html += "<i style='font-size:20pt;'>N/A</i></td>"
        elif JsonObject['icon'][0:10] != "data:image" and JsonObject['icon'][0:4] != "http":
            html = "<tr><td style='width:10%;vertical-align:top;' rowspan='2'><img width='40pt' "
            html += "src='file://" + CACHEBASE + "/" + JsonObject['icon'] + "'></td>"
        else:
            html = "<tr><td style='width:10%;vertical-align:top;' rowspan='2'><img width='40pt' "
            html += "src='file://" + CACHEBASE + "/" +  JsonObject['icon'] + "'></td>"
    else:
        html = "<tr><td style='width:10%;vertical-align:top;' rowspan='2'><i "
        html += "style='font-size:30pt;' class='" + JsonObject['icon'] + "'></i></td>"

    html += "<td style='width:80%;'><b>" + JsonObject['day'] + "</b></td>"

    if JsonObject['max'] != "&deg;C" and JsonObject['max'] != "&deg;F":
        html += "<td style='width:10%;text-align:right;vertical-align:top;'><b>"
        html += JsonObject['max'] + "</b></td></tr>"
    else:
        html += "<td style='width:10%;'><b>&nbsp;</b></td></tr>"

    if JsonObject['min'] != "&deg;C" and JsonObject['min'] != "&deg;F":
        html += "<tr><td>" + JsonObject['text'] + "</td>" + "<td style='width:10%;"
        html += "text-align:right;vertical-align:top;'>" + JsonObject['min'] + "</td></tr>"
    else:
        html += "<tr><td colspan='2'>" + JsonObject['text'] + "</td></tr>"

    html += "<tr><td colspan='2'>&nbsp;</td></tr>"

    return html

def getStats(iw):
    try:
        bits = download_data()[1].decode('utf8').split('|')
    except Exception as e:
        return "<div style='text-align:center;vertical-align:middle;" + \
                "font-size:12pt;'>Data is unavailable</div>"

    html = "<body>"

    # Today's stats

    html += "<div style='text-align:center;font-size:20pt'>" + bits[56] + "</div><br/>"
    html += "<div style='text-align:center;font-size:12pt'>" + bits[54] + " " + bits[55] + "</div>"

    html += "<div style='text-align:center;font-size:18pt;font-weight:bold;'>"
    html += "Today's Statistics</div>"
    html += "<table style='width:100%;border:0px;'>"

    html += "<tr><td><i style='font-size:" + iw + "pt;' class='flaticon-temperature'></i></td><td>"
    html += bits[3] + bits[60] + "</td><td>" + convert(bits[4])
    html += "</td><td style='text-align:right;'>" + convert(bits[2])
    html += "</td><td style='text-align:right;'>" + bits[1] + bits[60]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "pt;' class='flaticon-temperature'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + str(float(iw) * 1.4)
    html += "px;' class='wi wi-raindrop'></i></td><td>" + bits[15] + bits[60]
    html += "</td><td>" + convert(bits[16])
    html += "</td><td style='text-align:right;'>" + convert(bits[14])
    html += "</td><td style='text-align:right;'>" + bits[13] + bits[60]
    html += "</td><td style='text-align:right'><i style='font-size:" + str(float(iw) * 1.4)
    html += "pt;' class='wi wi-raindrop'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw
    html += "pt;' class='wi wi-humidity'></i></td><td>" + bits[9] + bits[64]
    html += "</td><td>" + convert(bits[10])
    html += "</td><td style='text-align:right;'>" + convert(bits[8])
    html += "</td><td style='text-align:right;'>" + bits[6] + bits[64]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "pt;' class='wi wi-humidity'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw + "pt;' class='wi wi-barometer'></i></td><td>"
    html += bits[39] + bits[63] + "</td><td>" + convert(bits[40])
    html += "</td><td style='text-align:right;'>" + convert(bits[42])
    html += "</td><td style='text-align:right;'>" + bits[41] + bits[63]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "pt;' class='wi wi-barometer'></i></td></tr>"

    if get_string('indoor_readings', '0') == "1":
        html += "<tr><td><i style='font-size:" + iw
        html += "pt;' class='flaticon-home-page'></i></td><td>" + bits[164] + bits[60]
        html += "</td><td>" + convert(bits[165])
        html += "</td><td style='text-align:right;'>" + convert(bits[163])
        html += "</td><td style='text-align:right;'>" + bits[162] + bits[60]
        html += "</td><td style='text-align:right'><i style='font-size:" + iw
        html += "pt;' class='flaticon-home-page'></i></td></tr>"

        html += "<tr><td><i style='font-size:" + iw
        html += "pt;' class='flaticon-home-page'></i></td><td>" + bits[169] + bits[64]
        html += "</td><td>" + convert(bits[170])
        html += "</td><td style='text-align:right;'>" + convert(bits[168])
        html += "</td><td style='text-align:right;'>" + bits[167] + bits[64]
        html += "</td><td style='text-align:right'><i style='font-size:" + iw
        html += "pt;' class='flaticon-home-page'></i></td></tr>"

    if len(bits) > 205 and bits[205] != "":
        html += "<tr><td><i style='font-size:" + iw
        html += "pt;' class='flaticon-women-sunglasses'></i></td><td>" + bits[205] + "UVI</td><td>"
        html += convert(bits[206])
        html += "</td><td style='text-align:right;'>" + convert(bits[208])
        html += "</td><td style='text-align:right;'>" + bits[207]
        html += "W/m\u00B2</td><td style='text-align:right'><i style='font-size:" + iw
        html += "pt;' class='flaticon-women-sunglasses'></i></td></tr>"

    rain = bits[20]
    since = "since mn"

    if len(bits) > 160 and bits[160] != "":
        rain = bits[158]

    if len(bits) > 160 and bits[158] != "" and bits[160] != "":
        since = "since " + bits[160]

    html += "<tr><td><i style='font-size:" + iw
    html += "pt;' class='flaticon-windy'></i></td><td colspan='3'>" + bits[19] + bits[61] + " "
    html += bits[32] + " " + convert(bits[33])
    html += "</td><td style='text-align:right;'>" + rain + bits[62]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "pt;' class='wi wi-umbrella'></i></td></tr>"
    html += "<tr><td colspan='4'>&nbsp;</td><td style='text-align:right;' colspan='2'>"
    html += since + "</td></tr>"

    html += "</table><br>"

    # Yesterday's stats

    html += "<div style='text-align:center;font-size:18pt;font-weight:bold;'>"
    html += "Yesterday's Statistics</div>"
    html += "<table style='width:100%;border:0px;'>"

    html += "<tr><td><i style='font-size:" + iw + "px;' class='flaticon-temperature'></i></td><td>"
    html += bits[67] + bits[60] + "</td><td>" + convert(bits[68])
    html += "</td><td style='text-align:right;'>" + convert(bits[66])
    html += "</td><td style='text-align:right;'>" + bits[65] + bits[60]
    html += "</td><td><i style='text-align:right;font-size:" + iw
    html += "px;' class='flaticon-temperature'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + str(float(iw) * 1.4)
    html += "pt;' class='wi wi-raindrop'></td><td>" + bits[78] + bits[60] + "</td><td>"
    html += convert(bits[79])
    html += "</td><td style='text-align:right;'>" + convert(bits[77])
    html += "</td><td style='text-align:right;'>" + bits[76] + bits[60]
    html += "</td><td style='text-align:right;'><i style='font-size:" + str(float(iw) * 1.4)
    html += "pt;' class='wi wi-raindrop'></td></tr>"

    html += "<tr><td><i style='font-size:" + iw + "px;' class='wi wi-humidity'></i></td><td>"
    html += bits[82] + bits[64] + "</td><td>" + convert(bits[83])
    html += "</td><td style='text-align:right;'>" + convert(bits[81])
    html += "</td><td style='text-align:right;'>" + bits[80] + bits[64]
    html += "</td><td style='text-align:right;'><i style='font-size:" + iw
    html += "px;' class='wi wi-humidity'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw + "px;' class='wi wi-barometer'></i></td><td>"
    html += bits[84] + bits[63] + "</td><td>" + convert(bits[85])
    html += "</td><td style='text-align:right;'>" + convert(bits[87])
    html += "</td><td style='text-align:right;'>" + bits[86] + bits[63]
    html += "</td><td style='text-align:right;'><i style='font-size:" + iw
    html += "px;' class='wi wi-barometer'></i></td></tr>"

    if len(bits) > 202 and get_string('indoor_readings', '0') == "1":
        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td><td>" + bits[173] + bits[60]
        html += "</td><td>" + convert(bits[174])
        html += "</td><td style='text-align:right;'>" + convert(bits[172])
        html += "</td><td style='text-align:right;'>" + bits[171] + bits[60]
        html += "</td><td style='text-align:right;'><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td></tr>"

        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td><td>" + bits[177] + bits[64]
        html += "</td><td>" + convert(bits[178])
        html += "</td><td style='text-align:right'>" + convert(bits[176])
        html += "</td><td style='text-align:right;'>" + bits[175] + bits[64]
        html += "</td><td style='text-align:right;'><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td></tr>"

    if len(bits) > 209 and bits[209] != "":
        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-women-sunglasses'></i></td><td>" + bits[209]
        html += "UVI</td><td>" + convert(bits[210])
        html += "</td><td style='text-align:right'>" + convert(bits[212])
        html += "</td><td style='text-align:right;'>" + bits[211]
        html += "W/m\u00B2</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-women-sunglasses'></i></td></tr>"

    rain = bits[21]
    since = "before mn"

    if len(bits) > 160 and bits[159] != "":
        rain = bits[159]

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='flaticon-windy'></i></td><td colspan='3'>" + bits[69] + bits[61] + " "
    html += bits[70] + " " + convert(bits[71])
    html += "</td><td style='text-align:right'>" + rain + bits[62]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-umbrella'></i></td></tr>"

    if len(bits) > 160 and bits[159] != "" and bits[160] != "":
        since = "before " + bits[160]

    html += "<tr><td colspan='4'>&nbsp;</td><td style='text-align:right' colspan='2'>"
    html += since + "</td></tr></table><br>"

    # This month's stats

    html += "<div style='text-align:center;font-size:18pt;font-weight:bold;'>"
    html += "This Month's Statistics</div>"
    html += "<table style='width:100%;border:0px;'>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='flaticon-temperature'></i></td><td>" + bits[90]
    html += bits[60] + "</td><td>" + getTime(bits[91])
    html += "</td><td style='text-align:right'>" + getTime(bits[89])
    html += "</td><td style='text-align:right'>" + bits[88] + bits[60]
    html += "</td><td style='text-align:right'><i style='font-size:"
    html += iw + "px;' class='flaticon-temperature'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + str(float(iw) * 1.4)
    html += "pt;' class='wi wi-raindrop'></td><td>" + bits[101] + bits[60] + "</td><td>"
    html += getTime(bits[102])
    html += "</td><td style='text-align:right'>" + getTime(bits[100])
    html += "</td><td style='text-align:right'>" + bits[99] + bits[60]
    html += "</td><td style='text-align:right'><i style='font-size:" + str(float(iw) * 1.4)
    html += "pt;' class='wi wi-raindrop'></td></tr>"

    html += "<tr><td><i style='font-size:" + iw + "px;' class='wi wi-humidity'></i></td><td>"
    html += bits[105] + bits[64] + "</td><td>" + getTime(bits[106])
    html += "</td><td style='text-align:right'>" + getTime(bits[104])
    html += "</td><td style='text-align:right'>" + bits[103] + bits[64]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-humidity'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw + "px;' class='wi wi-barometer'></i></td><td>"
    html += bits[107] + bits[63] + "</td><td>" + getTime(bits[108])
    html += "</td><td style='text-align:right'>" + getTime(bits[110])
    html += "</td><td style='text-align:right'>" + bits[109] + bits[63]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-barometer'></i></td></tr>"

    if len(bits) > 202 and get_string("indoor_readings", "0") == "1":
        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td><td>" + bits[181] + bits[60]
        html += "</td><td>" + getTime(bits[182])
        html += "</td><td style='text-align:right'>" + getTime(bits[180])
        html += "</td><td style='text-align:right'>" + bits[179] + bits[60]
        html += "</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td></tr>"

        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td><td>" + bits[185] + bits[64]
        html += "</td><td>" + getTime(bits[186])
        html += "</td><td style='text-align:right'>" + getTime(bits[184])
        html += "</td><td style='text-align:right'>" + bits[183] + bits[64]
        html += "</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td></tr>"

    if len(bits) > 213 and bits[213] != "":
        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-women-sunglasses'></i></td><td>" + bits[213]
        html += "UVI</td><td>" + getTime(bits[214])
        html += "</td><td style='text-align:right'>" + getTime(bits[216])
        html += "</td><td style='text-align:right'>" + bits[215]
        html += "W/m\u00B2</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-women-sunglasses'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='flaticon-windy'></i></td><td colspan='3'>" + bits[92] + bits[61]
    html += " " + bits[93] + " " + getTime(bits[94])
    html += "</td><td style='text-align:right'>" + bits[22] + bits[62]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-umbrella'></i></td></tr>"

    html += "</table><br>"

    # This years stats

    html += "<div style='text-align:center;font-size:18pt;font-weight:bold;'>"
    html += "This Year's Statistics</div>"
    html += "<table style='width:100%;border:0px;'>"

    html += "<tr><td><i style='font-size:" + iw + "px;' class='flaticon-temperature'></i></td><td>"
    html += bits[113] + bits[60] + "</td><td>" + getTime(bits[114])
    html += "</td><td style='text-align:right'>" + getTime(bits[112])
    html += "</td><td style='text-align:right'>" + bits[111] + bits[60]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='flaticon-temperature'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + str(float(iw) * 1.4)
    html += "px;' class='wi wi-raindrop'></td><td>" + bits[124] + bits[60]
    html += "</td><td>" + getTime(bits[125])
    html += "</td><td style='text-align:right'>" + getTime(bits[123])
    html += "</td><td style='text-align:right'>" + bits[122] + bits[60]
    html += "</td><td style='text-align:right'><i style='font-size:" + str(float(iw) * 1.4)
    html += "px;' class='wi wi-raindrop'></td></tr>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='wi wi-humidity'></i></td><td>" + bits[128] + bits[64]
    html += "</td><td>" + getTime(bits[129])
    html += "</td><td style='text-align:right'>" + getTime(bits[127])
    html += "</td><td style='text-align:right'>" + bits[126] + bits[64]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-humidity'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='wi wi-barometer'></i></td><td>" + bits[130] + bits[63]
    html += "</td><td>" + getTime(bits[131])
    html += "</td><td style='text-align:right'>" + getTime(bits[133])
    html += "</td><td style='text-align:right'>" + bits[132] + bits[63]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-barometer'></i></td></tr>"

    if len(bits) > 202 and get_string("indoor_readings", "0") == "1":
        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td><td>"
        html += bits[189] + bits[60] + "</td><td>" + getTime(bits[190])
        html += "</td><td style='text-align:right'>" + getTime(bits[188])
        html += "</td><td style='text-align:right'>" + bits[187] + bits[60]
        html += "</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td></tr>"

        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td><td>" + bits[193] + bits[64]
        html += "</td><td>" + getTime(bits[194])
        html += "</td><td style='text-align:right'>" + getTime(bits[192])
        html += "</td><td style='text-align:right'>" + bits[191] + bits[64]
        html += "</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td></tr>"

    if len(bits) > 217 and bits[217] != "":
        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-women-sunglasses'></i></td><td>" + bits[217]
        html += "UVI</td><td>" + getTime(bits[218])
        html += "</td><td style='text-align:right'>" + getTime(bits[220])
        html += "</td><td style='text-align:right'>" + bits[219]
        html += "W/m\u00B2</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-women-sunglasses'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='flaticon-windy'></i></td><td colspan='3'>" + bits[115] + bits[61] + " "
    html += bits[116] + " " + getTime(bits[117])
    html += "</td><td style='text-align:right'>" + bits[23] + bits[62]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-umbrella'></i></td></tr>"

    html += "</table><br>"

    # All time stats

    html += "<div style='text-align:center;font-size:18pt;font-weight:bold;'>"
    html += "All Time Statistics</div>"
    html += "<table style='width:100%;border:0px;'>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='flaticon-temperature'></i></td><td>" + bits[136] + bits[60]
    html += "</td><td>" + getTime(bits[137])
    html += "</td><td style='text-align:right'>" + getTime(bits[135])
    html += "</td><td style='text-align:right'>" + bits[134] + bits[60]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='flaticon-temperature'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + str(float(iw) * 1.4)
    html += "px;' class='wi wi-raindrop'></td><td>" + bits[147] + bits[60]
    html += "</td><td>" + getTime(bits[148])
    html += "</td><td style='text-align:right'>" + getTime(bits[146])
    html += "</td><td style='text-align:right'>" + bits[145] + bits[60]
    html += "</td><td style='text-align:right'><i style='font-size:"
    html += str(float(iw) * 1.4) + "px;' class='wi wi-raindrop'></td></tr>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='wi wi-humidity'></i></td><td>" + bits[151] + bits[64]
    html += "</td><td>" + getTime(bits[152])
    html += "</td><td style='text-align:right'>" + getTime(bits[150])
    html += "</td><td style='text-align:right'>" + bits[149] + bits[64]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-humidity'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='wi wi-barometer'></i></td><td>" + bits[153] + bits[63]
    html += "</td><td>" + getTime(bits[154])
    html += "</td><td style='text-align:right'>" + getTime(bits[156])
    html += "</td><td style='text-align:right'>" + bits[155] + bits[63]
    html += "</td><td style='text-align:right'><i style='font-size:" + iw
    html += "px;' class='wi wi-barometer'></i></td></tr>"

    if len(bits) > 202 and get_string("indoor_readings", "0") == "1":
        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td><td>" + bits[197] + bits[60]
        html += "</td><td>" + getTime(bits[198])
        html += "</td><td style='text-align:right'>" + getTime(bits[196])
        html += "</td><td style='text-align:right'>" + bits[195] + bits[60]
        html += "</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td></tr>"

        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td><td>" + bits[201] + bits[64]
        html += "</td><td>" + getTime(bits[202])
        html += "</td><td style='text-align:right'>" + getTime(bits[200])
        html += "</td><td style='text-align:right'>" + bits[199] + bits[64]
        html += "</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-home-page'></i></td></tr>"

    if len(bits) > 221 and bits[221] != "":
        html += "<tr><td><i style='font-size:" + iw
        html += "px;' class='flaticon-women-sunglasses'></i></td><td>" + bits[221]
        html += "UVI</td><td>" + getTime(bits[222])
        html += "</td><td style='text-align:right'>" + getTime(bits[224])
        html += "</td><td style='text-align:right'>" + bits[223]
        html += "W/m\u00B2</td><td style='text-align:right'><i style='font-size:" + iw
        html += "px;' class='flaticon-women-sunglasses'></i></td></tr>"

    html += "<tr><td><i style='font-size:" + iw
    html += "px;' class='flaticon-windy'></i></td><td colspan='3'>"
    html += bits[138] + bits[61] + " " + bits[139] + " " + getTime(bits[140])
    html += "</td><td style='text-align:right'>" + bits[157] + bits[62]
    html += "</td><td style='text-align:right'><i style='font-size:"
    html += iw + "px;' class='wi wi-umbrella'></i></td></tr>"

    html += "</table><br>"

    return html

def convert(cur):
    cur = cur.strip()
    if " " not in cur:
        return cur

    bits = cur.split(" ")
    if len(bits) < 2:
        return cur

    time = bits[0].strip().split(":")
    if len(time) < 3:
        return cur

    hours = int(time[0])
    mins = int(time[1])
    secs = int(time[2])
    pm = False
    if bits[1].strip().lower() == "pm":
        pm = True

    if not pm and hours == 12:
        hours = 0
    elif pm and hours != 12:
        hours = hours + 12

    return zeroPad(hours, 10) + zeroPad(mins, 10) + zeroPad(secs, 10)

def getTime(mystr):
    mystr = mystr.strip()

    if " " in mystr:
        return mystr

    return mystr.split(" ", 2)[0].strip()

def zeroPad(nr, base):
    return str(nr).zfill(2)

def getCredits():
    return """<span size="x-large">Big thanks to the <a href='http://weewx.com'>weeWX project</a>,
as this app wouldn't be possible otherwise.

Weather Icons from <a href='https://www.flaticon.com/'>FlatIcon</a> and
is licensed under <a href='http://creativecommons.org/licenses/by/3.0/'>CC 3.0 BY</a> and
<a href='https://github.com/erikflowers/weather-icons'>Weather Font</a> by Erik Flowers

Forecasts by
<a href='https://www.yahoo.com/?ilc=401'>Yahoo!</a>,
<a href='https://weatherzone.com.au'>weatherzone</a>,
<a href='https://hjelp.yr.no/hc/en-us/articles/360001940793-Free-weather-data-service-from-Yr'>yr.no</a>,
<a href='https://bom.gov.au'>Bureau of Meteorology</a>,
<a href='https://www.weather.gov'>Weather.gov</a>,
<a href='https://worldweather.wmo.int/en/home.html'>World Meteorology Organisation</a>,
<a href='https://weather.gc.ca'>Environment Canada</a>,
<a href='https://www.metoffice.gov.uk'>UK Met Office</a>,
<a href='https://www.aemet.es'>La Agencia Estatal de Meteorología</a>,
<a href='https://www.dwd.de'>Deutscher Wetterdienst</a>,
<a href='https://metservice.com'>MetService.com</a>,
<a href='https://meteofrance.com'>MeteoFrance.com</a>,
<a href='https://darksky.net'>DarkSky.net</a>

weeWX Weather App is by <a href='https://odiousapps.com'>OdiousApps</a>.</span>"""

TMP = read_file("/assets/apixu.json", APPBASE)
CONDITIONS = json.loads(TMP[1])
