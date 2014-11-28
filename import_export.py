import webapp2
from xl2model import parseWorkbook
from xlrd import open_workbook
import tmpl
import json
from google.appengine.ext import ndb

class ImportHandler(tmpl.BaseHandler):
	def get(self):
		self.render('html/import.html', {})
	def post(self):
		upload = self.request.get('file')
		wb = open_workbook(file_contents=upload)
		classes, errors = parseWorkbook(wb)
		for c in classes:
			for s in c.students:
				s.teacher = c.teacher.name
		all_students = sum([c.students for c in classes], [])
		ndb.put_multi(all_students)
		self.render('html/view_all.html', {
			'classes': classes,
			'errors': errors,
		})

class ExportHandler(tmpl.BaseHandler):
	def get(self):
		self.render('html/export.html', {})
	def post(self):
		self.response.write('<html><body>Export data to be handled here')
		self.response.write(BACK_BUTTON)
