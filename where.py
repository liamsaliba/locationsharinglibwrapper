"""
Location sharing lib wrapper
Liam Saliba
2018-06-24, 2019-01-29, 2019-02-02
"""
from locationsharinglib import Service
import math
import getpass
import datetime

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

def dist(c1, c2):
    """ Calculates the distance between two coordinates (lat, long) using the haversine formula """
    R = 6371e3 # meters
    lat1 = math.radians(c1[0])
    lat2 = math.radians(c2[0])
    latd = math.radians(c2[0]-c1[0])
    lond = math.radians(c2[1]-c1[1])
    return 2*R*math.asin(math.sqrt(math.sin(latd/2)*math.sin(latd/2)+math.cos(lat1)*math.cos(lat2)*math.sin(lond/2)*math.sin(lond/2)))

LOCATION_AWAY = "AWAY"
LOCATION_HOME = "HOME"
LOCATION_HOME_YOU = "HOME YOU"
LOCATION_YOU = "YOU"
YOU_THRESH = 50
HOME_THRESH = 150
FNAME = "save.dat"

class Person:
    def __init__(self, person, you=None, home=None):
        self.id = person._id
        self.home = home

        self.picture_url = None
        self.full_name = None
        self.nickname = None
        self.latitude = None
        self.longitude = None
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
        self.datetime = person.datetime
        self.accuracy = person.accuracy
        self.address = person.address
        self.country_code = person.country_code
        self.charging = person.charging
        self.battery_level = person.battery_level
        self.history.append({'loc': list(self.loc), 'dt': self.datetime})

        if you is not None:
            self.set_distance(you)

    @property
    def loc(self):
        if self.latitude is None:
            return None
        return (self.latitude, self.longitude)

    @property
    def at_home(self):
        if self.home is None:
            return False
        return dist(self.loc, self.home) <= HOME_THRESH

    @property
    def status(self):
        if self.distance < YOU_THRESH:
            if self.at_home:
                return LOCATION_HOME_YOU
            return LOCATION_YOU
        if self.at_home:
            return LOCATION_HOME
        return LOCATION_AWAY

    def set_distance(self, you):
        self.distance = dist(self.loc, you.loc)

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

    def __str__(self):
        return "{} ({}) at {} ({}, {})".format(self.full_name, self.nickname, self.address, self.latitude, self.longitude)

    def __repr__(self):
        return "Person ({}) {}".format(self.id, str(self))

class You(Person):
    def get_info_str(self):
        return "You are at %s.   (%s)" % (self.address, get_time_displacement(self.datetime))

    def __repr__(self):
        return "You ({}) {}".format(self.id, str(self))

class FrontEnd:
    def __init__(self, username, password, fname=None):
        self.service = Service(username, password)
        print("Authenticated.\n")
        self.now = None
        self.you = None
        self.people = []
        self.person_d = {}
        self.update()

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
        if i == 0:
            self.you.set_home()
        if i > len(self.people):
            return
        i -= 1
        self.people[i].set_home()

print("whereis --- \nEnter Google account login...")
username = input("Username: ")
password = getpass.getpass("Password: ")

fe = FrontEnd(username, password, FNAME)

while True:
    fe.print_all()
    i = input("\n> ")
    if i == "x" or i == 'exit':
        break
    cmds = i.split()
    if len(cmds) > 0 and cmds[0] == "sethome" and cmds[1].isnumeric():
        fe.set_home(int(cmds[1]))
    else:
        fe.update()
    print("")

print("Exiting...\n")

#save(FNAME)
#for person in people