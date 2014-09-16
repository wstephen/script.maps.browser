#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2014 Philipp Temminghoff (philipptemminghoff@gmail.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#


    # code for FourSquare scraping based on script.maps by a.a.alsaleh. credits to him.

import xbmc
import xbmcaddon
import xbmcgui
import urllib
from Utils import *
from LastFM import LastFM
from Eventful import Eventful
from MapQuest import MapQuest
from GooglePlaces import GooglePlaces
from FourSquare import FourSquare
from math import sin, cos, radians, pow
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__language__ = __addon__.getLocalizedString
__addonpath__ = __addon__.getAddonInfo('path')


addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
addon_name = addon.getAddonInfo('name')
googlemaps_key_normal = 'AIzaSyBESfDvQgWtWLkNiOYXdrA9aU-2hv_eprY'
googlemaps_key_streetview = 'AIzaSyCo31ElCssn5GfH2eHXHABR3zu0XiALCc4'


class GUI(xbmcgui.WindowXML):
    CONTROL_SEARCH = 101
    CONTROL_STREET_VIEW = 102
    CONTROL_ZOOM_IN = 103
    CONTROL_ZOOM_OUT = 104
    CONTROL_MODE_ROADMAP = 105
    CONTROL_MODE_HYBRID = 106
    CONTROL_MODE_SATELLITE = 107
    CONTROL_MODE_TERRAIN = 108
    CONTROL_MAP_IMAGE = 109
    CONTROL_STREETVIEW_IMAGE = 110
    CONTROL_GOTO_PLACE = 111
    CONTROL_SELECT_PROVIDER = 112
    CONTROL_LEFT = 120
    CONTROL_RIGHT = 121
    CONTROL_UP = 122
    CONTROL_DOWN = 123
    CONTROL_LOOK_UP = 124
    CONTROL_LOOK_DOWN = 125
    CONTROL_PLACES_LIST = 200
    CONTROL_MODE_TOGGLE = 126

    ACTION_CONTEXT_MENU = [117]
    ACTION_OSD = [122]
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    ACTION_SHOW_INFO = [11]
    ACTION_EXIT_SCRIPT = [13]
    ACTION_DOWN = [4]
    ACTION_UP = [3]
    ACTION_LEFT = [1]
    ACTION_RIGHT = [2]
    ACTION_0 = [58, 18]
    ACTION_PLAY = [79]
    ACTION_SELECT_ITEM = [7]

    def __init__(self, skin_file, addon_path):
        log('__init__')

    def onInit(self, startGUI=True):
        log('onInit')
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        itemlist = []
        self.init_vars()
        log("WindowID:" + str(xbmcgui.getCurrentWindowId()))
        self.window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        log("window = " + str(self.window))
        setWindowProperty(self.window, 'NavMode', '')
        setWindowProperty(self.window, 'streetview', '')
        if __addon__.getSetting("VenueLayout") == "1":
            setWindowProperty(self.window, 'ListLayout', '1')
        else:
            setWindowProperty(self.window, 'ListLayout', '0')
        for arg in sys.argv:
            param = arg.lower()
            log("param = " + param)
            if param.startswith('location='):
                self.location = (param[9:])
            elif param.startswith('lat='):
                self.strlat = (param[4:])
                self.lat = float(self.strlat)
            elif param.startswith('lon='):
                self.strlon = (param[4:])
                self.lon = float(self.strlon)
            elif param.startswith('type='):
                self.type = (param[5:])
            elif param.startswith('zoom='):
                self.zoom_level = (param[5:])
            elif param.startswith('aspect='):
                self.aspect = (param[7:])
            elif param.startswith('folder='):
                folder = (param[7:])
                itemlist, self.PinString = self.GetImages(folder)
            elif param.startswith('artist='):
                artist = (param[7:])
                LFM = LastFM()
                itemlist, self.PinString = LFM.GetEvents(artist)
            elif param.startswith('list='):
                listtype = (param[5:])
                self.zoom_level = 14
                if listtype == "nearfestivals":
                    LFM = LastFM()
                    itemlist, self.PinString = LFM.GetNearEvents(self.lat, self.lon, self.radius, "", True)
                elif listtype == "nearconcerts":
                    LFM = LastFM()
                    itemlist, self.PinString = LFM.GetNearEvents(self.lat, self.lon, self.radius)
            elif param.startswith('direction='):
                self.direction = (param[10:])
            elif param.startswith('prefix='):
                self.prefix = param[7:]
                if not self.prefix.endswith('.') and self.prefix != "":
                    self.prefix = self.prefix + '.'
        if self.location == "geocode":
            self.lat, self.lon = ParseGeoTags(self.strlat, self.strlon)
        elif (self.location == "") and (self.strlat == ""): # both empty
            self.lat, self.lon = GetLocationCoordinates()
            self.location = str(self.lat) + "," + str(self.lon)
            self.zoom_level = 2
        elif (not self.location == "") and (self.strlat == ""): # latlon empty
            self.lat, self.lon = self.GetGeoCodes(False, self.location)
        self.GetGoogleMapURLs()
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        if startGUI:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            self.getControls()
            self.c_places_list.reset()
            self.GetGoogleMapURLs()
            try:
                self.c_places_list.addItems(items=itemlist)
                self.c_map_image.setImage(self.GoogleMapURL)
                self.c_streetview_image.setImage(self.GoogleStreetViewURL)
            except Exception as e:
                log("Error: Exception in onInit with message:")
                log(e)
            settings = xbmcaddon.Addon(id='script.maps.browser')
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            if not settings.getSetting('firststart') == "true":
                settings.setSetting(id='firststart', value='true')
                dialog = xbmcgui.Dialog()
                dialog.ok(__language__(34001), __language__(34002), __language__(34003))
        log('onInit finished')

    def init_vars(self):
        self.NavMode_active = False
        self.street_view = False
        self.search_string = ""
        self.zoom_level = 10
        self.zoom_level_saved = 10
        self.zoom_level_streetview = 0
        self.type = "roadmap"
        self.lat = 0.0
        self.strlat = ""
        self.lon = 0.0
        self.strlon = ""
        self.pitch = 0
        self.venueid = None
        self.location = ""
        self.PinString = ""
        self.direction = 0
        self.saved_id = 100
        self.aspect = "640x400"
        self.prefix = ""
        self.radius = 50
        self.GoogleMapURL = ""
        self.GoogleStreetViewURL = ""

    def getControls(self):
        self.c_map_image = self.getControl(self.CONTROL_MAP_IMAGE)
        self.c_streetview_image = self.getControl(self.CONTROL_STREETVIEW_IMAGE)
        self.c_places_list = self.getControl(self.CONTROL_PLACES_LIST)

    def onAction(self, action):
        action_id = action.getId()
        if action_id in self.ACTION_SHOW_INFO:
            if __addon__.getSetting("InfoButtonAction") == "1":
                self.ToggleMapMode()
            else:
                if not self.street_view:
                    self.ToggleStreetMode()
                    self.ToggleNavMode()
                else:
                    self.ToggleStreetMode()
        elif action_id in self.ACTION_CONTEXT_MENU:
            self.ToggleNavMode()
        elif action_id in self.ACTION_PREVIOUS_MENU:
            if self.NavMode_active or self.street_view:
                setWindowProperty(self.window, 'NavMode', '')
                setWindowProperty(self.window, 'streetview', '')
                self.NavMode_active = False
                self.street_view = False
                xbmc.executebuiltin("SetFocus(" + str(self.saved_id) + ")")
            else:
                self.close()
        elif action_id in self.ACTION_EXIT_SCRIPT:
            self.close()
        elif self.NavMode_active:
            log("lat: " + str(self.lat) + " lon: " + str(self.lon))
            if not self.street_view:
                stepsize = 60.0 / pow(2, self.zoom_level)
                if action_id in self.ACTION_UP:
                    self.lat = float(self.lat) + stepsize
                elif action_id in self.ACTION_DOWN:
                    self.lat = float(self.lat) - stepsize
                elif action_id in self.ACTION_LEFT:
                    self.lon = float(self.lon) - 2.0 * stepsize
                elif action_id in self.ACTION_RIGHT:
                    self.lon = float(self.lon) + 2.0 * stepsize
            else:
                stepsize = 0.0002
                radiantdirection = float(radians(self.direction))
                if action_id in self.ACTION_UP and self.street_view is True:
                    self.lat = float(self.lat) + cos(radiantdirection) * float(stepsize)
                    self.lon = float(self.lon) + sin(radiantdirection) * float(stepsize)
                elif action_id in self.ACTION_DOWN and self.street_view is True:
                    self.lat = float(self.lat) - cos(radiantdirection) * float(stepsize)
                    self.lon = float(self.lon) - sin(radiantdirection) * float(stepsize)
                elif action_id in self.ACTION_LEFT and self.street_view is True:
                    if self.direction <= 0:
                        self.direction = 360
                    self.direction -= 18
                elif action_id in self.ACTION_RIGHT and self.street_view is True:
                    if self.direction >= 348:
                        self.direction = 0
                    self.direction += 18
            if self.lat > 90.0:
                self.lat -= 180.0
            if self.lat < -90.0:
                self.lat += 180.0
            if self.lon > 180.0:
                self.lon -= 360.0
            if self.lon < -180.0:
                self.lon += 180.0
            self.location = str(self.lat) + "," + str(self.lon)
        self.GetGoogleMapURLs()
        self.c_streetview_image.setImage(self.GoogleStreetViewURL)
        self.c_map_image.setImage(self.GoogleMapURL)

    def onClick(self, controlId):
        if controlId == self.CONTROL_ZOOM_IN:
            self.ZoomIn()
        elif controlId == self.CONTROL_ZOOM_OUT:
            self.ZoomOut()
        elif controlId == self.CONTROL_SEARCH:
            self.SearchDialog()
        elif controlId == self.CONTROL_MODE_TOGGLE:
            self.ToggleMapMode()
        elif controlId == self.CONTROL_STREET_VIEW:
            if not self.street_view:
                self.ToggleStreetMode()
                self.ToggleNavMode()
            else:
                self.ToggleStreetMode()
        elif controlId == self.CONTROL_MODE_ROADMAP:
            self.type = "roadmap"
        elif controlId == self.CONTROL_MODE_SATELLITE:
            self.type = "satellite"
        elif controlId == self.CONTROL_MODE_HYBRID:
            self.type = "hybrid"
        elif controlId == self.CONTROL_MODE_TERRAIN:
            self.type = "terrain"
        elif controlId == self.CONTROL_GOTO_PLACE:
            self.location = getWindowProperty(self.window, "Location")
            self.lat, self.lon = self.GetGeoCodes(False, self.location)
        elif controlId == self.CONTROL_SELECT_PROVIDER:
            self.SelectPlacesProvider()
        elif controlId == self.CONTROL_LEFT:
            pass
        elif controlId == self.CONTROL_RIGHT:
            pass
        elif controlId == self.CONTROL_UP:
            pass
        elif controlId == self.CONTROL_DOWN:
            pass
        elif controlId == self.CONTROL_LOOK_UP:
            self.PitchUp()
        elif controlId == self.CONTROL_LOOK_DOWN:
            self.PitchDown()
        elif controlId == self.CONTROL_PLACES_LIST:
            selecteditem = self.c_places_list.getSelectedItem()
            self.lat = float(selecteditem.getProperty("lat"))
            self.lon = float(selecteditem.getProperty("lon"))
            self.zoom_level = 12
            if not selecteditem.getProperty("index") == getWindowProperty(self.window, 'index'):
                setWindowProperty(self.window, 'index', selecteditem.getProperty("index"))
            else:
                venue_id = selecteditem.getProperty("venue_id")
                if venue_id is not "":
                    dialog = VenueInfoDialog(u'script-%s-dialog.xml' % addon_name, addon_path, venueid=venue_id)
                else:
                    dialog = EventInfoDialog(u'script-%s-dialog.xml' % addon_name, addon_path, item=selecteditem.getProperty("item_info"))
                dialog.doModal()
                if len(dialog.GetEventsitemlist) > 0:
                    self.PinString = dialog.GetEventsPinString
                    self.c_places_list.reset()
                    self.c_places_list.addItems(items=dialog.GetEventsitemlist)
        self.GetGoogleMapURLs()
        self.c_streetview_image.setImage(self.GoogleStreetViewURL)
        self.c_map_image.setImage(self.GoogleMapURL)

    def ZoomIn(self):
        self.location = str(self.lat) + "," + str(self.lon)
        if self.street_view:
            if self.zoom_level_streetview <= 20:
                self.zoom_level_streetview += 1
        else:
            if self.zoom_level <= 20:
                self.zoom_level += 1

    def ZoomOut(self):
        self.location = str(self.lat) + "," + str(self.lon)
        if self.street_view:
            if self.zoom_level_streetview >= 1:
                self.zoom_level_streetview -= 1
        else:
            if self.zoom_level >= 1:
                self.zoom_level -= 1

    def PitchUp(self):
        self.location = str(self.lat) + "," + str(self.lon)
        if self.pitch <= 80:
            self.pitch += 10

    def PitchDown(self):
        self.location = str(self.lat) + "," + str(self.lon)
        if self.pitch >= -80:
            self.pitch -= 10

    def ToggleNavMode(self):
        if self.NavMode_active:
            self.NavMode_active = False
            setWindowProperty(self.window, 'NavMode', '')
            xbmc.executebuiltin("SetFocus(" + str(self.saved_id) + ")")
        else:
            self.saved_id = xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId()
            self.NavMode_active = True
            setWindowProperty(self.window, 'NavMode', 'True')
            xbmc.executebuiltin("SetFocus(725)")

    def ToggleMapMode(self):
        if self.type == "roadmap":
            self.type = "satellite"
        elif self.type == "satellite":
            self.type = "hybrid"
        elif self.type == "hybrid":
            self.type = "terrain"
        else:
            self.type = "roadmap"

    def ToggleStreetMode(self):
        if self.street_view:
            self.street_view = False
            log("StreetView Off")
            self.zoom_level = self.zoom_level_saved
            setWindowProperty(self.window, 'streetview', '')
        else:
            self.street_view = True
            log("StreetView On")
            self.zoom_level_saved = self.zoom_level
            self.zoom_level = 15
            setWindowProperty(self.window, 'streetview', 'True')

    def SearchLocation(self):
        self.location = xbmcgui.Dialog().input(__language__(34032), type=xbmcgui.INPUT_ALPHANUM)
        if not self.location == "":
            self.street_view = False
            self.lat, self.lon = self.GetGeoCodes(True, self.location)

    def SelectPlacesProvider(self):
        setWindowProperty(self.window, 'index', "")
        modeselect = []
        itemlist = None
        modeselect.append(__language__(34016))  # concerts
        modeselect.append(__language__(34017))  # festivals
        modeselect.append(__language__(34027))  # geopics
        modeselect.append(__language__(34028))  # eventful
        modeselect.append(__language__(34029))  # FourSquare
        modeselect.append(__language__(34030))  # MapQuest
        modeselect.append(__language__(34031))  # Google Places
        modeselect.append(__language__(34019))  # reset
        dialogSelection = xbmcgui.Dialog()
        provider_index = dialogSelection.select(__language__(34020), modeselect)
        if not provider_index < 0:
            if modeselect[provider_index] == __language__(34031):
                GP = GooglePlaces()
                category = GP.SelectCategory()
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                if category is not None:
                    self.PinString, itemlist = GP.GetGooglePlacesList(self.lat, self.lon, self.radius * 1000, category)
            elif modeselect[provider_index] == __language__(34029):
                FS = FourSquare()
                section = FS.SelectSection()
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                if section is not None:
                    itemlist, self.PinString = FS.GetPlacesListExplore(self.lat, self.lon, section)
            elif modeselect[provider_index] == __language__(34016):
                LFM = LastFM()
                category = LFM.SelectCategory()
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                if category is not None:
                    itemlist, self.PinString = LFM.GetNearEvents(self.lat, self.lon, self.radius, category)
            elif modeselect[provider_index] == __language__(34030):
                MQ = MapQuest()
                itemlist, self.PinString = MQ.GetItemList(self.lat, self.lon, self.zoom_level)
            elif modeselect[provider_index] == __language__(34017):
                LFM = LastFM()
                category = LFM.SelectCategory()
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                if category is not None:
                    itemlist, self.PinString = LFM.GetNearEvents(self.lat, self.lon, self.radius, category, True)
            elif modeselect[provider_index] == __language__(34027):
                folder_path = xbmcgui.Dialog().browse(0, __language__(34021), 'pictures')
                setWindowProperty(self.window, 'imagepath', folder_path)
                itemlist, self.PinString = self.GetImages(folder_path)
            elif modeselect[provider_index] == __language__(34028):
                EF = Eventful()
                category = EF.SelectCategory()
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                if category is not None:
                    itemlist, self.PinString = EF.GetEventfulEventList(self.lat, self.lon, "", category, self.radius)
            elif modeselect[provider_index] == __language__(34019):
                self.PinString = ""
                itemlist = []
            if itemlist is not None:
                self.c_places_list.reset()
                self.c_places_list.addItems(items=itemlist)
            self.street_view = False
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    def SearchDialog(self):
        setWindowProperty(self.window, 'index', "")
        modeselect = []
        modeselect.append(__language__(34024))
        modeselect.append(__language__(34004))
        modeselect.append(__language__(34023))
        modeselect.append(__language__(34033))
        modeselect.append(__language__(34019))
        dialogSelection = xbmcgui.Dialog()
        provider_index = dialogSelection.select(__language__(34026), modeselect)
        if not provider_index < 0:
            if modeselect[provider_index] == __language__(34024):
                self.SearchLocation()
                itemlist = []
            elif modeselect[provider_index] == __language__(34004):
                query = xbmcgui.Dialog().input(__language__(34022), type=xbmcgui.INPUT_ALPHANUM)
                FS = FourSquare()
                itemlist, self.PinString = FS.GetPlacesList(self.lat, self.lon, query)
            elif modeselect[provider_index] == __language__(34023):
                artist = xbmcgui.Dialog().input(__language__(34025), type=xbmcgui.INPUT_ALPHANUM)
                LFM = LastFM()
                itemlist, self.PinString = LFM.GetEvents(artist)
            elif modeselect[provider_index] == __language__(34033):
                venue = xbmcgui.Dialog().input(__language__(34025), type=xbmcgui.INPUT_ALPHANUM)
                LFM = LastFM()
                venueid = LFM.GetVenueID(venue)
                itemlist, self.PinString = LFM.GetEvents(artist)
            elif modeselect[provider_index] == __language__(34019):
                self.PinString = ""
                itemlist = []
            self.c_places_list.reset()
            self.c_places_list.addItems(items=itemlist)
            self.street_view = False

    def toggleInfo(self):
        self.show_info = not self.show_info
        self.info_controller.setVisible(self.show_info)

    def GetGoogleMapURLs(self):
        if self.street_view is True:
            size = "320x200"
        else:
            size = "640x400"
        if self.lat and self.lon:
            self.search_string = str(self.lat) + "," + str(self.lon)
        else:
            self.search_string = urllib.quote_plus(self.location.replace('"', ''))
        base_url = 'http://maps.googleapis.com/maps/api/staticmap?&sensor=false&scale=2&format=%s&' % (__addon__.getSetting("ImageFormat"))
        url = base_url + 'maptype=%s&center=%s&zoom=%s&markers=%s&size=%s&key=%s' % (self.type, self.search_string, self.zoom_level, self.search_string, size, googlemaps_key_normal)
        self.GoogleMapURL = url + self.PinString
        zoom = 120 - int(self.zoom_level_streetview) * 6
        base_url = 'http://maps.googleapis.com/maps/api/streetview?&sensor=false&format=%s&' % (__addon__.getSetting("ImageFormat"))
        self.GoogleStreetViewURL = base_url + 'location=%s&size=640x400&fov=%s&key=%s&heading=%s&pitch=%s' % (self.search_string, str(zoom), googlemaps_key_streetview, str(self.direction), str(self.pitch))
        setWindowProperty(self.window, self.prefix + 'location', self.location)
        setWindowProperty(self.window, self.prefix + 'lat', str(self.lat))
        setWindowProperty(self.window, self.prefix + 'lon', str(self.lon))
        setWindowProperty(self.window, self.prefix + 'zoomlevel', str(self.zoom_level))
        setWindowProperty(self.window, self.prefix + 'direction', str(self.direction / 18))
        setWindowProperty(self.window, self.prefix + 'type', self.type)
        setWindowProperty(self.window, self.prefix + 'aspect', self.aspect)
        setWindowProperty(self.window, self.prefix + 'map_image', self.GoogleMapURL)
        setWindowProperty(self.window, self.prefix + 'streetview_image', self.GoogleStreetViewURL)
        setWindowProperty(self.window, self.prefix + 'NavMode', "")
        setWindowProperty(self.window, self.prefix + 'streetview', "")
        hor_px = int(size.split("x")[0])
        ver_px = int(size.split("x")[1])
        mx, my = LatLonToMeters(self.lat, self.lon)
        px, py = MetersToPixels(mx, my, self.zoom_level)
        mx2, my2 = PixelsToMeters(px + hor_px / 2, py + ver_px / 2, self.zoom_level)
        self.radiusx = abs((mx - mx2) / 1000)
        self.radius = abs((my - my2) / 1000)
        if self.radius > 500:
            self.radius = 500
        cache_path = xbmc.getCacheThumbName(self.GoogleMapURL)
        log(cache_path)
       # my = my - my2
      #  log("mx: " + str(mx) + "my: " + str(my) + "px: " + str(px) + "py: " + str(py))

        # import MercatorProjection
        # centerPoint = MercatorProjection.G_LatLng(self.lat, self.lon)
        # corners = MercatorProjection.getCorners(centerPoint, zoom, mapWidth, mapHeight)
        # prettyprint(corners)
        if self.street_view:
            setWindowProperty(self.window, self.prefix + 'streetview', "True")
        if self.NavMode_active:
            setWindowProperty(self.window, self.prefix + 'NavMode', "True")

    def GetGeoCodes(self, show_dialog, search_string):
        try:
            search_string = urllib.quote_plus(search_string)
            url = 'https://maps.googleapis.com/maps/api/geocode/json?&sensor=false&address=%s' % (search_string)
            log("Google Geocodes Search:" + url)
            response = GetStringFromUrl(url)
            results = simplejson.loads(response)
            events = []
            for item in results["results"]:
                locationinfo = item["geometry"]["location"]
                lat = str(locationinfo["lat"])
                lon = str(locationinfo["lng"])
                search_string = lat + "," + lon
                googlemap = 'http://maps.googleapis.com/maps/api/staticmap?&sensor=false&scale=1&maptype=roadmap&center=%s&zoom=13&markers=%s&size=640x640&key=%s' % (search_string, search_string, googlemaps_key_normal)
                event = {'generalinfo': item['formatted_address'],
                         'lat': lat,
                         'lon': lon,
                         'map': lon,
                         'preview': googlemap,
                         'id': item['formatted_address']}
                events.append(event)
            first_hit = results["results"][0]["geometry"]["location"]
            if show_dialog:
                if len(results["results"]) > 1:  # open dialog when more than one hit
                    w = dialog_select_UI('DialogSelect.xml', __addonpath__, listing=events)
                    w.doModal()
                    log(w.lat)
                    self.zoom_level = 12
                    return (w.lat, w.lon)
                elif len(results["results"]) == 1:
                    self.zoom_level = 12
                    return (first_hit["lat"], first_hit["lng"])  # no window when only 1 result
                else:
                    return (self.lat, self.lon)  # old values when no hit
            else:
                self.zoom_level = 12
                return (first_hit["lat"], first_hit["lng"])
        except Exception as e:
            log(e)
            return ("", "")


