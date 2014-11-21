import cgi
import cgitb
import urllib
import smtplib

from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required, admin_required
from google.appengine.api import users
from email.mime.text import MIMEText

import webapp2

import json
from string import Template

cgitb.enable()

LOGIN_PAGE_HTML = """
<html>
	<body>
		<form action="/Main" method="post">
			<div>Username:<textarea name="username" rows="1" cols="60"></textarea></div>
			<div>Password: <textarea name="password" rows="1" cols="60"></textarea></div>
			<div><input type="submit" value="Login"></div>
		</form>
	</body>
</html>
"""

MAIN_PAGE_HTML = """
<html>
	<body>
		<form action="/import" method="post">
			<div><input type="submit" value="Import Student Data"></div>
		</form>
		<form action="/export" method="post">
			<div><input type="submit" value="Export Student Data"></div>
		</form>
		<form action="/track" method="post">
			<div><input type="submit" value="Track Labs"></div>
		</form>
		<form action="/crontask" method="post">
			<div><input type="submit" value="Email"/></div>
		</form>
	</body>
</html>
"""

# Lap Tracking Page HTML
TRACK_PAGE_HTML = """
<html>
	<body>
		<form action="/track?" method="get">
			Student ID: <input type="text" name="student_id"/>
			<input type="Submit" value="Submit"/>
		</form>
		
		<!-- Back button -->
		<form action="/" method="post">
			<input type="submit" value="Back"/>
		</form>
	</body>
</html>
"""


BACK_BUTTON = """
		<form action="/Main" method="post">
			<div><input type="submit" value="Back to Main Page"></div>
		</form>
	</body>
</html>
"""

# JSON object template
jTemp = Template('{ "studentName" : "$name", "numLaps" : $numLaps, "teacherName" : "$teacherName", "barcodeID" : $barcodeID }')
# entry = jTemp.substitute("studentName='student_name', numLaps=1234, teacherName='teacher_Name', barcodeID=1111111")

# Data structure: Student Data
class studentData(ndb.Model):
	studentName = ndb.StringProperty(indexed=True)
	totalNumLaps = ndb.IntegerProperty()
	teacherName = ndb.StringProperty(indexed=False)
	barcodeID = ndb.IntegerProperty()

class GrassTrack(ndb.Model):
	studentName = ndb.StringProperty(indexed=True)
	numLaps = ndb.IntegerProperty()
	teacherName = ndb.StringProperty(indexed=False)
	
class CementTrack(ndb.Model):
	studentName = ndb.StringProperty(indexed=True)
	numLaps = ndb.IntegerProperty()
	teacherName = ndb.StringProperty(indexed=False)
	
class MainPage(webapp2.RequestHandler):
	@login_required
	def get(self):
		self.response.write(MAIN_PAGE_HTML)
		
	def post(self):
		self.response.write(MAIN_PAGE_HTML)
		
class ImportHandler(webapp2.RequestHandler):
	@admin_required
	def post(self):
		self.response.write('<html><body>Import data to be handled here')
		self.response.write(BACK_BUTTON)
		
class ExportHandler(webapp2.RequestHandler):
	@login_required
	def post(self):
		self.response.write('<html><body>Export data to be handled here')
		self.response.write(BACK_BUTTON)


# 11/1 - working on the lap tracker handler 		
class LapTrackerHandler(webapp2.RequestHandler):
	@admin_required
	def get(self):
		# get the given information from the browser
		# (using cgi?)
		studentID = self.response.get('student_id')
		
		# check if the ID given hasn't been checked recently
		
		# if not:
			# pull number of laps for given student from db
			# increment by 1
			# save new information to the db
	@admin_required
	def post(self):
		self.response.write(TRACK_PAGE_HTML)
		
# assigns a web address to a handler
application = webapp2.WSGIApplication([
	('/', MainPage),
	('/import', ImportHandler),
	('/export', ExportHandler),
	('/track', LapTrackerHandler),
], debug=True)