from string import Template
from models import Teacher, Milestone
from google.appengine.api import mail
import webapp2
import logging
from datetime import date
from google.appengine.api import app_identity

# Handler that sends a report of each teacher and how many 
# miles remaining before reaching their next milestone goal
# This handler should only be called by a cron task
class EmailHandler(webapp2.RequestHandler):
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
            teachers = Teacher.query()

            # iterate through list of teachers
            for result in teachers:
                # get the current teacher's total miles
                miles = result.totalClassMiles

                # get the current teacher's current milestone

                current_milestone = (result.currentMilestone).get()

                # get the progress
                miles_left = current_milestone.goalMiles - miles

                # add to the body of the email
                body = body + temp.substitute(
                    teacher=result.name, 
                    city=current_milestone.city_name, 
                    progress=miles_left)


            # finish the body
            body = body + """
                    </table>
                </body>
            </html>
            """

            # set the body as the email message html and send
            app_id = app_identity.get_application_id()
            mail.send_mail_to_admins("support@"+app_id+".appspotmail.com", subject, body, html=body)

        except Exception as message:
            # Log the error.
            logging.error(message)
            raise message


# Handler that will check if any teachers have met 
# their current milestone mile target
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
            mail.send_mail_to_admins("support@"+app_id+".appspotmail.com", subject, body, html=body)
