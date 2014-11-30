import cgi
import cgitb
import urllib

from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required, admin_required
from google.appengine.api import users
import webapp2
from import_export import ImportHandler, ExportHandler
from google.appengine.api import mail
from datetime import date
import logging

import json
from models import Student, Teacher, Milestone
from tmpl import BaseHandler
from string import Template

from google.appengine.api import app_identity

from cron import EmailHandler

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

# Handler that will check if any teachers have met their current milestone mile target
# This should only be called by a cron task
class CheckMilestones(webapp2.RequestHandler):
	# @login_required
	def get(self):
		# a list of teachers that have completed their milestone objective
		teacherList = []

		# get a list of all teachers
		allTeachers = Teacher.query()

		# iterate through all teachers
		for teacher in allTeachers:
			# get the current milestone for the teacher
			if not teacher.currentMilestone:
				currentMilestone = Milestone.query().order(Milestone.goalMiles).get()
				teacher.currentMilestone = currentMilestone.key
				teacher.put()
			else:
				currentMilestone = teacher.currentMilestone.get()
			
			# if the totalClassMiles of a teacher is >= its current milestone goal:
			if teacher.totalClassMiles >= currentMilestone.goalMiles:
				# add the teacher to the list
				teacherList.append((teacher.name, currentMilestone.city_name))

				# find the next milestone and assign it to the teacher
				nextMilestone = Milestone.query(Milestone.goalMiles > int(teacher.totalClassMiles)).order(Milestone.goalMiles).get()

				# check if there is a milestone
				if nextMilestone:
					teacher.currentMilestone = nextMilestone.key
					teacher.put()

		# if the teacherList is not empty
		if teacherList:
			# create an email to send to the teacher with the names of the teacher
			rowTemplate = Template("""
				<tr>
					<td>$teacher</td>
					<td>$milestone</td>
				</tr>
			""")


			body = """
			<html><body>
				<center><h2>Milestone Reached!</h2></center>
				The following teachers have reached their milestones:<br>
				<table width='30%' border='1'>
					<tr>
						<th>Teacher Name</th>
						<th>Milestone</th>
					</tr>
			"""

			# for every teacher name that has passed their milestone
			for t, m in teacherList:
				body = body + rowTemplate.substitute(teacher=t, milestone=m)

			body = body + """
				</table>
			</body></html>
			"""

			subject = 'A Milestone Has Been Reached! ' + str(date.today())
			app_id = app_identity.get_application_id()
			print body
			mail.send_mail_to_admins("support@"+app_id+".appspotmail.com", subject, body)

class TeacherNameHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		self.response.out.write(json.dumps([t.name for t in Teacher.query()]))

class StudentNameHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		students = list(Student.query(Student.teacher==self.request.get('teacher')))
		self.response.out.write(json.dumps([s.to_dict() for s in students]))

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
], debug=True)