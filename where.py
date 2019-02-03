"""
Location sharing lib wrapper
Liam Saliba
2018-06-24, 2019-01-29, 2019-02-02
"""
from locationsharinglib import Service
from geopy.geocoders import Nominatim
from geopy import distance
import requests
import json
import math
import getpass
import datetime
import os

geolocator = Nominatim(user_agent="whereis-friend")

def get_time_displacement(dt):
    delta = datetime.datetime.now(dt.tzinfo) - dt
    sec = delta.total_seconds()
    if sec < 60:
        return "now"
    if sec < 60*2:
        return "1 min ago"
    if sec < 60*60:
        return "%d mins ago" % (sec // 60)
    if sec < 60*60*2:
        return "1 hour ago"
    if sec < 60*60*24:
        return "%d hours ago" % (sec // (60*60))
    return "long ago"
    #return dt

LOCATION_AWAY = "AWAY"
LOCATION_HOME = "HOME"
LOCATION_HOME_YOU = "HOME YOU"
LOCATION_YOU = "YOU"
YOU_THRESH = 50
HOME_THRESH = 150
FNAME = "save.dat"

class Person:
    def __init__(self, person, you=None, home=None):
        self.id = person.id
        self.home = home

        self.picture_url = None
        self.full_name = None
        self.nickname = None
        self.latitude = None
        self.longitude = None
        self.location = None
        self.datetime = None
        self.accuracy = None
        self.address = None
        self.country_code = None
        self.charging = None
        self.battery_level = None
        self.history = []
        self.distance = None

        self.update(person, you)

    def update(self, person, you=None):
        self.picture_url = person.picture_url
        self.full_name = person.full_name
        self.nickname = person.nickname
        self.latitude = person.latitude
        self.longitude = person.longitude
        #self.location = geolocator.reverse(self.loc)
        #print(self.location.raw)
        self.datetime = person.datetime
        self.accuracy = person.accuracy
        self.address = person.address
        self.country_code = person.country_code
        self.charging = person.charging
        self.battery_level = person.battery_level
        self.history.append({'loc': self.loc, 'dt': self.datetime})

        if you is not None:
            self.distance = self.distance_to(you)

    def distance_to(self, other):
        """ returns distance in metres to other person or latitude/longitude """
        return distance.distance(self.loc, other if type(other) in [tuple, list] else other.loc).m

    @property
    def loc(self):
        if self.latitude == None:
            return None
        return (self.latitude, self.longitude)

    @property
    def at_home(self):
        if self.home is None:
            return False
        return self.distance_to(self.home) <= HOME_THRESH

    @property
    def status(self):
        if self.distance < YOU_THRESH:
            if self.at_home:
                return LOCATION_HOME_YOU
            return LOCATION_YOU
        if self.at_home:
            return LOCATION_HOME
        return LOCATION_AWAY

    def set_home(self, dest=None):
        if dest is not None:
            self.home = dest
            return
        self.home = list(self.loc)

    def get_info_str(self):
        middle = ""
        if self.status == LOCATION_HOME_YOU:
            middle = "at home with you"
        elif self.status == LOCATION_HOME:
            middle = "at their home"
        elif self.status == LOCATION_YOU:
            middle = "with you"
        else:
            middle = "at " + self.address
            if self.distance is not None:
                d = "%d m" % self.distance
                if self.distance >= 1000 and self.distance < 10000:
                    d = "{:.2} km".format(self.distance / 1000)
                elif self.distance > 10000:
                    d = "%d km" % (self.distance / 1000)
                middle = "%s away, %s" % (d, middle)
        return "%s is %s.  (%s)" % (self.nickname, middle, get_time_displacement(self.datetime))

    def print(self):
        print(self.get_info_str())

    def serialise(self):
        # no need to save if home hasn't been set
        if self.home is None:
            return None
        print(self.id)
        return "{},{},{}\n".format(self.id, self.home[0], self.home[1])

    def __str__(self):
        return "{} ({}) at {} ({}, {})".format(self.full_name, self.nickname, self.address, self.latitude, self.longitude)

    def __repr__(self):
        return "Person ({}) {}".format(self.id, str(self))

class You(Person):
    def get_info_str(self):
        place = ""
        if self.at_home:
            place += "home: "
        place += self.address
        return "You are at %s.   (%s)" % (place, get_time_displacement(self.datetime))

    def __repr__(self):
        return "You ({}) {}".format(self.id, str(self))

class FrontEnd:
    def __init__(self, username, password):
        self.service = Service(username, password)
        print("Authenticated.\n")
        self.now = None
        self.you = None
        self.people = []
        self.person_d = {}
        self.load()
        self.update()

    def load(self):
        if not os.path.isfile(FNAME):
            return
        for line in open(FNAME, 'r'):
            parts = line.split(",")
            if len(parts) != 3:
                continue
            pid, lat, lon = parts
            home = (float(lat), float(lon))
            self.person_d[pid] = home
        print("Loaded.")


    def update(self):
        print("Updating...\n")
        you = self.service.get_authenticated_person()
        self.now = datetime.datetime.now()

        if you.id in self.person_d.keys():
            # both 'homes' and people stored in the person dictionary
            if type(self.person_d[you.id]) == tuple:
                self.you = You(you, home=self.person_d[you.id])
            else:
                self.you = self.person_d[you.id]
                self.you.update(you)
        else:
            self.you = You(you)
        self.person_d[you.id] = self.you

        self.people = []
        for p in self.service.get_shared_people():
            new_p = None
            if p.id in self.person_d.keys():
                # both 'homes' and people stored in the person dictionary
                if type(self.person_d[p.id]) == tuple:
                    new_p = Person(p, you=self.you, home=self.person_d[p.id])
                else:
                    new_p = self.person_d[p.id]
                    new_p.update(p, self.you)
            else:
                new_p = Person(p, you=self.you)
            self.person_d[p.id] = new_p
            self.people.append(new_p)

        # sort by furthest distance
        self.people.sort(key=lambda p: p.distance)

    def print_all(self):
        self.you.print()
        print("")
        for i, p in enumerate(self.people):
            print("%2d. " % (i+1), end="")
            p.print()
        print("(Refreshed at %s.)" % self.now.strftime('%Y-%m-%d %H:%M:%S'))

    def set_home(self, i):
        if i > len(self.people):
            return
        if i == 0:
            self.you.set_home()
        else:
            i -= 1
            self.people[i].set_home()
        self.save()

    def save(self):
        f = open(FNAME, "w")
        for p in self.person_d.values():
            x = p.serialise()
            if x is not None:
                f.write(x)



print("whereis --- \nEnter Google account login...")
username = input("Username: ")
password = getpass.getpass("Password: ")

fe = FrontEnd(username, password)

while True:
    fe.print_all()
    i = input("\n> ")
    if i == "x" or i == 'exit':
        break
    cmds = i.split()
    if len(cmds) > 0 and (cmds[0] == "sethome" or cmds[0] == 's') and cmds[1].isnumeric():
        fe.set_home(int(cmds[1]))
    else:
        fe.update()
    print("")

print("Exiting...\n")