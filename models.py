from google.appengine.ext import ndb

import json

class Teacher(ndb.Model):
	name = ndb.StringProperty()
	grade = ndb.StringProperty()

class Student(ndb.Model):
	id = ndb.IntegerProperty()
	name = ndb.StringProperty()
	teacher = ndb.StringProperty()
	grade = ndb.StringProperty()
	laps1 = ndb.FloatProperty()
	laps2 = ndb.FloatProperty()
	total_miles = ndb.ComputedProperty(lambda self: self.laps1*0.1+self.laps2*0.25)

class Class(object):
	def __init__(self):
		self.teacher = Teacher()
		self.students = []
		self.used = False # used during parsing

	def to_dict(self):
		return {
			'teacher': self.teacher.to_dict(),
			'students': [s.to_dict() for s in self.students],
		}