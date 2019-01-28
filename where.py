"""
Liam Saliba, 24/06/18, 29/01/19
"""
from locationsharinglib import Service
import math
import getpass

def dist(c1, c2):
	""" Calculates the distance between two coordinates (lat, long) """
	R = 6371
	lat1 = math.radians(c1[0])
	lat2 = math.radians(c2[0])
	latd = math.radians(c2[0]-c1[0])
	lond = math.radians(c2[1]-c1[1])
	return 2*R*math.asin(math.sqrt(math.sin(latd/2)*math.sin(latd/2)+math.cos(lat1)*math.cos(lat2)*math.sin(lond/2)*math.sin(lond/2)))

class FrontEnd:
	def __init__(self, username, password):
		self.service = Service(username, password)
		self.you = None
		self.people = None
		self.update()
		

	def update(self):
		self.you = self.service.get_authenticated_person()
		self.you.coord = (self.you._latitude, self.you._longitude)
		self.people = self.service.get_shared_people()
		for person in self.people:
			person.coord = (person._latitude, person._longitude)

		self.print_all()

	def print_all(self):
		print("You are at %s (%s, %s)" % (self.you._address, self.you._latitude, self.you._longitude))
		for p in self.people:
			print("%s is %d km away, at %s (%s, %s)" % (p._nickname, dist(p.coord, self.you.coord), p._address, p._latitude, p._longitude))
		print("Last updated:", self.you.datetime)

print("Enter google login details: ")
username = input("Username: ")
password = getpass.getpass("Password: ")

print("\n")
fe = FrontEnd(username, password)

while True:
	print("\n\n")
	i = input("x to exit, anything to refresh > ")
	if i == 'x':
		break
	fe.update()

print("\n(Exiting...)")
#for person in people