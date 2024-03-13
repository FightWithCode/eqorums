# python imports
import os
import smtplib, ssl
import celery
import json
import requests
from datetime import timedelta
from time import sleep
from celery import shared_task
from websockets.models import AppNotification
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from email.mime.base import MIMEBase

# django imports
from django.db.models import Q
from django.template import Context, Template
from datetime import datetime, timedelta
from django.template.loader import get_template
from django.conf import settings

# models import
from openposition.models import (
	OpenPosition,
	Interview,
	CandidateAssociateData
)
from dashboard.models import Profile, EmailTemplate
from candidates.models import Candidate
from clients.models import ClientPackage, Client
from hiringgroup.models import HiringGroup

@shared_task()
def send(subject, html_content, content_type, recipient_list, reply_to, sender_name, filename_event=None, cc=""):
	recipients = ", ".join(recipient_list)
	port = 465  # For SSL
	password = settings.EMAIL_HOST_PASSWORD #sender email password
	sender_email = "noreply@qorums.com"
	message = MIMEMultipart('alternative')
	message['Subject'] = subject
	message['To'] = recipients
	message['From'] = formataddr(("{} - Qorums Notification".format(sender_name), sender_email))
	message['Reply-To'] = reply_to
	message["Cc"] = cc
	message.add_header("X-Priority","1 (High)")
	if content_type == 'html':
		message.attach(MIMEText(html_content, 'html'))
	else:
		message.attach(MIMEText(html_content))
	# print(os.getcwd())
	if filename_event:
		part = MIMEBase('application', "octet-stream")
		part.set_payload(open('/home/ubuntu/ts_2_backend/'+'invite.ics', "rb").read())
		part.add_header('Content-Disposition', 'attachment; filename="invite.ics"')
		message.attach(part)

		# with open('/home/ubuntu/ts_2_backend/'+filename_event, "r") as file:
		# 	print('in with')
		# 	message.attach(MIMEText(file.read(), 'text/calendar'))
	# 	# with open(filename_event, "rb") as fil:
		# 	part = MIMEApplication(
		# 		fil.read(),
		# 		Name=basename(f)
		# 	)
		# part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
		# message.attach(filename_event, 'text/calendar')
	server = smtplib.SMTP_SSL("smtp.gmail.com", port)
	server.login(sender_email, password)
	server.sendmail(sender_email, recipient_list, message.as_string())
	server.quit()


@shared_task()
def submited_email(cao_id, subject, html_content, content_type, recipient_list, reply_to, sender_name, filename_event=None, cc=""):
	sleep(180)
	try:
		CandidateAssociateData.objects.get(id=cao_id)
		port = 465  # For SSL
		password = settings.EMAIL_HOST_PASSWORD #sender email password
		sender_email = "noreply@qorums.com"
		message = MIMEMultipart('alternative')
		message['Subject'] = subject
		message['To'] = recipient_list
		message['From'] = formataddr(("{} - Qorums Notification".format(sender_name), sender_email))
		message['Reply-To'] = reply_to
		message["Cc"] = cc
		message.add_header("X-Priority","1 (High)")
		if content_type == 'html':
			message.attach(MIMEText(html_content, 'html'))
		else:
			message.attach(MIMEText(html_content))
		# print(os.getcwd())
		if filename_event:
			part = MIMEBase('application', "octet-stream")
			part.set_payload(open('/home/ubuntu/ts_2_backend/'+'invite.ics', "rb").read())
			part.add_header('Content-Disposition', 'attachment; filename="invite.ics"')
			message.attach(part)
		server = smtplib.SMTP_SSL("smtp.gmail.com", port)
		server.login(sender_email, password)
		server.sendmail(sender_email, recipient_list, message.as_string())
		server.quit()
	except:
		pass


