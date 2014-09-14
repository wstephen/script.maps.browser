from Utils import *
import xbmcgui
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

googlemaps_key_normal = 'AIzaSyBESfDvQgWtWLkNiOYXdrA9aU-2hv_eprY'
eventful_key = 'Nw3rh3mXn8RhMQNK'
max_limit = 25


class Eventful():

    def __init__(self):
        pass

    def GetEventfulList(self, lat="", lon="", query=""):
        if query is not "":
            url = 'http://api.eventful.com/json/events/search?where=%.8f,%.8f&image_sizes=large&include=price&page_size=25date&sort_order=date&within=30&date=Future&query=%s&app_key=%s' % (lat, lon, query, eventful_key)
        else:
            url = 'http://api.eventful.com/json/events/search?where=%.8f,%.8f&image_sizes=large&include=price&page_size=25date&sort_order=date&within=30&date=Future&app_key=%s' % (lat, lon, eventful_key)
      #  url = 'https://api.foursquare.com/v2/venues/search?ll=%.6f,%.8f&query=%s&limit=50&client_id=%s&client_secret=%s&v=20130815' % (self.lat, self.lon, "Food", foursquare_id, foursquare_secret)
        response = GetStringFromUrl(url)
        results = simplejson.loads(response)
        return self.HandleEventfulEventResult(results['events']['event'])

    def HandleEventfulEventResult(self, results):
        PinString = ""
        places_list = list()
        letter = ord('A')
        count = 0
        for venue in results:
            eventname = cleanText(venue['title'])
            venuename = cleanText(venue['venue_name'])
            formattedAddress = cleanText(venue["venue_address"])
            lat = str(venue['latitude'])
            lon = str(venue['longitude'])
            search_string = lat + "," + lon
            googlemap = 'http://maps.googleapis.com/maps/api/staticmap?&sensor=false&scale=2&maptype=roadmap&center=%s&zoom=13&markers=%s&size=640x640&key=%s' % (search_string, search_string, googlemaps_key_normal)
            if venue["image"] is not None:
                photo = venue["image"]["large"]["url"]
            else:
                photo = ""
            if (venue["start_time"] == venue["stop_time"]) or (venue["stop_time"] is None):
                date = venue["start_time"]
            else:
                date = venue["start_time"] + " - " + venue["stop_time"]
            prop_list = {"id": str(venue['id']),
                         "eventname": eventname,
                         "description": cleanText(venue['description']),
                         "name": venuename,
                         "photo": photo,
                         "date": date,
                         "address": formattedAddress,
                         "Venue_Image": photo,
                         "venue_id": venue['venue_id'],
                         "GoogleMap": googlemap,
                         "index":  str(count),
                         "sortletter": chr(letter),
                         "lat": lat,
                         "lon": lon}
            item = xbmcgui.ListItem(venuename)
            for key, value in prop_list.iteritems():
                item.setProperty(key, value)
            item.setProperty("item_info", simplejson.dumps(prop_list))
            item.setArt({'thumb': photo})
            item.setLabel(venuename)
            item.setLabel2(date)
            PinString = PinString + "&markers=color:blue%7Clabel:" + chr(letter) + "%7C" + lat + "," + lon
            places_list.append(item)
            count += 1
            letter += 1
            if count > max_limit:
                break
        return places_list, PinString
