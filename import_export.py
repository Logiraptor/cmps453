import webapp2
from xl2model import parseWorkbook
from xlrd import open_workbook
import tmpl
import json
from google.appengine.ext import ndb
import xlwt
from models import Student, Teacher, Class
from xl2model import grades, sanitize, grade_dict
import itertools

class ImportIDsHandler(tmpl.BaseHandler):
	def post(self):
		upload = self.request.get('file')
		wb = open_workbook(file_contents=upload)
		IDs = wb.sheet_by_name("IDs")
		nrows = IDs.nrows
		students = []
		teachers = {}
		for i in xrange(1, nrows):
			row = IDs.row_values(i)
			# id name teacher grade
			s = Student(
				id=int(row[0]),
				studentID=int(row[0]),
				name=sanitize(row[1]),
				grade=str(sanitize(row[3])),
				cementLaps=0,
				grassLaps=0,
			)
			s.teacher_name = sanitize(row[2])
			students.append(s)

		for s in students:
			if s.teacher_name in teachers:
				s.teacher = teachers[s.teacher_name].key
			else:
				t = Teacher(
					id=s.teacher_name, 
					name=s.teacher_name,
				)
				t.put()
				teachers[s.teacher_name] = t
				s.teacher = t.key

		ndb.put_multi(students)

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

class ExportSingleHandler(tmpl.BaseHandler):
	def get(self):
		student_id = self.request.get('id')
		key = ndb.Key('Student', int(student_id))
		student = key.get()
		data = student.to_dict()
		data.update({
			'_teacher': student.teacher.get(),
		})
		self.render('html/view_single.html', data)

class ExportAllHandler(tmpl.BaseHandler):
	def get(self):
		self.response.headers['Content-Type'] =  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
		exportAll(self.response.out)

def exportAll(stream):
	students = list(Student.query())
	for s in students:
		s._teacher = s.teacher.get()

	wb = xlwt.Workbook()

	# Group students by teacher name
	students = sorted(students, key=lambda s: s._teacher.name)
	classes_by_teacher = itertools.groupby(students, key=lambda s: s._teacher.name)
	classes_by_teacher = map(lambda x: (x[0], list(x[1])), classes_by_teacher)

	# Determines which sheet a class belongs in
	def determine_sheet(c):
		select_grade = lambda s: s.grade
		grades = list(set(map(select_grade, c[1])))
		if len(grades) == 1:
			return grade_dict[int(float(grades[0]))]
		return 'Misc'

	# Sort by sheet
	sheets_per_class = sorted(classes_by_teacher, key=determine_sheet)
	sheets_by_class = itertools.groupby(sheets_per_class, key=determine_sheet)

	for sheet, clazz in sheets_by_class:

		sheet = wb.add_sheet(sheet)

		row = 0
		for teacher, teacher_students in clazz:
			printClassHeader(sheet, row, teacher)
			row += 2
			start_row = row + 1
			for student in teacher_students:
				sheet.write(row, 0, student.name)
				sheet.write(row, 1, student.cementLaps)
				sheet.write(row, 2, xlwt.Formula('QUOTIENT(B%d,4)' % (row+1)))
				sheet.write(row, 3, student.grassLaps)
				sheet.write(row, 4, xlwt.Formula('QUOTIENT(D%d,10.5)' % (row+1)))
				sheet.write(row, 5, xlwt.Formula('SUM(C%d,E%d)'%(row+1,row+1)))
				row += 1
			sheet.write(row, 0, 'Class Total')
			sheet.write(row, 1, xlwt.Formula('SUM(B%d:B%d)'%(start_row, row)))
			sheet.write(row, 2, xlwt.Formula('QUOTIENT(B%d,4)' % (row+1)))
			sheet.write(row, 3, xlwt.Formula('SUM(D%d:D%d)'%(start_row, row)))
			sheet.write(row, 4, xlwt.Formula('QUOTIENT(D%d,10.5)' % (row+1)))
			sheet.write(row, 5, xlwt.Formula('SUM(C%d,E%d)'%(row+1,row+1)))
			row += 2



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

	wb.save(stream)

def printClassHeader(sheet, row, teacher_name):
	sheet.write(row, 1, 'Grass Track')
	sheet.write(row+1, 1, 'Laps')
	sheet.write(row+1, 2, 'Miles')

	sheet.write(row, 3, 'Cement Track')
	sheet.write(row+1, 3, 'Laps')
	sheet.write(row+1, 4, 'Miles')
	sheet.write(row+1, 5, 'Total Miles')

	sheet.write(row+1, 0, teacher_name)