@shared_task()
def invite_user(subject, html_content, content_type, recipient_list, reply_to, sender_name):
	print("slept for 180 sec")
	sleep(180)
	print("data is: ", subject, html_content, content_type, recipient_list)
	try:
		print("iminsidetry")
		port = 465  # For SSL
		password = settings.EMAIL_HOST_PASSWORD #sender email password
		sender_email = "noreply@qorums.com"
		message = MIMEMultipart('alternative')
		message['Subject'] = subject
		message['To'] = recipient_list
		message['From'] = formataddr(("{} - Qorums Notification".format(sender_name), sender_email))
		message['Reply-To'] = reply_to
		message.add_header("X-Priority","1 (High)")
		if content_type == 'html':
			message.attach(MIMEText(html_content, 'html'))
		else:
			message.attach(MIMEText(html_content))
		# print(os.getcwd())
		server = smtplib.SMTP_SSL("smtp.gmail.com", port)
		server.login(sender_email, password)
		server.sendmail(sender_email, recipient_list, message.as_string())
		print("mail sent")
		server.quit()
	except Exception as e:
		print("iminsideexcept")
		print(e)


@shared_task()
def send_app_notification(username, message):
	AppNotification.objects.create(username=username, message=message)
	url = "https://app.qorums.com/api/send/"
	payload = json.dumps({
	  "to": username,
	  "message": {
	    "msg": message
	  }
	})
	headers = {
	  'Content-Type': 'application/json'
	}
	rsp = requests.request("POST", url, headers=headers, data=payload)


@shared_task()
def push_notification(users, title, text):
	url = "https://management-api.wonderpush.com/v1/deliveries?accessToken=e34fe95aa9ead30db570baa5ce1c91ccea40f9555939f488809596bd593f8327"
	payload = {
	    "targetUserIds": users,
	    "notification": {"alert": {
	            "title": title,
	            "text": text
	        }}
	}
	headers = {
	    "accept": "text/plain",
	    "content-type": "application/json"
	}
	response = requests.post(url, json=payload, headers=headers)


@shared_task
def send_interview_reminder():
	for interview in Interview.objects.filter(Q(initial_informed=False) | Q(informed=False)).filter(disabled=False):
		if datetime.today()+timedelta(minutes=30) > interview.interview_date_time and interview.informed == False:
			interview.informed = True
			interview.save()
			try:
				candidate_obj = interview.candidate
				openposition_obj = OpenPosition.objects.get(id=interview.op_id.id)
				client_obj = Client.objects.get(id=openposition_obj.client)
				try:
					profile = Profile.objects.get(user=interview.htm.all().last())
					reply_to = profile.email
					sender_name = profile.user.get_full_name()
				except:
					reply_to = 'noreply@qorums.com'
					sender_name = 'No Reply'
				subject = 'Interview Reminder - {} - {}'.format(client_obj.company_name, openposition_obj.position_title)
				try:
					dur = int(interview.duration / 60)
				except:
					dur = 30
				d = {
					"candidate_name": "{} {}".format(candidate_obj.name, candidate_obj.last_name),
					"client_name": client_obj.company_name,
					"time": interview.interview_date_time.strftime("%I:%M %p"),
					"position_name": openposition_obj.position_title,
					"address": interview.zoom_link,
					"sender_name": sender_name,
					"time_duration": dur
				}
				email_from = 'noreply@qorums.com'
				# htmly_b = get_template('interview_reminder.html')
				try:
					email_template = EmailTemplate.objects.get(client__id=interview.op_id.client, name="Interview Reminder to Candidate")
					template = Template(email_template.content)
					context = Context(d)
				except:
					email_template = EmailTemplate.objects.get(client=None, name="Interview Reminder to Candidate")
					template = Template(email_template.content)
					context = Context(d)
				html_content = template.render(context)
				send.delay(subject, html_content, 'html', [candidate_obj.email], reply_to, sender_name)
				diff = interview.interview_date_time - datetime.now()
			except Exception as e:
				print(str(e))
		elif datetime.today()+timedelta(hours=4) > interview.interview_date_time and interview.initial_informed == False:
			interview.initial_informed = True
			interview.save()
			try:
				candidate_obj = interview.candidate
				openposition_obj = OpenPosition.objects.get(id=interview.op_id.id)
				client_obj = Client.objects.get(id=openposition_obj.client)
				try:
					profile = Profile.objects.get(user=interview.htm.all().last())
					reply_to = profile.email
					sender_name = profile.user.get_full_name()
				except:
					reply_to = 'noreply@qorums.com'
					sender_name = 'No Reply'
				subject = 'Interview Reminder - {} - {}'.format(client_obj.company_name, openposition_obj.position_title)
				try:
					dur = int(interview.duration / 60)
				except:
					dur = 30
				d = {
					"candidate_name": "{} {}".format(candidate_obj.name, candidate_obj.last_name),
					"client_name": client_obj.company_name,
					"time": interview.interview_date_time.strftime("%I:%M %p"),
					"position_name": openposition_obj.position_title,
					"address": interview.zoom_link,
					"sender_name": sender_name,
					"time_duration": dur
				}
				email_from = 'noreply@qorums.com'
				# htmly_b = get_template('interview_reminder.html')
				# text_content = ""
				# html_content = htmly_b.render(d)
				try:
					email_template = EmailTemplate.objects.get(client__id=interview.op_id.client, name="Interview Reminder to Candidate")
					template = Template(email_template.content)
					context = Context(d)
				except:
					email_template = EmailTemplate.objects.get(client=None, name="Interview Reminder to Candidate")
					template = Template(email_template.content)
					context = Context(d)
				html_content = template.render(context)
				send.delay(subject, html_content, 'html', [candidate_obj.email], reply_to, sender_name)
				diff = interview.interview_date_time - datetime.now()
			except Exception as e:
				print(str(e))


