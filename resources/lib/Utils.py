# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import urllib
import urllib2
import os
import re
import time
import math
from PIL import Image
import hashlib
import ImageTags
import simplejson as json
from functools import wraps
import threading


ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
ADDON_DATA_PATH = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8"))
TILESIZE = 256
INITIAL_RESOLUTION = 2 * math.pi * 6378137 / TILESIZE  # 156543.03392804062 for tileSize 256 pixels
ORIGIN_SHIFT = 2 * math.pi * 6378137 / 2.0  # 20037508.342789244
HOME = xbmcgui.Window(10000)


def LANG(label_id):
    if 31000 <= label_id <= 33000:
        return ADDON.getLocalizedString(label_id)
    else:
        return xbmc.getLocalizedString(label_id)


def run_async(func):
    """
    Decorator to put a function into a separate thread
    """
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = threading.Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


def busy_dialog(func):
    """
    Decorator to show busy dialog while function is running
    Only one of the decorated functions may run simultaniously
    """

    def decorator(self, *args, **kwargs):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        result = func(self, *args, **kwargs)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        return result

    return decorator


def fill_list_control(listcontrol, listitem_dict):
    listcontrol.reset()
    listitems = create_listitems(listitem_dict)
    listcontrol.addItems(items=listitems)
    xbmcgui.Window(xbmcgui.getCurrentWindowId()).clearProperty("index")


def pass_dict_to_skin(data=None, prefix="", debug=False, precache=False, window=10000):
    skinwindow = xbmcgui.Window(window)
    if not data:
        return None
    for (key, value) in data.iteritems():
        value = unicode(value)
        skinwindow.setProperty('%s%s' % (prefix, str(key)), value)
        if debug:
            log('%s%s' % (prefix, str(key)) + value)


def latlon_to_meters(lat, lon):
    '''
    Converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:900913
    '''

    if not lon:
        return None
    mx = lon * ORIGIN_SHIFT / 180.0
    my = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    my = my * ORIGIN_SHIFT / 180.0
    return mx, my


def meters_to_pixels(mx, my, zoom):
    '''
    Converts EPSG:900913 to pyramid pixel coordinates in given zoom level
    '''

    res = INITIAL_RESOLUTION / (2 ** zoom)
    px = (mx + ORIGIN_SHIFT) / res
    py = (my + ORIGIN_SHIFT) / res
    return px, py


def pixels_to_meters(px, py, zoom):
    '''
    Converts pixel coordinates in given zoom level of pyramid to EPSG:900913
    '''

    res = INITIAL_RESOLUTION / (2 ** zoom)
    mx = px * res - ORIGIN_SHIFT
    my = py * res - ORIGIN_SHIFT
    return mx, my


def meters_to_latlon(mx, my):
    '''
    Converts XY point from Spherical Mercator EPSG:900913 to lat/lon in WGS84 Datum
    '''

    lon = (mx / ORIGIN_SHIFT) * 180.0
    lat = (my / ORIGIN_SHIFT) * 180.0

    lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return lat, lon


def get_string_from_url(url):
    for i in range(0, 3):
        try:
            request = urllib2.Request(url)
            request.add_header('User-agent', 'XBMC/14.2 ( phil65@kodi.tv )')
            response = urllib2.urlopen(request, timeout=3)
            return response.read()
        except:
            xbmc.sleep(500)
    notify("Error", "Could not download data. Internet connection OK?")
    log("get_string_from_url: could not get data from %s" % url)
    return ""


def get_JSON_response(url="", cache_days=0.5):
    filename = hashlib.md5(url).hexdigest()
    path = xbmc.translatePath(ADDON_DATA_PATH + "/" + filename + ".txt")
    cache_seconds = int(cache_days * 86400.0)
    log(url)
    if xbmcvfs.exists(path) and ((time.time() - os.path.getmtime(path)) < cache_seconds):
        results = read_from_file(path)
    else:
        response = get_string_from_url(url)
        results = json.loads(response)
        save_to_file(results, filename, ADDON_DATA_PATH)
    return results


def fetch_musicbrainz_id(artist, xbmc_artist_id=-1):
    base_url = "http://musicbrainz.org/ws/2/artist/?fmt=json"
    url = '&query=artist:%s' % urllib.quote_plus(artist)
    results = get_JSON_response(base_url + url, 30)
    if not results or not results["artists"]:
        return None
    log("found artist id for %s: %s" % (artist.decode("utf-8"), results["artists"][0]["id"]))
    return results["artists"][0]["id"]


def log(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDON_ID, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)


