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
from models import Student
from tmpl import BaseHandler

cgitb.enable()

BACK_BUTTON = """
		<a href="/"><button>Back To Main Page</button></a>
	</body>
</html>
"""

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

class MainPage(BaseHandler):
	@login_required
	def get(self):
		self.render('html/index.html', {})

# Handler that sends a report of each teacher and how many miles remaining before reaching their next milestone goal
# This handler should only be called by a cron task
class EmailHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		try:
			# template variable
			temp = Template("""
				<tr>
					<td> $teacher </td>
					<td> $city </td>
					<td> $progress </td>
				</tr>
				""")

			subject = 'Weekly Milestone Progress Report: ' + str(date.today())
			# create an EmailMessage object
			eMessage = mail.EmailMessage(sender = 'dmeche520@gmail.com', subject = subject)
			user = users.get_current_user()
			eMessage.to = user.email()
			#eMessage.to = <teacher_email>
			
			
			body = """
			<html>
				<body>
					<center><h2>WEEKLY PROGRESS REPORT</h2></center>
					<table style="width:75%">
						<tr>
							<td><b>Teacher Name</b></td>
							<td><b>Current Milestone</b></td>
							<td><b>Miles To Go To Reach Milestone</b></td>
						</tr>
			"""

			# get all of the teacher from the database
			q = Teacher.query()

			# iterate through list of teachers
			for result in q.iter():
				# get the current teacher's total miles
				miles = result.getTotalMiles()

				# get the current teacher's current milestone
				# key.get()
				currentMilestone = (result.currentMilestone).get()

				# get the progress
				mileProgress = currentMilestone.goalMiles - totalClassMiles

				# add to the body of the email
				body = body + temp.substitute(teacher = result.name, city = currentMilestone.city_name, progress = mileProgress)


			# finish the body
			body = body + """
					</table>
				</body>
			</html>
			"""

			# set the body as the email message html and send
			eMessage.body = body
			eMessage.html = body
			eMessage.send()

			self.response.out.write('Email sent')
		except Exception as message:
					# Log the error.
					logging.error(message)
					# Display an informative message to the user.
					self.response.out.write('The email could not be sent. Please try again later.')
					self.response.write(ERROR_FORM % message)

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
			laps = self.request.get('laps')

			# if the user has input something for BOTH fields
			if city and laps:
				newMilestone = Milestone(id = city, city_name = city, goalMiles = int(laps))
				newMilestone.put()

			self.redirect('/milestones')
		except Exception, e:
			logging.error(e)
			self.response.out.write('Error adding milestone to datastore!')
			self.response.out.write(e)

# Handler that deletes a milestone from the datastore
class DeleteMilestone(webapp2.RequestHandler):
	@admin_required
	def get(self):
		try:
			# get the city name of the milestone that they wish to delete
			deleteChoice = self.request.get('cityName')

			#toDelete = Milestone.query(Milestone.city_name == deleteChoice)
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
		chosenCity = self.request.get('cityName')

		chosenMilestone = Milestone.query(Milestone.city_name == chosenCity).get()

		self.render('html/modifyMilestone.html', {
			'milestone' : chosenMilestone
			})

	def post(self):
		chosenCity = self.request.get('cityName')
		chosenMilestone = Milestone.query(Milestone.city_name == chosenCity).get()

		try:
			# get the new values
			newCity = self.request.get('city')
			newMiles = self.request.get('miles')

			# update the milestone and add changes to datastore
			chosenMilestone.city_name = newCity
			chosenMilestone.goalMiles = int(newMiles)
			chosenMilestone.put()

			self.redirect('milestones')
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
	@admin_required
	def get(self):
		# a list of teachers that have completed their milestone objective
		teacherList = []

		# get a list of all teachers
		allTeachers = Teacher.query()

		# iterate through all teachers
		for teacher in allTeachers:
			# get the current milestone for the teacher
			currentMilestone = teacher.currentMilestone.get()
			
			# if the totalClassMiles of a teacher is >= its current milestone goal:
			if teacher.totalClassMiles >= currentMilestone.goalMiles:
				# add the teacher to the list
				teacherList.append(teacher.name)

				# find the next milestone and assign it to the teacher
				nextMilestone = Milestone.query(Milestone.goalMiles > int(teacher.totalClassMiles)).get()

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
				</tr>
			""")

			subject = 'A Milestone Has Been Reached! ' + str(date.today())
			mailMessage = mail.EmailMessage(sender='dmeche520@gmail.com', subject=subject)
			# mailMessage.to = <teacher_email>
			user = users.get_current_user()
			mailMessage.to = user.email()

			body = """
			<html><body>
				<center><h2>Milestone Reached!</h2></center>
				The following teachers have reached their milestones:<br>
				<table width='30%' border='1'>
					<tr>
						<th>Teacher Name</th>
					</tr>
			"""

			# for every teacher name that has passed their milestone
			for t in teacherList:
				body = body + rowTemplate.substitute(teacher=t)

			body = body + """
				</table>
			</body></html>
			"""

			# attach the body to the EmailMessage and send
			mailMessage.body = body
			mailMessage.html = body
			mailMessage.send()

		self.redirect('/')

class TeacherNameHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		self.response.out.write(json.dumps(['Radle', 'Kumar']))

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