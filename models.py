from google.appengine.ext import ndb

import json


# TODO: merge theses with models.py
# Database Model: Milestone Data
class Milestone(ndb.Model):
	city_name = ndb.StringProperty()
	goalMiles = ndb.IntegerProperty()

# Database Model: Teacher Data
class Teacher(ndb.Model):
	name = ndb.StringProperty()
	currentMilestone = ndb.KeyProperty(Milestone)
	grade = ndb.StringProperty()
	totalClassMiles = ndb.ComputedProperty(lambda self: sum([s.total_miles for s in Student.query(Student.teacher == self.key)]))

# Data structure: Student Data
class Student(ndb.Model):
	studentID = ndb.IntegerProperty()
	name = ndb.StringProperty(indexed=True)
	teacher = ndb.KeyProperty(Teacher)
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