def get_images(path=""):
    pins = "&markers=color:blue"
    letter = ord('A')
    images = []
    for count, filename in enumerate(xbmcvfs.listdir(path)[-1]):
        try:
            img = Image.open(path + filename)
            exif_data = ImageTags.get_exif_data(img)
            lat, lon = ImageTags.get_lat_lon(exif_data)
            if "DateTimeOriginal" in exif_data:
                date = exif_data["DateTimeOriginal"]
            elif "DateTime" in exif_data:
                date = exif_data["DateTime"]
            else:
                date = ""
            if lat:
                props = {"name": filename,
                         "label": filename,
                         "lat": str(lat),
                         "lon": str(lon),
                         "date": date,
                         "description": date,
                         "thumb": path + filename,
                         "filepath": path + filename,
                         "index": str(count),
                         "letter": chr(letter),
                         }
                if len(pins) < 1850:
                    pins += "%7C" + str(lat) + "," + str(lon)
                    letter += 1
                images.append(props)
        except Exception as e:
            log("Error when handling get_images results")
            log(e)
    return images, pins


def string_to_deg(raw_string):
    raw_string = raw_string.strip().replace('"', '').replace("'", "")
    clean_string = raw_string[1:]
    clean_string = clean_string.replace("d", "")
    clean_string = clean_string.replace("  ", " ")
    div = '[|:|\s]'  # allowable field delimiters "|", ":", whitespace
    sdec = '(\d{1,3})' + div + '(\d{1,2})' + div + '(\d{1,2}\.?\d+?)'
    co_re = re.compile(sdec)
    co_search = co_re.search(clean_string)
    if co_search is None:
        raise ValueError("Invalid input string: %s" % raw_string)
    elems = co_search.groups()
    dec_degrees = float(elems[0]) + float(elems[1]) / 60.0 + float(elems[2]) / 3600.0
    if raw_string[0].lower() == "w" or raw_string[0].lower() == "s":
        dec_degrees = -1.0 * dec_degrees
    return float(dec_degrees)


def parse_geotags(lat, lon):
    if lon:
        lat = string_to_deg(lat)
        lon = string_to_deg(lon)
    else:
        coords = lat.split(",lon=")
        lat = string_to_deg(coords[0])
        lon = string_to_deg(coords[1])
    return lat, lon


def create_listitems(data):
    if not data:
        return []
    items = []
    for (count, result) in enumerate(data):
        listitem = xbmcgui.ListItem('%s' % (str(count)))
        for (key, value) in result.iteritems():
            if str(key).lower() in ["name", "label", "title"]:
                listitem.setLabel(unicode(value))
            if str(key).lower() in ["thumb"]:
                listitem.setThumbnailImage(unicode(value))
            if str(key).lower() in ["icon"]:
                listitem.setIconImage(unicode(value))
            if str(key).lower() in ["thumb", "poster", "banner", "fanart"]:
                listitem.setArt({str(key).lower(): unicode(value)})
            if str(key).lower() in ["path"]:
                listitem.setPath(path=unicode(value))
            listitem.setProperty('%s' % (str(key)), unicode(value))
        items.append(listitem)
    return items


def get_location_coords():
    # url = 'https://www.telize.com/geoip'
    response = get_string_from_url('http://ip-api.com/json')
    if not response:
        return "", ""
    results = json.loads(response)
    return results["lat"], results["lon"]


def save_to_file(content, filename, path=""):
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdir(path)
    text_file_path = os.path.join(path, filename + ".txt")
    log("save to textfile:")
    log(text_file_path)
    text_file = xbmcvfs.File(text_file_path, "w")
    json.dump(content, text_file)
    text_file.close()
    return True


def read_from_file(path=""):
    # Check to see if file exists
    if xbmcvfs.exists(path):
        f = open(path)
        fc = json.load(f)
        log("loaded textfile " + path)
        try:
            return fc
        except:
            notify("Exception in read_from_file()")
            return []
    else:
        return False


def cleanText(text):
    if text:
        text = re.sub('<br \/>', '[CR]', text)
        text = re.sub('<br\/>', '[CR]', text)
        text = re.sub('<(.|\n|\r)*?>', '', text)
        text = re.sub('&quot;', '"', text)
        text = re.sub('<*>', '', text)
        text = re.sub('&amp;', '&', text)
        text = re.sub('&gt;', '>', text)
        text = re.sub('&lt;', '<', text)
        text = re.sub('&#;', "'", text)
        text = re.sub('&#39;', "'", text)
        text = re.sub('<i>', '[I]', text)
        text = re.sub('<\/i>', '[/I]', text)
        text = re.sub('<strong>', '[B]', text)
        text = re.sub('<\/strong>', '[/B]', text)
        text = re.sub('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.', '', text)
        return text.strip()
    else:
        return ""


class PictureDialog(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    C_ARTIST_LIST = 500

    def __init__(self, *args, **kwargs):
        self.picture_path = kwargs.get('picture_path')

    def onInit(self):
        self.getControl(100).setImage(self.picture_path)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlID):
        pass

    def onFocus(self, controlID):
        pass


def notify(header="", message="", icon=ADDON_ICON, time=5000, sound=True):
    xbmcgui.Dialog().notification(heading=header, message=message, icon=icon, time=time, sound=sound)


def prettyprint(string):
    log(json.dumps(string, sort_keys=True, indent=4, separators=(',', ': ')))