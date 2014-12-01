import cgi
import cgitb
import urllib

from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required, admin_required
from google.appengine.api import users
import webapp2
from import_export import ImportHandler, ExportHandler, ExportAllHandler
from google.appengine.api import mail
from datetime import date
import logging

import json
from models import Student, Teacher, Milestone
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

# TODO: ensure all urls are protected with admin_required
class MainPage(BaseHandler):
	@admin_required
	def get(self):
		self.render('html/index.html', {})

# Handler that lists the milestones currently in the datastore
class Milestones(BaseHandler):
	@admin_required
	def get(self):
		# get all milestones
		milestones = Milestone.query()

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
				newMilestone = Milestone(id = city, city_name = city, goalMiles = int(miles))
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
			chosen_milestone.goalMiles = int(newMiles)
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
		self.render('html/tracker.html', {})

class TeacherNameHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		self.response.out.write(json.dumps([t.name for t in Teacher.query()]))

class StudentNameHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		key = ndb.Key('Teacher', self.request.get('teacher'))
		students = list(Student.query(Student.teacher==key))
		self.response.out.write(json.dumps([{'id':s.studentID, 'name':s.name} for s in students]))

# assigns a web address to a handler
application = webapp2.WSGIApplication([
	('/', MainPage),
	('/import', ImportHandler),
	('/export', ExportHandler),
	('/track', LapTrackerHandler),
	('/email', EmailHandler),
	('/milestones', Milestones),
	('/addMilestone', AddMilestone),
	('/deleteMilestone', DeleteMilestone),
	('/modifyMilestone', ModifyMilestone),
	('/checkMilestones', CheckMilestones),
	('/teacher_names', TeacherNameHandler),
	('/student_names', StudentNameHandler),
	('/Laps.xlsx', ExportAllHandler),
], debug=True)