@shared_task
def daily_interview_reminder():
	today = datetime.today().date()
	scheduled_today = Interview.objects.filter(interview_date_time__date=today, disabled=False)
	for ae in Profile.objects.filter(is_ae=True):
		for client in Client.objects.filter(id__in=json.loads(ae.client)):
			for op in OpenPosition.objects.filter(client=client.id, filled=False, drafted=False, archieved=False, trashed=False):
				interviews_count = Interview.objects.filter(op_id=op).filter(disabled=False).count()
				send_app_notification.delay(ae.user.username, 'There are {} interviews scheduled for today across your accounts.'.format(interviews_count))
				push_notification.delay([ae.user.username], 'Qorums Notification', 'There are {} interviews scheduled for today across your accounts.'.format(interviews_count))
				
				group_obj = HiringGroup.objects.get(group_id=op.hiring_group)
				hod_interviews = Interview.objects.filter(op_id=op, htm__in=[group_obj.hod_profile]).filter(disabled=False).count()
				
				# Notifications to HOD
				if group_obj.hod_profile:
					hod_profile = group_obj.hod_profile
					send_app_notification.delay(hod_profile.user.username, 'You are scheduled for {} interviews today'.format(hod_interviews))
					push_notification.delay([hod_profile.user.username], 'Qorums Notification', 'You are scheduled for {} interviews today'.format(hod_interviews))
					send_app_notification.delay(hod_profile.user.username, 'Your team has a total of {} interviews sheduled for today.'.format(interviews_count - hod_interviews))
					push_notification.delay([hod_profile.user.username], 'Qorums Notification', 'Your team has a total of {} interviews sheduled for today.'.format(interviews_count - hod_interviews))

				# Notification to HR
				try:
					if group_obj.hr_profile:
						hr_prifle = group_obj.hr_profile
						send_app_notification.delay(hr_prifle.user.username, 'Your team has a total of {} interviews sheduled for today.'.format(interviews_count))
						push_notification.delay([hr_prifle.user.username], 'Qorums Notification', 'Your team has a total of {} interviews sheduled for today.'.format(interviews_count))
				except:
					pass
				
				# Notifications to HTMs
				for htm in group_obj.members_list.all():
					if htm == group_obj.hod_profile or htm == group_obj.hr_profile:
						pass
					else:
						interviews_count = Interview.objects.filter(op_id=op, htm__in=[htm]).filter(disabled=False).count()
						send_app_notification.delay(ae.user.username, 'You are scheduled for {} interviews today.'.format(interviews_count))
						push_notification.delay([ae.user.username], 'Qorums Notification', 'You are scheduled for {} interviews today'.format(interviews_count))


@shared_task
def delete_interview():
	day_before = datetime.now() - timedelta(days=1)
	passed_scheduls = Interview.objects.filter(interview_date_time__lte=day_before)
	for shedule in passed_scheduls:
		shedule.disabled = True
		shedule.save()


@shared_task
def increase_deadline():
	open_position = OpenPosition.objects.get(id=settings.EXAMPLE_POSITION)
	if open_position.target_deadline <= datetime.today():
		open_position.target_deadline = timedelta(days=7)
		open_position.save()