import cgi
import cgitb
import urllib

from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required, admin_required
from google.appengine.api import users
import webapp2
from import_export import ImportHandler, ExportHandler

import json
from string import Template

from tmpl import BaseHandler

cgitb.enable()

BACK_BUTTON = """
		<form action="/Main" method="post">
			<div><input type="submit" value="Back to Main Page"></div>
		</form>
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
	totalClassMiles = ndb.ComputedProperty(lambda self: sum([s.total_miles for s in Student.query(Student.teacher == self.key)]))

# Data structure: Student Data
class Student(ndb.Model):
	id = ndb.IntegerProperty()
	name = ndb.StringProperty()
	teacher = ndb.KeyProperty(Teacher)
	grade = ndb.StringProperty
	laps1 = ndb.FloatProperty()
	laps2 = ndb.FloatProperty()
	total_miles = ndb.ComputedProperty(lambda self: self.laps1*0.1+self.laps2*0.25)

class MainPage(BaseHandler):
	@login_required
	def get(self):
		self.render('html/index.html', {})

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

			# create an EmailMessage object
			eMessage = mail.EmailMessage(sender = 'dmeche520@gmail.com', subject = 'Weekly Milestone Progress Report: <date>')
			user = users.get_current_user()
			eMessage.to = user.email()
			#eMessage.to = <teacher_email>
			subject = 'Weekly Milestone Progress Report: <date>'
			
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

# Handler: Milestone configuration
class ConfigureMilestones(webapp2.RequestHandler):
	@admin_required
	def get(self):
		self.response.write(CONFIG_HEADER_HTML)

		# get and write value
		boxValue = self.request.get('box')
		
		# test the value of boxValue
		if boxValue == "List":
			# get a list of all milestones
			allMilestones = Milestone.query()

			# define a template for jinja
			template_values = {
			'milestones' : allMilestones
			}

			jinjaTemplate = jinja2.Template(CONFIG_LIST_FOOTER)
			self.response.write(jinjaTemplate.render(template_values))

		elif boxValue == 'Add':
			self.redirect('/addMilestone')
		elif boxValue == 'Delete':
			# get all of the milestones
			allMilestones = Milestone.query()

			# define a template for jinja
			template_values = {
			'milestones' : allMilestones
			}

			jinjaTemplate = jinja2.Template(DELETE_HTML)
			self.response.write(jinjaTemplate.render(template_values))
		elif boxValue == 'Modify':
			# get all of the milestones
			allMilestones = Milestone.query()

			# define a template for jinja
			template_values = {
			'milestones' : allMilestones
			}

			jinjaTemplate = jinja2.Template(MODIFY_HEADER_HTML)
			self.response.write(jinjaTemplate.render(template_values))

# Handler that adds a new milestone to the datastore
class AddMilestone(webapp2.RequestHandler):
	def get(self):
		self.response.write(ADD_HTML)

		try:
			# get the city and goal
			city = self.request.get('city')
			goal = self.request.get('goal')

			# create new Milestone and store in datastore
			newMilestone = Milestone(id = city, city_name = city, goalMiles = int(goal))
			newMilestone.put()

			self.response.out.write('Milestone successfully added.')
		except Exception as e:
			logging.error(e)

# Handler that deletes a milestone from the datastore
class DeleteMilestone(webapp2.RequestHandler):
	def get(self):
		try:
			# get the city name of the milestone that they wish to delete
			deleteChoice = self.request.get('list')

			#toDelete = Milestone.query(Milestone.city_name == deleteChoice)
			q = Milestone.query()
			toDelete = q.filter(Milestone.city_name == deleteChoice).get()

			# jinja template
			deleteTemplate = {
			'city' : toDelete.city_name,
			}
			djt = jinja2.Template(SUCCESSFUL_DELETE)

			# delete from the datastore
			toDelete.key.delete()

			# display to user
			self.response.write(djt.render(deleteTemplate))
		except Exception as e:
			self.response.write(UNSUCCESSFUL_DELETE)
			self.response.out.write(e)
			logging.error(e)
		
class LapTrackerHandler(BaseHandler):
	@login_required
	def get(self):
		self.render('html/tracker.html')

# Handler that saves the changes made to a milestone
class ModifyMilestone(webapp2.RequestHandler):
	def get(self):
		chosenCity = self.request.get('choice')
		
		# get chosen milestone
		q = Milestone.query()
		chosenMilestone = q.filter(Milestone.city_name == chosenCity).get()

		# define second template
		secondTemplate = {
		'milestone' : chosenMilestone,
		}

		# output change environment
		jt = jinja2.Template(MOFIFY_FOOTER_HTML)
		self.response.write(jt.render(secondTemplate))

		try:
			# get the new values
			newCity = self.request.get('city')
			newMiles = self.request.get('miles')

			# update the milestone and put in datastore
			chosenMilestone.city_name = newCity
			chosenMilestone.goalMiles = int(newMiles)
			chosenMilestone.put()

			# write success message
			self.response.out.write('Milestone successfully modified.')
		except Exception as e:
			logging.error(e)

# assigns a web address to a handler
application = webapp2.WSGIApplication([
	('/', MainPage),
	('/import', ImportHandler),
	('/export', ExportHandler),
	('/track', LapTrackerHandler),
	('/email', EmailHandler),
	('/configMilestones', ConfigureMilestones),
	('/addMilestone', AddMilestone),
	('/deleteMilestone', DeleteMilestone),
	('/modifyMilestone', ModifyMilestone),
], debug=True)