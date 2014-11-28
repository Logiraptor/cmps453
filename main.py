import cgi
import cgitb
import urllib

from google.appengine.ext import ndb
from webapp2_extras.appengine.users import login_required, admin_required
from google.appengine.api import users
import webapp2
from import_export import ImportHandler, ExportHandler

import json
from models import Student
from tmpl import BaseHandler

# Data structure: Student Data
class studentData(ndb.Model):
	name = ndb.StringProperty(indexed=True)
	numLaps = ndb.IntegerProperty()
	teacherName = ndb.StringProperty(indexed=False)
	teacherName_lower = ndb.ComputedProperty(lambda self: self.teacherName.lower())
	barcodeID = ndb.IntegerProperty()

class MainPage(BaseHandler):
	@admin_required
	def get(self):
		self.render('html/index.html', {})
		
class LapTrackerHandler(BaseHandler):
	@admin_required
	def get(self):
		self.render('html/tracker.html', {})

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
	('/teacher_names', TeacherNameHandler),
	('/student_names', StudentNameHandler),
], debug=True)