import cgi
import cgitb
import urllib

from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required, admin_required
from google.appengine.api import users
import webapp2
from import_export import ImportHandler, ExportHandler, ExportAllHandler, ExportSingleHandler, ImportIDsHandler
from google.appengine.api import mail
from datetime import date
import logging

import json
from models import Student, Teacher, Milestone, Class
from tmpl import BaseHandler
from string import Template

from google.appengine.api import app_identity

from cron import EmailHandler, CheckMilestones

cgitb.enable()

# TODO: remove this
BACK_BUTTON = """
		<a href="/"><button>Back To Main Page</button></a>
	</body>
</html>
"""

# Handler that lists the milestones currently in the datastore
class Milestones(BaseHandler):
	@admin_required
	def get(self):
		# get all milestones
		milestones = Milestone.query().order(Milestone.goalMiles)

		# render milestones.html with all milestones
		self.render('html/milestones.html', {
			'milestones' : milestones
		})
		
# Handler that adds a new milestone to the datastore
class AddMilestone(BaseHandler):
	@admin_required
	def get(self):
		self.render('html/addMilestone.html', {})

	def post(self):
		try:
			# get the data that they wish to add
			city = self.request.get('city')
			miles = self.request.get('miles')

			# if the user has input something for BOTH fields
			if city and miles:
				newMilestone = Milestone(id = city, city_name = city, goalMiles = float(miles))
				newMilestone.put()

			self.redirect('/milestones')
		except Exception, e:
			logging.error(e)
			self.response.out.write('Error adding milestone to datastore!')
			self.response.out.write(e)

# Handler that deletes a milestone from the datastore
class DeleteMilestone(webapp2.RequestHandler):
	def post(self):
		try:
			# get the city name of the milestone that they wish to delete
			deleteChoice = self.request.get('id')

			toDelete = Milestone.query(Milestone.city_name == deleteChoice).get()
			
			# delete from the datastore
			toDelete.key.delete()

			self.redirect('/milestones')
		except Exception as e:
			self.response.write('<html><body>Error deleting milestone!<br>')
			self.response.write(e)
			self.response.write(BACK_BUTTON)
			logging.error(e)

# Handler that saves the changes made to a milestone
class ModifyMilestone(BaseHandler):
	@admin_required
	def get(self):
		# get the chosen milestone
		modify_id = self.request.get('id')

		chosen_milestone = Milestone.query(Milestone.city_name == modify_id).get()

		self.render('html/modifyMilestone.html', {
			'milestone' : chosen_milestone
		})

	def post(self):
		modify_id = self.request.get('id')
		chosen_milestone = Milestone.query(Milestone.city_name == modify_id).get()

		try:
			# get the new values
			newCity = self.request.get('city')
			newMiles = self.request.get('miles')

			# update the milestone and add changes to datastore
			chosen_milestone.city_name = newCity
			chosen_milestone.goalMiles = float(newMiles)
			chosen_milestone.put()

			self.redirect('/milestones')
		except Exception, e:
			logging.error(e)
			self.response.write('<html><body>Error modifying milestone!<br>')
			self.response.write(e)
			self.response.write(BACK_BUTTON)
		
class LapTrackerHandler(BaseHandler):
	@admin_required
	def get(self):
		track = self.request.get('track')
		data = {
			'track': track,
			'cement': track == '1',
			'grass': track == '2',
		}
		if track:
			self.render('html/tracker.html', data)
		else:
			self.render('html/which_track.html', data)
	def post(self):
		student_id = self.request.get('id')
		key = ndb.Key('Student', int(student_id))
		student = key.get()
		if not student:
			self.response.out.write(json.dumps({
				'error': 'invalid id',
			}))
			return
		track = self.request.get('track')
		if track == '1':
			student.cementLaps = student.cementLaps + 1
		else:
			print track
			student.grassLaps = student.grassLaps + 1
		student.put()
		self.response.out.write(json.dumps({
			'id': student.studentID,
			'name': student.name,
			'track': track
		}))

class RollbackHandler(BaseHandler):
	def post(self):
		student_id = self.request.get('id')
		key = ndb.Key('Student', int(student_id))
		student = key.get()
		if not student:
			self.response.out.write(json.dumps({
				'error': 'invalid id',
			}))
			return
		track = self.request.get('track')
		if track == '1':
			student.cementLaps = student.cementLaps - 1
		else:
			student.grassLaps = student.grassLaps - 1
		student.put()
		self.response.out.write(json.dumps({
			'id': student.studentID,
			'name': student.name,
			'track': track
		}))

class TeacherNameHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		data = [t.name for t in Teacher.query()]
		data = sorted(data, reverse=True)
		self.response.out.write(json.dumps(data))

class StudentNameHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		key = ndb.Key('Teacher', self.request.get('teacher'))
		students = list(Student.query(Student.teacher==key))
		data = [{'id':s.studentID, 'name':s.name} for s in students]
		data = sorted(data, key=lambda x: x['name'], reverse=True)
		self.response.out.write(json.dumps(data))

class ResetHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		qo = ndb.QueryOptions(keys_only=True)
		query = Student.query()
		ndb.delete_multi(query.fetch(1000, options=qo))

		query = Teacher.query()
		for t in query:
			t.currentMilestone = None
			t.put()

		self.redirect('/milestones')

class ViewAllHandler(BaseHandler):
	def get(self):
		students = list(Student.query())
		for s in students:
			s._teacher = s.teacher.get()
			s.teacher_name = s._teacher.name

		teachers = {s._teacher.name:s._teacher for s in students}

		classes = []
		for teacher_name, teacher in teachers.items():
			c = Class()
			c.teacher = teacher
			c.students = filter(lambda s: s.teacher_name == teacher_name, students)
			classes.append(c)
		self.render('html/view_all.html', {
			'errors':[],
			'classes': classes,
		})


# assigns a web address to a handler
application = webapp2.WSGIApplication([
	('/', LapTrackerHandler),
	('/import', ImportHandler),
	('/import_ids', ImportIDsHandler),
	('/export', ExportHandler),
	('/export_single', ExportSingleHandler),
	('/track', LapTrackerHandler),
	('/rollback', RollbackHandler),
	('/email', EmailHandler),
	('/milestones', Milestones),
	('/addMilestone', AddMilestone),
	('/deleteMilestone', DeleteMilestone),
	('/modifyMilestone', ModifyMilestone),
	('/checkMilestones', CheckMilestones),
	('/teacher_names', TeacherNameHandler),
	('/student_names', StudentNameHandler),
	('/reset', ResetHandler),
	('/Laps.xls', ExportAllHandler),
	('/view_all', ViewAllHandler),
], debug=True)