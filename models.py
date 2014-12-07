from google.appengine.ext import ndb

import json


# Database Model: Milestone Data
class Milestone(ndb.Model):
	city_name = ndb.StringProperty()
	goalMiles = ndb.FloatProperty()

# Database Model: Teacher Data
class Teacher(ndb.Model):
	name = ndb.StringProperty()
	currentMilestone = ndb.KeyProperty(Milestone)
	totalClassMiles = ndb.ComputedProperty(lambda self: sum([s.total_miles for s in Student.query(Student.teacher == self.key)]))
	
	def totalGrass(self):
		self._ensureStudents()
		return sum([s.grassLaps for s in self._students])
	
	def totalCement(self):
		self._ensureStudents()
		return str(sum([s.cementLaps for s in self._students]))

	def _ensureStudents(self):
		if not hasattr(self, '_students'):
			self._students = list(Student.query(Student.teacher==self.key))

# Data structure: Student Data
class Student(ndb.Model):
	studentID = ndb.IntegerProperty(indexed=False)
	name = ndb.StringProperty(indexed=True)
	teacher = ndb.KeyProperty(Teacher)
	grade = ndb.StringProperty()
	cementLaps = ndb.FloatProperty(indexed=False)
	grassLaps = ndb.FloatProperty(indexed=False)
	total_miles = ndb.ComputedProperty(lambda self: self.cementLaps / 10.5 + self.grassLaps / 4.0)

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