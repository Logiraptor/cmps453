import webapp2
from xl2model import parseWorkbook
from xlrd import open_workbook
import tmpl
import json
from google.appengine.ext import ndb
import xlwt
from models import Student
from xl2model import grades
import itertools

class ImportHandler(tmpl.BaseHandler):
	def get(self):
		self.render('html/import.html', {})
	def post(self):
		upload = self.request.get('file')
		wb = open_workbook(file_contents=upload)
		classes, errors = parseWorkbook(wb)

		for c in classes:
			c.teacher.put()
			for s in c.students:
				s.teacher = c.teacher.key

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

class ExportAllHandler(tmpl.BaseHandler):
	def get(self):
		students = list(Student.query())
		for s in students:
			s._teacher = s.teacher.get()

		print len(students)

		wb = xlwt.Workbook()


		# Construct Each Grade Sheet
		for num, name in grades:
			sheet = wb.add_sheet(name)
			grade_students = filter(lambda x: int(float(x.grade)) == num, students)
			print len(students)
			grade_students = sorted(grade_students, key=lambda s: s._teacher.name)
			print len(students)
			students_by_teacher = itertools.groupby(grade_students, key=lambda s: s._teacher.name)
			print len(students)

			row = 0
			for teacher, teacher_students in students_by_teacher:
				printClassHeader(sheet, row, teacher)
				row += 2
				start_row = row + 1
				for student in teacher_students:
					sheet.write(row, 0, student.name)
					sheet.write(row, 1, student.laps1)
					sheet.write(row, 2, xlwt.Formula('QUOTIENT(B%d,4)' % (row+1)))
					sheet.write(row, 3, student.laps2)
					sheet.write(row, 4, xlwt.Formula('QUOTIENT(D%d,10.5)' % (row+1)))
					sheet.write(row, 5, xlwt.Formula('SUM(C%d,E%d)'%(row+1,row+1)))
					row += 1
				sheet.write(row, 0, 'Class Total')
				sheet.write(row, 1, xlwt.Formula('SUM(B%d:B%d)'%(start_row, row)))
				sheet.write(row, 2, xlwt.Formula('QUOTIENT(B%d,4)' % (row+1)))
				sheet.write(row, 3, xlwt.Formula('SUM(D%d:D%d)'%(start_row, row)))
				sheet.write(row, 4, xlwt.Formula('QUOTIENT(D%d,10.5)' % (row+1)))
				sheet.write(row, 5, xlwt.Formula('SUM(C%d,E%d)'%(row+1,row+1)))

		# Construct IDs sheet
		IDs = wb.add_sheet('IDs')

		IDs.write(0, 0, 'Student Id')
		IDs.write(0, 1, 'Student Name')
		IDs.write(0, 2, 'Teacher')
		IDs.write(0, 3, 'Grade')

		for i, student in enumerate(students):
			IDs.write(i+1, 0, student.studentID)
			IDs.write(i+1, 1, student.name)
			IDs.write(i+1, 2, student._teacher.name)
			IDs.write(i+1, 3, int(float(student.grade)))


		self.response.headers['Content-Type'] =  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		wb.save(self.response.out)

def printClassHeader(sheet, row, teacher_name):
	sheet.write(row, 1, 'Grass Track')
	sheet.write(row+1, 1, 'Laps')
	sheet.write(row+1, 2, 'Miles')

	sheet.write(row, 3, 'Cement Track')
	sheet.write(row+1, 3, 'Laps')
	sheet.write(row+1, 4, 'Miles')
	sheet.write(row+1, 5, 'Total Miles')

	sheet.write(row+1, 0, teacher_name)