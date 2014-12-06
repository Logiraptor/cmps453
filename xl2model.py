import xlrd
import collections
import itertools
from models import Student, Teacher, Class

grade_sheets = ['pk', 'k', '1st', '2nd', '3rd', '4th', '5th', '6th', 'Misc']
grade_nums = [-1, 0, 1, 2, 3, 4, 5, 6, 7]
grades = zip(grade_nums, grade_sheets)
grade_dict = dict(grades)
typo_error = 'no id found for %s, but it may be a misspelling of %s (%.0f%% confidence)'
missing_error = '%s appears in the IDs sheet, but not in %s\'s class'
missing_id_error = '%s appears in %s\'s class, but not in the IDs sheet'

missing_class_error = '%s only appears in the IDs sheet.'
available_class_error = '%s does not appear in the IDs sheet.'

def parseWorkbook(wb):
	'''
		parseWorkbook accepts an xlrd.Workbook object
		and parses all the contained students into 
		Student objects. The result is a list of Class objects 
		and a list of error strings.
	'''

	errors = []
	sheets = []
	for n in grades:
		try:
			sheets.append(wb.sheet_by_name(n[1]))
		except xlrd.XLRDError, e:
			errors.append('Missing Sheet "%s"' % n[1])

	sheets  = zip(sheets, grade_sheets)
	classes = []
	for sheet, name in sheets:
		clss = parseSheet(sheet)
		for c in clss:
			c.teacher.grade = name
		classes += clss
	IDs     = wb.sheet_by_name("IDs")

	students = []
	id_rows = (IDs.row(i) for i in xrange(1, IDs.nrows))
	for row in id_rows:
		s = Student(
			studentID=int(row[0].value),
			id=int(row[0].value),
			name=sanitize(str(row[1].value)),
			grade=sanitize(str(row[3].value)),
		)
		s.teacher_name = sanitize(str(row[2].value)).split()[0]
		students.append(s)
	print 'Found', len(students), 'Students'

	missingStudents = []
	missingTableEntries = []
	for student in students:
		clazz = None
		# print '-----'
		for c in classes:
			# print repr(c.teacher.name)
			if nameEquals(c.teacher.name, student.teacher_name):
				clazz = c
				c.used = True
				break
		if not clazz:
			# print 'missing', repr(student.teacher_name)
			missingStudents.append(student)
			continue
		# print '-----'

		tableEntry = None
		tableEntryI = None
		for i, s in enumerate(clazz.students):
			if nameEquals(s.name, student.name):
				tableEntry = s
				tableEntryI = i
				break
		if not tableEntry:
			# Unsolvable error condition
			missingTableEntries.append(student)
			continue
		student.cementLaps = tableEntry.cementLaps
		student.grassLaps = tableEntry.grassLaps
		clazz.students[tableEntryI] = student

	missingStudents = sorted(missingStudents, key=lambda s: s.teacher_name)
	missingClasses = itertools.groupby(missingStudents, key=lambda s: s.teacher_name)
	availClasses = filter(lambda c: not c.used, classes)

	missingIDs = []
	for c in classes:
		for s in c.students:
			if not s.studentID:
				s.teacher_name = c.teacher.name
				missingIDs.append(s)
	
	missingErrors = [missing_class_error % s[0] for s in missingClasses]
	availErrors = [available_class_error % s.teacher.name for s in availClasses]
	errors += missingErrors
	errors += availErrors
	errors += [missing_id_error % (s.name, s.teacher_name) for s in missingIDs]
	errors += [missing_error % (s.name, s.teacher_name) for s in missingTableEntries]

	errors = sorted(errors)

	if errors:
		return [], errors

	errors = []
	
	return classes, errors

def nameEquals(a, b):
	# if 'Patin' in a:
	# 	print repr(a), repr(b)
	partsA = filter(lambda n: len(n)>1, a.split())
	partsB = filter(lambda n: len(n)>1, b.split())
	if len(partsA) == len(partsB):
		return partsA == partsB
	# make a shorter
	if len(partsA) > len(partsB):
		t = partsB
		partsB = partsA
		partsA = t
	return all(a in partsB for a in partsA)

def levenshteinDistance(s1,s2):
    if len(s1) > len(s2):
        s1,s2 = s2,s1
    distances = range(len(s1) + 1)
    for index2,char2 in enumerate(s2):
        newDistances = [index2+1]
        for index1,char1 in enumerate(s1):
            if char1 == char2:
                newDistances.append(distances[index1])
            else:
                newDistances.append(1 + min((distances[index1],
                                             distances[index1+1],
                                             newDistances[-1])))
        distances = newDistances
    return distances[-1]

def sanitize(s):
	if isinstance(s, str) or isinstance(s, unicode):
		return ' '.join(s.strip().split())
	return s

def parseSheet(sheet):
	tables = findTables(sheet)
	classes = [parseTable(sheet, t[0], t[1]) for t in tables]
	return classes

def parseTable(sheet, row, col):
	c = Class()
	state = startState
	while state != None:
		state, row = state(c, sheet, col, row)
	return c

def isHeader(row):
	laps = row[1].value
	miles = row[2].value
	if type(laps) != unicode:
		return False
	if type(miles) != unicode:
		return False
	return 'Laps' == laps and 'Miles' == miles

def isEmpty(row):
	return all([x.value == '' for x in row])

def startState(cl, sheet, c, r):
	if r >= sheet.nrows:
		return None, r
	row = sheet.row(r)
	if isEmpty(row[c:]):
		return startState, r+1
	if isHeader(row[c:]):
		return findTeacher, r

	return startState, r+1

def findTeacher(cl, sheet, c, r):
	row = sheet.row(r)

	if row[c].value.strip() == '':
		return findTeacher, r+1
	else:
		teacher = sanitize(row[c].value)
		cl.teacher = Teacher(id=teacher, name=teacher)
		return readStudents, r+1

def readStudents(cl, sheet, c, r):
	row = sheet.row(r)
	if not isinstance(row[c].value, collections.Iterable):
		return None, r
	if 'Total' in row[c].value:
		return None, r

	if type(row[c+1].value) != float:
		laps = 0.0
	else:
		laps = row[c+1].value

	if len(row) - c < 6:
		cementLaps = 0.0 
	elif type(row[c+3].value) != float:
		cementLaps = 0.0
	else:
		cementLaps = row[c+3].value

	cl.students.append(Student(
			name=row[c].value,
			cementLaps=cementLaps,
			grassLaps=laps,
		))
	return readStudents, r+1


def findTables(sheet):
	tables = []
	for i, row in ((n, sheet.row(n)) for n in xrange(sheet.nrows)):
		for j, col in enumerate(row):
			if len(row) > j + 1:
				if col.value == "Laps" and row[j+1].value == "Miles":
					if not (i-1, j-3) in tables:
						tables.append((i-1, j-1))
	return tables