class dialog_select_UI(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.listing = kwargs.get('listing')
        self.selected_id = ''
        self.lon = ''
        self.lat = ''

    def onInit(self):
        self.img_list = self.getControl(6)
        self.img_list.controlLeft(self.img_list)
        self.img_list.controlRight(self.img_list)
        self.getControl(3).setVisible(False)
        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(__language__(32015))
        for entry in self.listing:
            listitem = xbmcgui.ListItem('%s' % (entry['generalinfo']))
            listitem.setIconImage(entry['preview'])
            listitem.setLabel2(entry['id'])
            listitem.setProperty("lat", entry['lat'])
            listitem.setProperty("lon", entry['lon'])
            self.img_list.addItem(listitem)
        self.setFocus(self.img_list)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlID):
        if controlID == 6 or controlID == 3:
            self.selected_id = self.img_list.getSelectedItem().getLabel2()
            self.lat = float(self.img_list.getSelectedItem().getProperty("lat"))
            self.lon = float(self.img_list.getSelectedItem().getProperty("lon"))
            xbmc.log('# GUI selected lat: %s' % self.selected_id)
            self.zoom_level = 12
            self.close()

    def onFocus(self, controlID):
        pass


class EventInfoDialog(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    C_TEXT_FIELD = 200
    C_TITLE = 201
    C_BIG_IMAGE = 211
    C_RIGHT_IMAGE = 210
    C_ARTIST_LIST = 500

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.item = kwargs.get('item')
        self.prop_list = simplejson.loads(self.item)
        self.PinString = ""
        self.itemlist = []

    def onInit(self):
        LFM = LastFM()
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.setControls()
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def setControls(self):
        self.getControl(self.C_TEXT_FIELD).setText(self.prop_list["description"])
     #   self.getControl(202).setLabel(self.prop_list["date"])
        self.getControl(self.C_TITLE).setLabel(self.prop_list["name"])
        self.getControl(self.C_BIG_IMAGE).setImage(self.prop_list["thumb"])
    #    self.getControl(self.C_RIGHT_IMAGE).setImage(self.prop_list["venue_image"])
    #    self.getControl(204).setLabel(self.prop_list["street"])
    #    self.getControl(self.C_TITLE).setLabel(self.prop_list["eventname"])
    #    self.getControl(self.C_ARTIST_LIST).addItems(items=self.itemlist)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlID):
        if controlID == self.C_ARTIST_LIST:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            artist = self.getControl(self.C_ARTIST_LIST).getSelectedItem().getProperty("artists")
            self.close()
            LFM = LastFM()
            self.itemlist, self.PinString = LFM.GetEvents(artist)
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    def onFocus(self, controlID):
        pass


class VenueInfoDialog(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    C_TEXT_FIELD = 200
    C_TITLE = 201
    C_BIG_IMAGE = 211
    C_RIGHT_IMAGE = 210
    C_ARTIST_LIST = 500

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.venueid = kwargs.get('venueid')
        self.prop_list = []
        self.PinString = ""
        self.GetEventsPinString = ""
        self.itemlist = []
        self.GetEventsitemlist = []

    def onInit(self):
        LFM = LastFM()
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.itemlist, PinString = LFM.GetVenueEvents(self.venueid)
        self.prop_list = simplejson.loads(self.itemlist[0].getProperty("item_info"))
        self.setControls()
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def setControls(self):
        self.getControl(self.C_TEXT_FIELD).setText(self.prop_list["description"])
        self.getControl(202).setLabel(self.prop_list["date"])
        self.getControl(203).setLabel(self.prop_list["name"])
        self.getControl(self.C_BIG_IMAGE).setImage(self.prop_list["thumb"])
        self.getControl(self.C_RIGHT_IMAGE).setImage(self.prop_list["venue_image"])
        self.getControl(204).setLabel(self.prop_list["street"])
        self.getControl(self.C_TITLE).setLabel(self.prop_list["eventname"])
        self.getControl(self.C_ARTIST_LIST).addItems(items=self.itemlist)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlID):
        if controlID == self.C_ARTIST_LIST:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            artist = self.getControl(self.C_ARTIST_LIST).getSelectedItem().getProperty("artists")
            self.close()
            LFM = LastFM()
            self.GetEventsitemlist, self.GetEventsPinString = LFM.GetEvents(artist)
            xbmc.executebuiltin("Dialog.Close(busydialog)")

    def onFocus(self, controlID):
        pass


if __name__ == '__main__':
    startGUI = True
    for arg in sys.argv:
        param = arg.lower()
        xbmc.log("param = " + param)
        if param.startswith('prefix='):
            startGUI = False
        if param.startswith('venueid='):
            startGUI = False
            venueid = (param[8:])
            dialog = VenueInfoDialog(u'script-%s-dialog.xml' % addon_name, addon_path, venueid=venueid)
            dialog.doModal()
    if startGUI:
        gui = GUI(u'script-%s-main.xml' % addon_name, addon_path).doModal()
    else:
        gui = GUI(u'script-%s-main.xml' % addon_name, addon_path).onInit(startGUI)
    del gui
    sys.modules.clear()
