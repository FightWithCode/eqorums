# Google Calendar
from __future__ import print_function
import pickle
import os.path
import boto3
import pytz
import random
import string
import requests
import ast
import re
from dashboard.iotum_utils import get_iotum_auth_code, create_meeting_room, get_host_and_create_meeting, end_meeting
from time import time
import jwt
import json
from allauth.account.signals import user_logged_in
from datetime import datetime, timedelta
import os
from django.core import files
from io import BytesIO
from django.db.models import F
from django.db.models import Value as V


from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Testing New Auth FLow
import google.oauth2.credentials
import google_auth_oauthlib.flow
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.conf import settings 
from django.core.mail import send_mail

# Django Imports
from rest_framework.views import APIView
from django.contrib.auth import login
from django.db.models import Count
from django.db.models.functions import ExtractMonth, Concat
from django.template import Context, Template
from django.dispatch import receiver
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import FileSystemStorage
from django.db.models import Avg
from django.db.models import Q
from django.utils.html import strip_tags
# serializers import
from openposition.serializers import (
	OpenPositionSerializer
)

from .serializers import (
	ClientSerializer,
	ProfileSerializer,
	ChangePasswordSerializer,
	HiringGroupSerializer,
	GetHiringGroupSerializer,
	PositionTitleSerializer,
	QualifyingQuestionSerializer,
	OpenPositionStageCompletionSerializer,
	CandidateSerializer,
	CandidateMarksSerializer,
	UsernameSerializer,
	DepartmentSerializer,
	CandidateStatusSerializer,
	ScheduleTemplateSerializer,
	HTMWeightageSerializer,
	ProTipSerializer,
	CandidateAssociateDataSerializer,
	EvaluationCommentSerializer,
	HTMsDeadlineSerializer,
	CustomProfileSerializer,
	EmailTemplateSerializer,
	PackageSerializer,
	ClientPackageSerializer,
	ExtraAccountsPriceSerializer,
	BillingDetailSerializer,
)
from clients.models import Client, Package, ClientPackage
from openposition.models import (
	OpenPosition,
	HTMsDeadline,
	Interview,
	CandidateMarks,
	CandidateAssociateData,
	CandidateStatus,
	PositionDoc,
	Offered,
	HTMWeightage
)
from hiringgroup.models import HiringGroup
from clients.serializers import ClientSerializer
from .models import (
	Profile,
	PositionTitle,
	QualifyingQuestion,
	OpenPositionStageCompletion,
	# Department,
	InterviewSchedule,
	TempCandidate,
	CandidatePositionDetails,
	AskedNotification,
	Hired,
	ScheduleTemplate,
	HTMAvailability,
	APIData,
	SelectedAnalyticsDashboard,
	ProTip,
	CandidateAvailability,
	EvaluationComment,
	WithdrawCandidateData,
	EmailTemplate,
	OTPRequested,
	ExtraAccountsPrice,
	BillingDetail,
	StripePayments,
	StripeWebhookData
)
from candidates.models import Candidate
from websockets.models import AppNotification
from django.contrib.auth.models import User
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.core.mail.message import EmailMultiAlternatives as MessageEmailMultiAlternatives
from ics import Calendar, Event
from rest_framework import permissions
from rest_framework.generics import UpdateAPIView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.permissions import IsAuthenticated
from knox.views import LoginView as KnoxLoginView
from . import tasks
from .utils import (
	get_openposition_data,
	get_client_openposition_data,
	get_liked_candidates_data,
	get_client_liked_candidates_data,
	get_passed_candidates_data,
	get_client_passed_candidates_data,
	get_interview_data,
	get_client_interview_data,
	daterange,
	create_email_templates,
	get_htm_specific_data,
	get_timediff,
	get_htm_flag_data
)
from demo.aws_utils import (
	delete_image
)
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
from dashboard.stripe_utils import get_or_create_stripe_customer, create_price, create_subscription, get_payment_method
from dashboard.pdf_utils import generate_pdf
from urllib.request import urlopen
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from calendar import monthrange

# Flexbooker APIs not used anymore.
from .flexbooker import get_flexb_auth_code, get_employees_detail, create_flexb_employee, get_schedules, create_schedule, update_schedule, delete_schedule

# AWS bedrock generative
from dashboard.generative import get_five_question, get_single_question

# Google APIs not used anymore.
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ID = 43428
COLORS = ["#ff0000", "#ffdd00", "#88ff00", "#7FFFD4", "#0000EE", "#8A2BE2", "#EE3B3B", "#EEC591", "#8EE5EE", "#FF6103", "#76EE00", "#6495ED", "#DC143C", "#B4EEB4", "#8B6914", "#7CFC00", "#8B5742","#191970"]
COLORS_DICT = {
	"#ff0000": "red",
	"#ffdd00": "yellow", 
	"#88ff00": "lime", 
	"#7FFFD4": "aqua", 
	"#0000EE": "blue", 
	"#8A2BE2": "blueviolet", 
	"#EE3B3B": "firebrick", 
	"#EEC591": "burlywood", 
	"#8EE5EE": "cyan", 
	"#FF6103": "orangered", 
	"#76EE00": "greenyellow", 
	"#6495ED": "cornflowerblue", 
	"#DC143C": "crimson", 
	"#B4EEB4": "darkred", 
	"#8B6914": "goldenrod", 
	"#7CFC00": "lawngreen", 
	"#8B5742": "lightsalmon",
	"#191970": "midnightblue"
}
# Utilities Functions
@receiver(user_logged_in)
def user_logged_in_(request, user, **kwargs):
	print(user.__dict__)
	try:
		candidate_obj = Candidate.objects.get(name__iexact=user.first_name + ' ' + user.last_name)
	except:
		try:
			candidate_obj = Candidate.objects.get(email_iexact=user.email)
		except:
			candidate_obj = Candidate.objects.all().last()
	candidate_obj.linkedin_first_name = user.first_name
	candidate_obj.linkedin_last_name = user.last_name
	candidate_obj.linkedin_email = user.email
	candidate_obj.save()


def update_assigned_clients():
	for i in Profile.objects.filter(roles__contains="is_ae"):
		client_list = []
		for j in Client.objects.filter(ae_assigned=i.user.username, disabled=False):
			client_list.append(j.id)
		i.client = json.dumps(client_list)
		i.save()
	return True


class AccountManagerView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			username = request.data.get("username")
			password = request.data.get("password")
			first_name = request.data.get("first_name")
			last_name = request.data.get("last_name")
			user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name)
			user.set_password(password)
			phone_number = request.data.get("phone_number")
			skype_id = request.data.get("skype_id")
			email = request.data.get("email")
			if Profile.objects.filter(email=email).exists() or Candidate.objects.filter(email=email).exists():
				return Response({'message': 'Email already exists!'}, status=status.HTTP_400_BAD_REQUEST)
			try:
				profile_photo = request.FILES['profile_photo']
			except Exception as e:
				profile_photo = None
			try:
				Profile.objects.create(user=user, phone_number=phone_number, skype_id=skype_id, email=email, roles=["is_ae"], profile_photo=profile_photo)
			except Exception as e:
				user.delete()
				return Response({'msg': str(e)}, status=status.HTTP_409_CONFLICT)
			response = {}
			response['msg'] = "added"
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		try:
			username = request.query_params.get('username')
			try:
				user_obj = User.objects.get(username=username)
				profile_obj = Profile.objects.get(user=user_obj)
			except Exception as e:
				response = {}
				response["msg"] = str(e)
				return Response(response, status=status.HTTP_204_NO_CONTENT)
			response = {}
			response["username"] = user_obj.username
			response["first_name"] = user_obj.first_name
			response["last_name"] = user_obj.last_name
			response["phone_number"] = profile_obj.phone_number
			response["skype_id"] = profile_obj.skype_id
			response["email"] = profile_obj.email
			response['profile_photo'] = profile_obj.profile_photo.url if profile_obj.profile_photo else None
			clients_list = []
			try:
				for i in json.loads(profile_obj.client):
					try:
						temp_dict =  {}
						client_obj = Client.objects.get(id=i)
						temp_dict['logo'] = client_obj.logo.url if client_obj.logo else None
						temp_dict['company_name'] = client_obj.company_name
						clients_list.append(temp_dict)
					except Exception as e:
						print(e)
			except Exception as e:
				print(e)
			response['clients'] = clients_list
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request):
		try:
			username = request.data.get("username")
			try:
				user_obj = User.objects.get(username=username)
				user_obj.first_name = request.data.get('first_name')
				user_obj.last_name = request.data.get('last_name')
				user_obj.save()
				profile_obj = Profile.objects.get(user=user_obj)
			except Exception as e:
				response = {}
				response["msg"] = str(e)
				return Response(response, status=status.HTTP_204_NO_CONTENT)
			profile_obj.phone_number = request.data.get("phone_number")
			profile_obj.skype_id = request.data.get("skype_id")
			if profile_obj.email != request.data.get("email"):
				if Profile.objects.filter(email=request.data.get("email")).exists() or Candidate.objects.filter(email=request.data.get("email")).exists():
					return Response({'message': 'Email already exists!'}, status=status.HTTP_400_BAD_REQUEST)
			profile_obj.email = request.data.get("email")
			try:
				profile_photo = request.FILES['profile_photo']
			except Exception as e:
				profile_photo = None
			profile_obj.profile_photo = profile_photo if profile_photo else profile_obj.profile_photo
			if request.data.get('profile_photo_deleted') == "true":
				profile_obj.profile_photo = None
			profile_obj.save()
			response = {}
			response["msg"] = "updated"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request):
		try:
			print("delete")
			username = request.query_params.get('username')
			user_obj = User.objects.get(username=username)
			profile_obj = Profile.objects.get(user=user_obj)
			user_obj.delete()
			clients_associated = json.loads(profile_obj.client)
			for i in clients_associated:
				client_obj = Client.objects.get(id=i)
				client_obj.ae_assigned = 'Not Assigned'
				client_obj.save()
			profile_obj.delete()
			response = {}
			response["msg"] = "deleted"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Hiring Members and Hiring Managers is same
class HiringManagerView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			if User.objects.filter(email=request.data.get("email")) or Profile.objects.filter(email=request.data.get("email")) or Candidate.objects.filter(email=request.data.get("email")):
				return Response({'msg': "Email already exists."}, status=status.HTTP_200_OK)
			username = request.data.get("username")
			password = request.data.get("password")
			npassword = request.data.get("npassword")
			first_name = request.data.get("first_name")
			last_name = request.data.get("last_name")
			user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)
			user.set_password(password)
			phone_number = request.data.get("phone_number")
			cell_phone = request.data.get("cell_phone_number")
			skype_id = request.data.get("skype_id")
			job_title = request.data.get("job_title")
			email = request.data.get("email")
			client = request.data.get("client")
			rankings = json.dumps(request.data.get('rankings', []))
			roles = ["is_htm"]
			try:
				proffile_obj = Profile.objects.create(user=user, phone_number=phone_number, cell_phone=cell_phone, skype_id=skype_id, job_title=job_title, email=email, client=client, rankings=rankings, roles=roles)
				proffile_obj.save()
			except Exception as e:
				user.delete()
				return Response({'msg': str(e)}, status=status.HTTP_409_CONFLICT)
			try:
				profile_photo = request.FILES['profile_photo']
				proffile_obj.profile_photo = profile_photo
			except Exception as e:
				pass
			proffile_obj.save()
			# if "profile_photo" in request.data and request.data.get("profile_photo") in [None, "null"]:
			# 	proffile_obj.profile_photo = None
			# 	proffile_obj.save()
			# Send mail with password and 
			try:
				client_obj = Client.objects.get(id=int(client))
				company_name = client_obj.company_name
			except:
				company_name = None
			subject = 'New User Created - Qorums'
			d = {
				"user_name": user.get_full_name(),
				"username": user.username,
				"password": npassword,
				"company": company_name
			}
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [email, ]
			try:
				email_template = EmailTemplate.objects.get(client__id=int(client), name="User created")
				template = Template(email_template.content)
			except EmailTemplate.DoesNotExist:
				email_template = EmailTemplate.objects.get(client=None, name="User created")
				template = Template(email_template.content)
			context = Context(d)
			html_content = template.render(context)	
			msg = EmailMultiAlternatives(subject, html_content, email_from, recipient_list)
			msg.attach_alternative(html_content, "text/html")
			try:
				msg.send(fail_silently=True)
			except Exception as e:
				print(e)
			response = {}
			response['msg'] = "added"
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		try:
			username = request.query_params.get('username')
			try:
				user_obj = User.objects.get(username=username)
				profile_obj = Profile.objects.get(user=user_obj)
			except Exception as e:
				response = {}
				response["msg"] = str(e)
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			response = {}
			response["username"] = user_obj.username
			response["first_name"] = user_obj.first_name
			response["last_name"] = user_obj.last_name
			response["phone_number"] = profile_obj.phone_number
			response["cell_phone_number"] = profile_obj.cell_phone
			response["skype_id"] = profile_obj.skype_id
			response["job_title"] = profile_obj.job_title
			response["email"] = profile_obj.email
			response["client"] = profile_obj.client
			response["rankings"] = json.loads(profile_obj.rankings)
			response["profile_photo"] = profile_obj.profile_photo.url if profile_obj.profile_photo else None
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request):
		try:
			username = request.data.get("username")
			try:
				user_obj = User.objects.get(username=username)
				profile_obj = Profile.objects.get(user=user_obj)
			except Exception as e:
				response = {}
				response["msg"] = str(e)
				return Response(response, status=status.HTTP_204_NO_CONTENT)
			try:
				profile_photo = request.FILES['profile_photo']
			except Exception as e:
				if request.data.get("profile_photo") in [None, "null"]:
					profile_photo = None
				else:
					profile_obj = profile_obj.profile_photo
			profile_obj.profile_photo = profile_photo
			profile_obj.phone_number = request.data.get("phone_number")
			profile_obj.cell_phone = request.data.get("cell_phone_number")
			profile_obj.skype_id = request.data.get("skype_id")
			profile_obj.email = request.data.get("email")
			profile_obj.client = request.data.get("client")
			profile_obj.job_title = request.data.get("job_title")
			profile_obj.rankings = json.dumps(request.data.get('rankings'))
			user_obj.first_name = request.data.get('first_name')
			user_obj.last_name = request.data.get('last_name')
			user_obj.save()
			response = {}
			response['flag'] = request.data.get('profile_photo_deleted')
			# if request.data.get('profile_photo_deleted') == "true":
			# 	try:
			# 		file = request.FILES['profile_photo']
			# 	except:
			# 		profile_obj.profile_photo = None
			profile_obj.save()
			response["msg"] = "updated"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request):
		try:
			username = request.query_params.get('username')
			user_obj = User.objects.get(username=username)
			profile_obj = Profile.objects.get(user=user_obj)
			profile_id = profile_obj.id
			user_obj.delete()
			profile_obj.delete()
			candidate_marks_objs=CandidateMarks.objects.filter(marks_given_by=profile_id)
			if candidate_marks_objs:
				for i in candidate_marks_objs:
					i.delete()
			response = {}
			response["msg"] = "deleted"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HiringMemberView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			try:
				client_id = int(request.query_params.get('client_id'))
				hiring_member_objs = Profile.objects.filter(Q(roles__contains="is_htm") | Q(roles__contains="is_sm"), client=client_id)
			except:
				hiring_member_objs = Profile.objects.filter(Q(roles__contains="is_htm") | Q(roles__contains="is_sm"))
			members_list = []
			for i in hiring_member_objs:
				temp_dict = {}
				temp_dict['id'] = i.id
				temp_dict['name'] = i.user.get_full_name()
				temp_dict["email"] = i.email
				temp_dict["skills"] = "NA"
				temp_dict["interviews_done"] = "1/10 Interview Completed"
				members_list.append(temp_dict)
			response = {}
			response['data'] = members_list
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetAllHiringManagerView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			data = {}
			user = request.user
			if "is_ca" in user.profile.roles or "is_sm" in user.profile.roles:
				# hiring_member_objs = Profile.objects.filter(is_he=True, client=int(user.profile.client))
				# override for the ca when he sees the guide for first time
				if request.query_params.get('first'):
					hiring_member_objs = Profile.objects.filter(client=int(user.profile.client)).filter(roles__contains="is_htm")
				elif request.query_params.get('client_id'):
					hiring_member_objs = Profile.objects.filter(client=int(request.query_params.get('client_id'))).filter(roles__contains="is_htm")
				else:
					hiring_member_objs = Profile.objects.filter(client=int(user.profile.client)).filter(roles__contains="is_htm")
			elif "is_ae" in user.profile.roles:
				hiring_member_objs = Profile.objects.filter(client__in=json.loads(user.profile.client)).filter(roles__contains="is_htm")
			else:
				hiring_member_objs = Profile.objects.filter(user__is_active=True).filter(roles__contains="is_htm")
			members_list = []
			for i in hiring_member_objs:
				temp_dict = {}
				temp_dict["id"] = i.id
				temp_dict["name"] = i.user.get_full_name()
				temp_dict["last_name"] = i.user.last_name
				temp_dict["username"] = i.user.username
				temp_dict["mobile_no"] = i.phone_number
				temp_dict["email"] = i.email
				temp_dict["profile_photo"] = i.profile_photo.url if i.profile_photo else None
				if i.job_title:
					temp_dict['job_title'] = i.job_title
				else:
					temp_dict['job_title'] = '---'
				try:
					client_obj = Client.objects.get(id=int(i.client))
					temp_dict['client'] = client_obj.company_name
				except:
					temp_dict['client'] = 'No Client'
				try:
					hiring_group_objs = HiringGroup.objects.filter(client_id=int(i.client))
				except:
					temp_dict['group'] = 'No Group'
				found = False
				for j in hiring_group_objs:
					if i in j.members_list.all():
						temp_dict['group'] = j.name
						found = True
				if not found:
					temp_dict['group'] = 'No Group'
				try:
					data[temp_dict['client']].append(temp_dict)
				except Exception as e:
					data[temp_dict['client']] = []
					data[temp_dict['client']].append(temp_dict)
			new_data = {}
			for key, value in data.items():
				sorted_value = sorted(value, key=lambda i: i['last_name'])
				new_data[key] = sorted_value
			return Response(new_data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(KnoxLoginView):
	permission_classes = (permissions.AllowAny,)
	def post(self, request, format=None):
		serializer = AuthTokenSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.validated_data['user']
		login(request, user)
		data = super(LoginView, self).post(request, format=None)
		data.data['username'] = user.username
		data.data['name'] = user.first_name + ' ' + user.last_name
		data.data['first_name'] = user.first_name
		data.data['last_name'] = user.last_name
		user_profile = Profile.objects.get(user=user)
		# Get first log data
		if any((True for x in user.profile.roles if x in ["is_htm", "is_sm", "is_ca"])):
			client_obj = Client.objects.get(id=int(user.profile.client))
			if client_obj.status == "inactive":
				return Response({"msg": "Your account is suspended. Please contact support@qorums.com"}, status=status.HTTP_400_BAD_REQUEST)
		if "is_ca" in user.profile.roles:
			client_obj = Client.objects.get(id=int(user.profile.client))
			data.data['client_data'] = ClientSerializer(client_obj).data
			try:
				billing_obj = BillingDetail.objects.get(profile=request.user.profile)
				data.data['billing_data'] = BillingDetailSerializer(billing_obj).data
			except:
				data.data['billing_data'] = None
			try:
				client_package = ClientPackage.objects.get(client=client_obj)
				data.data['package_data'] = ClientPackageSerializer(client_package).data
				if client_package.is_trial or client_package.strip_subs_status == "active":
					data.data['payment_done'] = True
				else:
					data.data['payment_done'] = False
			except:
				data.data['payment_done'] = False
				data.data['package_data'] = None
			data.data['role'] = 'Client Admin'
		elif not (user.is_superuser or "is_ae" in user.profile.roles):
			try:
				client_package = ClientPackage.objects.get(client__id=int(user.profile.client))
				if client_package.is_trial or client_package.strip_subs_status:
					data.data['payment_done'] = True
				else:
					data.data['payment_done'] = False
			except:
				data.data['payment_done'] = False
		if "is_htm" in user.profile.roles:
			temp_profile = user.profile
			data.data['role'] = 'Hiring Team Member'
		if "is_ae" in user.profile.roles:
			data.data['role'] = 'Account Manager'
			try:
				for i in json.loads(user.profile.client):
					for j in OpenPosition.objects.filter(client=int(i)):
						obj, created = AskedNotification.objects.get_or_create(user=user.profile.id, op_id=j.id)
						obj.asked = False
						obj.save()
			except:
				pass
		if user.is_superuser:
			data.data['role'] = 'Superuser'
		try:
			data.data['client_id'] = int(user.profile.client)
		except:
			data.data['client_id'] = 0
		if "is_sm" in user.profile.roles:
			data.data['role'] = 'Senior Manager'
		if "is_candidate" in user.profile.roles:
			data.data['role'] = 'Candidate'
			candidate_obj = Candidate.objects.get(user=user.id)
			data.data['redirect_to'] = 'https://qorums.com/add-candidate-data/?email=' + candidate_obj.email + '&id=' + str(candidate_obj.candidate_id)
			# data.data['associated_op_ids'] = json.loads(candidate_obj.associated_op_ids)
			data.data['associated_op_ids'] = list(CandidateAssociateData.objects.filter(candidate=candidate_obj, accepted=True, withdrawed = False).values_list('open_position', flat=True))
			data.data['candidate_id'] = candidate_obj.candidate_id
			data.data['linkedin_first_name'] = candidate_obj.linkedin_first_name
			data.data['linkedin_last_name'] = candidate_obj.linkedin_last_name
			data.data['alernate_email'] = candidate_obj.alernate_email
			if candidate_obj.profile_photo:
				data.data['profile_photo'] = candidate_obj.profile_photo
			elif "profile_pic_url" in candidate_obj.linkedin_data and candidate_obj.linkedin_data['profile_pic_url'] != "null":
				data.data['profile_photo'] = candidate_obj.linkedin_data["profile_pic_url"]
			else:
				data.data['profile_photo'] = None
		data.data['roles'] = user.profile.roles			
		if "profile_photo" not in data.data: 
			data.data['profile_photo'] = user_profile.profile_photo.url if user_profile.profile_photo else None
		data.data['phone_number'] = user_profile.phone_number
		data.data['email'] = user_profile.email
		data.data['skype_id'] = user_profile.skype_id
		data.data['tnc_accepted'] = user_profile.tnc_accepted
		data.data['profile_id'] = user_profile.id
		data.data['dark_mode'] = user_profile.dark_mode
		return data


class AllAccountManagers(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			ae_objs = Profile.objects.filter(roles__contains="is_ae")
			data = []
			for i in ae_objs:
				temp_dict = {}
				temp_dict["id"] = i.id
				temp_dict["name"] = i.user.first_name + ' ' + i.user.last_name
				temp_dict["username"] = i.user.username
				temp_dict["mobile_no"] = i.phone_number
				temp_dict["email"] = i.email
				temp_dict['profile_photo'] = i.profile_photo.url if i.profile_photo else None
				data.append(temp_dict)
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Open Position Step 3
class HiringGroupView(APIView):
	def post(self, request):
		try:
			response = {}
			members_list = request.data.get("members")
			members = request.data.get("members")
			# try:
			# 	members_list = request.data.get("members")
			# 	members = request.data.get("members")
			# 	request.data["members"] = json.dumps(members)
			# except:
			# 	members = "[]"
			n_data = request.data.copy()
			n_data['members'] = json.dumps(request.data.get('members'))
			n_data['members_list'] = request.data.get('members')
			n_data['hod_profile'] = request.data.get('hod')
			n_data['hr_profile'] = request.data.get('hr')
			# check if HR is selected or not
			if request.data.get('hr'):
				pass
			else:
				n_data['hr'] = 0
			members_color = []
			selected_color = []
			for member in members:
				color = random.choice(COLORS)
				while color in selected_color:
					color = random.choice(COLORS)
					selected_color.append(color)
				else:
					selected_color.append(color)
				temp_color = {}
				temp_color['color'] = color
				temp_color["htm"] = member
				members_color.append(temp_color)
			n_data["members_color"] = members_color
			group_serializer = HiringGroupSerializer(data=n_data)
			if group_serializer.is_valid():
				group_obj = group_serializer.save()
				# update members_list other can be comented
				# comment line: 
				
				# Send Notifications
				try:
					for profile_obj in group_obj.members_list.all():
						if profile_obj is group_obj.hod_profile:
							tasks.send_app_notification.delay(profile_obj.user.username, 'You have been assigned as the hiring manager for the {} team.'.format(request.data.get('name')))
							tasks.push_notification.delay([profile_obj.user.username], 'Qorums Notification', 'You have been assigned as the hiring manager for the {} team.'.format(request.data.get('name')))
						elif profile_obj is group_obj.hr_profile:
							tasks.send_app_notification.delay(profile_obj.user.username, 'You have been assigned as the HR administrator for the {} team.'.format(request.data.get('name')))
							tasks.push_notification.delay([profile_obj.user.username], 'Qorums Notification', 'You have been assigned as the HR administrator for the {} team.'.format(request.data.get('name')))
						else:
							tasks.send_app_notification.delay(profile_obj.user.username, 'You have been assigned to the {} team.'.format(request.data.get('name')))
							tasks.push_notification.delay([profile_obj.user.username], 'Qorums Notification', 'You have been assigned to the {} team.'.format(request.data.get('name')))
				except Exception as e:
					response['notitication-error'] = str(e)
				response['msg'] = 'added'
				response['data'] = group_serializer.data
				hiring_group_obj = HiringGroup.objects.get(group_id=response['data']['group_id'])
			else:
				response = {}
				response['error'] = group_serializer.errors
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			op_id = request.data.get('op_id')
			if op_id:
				open_position_obj = OpenPosition.objects.get(id=op_id)
				open_position_obj.hiring_group = group_serializer.data['group_id']
				open_position_obj.save()
			else:
				pass
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request):
		try:
			group_obj = HiringGroup.objects.filter(group_id=request.data.get('group_id'))
			client_obj = None
			response = {}
			if group_obj:
				client_obj = Client.objects.get(id=group_obj[0].client_id)
				old_members = list(group_obj[0].members_list.all().values_list('id', flat=True))
				old_members_color =group_obj[0].members_color
				n_data = request.data.copy()
				n_data['members'] = json.dumps(request.data.get('members'))
				n_data['members_list'] = request.data.get('members')
				n_data['hod_profile'] = request.data.get('hod')
				n_data['hr_profile'] = request.data.get('hr')
				if request.data.get('hr'):
					pass
				else:
					n_data['hr'] = 0
				members_color = []
				selected_color = []
				for member in request.data.get('members'):
					color = [d["color"] for d in old_members_color if d['htm'] == member]
					if color:
						color = color[0]
					else:
						color = random.choice(COLORS)
					print(color)
					while color in selected_color:
						color = random.choice(COLORS)
						selected_color.append(color)
						print(selected_color)
					else:
						selected_color.append(color)
					temp_color = {}
					temp_color['color'] = color
					temp_color["htm"] = member
					members_color.append(temp_color)
				n_data["members_color"] = members_color
				group_serializer = HiringGroupSerializer(group_obj[0], data=n_data, partial=True)
				if group_serializer.is_valid():
					group_serializer.save()
				else:
					response = {}
					response['error'] = group_serializer.errors
					return Response(response, status=status.HTTP_400_BAD_REQUEST)
				group_data = group_serializer.data
				
				# get new members
				new_members = []
				for i in request.data.get('members'):
					if i in old_members:
						pass
					else:
						new_members.append(i)
				response['new_members'] = new_members
				# Send Mail to New Group Members
				if new_members:
					try:
						candidate_emails = []
						for i in OpenPosition.objects.filter(hiring_group=group_obj[0].group_id):
							# for j in Candidate.objects.all():
							# 	if i.id in json.loads(j.associated_op_ids):
							# 		candidate_emails.append(j.email)
							for cao in CandidateAssociateData.objects.filter(open_position=i, accepted=True, withdrawed=False):
								candidate_emails.append(cao.candidate.email)
						subject = 'A new HTM is added!'
						d = {
							"company": client_obj.company_name,
							"manager": "{} {}".format(client_obj.hr_first_name, client_obj.hr_last_name),
							"manager_contact": client_obj.hr_contact_phone_no,
							"manager_email": client_obj.hr_contact_email,
						}
						email_from = settings.EMAIL_HOST_USER
						htmly_b = get_template('htm_added.html')
						text_content = ""
						html_content = htmly_b.render(d)
						try:
							profile = Profile.objects.get(user=request.user)
							reply_to = profile.email
							sender_name = profile.user.get_full_name()
						except:
							reply_to = 'noreply@qorums.com'
							sender_name = 'No Reply'
						try:
							tasks.send.delay(subject, html_content, 'html', candidate_emails, reply_to, sender_name)
						except Exception as e:
							return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
					except Exception as e:
						response['new-member-send'] = str(e)
						print("Error sending mail to Candidate", e)
					try:
						for member in new_members:
							profile_obj = Profile.objects.get(id=member)
							if member is request.data.get('hod'):
								tasks.send_app_notification.delay(profile_obj.user.username, 'You have been assigned as the hiring manager for the {} team.'.format(request.data.get('name')))
								tasks.push_notification.delay([profile_obj.user.username], 'Qorums Notification', 'You have been assigned as the hiring manager for the {} team.'.format(request.data.get('name')))
							elif member is request.data.get('hr'):
								tasks.send_app_notification.delay(profile_obj.user.username, 'You have been assigned as the HR administrator for the {} team.'.format(request.data.get('name')))
								tasks.push_notification.delay([profile_obj.user.username], 'Qorums Notification', 'You have been assigned as the HR administrator for the {} team.'.format(request.data.get('name')))
							else:
								tasks.send_app_notification.delay(profile_obj.user.username, 'You have been assigned to the {} team.'.format(request.data.get('name')))
								tasks.push_notification.delay([profile_obj.user.username], 'Qorums Notification', 'You have been assigned to the {} team.'.format(request.data.get('name')))
					except Exception as e:
						response['notitication-error'] = str(e)
				response['msg'] = 'updated'
				response['data'] = group_data
			else:
				response = {}
				response['msg'] = 'No Group Found'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		try:
			data = {}
			user = request.user
			if user.profile.is_ca or user.profile.is_sm:
				hiring_group_objs = HiringGroup.objects.filter(client_id=int(user.profile.client))
				try:
					# data = []
					client_id = int(request.query_params.get('client_id'))
					hiring_group_objs = HiringGroup.objects.filter(client_id=client_id, disabled=False)
				except:
					pass
			elif "is_htm" in user.profile.roles:
				hiring_group_objs = HiringGroup.objects.filter(client_id=int(user.profile.client))
				try:
					# data = []
					htm_id = int(request.query_params.get('htm_id'))
					if htm_id:
						hiring_group_objs = HiringGroup.objects.filter(hod=htm_id, disabled=False)
				except:
					pass
			elif user.profile.is_ch:
				hiring_group_objs = HiringGroup.objects.filter(client_id=int(user.profile.client))
				try:
					# data = []
					client_id = int(request.query_params.get('client_id'))
					hiring_group_objs = HiringGroup.objects.filter(client_id=client_id, disabled=False)
				except:
					pass
			elif "is_ae" in user.profile.roles:
				hiring_group_objs = HiringGroup.objects.filter(client_id__in=json.loads(user.profile.client))
				try:
					# data = []
					client_id = int(request.query_params.get('client_id'))
					hiring_group_objs = HiringGroup.objects.filter(client_id=client_id, disabled=False)
				except:
					pass
			else:
				try:
					client_id = int(request.query_params.get('client_id'))
					# data = []
					hiring_group_objs = HiringGroup.objects.filter(client_id=client_id, disabled=False)
				except:
					hiring_group_objs = HiringGroup.objects.filter(disabled=False)
			for i in hiring_group_objs:
				temp_dict = {}
				temp_dict['group_id'] = i.group_id
				temp_dict['name'] = i.name
				temp_dict['description'] = i.description
				temp_dict['client'] = i.client_id
				client_obj = Client.objects.get(id=i.client_id)
				temp_dict['client_name'] = client_obj.company_name
				temp_dict["members"] = []
				open_position_objs = OpenPosition.objects.filter(hiring_group=i.group_id)
				open_position_serializer = OpenPositionSerializer(open_position_objs, many=True)
				temp_dict['jobs'] = open_position_serializer.data
				for profile in i.members_list.all():
					try:
						member_dict = {}
						member_dict['id'] = profile.id
						member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
						member_dict['profile_photo'] = profile.profile_photo
						temp_dict["members"].append(member_dict)
					except Exception as e:
						print(e)
						pass
				try:
					data[temp_dict['client_name']].append(temp_dict)
				except Exception as e:
					data[temp_dict['client_name']] = []
					data[temp_dict['client_name']].append(temp_dict)
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request):
		try:
			ops = OpenPosition.objects.filter(hiring_group=int(request.query_params.get('group_id')))
			if ops:
				position = ", ".join(ops.values_list("position_title", flat=True))
				return Response({'msg': "This Hiring Team is associated to an Open Position - {}. To delete the Hiring Team should not be associated with any Open Position.".format(position)}, status=status.HTTP_400_BAD_REQUEST)
			HiringGroup.objects.filter(group_id=int(request.query_params.get('group_id'))).delete()
			response = {}
			response["msg"] = "deleted"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SelectHiringGroup(APIView):
	def get(self, request):
		try:
			data = []
			user = request.user
			if user.profile.is_ca or user.profile.is_sm:
				try:
					client_id = int(request.query_params.get('client_id'))
					hiring_group_objs = HiringGroup.objects.filter(client_id=client_id, disabled=False)
				except:
					pass
			elif "is_htm" in user.profile.roles:
				hiring_group_objs = HiringGroup.objects.filter(client_id=int(user.profile.client), hod=user.profile.id)
			elif user.profile.is_ch:
				hiring_group_objs = HiringGroup.objects.filter(client_id=int(user.profile.client))
				try:
					client_id = int(request.query_params.get('client_id'))
					hiring_group_objs = HiringGroup.objects.filter(client_id=client_id, disabled=False)
				except:
					pass
			elif "is_ae" in user.profile.roles:
				hiring_group_objs = HiringGroup.objects.filter(client_id__in=json.loads(user.profile.client))
				try:
					client_id = int(request.query_params.get('client_id'))
					hiring_group_objs = HiringGroup.objects.filter(client_id=client_id, disabled=False)
				except:
					pass
			else:
				try:
					client_id = int(request.query_params.get('client_id'))
					hiring_group_objs = HiringGroup.objects.filter(client_id=client_id, disabled=False)
				except:
					hiring_group_objs = HiringGroup.objects.filter(disabled=False)
			for i in hiring_group_objs:
				temp_dict = {}
				temp_dict['group_id'] = i.group_id
				temp_dict['name'] = i.name
				temp_dict['description'] = i.description
				temp_dict['client'] = i.client_id
				client_obj = Client.objects.get(id=i.client_id)
				temp_dict['client_name'] = client_obj.company_name
				temp_dict["members"] = []
				open_position_objs = OpenPosition.objects.filter(hiring_group=i.group_id)
				open_position_serializer = OpenPositionSerializer(open_position_objs, many=True)
				temp_dict['jobs'] = open_position_serializer.data
				try:
					members_list = json.loads(i.members)
				except Exception as e:
					members_list = []
				for profile in i.members_list.all():
					try:
						member_dict = {}
						member_dict['id'] = profile.id
						member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
						member_dict['profile_photo'] = profile.profile_photo
						temp_dict["members"].append(member_dict)
					except Exception as e:
						print(e)
						pass
					if i.hod_profile == profile:
						member_dict['isHod'] = True
					if i.hr_profile == profile:
						member_dict['isHr'] = True
				data.append(temp_dict)
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)



class SingleHiringGroupOPView(APIView):
	def get(self, request, group_id, op_id):
		try:
			data = []
			openposition_obj = OpenPosition.objects.get(id=op_id)
			for i in HiringGroup.objects.filter(group_id=group_id):
				temp_dict = {}
				temp_dict['group_id'] = i.group_id
				temp_dict['name'] = i.name
				temp_dict['description'] = i.description
				temp_dict['client'] = i.client_id
				temp_dict["members"] = []
				open_position_objs = OpenPosition.objects.filter(hiring_group=group_id)
				open_position_serializer = OpenPositionSerializer(open_position_objs, many=True)
				temp_dict['position'] = open_position_serializer.data
				candidates_obj = []
				# for can in Candidate.objects.all():
				# 	if op_id in json.loads(can.associated_op_ids):
				# 		candidates_obj.append(can)
				for cao in CandidateAssociateData.objects.filter(open_position__id=op_id, accepted=True, withdrawed=False):
					candidates_obj.append(cao.candidate)
				
				try:
					hiring_manager_hod = i.hod_profile
					hiring_manager_dict = {}
					hiring_manager_dict['id'] = hiring_manager_hod.id
					hiring_manager_dict["name"] = hiring_manager_hod.user.first_name + ' ' + hiring_manager_hod.user.last_name
					hiring_manager_dict["username"] = hiring_manager_hod.user.username
					hiring_manager_dict["mobile_no"] = hiring_manager_hod.phone_number
					hiring_manager_dict["email"] = hiring_manager_hod.email
					hiring_manager_dict['total_candidates'] = len(candidates_obj)
					hiring_manager_dict['profile_photo'] = hiring_manager_hod.profile_photo
					hiring_manager_dict['interview_taken'] = CandidateMarks.objects.filter(op_id=op_id, marks_given_by=hiring_manager_hod.id).count()
					temp_dict['hiring_manager'] = hiring_manager_dict
				except Exception as e:
					temp_dict['hiring_manager'] = None
				# HR
				try:
					hr_profile = i.hr_profile
					hr_dict = {}
					hr_dict['id'] = hr_profile.id
					hr_dict["name"] = hr_profile.user.first_name + ' ' + hr_profile.user.last_name
					hr_dict["username"] = hr_profile.user.username
					hr_dict["mobile_no"] = hr_profile.phone_number
					hr_dict["email"] = hr_profile.email
					hr_dict['total_candidates'] = len(candidates_obj)
					hr_dict['profile_photo'] = hr_profile.profile_photo
					hr_dict['interview_taken'] = CandidateMarks.objects.filter(op_id=op_id, marks_given_by=hr_profile.id).count()
					temp_dict['human_resource'] = hr_dict
				except Exception as e:
					temp_dict['human_resource'] = None

				try:
					withdrawed_members = json.loads(openposition_obj.withdrawed_members)
				except Exception as e:
					withdrawed_members = []

				try:
					members_list = list(i.members_list.all().values_list("id", flat=True))
					if i.hod_profile and i.hod_profile.id in members_list:
						members_list.remove(i.hod_profile.id)
				except Exception as e:
					print(e)
					members_list = []
				for m in members_list:
					if m in withdrawed_members:
						members_list.remove(m)
				for j in members_list:
					try:
						profile = Profile.objects.get(id=j)
						member_dict = {}
						member_dict['id'] = profile.id
						member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
						member_dict['client_id'] = int(profile.client)
						member_dict['email'] = profile.email
						member_dict['phone_number'] = profile.phone_number
						member_dict['linkedin'] = profile.skype_id
						member_dict['job_title'] = profile.job_title
						member_dict['skillsets'] = json.loads(profile.rankings)
						member_dict['username'] = profile.user.username
						member_dict['profile_photo'] = profile.profile_photo
						member_dict['total_candidates'] = len(candidates_obj)
						member_dict['interview_taken'] = CandidateMarks.objects.filter(op_id=op_id, marks_given_by=profile.id).count()
						member_dict['withdrawed'] = False
						temp_dict["members"].append(member_dict)
					except Exception as e:
						print(e)
				for j in withdrawed_members:
					try:
						profile = Profile.objects.get(id=j)
						member_dict = {}
						member_dict['id'] = profile.id
						member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
						member_dict['client_id'] = int(profile.client)
						member_dict['email'] = profile.email
						member_dict['username'] = profile.user.username
						member_dict['profile_photo'] = profile.profile_photo
						member_dict['total_candidates'] = len(candidates_obj)
						member_dict['interview_taken'] = CandidateMarks.objects.filter(op_id=op_id, marks_given_by=profile.id).count()
						member_dict['withdrawed'] = True
						temp_dict["members"].append(member_dict)
					except Exception as e:
						pass
				data.append(temp_dict)
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OpenPositionHiringGroupView(APIView):
	def get(self, request, group_id, op_id):
		try:
			data = []
			openposition_obj = OpenPosition.objects.get(id=op_id)
			for i in HiringGroup.objects.filter(group_id=group_id):
				temp_dict = {}
				temp_dict['group_id'] = i.group_id
				temp_dict['name'] = i.name
				temp_dict['description'] = i.description
				temp_dict['client'] = i.client_id
				temp_dict["members"] = []
				open_position_objs = OpenPosition.objects.filter(hiring_group=group_id)
				open_position_serializer = OpenPositionSerializer(open_position_objs, many=True)
				temp_dict['position'] = open_position_serializer.data
				# Get HM data
				hiring_manager_dict = {}
				try:
					hiring_manager_hod = i.hod_profile
					
					hiring_manager_dict['id'] = hiring_manager_hod.id
					hiring_manager_dict["name"] = hiring_manager_hod.user.first_name + ' ' + hiring_manager_hod.user.last_name
					hiring_manager_dict["username"] = hiring_manager_hod.user.username
					hiring_manager_dict["mobile_no"] = hiring_manager_hod.phone_number
					hiring_manager_dict["email"] = hiring_manager_hod.email
					hiring_manager_dict['linkedin_id'] = hiring_manager_hod.skype_id
					hiring_manager_dict['phone_number'] = hiring_manager_hod.phone_number
					try:
						htm_avail = HTMAvailability.objects.get(htm_id=hiring_manager_hod.id)
						hiring_manager_dict['color'] = htm_avail.color
						avails = json.loads(htm_avail.availability)
						hiring_manager_dict['schedule'] = []
						for avail in avails:
							if Interview.objects.filter(htm__in=[hiring_manager_hod], texted_start_time=json.dumps(avail)).filter(disabled=False):
								avail["scheduled"] = True
							else:
								avail["scheduled"] = False
						hiring_manager_dict['schedule'] = avails
					except Exception as e:
						hiring_manager_dict['error'] = str(e)
						hiring_manager_dict['color'] = '#ffffff'
						hiring_manager_dict['schedule'] = []
					temp_dict['hiring_manager'] = hiring_manager_dict

				except Exception as e:
					temp_dict['hiring_manager'] = hiring_manager_dict if hiring_manager_dict else None
				
				# Get HR data
				hr_dict = {}
				try:
					hr_profile = i.hr_profile
					
					hr_dict['id'] = hr_profile.id
					hr_dict["name"] = hr_profile.user.first_name + ' ' + hr_profile.user.last_name
					hr_dict["username"] = hr_profile.user.username
					hr_dict["mobile_no"] = hr_profile.phone_number
					hr_dict["email"] = hr_profile.email
					hr_dict['linkedin_id'] = hr_profile.skype_id
					hr_dict['phone_number'] = hr_profile.phone_number
					try:
						htm_avail = HTMAvailability.objects.get(htm_id=hr_profile.id)
						hiring_manager_dict['color'] = htm_avail.color
						avails = json.loads(htm_avail.availability)
						hiring_manager_dict['schedule'] = []
						for avail in avails:
							if Interview.objects.filter(htm__in=[hr_profile], texted_start_time=json.dumps(avail)).filter(disabled=False):
								avail["scheduled"] = True
							else:
								avail["scheduled"] = False
						hr_dict['schedule'] = avails
					except Exception as e:
						hr_dict['error'] = str(e)
						hr_dict['color'] = '#ffffff'
						hr_dict['schedule'] = []
					temp_dict['human_resource'] = hr_dict

				except Exception as e:
					temp_dict['human_resource'] = hr_dict if hr_dict else None
				members_list = i.members_list.all().values_list("id", flat=True)
				# Add HM as member
				member_dict = {}
				if i.hod_profile:
					hiring_manager_hod = i.hod_profile
					member_dict['id'] = hiring_manager_hod.id
					member_dict['name'] = hiring_manager_hod.user.first_name + ' ' + hiring_manager_hod.user.last_name
					member_dict['client_id'] = int(hiring_manager_hod.client)
					member_dict['email'] = hiring_manager_hod.email
					member_dict['username'] = hiring_manager_hod.user.username
					member_dict['profile_photo'] = hiring_manager_hod.profile_photo
					member_dict['withdrawed'] = False
					member_dict['phone_number'] = hiring_manager_hod.phone_number
					member_dict['linkedin_id'] = hiring_manager_hod.skype_id
					member_dict['role'] = "Hiring Manager"
					# Get HM availabilities
					try:
						htm_avail = HTMAvailability.objects.get(htm_id=hiring_manager_hod.id)
						member_dict['color'] = htm_avail.color
						avails = json.loads(htm_avail.availability)
						member_dict['schedule'] = []
						for avail in avails:
							if Interview.objects.filter(htm__in=[hiring_manager_hod], texted_start_time=json.dumps(avail)).filter(disabled=False):
								avail["scheduled"] = True
							else:
								avail["scheduled"] = False
						member_dict['schedule'] = avails
							
					except Exception as e:
						member_dict['error'] = str(e)
						member_dict['color'] = '#ffffff'
						member_dict['schedule'] = []
					temp_dict["members"].append(member_dict)

				for j in members_list:
					try:
						if j == i.hod_profile.id:
							pass
						else:
							profile = Profile.objects.get(id=j)
							member_dict = {}
							member_dict['id'] = profile.id
							member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
							member_dict['client_id'] = int(profile.client)
							member_dict['email'] = profile.email
							member_dict['username'] = profile.user.username
							member_dict['profile_photo'] = profile.profile_photo
							member_dict['withdrawed'] = False
							member_dict['phone_number'] = profile.phone_number
							member_dict['linkedin_id'] = profile.skype_id
							member_dict['role'] = "Hiring Team Member"
							try:
								htm_avail = HTMAvailability.objects.get(htm_id=profile.id)
								member_dict['color'] = htm_avail.color
								member_dict['schedule'] = json.loads(htm_avail.availability)
								avails = json.loads(htm_avail.availability)
								member_dict['schedule'] = []
								for avail in avails:
									if Interview.objects.filter(htm__in=[profile], texted_start_time=json.dumps(avail)).filter(disabled=False):
										avail["scheduled"] = True
									else:
										avail["scheduled"] = False
								member_dict['schedule'] = avails
							except Exception as e:
								member_dict['error'] = str(e)
								member_dict['color'] = '#ffffff'
								member_dict['schedule'] = []
							temp_dict["members"].append(member_dict)
					except Exception as e:
						print(e)
						temp_dict['members_error'] = str(e)

				# Add HR as Member
				member_dict = {}
				try:
					hr_profile = i.hr_profile
					member_dict['id'] = hr_profile.id
					member_dict['name'] = hr_profile.user.first_name + ' ' + hr_profile.user.last_name
					member_dict['client_id'] = int(hr_profile.client)
					member_dict['email'] = hr_profile.email
					member_dict['username'] = hr_profile.user.username
					member_dict['profile_photo'] = hr_profile.profile_photo
					member_dict['withdrawed'] = False
					member_dict['phone_number'] = hr_profile.phone_number
					member_dict['linkedin_id'] = hr_profile.skype_id
					member_dict['role'] = "Human Resource"

					try:
						htm_avail = HTMAvailability.objects.get(htm_id=hr_profile.id)
						member_dict['color'] = htm_avail.color
						avails = json.loads(htm_avail.availability)
						member_dict['schedule'] = []
						for avail in avails:
							if Interview.objects.filter(htm__in=[hr_profile], texted_start_time=json.dumps(avail)).filter(disabled=False):
								avail["scheduled"] = True
							else:
								avail["scheduled"] = False
						member_dict['schedule'] = avails
							
					except Exception as e:
						member_dict['error'] = str(e)
						member_dict['color'] = '#ffffff'
						member_dict['schedule'] = []
					temp_dict["members"].append(member_dict)
				except Exception as e:
					pass
				try:
					withdrawed_members = json.loads(openposition_obj.withdrawed_members)
				except Exception as e:
					withdrawed_members = []
				for j in withdrawed_members:
					try:
						profile = Profile.objects.get(id=j)
						member_dict = {}
						member_dict['id'] = profile.id
						member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
						member_dict['client_id'] = int(profile.client)
						member_dict['email'] = profile.email
						member_dict['username'] = profile.user.username
						member_dict['profile_photo'] = profile.profile_photo
						member_dict['withdrawed'] = True
						member_dict['phone_number'] = profile.phone_number
						member_dict['linkedin_id'] = profile.skype_id
						member_dict['role'] = "Hiring Team Member"
						try:
							htm_avail = HTMAvailability.objects.get(htm_id=profile.id)
							hiring_manager_dict['color'] = htm_avail.color
						except:
							hiring_manager_dict['color'] = '#ffffff'
						temp_dict["members"].append(member_dict)
					except Exception as e:
						print(e)
						pass
				data.append(temp_dict)
			print(data)
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SingleHiringGroupView(APIView):
	def get(self, request, group_id):
		try:
			data = []
			q_op_id = request.GET.get("op_id")
			colors = []
			for i in HiringGroup.objects.filter(group_id=group_id):
				temp_dict = {}
				temp_dict['group_id'] = i.group_id
				temp_dict['name'] = i.name
				temp_dict['description'] = i.description
				temp_dict['client'] = i.client_id
				temp_dict["members"] = []
				open_position_objs = OpenPosition.objects.filter(hiring_group=group_id)
				open_position_serializer = OpenPositionSerializer(open_position_objs, many=True)
				temp_dict['position'] = open_position_serializer.data
				for j in temp_dict['position']:
					j['withdrawed_members'] = json.loads(j['withdrawed_members'])
				# Get HM data
				hiring_manager_dict = {}
				try:
					hiring_manager_hod = i.hod_profile
					hiring_manager_dict['id'] = hiring_manager_hod.id
					hiring_manager_dict["name"] = hiring_manager_hod.user.first_name + ' ' + hiring_manager_hod.user.last_name
					hiring_manager_dict["username"] = hiring_manager_hod.user.username
					hiring_manager_dict["mobile_no"] = hiring_manager_hod.phone_number
					hiring_manager_dict["email"] = hiring_manager_hod.email
					hiring_manager_dict['linkedin_id'] = hiring_manager_hod.skype_id
					hiring_manager_dict['phone_number'] = hiring_manager_hod.phone_number
					try:
						hiring_manager_dict['color'] = HTMsDeadline.objects.get(htm__id=hiring_manager_hod.id, open_position__id=q_op_id).color
						colors.append(hiring_manager_dict['color'])
					except Exception as e:
						color = random.choice(COLORS)
						while color in colors:
							color = random.choice(COLORS)
						else:
							colors.append(color)
						hiring_manager_dict['color'] = color
					try:
						htm_avail = HTMAvailability.objects.get(htm_id=hiring_manager_hod.id)
						avails = json.loads(htm_avail.availability)
						hiring_manager_dict['schedule'] = []
						new_avails = []
						for avail in avails:
							try:
								temp_l = avail["hours"][0]["startTime"].split(":")
								if len(temp_l[0])==1:
									temp_l[0] = '0'+temp_l[0]
								if len(temp_l[0])==1:
									temp_l[1] = '0'+temp_l[1]
								s_time = avail['date'].replace('-', '/') + temp_l[0] + ':' + temp_l[1]
								avail_obj = datetime.strptime(s_time, "%Y/%m/%d%H:%M")
								if avail_obj > datetime.now():
									if Interview.objects.filter(htm__in=[hiring_manager_hod], texted_start_time=json.dumps(avail)).filter(disabled=False):
										interview_obj = Interview.objects.filter(htm__in=[hiring_manager_hod], texted_start_time=json.dumps(avail)).filter(disabled=False).filter(disabled=False).last()
										openposition_obj = OpenPosition.objects.get(id=interview_obj.op_id.id)
										avail["scheduled"] = True
										avail['position_name'] = openposition_obj.position_title
									else:
										avail["scheduled"] = False
									new_avails.append(avail)
							except Exception as e:
								print(e)
								avail["scheduled_error"] = str(e)
						new_avails.sort(key=lambda item:item['date'])
						hiring_manager_dict['schedule'] = new_avails
					except Exception as e:
						hiring_manager_dict['error'] = str(e)
						hiring_manager_dict['schedule'] = []
					temp_dict['hiring_manager'] = hiring_manager_dict

				except Exception as e:
					temp_dict['hiring_manager'] = hiring_manager_dict if hiring_manager_dict else None
				
				# Get HR data
				hr_dict = {}
				try:
					hr_profile = i.hr_profile
					hr_dict['id'] = hr_profile.id
					hr_dict["name"] = hr_profile.user.first_name + ' ' + hr_profile.user.last_name
					hr_dict["username"] = hr_profile.user.username
					hr_dict["mobile_no"] = hr_profile.phone_number
					hr_dict["email"] = hr_profile.email
					hr_dict['linkedin_id'] = hr_profile.skype_id
					hr_dict['phone_number'] = hr_profile.phone_number
					try:
						hiring_manager_dict['color'] = HTMsDeadline.objects.get(htm__id=hr_profile.id, open_position__id=q_op_id).color
						colors.append(hiring_manager_dict['color'])
					except Exception as e:
						color = random.choice(COLORS)
						while color in colors:
							color = random.choice(COLORS)
						else:
							colors.append(color)
						hiring_manager_dict['color'] = color
					try:
						htm_avail = HTMAvailability.objects.get(htm_id=hr_profile.id)
						# hiring_manager_dict['color'] = htm_avail.color
						avails = json.loads(htm_avail.availability)
						new_avails = []
						hiring_manager_dict['schedule'] = []
						for avail in avails:
							try:
								temp_l = avail["hours"][0]["startTime"].split(":")
								if len(temp_l[0])==1:
									temp_l[0] = '0'+temp_l[0]
								if len(temp_l[0])==1:
									temp_l[1] = '0'+temp_l[1]
								
								s_time = avail['date'].replace('-', '/') + temp_l[0] + ':' + temp_l[1]
								avail_obj = datetime.strptime(s_time, "%Y/%m/%d%H:%M")
								if avail_obj > datetime.now():
									if Interview.objects.filter(htm__in=[hr_profile], texted_start_time=json.dumps(avail)).filter(disabled=False):
										interview_obj = Interview.objects.filter(htm__in=[hr_profile], texted_start_time=json.dumps(avail)).filter(disabled=False).last()
										openposition_obj = OpenPosition.objects.get(id=interview_obj.op_id.id)
										avail["scheduled"] = True
										avail['position_name'] = openposition_obj.position_title
									else:
										avail["scheduled"] = False
									new_avails.append(avail)
							except Exception as e:
								print(e)
								avail["scheduled_error"] = str(e)
						new_avails.sort(key=lambda item:item['date'])
						hr_dict['schedule'] = new_avails
					except Exception as e:
						hr_dict['error'] = str(e)
						hr_dict['schedule'] = []
					temp_dict['human_resource'] = hr_dict
				except Exception as e:
					temp_dict['human_resource'] = hr_dict if hr_dict else None
				try:
					members_list = json.loads(i.members)
				except Exception as e:
					print(e)
				members_list = list(i.members_list.all().values_list("id", flat=True))
				# Add HM as member
				hiring_manager_hod = i.hod_profile
				if hiring_manager_hod:
					member_dict = {}
					member_dict['id'] = hiring_manager_hod.id
					member_dict['name'] = hiring_manager_hod.user.first_name + ' ' + hiring_manager_hod.user.last_name
					member_dict['client_id'] = int(hiring_manager_hod.client)
					member_dict['email'] = hiring_manager_hod.email
					member_dict['username'] = hiring_manager_hod.user.username
					member_dict['profile_photo'] = hiring_manager_hod.profile_photo
					member_dict['withdrawed'] = False
					member_dict['phone_number'] = hiring_manager_hod.phone_number
					member_dict['linkedin_id'] = hiring_manager_hod.skype_id
					member_dict['role'] = "Hiring Manager"
					try:
						member_dict['color'] = HTMsDeadline.objects.get(htm__id=hiring_manager_hod.id, open_position__id=q_op_id).color
						colors.append(member_dict['color'])
					except Exception as e:
						color = random.choice(COLORS)
						while color in colors:
							color = random.choice(COLORS)
						else:
							colors.append(color)
						member_dict['color'] = color
					# Get HM availabilities
					try:
						htm_avail = HTMAvailability.objects.get(htm_id=hiring_manager_hod.id)
						# member_dict['color'] = htm_avail.color
						avails = json.loads(htm_avail.availability)
						member_dict['schedule'] = []
						new_avails = []
						for avail in avails:
							try:
								temp_l = avail["hours"][0]["startTime"].split(":")
								if len(temp_l[0])==1:
									temp_l[0] = '0'+temp_l[0]
								if len(temp_l[0])==1:
									temp_l[1] = '0'+temp_l[1]
								
								s_time = avail['date'].replace('-', '/') + temp_l[0] + ':' + temp_l[1]
								avail_obj = datetime.strptime(s_time, "%Y/%m/%d%H:%M")
								if avail_obj > datetime.now():
									if Interview.objects.filter(htm__in=[hiring_manager_hod], texted_start_time=json.dumps(avail)).filter(disabled=False):
										interview_obj = Interview.objects.filter(htm__in=[hiring_manager_hod], texted_start_time=json.dumps(avail)).filter(disabled=False).last()
										openposition_obj = OpenPosition.objects.get(id=interview_obj.op_id.id)
										avail["scheduled"] = True
										avail['position_name'] = openposition_obj.position_title
									else:
										avail["scheduled"] = False
									new_avails.append(avail)
							except Exception as e:
								print(e)
								avail["scheduled_error"] = str(e)
						new_avails.sort(key=lambda item:item['date'])
						member_dict['schedule'] = new_avails
							
					except Exception as e:
						member_dict['error'] = str(e)
						member_dict['schedule'] = []
					temp_dict["members"].append(member_dict)
				else:
					pass
				for j in members_list:
					try:
						if i.hr_profile and (j == i.hr_profile.id or j == i.hr_profile):
							pass
						elif i.hod_profile and (j == i.hod_profile.id or j == i.hod_profile):
							pass
						else:
							profile = Profile.objects.get(id=j)
							member_dict = {}
							member_dict['id'] = profile.id
							member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
							member_dict['client_id'] = int(profile.client)
							member_dict['email'] = profile.email
							member_dict['username'] = profile.user.username
							member_dict['profile_photo'] = profile.profile_photo
							member_dict['withdrawed'] = False
							member_dict['phone_number'] = profile.phone_number
							member_dict['linkedin_id'] = profile.skype_id
							member_dict['role'] = "Hiring Team Member"
							try:
								member_dict['color'] = HTMsDeadline.objects.get(htm__id=profile.id, open_position__id=q_op_id).color
								colors.append(member_dict['color'])
							except Exception as e:
								color = random.choice(COLORS)
								while color in colors:
									color = random.choice(COLORS)
								else:
									colors.append(color)
								member_dict['color'] = color
							try:
								htm_avail = HTMAvailability.objects.get(htm_id=profile.id)
								# member_dict['color'] = htm_avail.color
								member_dict['schedule'] = json.loads(htm_avail.availability)
								avails = json.loads(htm_avail.availability)
								member_dict['schedule'] = []
								new_avails = []
								for avail in avails:
									try:
										temp_l = avail["hours"][0]["startTime"].split(":")
										if len(temp_l[0])==1:
											temp_l[0] = '0'+temp_l[0]
										if len(temp_l[0])==1:
											temp_l[1] = '0'+temp_l[1]
										
										s_time = avail['date'].replace('-', '/') + temp_l[0] + ':' + temp_l[1]
										avail_obj = datetime.strptime(s_time, "%Y/%m/%d%H:%M")
										if avail_obj > datetime.now():
											if Interview.objects.filter(htm__in=[profile], interview_date_time=avail_obj).filter(disabled=False):
												interview_obj = Interview.objects.filter(htm__in=[profile], texted_start_time=json.dumps(avail)).filter(disabled=False).last()
												openposition_obj = OpenPosition.objects.get(id=interview_obj.op_id.id)
												avail["scheduled"] = True
												avail['position_name'] = openposition_obj.position_title
											else:
												avail["scheduled"] = False
											new_avails.append(avail)
									except Exception as e:
										print(e)
										avail["scheduled_error"] = str(e)
								new_avails.sort(key=lambda item:item['date'])
								member_dict['schedule'] = new_avails
							except Exception as e:
								member_dict['error'] = str(e)
								member_dict['schedule'] = []
							temp_dict["members"].append(member_dict)
					except Exception as e:
						print(e)
						temp_dict['members_error'] = str(e)

				# Add HR as Member
				if hr_dict:
					member_dict = {}
					try:
						hr_profile = i.hr_profile
						member_dict['id'] = hr_profile.id
						member_dict['name'] = hr_profile.user.first_name + ' ' + hr_profile.user.last_name
						member_dict['client_id'] = int(hr_profile.client)
						member_dict['email'] = hr_profile.email
						member_dict['username'] = hr_profile.user.username
						member_dict['profile_photo'] = hr_profile.profile_photo
						member_dict['withdrawed'] = False
						member_dict['phone_number'] = hr_profile.phone_number
						member_dict['linkedin_id'] = hr_profile.skype_id
						member_dict['role'] = "Human Resource"
						try:
							member_dict['color'] = HTMsDeadline.objects.get(htm__id=hr_profile.id, open_position__id=q_op_id).color
							colors.append(member_dict['color'])
						except Exception as e:
							color = random.choice(COLORS)
							while color in colors:
								color = random.choice(COLORS)
							else:
								colors.append(color)
							member_dict['color'] = color
						try:
							htm_avail = HTMAvailability.objects.get(htm_id=hr_profile.id)
							# member_dict['color'] = htm_avail.color
							
							avails = json.loads(htm_avail.availability)
							member_dict['schedule'] = []
							new_avails = []
							for avail in avails:
								try:
									temp_l = avail["hours"][0]["startTime"].split(":")
									if len(temp_l[0])==1:
										temp_l[0] = '0'+temp_l[0]
									if len(temp_l[0])==1:
										temp_l[1] = '0'+temp_l[1]
									
									s_time = avail['date'].replace('-', '/') + temp_l[0] + ':' + temp_l[1]
									avail_obj = datetime.strptime(s_time, "%Y/%m/%d%H:%M")
									if avail_obj > datetime.now():
										if Interview.objects.filter(htm__in=[hr_profile], texted_start_time=json.dumps(avail)).filter(disabled=False):
											interview_obj = Interview.objects.filter(htm__in=[hr_profile], texted_start_time=json.dumps(avail)).filter(disabled=False).last()
											openposition_obj = OpenPosition.objects.get(id=interview_obj.op_id.id)
											avail["scheduled"] = True
											avail['position_name'] = openposition_obj.position_title
										else:
											avail["scheduled"] = False
										new_avails.append(avail)
								except Exception as e:
									print(e)
									avail["scheduled_error"] = str(e)
							new_avails.sort(key=lambda item:item['date'])
							member_dict['schedule'] = new_avails
								
						except Exception as e:
							member_dict['error'] = str(e)
							member_dict['schedule'] = []
						temp_dict["members"].append(member_dict)
					except Exception as e:
						pass
				else:
					pass
				data.append(temp_dict)
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AddGroupMemberView(APIView):
	def post(self, request):
		try:
			group_obj = HiringGroup.objects.get(group_id=request.data.get("group_id"))
			data = request.data
			data['members'] = json.dumps(data['members'])
			data['members_list'] = data.get("members", [])
			group_serializer = HiringGroupSerializer(group_obj, data=data, partial=True)
			if group_serializer.is_valid():
				group_serializer.save()
			else:
				return Response({'error': str(group_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
			response = {}
			response['msg'] = 'members added in group'
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(UpdateAPIView):
	serializer_class = ChangePasswordSerializer
	model = User
	permission_classes = (IsAuthenticated,)

	def update(self, request, *args, **kwargs):
		try:
			serializer = self.get_serializer(data=request.data)
			if serializer.is_valid():
				self.object = User.objects.get(username=serializer.data.get("username"))
				self.object.set_password(serializer.data.get("new_password"))
				self.object.save()
				response = {}
				for admin in User.objects.filter(is_superuser=True):
					tasks.send_app_notification.delay(admin.username, 'Password is changed for user {}'.format(serializer.data.get("username")))
					tasks.push_notification.delay([admin.username], 'Qorums Notification', 'Password is changed for user {}'.format(serializer.data.get("username")))
				for ae in Profile.objects.filter(roles__contains="is_ae"):
					tasks.send_app_notification.delay(ae.user.username, 'Password is changed for user {}'.format(serializer.data.get("username")))
					tasks.push_notification.delay([ae.user.username], 'Qorums Notification', 'Password is changed for user {}'.format(serializer.data.get("username")))
				response['msg'] = 'changed'
				return Response(response, status=status.HTTP_200_OK)
			else:
				response = {}
				response['error'] = serializer.errors
				return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PositionView(APIView):
	permission_classes = (IsAuthenticated,)

	def get(self, request, *args, **kwargs):
		try:
			data = []
			if "is_sm" in request.user.profile.roles or "is_ca" in request.user.profile.roles or "is_htm" in request.user.profile.roles:
				for i in OpenPosition.objects.filter(client=int(request.user.profile.client)).distinct('position_title').exclude(position_title__endswith="(COPY)"):
					data.append({'name': i.position_title})
			else:
				for i in OpenPosition.objects.all().distinct('position_title').exclude(position_title__endswith="(COPY)"):
					data.append({'name': i.position_title})
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def post(self, request):
		try:
			position_serializer = PositionTitleSerializer(data=request.data)
			if position_serializer.is_valid():
				position_serializer.save()
			else:
				return Response({'error': position_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
			return Response(position_serializer.data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class QualifyingQuestionView(APIView):
	def get(self, request, *args, **kwargs):
		try:
			questions_objs = QualifyingQuestion.objects.all()
			questions_serializer = QualifyingQuestionSerializer(questions_objs, many=True)
			return Response(questions_serializer.data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def post(self, request):
		try:
			question_serializer = QualifyingQuestionSerializer(data=request.data)
			if question_serializer.is_valid():
				question_serializer.save()
			else:
				return Response({'error': question_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
			return Response(question_serializer.data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Start From Here
class CandidateDataView(APIView):
	# permission_classes = (IsAuthenticated,)

	def post(self, request):
		response = {}
		print('-----------------Start Initial Data----------------------')
		print(request.data)

		print(request.FILES)
		print('-----------------End Initial Data----------------------')
		# try:
		if Candidate.objects.filter(email=request.data.get('email')) or Profile.objects.filter(email=request.data.get('email')):
			return Response({'msg': 'existing email'}, status=status.HTTP_409_CONFLICT)
		data = request.data.copy()
		try:
			client_id = int(request.user.profile.client)
		except:
			client_id = request.data.get('created_by_client')
		data['created_by_client'] = client_id
		# skillsets = json.loads(request.data.get('skillsets'))
		# data['skillsets'] = []
		document_links = request.data.get('document_links[]')
		reference_links = request.data.get('referenceLinks[]')
		print('-----------------Print documment link----------------------')
		print("Get Document Links: ", document_links)
		
		if document_links is None:
			document_links = []
		else:
			pass 
		if reference_links is None:
			reference_links = []
		else:
			pass 
		print("Changed Document Link:", document_links)
		print('-----------------End Print documment link----------------------')
		try:
			print('-----------------Start Removing keys from Data----------------------')
			data.pop('profile_photo', None)
			data.pop('documents[]', None)
			data.pop('document_links[]', None)
			data.pop('references[]', None)
			data.pop('referenceLinks[]', None)
			print('-----------------End Removing keys from Data----------------------')
		except Exception as e:
			print('-----------------Error Removing keys from Data----------------------')
			print(e)
		linkedin_data = {}
		linkedin_data['email'] = request.data.get('linkedin_data[email]')
		linkedin_data['first_name'] = request.data.get('linkedin_data[first_name]')
		linkedin_data['job_title'] = request.data.get('linkedin_data[job_title]')
		linkedin_data['last_name'] = request.data.get('linkedin_data[last_name]')
		linkedin_data['location'] = request.data.get('linkedin_data[location]')
		linkedin_data['phone_number'] = request.data.get('linkedin_data[phone_number]')
		linkedin_data['profile_pic_url'] = request.data.get('linkedin_data[profile_pic_url]')
		linkedin_data['about'] = request.data.get('linkedin_data[about]')
		try:
			linkedin_data['experience'] = json.loads(request.data.get('linkedin_data[experience]'))
		except:
			linkedin_data['experience'] = []
		try:
			linkedin_data['reference'] = json.loads(request.data.get('linkedin_data[reference]'))
		except:
			linkedin_data['reference'] = []
		candidate_serializer = CandidateSerializer(data=data)
		if candidate_serializer.is_valid():
			obj = candidate_serializer.save()
			obj.linkedin_data = linkedin_data
			# obj.skillsets = skillsets
			obj.save()
			print('-----------------Candidate Data Saved----------------------')
		else:
			print('-----------------Candidate Data Save Error----------------------')
			print('-----------------Candidate Data Save Error List----------------------', str(candidate_serializer.errors))
			print(request.data)
			print(request.data.get('skillsets'))
			return Response({'error': candidate_serializer.errors, 'data': str(request.data.get('skillsets'))}, status=status.HTTP_400_BAD_REQUEST)
		username = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))
		password = request.data.get('key')
		hashed_password = request.data.get('ekey')
		first_name = candidate_serializer.data['name']
		last_name = candidate_serializer.data['last_name']
		user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)
		user.set_password(hashed_password)
		user.save()
		try:
			Profile.objects.create(user=user, phone_number=candidate_serializer.data['phone_number'], skype_id=candidate_serializer.data['skype_id'], email=candidate_serializer.data['email'], is_candidate=True)
		except Exception as e:
			obj.delete()
			user.delete()
			return Response({'msg': str(e)}, status=status.HTTP_409_CONFLICT)
		candidate_obj = Candidate.objects.get(candidate_id=candidate_serializer.data['candidate_id'])
		candidate_obj.user = user.id
		candidate_obj.username = username
		candidate_obj.key = password
		# Send mail to candidate
		d = {
			"user_name": candidate_obj.name,
			"username": user.username,
			"password": password,
		}
		subject = "New Candidate Created - Qorums"
		# htmly_b = get_template('candidate_added.html')
		# text_content = ""
		# html_content = htmly_b.render(d)
		# Candidate Added Email for Candidate
		try:
			reply_to = request.user.profile.email
			sender_name = request.user.get_full_name()
		except:
			reply_to = 'noreply@qorums.com'
			sender_name = 'No Reply'
		try:
			email_template = EmailTemplate.objects.get(client__id=client_id, name="Candidate Added Email for Candidate")
			template = Template(email_template.content)
			context = Context(d)
		except:
			email_template = EmailTemplate.objects.get(client=None, name="Candidate Added Email for Candidate")
			template = Template(email_template.content)
			context = Context(d)
		html_content = template.render(context)
		try:
			tasks.send.delay(subject, html_content, 'html', [candidate_obj.email], reply_to, sender_name)
		except Exception as e:
			return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
		try:
			print('-----------------Try Getting Profile Photo----------------------')
			print('Request Files:', request.FILES)
			profile_photo = request.FILES['profile_photo']
			p_fs = FileSystemStorage()
			profile_filename = p_fs.save(profile_photo.name, profile_photo)
			uploaded_profile_photo = p_fs.url(profile_filename)
			print('-----------------Profile Photo Saved----------------------')
		except Exception as e:
			print('-----------------Error Getting Profile Photo----------------------')
			print(e)
			uploaded_profile_photo = candidate_obj.profile_photo
		# Check for linkedin photo
		if linkedin_data['profile_pic_url']:
			if linkedin_data['profile_pic_url'].startswith("/"):
				candidate_obj.profile_photo = linkedin_data['profile_pic_url']
				candidate_obj.save()
			elif linkedin_data['profile_pic_url'].startswith("h"):
				url = linkedin_data['profile_pic_url']
				img_tmp = NamedTemporaryFile(delete=True)
				with urlopen(url) as uo:
					assert uo.status == 200
					img_tmp.write(uo.read())
					img_tmp.flush()
				img = File(img_tmp)
				candidate_obj.temp_profile_photo.save(img_tmp.name.split('/')[-1], img)
				candidate_obj.profile_photo = candidate_obj.temp_profile_photo.url
				response['url'] = candidate_obj.temp_profile_photo.url
				candidate_obj.save()
		# Saving Documents
		docs_list = []
		try:
			print('-----------------Try Getting Documents----------------------')
			print(request.data)
			print(request.FILES)
			print(request.data.get('documents[]'))
			print(request.FILES.getlist('documents[]'))
			if request.FILES.getlist('documents[]'):
				for doc in request.FILES.getlist('documents[]'):
					print('-----------------For loop Docs----------------------')
					print(doc)
					p_fs = FileSystemStorage()
					profile_filename = p_fs.save(doc.name, doc)
					uploaded_doc = p_fs.url(profile_filename)
					docs_list.append(uploaded_doc)
		except Exception as e:
			print('-----------------Error Getting Documents List----------------------')
			print(e)
		try:
			candidate_document_lists = json.loads(candidate_obj.documents)
		except:
			candidate_document_lists = []
		if candidate_document_lists:
			for i in candidate_document_lists:
				if i not in document_links:
					try:
						candidate_document_lists.remove(i)
					except Exception as e:
						print('-----------------Removing Unwated Links----------------------')
						print(e)
				# uploaded_doc = candidate_obj.profile_photo
		if docs_list:
			pass
		else:
			docs_list = []
		if candidate_document_lists:
			pass
		else:
			candidate_document_lists = []
		candidate_obj.documents = json.dumps(docs_list + candidate_document_lists)
		# Getting References
		refs_list = []
		try:
			print('-----------------Try Getting References----------------------')
			print(request.data)
			print(request.FILES)
			print(request.data.get('references[]'))
			print(request.FILES.getlist('references[]'))
			if request.FILES.getlist('references[]'):
				for doc in request.FILES.getlist('references[]'):
					print('-----------------For loop Docs----------------------')
					print(doc)
					p_fs = FileSystemStorage()
					profile_filename = p_fs.save(doc.name, doc)
					uploaded_doc = p_fs.url(profile_filename)
					refs_list.append(uploaded_doc)
		except Exception as e:
			print('-----------------Error Getting Documents List----------------------')
			print(e)
		try:
			candidate_ref_lists = json.loads(candidate_obj.references)
		except:
			candidate_ref_lists = []
		if candidate_ref_lists:
			for i in candidate_ref_lists:
				if i not in reference_links:
					try:
						candidate_ref_lists.remove(i)
					except Exception as e:
						print('-----------------Removing Unwated Links----------------------')
						print(e)
				# uploaded_doc = candidate_obj.profile_photo
		if refs_list:
			pass
		else:
			refs_list = []
		if candidate_ref_lists:
			pass
		else:
			candidate_ref_lists = []
		candidate_obj.references = json.dumps(refs_list + candidate_ref_lists)
		
		candidate_obj.profile_photo = uploaded_profile_photo
		if request.data.get('profile_photo_deleted') == "true":
			candidate_obj.profile_photo = None
		candidate_obj.save()
		updated_candidate_serializer = CandidateSerializer(candidate_obj)
		data = updated_candidate_serializer.data
		data['response'] = response
		data['password'] = password
		data['hashed_password'] = hashed_password

		return Response(data, status=status.HTTP_200_OK)
		# except Exception as e:
		# 	return Response({'msg': str(e), "response": response}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request, op_id):
		try:
			candidate_objs = Candidate.objects.filter(op_id=op_id)
			candidate_serializer = CandidateSerializer(candidate_objs, many=True)
			data = candidate_serializer.data
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			for i in data:
				try:
					candidate_marks_obj = CandidateMarks.objects.get(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=logged_user_profile.id)
					i['feedback'] = True
				except:
					i['feedback'] = False
					i['flag'] = None
					continue
				if candidate_marks_obj.thumbs_up:
					i['flag'] = 'Thumbs Up'
				if candidate_marks_obj.thumbs_down:
					i['flag'] = 'Thumbs Down'
				if candidate_marks_obj.hold:
					i['flag'] = 'Hold'
				if candidate_marks_obj.golden_gloves:
					i['flag'] = 'Golden Gloves'
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request):
		try:
			response = {}
			print('---------------------------------------')
			print(request.data)
			print(request.FILES)
			data = request.data.copy()
			# skillsets = json.loads(request.data.get('skillsets'))
			# data['skillsets'] = []
			document_links = request.data.get('documentLinks[]')
			reference_links = request.data.get('referenceLinks[]')
			if document_links is None:
				document_links = []
			else:
				pass
			if reference_links is None:
				reference_links = []
			else:
				pass
			try:
				data.pop('profile_photo', None)
				data.pop('documents', None)
				data.pop('documentLinks[]', None)
				data.pop('referenceLinks[]', None)
			except Exception as e:
				print("error here")
				print(e)
			linkedin_data = {}
			linkedin_data['email'] = request.data.get('linkedin_data[email]')
			linkedin_data['first_name'] = request.data.get('linkedin_data[first_name]')
			linkedin_data['job_title'] = request.data.get('linkedin_data[job_title]')
			linkedin_data['last_name'] = request.data.get('linkedin_data[last_name]')
			linkedin_data['location'] = request.data.get('linkedin_data[location]')
			linkedin_data['phone_number'] = request.data.get('linkedin_data[phone_number]')
			linkedin_data['profile_pic_url'] = request.data.get('linkedin_data[profile_pic_url]')
			linkedin_data['about'] = request.data.get('linkedin_data[about]')
			try:
				linkedin_data['experience'] = json.loads(request.data.get('linkedin_data[experience]'))
			except:
				linkedin_data['experience'] = []
			try:
				linkedin_data['reference'] = json.loads(request.data.get('linkedin_data[reference]'))
			except:
				linkedin_data['reference'] = []
			candidate_obj = Candidate.objects.get(candidate_id=request.data.get('candidate_id'))
			if request.data.get('email') and candidate_obj.email != request.data.get('email'):
				if Candidate.objects.filter(email=request.data.get('email')) or Profile.objects.filter(email=request.data.get('email')):
					return Response({'msg': 'existing email'}, status=status.HTTP_409_CONFLICT)
			candidate_serializer = CandidateSerializer(candidate_obj, data=data, partial=True)
			if candidate_serializer.is_valid():
				obj = candidate_serializer.save()
				obj.linkedin_data = linkedin_data
				# obj.skillsets = skillsets
				obj.save()
				try:
					profile_photo = request.FILES['profile_photo']
					p_fs = FileSystemStorage()
					profile_filename = p_fs.save(profile_photo.name, profile_photo)
					uploaded_profile_photo = p_fs.url(profile_filename)
				except Exception as e:
					print(e)
					uploaded_profile_photo = candidate_obj.profile_photo
				docs_list = []
				try:
					for doc in request.FILES.getlist('documents[]'):
						p_fs = FileSystemStorage()
						profile_filename = p_fs.save(doc.name, doc)
						uploaded_doc = p_fs.url(profile_filename)
						docs_list.append(uploaded_doc)
						# print(docs_list)
				except Exception as e:
					# print("1")
					print(e)
				try:
					candidate_document_lists = json.loads(candidate_obj.documents)
				except:
					candidate_document_lists = []
				if candidate_document_lists:
					pass
				else:
					candidate_document_lists = []
				copy_candidates_docs = candidate_document_lists
				for i in candidate_document_lists:
					if i not in document_links:
						print("Existing link does not exists in document_links, remove", i)
						try:
							copy_candidates_docs.remove(i)
							print(copy_candidates_docs)
						except Exception as e:
							print(e)
							# pass
					# uploaded_doc = candidate_obj.profile_photo
				if docs_list:
					pass
				else:
					docs_list = []
				candidate_obj.documents = json.dumps(docs_list + candidate_document_lists)
				# Save references
				refs_list = []
				try:
					for doc in request.FILES.getlist('references[]'):
						p_fs = FileSystemStorage()
						profile_filename = p_fs.save(doc.name, doc)
						uploaded_doc = p_fs.url(profile_filename)
						refs_list.append(uploaded_doc)
						# print(docs_list)
				except Exception as e:
					# print("1")
					print(e)
				print(refs_list)
				print(candidate_obj.references)
				print(reference_links)
				try:
					candidate_ref_lists = json.loads(candidate_obj.references)
				except:
					candidate_ref_lists = []
				copy_candidates_ref = candidate_ref_lists
				for i in candidate_ref_lists:
					print(i)
					# print("for")
					if i not in reference_links:
						print("Existing link does not exists in document_links, remove", i)
						try:
							copy_candidates_ref.remove(i)
							print(copy_candidates_ref)
						except Exception as e:
							print(e)
							# pass
					# uploaded_doc = candidate_obj.profile_photo
				if docs_list:
					pass
				else:
					docs_list = []
				if refs_list:
					pass
				else:
					refs_list = []
				if candidate_ref_lists:
					pass
				else:
					candidate_ref_lists = []
				candidate_obj.references = json.dumps(refs_list + candidate_ref_lists)
				
				candidate_obj.profile_photo = uploaded_profile_photo
				if request.data.get('profile_photo_deleted') == "true":
					candidate_obj.profile_photo = None
				candidate_obj.updated_at = datetime.now()
				candidate_obj.save()
				# Check for linkedin photo
				if linkedin_data['profile_pic_url']:
					if linkedin_data['profile_pic_url'].startswith("/"):
						candidate_obj.profile_photo = linkedin_data['profile_pic_url']
						candidate_obj.save()
					elif linkedin_data['profile_pic_url'].startswith("h"):
						url = linkedin_data['profile_pic_url']
						img_tmp = NamedTemporaryFile(delete=True)
						with urlopen(url) as uo:
							assert uo.status == 200
							img_tmp.write(uo.read())
							img_tmp.flush()
						img = File(img_tmp)
						candidate_obj.temp_profile_photo.save(img_tmp.name.split('/')[-1], img)
						candidate_obj.profile_photo = candidate_obj.temp_profile_photo.url
						response['url'] = candidate_obj.temp_profile_photo.url
						candidate_obj.save()
			else:
				return Response({'error': candidate_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
			# update candidate user and profile data
			try:
				user_obj = User.objects.get(ussername=candidate_obj.username)
				user_obj.first_name = candidate_obj.name
				user_obj.last_name = candidate_obj.last_name
				user_obj.save()
				user_obj.profile.phone_number = candidate_obj.phone_number
				user_obj.profile.skype_id = candidate_obj.skype_id
				user_obj.profile.email = candidate_obj.email
				user_obj.profile.save()
			except:
				pass
			response['msg'] = 'updated'
			response['data'] = candidate_serializer.data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=int(request.query_params.get('candidate_id')))
			user_id = candidate_obj.user
			candidate_obj.delete()
			try:
				User.objects.get(id=user_id).delete()
			except Exception as e:
				print(e)
			response = {}
			response["msg"] = "deleted"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SingleCandidateDataView(APIView):
	def get(self, request, op_id):
		try:
			candidate_obj = Candidate.objects.filter(candidate_id=int(request.query_params.get('candidate_id')))
			if candidate_obj:
				candidate_serializer = CandidateSerializer(candidate_obj[0])
				response = {}
				response['data'] = candidate_serializer.data
				return Response(response, status=status.HTTP_200_OK)
			else:
				response = {}
				response['msg'] = 'No Candiate Found'
				return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Gives all the HTMs of a Client
class HiringManagerByClient(APIView):
	def get(self, request, id):
		try:
			hiring_manager_objs = Profile.objects.filter(client=id, roles__contains="is_htm")
			members_list = []
			if hiring_manager_objs:
				for i in hiring_manager_objs:
					temp_dict = {}
					temp_dict["id"] = i.id
					temp_dict["name"] = i.user.first_name + ' ' + i.user.last_name
					temp_dict["username"] = i.user.username
					temp_dict["mobile_no"] = i.phone_number
					temp_dict["email"] = i.email
					# client_obj = Client.objects.get(id=i.client)
					temp_dict['client'] = int(i.client)
					members_list.append(temp_dict)
				response = {}
				response['data'] = members_list
			else:
				response = {}
				response['msg'] = 'Not Found'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClientHRView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			if logged_user_profile.is_ca:
				username = request.data.get("username")
				password = request.data.get("password")
				first_name = request.data.get("name")
				user = User.objects.create_user(username=username, password=password, first_name=first_name)
				phone_number = request.data.get("phone_number")
				skype_id = request.data.get("skype_id")
				email = request.data.get("email")
				client = logged_user_profile.client
				if Profile.objects.filter(email=request.data.get("email")) or Candidate.objects.filter(email=request.data.get("email")):
					return Response({'msg': "Email already exists."}, status=status.HTTP_200_OK)
				try:
					Profile.objects.create(user=user, phone_number=phone_number, skype_id=skype_id, email=email, is_ch=True, client=client)
				except Exception as e:
					user.delete()
					return Response({'msg': str(e)}, status=status.HTTP_409_CONFLICT)
				response = {}
				response['msg'] = "added"
				return Response(response, status=status.HTTP_201_CREATED)
			else:
				response = {}
				response['msg'] = "Not a Client Admin"
				return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			if logged_user_profile.is_ca:
				client_hr = int(request.data.get('client_hr'))
				client_hr_obj = Profile.objects.get(id=client_hr)
				client_hr_obj.user.first_name = request.data.get("name")
				client_hr_obj.phone_number = request.data.get("phone_number")
				client_hr_obj.skype_id = request.data.get("skype_id")
				client_hr_obj.email = request.data.get("email")
				client_hr_obj.client = logged_user_profile.client
				client_hr_obj.save()
				client_hr_obj.user.save()
				response = {}
				response['msg'] = "updated"
				return Response(response, status=status.HTTP_201_CREATED)
			else:
				response = {}
				response['msg'] = "Not a Client Admin"
				return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			if logged_user_profile.is_ca:
				client_hr = int(request.query_params.get('client_hr'))
				client_hr_obj = Profile.objects.get(id=client_hr)
				client_hr_dict = {}
				client_hr_dict["id"] = client_hr_obj.id
				client_hr_dict["name"] = client_hr_obj.user.first_name + ' ' + client_hr_obj.user.last_name
				client_hr_dict["username"] = client_hr_obj.user.username
				client_hr_dict["mobile_no"] = client_hr_obj.phone_number
				client_hr_dict["email"] = client_hr_obj.email
				client_hr_dict["skype_id"] = client_hr_obj.skype_id
				# client_obj = Client.objects.get(id=i.client)
				client_hr_dict['client'] = int(client_hr_obj.client)
				response = {}
				response['data'] = [client_hr_dict]
				return Response(response, status=status.HTTP_200_OK)
			else:
				response = {}
				response['msg'] = "Not a Client Admin"
				return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			if logged_user_profile.is_ca:
				client_hr = int(request.query_params.get('client_hr'))
				Profile.objects.filter(id=client_hr).delete()
				response = {}
				response['data'] = "deleted"
				return Response(response, status=status.HTTP_201_CREATED)
			else:
				response = {}
				response['msg'] = "Not a Client Admin"
				return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetAllClientHR(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			client = int(logged_user_profile.client)
			client_hr_obj = Profile.objects.filter(client=client, is_ch=True)
			members_list = []
			if client_hr_obj:
				for i in client_hr_obj:
					temp_dict = {}
					temp_dict["id"] = i.id
					temp_dict["name"] = i.user.first_name + ' ' + i.user.last_name
					temp_dict["username"] = i.user.username
					temp_dict["mobile_no"] = i.phone_number
					temp_dict["skype_id"] = i.skype_id
					temp_dict["email"] = i.email
					temp_dict['client'] = int(i.client)
					members_list.append(temp_dict)
				response = {}
				response['data'] = members_list
			else:
				response = {}
				response['msg'] = 'No HR Found'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Not Used
class GetClientByClinetAdmin(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			if logged_user_profile.is_ca:
				client = logged_user_profile.client
				client_obj = Client.objects.get(id=client)
				clients_serializer = ClientSerializer(client_obj)
				data = clients_serializer.data
				open_positions_obj = OpenPosition.objects.filter(client=data["id"])
				open_position_serializer = OpenPositionSerializer(open_positions_obj, many=True)
				open_position_data = open_position_serializer.data
				data["open_position_data"] = open_position_data
				response = {}
				response['clients'] = data
				return Response(response, status=status.HTTP_201_CREATED)
			else:
				response = {}
				response['msg'] = "Not a Client Admin"
				return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# To give marks
class CandidateMarksView(APIView):
	def post(self, request, op_id):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			open_position_obj = OpenPosition.objects.get(id=op_id)
			hiring_group_obj = HiringGroup.objects.get(group_id=open_position_obj.hiring_group)
			members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
			candidate_id = request.data.get('candidate_id')
			marks_given_by = logged_user_profile.id
			try:
				candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
				if op_id in json.loads(candidate_obj.associated_op_ids):
					pass
				else:
					raise Exception('Candidate do not have this op id')
			except:
				return Response({'msg': 'This Candidate is not associated with this Open Position'}, status=status.HTTP_200_OK)
			try:
				candidate_marks_obj = CandidateMarks.objects.get(candidate_id=candidate_id, op_id=op_id, marks_given_by=marks_given_by)
				return Response({'msg': 'Marks to this Candidate already Given Update it.'}, status=status.HTTP_208_ALREADY_REPORTED)
			except Exception as e:
				print(e)
				CandidateMarks.objects.create(
					candidate_id=candidate_id,
					marks_given_by=marks_given_by,
					op_id=op_id,
					client_id=open_position_obj.client,
					criteria_1_marks=request.data.get('criteria_1_marks'),
					criteria_2_marks=request.data.get('criteria_2_marks'),
					criteria_3_marks=request.data.get('criteria_3_marks'),
					criteria_4_marks=request.data.get('criteria_4_marks'),
					criteria_5_marks=request.data.get('criteria_5_marks'),
					criteria_6_marks=request.data.get('criteria_6_marks'),
					criteria_7_marks=request.data.get('criteria_7_marks'),
					criteria_8_marks=request.data.get('criteria_8_marks'),
					suggestion_1=request.data.get('suggestion_1'),
					suggestion_2=request.data.get('suggestion_2'),
					suggestion_3=request.data.get('suggestion_3'),
					suggestion_4=request.data.get('suggestion_4'),
					suggestion_5=request.data.get('suggestion_5'),
					suggestion_6=request.data.get('suggestion_6'),
					suggestion_7=request.data.get('suggestion_7'),
					suggestion_8=request.data.get('suggestion_8'),
					thumbs_up=request.data.get('thumbs_up'),
					thumbs_down=request.data.get('thumbs_down'),
					hold=request.data.get('hold'),
					golden_gloves=request.data.get('golden_gloves'),
					feedback=request.data.get('feedback')
				)
			# sending mails to hm and sm
			response = {}
			try:
				candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
				client_obj = Client.objects.get(id=open_position_obj.client)
				if hiring_group_obj.hod_profile:
					user_name = hiring_group_obj.hod_profile.user.get_full_name()
				else:
					user_name = "No Manager"
				candidate_name = candidate_obj.name
				posiotion_title = open_position_obj.position_title
				htm_name = Profile.objects.get(id=marks_given_by).user.get_full_name()
				subject = 'A candidate, {}, has received a Golden Glove vote while interviewing for the {} opening.'.format(htm_name, posiotion_title)
				d = {
					"company": client_obj.company_name,
					"candidate_name": candidate_name,
					"posiotion_title": posiotion_title,
					"user_name": user_name,
					"htm_name": htm_name
				}
				# htmly_b = get_template('golden_glove.html')
				# html_content = htmly_b.render(d)
				# send mail to htm
				hm_email = "noreply@qorums.com"
				try:
					profile = hiring_group_obj.hod_profile
					reply_to = profile.email
					hm_email = profile.email
					sender_name = profile.user.get_full_name()
				except:
					reply_to = 'noreply@qorums.com'
					sender_name = 'No Reply'
				try:
					email_template = EmailTemplate.objects.get(client__id=open_position_obj.client, name="Golden Glove Email")
					template = Template(email_template.content)
					context = Context(d)
				except:
					email_template = EmailTemplate.objects.get(client=None, name="Golden Glove Email")
					template = Template(email_template.content)
					context = Context(d)
				html_content = template.render(context)
				try:
					tasks.send.delay(subject, html_content, 'html', [hm_email], reply_to, sender_name)
				except Exception as e:
					response["mail-error-hm"] = str(e)
				# send mail to sm
				for sm in Profile.objects.get(client=str(client_obj.id), is_sm=True):
					subject = 'A candidate, {}, has received a Golden Glove vote while interviewing for the {} opening.'.format(htm_name, posiotion_title)
					d["user_name"] = sm.user.get_full_name()
					# htmly_b = get_template('golden_glove.html')
					# html_content = htmly_b.render(d)
					try:
						email_template = EmailTemplate.objects.get(client__id=open_position_obj.client, name="Golden Glove Email")
						template = Template(email_template.content)
						context = Context(d)
					except:
						email_template = EmailTemplate.objects.get(client=None, name="Golden Glove Email")
						template = Template(email_template.content)
						context = Context(d)
					html_content = template.render(context)
					try:
						profile = sm
						reply_to = profile.email
						sender_name = profile.user.get_full_name()
					except:
						reply_to = 'noreply@qorums.com'
						sender_name = 'No Reply'
					try:
						tasks.send.delay(subject, html_content, 'html', [sm.email], reply_to, sender_name)
					except Exception as e:
						response["mail-error-sm"] = str(e)
			except Exception as e:
				response["mail-error"] = str(e)
			response['msg'] = 'marks added'
			for i in Candidate.objects.all():
				i.save()
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request, op_id):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			open_position_obj = OpenPosition.objects.get(id=op_id)
			hiring_group_obj = HiringGroup.objects.get(group_id=open_position_obj.hiring_group)
			members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
			candidate_id = request.data.get('candidate_id')
			marks_given_by = logged_user_profile.id
			try:
				candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=candidate_id, op_id=op_id, marks_given_by=marks_given_by)[0]
			except Exception as e:
				print(e)
				response = {}
				response['msg'] = 'No Such Candidate Found For This Open Position and Current Logged Hiring Member!'
				response['error'] = str(e)
				response['logged'] = logged_user_profile.id
				return Response(response, status=status.HTTP_200_OK)
			candidate_marks_obj.criteria_1_marks = request.data.get('criteria_1_marks')
			candidate_marks_obj.criteria_2_marks = request.data.get('criteria_2_marks')
			candidate_marks_obj.criteria_3_marks = request.data.get('criteria_3_marks')
			candidate_marks_obj.criteria_4_marks = request.data.get('criteria_4_marks')
			candidate_marks_obj.criteria_5_marks = request.data.get('criteria_5_marks')
			candidate_marks_obj.criteria_6_marks = request.data.get('criteria_6_marks')
			candidate_marks_obj.criteria_7_marks = request.data.get('criteria_7_marks')
			candidate_marks_obj.criteria_8_marks = request.data.get('criteria_8_marks')
			candidate_marks_obj.thumbs_up = request.data.get('thumbs_up')
			candidate_marks_obj.thumbs_down = request.data.get('thumbs_down')
			candidate_marks_obj.hold = request.data.get('hold')
			candidate_marks_obj.golden_gloves = request.data.get('golden_gloves')
			candidate_marks_obj.feedback = request.data.get('feedback')
			candidate_marks_obj.save()
			response = {}
			response['msg'] = 'marks updated'
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request, op_id):
		try:
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			open_position_obj = OpenPosition.objects.get(id=op_id)
			if "is_htm" in logged_user_profile.roles:
				given_by = logged_user_profile.id
				try:
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=int(request.query_params.get('candidate_id')), op_id=op_id, marks_given_by=logged_user_profile.id)[0]
				except Exception as e:
					print(e)
					response = {}
					response['msg'] = '!!No Such Candidate Found For This Open Position and Current Logged Hiring Member!'
					response['error'] = str(e)
					response['logged'] = logged_user_profile.id
					response['marks_given'] = False
					response['pending_interview_acceptance'] = True
					if Interview.objects.filter(op_id__id=op_id, htm__id__in=[int(given_by)], candidate__candidate_id=int(request.query_params.get('candidate_id')), accepted=True):
						response['pending_interview_acceptance'] = False
					response['data'] = {}
					response['data']['init_qualify_ques_1_text'] = open_position_obj.init_qualify_ques_1
					response['data']['init_qualify_ques_2_text'] = open_position_obj.init_qualify_ques_2
					response['data']['init_qualify_ques_3_text'] = open_position_obj.init_qualify_ques_3
					response['data']['init_qualify_ques_4_text'] = open_position_obj.init_qualify_ques_4
					response['data']['init_qualify_ques_5_text'] = open_position_obj.init_qualify_ques_5
					response['data']['init_qualify_ques_6_text'] = open_position_obj.init_qualify_ques_6
					response['data']['init_qualify_ques_7_text'] = open_position_obj.init_qualify_ques_7
					response['data']['init_qualify_ques_8_text'] = open_position_obj.init_qualify_ques_8
					response['data']['init_qualify_ques_1'] = 0
					response['data']['init_qualify_ques_2'] = 0
					response['data']['init_qualify_ques_3'] = 0
					response['data']['init_qualify_ques_4'] = 0
					response['data']['init_qualify_ques_5'] = 0
					response['data']['init_qualify_ques_6'] = 0
					response['data']['init_qualify_ques_7'] = 0
					response['data']['init_qualify_ques_8'] = 0

					response['data']['init_qualify_ques_weightage_1'] = open_position_obj.init_qualify_ques_weightage_1
					response['data']['init_qualify_ques_weightage_2'] = open_position_obj.init_qualify_ques_weightage_2
					response['data']['init_qualify_ques_weightage_3'] = open_position_obj.init_qualify_ques_weightage_3
					response['data']['init_qualify_ques_weightage_4'] = open_position_obj.init_qualify_ques_weightage_4
					response['data']['init_qualify_ques_weightage_5'] = open_position_obj.init_qualify_ques_weightage_5
					response['data']['init_qualify_ques_weightage_6'] = open_position_obj.init_qualify_ques_weightage_6
					response['data']['init_qualify_ques_weightage_7'] = open_position_obj.init_qualify_ques_weightage_7
					response['data']['init_qualify_ques_weightage_8'] = open_position_obj.init_qualify_ques_weightage_8

					response['data']['init_qualify_ques_suggestion_1'] = open_position_obj.init_qualify_ques_suggestion_1
					response['data']['init_qualify_ques_suggestion_2'] = open_position_obj.init_qualify_ques_suggestion_2
					response['data']['init_qualify_ques_suggestion_3'] = open_position_obj.init_qualify_ques_suggestion_3
					response['data']['init_qualify_ques_suggestion_4'] = open_position_obj.init_qualify_ques_suggestion_4
					response['data']['init_qualify_ques_suggestion_5'] = open_position_obj.init_qualify_ques_suggestion_5
					response['data']['init_qualify_ques_suggestion_6'] = open_position_obj.init_qualify_ques_suggestion_6
					response['data']['init_qualify_ques_suggestion_7'] = open_position_obj.init_qualify_ques_suggestion_7
					response['data']['init_qualify_ques_suggestion_8'] = open_position_obj.init_qualify_ques_suggestion_8

					try:
						htm_weightage_obj = HTMWeightage.objects.filter(op_id=op_id, htm_id=given_by)
						response['data']['htm_weightage_1'] = htm_weightage_obj.init_qualify_ques_1_weightage
						response['data']['htm_weightage_2'] = htm_weightage_obj.init_qualify_ques_2_weightage
						response['data']['htm_weightage_3'] = htm_weightage_obj.init_qualify_ques_3_weightage
						response['data']['htm_weightage_4'] = htm_weightage_obj.init_qualify_ques_4_weightage
						response['data']['htm_weightage_5'] = htm_weightage_obj.init_qualify_ques_5_weightage
						response['data']['htm_weightage_6'] = htm_weightage_obj.init_qualify_ques_6_weightage
						response['data']['htm_weightage_7'] = htm_weightage_obj.init_qualify_ques_7_weightage
						response['data']['htm_weightage_8'] = htm_weightage_obj.init_qualify_ques_8_weightage
					except:
						response['data']['htm_weightage_1'] = 10
						response['data']['htm_weightage_2'] = 10
						response['data']['htm_weightage_3'] = 10
						response['data']['htm_weightage_4'] = 10
						response['data']['htm_weightage_5'] = 10
						response['data']['htm_weightage_6'] = 10
						response['data']['htm_weightage_7'] = 10
						response['data']['htm_weightage_8'] = 10
					# Zoom link
					zoom_links = []
					for i in Interview.objects.filter(op_id__id=op_id, htm__id__in=[int(given_by)], candidate__candidate_id=int(request.query_params.get('candidate_id'))).exclude(zoom_link=None).filter(disabled=False):
						zoom_temp = {}
						zoom_temp['link'] = i.zoom_link
						zoom_temp['meeting_key'] = i.meeting_key
						zoom_temp['conference_id'] = i.conference_id
						timedelta = i.interview_date_time - datetime.now()
						if timedelta.seconds > 1800:
							zoom_temp['disabled'] = True
						else:
							zoom_temp['disabled'] = False
						zoom_temp['date'] = i.interview_date_time.strftime("%m-%d-%Y")
						zoom_temp['time'] = i.interview_date_time.strftime("%I:%M %p")
						zoom_links.append(zoom_temp)
					response['data']['zoom_links'] = zoom_links
					response['zoom_links'] = zoom_links
					return Response(response, status=status.HTTP_200_OK)
				marks_dict = {}
				marks_dict['init_qualify_ques_1_text'] = open_position_obj.init_qualify_ques_1
				marks_dict['init_qualify_ques_2_text'] = open_position_obj.init_qualify_ques_2
				marks_dict['init_qualify_ques_3_text'] = open_position_obj.init_qualify_ques_3
				marks_dict['init_qualify_ques_4_text'] = open_position_obj.init_qualify_ques_4
				marks_dict['init_qualify_ques_5_text'] = open_position_obj.init_qualify_ques_5
				marks_dict['init_qualify_ques_6_text'] = open_position_obj.init_qualify_ques_6
				marks_dict['init_qualify_ques_7_text'] = open_position_obj.init_qualify_ques_7
				marks_dict['init_qualify_ques_8_text'] = open_position_obj.init_qualify_ques_8
				
				marks_dict['candidate_id'] = candidate_marks_obj.candidate_id
				marks_dict['init_qualify_ques_1'] = candidate_marks_obj.criteria_1_marks
				marks_dict['init_qualify_ques_2'] = candidate_marks_obj.criteria_2_marks
				marks_dict['init_qualify_ques_3'] = candidate_marks_obj.criteria_3_marks
				marks_dict['init_qualify_ques_4'] = candidate_marks_obj.criteria_4_marks
				marks_dict['init_qualify_ques_5'] = candidate_marks_obj.criteria_5_marks
				marks_dict['init_qualify_ques_6'] = candidate_marks_obj.criteria_6_marks
				marks_dict['init_qualify_ques_7'] = candidate_marks_obj.criteria_7_marks
				marks_dict['init_qualify_ques_8'] = candidate_marks_obj.criteria_8_marks

				marks_dict['suggestion_1'] = candidate_marks_obj.suggestion_1
				marks_dict['suggestion_2'] = candidate_marks_obj.suggestion_2
				marks_dict['suggestion_3'] = candidate_marks_obj.suggestion_3
				marks_dict['suggestion_4'] = candidate_marks_obj.suggestion_4
				marks_dict['suggestion_5'] = candidate_marks_obj.suggestion_5
				marks_dict['suggestion_6'] = candidate_marks_obj.suggestion_6
				marks_dict['suggestion_7'] = candidate_marks_obj.suggestion_7
				marks_dict['suggestion_8'] = candidate_marks_obj.suggestion_8

				marks_dict['init_qualify_ques_weightage_1'] = open_position_obj.init_qualify_ques_weightage_1
				marks_dict['init_qualify_ques_weightage_2'] = open_position_obj.init_qualify_ques_weightage_2
				marks_dict['init_qualify_ques_weightage_3'] = open_position_obj.init_qualify_ques_weightage_3
				marks_dict['init_qualify_ques_weightage_4'] = open_position_obj.init_qualify_ques_weightage_4
				marks_dict['init_qualify_ques_weightage_5'] = open_position_obj.init_qualify_ques_weightage_5
				marks_dict['init_qualify_ques_weightage_6'] = open_position_obj.init_qualify_ques_weightage_6
				marks_dict['init_qualify_ques_weightage_7'] = open_position_obj.init_qualify_ques_weightage_7
				marks_dict['init_qualify_ques_weightage_8'] = open_position_obj.init_qualify_ques_weightage_8

				marks_dict['init_qualify_ques_suggestion_1'] = open_position_obj.init_qualify_ques_suggestion_1
				marks_dict['init_qualify_ques_suggestion_2'] = open_position_obj.init_qualify_ques_suggestion_2
				marks_dict['init_qualify_ques_suggestion_3'] = open_position_obj.init_qualify_ques_suggestion_3
				marks_dict['init_qualify_ques_suggestion_4'] = open_position_obj.init_qualify_ques_suggestion_4
				marks_dict['init_qualify_ques_suggestion_5'] = open_position_obj.init_qualify_ques_suggestion_5
				marks_dict['init_qualify_ques_suggestion_6'] = open_position_obj.init_qualify_ques_suggestion_6
				marks_dict['init_qualify_ques_suggestion_7'] = open_position_obj.init_qualify_ques_suggestion_7
				marks_dict['init_qualify_ques_suggestion_8'] = open_position_obj.init_qualify_ques_suggestion_8

				marks_dict['op_id'] = candidate_marks_obj.op_id
				marks_dict['thumbs_up'] = candidate_marks_obj.thumbs_up
				marks_dict['thumbs_down'] = candidate_marks_obj.thumbs_down
				marks_dict['hold'] = candidate_marks_obj.hold
				marks_dict['golden_gloves'] = candidate_marks_obj.golden_gloves
				marks_dict['feedback'] = candidate_marks_obj.feedback
				response = {}
				response['data'] = marks_dict
				response['marks_given'] = True
				try:
					htm_weightage_obj = HTMWeightage.objects.filter(op_id=op_id, htm_id=given_by)
					response['data']['htm_weightage_1'] = htm_weightage_obj.init_qualify_ques_1_weightage
					response['data']['htm_weightage_2'] = htm_weightage_obj.init_qualify_ques_2_weightage
					response['data']['htm_weightage_3'] = htm_weightage_obj.init_qualify_ques_3_weightage
					response['data']['htm_weightage_4'] = htm_weightage_obj.init_qualify_ques_4_weightage
					response['data']['htm_weightage_5'] = htm_weightage_obj.init_qualify_ques_5_weightage
					response['data']['htm_weightage_6'] = htm_weightage_obj.init_qualify_ques_6_weightage
					response['data']['htm_weightage_7'] = htm_weightage_obj.init_qualify_ques_7_weightage
					response['data']['htm_weightage_8'] = htm_weightage_obj.init_qualify_ques_8_weightage
				except:
					response['data']['htm_weightage_1'] = 10
					response['data']['htm_weightage_2'] = 10
					response['data']['htm_weightage_3'] = 10
					response['data']['htm_weightage_4'] = 10
					response['data']['htm_weightage_5'] = 10
					response['data']['htm_weightage_6'] = 10
					response['data']['htm_weightage_7'] = 10
					response['data']['htm_weightage_8'] = 10
				zoom_links = []
				for i in Interview.objects.filter(op_id__id=op_id, htm__id__in=[int(given_by)], candidate__candidate_id=int(request.query_params.get('candidate_id'))).filter(disabled=False):
					zoom_temp = {}
					zoom_temp['link'] = i.zoom_link
					zoom_temp['meeting_key'] = i.meeting_key
					zoom_temp['conference_id'] = i.conference_id
					timedelta = i.interview_date_time - datetime.now()
					if timedelta.seconds > 1800:
						zoom_temp['disabled'] = True
					else:
						zoom_temp['disabled'] = False
					zoom_temp['date'] = i.interview_date_time.strftime("%m-%d-%Y")
					zoom_temp['time'] = i.interview_date_time.strftime("%I:%M %p")
					zoom_links.append(zoom_temp)
				response['data']['zoom_links'] = zoom_links
				response['zoom_links'] = zoom_links
				return Response(response, status=status.HTTP_200_OK)
			else:
				try:
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=int(request.query_params.get('candidate_id')), op_id=op_id)[0]
				except Exception as e:
					print(e)
					response = {}
					response['msg'] = 'No Such Candidate Found For This Open Position and Current Logged Hiring Member!'
					response['error'] = str(e)
					response['logged'] = logged_user_profile.id
					response['marks_given'] = False
					response['pending_interview_acceptance'] = True
					if Interview.objects.filter(op_id__id=op_id, htm__id__in=[int(logged_user_profile.id)], candidate__candidate_id=int(request.query_params.get('candidate_id')), accepted=True):
						response['pending_interview_acceptance'] = False
					response['data'] = {}
					response['data']['init_qualify_ques_1_text'] = open_position_obj.init_qualify_ques_1
					response['data']['init_qualify_ques_2_text'] = open_position_obj.init_qualify_ques_2
					response['data']['init_qualify_ques_3_text'] = open_position_obj.init_qualify_ques_3
					response['data']['init_qualify_ques_4_text'] = open_position_obj.init_qualify_ques_4
					response['data']['init_qualify_ques_5_text'] = open_position_obj.init_qualify_ques_5
					response['data']['init_qualify_ques_6_text'] = open_position_obj.init_qualify_ques_6
					response['data']['init_qualify_ques_7_text'] = open_position_obj.init_qualify_ques_7
					response['data']['init_qualify_ques_8_text'] = open_position_obj.init_qualify_ques_8
					response['data']['init_qualify_ques_1'] = 0
					response['data']['init_qualify_ques_2'] = 0
					response['data']['init_qualify_ques_3'] = 0
					response['data']['init_qualify_ques_4'] = 0
					response['data']['init_qualify_ques_5'] = 0
					response['data']['init_qualify_ques_6'] = 0
					response['data']['init_qualify_ques_7'] = 0
					response['data']['init_qualify_ques_8'] = 0

					response['data']['init_qualify_ques_weightage_1'] = open_position_obj.init_qualify_ques_weightage_1
					response['data']['init_qualify_ques_weightage_2'] = open_position_obj.init_qualify_ques_weightage_2
					response['data']['init_qualify_ques_weightage_3'] = open_position_obj.init_qualify_ques_weightage_3
					response['data']['init_qualify_ques_weightage_4'] = open_position_obj.init_qualify_ques_weightage_4
					response['data']['init_qualify_ques_weightage_5'] = open_position_obj.init_qualify_ques_weightage_5
					response['data']['init_qualify_ques_weightage_6'] = open_position_obj.init_qualify_ques_weightage_6
					response['data']['init_qualify_ques_weightage_7'] = open_position_obj.init_qualify_ques_weightage_7
					response['data']['init_qualify_ques_weightage_8'] = open_position_obj.init_qualify_ques_weightage_8

					response['data']['init_qualify_ques_suggestion_1'] = open_position_obj.init_qualify_ques_suggestion_1
					response['data']['init_qualify_ques_suggestion_2'] = open_position_obj.init_qualify_ques_suggestion_2
					response['data']['init_qualify_ques_suggestion_3'] = open_position_obj.init_qualify_ques_suggestion_3
					response['data']['init_qualify_ques_suggestion_4'] = open_position_obj.init_qualify_ques_suggestion_4
					response['data']['init_qualify_ques_suggestion_5'] = open_position_obj.init_qualify_ques_suggestion_5
					response['data']['init_qualify_ques_suggestion_6'] = open_position_obj.init_qualify_ques_suggestion_6
					response['data']['init_qualify_ques_suggestion_7'] = open_position_obj.init_qualify_ques_suggestion_7
					response['data']['init_qualify_ques_suggestion_8'] = open_position_obj.init_qualify_ques_suggestion_8
					
					return Response(response, status=status.HTTP_200_OK)

				marks_dict = {}
				marks_dict['init_qualify_ques_1_text'] = open_position_obj.init_qualify_ques_1
				marks_dict['init_qualify_ques_2_text'] = open_position_obj.init_qualify_ques_2
				marks_dict['init_qualify_ques_3_text'] = open_position_obj.init_qualify_ques_3
				marks_dict['init_qualify_ques_4_text'] = open_position_obj.init_qualify_ques_4
				marks_dict['init_qualify_ques_5_text'] = open_position_obj.init_qualify_ques_5
				marks_dict['init_qualify_ques_6_text'] = open_position_obj.init_qualify_ques_6
				marks_dict['init_qualify_ques_7_text'] = open_position_obj.init_qualify_ques_7
				marks_dict['init_qualify_ques_8_text'] = open_position_obj.init_qualify_ques_8
				marks_dict['candidate_id'] = candidate_marks_obj.candidate_id
				marks_dict['init_qualify_ques_1'] = candidate_marks_obj.criteria_1_marks
				marks_dict['init_qualify_ques_2'] = candidate_marks_obj.criteria_2_marks
				marks_dict['init_qualify_ques_3'] = candidate_marks_obj.criteria_3_marks
				marks_dict['init_qualify_ques_4'] = candidate_marks_obj.criteria_4_marks
				marks_dict['init_qualify_ques_5'] = candidate_marks_obj.criteria_5_marks
				marks_dict['init_qualify_ques_6'] = candidate_marks_obj.criteria_6_marks
				marks_dict['init_qualify_ques_7'] = candidate_marks_obj.criteria_7_marks
				marks_dict['init_qualify_ques_8'] = candidate_marks_obj.criteria_8_marks

				marks_dict['suggestion_1'] = candidate_marks_obj.suggestion_1
				marks_dict['suggestion_2'] = candidate_marks_obj.suggestion_2
				marks_dict['suggestion_3'] = candidate_marks_obj.suggestion_3
				marks_dict['suggestion_4'] = candidate_marks_obj.suggestion_4
				marks_dict['suggestion_5'] = candidate_marks_obj.suggestion_5
				marks_dict['suggestion_6'] = candidate_marks_obj.suggestion_6
				marks_dict['suggestion_7'] = candidate_marks_obj.suggestion_7
				marks_dict['suggestion_8'] = candidate_marks_obj.suggestion_8

				marks_dict['init_qualify_ques_weightage_1'] = open_position_obj.init_qualify_ques_weightage_1
				marks_dict['init_qualify_ques_weightage_2'] = open_position_obj.init_qualify_ques_weightage_2
				marks_dict['init_qualify_ques_weightage_3'] = open_position_obj.init_qualify_ques_weightage_3
				marks_dict['init_qualify_ques_weightage_4'] = open_position_obj.init_qualify_ques_weightage_4
				marks_dict['init_qualify_ques_weightage_5'] = open_position_obj.init_qualify_ques_weightage_5
				marks_dict['init_qualify_ques_weightage_6'] = open_position_obj.init_qualify_ques_weightage_6
				marks_dict['init_qualify_ques_weightage_7'] = open_position_obj.init_qualify_ques_weightage_7
				marks_dict['init_qualify_ques_weightage_8'] = open_position_obj.init_qualify_ques_weightage_8

				marks_dict['init_qualify_ques_suggestion_1'] = open_position_obj.init_qualify_ques_suggestion_1
				marks_dict['init_qualify_ques_suggestion_2'] = open_position_obj.init_qualify_ques_suggestion_2
				marks_dict['init_qualify_ques_suggestion_3'] = open_position_obj.init_qualify_ques_suggestion_3
				marks_dict['init_qualify_ques_suggestion_4'] = open_position_obj.init_qualify_ques_suggestion_4
				marks_dict['init_qualify_ques_suggestion_5'] = open_position_obj.init_qualify_ques_suggestion_5
				marks_dict['init_qualify_ques_suggestion_6'] = open_position_obj.init_qualify_ques_suggestion_6
				marks_dict['init_qualify_ques_suggestion_7'] = open_position_obj.init_qualify_ques_suggestion_7
				marks_dict['init_qualify_ques_suggestion_8'] = open_position_obj.init_qualify_ques_suggestion_8

				marks_dict['op_id'] = candidate_marks_obj.op_id
				marks_dict['thumbs_up'] = candidate_marks_obj.thumbs_up
				marks_dict['thumbs_down'] = candidate_marks_obj.thumbs_down
				marks_dict['hold'] = candidate_marks_obj.hold
				marks_dict['golden_gloves'] = candidate_marks_obj.golden_gloves
				
				# marks_dict['undecided'] = candidate_marks_obj.undecided
				marks_dict['feedback'] = candidate_marks_obj.feedback
				response = {}
				response['data'] = marks_dict
				response['marks_given'] = True	
				return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CandidateFeedback(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			open_position_obj = OpenPosition.objects.get(id=op_id)
			candidates_obj = []
			for cao in CandidateAssociateData.objects.filter(open_position=open_position_obj):
				if cao.candidate not in candidates_obj:
					candidates_obj.append(cao.candidate)
			candidates_serializer = CandidateSerializer(candidates_obj, many=True)
			data = candidates_serializer.data
			try:
				hiring_group_obj = HiringGroup.objects.get(group_id=open_position_obj.hiring_group)
			except:
				for i in data:
					i['marks'] = {}
					i['final_avg_marks'] = 0
					i['total_hiring_members'] = 1
					i['marks_given_by'] = 0
					i['flag'] = 'Not Given'
					i['op_id'] = op_id
					i['client_id'] = open_position_obj.client
				return Response(data, status=status.HTTP_200_OK)
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			for i in data:
				# Adding Position Specific Resume and References
				try:
					cad = CandidateAssociateData.objects.get(candidate__candidate_id=i['candidate_id'], open_position=open_position_obj)
					i['position_specific_data'] = CandidateAssociateDataSerializer(cad).data
					try:
						if cad.resume:
							docs = []
							for doc in cad.resume:
								temp_doc = {}
								temp_doc["url"] = doc
								temp_doc["name"] = doc.split('/')[-1]
								docs.append(temp_doc)
							i['position_specific_data']['resume'] = docs
						else:
							docs = []
							for doc in json.loads(cad.candidate.documents):
								temp_doc = {}
								temp_doc["url"] = doc
								temp_doc["name"] = doc.split('/')[-1]
								docs.append(temp_doc)
							i['position_specific_data']['resume'] = docs
						
					except Exception as e:
						i['position_specific_data']['resume'] = []
					try:
						docs = []
						if cad.references:
							for doc in cad.references:
								temp_doc = {}
								temp_doc["url"] = doc
								temp_doc["name"] = doc.split('/')[-1]
								docs.append(temp_doc)
							i['position_specific_data']['references'] = docs
						else:
							for doc in json.loads(cad.candidate.references):
								temp_doc = {}
								temp_doc["url"] = doc
								temp_doc["name"] = doc.split('/')[-1]
								docs.append(temp_doc)
							i['position_specific_data']['references'] = docs
					except Exception as e:
						i['position_specific_data']['references'] = []
				except Exception as e:
					i['position_specific_data'] = {}
					i['position_specific_data_error'] = str(e)
				# Additin Profile Picture
				if 'profile_pic_url' in i['linkedin_data'] and i['linkedin_data']['profile_pic_url'] and i['linkedin_data']['profile_pic_url'] != "null":
					i['profile_photo'] = i['linkedin_data']['profile_pic_url']
				else:
					i['profile_photo'] = i['profile_photo']
				i['documents'] = json.loads(i['documents'])
				i['init_qualify_ques_1'] = open_position_obj.init_qualify_ques_1
				i['init_qualify_ques_2'] = open_position_obj.init_qualify_ques_2
				i['init_qualify_ques_3'] = open_position_obj.init_qualify_ques_3
				i['init_qualify_ques_4'] = open_position_obj.init_qualify_ques_4
				i['init_qualify_ques_5'] = open_position_obj.init_qualify_ques_5
				i['init_qualify_ques_6'] = open_position_obj.init_qualify_ques_6
				i['init_qualify_ques_7'] = open_position_obj.init_qualify_ques_7
				i['init_qualify_ques_8'] = open_position_obj.init_qualify_ques_8
				try:
					hire_obj = Hired.objects.get(candidate_id=i['candidate_id'], op_id=op_id)
					i['hired'] = True
				except:
					i['hired'] = False
				try:
					hire_obj = Offered.objects.get(candidate_id=i['candidate_id'], op_id=op_id)
					i['offered'] = True
				except:
					i['offered'] = False
				i['op_id'] = op_id
				if i['op_id'] in json.loads(i['withdrawed_op_ids']):
					i['withdrawed'] = True
				else:
					i['withdrawed'] = False
				if i['op_id'] in i["requested_op_ids"]:
					i["requested"] = True
				else:
					i["requested"] = False
				i['client_id'] = open_position_obj.client
				if "is_htm" in logged_user_profile.roles and hiring_group_obj.hod_profile != request.user.profile and hiring_group_obj.hr_profile != request.user.profile:
					marks_dict = {}
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=logged_user_profile.id)
					given_by = logged_user_profile.id
					try:
						htm_weightage_obj = HTMWeightage.objects.filter(op_id=op_id, htm_id=given_by)
						htm_weightage_1 = htm_weightage_obj.init_qualify_ques_1_weightage
						htm_weightage_2 = htm_weightage_obj.init_qualify_ques_2_weightage
						htm_weightage_3 = htm_weightage_obj.init_qualify_ques_3_weightage
						htm_weightage_4 = htm_weightage_obj.init_qualify_ques_4_weightage
						htm_weightage_5 = htm_weightage_obj.init_qualify_ques_5_weightage
						htm_weightage_6 = htm_weightage_obj.init_qualify_ques_6_weightage
						htm_weightage_7 = htm_weightage_obj.init_qualify_ques_7_weightage
						htm_weightage_8 = htm_weightage_obj.init_qualify_ques_8_weightage
					except:
						htm_weightage_1 = 10
						htm_weightage_2 = 10
						htm_weightage_3 = 10
						htm_weightage_4 = 10
						htm_weightage_5 = 10
						htm_weightage_6 = 10
						htm_weightage_7 = 10
						htm_weightage_8 = 10
					if candidate_marks_obj:
						marks_dict['init_qualify_ques_1'] = candidate_marks_obj[0].criteria_1_marks #* open_position_obj.init_qualify_ques_weightage_1 / htm_weightage_1, 1)
						marks_dict['init_qualify_ques_2'] = candidate_marks_obj[0].criteria_2_marks #* open_position_obj.init_qualify_ques_weightage_2 / htm_weightage_2, 1)
						marks_dict['init_qualify_ques_3'] = candidate_marks_obj[0].criteria_3_marks #* open_position_obj.init_qualify_ques_weightage_3 / htm_weightage_3, 1)
						marks_dict['init_qualify_ques_4'] = candidate_marks_obj[0].criteria_4_marks #* open_position_obj.init_qualify_ques_weightage_4 / htm_weightage_4, 1)
						marks_dict['init_qualify_ques_5'] = candidate_marks_obj[0].criteria_5_marks #* open_position_obj.init_qualify_ques_weightage_5 / htm_weightage_5, 1)
						marks_dict['init_qualify_ques_6'] = candidate_marks_obj[0].criteria_6_marks #* open_position_obj.init_qualify_ques_weightage_6 / htm_weightage_6, 1)
						marks_dict['init_qualify_ques_7'] = candidate_marks_obj[0].criteria_7_marks #* open_position_obj.init_qualify_ques_weightage_7 / htm_weightage_7, 1)
						marks_dict['init_qualify_ques_8'] = candidate_marks_obj[0].criteria_8_marks #* open_position_obj.init_qualify_ques_weightage_8 / htm_weightage_8, 1)
						marks_dict['feedback'] = candidate_marks_obj[0].feedback
						i['marks'] = marks_dict
						avg_marks = 0
						count = 0
						# Algorith to calculate marks based on HTM Weightage and Skills Weightage
						if candidate_marks_obj[0].criteria_1_marks not in [None]: 
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_1_marks * open_position_obj.init_qualify_ques_weightage_1
						if candidate_marks_obj[0].criteria_2_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_2_marks* open_position_obj.init_qualify_ques_weightage_2
						if candidate_marks_obj[0].criteria_3_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_3_marks* open_position_obj.init_qualify_ques_weightage_3
						if candidate_marks_obj[0].criteria_4_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_4_marks* open_position_obj.init_qualify_ques_weightage_4
						if candidate_marks_obj[0].criteria_5_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_5_marks * open_position_obj.init_qualify_ques_weightage_5 #* htm_weightage_5 * open_position_obj.init_qualify_ques_weightage_5
						if candidate_marks_obj[0].criteria_6_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_6_marks * open_position_obj.init_qualify_ques_weightage_6 #* htm_weightage_6 * open_position_obj.init_qualify_ques_weightage_6
						if candidate_marks_obj[0].criteria_7_marks not in [ None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_7_marks * open_position_obj.init_qualify_ques_weightage_7 #* htm_weightage_7 * open_position_obj.init_qualify_ques_weightage_7
						if candidate_marks_obj[0].criteria_8_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_8_marks * open_position_obj.init_qualify_ques_weightage_8 #* htm_weightage_8 * open_position_obj.init_qualify_ques_weightage_8
						i['avg_marks'] = round(avg_marks / count, 1)
						i['total_hiring_members'] = hiring_group_obj.members_list.all().count() - 1
						all_marks_candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id)
						i['final_avg_marks'] = i['avg_marks']  # (all_marks_candidate_marks_obj.aggregate(Avg('criteria_1_marks'))['criteria_1_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_2_marks'))['criteria_2_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_3_marks'))['criteria_3_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_4_marks'))['criteria_4_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_5_marks'))['criteria_5_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_6_marks'))['criteria_6_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_7_marks'))['criteria_7_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_8_marks'))['criteria_8_marks__avg']) / 8
						i['marks_given_by'] = all_marks_candidate_marks_obj.count()
						if candidate_marks_obj[0].thumbs_up:
							i['he_flag'] = 'Thumbs Up'
							i['flag'] = 'Thumbs Up'
						if candidate_marks_obj[0].thumbs_down:
							i['he_flag'] = 'Thumbs Down'
							i['flag'] = 'Thumbs Down'
						if candidate_marks_obj[0].hold:
							i['he_flag'] = 'Hold'
							i['flag'] = 'Hold'
						if candidate_marks_obj[0].golden_gloves:
							i['he_flag'] = 'Golden Glove'
							i['flag'] = 'Golden Glove'
						i['flag_by_hiring_manager'] = []
						temp_dict = {}
						temp_dict['id'] = int(logged_user_profile.id)
						if candidate_marks_obj:
							candidate_marks_obj = candidate_marks_obj[0]
							if candidate_marks_obj.thumbs_up:
								temp_dict['flag'] = 'Thumbs Up'
							if candidate_marks_obj.thumbs_down:
								temp_dict['flag'] = 'Thumbs Down'
							if candidate_marks_obj.hold:
								temp_dict['flag'] = 'Hold'
							if candidate_marks_obj.golden_gloves:
								temp_dict['flag'] = 'Golden Glove'
						else:
							temp_dict['flag'] = 'Not Given'
							try:
								interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[logged_user_profile], candidate__candidate_id=i['candidate_id'])[0]
								# temp_dict['flag'] = 'Interview Scheduled'
								if not interview_obj.accepted:
									temp_dict['flag'] = "Interview NOT CONFIRMED"
								else:
									temp_dict['flag'] = "Interview Confirmed"
									if interview_obj.interview_date_time.date() == datetime.today().date():
										temp_dict['flag'] = "Interview Today"
										temp_dict['button_data'] = {}
										temp_dict['button_data']["type"] = interview_obj.interview_type
										temp_dict['button_data']["link"] = interview_obj.zoom_link
										temp_dict["start_in"] = get_timediff(interview_obj.interview_date_time)
									else:
										temp_dict['button_data'] = {}
										temp_dict['button_data']["type"] = interview_obj.interview_type
										temp_dict['button_data']["link"] = interview_obj.zoom_link
										temp_dict['interviewer'] = hiring_manager_hod.user.get_full_name()
								temp_dict['interviewer'] = logged_user_profile.user.get_full_name()
								# date_time = str(interview_obj.interview_date_time).split()
								temp_dict['date'] = interview_obj.interview_date_time.strftime("%m/%d/%Y")
								temp_dict['time'] = interview_obj.interview_date_time.strftime("%I:%M %p")
							except:
								pass
						i['flag_by_hiring_manager'].append(temp_dict)
					else:
						i['marks'] = {}
						i['final_avg_marks'] = 0
						i['total_hiring_members'] = hiring_group_obj.members_list.all().count() - 1
						i['marks_given_by'] = 0
						i['flag'] = 'Not Given'
						i['flag_by_hiring_manager'] = []
						temp_dict = {}
						temp_dict['id'] = int(logged_user_profile.id)
						try:
							interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[logged_user_profile], candidate__candidate_id=i['candidate_id'])[0]
							# temp_dict['flag'] = 'Interview Scheduled'
							if not interview_obj.accepted:
								temp_dict['flag'] = "Interview NOT CONFIRMED"
							else:
								temp_dict['flag'] = "Interview Confirmed"
								if interview_obj.interview_date_time.date() == datetime.today().date():
									temp_dict['flag'] = "Interview Today"
									temp_dict['button_data'] = {}
									temp_dict['button_data']["type"] = interview_obj.interview_type
									temp_dict['button_data']["link"] = interview_obj.zoom_link
									temp_dict["start_in"] = get_timediff(interview_obj.interview_date_time)
								else:
									temp_dict['button_data'] = {}
									temp_dict['button_data']["type"] = interview_obj.interview_type
									temp_dict['button_data']["link"] = interview_obj.zoom_link
									temp_dict['interviewer'] = hiring_manager_hod.user.get_full_name()
							temp_dict['interviewer'] = logged_user_profile.user.get_full_name()
							# date_time = str(interview_obj.interview_date_time).split()
							temp_dict['date'] = interview_obj.interview_date_time.strftime("%m/%d/%Y")
							temp_dict['time'] = interview_obj.interview_date_time.strftime("%I:%M %p")
						except:
							pass
						i['flag_by_hiring_manager'].append(temp_dict)
				else:
					# Check Candidate Marks Code from here
					marks_dict = {}
					marks_dict['init_qualify_ques_1'] = 0
					marks_dict['init_qualify_ques_2'] = 0
					marks_dict['init_qualify_ques_3'] = 0
					marks_dict['init_qualify_ques_4'] = 0
					marks_dict['init_qualify_ques_5'] = 0
					marks_dict['init_qualify_ques_6'] = 0
					marks_dict['init_qualify_ques_7'] = 0
					marks_dict['init_qualify_ques_8'] = 0
					# Get all scheduled interviews for the candidate
					candidate_schedule_list = []
					for interview in Interview.objects.filter(candidate__candidate_id=i["candidate_id"], op_id__id=op_id).filter(disabled=False):
						try:
							temp_dict = {}
							interviewers_names = interview.htm.all().values_list("user__first_name", flat=True)
							temp_dict['interviewer_name'] = ", ".join(interviewers_names)
							temp_dict['time'] = interview.interview_date_time.strftime("%m/%d/%Y, %H:%M:%S")
							candidate_schedule_list.append(temp_dict)
						except:
							continue
					i['candidate_schedule'] = candidate_schedule_list
					HM_vote = {}
					members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
					if hiring_group_obj.hod_profile:
						members_list.append(hiring_group_obj.hod_profile.id)
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by__in=members_list)
					candidate_status_HM = CandidateStatus.objects.filter(candidate_id=i['candidate_id'], op_id=op_id)
					if candidate_status_HM:
						HM_vote["shortlist_status"] = candidate_status_HM[0].shortlist_status
						HM_vote["make_offer_status"] = candidate_status_HM[0].make_offer_status
						HM_vote["finall_selection_status"] = candidate_status_HM[0].finall_selection_status
						i["vote_by_HM"]=HM_vote
					htm_weightage_1_total = 0
					htm_weightage_2_total = 0
					htm_weightage_3_total = 0
					htm_weightage_4_total = 0
					htm_weightage_5_total = 0
					htm_weightage_6_total = 0
					htm_weightage_7_total = 0
					htm_weightage_8_total = 0
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						try:
							htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
							htm_weightage_1_total = htm_weightage_1_total + htm_weightage_obj.init_qualify_ques_1_weightage
							htm_weightage_2_total = htm_weightage_2_total + htm_weightage_obj.init_qualify_ques_2_weightage
							htm_weightage_3_total = htm_weightage_3_total + htm_weightage_obj.init_qualify_ques_3_weightage
							htm_weightage_4_total = htm_weightage_4_total + htm_weightage_obj.init_qualify_ques_4_weightage
							htm_weightage_5_total = htm_weightage_5_total + htm_weightage_obj.init_qualify_ques_5_weightage
							htm_weightage_6_total = htm_weightage_6_total + htm_weightage_obj.init_qualify_ques_6_weightage
							htm_weightage_7_total = htm_weightage_7_total + htm_weightage_obj.init_qualify_ques_7_weightage
							htm_weightage_8_total = htm_weightage_8_total + htm_weightage_obj.init_qualify_ques_8_weightage
						except Exception as e:
							htm_weightage_1_total = htm_weightage_1_total + 10
							htm_weightage_2_total = htm_weightage_2_total + 10
							htm_weightage_3_total = htm_weightage_3_total + 10
							htm_weightage_4_total = htm_weightage_4_total + 10
							htm_weightage_5_total = htm_weightage_5_total + 10
							htm_weightage_6_total = htm_weightage_6_total + 10
							htm_weightage_7_total = htm_weightage_7_total + 10
							htm_weightage_8_total = htm_weightage_8_total + 10
					if candidate_marks_obj:
						for c_obj in candidate_marks_obj:
							given_by = c_obj.marks_given_by
							try:
								htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
								htm_weightage_1 = htm_weightage_obj.init_qualify_ques_1_weightage
								htm_weightage_2 = htm_weightage_obj.init_qualify_ques_2_weightage
								htm_weightage_3 = htm_weightage_obj.init_qualify_ques_3_weightage
								htm_weightage_4 = htm_weightage_obj.init_qualify_ques_4_weightage
								htm_weightage_5 = htm_weightage_obj.init_qualify_ques_5_weightage
								htm_weightage_6 = htm_weightage_obj.init_qualify_ques_6_weightage
								htm_weightage_7 = htm_weightage_obj.init_qualify_ques_7_weightage
								htm_weightage_8 = htm_weightage_obj.init_qualify_ques_8_weightage
							except Exception as e:
								print(e)
								i['error-in-htm-wightage'] = str(e)
								htm_weightage_1 = 10
								htm_weightage_2 = 10
								htm_weightage_3 = 10
								htm_weightage_4 = 10
								htm_weightage_5 = 10
								htm_weightage_6 = 10
								htm_weightage_7 = 10
								htm_weightage_8 = 10
							marks_dict['init_qualify_ques_1'] = marks_dict['init_qualify_ques_1'] + c_obj.criteria_1_marks * htm_weightage_1
							marks_dict['init_qualify_ques_2'] = marks_dict['init_qualify_ques_2'] + c_obj.criteria_2_marks * htm_weightage_2
							marks_dict['init_qualify_ques_3'] = marks_dict['init_qualify_ques_3'] + c_obj.criteria_3_marks * htm_weightage_3
							marks_dict['init_qualify_ques_4'] = marks_dict['init_qualify_ques_4'] + c_obj.criteria_4_marks * htm_weightage_4
							marks_dict['init_qualify_ques_5'] = marks_dict['init_qualify_ques_5'] + c_obj.criteria_5_marks * htm_weightage_5
							marks_dict['init_qualify_ques_6'] = marks_dict['init_qualify_ques_6'] + c_obj.criteria_6_marks * htm_weightage_6
							marks_dict['init_qualify_ques_7'] = marks_dict['init_qualify_ques_7'] + c_obj.criteria_7_marks * htm_weightage_7
							marks_dict['init_qualify_ques_8'] = marks_dict['init_qualify_ques_8'] + c_obj.criteria_8_marks * htm_weightage_8
						marks_dict['init_qualify_ques_1'] = round(marks_dict['init_qualify_ques_1'] / htm_weightage_1_total, 1)
						marks_dict['init_qualify_ques_2'] = round(marks_dict['init_qualify_ques_2'] / htm_weightage_2_total, 1)
						marks_dict['init_qualify_ques_3'] = round(marks_dict['init_qualify_ques_3'] / htm_weightage_3_total, 1)
						marks_dict['init_qualify_ques_4'] = round(marks_dict['init_qualify_ques_4'] / htm_weightage_4_total, 1)
						marks_dict['init_qualify_ques_5'] = round(marks_dict['init_qualify_ques_5'] / htm_weightage_5_total, 1)
						marks_dict['init_qualify_ques_6'] = round(marks_dict['init_qualify_ques_6'] / htm_weightage_6_total, 1)
						marks_dict['init_qualify_ques_7'] = round(marks_dict['init_qualify_ques_7'] / htm_weightage_7_total, 1)
						marks_dict['init_qualify_ques_8'] = round(marks_dict['init_qualify_ques_8'] / htm_weightage_8_total, 1)
						i['marks'] = marks_dict
						count = 0
						avg_marks = 0
						if marks_dict['init_qualify_ques_1'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_1
							avg_marks = avg_marks + marks_dict['init_qualify_ques_1'] * open_position_obj.init_qualify_ques_weightage_1
						if marks_dict['init_qualify_ques_2'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_2
							avg_marks = avg_marks + marks_dict['init_qualify_ques_2'] * open_position_obj.init_qualify_ques_weightage_2
						if marks_dict['init_qualify_ques_3'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_3
							avg_marks = avg_marks + marks_dict['init_qualify_ques_3'] * open_position_obj.init_qualify_ques_weightage_3
						if marks_dict['init_qualify_ques_4'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_4
							avg_marks = avg_marks + marks_dict['init_qualify_ques_4'] * open_position_obj.init_qualify_ques_weightage_4
						if marks_dict['init_qualify_ques_5'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_5
							avg_marks = avg_marks + marks_dict['init_qualify_ques_5'] * open_position_obj.init_qualify_ques_weightage_5
						if marks_dict['init_qualify_ques_6'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_6
							avg_marks = avg_marks + marks_dict['init_qualify_ques_6'] * open_position_obj.init_qualify_ques_weightage_6
						if marks_dict['init_qualify_ques_7'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_7
							avg_marks = avg_marks + marks_dict['init_qualify_ques_7'] * open_position_obj.init_qualify_ques_weightage_7
						if marks_dict['init_qualify_ques_8'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_8
							avg_marks = avg_marks + marks_dict['init_qualify_ques_8'] * open_position_obj.init_qualify_ques_weightage_8
						i['total_hiring_members'] = hiring_group_obj.members_list.all().count() - 1
						i['marks_given_by'] = candidate_marks_obj.count()
						thumbs_up = 0
						thumbs_down = 0
						hold = 0
						print(count, avg_marks)
						if count:
							i['final_avg_marks'] = round(avg_marks / count, 1)
						else:
							i['final_avg_marks'] = 0.0
						i['he_flag'] = None
						i['flag_by_hiring_manager'] = []
						hm_members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
						try:
							withdrawed_members = json.loads(open_position_obj.withdrawed_members)
						except Exception as e:
							print(e)
							withdrawed_members = []
						hm_members_list = hm_members_list + withdrawed_members
						i['like_count'] = 0
						i['hold_count'] = 0
						i['pass_count'] = 0
						i['golden_glove_count'] = 0
						for j in candidate_marks_obj:
							if j.thumbs_up or j.golden_gloves:
								i['like_count'] = i['like_count'] + 1
							if j.thumbs_down:
								i['pass_count'] = i['pass_count'] + 1
							if j.hold:
								i['hold_count'] = i['hold_count'] + 1
							if j.golden_gloves:
								i['golden_glove_count'] = i['golden_glove_count'] + 1
						hiring_manager_hod = hiring_group_obj.hod_profile
						if hiring_manager_hod:
							hm_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=int(hiring_manager_hod.id))
							temp_dict = {}
							temp_dict['id'] = hiring_manager_hod.id
							if hm_marks_obj:
								hm_marks_obj = hm_marks_obj[0]
								if hm_marks_obj.thumbs_up:
									temp_dict['flag'] = 'Thumbs Up'
								if hm_marks_obj.thumbs_down:
									temp_dict['flag'] = 'Thumbs Down'
								if hm_marks_obj.hold:
									temp_dict['flag'] = 'Hold'
								if hm_marks_obj.golden_gloves:
									temp_dict['flag'] = 'Golden Glove'
							else:
								temp_dict['flag'] = 'Not Given'
								try:
									interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[hiring_manager_hod], candidate__candidate_id=i['candidate_id'])[0]
									# temp_dict['flag'] = 'Interview Scheduled'
									if not interview_obj.accepted:
										temp_dict['flag'] = "Interview NOT CONFIRMED"
									else:
										temp_dict['flag'] = "Interview Confirmed"
										if interview_obj.interview_date_time.date() == datetime.today().date():
											temp_dict['flag'] = "Interview Today"
											temp_dict['button_data'] = {}
											temp_dict['button_data']["type"] = interview_obj.interview_type
											temp_dict['button_data']["link"] = interview_obj.zoom_link
											temp_dict["start_in"] = get_timediff(interview_obj.interview_date_time)
										else:
											temp_dict['button_data'] = {}
											temp_dict['button_data']["type"] = interview_obj.interview_type
											temp_dict['button_data']["link"] = interview_obj.zoom_link
									temp_dict['interviewer'] = hiring_manager_hod.user.get_full_name()
									# date_time = str(interview_obj.interview_date_time).split()
									temp_dict['date'] = interview_obj.interview_date_time.strftime("%m/%d/%Y")
									temp_dict['time'] = interview_obj.interview_date_time.strftime("%I:%M %p")
								except:
									pass
							i['flag_by_hiring_manager'].append(temp_dict)
						else:
							i['flag_by_hiring_manager'].append({})

						hm_list = list(hiring_group_obj.members_list.all())
						if hiring_group_obj.hr_profile in hm_list:
							hm_list.remove(hiring_group_obj.hr_profile)
						if hiring_group_obj.hod_profile in hm_list:
							hm_list.remove(hiring_group_obj.hod_profile)
						for hm in hm_list:
							hm_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=hm.id)
							temp_dict = {}
							temp_dict['id'] = hm.id
							if hm_marks_obj:
								hm_marks_obj = hm_marks_obj[0]
								if True:
									temp_dict['flag'] = 'Interview Scheduled'
								if hm_marks_obj.thumbs_up:
									temp_dict['flag'] = 'Thumbs Up'
								if hm_marks_obj.thumbs_down:
									temp_dict['flag'] = 'Thumbs Down'
								if hm_marks_obj.hold:
									temp_dict['flag'] = 'Hold'
								if hm_marks_obj.golden_gloves:
									temp_dict['flag'] = 'Golden Glove'
							else:
								temp_dict['flag'] = 'Not Given'
								try:
									interview_obj = Interview.objects.filter(op_id__id=op_id, htm__id__in=[hm.id], candidate__candidate_id=i['candidate_id'])[0]
									# temp_dict['flag'] = 'Interview Scheduled'
									if not interview_obj.accepted:
										temp_dict['flag'] = "Interview NOT CONFIRMED"
									else:
										temp_dict['flag'] = "Interview Confirmed"
										if interview_obj.interview_date_time.date() == datetime.today().date():
											temp_dict['flag'] = "Interview Today"
											temp_dict['button_data'] = {}
											temp_dict['button_data']["type"] = interview_obj.interview_type
											temp_dict['button_data']["link"] = interview_obj.zoom_link
											temp_dict["start_in"] = get_timediff(interview_obj.interview_date_time)
										else:
											temp_dict['button_data'] = {}
											temp_dict['button_data']["type"] = interview_obj.interview_type
											temp_dict['button_data']["link"] = interview_obj.zoom_link
									temp_dict['interviewer'] = hiring_manager_hod.user.get_full_name()
									temp_hm_profile = hm
									temp_dict['interviewer'] = temp_hm_profile.user.get_full_name()
									temp_dict['date'] = interview_obj.interview_date_time.strftime("%m/%d/%Y")
									temp_dict['time'] = interview_obj.interview_date_time.strftime("%I:%M %p")
								except:
									pass
							i['flag_by_hiring_manager'].append(temp_dict)
						i['interviews_done'] = candidate_marks_obj.count()
					else:
						i['flag_by_hiring_manager'] = []
						hm_members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
						try:
							withdrawed_members = json.loads(open_position_obj.withdrawed_members)
						except Exception as e:
							print(e)
							withdrawed_members = []
						hm_members_list = hm_members_list + withdrawed_members
						i['marks'] = {}
						i['final_avg_marks'] = 0
						i['total_hiring_members'] = len(json.loads(hiring_group_obj.members)) - 1
						i['marks_given_by'] = 0
						i['flag'] = 'Not Given'
						i['like_count'] = 0
						i['hold_count'] = 0
						i['pass_count'] = 0
						i['golden_glove_count'] = 0
						hiring_manager_hod = hiring_group_obj.hod_profile
						if hiring_group_obj.hod_profile:
							hm_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=int(hiring_manager_hod.id))
							temp_dict = {}
							temp_dict['id'] = hiring_group_obj.hod_profile.id
							if hm_marks_obj:
								hm_marks_obj = hm_marks_obj[0]
								if True:
									temp_dict['flag'] = 'Interview Scheduled'
								if hm_marks_obj.thumbs_up:
									temp_dict['flag'] = 'Thumbs Up'
								if hm_marks_obj.thumbs_down:
									temp_dict['flag'] = 'Thumbs Down'
								if hm_marks_obj.hold:
									temp_dict['flag'] = 'Hold'
								if hm_marks_obj.golden_gloves:
									temp_dict['flag'] = 'Golden Glove'
							else:
								temp_dict['flag'] = 'Not Given'
								try:
									interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[hiring_manager_hod], candidate__candidate_id=i['candidate_id'])[0]
									# temp_dict['flag'] = 'Interview Scheduled'
									if not interview_obj.accepted:
										temp_dict['flag'] = "Interview NOT CONFIRMED"
									else:
										temp_dict['flag'] = "Interview Confirmed"
										if interview_obj.interview_date_time.date() == datetime.today().date():
											temp_dict['flag'] = "Interview Today"
											temp_dict['button_data'] = {}
											temp_dict['button_data']["type"] = interview_obj.interview_type
											temp_dict['button_data']["link"] = interview_obj.zoom_link
											temp_dict["start_in"] = get_timediff(interview_obj.interview_date_time)
										else:
											temp_dict['button_data'] = {}
											temp_dict['button_data']["type"] = interview_obj.interview_type
											temp_dict['button_data']["link"] = interview_obj.zoom_link
									temp_dict['interviewer'] = hiring_manager_hod.user.get_full_name()
									temp_dict['interviewer'] = hiring_manager_hod.user.get_full_name()
									temp_dict['date'] = interview_obj.interview_date_time.strftime("%m/%d/%Y")
									temp_dict['time'] = interview_obj.interview_date_time.strftime("%I:%M %p")
								except:
									pass
							i['flag_by_hiring_manager'].append(temp_dict)
						else:
							i['flag_by_hiring_manager'].append({})
						hm_list = list(hiring_group_obj.members_list.all())
						if hiring_group_obj.hr_profile in hm_list:
							hm_list.remove(hiring_group_obj.hr_profile)
						if hiring_group_obj.hod_profile in hm_list:
							hm_list.remove(hiring_group_obj.hod_profile)
						for hm in hm_list:
							hm_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=hm.id)
							temp_dict = {}
							temp_dict['id'] = hm.id
							if hm_marks_obj:
								hm_marks_obj = hm_marks_obj[0]
								if hm_marks_obj.thumbs_up:
									temp_dict['flag'] = 'Thumbs Up'
								if hm_marks_obj.thumbs_down:
									temp_dict['flag'] = 'Thumbs Down'
								if hm_marks_obj.hold:
									temp_dict['flag'] = 'Hold'
								if hm_marks_obj.golden_gloves:
									temp_dict['flag'] = 'Golden Glove'
							else:
								temp_dict['flag'] = 'Not Given'
								try:
									interview_obj = Interview.objects.filter(op_id__id=op_id, htm__id__in=[hm.id], candidate__candidate_id=i['candidate_id'])[0]
									# temp_dict['flag'] = 'Interview Scheduled'
									if not interview_obj.accepted:
										temp_dict['flag'] = "Interview NOT CONFIRMED"
									else:
										temp_dict['flag'] = "Interview Confirmed"
										if interview_obj.interview_date_time.date() == datetime.today().date():
											temp_dict['flag'] = "Interview Today"
											temp_dict['button_data'] = {}
											temp_dict['button_data']["type"] = interview_obj.interview_type
											temp_dict['button_data']["link"] = interview_obj.zoom_link
											temp_dict["start_in"] = get_timediff(interview_obj.interview_date_time)
										else:
											temp_dict['button_data'] = {}
											temp_dict['button_data']["type"] = interview_obj.interview_type
											temp_dict['button_data']["link"] = interview_obj.zoom_link
									temp_dict['interviewer'] = hiring_manager_hod.user.get_full_name()
									temp_hm_profile = hm
									temp_dict['interviewer'] = temp_hm_profile.user.get_full_name()
									temp_dict['date'] = interview_obj.interview_date_time.strftime("%m/%d/%Y")
									temp_dict['time'] = interview_obj.interview_date_time.strftime("%I:%M %p")
								except:
									pass
							i['flag_by_hiring_manager'].append(temp_dict)
						continue
			data = sorted(data, key=lambda i: i['final_avg_marks'])
			data.reverse()
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AllCandidateFeedback(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			open_position_obj = OpenPosition.objects.get(id=op_id)
			candidates_obj = []
			for cao in CandidateAssociateData.objects.filter(open_position=open_position_obj):
				if cao.candidate not in candidates_obj:
					candidates_obj.append(cao.candidate)
			candidates_serializer = CandidateSerializer(candidates_obj, many=True)
			data = candidates_serializer.data
			try:
				hiring_group_obj = HiringGroup.objects.get(group_id=open_position_obj.hiring_group)
			except:
				for i in data:
					i['final_avg_marks'] = 0
					i['total_hiring_members'] = 1
					i['marks_given_by'] = 0
					i['flag'] = 'Not Given'
					i['op_id'] = op_id
					i['client_id'] = open_position_obj.client
				return Response(data, status=status.HTTP_200_OK)
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			for i in data:
				# Additin Profile Picture
				if 'profile_pic_url' in i['linkedin_data'] and i['linkedin_data']['profile_pic_url'] and i['linkedin_data']['profile_pic_url'] != "null":
					i['profile_photo'] = i['linkedin_data']['profile_pic_url']
				else:
					i['profile_photo'] = i['profile_photo']
				# Getting if hired or not
				try:
					hire_obj = Hired.objects.get(candidate_id=i['candidate_id'], op_id=op_id)
					i['hired'] = True
				except:
					i['hired'] = False
				# Getting Offered or not
				try:
					hire_obj = Offered.objects.get(candidate_id=i['candidate_id'], op_id=op_id)
					i['offered'] = True
				except:
					i['offered'] = False
				# Getting withdrawed and requested data
				i['op_id'] = op_id
				if i['op_id'] in json.loads(i['withdrawed_op_ids']):
					i['withdrawed'] = True
				else:
					i['withdrawed'] = False
				if i['op_id'] in i["requested_op_ids"]:
					i["requested"] = True
				else:
					i["requested"] = False
				i['client_id'] = open_position_obj.client
				
				if "is_htm" in logged_user_profile.roles and hiring_group_obj.hod_profile != request.user.profile and hiring_group_obj.hr_profile != request.user.profile:
					# Sending data as a HTM perspective
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=logged_user_profile.id)
					given_by = logged_user_profile.id
					# Get weighage of the HTM if not found then assign 10 by default - Not being used
					try:
						htm_weightage_obj = HTMWeightage.objects.filter(op_id=op_id, htm_id=given_by)
						htm_weightage_1 = htm_weightage_obj.init_qualify_ques_1_weightage
						htm_weightage_2 = htm_weightage_obj.init_qualify_ques_2_weightage
						htm_weightage_3 = htm_weightage_obj.init_qualify_ques_3_weightage
						htm_weightage_4 = htm_weightage_obj.init_qualify_ques_4_weightage
						htm_weightage_5 = htm_weightage_obj.init_qualify_ques_5_weightage
						htm_weightage_6 = htm_weightage_obj.init_qualify_ques_6_weightage
						htm_weightage_7 = htm_weightage_obj.init_qualify_ques_7_weightage
						htm_weightage_8 = htm_weightage_obj.init_qualify_ques_8_weightage
					except:
						htm_weightage_1 = 10
						htm_weightage_2 = 10
						htm_weightage_3 = 10
						htm_weightage_4 = 10
						htm_weightage_5 = 10
						htm_weightage_6 = 10
						htm_weightage_7 = 10
						htm_weightage_8 = 10
					if candidate_marks_obj:
						avg_marks = 0
						count = 0
						# Algorith to calculate marks based on HTM Weightage and Skills Weightage
						if candidate_marks_obj[0].criteria_1_marks not in [None]: 
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_1_marks * open_position_obj.init_qualify_ques_weightage_1
						if candidate_marks_obj[0].criteria_2_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_2_marks* open_position_obj.init_qualify_ques_weightage_2
						if candidate_marks_obj[0].criteria_3_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_3_marks* open_position_obj.init_qualify_ques_weightage_3
						if candidate_marks_obj[0].criteria_4_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_4_marks* open_position_obj.init_qualify_ques_weightage_4
						if candidate_marks_obj[0].criteria_5_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_5_marks * open_position_obj.init_qualify_ques_weightage_5
						if candidate_marks_obj[0].criteria_6_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_6_marks * open_position_obj.init_qualify_ques_weightage_6
						if candidate_marks_obj[0].criteria_7_marks not in [ None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_7_marks * open_position_obj.init_qualify_ques_weightage_7
						if candidate_marks_obj[0].criteria_8_marks not in [None]:
							count = count + 1
							avg_marks = avg_marks + candidate_marks_obj[0].criteria_8_marks * open_position_obj.init_qualify_ques_weightage_8
						i['avg_marks'] = round(avg_marks / count, 1)
						i['total_hiring_members'] = hiring_group_obj.members_list.all().count() - 1
						all_marks_candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id)
						i['final_avg_marks'] = i['avg_marks']  # (all_marks_candidate_marks_obj.aggregate(Avg('criteria_1_marks'))['criteria_1_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_2_marks'))['criteria_2_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_3_marks'))['criteria_3_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_4_marks'))['criteria_4_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_5_marks'))['criteria_5_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_6_marks'))['criteria_6_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_7_marks'))['criteria_7_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_8_marks'))['criteria_8_marks__avg']) / 8
						i['marks_given_by'] = all_marks_candidate_marks_obj.count()
						if candidate_marks_obj[0].thumbs_up:
							i['he_flag'] = 'Thumbs Up'
							i['flag'] = 'Thumbs Up'
						if candidate_marks_obj[0].thumbs_down:
							i['he_flag'] = 'Thumbs Down'
							i['flag'] = 'Thumbs Down'
						if candidate_marks_obj[0].hold:
							i['he_flag'] = 'Hold'
							i['flag'] = 'Hold'
						if candidate_marks_obj[0].golden_gloves:
							i['he_flag'] = 'Golden Glove'
							i['flag'] = 'Golden Glove'
						i['flag_by_hiring_manager'] = []
						temp_dict = {}
						temp_dict['id'] = int(logged_user_profile.id)
						candidate_marks_obj = candidate_marks_obj[0]
						if candidate_marks_obj.thumbs_up:
							temp_dict['flag'] = 'Thumbs Up'
						if candidate_marks_obj.thumbs_down:
							temp_dict['flag'] = 'Thumbs Down'
						if candidate_marks_obj.hold:
							temp_dict['flag'] = 'Hold'
						if candidate_marks_obj.golden_gloves:
							temp_dict['flag'] = 'Golden Glove'
						# get other htm specific data
						try:
							interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[logged_user_profile], candidate__candidate_id=i['candidate_id'])[0]
							# call the function and pass interview_obj and logged_user_profile
							extra_data = get_htm_specific_data(interview_obj, logged_user_profile)
							temp_dict.update(extra_data)
						except:
							pass
						temp_dict["marks"] = i['final_avg_marks']
						i['flag_by_hiring_manager'].append(temp_dict)
					else:
						i['marks'] = {}
						i['final_avg_marks'] = 0
						i['total_hiring_members'] = hiring_group_obj.members_list.all().count() - 1
						i['marks_given_by'] = 0
						i['flag'] = 'Not Given'
						i['flag_by_hiring_manager'] = []
						temp_dict = {}
						temp_dict['id'] = int(logged_user_profile.id)
						try:
							interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[logged_user_profile], candidate__candidate_id=i['candidate_id'])[0]
							extra_data = get_htm_specific_data(interview_obj, logged_user_profile)
							temp_dict.update(extra_data)
						except:
							pass
						temp_dict["marks"] = i['final_avg_marks']
						i['flag_by_hiring_manager'].append(temp_dict)
				else:
					# Sending data as HM, HR, SM, CA or SA
					# Check Candidate Marks Code from here
					marks_dict = {}
					marks_dict['init_qualify_ques_1'] = 0
					marks_dict['init_qualify_ques_2'] = 0
					marks_dict['init_qualify_ques_3'] = 0
					marks_dict['init_qualify_ques_4'] = 0
					marks_dict['init_qualify_ques_5'] = 0
					marks_dict['init_qualify_ques_6'] = 0
					marks_dict['init_qualify_ques_7'] = 0
					marks_dict['init_qualify_ques_8'] = 0
					# Get all scheduled interviews for the candidate
					candidate_schedule_list = []
					for interview in Interview.objects.filter(candidate__candidate_id=i["candidate_id"], op_id__id=op_id).filter(disabled=False):
						try:
							temp_dict = {}
							interviewers_names = interview.htm.all().values_list("user__first_name", flat=True)
							temp_dict['interviewer_name'] = ", ".join(interviewers_names)
							temp_dict['time'] = interview.interview_date_time.strftime("%m/%d/%Y, %H:%M:%S")
							candidate_schedule_list.append(temp_dict)
						except:
							continue
					i['candidate_schedule'] = candidate_schedule_list
					HM_vote = {}
					members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
					if hiring_group_obj.hod_profile:
						members_list.append(hiring_group_obj.hod_profile.id)
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by__in=members_list)
					candidate_status_HM = CandidateStatus.objects.filter(candidate_id=i['candidate_id'], op_id=op_id)
					if candidate_status_HM:
						HM_vote["shortlist_status"] = candidate_status_HM[0].shortlist_status
						HM_vote["make_offer_status"] = candidate_status_HM[0].make_offer_status
						HM_vote["finall_selection_status"] = candidate_status_HM[0].finall_selection_status
						i["vote_by_HM"]=HM_vote
					htm_weightage_1_total = 0
					htm_weightage_2_total = 0
					htm_weightage_3_total = 0
					htm_weightage_4_total = 0
					htm_weightage_5_total = 0
					htm_weightage_6_total = 0
					htm_weightage_7_total = 0
					htm_weightage_8_total = 0
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						try:
							htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
							htm_weightage_1_total = htm_weightage_1_total + htm_weightage_obj.init_qualify_ques_1_weightage
							htm_weightage_2_total = htm_weightage_2_total + htm_weightage_obj.init_qualify_ques_2_weightage
							htm_weightage_3_total = htm_weightage_3_total + htm_weightage_obj.init_qualify_ques_3_weightage
							htm_weightage_4_total = htm_weightage_4_total + htm_weightage_obj.init_qualify_ques_4_weightage
							htm_weightage_5_total = htm_weightage_5_total + htm_weightage_obj.init_qualify_ques_5_weightage
							htm_weightage_6_total = htm_weightage_6_total + htm_weightage_obj.init_qualify_ques_6_weightage
							htm_weightage_7_total = htm_weightage_7_total + htm_weightage_obj.init_qualify_ques_7_weightage
							htm_weightage_8_total = htm_weightage_8_total + htm_weightage_obj.init_qualify_ques_8_weightage
						except Exception as e:
							htm_weightage_1_total = htm_weightage_1_total + 10
							htm_weightage_2_total = htm_weightage_2_total + 10
							htm_weightage_3_total = htm_weightage_3_total + 10
							htm_weightage_4_total = htm_weightage_4_total + 10
							htm_weightage_5_total = htm_weightage_5_total + 10
							htm_weightage_6_total = htm_weightage_6_total + 10
							htm_weightage_7_total = htm_weightage_7_total + 10
							htm_weightage_8_total = htm_weightage_8_total + 10
					if candidate_marks_obj:
						for c_obj in candidate_marks_obj:
							given_by = c_obj.marks_given_by
							try:
								htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
								htm_weightage_1 = htm_weightage_obj.init_qualify_ques_1_weightage
								htm_weightage_2 = htm_weightage_obj.init_qualify_ques_2_weightage
								htm_weightage_3 = htm_weightage_obj.init_qualify_ques_3_weightage
								htm_weightage_4 = htm_weightage_obj.init_qualify_ques_4_weightage
								htm_weightage_5 = htm_weightage_obj.init_qualify_ques_5_weightage
								htm_weightage_6 = htm_weightage_obj.init_qualify_ques_6_weightage
								htm_weightage_7 = htm_weightage_obj.init_qualify_ques_7_weightage
								htm_weightage_8 = htm_weightage_obj.init_qualify_ques_8_weightage
							except Exception as e:
								print(e)
								i['error-in-htm-wightage'] = str(e)
								htm_weightage_1 = 10
								htm_weightage_2 = 10
								htm_weightage_3 = 10
								htm_weightage_4 = 10
								htm_weightage_5 = 10
								htm_weightage_6 = 10
								htm_weightage_7 = 10
								htm_weightage_8 = 10
							marks_dict['init_qualify_ques_1'] = marks_dict['init_qualify_ques_1'] + c_obj.criteria_1_marks * htm_weightage_1
							marks_dict['init_qualify_ques_2'] = marks_dict['init_qualify_ques_2'] + c_obj.criteria_2_marks * htm_weightage_2
							marks_dict['init_qualify_ques_3'] = marks_dict['init_qualify_ques_3'] + c_obj.criteria_3_marks * htm_weightage_3
							marks_dict['init_qualify_ques_4'] = marks_dict['init_qualify_ques_4'] + c_obj.criteria_4_marks * htm_weightage_4
							marks_dict['init_qualify_ques_5'] = marks_dict['init_qualify_ques_5'] + c_obj.criteria_5_marks * htm_weightage_5
							marks_dict['init_qualify_ques_6'] = marks_dict['init_qualify_ques_6'] + c_obj.criteria_6_marks * htm_weightage_6
							marks_dict['init_qualify_ques_7'] = marks_dict['init_qualify_ques_7'] + c_obj.criteria_7_marks * htm_weightage_7
							marks_dict['init_qualify_ques_8'] = marks_dict['init_qualify_ques_8'] + c_obj.criteria_8_marks * htm_weightage_8
						marks_dict['init_qualify_ques_1'] = round(marks_dict['init_qualify_ques_1'] / htm_weightage_1_total, 1)
						marks_dict['init_qualify_ques_2'] = round(marks_dict['init_qualify_ques_2'] / htm_weightage_2_total, 1)
						marks_dict['init_qualify_ques_3'] = round(marks_dict['init_qualify_ques_3'] / htm_weightage_3_total, 1)
						marks_dict['init_qualify_ques_4'] = round(marks_dict['init_qualify_ques_4'] / htm_weightage_4_total, 1)
						marks_dict['init_qualify_ques_5'] = round(marks_dict['init_qualify_ques_5'] / htm_weightage_5_total, 1)
						marks_dict['init_qualify_ques_6'] = round(marks_dict['init_qualify_ques_6'] / htm_weightage_6_total, 1)
						marks_dict['init_qualify_ques_7'] = round(marks_dict['init_qualify_ques_7'] / htm_weightage_7_total, 1)
						marks_dict['init_qualify_ques_8'] = round(marks_dict['init_qualify_ques_8'] / htm_weightage_8_total, 1)
						i['marks'] = marks_dict
						count = 0
						avg_marks = 0
						if marks_dict['init_qualify_ques_1'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_1
							avg_marks = avg_marks + marks_dict['init_qualify_ques_1'] * open_position_obj.init_qualify_ques_weightage_1
						if marks_dict['init_qualify_ques_2'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_2
							avg_marks = avg_marks + marks_dict['init_qualify_ques_2'] * open_position_obj.init_qualify_ques_weightage_2
						if marks_dict['init_qualify_ques_3'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_3
							avg_marks = avg_marks + marks_dict['init_qualify_ques_3'] * open_position_obj.init_qualify_ques_weightage_3
						if marks_dict['init_qualify_ques_4'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_4
							avg_marks = avg_marks + marks_dict['init_qualify_ques_4'] * open_position_obj.init_qualify_ques_weightage_4
						if marks_dict['init_qualify_ques_5'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_5
							avg_marks = avg_marks + marks_dict['init_qualify_ques_5'] * open_position_obj.init_qualify_ques_weightage_5
						if marks_dict['init_qualify_ques_6'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_6
							avg_marks = avg_marks + marks_dict['init_qualify_ques_6'] * open_position_obj.init_qualify_ques_weightage_6
						if marks_dict['init_qualify_ques_7'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_7
							avg_marks = avg_marks + marks_dict['init_qualify_ques_7'] * open_position_obj.init_qualify_ques_weightage_7
						if marks_dict['init_qualify_ques_8'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_8
							avg_marks = avg_marks + marks_dict['init_qualify_ques_8'] * open_position_obj.init_qualify_ques_weightage_8
						i['total_hiring_members'] = hiring_group_obj.members_list.all().count() - 1
						i['marks_given_by'] = candidate_marks_obj.count()
						thumbs_up = 0
						thumbs_down = 0
						hold = 0
						print(count, avg_marks)
						if count:
							i['final_avg_marks'] = round(avg_marks / count, 1)
						else:
							i['final_avg_marks'] = 0.0
						i['he_flag'] = None
						i['flag_by_hiring_manager'] = []
						hm_members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
						try:
							withdrawed_members = json.loads(open_position_obj.withdrawed_members)
						except Exception as e:
							withdrawed_members = []
						hm_members_list = hm_members_list + withdrawed_members
						i['like_count'] = 0
						i['hold_count'] = 0
						i['pass_count'] = 0
						i['golden_glove_count'] = 0
						if hiring_group_obj.hod_profile:
							flag_data = get_htm_flag_data(hiring_group_obj.hod_profile, op_id, i["candidate_id"])
							i['flag_by_hiring_manager'].append(flag_data)
						else:
							i['flag_by_hiring_manager'].append({})

						hm_list = list(hiring_group_obj.members_list.all())
						if hiring_group_obj.hr_profile in hm_list:
							hm_list.remove(hiring_group_obj.hr_profile)
						if hiring_group_obj.hod_profile in hm_list:
							hm_list.remove(hiring_group_obj.hod_profile)
						for hm in hm_list:
							flag_data = get_htm_flag_data(hm, op_id, i["candidate_id"])
							i['flag_by_hiring_manager'].append(flag_data)
						i['interviews_done'] = candidate_marks_obj.count()
					else:
						i['flag_by_hiring_manager'] = []
						hm_members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
						try:
							withdrawed_members = json.loads(open_position_obj.withdrawed_members)
						except Exception as e:
							print(e)
							withdrawed_members = []
						hm_members_list = hm_members_list + withdrawed_members
						i['marks'] = {}
						i['final_avg_marks'] = 0
						i['total_hiring_members'] = len(json.loads(hiring_group_obj.members)) - 1
						i['marks_given_by'] = 0
						i['flag'] = 'Not Given'
						i['like_count'] = 0
						i['hold_count'] = 0
						i['pass_count'] = 0
						i['golden_glove_count'] = 0
						hiring_manager_hod = hiring_group_obj.hod_profile
						if hiring_group_obj.hod_profile:
							flag_data = get_htm_flag_data(hiring_group_obj.hod_profile, op_id, i["candidate_id"])
							i['flag_by_hiring_manager'].append(flag_data)
						else:
							i['flag_by_hiring_manager'].append({})
						hm_list = list(hiring_group_obj.members_list.all())
						if hiring_group_obj.hr_profile in hm_list:
							hm_list.remove(hiring_group_obj.hr_profile)
						if hiring_group_obj.hod_profile in hm_list:
							hm_list.remove(hiring_group_obj.hod_profile)
						for hm in hm_list:
							flag_data = get_htm_flag_data(hm, op_id, i["candidate_id"])
							i['flag_by_hiring_manager'].append(flag_data)
						continue
			data = sorted(data, key=lambda i: i['final_avg_marks'])
			data.reverse()
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetAllUsernamesView(APIView):
	def get(self, request):
		try:
			username_list = []
			for i in User.objects.all():
				username_list.append(i.username)
			return Response(username_list, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetAccountManagerName(APIView):
	def get(self, request):
		try:
			client_id = int(request.query_params.get('client_id'))
			for i in Profile.objects.filter(roles__contains="is_ae"):
				client_list = json.loads(i.client)
				if client_id in client_list:
					try:
						user_obj = User.objects.get(username=i.user.username)
					except:
						response = {}
						response['account_manager'] = 'Not Assigned'
						return Response(response, status=status.HTTP_200_OK)
					response = {}
					response['account_manager'] = user_obj.first_name + ' ' + user_obj.last_name
					user_profile = Profile.objects.get(user=user_obj)
					response['phone_number'] = user_profile.phone_number
					response['email'] = user_profile.email
					response['skype_id'] = user_profile.skype_id
					return Response(response, status=status.HTTP_200_OK)
			response = {}
			response['account_manager'] = 'No Such Client or Not Assigned'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Departments APIs not used anymore.
# class DepartmentView(APIView):
# 	permission_classes = (permissions.IsAuthenticated,)

# 	def post(self, request):
# 		try:
# 			username = request.data.get("username")
# 			password = request.data.get("password")
# 			first_name = request.data.get("first_name")
# 			last_name = request.data.get("last_name")
# 			user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)
# 			phone_number = request.data.get("phone_number")
# 			skype_id = request.data.get("skype_id")
# 			email = request.data.get("email")
# 			client = request.data.get("client")
# 			data = {}
# 			data['client'] = request.data.get('client')
# 			data['name'] = request.data.get('name')
# 			data['hod'] = user.id
# 			department_serializer = DepartmentSerializer(data=data)
# 			if department_serializer.is_valid():
# 				department_serializer.save()
# 			else:
# 				return Response({'error': department_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
# 			try:
# 				Profile.objects.create(user=user, phone_number=phone_number, skype_id=skype_id, email=email, is_hod=True, client=client, hod_of=department_serializer.data['id'])
# 			except Exception as e:
# 				user.delete()
# 				department_obj = Department.objects.filter(id=department_serializer.data['id']).delete()
# 				return Response({'msg': str(e)}, status=status.HTTP_409_CONFLICT)
# 			return Response(department_serializer.data, status=status.HTTP_200_OK)
# 		except Exception as e:
# 			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# 	def get(self, request):
# 		try:
# 			user = request.user
# 			if user.profile.is_ca:
# 				department_objs = Department.objects.filter(client=int(user.profile.client))
# 			elif user.profile.is_he:
# 				department_objs = Department.objects.filter(client=int(user.profile.client))
# 			elif user.profile.is_hod:
# 				department_objs = Department.objects.filter(client=int(user.profile.client))
# 			elif user.profile.is_ch:
# 				department_objs = Department.objects.filter(client=int(user.profile.client))
# 			elif user.profile.is_ae:
# 				department_objs = Department.objects.filter(client__in=json.loads(user.profile.client))
# 			else:
# 				department_objs = Department.objects.all()
# 			# data = []
# 			data = {}
# 			for i in department_objs:
# 				try:
# 					client_obj = Client.objects.get(id=i.client)
# 					temp_dict = {}
# 					temp_dict['name'] = i.name
# 					temp_dict['id'] = i.id
# 					temp_dict['client'] = client_obj.company_name
# 					temp_dict['client_id'] = client_obj.id
# 					profile_obj = Profile.objects.get(is_hod=True, hod_of=i.id)
# 					user_obj = User.objects.get(username=profile_obj.user)
# 					temp_dict['hiring_manager_name'] = user_obj.first_name + ' ' + user_obj.last_name
# 					# temp_dict['last_name'] = user_obj.last_name
# 					temp_dict['phone_number'] = profile_obj.phone_number
# 					temp_dict['skype_id'] = profile_obj.skype_id
# 					temp_dict['email'] = profile_obj.email
# 					temp_dict['username'] = user_obj.username
# 					# data.append(temp_dict)
# 					try:
# 						data[temp_dict['client']].append(temp_dict)
# 					except Exception as e:
# 						print(e)
# 						data[temp_dict['client']] = []
# 						data[temp_dict['client']].append(temp_dict)
# 				except Exception as e:
# 					print(e)
# 			return Response(data, status=status.HTTP_200_OK)
# 		except Exception as e:
# 			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# 	def put(self, request):
# 		try:
# 			department_id = request.data.get('id')
# 			department_obj = Department.objects.get(id=department_id)
# 			department_serializer = DepartmentSerializer(department_obj, data=request.data, partial=True)
# 			if department_serializer.is_valid():
# 				department_serializer.save()
# 			else:
# 				return Response({'error': department_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
# 			profile_obj = Profile.objects.get(is_hod=True, hod_of=department_obj.id)
# 			user_obj = User.objects.get(username=profile_obj.user)
# 			user_obj.first_name = request.data.get('first_name')
# 			user_obj.last_name = request.data.get('last_name')
# 			profile_obj.email = request.data.get('email')
# 			profile_obj.skype_id = request.data.get('skype_id')
# 			profile_obj.phone_number = request.data.get('phone_number')
# 			profile_obj.save()
# 			if request.data.get('password') == '':
# 				pass
# 			else:
# 				user_obj.set_password(request.data.get("password"))
# 				user_obj.save()

# 			return Response(department_serializer.data, status=status.HTTP_200_OK)
# 		except Exception as e:
# 			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
	
# 	def delete(self, request):
# 		try:
# 			Department.objects.filter(id=int(request.query_params.get('department_id'))).delete()
# 			response = {}
# 			response["msg"] = "deleted"
# 			return Response(response, status=status.HTTP_200_OK)
# 		except Exception as e:
# 			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# class GetDepartmentsByClientId(APIView):
# 	permission_classes = (permissions.IsAuthenticated,)

# 	def get(self, request, client_id):
# 		try:
# 			department_objs = Department.objects.filter(client=client_id)
# 			data = []
# 			for i in department_objs:
# 				client_obj = Client.objects.get(id=i.client)
# 				temp_dict = {}
# 				temp_dict['name'] = i.name
# 				temp_dict['id'] = i.id
# 				temp_dict['client'] = client_obj.company_name
# 				temp_dict['client_id'] = client_obj.id
# 				data.append(temp_dict)
# 			return Response(data, status=status.HTTP_200_OK)
# 		except Exception as e:
# 			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# class GetDepartmentsByDepartmentId(APIView):
# 	permission_classes = (permissions.IsAuthenticated,)

# 	def get(self, request, department_id):
# 		try:
# 			department_obj = Department.objects.get(id=department_id)
# 			data = []
# 			client_obj = Client.objects.get(id=department_obj.client)
# 			temp_dict = {}
# 			temp_dict['client'] = client_obj.company_name
# 			temp_dict['client_id'] = client_obj.id
# 			temp_dict['name'] = department_obj.name
# 			temp_dict['id'] = department_obj.id
# 			profile_obj = Profile.objects.get(is_hod=True, hod_of=department_obj.id)
# 			user_obj = User.objects.get(username=profile_obj.user)
# 			temp_dict['first_name'] = user_obj.first_name
# 			temp_dict['last_name'] = user_obj.last_name
# 			temp_dict['phone_number'] = profile_obj.phone_number
# 			temp_dict['skype_id'] = profile_obj.skype_id
# 			temp_dict['email'] = profile_obj.email
# 			temp_dict['username'] = user_obj.username
# 			data.append(temp_dict)
# 			return Response(data, status=status.HTTP_200_OK)
# 		except Exception as e:
# 			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetManagerAndMember(APIView):
	# permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, client):
		try:
			response = {}
			hiring_manager_objs = Profile.objects.filter(roles__contains="is_htm", client=client)
			members_list = []
			if hiring_manager_objs:
				for i in hiring_manager_objs:
					temp_dict = {}
					temp_dict["id"] = i.id
					temp_dict["name"] = i.user.first_name + ' ' + i.user.last_name
					temp_dict["username"] = i.user.username
					temp_dict["mobile_no"] = i.phone_number
					temp_dict["email"] = i.email
					temp_dict['client'] = int(i.client)
					members_list.append(temp_dict)
				response['hiring_members'] = members_list
			else:
				response['msg'] = 'No Members found please add some'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChangeCandidateStatus(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, candidate_id, op_id):
		try:
			openposition_obj = OpenPosition.objects.get(id=op_id)
			candidate_status_obj = CandidateStatus.objects.filter(candidate_id=candidate_id, op_id=op_id)
			if candidate_status_obj:
				candidate_status_serializer = CandidateStatusSerializer(candidate_status_obj[0], data=request.data, partial=True)
				if candidate_status_serializer.is_valid():
					candidate_status_serializer.save()
					response = {}
					response['msg'] = 'updated'
					return Response(response, status=status.HTTP_200_OK)
				else:
					return Response({'msg': 'error', 'error': candidate_status_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
			else:
				data = {}
				data['candidate_id'] = candidate_id
				data['op_id'] = op_id
				data['shortlist_status'] = request.data.get('shortlist_status')
				data['make_offer_status'] = request.data.get('make_offer_status')
				data['finall_selection_status'] = request.data.get('finall_selection_status')
				candidate_status_serializer = CandidateStatusSerializer(data=data)
				if candidate_status_serializer.is_valid():
					candidate_status_serializer.save()
					response = {}
					response['msg'] = 'added'
					return Response(response, status=status.HTTP_200_OK)
				else:
					return Response({'msg': 'error', 'error': candidate_status_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request, candidate_id, op_id):
		try:
			response = {
				'data': {}
			}
			candidate_status_obj = CandidateStatus.objects.filter(candidate_id=candidate_id, op_id=op_id)
			if candidate_status_obj:
				candidate_status_serializer = CandidateStatusSerializer(candidate_status_obj[0])
				response['data'] = candidate_status_serializer.data
			else:
				response['data']['finall_selection_status'] = False
				response['data']['make_offer_status'] = False
				response['data']['shortlist_status'] = False
				response['data']['op_id'] = op_id
				response['data']['candidate_id'] = candidate_id
			candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=candidate_id, op_id=op_id, marks_given_by=request.user.profile.id)		
			if candidate_marks_obj:
				response['data']['marks_given'] = True
			else:
				response['data']['marks_given'] = False
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CandidateWithTimeLine(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, op_id):
		try:
			source_candidate_list = []
			short_list_selection = []
			final_selection_list = []
			make_offer_list = []
			source_candidate_objs = Candidate.objects.filter(op_id=op_id)
			source_candidate_serializer = CandidateSerializer(source_candidate_objs, many=True)
			source_candidate_list = source_candidate_serializer.data
			short_list_selection_objs = Candidate.objects.filter(op_id=op_id, shortlist_status=True)
			short_list_selection_serializer = CandidateSerializer(short_list_selection_objs, many=True)
			short_list_selection = short_list_selection_serializer.data
			final_selection_list_objs = Candidate.objects.filter(op_id=op_id, finall_selection_status=True)
			final_selection_list_serializer = CandidateSerializer(final_selection_list_objs, many=True)
			final_selection_list = final_selection_list_serializer.data
			make_offer_objs = Candidate.objects.filter(op_id=op_id, make_offer_status=True)
			make_offer_serializer = CandidateSerializer(make_offer_objs, many=True)
			make_offer_list = make_offer_serializer.data
			response = {}
			response['source_candidate_list'] = source_candidate_list
			response['short_list_selection'] = short_list_selection
			response['final_selection_list'] = final_selection_list
			response['make_offer_list'] = make_offer_list
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetTeamOfOP(APIView):
	permission_classed = [IsAuthenticated]

	def get(self, request, op_id):
		responsep = {}
		try:
			response = {}
			open_position = OpenPosition.objects.get(id=op_id)
			if open_position.hiring_group:
				response['available'] = True
				hiring_group_obj = HiringGroup.objects.get(group_id=open_position.hiring_group)
				responsep['group_name'] = hiring_group_obj.name
			else:
				response['available'] = False
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetClientAndOPName(APIView):
	permission_classes= [IsAuthenticated]

	def get(self, request, op_id):
		try:
			response = {}
			open_position = OpenPosition.objects.get(id=op_id)
			client_obj = Client.objects.get(id=open_position.client)
			response['client_id'] = client_obj.id
			response['client_name'] = client_obj.company_name
			response['op_id'] = op_id
			response['open_position_name'] = open_position.position_title
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetThumbsByHiringMember(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, candidate_id, hiring_member_id, op_id):
		try:
			response = {}
			marks_dict = {}
			try:
				candidate_marks_obj = CandidateMarks.objects.get(candidate_id=candidate_id, marks_given_by=hiring_member_id, op_id=op_id)
				open_position_obj = OpenPosition.objects.get(id=op_id)
			except Exception as e:
				response['error'] = str(e)
				response['marks_given'] = False
				return Response(response, status=status.HTTP_200_OK)
			marks_dict['init_qualify_ques_1'] = candidate_marks_obj.criteria_1_marks
			marks_dict['init_qualify_ques_2'] = candidate_marks_obj.criteria_2_marks
			marks_dict['init_qualify_ques_3'] = candidate_marks_obj.criteria_3_marks
			marks_dict['init_qualify_ques_4'] = candidate_marks_obj.criteria_4_marks
			marks_dict['init_qualify_ques_5'] = candidate_marks_obj.criteria_5_marks
			marks_dict['init_qualify_ques_6'] = candidate_marks_obj.criteria_6_marks
			marks_dict['init_qualify_ques_7'] = candidate_marks_obj.criteria_7_marks
			marks_dict['init_qualify_ques_8'] = candidate_marks_obj.criteria_8_marks
			

			marks_dict['init_qualify_ques_1_ques'] = open_position_obj.init_qualify_ques_suggestion_1
			marks_dict['init_qualify_ques_2_ques'] = open_position_obj.init_qualify_ques_suggestion_2
			marks_dict['init_qualify_ques_3_ques'] = open_position_obj.init_qualify_ques_suggestion_3
			marks_dict['init_qualify_ques_4_ques'] = open_position_obj.init_qualify_ques_suggestion_4
			marks_dict['init_qualify_ques_5_ques'] = open_position_obj.init_qualify_ques_suggestion_5
			marks_dict['init_qualify_ques_6_ques'] = open_position_obj.init_qualify_ques_suggestion_6
			marks_dict['init_qualify_ques_7_ques'] = open_position_obj.init_qualify_ques_suggestion_7
			marks_dict['init_qualify_ques_8_ques'] = open_position_obj.init_qualify_ques_suggestion_8

			
			marks_dict['init_qualify_ques_1_answer'] = candidate_marks_obj.suggestion_1
			marks_dict['init_qualify_ques_2_answer'] = candidate_marks_obj.suggestion_2
			marks_dict['init_qualify_ques_3_answer'] = candidate_marks_obj.suggestion_3
			marks_dict['init_qualify_ques_4_answer'] = candidate_marks_obj.suggestion_4
			marks_dict['init_qualify_ques_5_answer'] = candidate_marks_obj.suggestion_5
			marks_dict['init_qualify_ques_6_answer'] = candidate_marks_obj.suggestion_6
			marks_dict['init_qualify_ques_7_answer'] = candidate_marks_obj.suggestion_7
			marks_dict['init_qualify_ques_8_answer'] = candidate_marks_obj.suggestion_8
			response['marks'] = marks_dict
			response['final_avg_marks'] = (marks_dict['init_qualify_ques_1'] + marks_dict['init_qualify_ques_2'] + marks_dict['init_qualify_ques_3'] + marks_dict['init_qualify_ques_4'] + marks_dict['init_qualify_ques_5'] + marks_dict['init_qualify_ques_6'] + marks_dict['init_qualify_ques_7'] + marks_dict['init_qualify_ques_8']) / 8
			if candidate_marks_obj.thumbs_up:
				response['flag'] = 'Thumbs Up'
			if candidate_marks_obj.thumbs_down:
				response['flag'] = 'Thumbs Down'
			if candidate_marks_obj.hold:
				response['flag'] = 'Hold'
			if candidate_marks_obj.golden_gloves:
				response['flag'] = 'Golden Glove'
			response['marks_given_by'] = hiring_member_id
			response['feedback'] = candidate_marks_obj.feedback
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Google Calendar APIs Not used anymore
class GetGoogleAuthUrl(APIView):
	def post(self, request):
		try:
			flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
			    'client_secret.json',
			    scopes=SCOPES)
			flow.redirect_uri = 'http://qorums.com/callbackoauth'
			authorization_url, state = flow.authorization_url(
			    access_type='offline',
			    include_granted_scopes='true')
			print(authorization_url)
			response = {}
			response['msg'] = 'success'
			response['url'] = authorization_url
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Google Calendar APIs Not used anymore
class GetGoogleAuthUrlResponse(APIView):
	def post(self, request):
		try:
			flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
			    'client_secret.json',
			    scopes=SCOPES)
			flow.redirect_uri = 'http://qorums.com/callbackoauthresponse'
			authorization_url, state = flow.authorization_url(
			    access_type='offline',
			    include_granted_scopes='true')
			print(authorization_url)
			response = {}
			response['msg'] = 'success'
			response['url'] = authorization_url
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Google Calendar APIs Not used anymore
class CreateCalendarEventForInterview(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, op_id):
		try:
			candidate_id = request.data.get('candidate_id')
			if InterviewSchedule.objects.filter(candidate=candidate_id):
				schedule_obj = InterviewSchedule.objects.get(candidate=candidate_id)
				code = request.data.get('code')
				state = request.data.get('state')
				start_time = request.data.get('starttime')
				end_time = request.data.get('endtime')
				timezone = request.data.get('timezone')
				htm_message = request.data.get('htm_message')
				candidate_email = request.data.get('candidate_email')
				candidate_id = request.data.get('candidate_id')
				open_position_obj = OpenPosition.objects.get(id=op_id)
				flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
				    'client_secret.json',
				    scopes=SCOPES,
				    state=state)
				flow.redirect_uri = 'http://qorums.com/callbackoauth'

				authorization_response = request.build_absolute_uri()
				print(authorization_response)
				flow.fetch_token(authorization_response=authorization_response)
				credentials = flow.credentials
				print(credentials)

				service = build('calendar', 'v3', credentials=credentials)
				print(start_time)
				print(end_time)
				print(timezone)
				print(candidate_email)
				print('Interview for ' + ' ' + open_position_obj.position_title)
				print('Interview Schedule for the Open Position ' + open_position_obj.position_title)
				event = {
				  'summary': 'Interview for ' + ' ' + open_position_obj.position_title,
				  'description': htm_message,
				  'start': {
				    'dateTime': start_time + ':00',
				    'timeZone': timezone,
				  },
				  'end': {
				    'dateTime': end_time + ':00',
				    'timeZone': timezone,
				  },
				  'attendees': [
				    {'email': candidate_email},
				  ],
				}
				updated_event = service.events().update(calendarId='primary', eventId=schedule_obj.event_id, body=event).execute()
				schedule_obj.candidate = candidate_id
				schedule_obj.event_id = updated_event['id']
				schedule_obj.start_time = start_time
				schedule_obj.end_time = end_time
				schedule_obj.timezone = timezone
				schedule_obj.htm_message = htm_message
				schedule_obj.op_id = op_id
				schedule_obj.save()
				print(updated_event)
				return Response({'msg': 'Schedule Updated!'}, status=status.HTTP_200_OK)
			else:
				code = request.data.get('code')
				state = request.data.get('state')
				start_time = request.data.get('starttime')
				end_time = request.data.get('endtime')
				timezone = request.data.get('timezone')
				htm_message = request.data.get('htm_message')
				candidate_email = request.data.get('candidate_email')
				candidate_id = request.data.get('candidate_id')
				open_position_obj = OpenPosition.objects.get(id=op_id)
				if InterviewSchedule.objects.filter(op_id=op_id, start_time=start_time):
					return Response({'msg': 'An interview is already scheduled at this time.'}, status=status.HTTP_409_CONFLICT)
				flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
				    'client_secret.json',
				    scopes=SCOPES,
				    state=state)
				flow.redirect_uri = 'http://qorums.com/callbackoauth'

				authorization_response = request.build_absolute_uri()
				print(authorization_response)
				flow.fetch_token(authorization_response=authorization_response)
				credentials = flow.credentials
				print(credentials)

				service = build('calendar', 'v3', credentials=credentials)
				print(start_time)
				print(end_time)
				print(timezone)
				print(candidate_email)
				print('Interview for ' + ' ' + open_position_obj.position_title)
				print('Interview Schedule for the Open Position ' + open_position_obj.position_title)
				event = {
				  'summary': 'Interview for ' + ' ' + open_position_obj.position_title,
				  'description': htm_message,
				  'start': {
				    'dateTime': start_time + ':00',
				    'timeZone': timezone,
				  },
				  'end': {
				    'dateTime': end_time + ':00',
				    'timeZone': timezone,
				  },
				  'attendees': [
				    {'email': candidate_email},
				  ],
				}
				event = service.events().insert(calendarId='primary', body=event, sendNotifications='true').execute()
				interview_schedule_obj = InterviewSchedule(
					candidate=candidate_id,
					event_id=event['id'],
					start_time=start_time,
					end_time=end_time,
					timezone=timezone,
					htm_message=htm_message,
					op_id=op_id
				)
				interview_schedule_obj.save()
				print(event)
				return Response({'msg': 'Schedule Created!'}, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Google Calendar APIs Not used anymore
class GetScheduleForCandidate(APIView):
	def get(self, request, candidate_id):
		try:
			candidate_schedule = InterviewSchedule.objects.filter(candidate=candidate_id).last()
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			position_obj = OpenPosition.objects.get(id=candidate_obj.op_id)
			response = {}
			response['msg'] = 'already scheduled'
			response['scheduled'] = True
			response['title'] = 'Interview for ' + position_obj.position_title
			response['starttime'] = candidate_schedule.start_time
			response['endtime'] = candidate_schedule.end_time
			if candidate_schedule.candidate_response == 'needsAction':
				response['candidate_response'] = 'No Response'
			elif candidate_schedule.candidate_response == 'accepted':
				response['candidate_response'] = 'Accepted'
			elif candidate_schedule.candidate_response == 'tentative':
				response['candidate_response'] = 'May be'
			elif candidate_schedule.candidate_response == 'declined':
				response['candidate_response'] = 'Declined'
			else:
				response['candidate_response'] = candidate_schedule.candidate_response
			response['timezone'] = candidate_schedule.timezone
			response['htm_message'] = candidate_schedule.htm_message
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			response['msg'] = 'not scheduled'
			response['scheduled'] = False
			return Response(response, status=status.HTTP_200_OK)


# Google Calendar APIs Not used anymore
class GetScheduleResponse(APIView):
	def get(self, request, op_id):
		try:
			code = request.query_params.get('code')
			state = request.query_params.get('state')
			flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
			    'client_secret.json',
			    scopes=SCOPES,
			    state=state)
			flow.redirect_uri = 'http://qorums.com/callbackoauthresponse'

			authorization_response = request.build_absolute_uri()
			print(authorization_response)
			flow.fetch_token(authorization_response=authorization_response)
			credentials = flow.credentials
			print(credentials)

			service = build('calendar', 'v3', credentials=credentials)
			page_token = None
			while True:
				events = service.events().list(calendarId='primary', pageToken=page_token).execute()
				for event in events['items']:
					try:
						interview_obj = InterviewSchedule.objects.get(event_id=event['id'])
					except:
						continue
					interview_obj.candidate_response = event['attendees'][0]['responseStatus']
					interview_obj.save()
				page_token = events.get('nextPageToken')
				if not page_token:
					break
			response = {}
			response['data'] = []
			for i in InterviewSchedule.objects.filter(op_id=op_id):
				if i.candidate_response == 'needsAction':
					i.candidate_response = 'No Response'
				elif i.candidate_response == 'accepted':
					i.candidate_response = 'Accepted'
				elif i.candidate_response == 'tentative':
					i.candidate_response = 'May be'
				elif i.candidate_response == 'declined':
					i.candidate_response = 'Declined'
				i.save()
				response['data'].append({'candidate_id': i.candidate, 'candidate_response': i.candidate_response})
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetQuestiosView(APIView):
	def get(self, request, op_id):
		open_position_obj = OpenPosition.objects.get(id=op_id)
		data = {}
		data['init_qualify_ques_1'] = open_position_obj.sec_ques_1
		data['init_qualify_ques_2'] = open_position_obj.sec_ques_2
		data['init_qualify_ques_3'] = open_position_obj.sec_ques_3
		data['init_qualify_ques_4'] = open_position_obj.sec_ques_4
		data['init_qualify_ques_5'] = open_position_obj.sec_ques_5
		data['init_qualify_ques_6'] = open_position_obj.sec_ques_6
		data['init_qualify_ques_7'] = open_position_obj.sec_ques_7
		data['init_qualify_ques_8'] = open_position_obj.sec_ques_8
		return Response(data, status=status.HTTP_200_OK)


# APIs used for Candidate Management from Candidate Screen 
class CandidateBasicDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, candidate_id):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			response = {}
			response['redirect_to'] = 'http://qorums.com/add-candidate-data/?email=' + candidate_obj.email + '&id=' + str(candidate_obj.candidate_id)
			response['candidate_id'] = candidate_obj.candidate_id
			response['linkedin_first_name'] = candidate_obj.linkedin_first_name
			response['linkedin_last_name'] = candidate_obj.linkedin_last_name
			response['linkedin_last_name'] = candidate_obj.linkedin_last_name
			response['alernate_email'] = candidate_obj.alernate_email
			response['name'] = candidate_obj.name
			response['nickname'] = candidate_obj.nickname
			response['last_name'] = candidate_obj.last_name
			response['email'] = candidate_obj.email
			if 'profile_pic_url' in candidate_obj.linkedin_data and candidate_obj.linkedin_data['profile_pic_url'] and candidate_obj.linkedin_data["profile_pic_url"] != "null":
				response['profile_photo'] = candidate_obj.linkedin_data['profile_pic_url']
			else:
				response['profile_photo'] = candidate_obj.profile_photo
			response['profile_photo'] = candidate_obj.profile_photo
			response['phone_number'] = candidate_obj.phone_number
			response['skype_id'] = candidate_obj.skype_id
			response['job_title'] = candidate_obj.job_title
			response['location'] = candidate_obj.location
			response['work_auth'] = candidate_obj.work_auth
			response['personal_notes'] = candidate_obj.personal_notes
			response['comments'] = candidate_obj.comments
			response['current_position'] = candidate_obj.job_title
			response['created_by_client'] = candidate_obj.created_by_client
			try:
				docs = []
				for doc in json.loads(candidate_obj.documents):
					temp_doc = {}
					temp_doc["url"] = doc
					temp_doc["name"] = doc.split('/')[-1]
					docs.append(temp_doc)
				response['documents'] = docs
			except:
				pass
			try:
				docs = []
				for doc in json.loads(candidate_obj.references):
					temp_doc = {}
					temp_doc["url"] = doc
					temp_doc["name"] = doc.split('/')[-1]
					docs.append(temp_doc)
				response['references'] = docs
			except:
				pass
			response['linkedin_data'] = candidate_obj.linkedin_data
			response['skillsets'] = candidate_obj.skillsets
			response['desired_work_location'] = candidate_obj.desired_work_location
			response['salaryRange'] = candidate_obj.salaryRange
			response['currency'] = candidate_obj.currency
			positions_data = []
			for position in json.loads(candidate_obj.associated_op_ids):
				try:
					open_position_obj = OpenPosition.objects.get(id=position)
					try:
						hiring_group_obj = HiringGroup.objects.get(group_id=open_position_obj.hiring_group)
					except:
						continue
					marks_dict = {}
					final_avg_marks = 0
					marks_dict['init_qualify_ques_1'] = 0
					marks_dict['init_qualify_ques_2'] = 0
					marks_dict['init_qualify_ques_3'] = 0
					marks_dict['init_qualify_ques_4'] = 0
					marks_dict['init_qualify_ques_5'] = 0
					marks_dict['init_qualify_ques_6'] = 0
					marks_dict['init_qualify_ques_7'] = 0
					marks_dict['init_qualify_ques_8'] = 0
					marks_dict['init_qualify_ques_1_text'] = open_position_obj.init_qualify_ques_1
					marks_dict['init_qualify_ques_2_text'] = open_position_obj.init_qualify_ques_2
					marks_dict['init_qualify_ques_3_text'] = open_position_obj.init_qualify_ques_3
					marks_dict['init_qualify_ques_4_text'] = open_position_obj.init_qualify_ques_4
					marks_dict['init_qualify_ques_5_text'] = open_position_obj.init_qualify_ques_5
					marks_dict['init_qualify_ques_6_text'] = open_position_obj.init_qualify_ques_6
					marks_dict['init_qualify_ques_7_text'] = open_position_obj.init_qualify_ques_7
					marks_dict['init_qualify_ques_8_text'] = open_position_obj.init_qualify_ques_8
					# Get all scheduled interviews for the candidate
					candidate_schedule_list = []
					for interview in Interview.objects.filter(candidate__candidate_id=candidate_id, op_id__id=position).filter(disabled=False):
						try:
							temp_dict = {}
							interviewers_names = interview.htm.all().values_list("user__first_name", flat=True)
							temp_dict['interviewer_name'] = ", ".join(interviewers_names)
							temp_dict['time'] = interview.interview_date_time.strftime("%m/%d/%Y, %H:%M:%S")
							candidate_schedule_list.append(temp_dict)
						except:
							continue
					HM_vote = {}
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=candidate_id, op_id=position)
					htm_weightage_1_total = 0
					htm_weightage_2_total = 0
					htm_weightage_3_total = 0
					htm_weightage_4_total = 0
					htm_weightage_5_total = 0
					htm_weightage_6_total = 0
					htm_weightage_7_total = 0
					htm_weightage_8_total = 0
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						try:
							htm_weightage_obj = HTMWeightage.objects.get(op_id=position, htm_id=given_by)
							htm_weightage_1_total = htm_weightage_1_total + htm_weightage_obj.init_qualify_ques_1_weightage
							htm_weightage_2_total = htm_weightage_2_total + htm_weightage_obj.init_qualify_ques_2_weightage
							htm_weightage_3_total = htm_weightage_3_total + htm_weightage_obj.init_qualify_ques_3_weightage
							htm_weightage_4_total = htm_weightage_4_total + htm_weightage_obj.init_qualify_ques_4_weightage
							htm_weightage_5_total = htm_weightage_5_total + htm_weightage_obj.init_qualify_ques_5_weightage
							htm_weightage_6_total = htm_weightage_6_total + htm_weightage_obj.init_qualify_ques_6_weightage
							htm_weightage_7_total = htm_weightage_7_total + htm_weightage_obj.init_qualify_ques_7_weightage
							htm_weightage_8_total = htm_weightage_8_total + htm_weightage_obj.init_qualify_ques_8_weightage
						except:
							htm_weightage_1_total = htm_weightage_1_total + 10
							htm_weightage_2_total = htm_weightage_2_total + 10
							htm_weightage_3_total = htm_weightage_3_total + 10
							htm_weightage_4_total = htm_weightage_4_total + 10
							htm_weightage_5_total = htm_weightage_5_total + 10
							htm_weightage_6_total = htm_weightage_6_total + 10
							htm_weightage_7_total = htm_weightage_7_total + 10
							htm_weightage_8_total = htm_weightage_8_total + 10
					if candidate_marks_obj:
						for c_obj in candidate_marks_obj:
							given_by = c_obj.marks_given_by
							try:
								htm_weightage_obj = HTMWeightage.objects.get(op_id=position, htm_id=given_by)
								htm_weightage_1 = htm_weightage_obj.init_qualify_ques_1_weightage
								htm_weightage_2 = htm_weightage_obj.init_qualify_ques_2_weightage
								htm_weightage_3 = htm_weightage_obj.init_qualify_ques_3_weightage
								htm_weightage_4 = htm_weightage_obj.init_qualify_ques_4_weightage
								htm_weightage_5 = htm_weightage_obj.init_qualify_ques_5_weightage
								htm_weightage_6 = htm_weightage_obj.init_qualify_ques_6_weightage
								htm_weightage_7 = htm_weightage_obj.init_qualify_ques_7_weightage
								htm_weightage_8 = htm_weightage_obj.init_qualify_ques_8_weightage
							except Exception as e:
								htm_weightage_1 = 10
								htm_weightage_2 = 10
								htm_weightage_3 = 10
								htm_weightage_4 = 10
								htm_weightage_5 = 10
								htm_weightage_6 = 10
								htm_weightage_7 = 10
								htm_weightage_8 = 10
							marks_dict['init_qualify_ques_1'] = marks_dict['init_qualify_ques_1'] + c_obj.criteria_1_marks * htm_weightage_1
							marks_dict['init_qualify_ques_2'] = marks_dict['init_qualify_ques_2'] + c_obj.criteria_2_marks * htm_weightage_2
							marks_dict['init_qualify_ques_3'] = marks_dict['init_qualify_ques_3'] + c_obj.criteria_3_marks * htm_weightage_3
							marks_dict['init_qualify_ques_4'] = marks_dict['init_qualify_ques_4'] + c_obj.criteria_4_marks * htm_weightage_4
							marks_dict['init_qualify_ques_5'] = marks_dict['init_qualify_ques_5'] + c_obj.criteria_5_marks * htm_weightage_5
							marks_dict['init_qualify_ques_6'] = marks_dict['init_qualify_ques_6'] + c_obj.criteria_6_marks * htm_weightage_6
							marks_dict['init_qualify_ques_7'] = marks_dict['init_qualify_ques_7'] + c_obj.criteria_7_marks * htm_weightage_7
							marks_dict['init_qualify_ques_8'] = marks_dict['init_qualify_ques_8'] + c_obj.criteria_8_marks * htm_weightage_8
						marks_dict['init_qualify_ques_1'] = round(marks_dict['init_qualify_ques_1'] / htm_weightage_1_total, 1)
						marks_dict['init_qualify_ques_2'] = round(marks_dict['init_qualify_ques_2'] / htm_weightage_2_total, 1)
						marks_dict['init_qualify_ques_3'] = round(marks_dict['init_qualify_ques_3'] / htm_weightage_3_total, 1)
						marks_dict['init_qualify_ques_4'] = round(marks_dict['init_qualify_ques_4'] / htm_weightage_4_total, 1)
						marks_dict['init_qualify_ques_5'] = round(marks_dict['init_qualify_ques_5'] / htm_weightage_5_total, 1)
						marks_dict['init_qualify_ques_6'] = round(marks_dict['init_qualify_ques_6'] / htm_weightage_6_total, 1)
						marks_dict['init_qualify_ques_7'] = round(marks_dict['init_qualify_ques_7'] / htm_weightage_7_total, 1)
						marks_dict['init_qualify_ques_8'] = round(marks_dict['init_qualify_ques_8'] / htm_weightage_8_total, 1)
						count = 0
						avg_marks = 0
						if marks_dict['init_qualify_ques_1'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_1
							avg_marks = avg_marks + marks_dict['init_qualify_ques_1'] * open_position_obj.init_qualify_ques_weightage_1
						if marks_dict['init_qualify_ques_2'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_2
							avg_marks = avg_marks + marks_dict['init_qualify_ques_2'] * open_position_obj.init_qualify_ques_weightage_2
						if marks_dict['init_qualify_ques_3'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_3
							avg_marks = avg_marks + marks_dict['init_qualify_ques_3'] * open_position_obj.init_qualify_ques_weightage_3
						if marks_dict['init_qualify_ques_4'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_4
							avg_marks = avg_marks + marks_dict['init_qualify_ques_4'] * open_position_obj.init_qualify_ques_weightage_4
						if marks_dict['init_qualify_ques_5'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_5
							avg_marks = avg_marks + marks_dict['init_qualify_ques_5'] * open_position_obj.init_qualify_ques_weightage_5
						if marks_dict['init_qualify_ques_6'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_6
							avg_marks = avg_marks + marks_dict['init_qualify_ques_6'] * open_position_obj.init_qualify_ques_weightage_6
						if marks_dict['init_qualify_ques_7'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_7
							avg_marks = avg_marks + marks_dict['init_qualify_ques_7'] * open_position_obj.init_qualify_ques_weightage_7
						if marks_dict['init_qualify_ques_8'] not in [0, 0.0]:
							count = count + open_position_obj.init_qualify_ques_weightage_8
							avg_marks = avg_marks + marks_dict['init_qualify_ques_8'] * open_position_obj.init_qualify_ques_weightage_8
						if count:
							final_avg_marks = round(avg_marks / count, 1)
						else:
							final_avg_marks = 0.0
					temp_dict = {}
					temp_dict['marks'] = marks_dict
					temp_dict['position_name'] = open_position_obj.position_title
					temp_dict['final_avg_marks'] = final_avg_marks
					positions_data.append(temp_dict)
				except Exception as e:
					print(e)
					continue
			response['positions_data'] = positions_data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def post(self, request, candidate_id):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			response = {}
			linkedin_first_name = request.data.get('linkedin_first_name')
			linkedin_last_name = request.data.get('linkedin_last_name')
			alernate_email = request.data.get('alernate_email')
			current_position = request.data.get('current_position')
			location = request.data.get('location')
			work_auth = request.data.get('work_auth')
			personal_notes = request.data.get('personal_notes')
			comments = request.data.get('comments')
			try:
				profile_photo = request.FILES['Profile_image']
				p_fs = FileSystemStorage()
				profile_filename = p_fs.save(profile_photo.name, profile_photo)
				uploaded_profile_photo = p_fs.url(profile_filename)
			except Exception as e:
				print(e)
				uploaded_profile_photo = candidate_obj.profile_photo
			candidate_obj.linkedin_first_name = linkedin_first_name
			candidate_obj.linkedin_last_name = linkedin_last_name
			candidate_obj.alernate_email = alernate_email
			candidate_obj.profile_photo = uploaded_profile_photo
			candidate_obj.job_title = current_position
			candidate_obj.location = location
			candidate_obj.work_auth = work_auth
			candidate_obj.personal_notes = personal_notes
			candidate_obj.comments = comments
			candidate_obj.skillsets = request.data.get('skillsets', candidate_obj.skillsets)
			candidate_obj.desired_work_location = request.data.get('desired_work_location', candidate_obj.desired_work_location)
			candidate_obj.currency = request.data.get('currency')
			candidate_obj.salaryRange = request.data.get('salaryRange', candidate_obj.salaryRange)
			candidate_obj.updated_at = datetime.now()
			candidate_obj.save()
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


# APIs used for Candidate Management from Candidate Screen 
class AddCandidateDetailsView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		try:
			candidate_email = request.data.get('email')
			op_id = request.data.get('op_id')
			candidate_obj = Candidate.objects.get(email=candidate_email)
			question_response = request.data.get('question_response')
			try:
				candidate_position_obj = CandidatePositionDetails.objects.get(candidate_id=candidate_obj.candidate_id, op_id=op_id)
				uploaded_resume = json.loads(candidate_position_obj.uploaded_docs)
			except:
				uploaded_resume = []
			if request.FILES:
				for i in request.FILES:
					if i == 'Profile_image':
						pass
					else:
						file = request.FILES[i]
						fs = FileSystemStorage()
						filename = fs.save(file.name, file)
						uploaded_file_url = fs.url(filename)
						uploaded_resume.append(uploaded_file_url)
						print(uploaded_resume)
				uploaded_resume = json.dumps(uploaded_resume)
			else:
				uploaded_resume = json.dumps(uploaded_resume)
			question_response = question_response.replace("\\", "")
			question_response = question_response.strip('"').rstrip('"')
			candidate_position_obj = CandidatePositionDetails.objects.create(
				candidate_id=candidate_obj.candidate_id,
				op_id=op_id,
				question_response=question_response,
				uploaded_docs=uploaded_resume
			)
			candidate_position_obj.save()
			return Response({'msg': 'data added', })
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def get(self, request):
		try:
			candidate_email = request.query_params.get('email')
			op_id = request.query_params.get('op_id')
			candidate_obj = Candidate.objects.filter(email=candidate_email)[0]
			response = {}
			open_position_obj = OpenPosition.objects.get(id=op_id)
			candidate_position_data_objs = CandidatePositionDetails.objects.filter(candidate_id=candidate_obj.candidate_id, op_id=op_id)
			if candidate_position_data_objs:
				question_response = json.loads(candidate_position_data_objs[0].question_response)
				print(question_response)
				length = len(question_response)
				print(length)
				for i in range(length, 8):
					question_response.append('None')
				print(question_response)
				response['string_response'] = candidate_position_data_objs[0].question_response
				response['loaded_response'] = question_response
				response['question_response'] = []
				response['question_response'].append({open_position_obj.sec_ques_1: question_response[0]})
				response['question_response'].append({open_position_obj.sec_ques_2: question_response[1]})
				response['question_response'].append({open_position_obj.sec_ques_3: question_response[2]})
				response['question_response'].append({open_position_obj.sec_ques_4: question_response[3]})
				response['question_response'].append({open_position_obj.sec_ques_5: question_response[4]})
				response['question_response'].append({open_position_obj.sec_ques_6: question_response[5]})
				response['question_response'].append({open_position_obj.sec_ques_7: question_response[6]})
				response['question_response'].append({open_position_obj.sec_ques_8: question_response[7]})
				res = [i for i in response['question_response'] if i != {'Use Existing': 'None'}]
				response['question_response'] = res
				response['uploaded_docs'] = json.loads(candidate_position_data_objs[0].uploaded_docs)
			else:
				response['msg'] = 'No Response'
				response['question_response'] = []
				response['uploaded_docs'] = []
			# response['profile_photo'] = candidate_obj.profile_photo
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class AssociateCandidateView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, client_id, op_id):
		try:
			response = {}
			if int(op_id) == int(settings.EXAMPLE_POSITION) and not request.user.is_superuser:
				response['msg'] = 'Candidates can not be associated in this position!'
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			try:
				openposition_obj = OpenPosition.objects.get(id=op_id)
			except Exception as e:
				response['error'] = str(e)
				response['msg'] = 'op does not exists'
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			try:
				client_obj = Client.objects.get(id=client_id)
			except Exception as e:
				response = {}
				response['error'] = str(e)
				response['msg'] = 'client does not exists'
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			candidate_id = request.data.get('candidate_id')
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			if CandidateAssociateData.objects.filter(candidate=candidate_obj, open_position__id=op_id):
				return Response({'msg': "Candidate already associated to this position."}, status=status.HTTP_400_BAD_REQUEST)
			associated_client_ids = json.loads(candidate_obj.associated_client_ids)
			if int(client_id) not in associated_client_ids:
				associated_client_ids.append(int(client_id))
			candidate_obj.associated_client_ids = json.dumps(associated_client_ids)

			requested_op_ids = candidate_obj.requested_op_ids
			if int(op_id) not in requested_op_ids:
				requested_op_ids.append(int(op_id))
			else:
				response = {}
				response['msg'] = 'Candidate Already Requested Associated.'
				return Response(response, status=status.HTTP_208_ALREADY_REPORTED)
			candidate_obj.requested_op_ids = requested_op_ids
			candidate_obj.save()
			# Sending Mail to Candidate - Not used amymore
			# subject = 'Welcome to Qorums'
			# d = {
			# 	"candidate_name": candidate_obj.name,
			# 	"position_title": openposition_obj.position_title,
			# 	"company": client_obj.company_name,
			# 	"username": candidate_obj.username,
			# 	"password": candidate_obj.key,
			# 	"manager": client_obj.hr_contact_name,
			# 	"manager_contact": client_obj.hr_contact_phone_no,
			# 	"manager_email": client_obj.hr_contact_email,
			# }
			# email_from = settings.EMAIL_HOST_USER
			# recipient_list = [candidate_obj.email, ]
			# htmly_b = get_template('candidate_mail.html')
			# text_content = ""
			# html_content = htmly_b.render(d)
			# msg = EmailMultiAlternatives(subject, text_content, email_from, recipient_list)
			# msg.attach_alternative(html_content, "text/html")
			# try:
			# 	msg.send(fail_silently=False)
			# except Exception as e:
			# 	return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
						# Sending Mail to Candidate
			response['msg'] = 'Candidate Associated'
			# response['htm_emails'] = htm_emails
			# add associate candidate data
			associate_data = request.data.copy()
			associate_data['open_position'] = op_id
			associate_data['candidate'] = candidate_id
			serializer = CandidateAssociateDataSerializer(data=associate_data)
			if serializer.is_valid():
				obj = serializer.save()
				# Saving resume
				docs_list = []
				try:
					print('-----------------Try Getting Resume----------------------')
					if request.FILES.getlist('resume[]'):
						for doc in request.FILES.getlist('resume[]'):
							try:
								p_fs = FileSystemStorage()
								profile_filename = p_fs.save(doc.name, doc)
								uploaded_doc = p_fs.url(profile_filename)
								docs_list.append(uploaded_doc)
							except Exception as e:
								print(e)
				except Exception as e:
					print('-----------------Error Getting Documents List----------------------')
					print(e)
				obj.resume = docs_list
				# Savinf reference
				docs_list = []
				try:
					print('-----------------Try Getting reference----------------------')
					if request.FILES.getlist('reference[]'):
						for doc in request.FILES.getlist('reference[]'):
							try:
								p_fs = FileSystemStorage()
								profile_filename = p_fs.save(doc.name, doc)
								uploaded_doc = p_fs.url(profile_filename)
								docs_list.append(uploaded_doc)
							except Exception as e:
								print(e)
				except Exception as e:
					print('-----------------Error Getting Documents List----------------------')
					print(e)
				obj.references = docs_list
				obj.accepted = None
				obj.save()
				response['resume-ref'] = 'Saved'
			else:
				response['associate-data'] = 'error adding associate data'
				response['error'] = serializer.errors
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetQualifyingResponse(APIView):
	def get(self, request, candidate_id):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			op_id = candidate_obj.op_id
			open_position_obj = OpenPosition.objects.get(id=op_id)
			data = {}
			if candidate_obj.question_response == 'None':
				data['msg'] = 'No Response'
				data['question_response'] = []
			else:
				question_response = json.loads(candidate_obj.question_response)
				length = len(question_response)
				for i in range(length, 8):
					question_response.append('None')
				data['question_response'] = []
				data['question_response'].append({open_position_obj.sec_ques_1: question_response[0]})
				data['question_response'].append({open_position_obj.sec_ques_2: question_response[1]})
				data['question_response'].append({open_position_obj.sec_ques_3: question_response[2]})
				data['question_response'].append({open_position_obj.sec_ques_4: question_response[3]})
				data['question_response'].append({open_position_obj.sec_ques_5: question_response[4]})
				data['question_response'].append({open_position_obj.sec_ques_6: question_response[5]})
				data['question_response'].append({open_position_obj.sec_ques_7: question_response[6]})
				data['question_response'].append({open_position_obj.sec_ques_8: question_response[7]})
				res = []
				for i in data["question_response"]:
					if None in i:
						pass
					else:
						res.append(i)
				data['question_response'] = res
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetCandidateDocs(APIView):
	def get(self, request, candidate_id):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			response = {}
			if 'profile_pic_url' in candidate_obj.linkedin_data and candidate_obj.linkedin_data['profile_pic_url'] and candidate_obj.linkedin_data['profile_pic_url'] != "null":
				response['profile_photo'] = candidate_obj.linkedin_data['profile_pic_url']
			else:
				response['profile_photo'] = candidate_obj.profile_phot
			if candidate_obj.uploaded_docs == 'None':
				response['uploaded_docs'] = 'None'
			else:
				response['uploaded_docs'] = json.loads(candidate_obj.uploaded_docs)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class AllCandidateDataView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			data = {}
			for i in string.ascii_uppercase:
				data[i] = []
			if request.user.is_superuser or "is_ae" in request.user.profile.roles:
				queryset = Candidate.objects.all()
			else:
				queryset = Candidate.objects.filter(Q(created_by_client=request.user.profile.client)|Q(created_by_client=0))				
			for i in queryset.order_by('last_name'):
				temp_dict = {}
				temp_dict['candidate_id'] = i.candidate_id
				temp_dict['name'] = i.name + ' ' + i.last_name
				temp_dict['last_name'] = i.last_name
				application_count = CandidateAssociateData.objects.filter(candidate=i, accepted=True, withdrawed=False).count()
				temp_dict['applications'] = application_count
				temp_dict['status'] = 'Open'
				temp_dict['phone'] = i.phone_number
				temp_dict['email'] = i.email
				if 'profile_pic_url' in i.linkedin_data and i.linkedin_data['profile_pic_url'] and i.linkedin_data['profile_pic_url'] != "null":
					temp_dict['profile_photo'] = i.linkedin_data['profile_pic_url']
				else:
					temp_dict['profile_photo'] = i.profile_photo
				temp_dict['current_position'] = i.job_title
				temp_dict['location'] = i.location
				temp_dict['skillsets'] = i.skillsets
				temp_dict['linkedin_data'] = i.linkedin_data
				temp_dict['currency'] = i.currency
				temp_dict['salaryRange'] = i.salaryRange
				temp_dict['desired_work_location'] = i.desired_work_location
				# temp_dict['profile_pic_url'] = i.linkedin_data.get('profile_pic_url')
				overallscore = 0
				for j in CandidateMarks.objects.filter(candidate_id=i.candidate_id):
					avg_marks = (j.criteria_1_marks + j.criteria_2_marks + j.criteria_3_marks + j.criteria_4_marks + j.criteria_5_marks + j.criteria_6_marks + j.criteria_7_marks + j.criteria_8_marks) / 8
					overallscore = overallscore + avg_marks
				if application_count == 0 or CandidateMarks.objects.filter(candidate_id=i.candidate_id).count() == 0:
					temp_dict['overallscore'] = 0
				else:
					temp_dict['overallscore'] = round(overallscore / (application_count * CandidateMarks.objects.filter(candidate_id=i.candidate_id).count()), 2)
				try:
					data[temp_dict['last_name'][0].upper()].append(temp_dict)
					l = data[temp_dict['last_name'][0].upper()]
					sorted_list = sorted(l, key=lambda d: d['last_name'], reverse=False)
					data[temp_dict['last_name'][0].upper()] = sorted_list
				except Exception as e:
					data[temp_dict['last_name'][0].upper()] = [temp_dict]
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetCandidatesToAssociateView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			response = {}
			data = []
			if request.user.profile.is_ca or request.user.profile.is_sm:
				queryset = Candidate.objects.filter(Q(created_by_client=request.user.profile.client)|Q(created_by_client=0))
			else:
				queryset = Candidate.objects.all()
			for i in queryset:
				temp_dict = {}
				if CandidateAssociateData.objects.filter(candidate=i, open_position__id=op_id):
					temp_dict['associated'] = True
				else:
					temp_dict['associated'] = False
				temp_dict['candidate_id'] = i.candidate_id
				temp_dict['name'] = i.name + ' ' + i.last_name
				application_count = CandidateAssociateData.objects.filter(candidate=i, accepted=True, withdrawed=False).count()
				temp_dict['applications'] = application_count
				temp_dict['status'] = 'Open'
				temp_dict['phone'] = i.phone_number
				temp_dict['email'] = i.email 
				temp_dict['nickname'] = i.nickname
				temp_dict['location'] = i.location
				temp_dict['current_job'] = i.job_title
				temp_dict['skillsets'] = i.skillsets
				temp_dict['desired_work_location'] = i.desired_work_location
				temp_dict['currency'] = i.currency
				temp_dict['salaryRange'] = i.salaryRange
				temp_dict['linkedin_data'] = i.linkedin_data
				if 'profile_pic_url' in i.linkedin_data and i.linkedin_data['profile_pic_url'] and i.linkedin_data['profile_pic_url'] != "null":
					temp_dict['profile_photo'] = i.linkedin_data['profile_pic_url']
					# response['profile_pic_url'] = i.linkedin_data['profile_pic_url']
				else:
					temp_dict['profile_photo'] = i.profile_photo
				overallscore = 0
				for j in CandidateMarks.objects.filter(candidate_id=i.candidate_id):
					avg_marks = (j.criteria_1_marks + j.criteria_2_marks + j.criteria_3_marks + j.criteria_4_marks + j.criteria_5_marks + j.criteria_6_marks + j.criteria_7_marks + j.criteria_8_marks) / 8
					overallscore = overallscore + avg_marks
				if application_count == 0 or CandidateMarks.objects.filter(candidate_id=i.candidate_id).count() == 0:
					temp_dict['overallscore'] = 0
				else:
					temp_dict['overallscore'] = round(overallscore / (application_count * CandidateMarks.objects.filter(candidate_id=i.candidate_id).count()), 2)
				data.append(temp_dict)
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


# Not used anymore
class CandidateApplicationsDataView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, candidate_id):
		try:
			response = {}
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			data = []
			for cao in CandidateAssociateData.objects.filter(candidate=candidate_obj, accepted=True, withdrawed=False):
				temp_dict = {}
				position_obj = cao.open_position
				temp_dict['date'] = position_obj.target_deadline
				client_obj = Client.objects.get(id=position_obj.client)
				try:
					candidate_status_obj = CandidateStatus.objects.get(candidate_id=candidate_id, op_id=cao.open_position.id)
					temp_dict['shortlist_status'] = candidate_status_obj.shortlist_status
					temp_dict['make_offer_status'] = candidate_status_obj.make_offer_status
					temp_dict['finall_selection_status'] = candidate_status_obj.finall_selection_status
				except:
					temp_dict['shortlist_status'] = False
					temp_dict['make_offer_status'] = False
					temp_dict['finall_selection_status'] = False
				temp_dict['client'] = client_obj.company_name
				temp_dict['position'] = position_obj.position_title
				temp_dict['date'] = position_obj.target_deadline
				candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=candidate_id, op_id=cao.open_position.id)
				marks_dict = {}
				if candidate_marks_obj:
					marks_dict['init_qualify_ques_1'] = candidate_marks_obj.aggregate(Avg('criteria_1_marks'))['criteria_1_marks__avg']
					marks_dict['init_qualify_ques_2'] = candidate_marks_obj.aggregate(Avg('criteria_2_marks'))['criteria_2_marks__avg']
					marks_dict['init_qualify_ques_3'] = candidate_marks_obj.aggregate(Avg('criteria_3_marks'))['criteria_3_marks__avg']
					marks_dict['init_qualify_ques_4'] = candidate_marks_obj.aggregate(Avg('criteria_4_marks'))['criteria_4_marks__avg']
					marks_dict['init_qualify_ques_5'] = candidate_marks_obj.aggregate(Avg('criteria_5_marks'))['criteria_5_marks__avg']
					marks_dict['init_qualify_ques_6'] = candidate_marks_obj.aggregate(Avg('criteria_6_marks'))['criteria_6_marks__avg']
					marks_dict['init_qualify_ques_7'] = candidate_marks_obj.aggregate(Avg('criteria_7_marks'))['criteria_7_marks__avg']
					marks_dict['init_qualify_ques_8'] = candidate_marks_obj.aggregate(Avg('criteria_8_marks'))['criteria_8_marks__avg']
					temp_dict['overall_score'] = round((marks_dict['init_qualify_ques_1'] + marks_dict['init_qualify_ques_2'] + marks_dict['init_qualify_ques_3'] + marks_dict['init_qualify_ques_4'] + marks_dict['init_qualify_ques_5'] + marks_dict['init_qualify_ques_6'] + marks_dict['init_qualify_ques_7'] + marks_dict['init_qualify_ques_8']) / 8, 2)
				else:
					temp_dict['overall_score'] = 0
				temp_dict['op_id'] = cao.open_position.id
				data.append(temp_dict)
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class CandidateSingleApplicationDatView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, candidate_id, op_id):
		try:
			open_position_obj = OpenPosition.objects.get(id=op_id)
			candidates_obj = Candidate.objects.get(candidate_id=candidate_id)
			data = {}
			data['name'] = candidates_obj.name
			data['email'] = candidates_obj.email
			data['op_id'] = op_id
			data['client_id'] = open_position_obj.client
			try:
				hiring_group_obj = HiringGroup.objects.get(group_id=open_position_obj.hiring_group)
			except:
				data['marks'] = {}
				data['final_avg_marks'] = 0
				data['total_hiring_members'] = 0
				data['marks_given_by'] = 0
				data['flag'] = 'Not Given'
				return Response(data, status=status.HTTP_200_OK)
			marks_dict = {}
			candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=candidate_id, op_id=op_id)
			if candidate_marks_obj:
				marks_dict['init_qualify_ques_1'] = candidate_marks_obj.aggregate(Avg('criteria_1_marks'))['criteria_1_marks__avg']
				marks_dict['init_qualify_ques_2'] = candidate_marks_obj.aggregate(Avg('criteria_2_marks'))['criteria_2_marks__avg']
				marks_dict['init_qualify_ques_3'] = candidate_marks_obj.aggregate(Avg('criteria_3_marks'))['criteria_3_marks__avg']
				marks_dict['init_qualify_ques_4'] = candidate_marks_obj.aggregate(Avg('criteria_4_marks'))['criteria_4_marks__avg']
				marks_dict['init_qualify_ques_5'] = candidate_marks_obj.aggregate(Avg('criteria_5_marks'))['criteria_5_marks__avg']
				marks_dict['init_qualify_ques_6'] = candidate_marks_obj.aggregate(Avg('criteria_6_marks'))['criteria_6_marks__avg']
				marks_dict['init_qualify_ques_7'] = candidate_marks_obj.aggregate(Avg('criteria_7_marks'))['criteria_7_marks__avg']
				marks_dict['init_qualify_ques_8'] = candidate_marks_obj.aggregate(Avg('criteria_8_marks'))['criteria_8_marks__avg']
				data['marks'] = marks_dict
				data['final_avg_marks'] = (marks_dict['init_qualify_ques_1'] + marks_dict['init_qualify_ques_2'] + marks_dict['init_qualify_ques_3'] + marks_dict['init_qualify_ques_4'] + marks_dict['init_qualify_ques_5'] + marks_dict['init_qualify_ques_6'] + marks_dict['init_qualify_ques_7'] + marks_dict['init_qualify_ques_8']) / 8
				data['total_hiring_members'] = hiring_group_obj.members_list.all().count() - 1
				data['marks_given_by'] = candidate_marks_obj.count()
				thumbs_up = 0
				thumbs_down = 0
				hold = 0
				data['he_flag'] = None
				data['flag_by_hiring_manager'] = []
				for j in candidate_marks_obj:
					temp_dict = {}
					temp_dict['id'] = j.marks_given_by
					try:
						profile_obj = Profile.objects.get(id=j.marks_given_by)
						temp_dict['hiring_member_name'] = profile_obj.user.first_name
					except:
						temp_dict['hiring_member_name'] = 'None'
					if j.thumbs_up or j.golden_gloves:
						temp_dict['flag'] = 'Thumbs Up'
						thumbs_up = thumbs_up + 1
					if j.thumbs_down:
						temp_dict['flag'] = 'Thumbs Down'
						thumbs_down = thumbs_down + 1
					if j.hold:
						temp_dict['flag'] = 'Hold'
						hold = hold + 1
					specific_marks_obj = CandidateMarks.objects.filter(op_id=op_id, candidate_id=candidate_id, marks_given_by=j.marks_given_by)
					if specific_marks_obj:
						temp_dict['feedback'] = specific_marks_obj[0].feedback
					data['flag_by_hiring_manager'].append(temp_dict)
			else:
				data['marks'] = {}
				data['final_avg_marks'] = 0
				data['total_hiring_members'] = hiring_group_obj.members_list.all().count() - 1
				data['marks_given_by'] = 0
				data['flag'] = 'Not Given'
				data['flag_by_hiring_manager'] = []
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetCandidatesBasedOnClient(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, client_id):
		try:
			response = {}
			data = []
			for i in Candidate.objects.all():
				if client_id in json.loads(i.associated_client_ids):
					temp_dict = {}
					temp_dict['candidate_id'] = i.candidate_id
					temp_dict['name'] = i.name
					application_count = CandidateAssociateData.objects.filter(candidate=i, accepted=True, withdrawed=False)
					temp_dict['applications'] = application_count
					temp_dict['status'] = 'Open'
					temp_dict['phone'] = i.phone_number
					temp_dict['email'] = i.email
					overallscore = 0
					for j in CandidateMarks.objects.filter(candidate_id=i.candidate_id):
						avg_marks = (j.criteria_1_marks + j.criteria_2_marks + j.criteria_3_marks + j.criteria_4_marks + j.criteria_5_marks + j.criteria_6_marks + j.criteria_7_marks + j.criteria_8_marks) / 8
						overallscore = overallscore + avg_marks
					if application_count == 0 or CandidateMarks.objects.filter(candidate_id=i.candidate_id).count() == 0:
						temp_dict['overallscore'] = 0
					else:
						temp_dict['overallscore'] = round(overallscore / (application_count * CandidateMarks.objects.filter(candidate_id=i.candidate_id).count()), 2)
					data.append(temp_dict)
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class SearchCandidateView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			response = {}
			job_title = request.data.get('job_title')
			first_name = request.data.get("first_name")
			last_name = request.data.get("last_name")
			comp_target = request.data.get("comp_target")
			currency = request.data.get('currency')
			salary_range = request.data.get("salaryRange")
			location = request.data.get("location")
			offer_status = request.data.get("offer_status")
			hired_status = request.data.get("hired_status")
			pass_or_hold = request.data.get("pass_or_hold")
			thumbs_up = None
			thumbs_down = None
			golden_gloves = None
			if pass_or_hold == "like":
				thumbs_up = True
			elif pass_or_hold == "hold":
				thumbs_down = True
			elif pass_or_hold == "golen gloves":
				golden_gloves = True
			work_auth = request.data.get('work_auth')
			if request.user.profile.is_ca or request.user.profile.is_ch or request.user.profile.is_cto:
				try:
					queryset = Candidate.objects.filter(created_by_client=int(request.user.profile.client))
				except:
					queryset = Candidate.objects.all()
			else:
				queryset = Candidate.objects.all()
			if request.data.get("last_five_can"):
				queryset = queryset.order_by('-candidate_id')[0:5]
				candidate_data = CandidateSerializer(queryset, many=True).data
			else:
				if job_title:
					# candidate_ids = []
					# for op in OpenPosition.objects.filter(position_title__icontains=job_title):
					# 	for candidate in queryset:
					# 		if op.id in json.loads(candidate.associated_op_ids):
					# 			candidate_ids.append(candidate.candidate_id)
					queryset = queryset.filter(job_title__icontains=job_title)
				if first_name:
					queryset = queryset.filter(name__icontains=first_name)
				if last_name:
					queryset = queryset.filter(last_name__icontains=last_name)
				if comp_target:
					candidate_ids = []
					try:
						salary_list = comp_target.split(",")
						for query in queryset:
							try:
								query_salary_list = query.salaryRange.split(',')
								if salary_list[0] <= int(query_salary_list[0]) and salary_list[1] >= int(query_salary_list[1]):
									candidate_ids.append(query.candidate_id)
							except:
								pass
						queryset = queryset.filter(candidate_id__in=candidate_ids)
					except Exception as e:
						print(e)
				if salary_range:
					candidate_ids = []
					try:
						for query in queryset:
							try:
								query_salary_list = query.salaryRange.split(',')
								if salary_range[0] <= int(query_salary_list[0]) and salary_range[1] >= int(query_salary_list[1]):
									candidate_ids.append(query.candidate_id)
							except:
								candidate_ids.append(query.candidate_id)
						queryset = queryset.filter(candidate_id__in=candidate_ids)					
					except Exception as e:
						print(e)
				if currency:
					queryset = queryset.filter(currency=currency)
				if location:
					queryset = queryset.filter(location__icontains=location)
				if work_auth:
					queryset = queryset.filter(work_auth__icontains=work_auth)
				candidate_ids = []
				if hired_status:
					for query in queryset:
						if Hired.objects.filter(candidate_id=query.candidate_id).count() == 0:
							candidate_ids.append(query.candidate_id)
				if offer_status:
					for query in queryset:
						if Offered.objects.filter(candidate_id=query.candidate_id).count() == 0:
							candidate_ids.append(query.candidate_id)
				if hired_status or offer_status:
					queryset = queryset.filter(candidate_id__in=set(candidate_ids))
				if pass_or_hold:
					candidate_ids = []
					for candidate in queryset:
						if thumbs_up:
							if CandidateMarks.objects.filter(thumbs_up=thumbs_up) and candidate.candidate_id not in candidate_ids:
								candidate_ids.append(candidate.candidate_id)
						if thumbs_down:
							if CandidateMarks.objects.filter(thumbs_down=thumbs_down) and candidate.candidate_id not in candidate_ids:
								candidate_ids.append(candidate.candidate_id)
						if golden_gloves:
							if CandidateMarks.objects.filter(golden_gloves=golden_gloves) and candidate.candidate_id not in candidate_ids:
								candidate_ids.append(candidate.candidate_id)
					queryset = queryset.filter(candidate_id__in=candidate_ids)
				# Apply filters
				"""Exclude candidate old
				# exclude_withdrawn_candidate = request.data.get("exclude_withdrawn_candidate")
				# candidate_ids = []
				# if exclude_withdrawn_candidate:
				# 	for i in queryset:
				# 		print(i.name)
				# 		if WithdrawCandidateData.objects.filter(candidate=i):
				# 			pass
				# 		else:
				# 			candidate_ids.append(i.candidate_id)
				# 	queryset = queryset.filter(candidate_id__in=candidate_ids)
				"""
				if request.data.get("recentlyUpdated"):
					filter_time = datetime.now() - timedelta(hours=request.data.get("recentlyUpdated"))
					queryset = queryset.filter(updated_at__gte=filter_time)
				# apply  sorting
				candidate_data = CandidateSerializer(queryset, many=True).data
				sort_by = request.data.get("sortBy")
				if sort_by in ["like-htl", "like-lth", "pass-htl", "pass-lth"]:
					for  data in candidate_data:
						liked_counts = CandidateMarks.objects.filter(candidate_id=data["candidate_id"]).filter(Q(thumbs_up=True)|Q(golden_gloves=True)).count()
						pass_counts = CandidateMarks.objects.filter(candidate_id=data["candidate_id"], thumbs_down=True).count()
						data["liked_counts"] = liked_counts
						data["pass_counts"] = pass_counts
				if sort_by == "lu-nto":
					queryset = queryset.order_by(F('updated_at').desc(nulls_last=True))
					candidate_data = CandidateSerializer(queryset, many=True).data
				elif sort_by == "lu-otn":
					queryset = queryset.order_by('updated_at')
					candidate_data = CandidateSerializer(queryset, many=True).data
				elif sort_by == "comp-htl":
					queryset = queryset.order_by(F('salaryRange').desc(nulls_last=True))
					candidate_data = CandidateSerializer(queryset, many=True).data
				elif sort_by == "comp-lth":
					queryset = queryset.order_by('salaryRange')
					candidate_data = CandidateSerializer(queryset, many=True).data
				elif sort_by ==  "ls-nto":
					queryset = queryset.order_by(F('last_associated_at').desc(nulls_last=True))
					candidate_data = CandidateSerializer(queryset, many=True).data
				elif sort_by ==  "ls-otn":
					queryset = queryset.order_by('last_associated_at')
					candidate_data = CandidateSerializer(queryset, many=True).data
				elif sort_by ==  "like-htl":
					candidate_data = sorted(candidate_data, key=lambda i: i['liked_counts'], reverse=True)
				elif sort_by ==  "like-lth":
					candidate_data = sorted(candidate_data, key=lambda i: i['liked_counts'])
				elif sort_by ==  "pass-htl":
					candidate_data = sorted(candidate_data, key=lambda i: i['pass_counts'], reverse=True)
				elif sort_by ==  "pass-lth":
					candidate_data = sorted(candidate_data, key=lambda i: i['pass_counts'])
			# candidate_list = []
			# position_objs = OpenPosition.objects.filter(position_title__icontains=job_title)
			# for i in position_objs:
			# 	client_obj = Client.objects.get(id=i.client)
			# 	print("open position:", i)
			# 	print(candidate_name)
			# 	for j in Candidate.objects.filter(name__icontains=candidate_name):
			# 		if i.id in json.loads(j.associated_op_ids):
			# 			print("found candidate off this pos")
			# 			temp_dict = {}
			# 			if j.last_name == None or j.last_name == "Last Name":
			# 				temp_dict['name'] = j.name
			# 			else:
			# 				temp_dict['name'] = "{} {}".format(j.name, j.last_name)
			# 			temp_dict['candidate_id'] = j.candidate_id
			# 			temp_dict['phone'] = j.phone_number
			# 			temp_dict['email'] = j.email
			# 			temp_dict['op_id'] = i.id
			# 			temp_dict['job_title'] = i.position_title
			# 			temp_dict['date'] = i.final_round_completetion_date
			# 			temp_dict['client_id'] = i.client
			# 			temp_dict['client'] = client_obj.company_name
			# 			# temp_dict['profile_photo'] = j.profile_photo
			# 			if 'profile_pic_url' in j.linkedin_data and j.linkedin_data['profile_pic_url']:
			# 				temp_dict['profile_photo'] = j.linkedin_data['profile_pic_url']
			# 			else:
			# 				temp_dict['profile_photo'] = j.profile_photo
			# 			try:
			# 				candidate_status = CandidateStatus.objects.get(candidate_id=j.candidate_id)
			# 				temp_dict['shortlist_status'] = candidate_status.shortlist_status
			# 				temp_dict['make_offer_status'] = candidate_status.make_offer_status
			# 				temp_dict['finall_selection_status'] = candidate_status.finall_selection_status
			# 			except Exception as e:
			# 				print(e)
			# 				# response['status_error'] = str(e)
			# 				temp_dict['shortlist_status'] = False
			# 				temp_dict['make_offer_status'] = False
			# 				temp_dict['finall_selection_status'] = False
			# 			candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=j.candidate_id, op_id=i.id)
			# 			overallscore = 0
			# 			if candidate_marks_obj:
			# 				for k in CandidateMarks.objects.filter(candidate_id=j.candidate_id):
			# 					avg_marks = (k.criteria_1_marks + k.criteria_2_marks + k.criteria_3_marks + k.criteria_4_marks + k.criteria_5_marks + k.criteria_6_marks + k.criteria_7_marks + k.criteria_8_marks) / 8
			# 					overallscore = overallscore + avg_marks
			# 				temp_dict['overallscore'] = overallscore / candidate_marks_obj.count()
			# 			else:
			# 				temp_dict['overallscore'] = 0
			# 			thumbs_up = 0
			# 			thumbs_down = 0
			# 			hold = 0
			# 			for k in candidate_marks_obj:
			# 				if k.thumbs_up or k.golden_gloves:
			# 					thumbs_up = thumbs_up + 1
			# 				if k.thumbs_down:
			# 					thumbs_down = thumbs_down + 1
			# 				if k.hold:
			# 					hold = hold + 1
			# 			if voting in ['pass', 'offer', 'hold']:
			# 				if (thumbs_up >= thumbs_down) and (thumbs_up >= hold):
			# 					temp_dict['vote'] = 'Offer'
			# 					if voting == 'offer':
			# 						candidate_list.append(temp_dict)
			# 						continue
			# 				elif (thumbs_down >= thumbs_up) and (thumbs_down >= hold):
			# 					temp_dict['vote'] = 'Pass'
			# 					if voting == 'pass':
			# 						candidate_list.append(temp_dict)
			# 						continue
			# 				else:
			# 					temp_dict['vote'] = 'Hold'
			# 					if voting == 'hold':
			# 						candidate_list.append(temp_dict)
			# 						continue
			# 			else:
			# 				candidate_list.append(temp_dict)
			# remove_candidates = []
			# for i in candidate_list:
			# 	try:
			# 		candidate_status = CandidateStatus.objects.get(candidate_id=i['candidate_id'])
			# 	except Exception as e:
			# 		print(e)
			# 		continue
			# 	if shortlist_status is not None:
			# 		if (shortlist_status and candidate_status.shortlist_status) or (shortlist_status is False and candidate_status.shortlist_status is False):
			# 			pass
			# 		else:
			# 			try:
			# 				remove_candidates.append(i)
			# 			except:
			# 				pass
			# 	if offer_status is not None:
			# 		if (offer_status and candidate_status.offer_status) or (offer_status is False and candidate_status.offer_status is False):
			# 			pass
			# 		else:
			# 			try:
			# 				remove_candidates.append(i)
			# 			except:
			# 				pass
			# 	if final_selection is not None:
			# 		if (final_selection and candidate_status.final_selection) or (final_selection is False and candidate_status.final_selection is False):
			# 			pass
			# 		else:
			# 			try:
			# 				remove_candidates.append(i)
			# 			except:
			# 				pass
			# print(candidate_list)
			# for i in remove_candidates:
			# 	try:
			# 		candidate_list.remove(i)
			# 	except:
			# 		pass
			response['data'] = candidate_data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class EmployeeScheduleView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			htm_id = int(request.query_params.get('htm_id'))
			htm_availability_objs = HTMAvailability.objects.filter(htm_id=htm_id)
			if htm_availability_objs:
				response['msg'] = 'schedule found'
				avails = json.loads(htm_availability_objs[0].availability)
				avails.sort(key=lambda item:item['date'])
				show_shedule_data = []
				prev_date = None
				prev_time = None
				for avail in avails:
					avail_date = datetime.strptime(avail['date'], "%Y-%m-%d").date()
					if datetime.now().date().year <= avail_date.year and datetime.now().date().month <= avail_date.month and datetime.now().date().day <= avail_date.day:
						if prev_date == avail['date']:
							if prev_time == avail['hours'][0]['startTime']:
								last = show_shedule_data[-1]
								show_shedule_data.pop()
								last['hours'][0]['endTime'] = avail['hours'][0]['endTime']
								prev_time = avail['hours'][0]['endTime']
								show_shedule_data.append(last)
							else:
								show_shedule_data.append(avail)
						else:
							prev_date = avail['date']
							prev_time = avail['hours'][0]['endTime']
							show_shedule_data.append(avail)

					# if avail['date'] in show_shedule_data:
					# 	for i in avail['hours']:
					# 		show_shedule_data[avail['date']].append(i)
					# else:
					# 	show_shedule_data[avail['date']] = []
					# 	for i in avail['hours']:
					# 		show_shedule_data[avail['date']].append(i)
				show_shedule_data = sorted(show_shedule_data, key=lambda i: i['date'], reverse=True)
				response['scheduled_found'] = True
				response['schedule_data'] = show_shedule_data
				response['show_shedule_data'] = avails
			else:
				response['htm_id'] = htm_id
				response['msg'] = 'schedule not found'
				response['scheduled_found'] = False
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def post(self, request):
		response = {}
		try:
			htm_id = request.data.get('htm_id')
			days_availability = request.data.get('availableDays')
			new_availability = []
			for i in days_availability:
				temp_dict = [x for x in new_availability if x["date"] == i["date"]]
				if temp_dict:
					new_availability.remove(temp_dict[0])
					temp_dict = temp_dict[0]
				else:
					temp_dict = {}
					temp_dict["day"] = 1
					temp_dict["date"] = i["date"]
					temp_dict["hours"] = []
				for j in i["hours"]:
					lited_start = j["startTime"].split(":")
					start_hour = int(lited_start[0])
					start_min = int(lited_start[1])
					lited_end = j["endTime"].split(":")
					end_hour = int(lited_end[0])
					end_min = int(lited_end[1])
					run = True
					if start_hour > end_hour:
						return Response({"error": "Start hour can not be greater!"}, status=status.HTTP_400_BAD_REQUEST)
					while run:
						if start_hour == end_hour and start_min == end_min:
							run = False
						else:
							if start_min == 30:
								new_start_hour = start_hour + 1
								new_start_min = 0
							else:
								new_start_hour = start_hour
								new_start_min = 30
							temp_hours = {"startTime": "{}:{}".format(start_hour, start_min), "endTime": "{}:{}".format(new_start_hour, new_start_min),}
							if temp_hours not in temp_dict["hours"]:
								temp_dict["hours"].append(temp_hours)
							start_hour = new_start_hour
							start_min = new_start_min
				if temp_dict not in new_availability:
					new_availability.append(temp_dict)
				response['msg'] = 'Availability Updated'
			htm_availability_objs = HTMAvailability.objects.filter(htm_id=htm_id)
			if htm_availability_objs:
				htm_availability_obj = htm_availability_objs[0]
				htm_avail = json.loads(htm_availability_obj.availability)
				add_avails = []
				# # for avail in new_availability:
				# # 	# avail = json.loads(avail)
				# # 	avail["htm_created"] = True
				# # 	t_avail = avail
				# # 	avail["htm_created"] = False
				# # 	f_avail = avail
				# # 	del avail["htm_created"]
				# # 	n_avail = avail
				# # 	if t_avail in htm_avail or f_avail in htm_avail or n_avail in htm_avail:
				# # 		pass
				# # 	else:
				# # 		add_avails.append(avail)
				# htm_availability_obj.availability = json.dumps(htm_avail + add_avails)
				htm_availability_obj.availability = json.dumps(new_availability)
				htm_availability_obj.save()
				response['msg'] = 'schedule updated'
			else:
				HTMAvailability.objects.create(
					htm_id=htm_id,
					availability=json.dumps(new_availability)
				)
				response['msg'] = 'schedule added'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	# Schedule APIs using Flexbooker - Not used anymore
	def put(self, request):
		try:
			response = {}
			if request.user.profile.flexbooker_employee_id:
				employee_id = request.user.profile.flexbooker_employee_id
				available_days = request.data.get('availableDays')
				for i in available_days:
					try:
						del i["id"]
					except:
						pass
				schedule_id = request.data.get('schedule_id')
				print(schedule_id)
				update_response = update_schedule(employee_id, available_days, schedule_id)
				print(update_response)
				if schedule_id:
					response['msg'] = 'Schedule Updated'
				else:
					response['msg'] = 'Schedule Not Updated'
			else:
				response['msg'] = 'Employee Does not Exists'
				response['schedule_exists'] = False
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def delete(self, request):
		try:
			response = {}
			if request.user.profile.flexbooker_employee_id:
				schedule_id = int(request.query_params.get('schedule_id'))
				delete_response = delete_schedule(schedule_id)
				print(delete_response)
				if schedule_id:
					response['msg'] = 'Schedule Deleted'
					request.user.profile.flexbooker_schedule_id = 0
					request.user.profile.save()
				else:
					response['msg'] = 'Schedule Not Deleted'
			else:
				response['msg'] = 'Employee Does not Exists'
				response['schedule_exists'] = False
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetHiringMemberByOpId(APIView):
	def get(self, request, op_id):
		try:
			response = {}
			data = []
			openposition_obj = OpenPosition.objects.get(id=op_id)
			hiring_group_id = openposition_obj.hiring_group
			for i in HiringGroup.objects.filter(group_id=hiring_group_id):
				members_list = i.members_list.all()
				for profile in members_list:
					try:
						member_dict = {}
						member_dict['id'] = profile.id
						member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
						member_dict['email'] = profile.email
						data.append(member_dict)
					except Exception as e:
						pass
			response['msg'] = 'success'
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class SendMail(APIView):
	def post(self, request):
		try:
			response = {}
			email = request.data.get('email')
			recipient_list = [email, ]
			user = request.user.first_name + ' ' + request.user.last_name
			user_profile = Profile.objects.get(user=request.user)
			subject = user + ' - ' + request.data.get('subject')
			message = request.data.get('message')
			try:
				tasks.send.delay(subject, message, 'text', recipient_list, user_profile.email, user)
			except Exception as e:
				return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


# Schedule APIs using Flexbooker - Not used anymore
class SendInterviewSetMail(APIView):
	def post(self, request, op_id):
		try:
			response = {}
			htm_username = request.data.get('username')
			htm_obj = Profile.objects.get(user__username=htm_username)
			flexbooker_employee_id = htm_obj.flexbooker_employee_id
			candidates_mail = request.data.get('candididates_mail')
			try:
				openposition_obj = OpenPosition.objects.get(id=op_id)
			except Exception as e:
				response['error'] = str(e)
				response['msg'] = 'op does not exists'
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			try:
				client_obj = Client.objects.get(id=openposition_obj.client)
			except Exception as e:
				response = {}
				response['error'] = str(e)
				response['msg'] = 'client does not exists'
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			for i in candidates_mail:
				candidate_obj = Candidate.objects.get(email=i)
				email_from = settings.EMAIL_HOST_USER
				subject = 'Setup your Interview at Qorums'
				d = {
					"candidate_name": candidate_obj.name,
					"link": "https://a.flexbooker.com/widget/45f2a3ec-4564-4de4-8d1d-5ff06e2305f0/employee?employeeId=" + str(flexbooker_employee_id),
					"position_title": openposition_obj.position_title,
					"company": client_obj.company_name,
					"manager": "{} {}".format(client_obj.hr_first_name, client_obj.hr_last_name),
					"manager_contact": client_obj.hr_contact_phone_no,
					"manager_email": client_obj.hr_contact_email,
				}
				email_from = settings.EMAIL_HOST_USER
				recipient_list = [candidate_obj.email, ]
				# htmly_b = get_template('candidate_set_interview_mail.html')
				# text_content = ""
				# html_content = htmly_b.render(d)
				try:
					email_template = EmailTemplate.objects.get(client=client_obj, name="Interview Set Email for Candidate")
					template = Template(email_template.content)
					context = Context(d)
				except:
					email_template = EmailTemplate.objects.get(client=None, name="Interview Set Email for Candidate")
					template = Template(email_template.content)
					context = Context(d)
				html_content = template.render(context)
				cc = []
				try:
					profile = Profile.objects.get(user=request.user)
					cc = cc.append(profile.email)
				except:
					pass
				msg = EmailMultiAlternatives(subject, html_content, email_from, recipient_list, cc=cc)
				msg.attach_alternative(html_content, "text/html")
				try:
					msg.send(fail_silently=True)
					candidate_obj.interview_status = "Requested"
					candidate_obj.save()
				except Exception as e:
					print(e)
					pass
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


# Schedule APIs using Flexbooker - Not used anymore
class ReceiveWebhook(APIView):
	def post(self, request):
		try:
			response = {}
			webhook_data = request.data
			candidate_email = webhook_data['EmailAddresss']
			status = webhook_data['EventType']
			candidate_objs = Candidate.objects.filter(email=candidate_email)
			email = 'fightermoxly@gmail.com'
			subject = 'Webhook Received'
			message = str(webhook_data)
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [email, ]
			send_mail(subject, message, email_from, recipient_list)
			if candidate_objs:
				candidate_obj = candidate_objs[0]
				candidate_obj.interview_status = status
				candidate_obj.save()
				response['msg'] = 'success'
			else:
				response['msg'] = 'candidate not found'
				return Response(response, status=status.HTTP_200_OK)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class PositionProgress(APIView):
	def get(self, request, op_id):
		try:
			response = {}
			openposition_obj = OpenPosition.objects.get(id=op_id)
			progress_percent = 0
			candidates_obj = []
			# for i in Candidate.objects.all():
			# 	if op_id in json.loads(i.associated_op_ids):
			# 		candidates_obj.append(i)
			for cao in CandidateAssociateData.objects.filter(open_position=openposition_obj, accepted=True, withdrawed=False):
				candidates_obj.append(cao.candidate)
			hiring_group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
			members_list = hiring_group_obj.members_list.all()
			total_interviews = members_list.count() * len(candidates_obj)
			total_interviewsdone = CandidateMarks.objects.filter(op_id=op_id).count()
			progress_percent = int((total_interviewsdone / total_interviews) * 100)

			if datetime.now().date() > openposition_obj.target_deadline:
				response['deadline'] = 'On Schedule'
			else:
				response['deadline'] = 'Delayed'
			response['progress_percent'] = progress_percent
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class WidhrawCandidate(APIView):
	def post(self, request, op_id, candidate_id):
		try:
			response = {}
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			withdrawed_list = json.loads(candidate_obj.withdrawed_op_ids)
			associated_list = json.loads(candidate_obj.associated_op_ids)
			try:
				associated_list.remove(op_id)
			except:
				pass
			withdrawed_list.append(op_id)
			Hired.objects.filter(candidate_id=candidate_id, op_id=op_id).delete()
			Offered.objects.filter(candidate_id=candidate_id, op_id=op_id).delete()
			candidate_obj.withdrawed_op_ids = json.dumps(withdrawed_list)
			candidate_obj.associated_op_ids = json.dumps(associated_list)
			candidate_obj.save()
			openposition_obj = OpenPosition.objects.get(id=op_id)
			hiring_group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
			WithdrawCandidateData.objects.create(candidate=candidate_obj, open_position=openposition_obj)
			# update in candidate associate data 
			try:
				cad = CandidateAssociateData.objects.get(candidate=candidate_obj, open_position=openposition_obj)
				cad.withdrawed = True
				cad.save()
			except Exception as e:
				response['cad-error'] = str(e)
			# notitication to HM
			if hiring_group_obj.hod_profile:
				hm_profile_obj = hiring_group_obj.hod_profile
				tasks.send_app_notification.delay(hm_profile_obj.user.username, 'A candidate has been withdrawn from the {} opening.'.format(openposition_obj.position_title))
				tasks.push_notification.delay([hm_profile_obj.user.username], 'Qorums Notification', 'A candidate has been withdrawn from the {} opening.'.format(openposition_obj.position_title))
			# notification to HR
			if hiring_group_obj.hr_profile:
				hr_profile_obj = hiring_group_obj.hr_profile
				tasks.send_app_notification.delay(hr_profile_obj.user.username, 'A candidate has been withdrawn from the {} opening.'.format(openposition_obj.position_title))
				tasks.push_notification.delay([hr_profile_obj.user.username], 'Qorums Notification', 'A candidate has been withdrawn from the {} opening.'.format(openposition_obj.position_title))
			# notification to am
			client_obj = Client.objects.get(id=openposition_obj.client)
			tasks.send_app_notification.delay(client_obj.ae_assigned, 'A candidate has been withdrawn from the {} opening at {}'.format(openposition_obj.position_title, client_obj.company_name))
			tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'A candidate has been withdrawn from the {} opening at {}'.format(openposition_obj.position_title, client_obj.company_name))
			response['msg'] = 'Candidate Withdrawed'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class UnWidhrawCandidate(APIView):
	def post(self, request, op_id, candidate_id):
		try:
			response = {}
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			withdrawed_list = json.loads(candidate_obj.withdrawed_op_ids)
			associated_list = json.loads(candidate_obj.associated_op_ids)
			try:
				withdrawed_list.remove(op_id)
			except:
				pass
			associated_list.append(op_id)
			candidate_obj.withdrawed_op_ids = json.dumps(withdrawed_list)
			candidate_obj.associated_op_ids = json.dumps(associated_list)
			candidate_obj.save()
			WithdrawCandidateData.objects.filter(candidate=candidate_obj, open_position__id=op_id).delete()
			# update in candidate associate data 
			try:
				cad = CandidateAssociateData.objects.get(candidate=candidate_obj, open_position__id=op_id)
				cad.withdrawed = False
				cad.save()
			except Exception as e:
				response['cad-error'] = str(e)
			response['msg'] = 'Candidate Unwithdrawed'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class DeleteCandidate(APIView):
	def post(self, request, op_id, candidate_id):
		try:
			response = {}
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			associated_op_ids = json.loads(candidate_obj.associated_op_ids)
			try:
				associated_op_ids.remove(op_id)
			except:
				pass
			candidate_obj.associated_op_ids = json.dumps(associated_op_ids)
			openposition_obj = OpenPosition.objects.get(id=op_id)
			associated_client_ids = json.loads(candidate_obj.associated_client_ids)
			associated_client_ids.remove(openposition_obj.client)
			candidate_obj.associated_op_ids = json.dumps(associated_op_ids)
			# update in candidate associate data 
			try:
				cad = CandidateAssociateData.objects.filter(candidate=candidate_obj, open_position__id=op_id).delete()
			except Exception as e:
				response['cad-error'] = str(e)
			candidate_obj.save()
			response['msg'] = 'Candidate Deleted'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetOPbyClientID(APIView):
	def get(self, request, client_id):
		try:
			response = {}
			open_position_objs = OpenPosition.objects.filter(client=client_id)
			open_position_serializer = OpenPositionSerializer(open_position_objs, many=True)
			response['data'] = open_position_serializer.data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class AssociateHiringGroup(APIView):
	def post(self, request, op_id, group_id):
		try:
			response = {}
			open_position_obj = OpenPosition.objects.get(id=op_id)
			open_position_obj.hiring_group = group_id
			open_position_obj.save()
			CandidateMarks.objects.filter(op_id=op_id).delete()
			response['msg'] = 'updated'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def delete(self, request, op_id, group_id):
		try:
			response = {}
			open_position_obj = OpenPosition.objects.get(id=op_id)
			open_position_obj.hiring_group = 0
			open_position_obj.save()
			response['msg'] = 'removed'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class UpdateTNCStatus(APIView):
	def post(self, request, username):
		try:
			response = {}
			user = User.objects.get(username=username)
			user_profile = Profile.objects.get(user=user)
			if request.data.get('tnc_accepted'):
				user_profile.tnc_accepted = True
				user_profile.save()
			response['msg'] = 'updated'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


# Not used anymore
class GetZoomAuthURL(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			auth_url = "https://zoom.us/oauth/authorize?response_type=code&client_id=" + settings.ZOOM_CLIENT_ID + "&redirect_uri=" + "https://127.0.0.1:8000/dashboard-api/zoom-callback"
			response["auth_url"] = auth_url
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)



# Not used anymore
class CreateZoomMeeting(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			response = {}
			code = request.data.get('code')
			url = "https://zoom.us/oauth/token?code=" + code + "&grant_type=authorization_code&redirect_uri=" + "http://qorums.com/zoom-callback"
			headers = {'authorization': 'Basic ' + settings.ZOOM_ENCODE, 'content-type': 'application/x-www-form-urlencoded'}
			r = requests.post(
				url,
				headers=headers
			)
			print(r.text)
			token_data = json.loads(r.text)
			access_token = token_data['access_token']
			print('Creating Meeting')
			payload = "{\n    \"topic\": \"Meeting with Candidate\",\n    \"type\": 1,\n    \"agenda\": \"test\",\n    \"settings\": {\"host_video\": \"true\",\n                \"participant_video\": \"true\",\n                \"join_before_host\": \"False\",\n                \"mute_upon_entry\": \"False\",\n                \"watermark\": \"true\",\n                \"audio\": \"voip\",\n                \"auto_recording\": \"cloud\"\n                }\n}"
			meeting_url = "https://api.zoom.us/v2/users/me/meetings"
			meeting_header = {
			  'Authorization': 'Bearer ' + access_token,
			  'Content-Type': 'application/json',
			}
			meeting_response = requests.request("POST", meeting_url, headers=meeting_header, data=payload)
			response['msg'] = 'meeting created'
			response['metting_details'] = json.loads(meeting_response.text)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class DuplicateOpenPositionView(APIView):
	def post(self, request, op_id):
		response = {}
		if int(op_id) == int(settings.EXAMPLE_POSITION) and not request.user.is_superuser:
			response['msg'] = 'This position can not be cloned!'
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
		try:
			position_obj = OpenPosition.objects.get(id=op_id)
			position_obj.id = None
			position_obj.pk = None
			position_obj.save()
			position_obj.filled = False
			position_obj.filled_date = None
			position_obj.archieved = False
			position_obj.drafted = True
			position_obj.save()
			try:
				original_op = OpenPosition.objects.get(id=op_id)
				position_obj.copied_from = op_id
				position_obj.position_title = original_op.position_title + ' - (COPY)'
				position_obj.save()
			except Exception as e:
				print(e)
				response['msg'] = 'error'
				response['error'] = str(e)
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			response["id"] = position_obj.id
			""" Old Code
			if position_obj.copied_from == 0:
				position_obj.copied_from = op_id
				position_obj.save()
				count = OpenPosition.objects.filter(copied_from=op_id).count()
			else:
				position_obj.copied_from = position_obj.copied_from
				position_obj.save()
				count = OpenPosition.objects.filter(copied_from=position_obj.copied_from).count()
			# try:
			# 	original_op = OpenPosition.objects.get(id=position_obj.copied_from)
			# 	position_obj.position_title = original_op.position_title + ' (COPY)'
			# 	position_obj.save()
			# except Exception as e:
			# 	print(e)
			# 	response['msg'] = 'error'
			# 	response['error'] = str(e)
			# 	return Response(response, status=status.HTTP_400_BAD_REQUEST)
			"""
			# try:
			# 	opsc_obj = OpenPositionStageCompletion.objects.get(op_id=op_id)
			# 	opsc_obj.id = None
			# 	opsc_obj.pk = None
			# 	opsc_obj.save()
			# 	opsc_obj.op_id = position_obj.id
			# except Exception as e:
			# 	print(e)
			# candidates_objs = []
			# for i in Candidate.objects.all():
			# 	a_o_i_l = json.loads(i.associated_op_ids)
			# 	w_o_i_l = json.loads(i.withdrawed_op_ids)
			# 	if op_id in a_o_i_l:
			# 		a_o_i_l.append(int(position_obj.id))
			# 		i.associated_op_ids = json.dumps(a_o_i_l)
			# 		if op_id in w_o_i_l:
			# 			w_o_i_l.append(int(position_obj.id))
			# 			i.withdrawed_op_ids = json.dumps(w_o_i_l)
			# 		i.save()
			# for candidate_marks in CandidateMarks.objects.filter(op_id=op_id):
			# 	candidate_marks.id = None
			# 	candidate_marks.pk = None
			# 	candidate_marks.save()
			# 	candidate_marks.op_id = position_obj.id
			# 	candidate_marks.save()
			# for i in CandidatePositionDetails.objects.filter(op_id=op_id):
			# 	i.id = None
			# 	i.pk = None
			# 	i.save()
			# 	i.op_id = position_obj.id
			# 	i.save()
			response['msg'] = 'success'
			response['new_op_id'] = position_obj.id
			response['group_id'] = position_obj.hiring_group
			# hire_obj = Hired.objects.filter(op_id=op_id)
			# offer_obj = Offered.objects.filter(op_id=op_id)
			# response['hires'] = []
			# response['offered'] = []
			# for i in hire_obj:
			# 	Hired.objects.create(candidate_id=i.candidate_id, op_id=position_obj.id)
			# 	response['hires'].append(i.id)
			# for i in offer_obj:
			# 	Offered.objects.create(candidate_id=i.candidate_id, op_id=position_obj.id)
			# 	response['offered'].append(i.id)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			print(e)
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetNotificationsView(APIView):
	
	permission_classes = [IsAuthenticated]

	def get(self, request, op_id):
		try:
			position_obj = OpenPosition.objects.get(id=op_id)
			now = datetime.today().date()
			data = []
			ask_dict = {
				"open_position": position_obj.id,
				"date": str(datetime.now()).split('.')[0],
			}
			last_date = None
			temp_data = None
			for i in request.user.profile.notification_data:
				if i["open_position"] == position_obj.id:
					last_date = i["date"]
					temp_data = i
					break
			if temp_data:
				request.user.profile.notification_data.remove(temp_data)
			if last_date is None or datetime.strptime(last_date, "%Y-%m-%d %H:%M:%S") < datetime.now() - timedelta(days=2):
				try:
					# for step in json.loads(position_obj.stages):
					# 	date_obj = datetime.strptime(step['endDate'], "%m-%d-%Y").date()
					# 	delta = date_obj - now
					# 	if delta.days < 0 and step.get('completed', False) == False:
					# 		temp_dict = {}
					# 		temp_dict[step['label']] = True
					# 		temp_dict['Text'] = step['label']
					# 		data.append(temp_dict)
					

					delta = position_obj.target_deadline - now
					if delta.days < 0 and position_obj.target_deadline == False:
						temp_dict = {}
						temp_dict['Completion'] = True
						temp_dict['Text'] = 'Completion'
						data.append(temp_dict)
				except Exception as e:
					data.append(str(e))
				request.user.profile.notification_data.append(ask_dict) 
				request.user.profile.save()
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SaveResponseView(APIView):
	def post(self, request, op_id):
		position_obj = OpenPosition.objects.get(id=op_id)
		try:
			data = request.data
			label = None
			value = None
			for i in data:
				label = i
				value = data[i]
			steps_data = []
			executed = False
			for step in json.loads(position_obj.stages):
				if step['label'] == label:
					step['completed'] = value
					executed = True
				steps_data.append(step)
			if not executed:
				if label == 'Completion':
					position_obj.final_round_completetion_date_completed = True
			position_obj.stages = json.dumps(steps_data)
			position_obj.save()
		except Exception as e:
			return Response({'msg': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
		return Response({'msg': 'response updated'}, status=status.HTTP_200_OK)


class HireCandidateView(APIView):
	def post(self, request, op_id, candidate_id):
		response = {}
		try:
			openposition_obj = OpenPosition.objects.get(id=op_id)
			hire_objs = Hired.objects.filter(op_id=op_id)
			hiring_group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
			client_obj = Client.objects.get(id=openposition_obj.client)
			if openposition_obj.no_of_open_positions > hire_objs.count():
				hire_obj, created = Hired.objects.get_or_create(candidate_id=candidate_id, op_id=op_id)
				# send hired notitcation to CA
				try:
					tasks.send_app_notification.delay(client_obj.ae_assigned, 'A candidate has been marked for hire for the {} opening at {}'.format(openposition_obj.position_title, client_obj.company_name))
					tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'A candidate has been marked for hire for the {} opening at {}'.format(openposition_obj.position_title, client_obj.company_name))
					tasks.send_app_notification.delay(client_obj.key_username, 'A candidate has been marked for hire for the {} opening.'.format(openposition_obj.position_title))
					tasks.push_notification.delay([client_obj.key_username], 'Qorums Notification', 'A candidate has been marked for hire for the {} opening.'.format(openposition_obj.position_title))
					if hiring_group_obj.hr_profile:
						hr_profile = hiring_group_obj.hr_profile
						tasks.send_app_notification.delay(hr_profile.user.username, 'A candidate has been marked for hire for the {} opening.'.format(openposition_obj.position_title))
						tasks.push_notification.delay([hr_profile.user.username], 'Qorums Notification', 'A candidate has been marked for hire for the {} opening.'.format(openposition_obj.position_title))
				except Exception as e:
					response['notitication-error'] = str(e)
				response['msg'] = 'success'
			else:
				response['msg'] = 'maximum candidates exceed. fire one.'
			if openposition_obj.no_of_open_positions <= hire_objs.count():
				openposition_obj.filled = True
				openposition_obj.save()
				# send notifications
				try:
					client_obj = Client.objects.get(id=openposition_obj.client)
					tasks.send_app_notification.delay(client_obj.ae_assigned, 'The {} opening at {} has been filled'.format(openposition_obj.position_title, client_obj.company_name))
					tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'The {} opening at {} has been filled'.format(openposition_obj.position_title, client_obj.company_name))

					tasks.send_app_notification.delay(client_obj.key_username, 'The {} opening has been filled'.format(openposition_obj.position_title))
					tasks.push_notification.delay([client_obj.key_username], 'Qorums Notification', 'The {} opening has been filled'.format(openposition_obj.position_title))
					
					if hiring_group_obj.hod_profile:
						hod_profile = hiring_group_obj.hod_profile
						tasks.send_app_notification.delay(hod_profile.user.username, 'The {} opening has been filled'.format(openposition_obj.position_title))
						tasks.push_notification.delay([hod_profile.user.username], 'Qorums Notification', 'The {} opening has been filled'.format(openposition_obj.position_title))
					
					if hiring_group_obj.hr_profile:
						hr_profile = hiring_group_obj.hr_profile
						tasks.send_app_notification.delay(hr_profile.user.username, 'The {} opening has been filled'.format(openposition_obj.position_title))
						tasks.push_notification.delay([hr_profile.user.username], 'Qorums Notification', 'The {} opening has been filled'.format(openposition_obj.position_title))
				except Exception as e:
					response['notitication-error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def put(self, request, op_id, candidate_id):
		response = {}
		try:
			openposition_obj = OpenPosition.objects.get(id=op_id)
			hire_obj = Hired.objects.filter(candidate_id=candidate_id, op_id=op_id).delete()
			hire_objs = Hired.objects.filter(op_id=op_id)
			response['msg'] = 'success'
			if openposition_obj.no_of_open_positions <= hire_objs.count():
				openposition_obj.filled = True
				openposition_obj.save()
				# send notifications
				try:
					client_obj = Client.objects.get(id=openposition_obj.client)
					tasks.send_app_notification.delay(client_obj.ae_assigned, '{} filled!'.format(openposition_obj.position_title))
					tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', '{} filled!'.format(openposition_obj.position_title))

					tasks.send_app_notification.delay(client_obj.key_username, '{} filled!'.format(openposition_obj.position_title))
					tasks.push_notification.delay([client_obj.key_username], 'Qorums Notification', '{} filled!'.format(openposition_obj.position_title))

					hiring_group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
					
					if hiring_group_obj.hod_profile:
						hod_profile = hiring_group_obj.hod_profile
						tasks.send_app_notification.delay(hod_profile.user.username, '{} filled!'.format(openposition_obj.position_title))
						tasks.push_notification.delay([hod_profile.user.username], 'Qorums Notification', '{} filled!'.format(openposition_obj.position_title))
					
					if hiring_group_obj.hr_profile:
						hr_profile = hiring_group_obj.hr_profile
						tasks.send_app_notification.delay(hr_profile.user.username, '{} filled!'.format(openposition_obj.position_title))
						tasks.push_notification.delay([hr_profile.user.username], 'Qorums Notification', '{} filled!'.format(openposition_obj.position_title))
				except Exception as e:
					response['notitication-error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def get(self, request, op_id, candidate_id):
		response = {}
		try:
			hire_obj = Hired.objects.filter(candidate_id=candidate_id, op_id=op_id)
			if hire_obj:
				response['hired'] = 1
			else:
				hire_objs = Hired.objects.filter(op_id=op_id)
				openposition_obj = OpenPosition.objects.get(id=op_id)
				if openposition_obj.no_of_open_positions > hire_objs.count(): 
					response['hired'] = 2
				else:
					response['hired'] = 0
			response['msg'] = 'success'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetDashboardDataView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		response = {}
		try:
			user = request.user
			if "is_ae" in user.profile.roles:
				active_clients = Client.objects.filter(id__in=json.loads(user.profile.client)).order_by('-updated_at')
				clients_list = []
				clients_list_int = []
				for i in active_clients:
					if str(i.id) not in clients_list:
						clients_list.append(str(i.id))
					if i.id not in clients_list_int:
						clients_list_int.append(i.id)
				hiring_managers = Profile.objects.filter(roles__contains="is_htm", client__in=clients_list)
				open_positions = OpenPosition.objects.filter(client__in=clients_list_int, disabled=False, drafted=False, trashed=False)
				filled_positions = OpenPosition.objects.filter(client__in=clients_list_int, filled=True, drafted=False)
				active_candidates = []
				for i in Candidate.objects.all():
					candidate_clients = json.loads(i.associated_client_ids)
					if not set(candidate_clients).isdisjoint(clients_list_int):
						active_candidates.append(i)
				hiring_teams = HiringGroup.objects.filter(client_id__in=clients_list_int)
			else:
				active_clients = Client.objects.filter(disabled=False)
				hiring_managers = Profile.objects.filter(roles__contains="is_htm")
				open_positions = OpenPosition.objects.filter(disabled=False, drafted=False, trashed=False)
				filled_positions = OpenPosition.objects.filter(filled=True, drafted=False)
				active_candidates = Candidate.objects.all()
				hiring_teams = HiringGroup.objects.all()
			client_list = []
			for i in active_clients:
				client_list.append(i.id)
			on_scheduled_count = 0
			delayed_count = 0
			this_month_sc = 0
			this_month_c = 0
			prev_month_sc = 0
			prev_month_c = 0
			total_interviews = 0
			increased = False
			for openposition_obj in open_positions:
				group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
				candidates = 0
				# for candid in Candidate.objects.all():
				# 	if openposition_obj.id in json.loads(candid.associated_op_ids):
				# 		candidates += 1
				candidates = CandidateAssociateData.objects.filter(open_position=openposition_obj, accepted=True, withdrawed=False).count()
				member_list = group_obj.members_list.all()
				temp_total_interviews = (member_list.count() + 1) * candidates
				total_interviews = total_interviews + temp_total_interviews
				now = datetime.today().date()
				for step in json.loads(openposition_obj.stages):
					date_obj = datetime.strptime(step['endDate'], "%m-%d-%Y").date()
					delta = date_obj - now
					if delta.days < 0 and step.get('completed', False) == False:
						delayed_count = delayed_count + 1
						increased = True
						break
				if not increased:
					delta = openposition_obj.target_deadline - now
					if delta.days < 0 and openposition_obj.final_round_completetion_date_completed == False:
						delayed_count = delayed_count + 1
						increased = True
				if not increased:
					on_scheduled_count = on_scheduled_count + 1

				# Get scheduled and completed
				increased = False
				for step in json.loads(openposition_obj.stages):
					date_obj = datetime.strptime(step['endDate'], "%m-%d-%Y").date()
					if date_obj.year == now.year and date_obj.month == now.month:
						if step.get('completed', False) == False:
							this_month_sc = this_month_sc + 1
							increased = True
							break
						else:
							this_month_c = this_month_c + 1
							increased = True
							break
				if not increased:
					if openposition_obj.target_deadline.year == now.year and openposition_obj.target_deadline.month == now.month:
						if openposition_obj.final_round_completetion_date_completed == False:
							this_month_sc = this_month_sc + 1
							increased = True
						else:
							this_month_c = this_month_c + 1
							increased = True

				# Getting Next month counts
				increased = False
				for step in json.loads(openposition_obj.stages):
					date_obj = datetime.strptime(step['endDate'], "%m-%d-%Y").date()
					if date_obj.year == now.year and date_obj.month == now.month + 1:
						if step.get('completed', False) == False:
							tprev_month_sc = prev_month_sc + 1
							increased = True
							break
						else:
							prev_month_c = prev_month_c + 1
							increased = True
							break
				if not increased:
					if openposition_obj.target_deadline.year == now.year and openposition_obj.target_deadline.month == now.month + 1:
						if openposition_obj.final_round_completetion_date_completed == False:
							prev_month_sc = prev_month_sc + 1
							increased = True
						else:
							prev_month_c = prev_month_c + 1
							increased = True
				
			op_by_client = [['1', 0], ['2', 0], ['3', 0], ['4', 0], ['>5', 0]]
			
			clients_positions = []
			clients = []
			clients_hires = []
			
			for client in active_clients:
				op_count = OpenPosition.objects.filter(client=client.id, drafted=False, trashed=False).count()
				op_ids = OpenPosition.objects.filter(client=client.id, drafted=False, trashed=False).values_list('id')
				op_ids_list = [list(i)[0] for i in op_ids]
				hired_count = Hired.objects.filter(op_id__in=op_ids_list).count()
				clients_hires.append(hired_count)
				clients_positions.append(op_count)
				try:
					clients.append(client.logo.url if client.logo else None)
				except:
					clients.append(client.company_name)
				if op_count == 1:
					op_by_client[0][1] = op_by_client[0][1] + 1
				if op_count == 2:
					op_by_client[1][1] = op_by_client[1][1] + 1
				if op_count == 3:
					op_by_client[2][1] = op_by_client[2][1] + 1
				if op_count == 4:
					op_by_client[3][1] = op_by_client[3][1] + 1
				if op_count >=5:
					op_by_client[4][1] = op_by_client[4][1] + 1
			total_op_count = op_by_client[0][1] + op_by_client[1][1] + op_by_client[2][1] + op_by_client[3][1] + op_by_client[4][1]
			op_by_client[0][1] = op_by_client[0][1]/total_op_count * 100
			op_by_client[1][1] = op_by_client[1][1]/total_op_count * 100
			op_by_client[2][1] = op_by_client[2][1]/total_op_count * 100
			op_by_client[3][1] = op_by_client[3][1]/total_op_count * 100
			op_by_client[4][1] = op_by_client[4][1]/total_op_count * 100

			productive_clients_op = sorted(zip(clients_positions, clients), reverse=True)[:3]
			productive_clients_hires = sorted(zip(clients_hires, clients), reverse=True)[:3]
			
			current_voting = {}
			current_voting['thumbs_up'] = 0
			current_voting['thumbs_down'] = 0
			current_voting['hold'] = 0
			done_interviews = 0
			print(client_list)
			for marks_obj in CandidateMarks.objects.filter(client_id__in=client_list):
				if marks_obj.thumbs_up or marks_obj.golden_gloves:
					current_voting['thumbs_up'] = current_voting['thumbs_up'] + 1
				if marks_obj.thumbs_down:
					current_voting['thumbs_down'] = current_voting['thumbs_down'] + 1
				done_interviews += 1
			if current_voting['thumbs_up']:
				current_voting['thumbs_up'] = round((current_voting['thumbs_up'] / total_interviews) * 100, 1)
			else:
				current_voting['thumbs_up'] = 0
			if current_voting['thumbs_down']:
				current_voting['thumbs_down'] = round((current_voting['thumbs_down'] / total_interviews) * 100, 1)
			else:
				current_voting['thumbs_down'] = 0
			if total_interviews - done_interviews:
				current_voting['hold'] = round(((total_interviews - done_interviews) / total_interviews) * 100, 1)
			else:
				current_voting['hold'] = 0
			response['productive_clients_op'] = productive_clients_op
			response['productive_clients_hires'] = productive_clients_hires
			response['current_voting'] = current_voting
			response['op_by_client'] = op_by_client
			response['active_clients'] = active_clients.count()
			response['hiring_managers'] = hiring_managers.count()
			response['open_positions'] = open_positions.count()
			response['filled_positions'] = filled_positions.count()
			response['active_candidates'] = len(active_candidates)
			response['hiring_teams'] = hiring_teams.count()
			response['on_scheduled_count'] = active_clients.count()
			response['delayed_count'] = active_clients.count()
			response['this_month_sc'] = this_month_sc
			response['this_month_c'] = this_month_c
			response['prev_month_sc'] = prev_month_sc
			response['prev_month_c'] = prev_month_c
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class ClientAdminDashboardView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		response ={}
		try:
			if request.user.profile.is_ca or request.user.profile.is_sm:
				client = int(json.loads(request.user.profile.client))
				open_positions = OpenPosition.objects.filter(client=client, filled=False, drafted=False, trashed=False)
				position_in_process  = open_positions.count()
				hiring_teams_id = []
				on_scheduled_count = 0
				delayed_count = 0
				position_filled =  []
				candidate_pipeline = []
				htm_performace = []
				for openposition_obj in OpenPosition.objects.filter(client=client, drafted=False, trashed=False):
					print(openposition_obj)
					last_month = datetime.today() - timedelta(days=30)
					hired_in_30 = Hired.objects.filter(created__gte=last_month, op_id=openposition_obj.id).count()
					if hired_in_30:
						temp_dict = {}
						temp_dict['op_name'] = openposition_obj.position_title
						hired = Hired.objects.filter(op_id=openposition_obj.id).count()
						temp_dict['hired'] = hired
						temp_dict['open'] = openposition_obj.no_of_open_positions - hired
						position_filled.append(temp_dict)
				for openposition_obj in open_positions:
					pipeline_dict = {}
					on_time = True
					now = datetime.today().date()
					for step in json.loads(openposition_obj.stages):
						date_obj = datetime.strptime(step['endDate'], "%m-%d-%Y").date()
						delta = date_obj - now
						if delta.days < 0 and step.get('completed', False) == False and on_time:
							on_time = False
							break
					delta = openposition_obj.target_deadline - now
					if delta.days < 0 and openposition_obj.final_round_completetion_date_completed == False and on_time:
						on_time = False
					if on_time:
						pass
					else:
						candidates_obj = []
						# for k in Candidate.objects.all():
						# 	if openposition_obj.id in json.loads(k.associated_op_ids):
						# 		candidates_obj.append(k)
						for cao in CandidateAssociateData.objects.filter(open_position=openposition_obj, accepted=True, withdrawed=False):
							candidates_obj.append(cao.candidate)
						length_of_candidates = len(candidates_obj)
						if candidates_obj:
							group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
							group_members = list(group_obj.members_list.all().values_list("id", flat=True))
							for member_id in group_members:
								candidate_marks_count = CandidateMarks.objects.filter(op_id=openposition_obj.id, marks_given_by=str(member_id)).count()
								temp_dict = {
									"member_id": None,
									"counts": 0,
									"member_name": None,
								}
								try:
									temp_dict = next(item for item in htm_performace if item["member_id"] == str(member_id))
									index_of_item = htm_performace.index(temp_dict)
									htm_performace[index_of_item]["counts"] = htm_performace[index_of_item]["counts"] + (length_of_candidates - candidate_marks_count)
								except Exception as e:
									temp_dict["member_id"] = str(member_id)
									temp_dict["counts"] = (length_of_candidates - candidate_marks_count)
									try:
										profile_obj = Profile.objects.get(id=member_id)
										temp_dict["member_name"] = profile_obj.user.first_name
									except:
										temp_dict["member_name"] = "None"
									htm_performace.append(temp_dict)
						else:
							pass
					pipeline_dict['on_scheduled'] = on_time
					pipeline_dict['op_name'] = openposition_obj.position_title
					candidates_obj = []
					# for k in Candidate.objects.all():
					# 	if openposition_obj.id in json.loads(k.associated_op_ids):
					# 		candidates_obj.append(k)
					for cao in CandidateAssociateData.objects.filter(open_position=openposition_obj, accepted=True, withdrawed=False):
						candidates_obj.append(cao.candidate)
					pipeline_dict['total_candidates'] = len(candidates_obj)
					hired_count = Hired.objects.filter(op_id=openposition_obj.id).count()
					pipeline_dict['position_filled'] = hired_count
					pipeline_dict['position_remaing'] = openposition_obj.no_of_open_positions - hired_count
					pipeline_dict['likes_count'] = CandidateMarks.objects.filter(op_id=openposition_obj.id, thumbs_up=True).count()
					pipeline_dict['pass_count'] = CandidateMarks.objects.filter(op_id=openposition_obj.id, thumbs_down=True).count()
					candidate_pipeline.append(pipeline_dict)
					if openposition_obj.hiring_group in hiring_teams_id:
						pass
					else:
						hiring_teams_id.append(openposition_obj.hiring_group)
					increased = False
					for step in json.loads(openposition_obj.stages):
						date_obj = datetime.strptime(step['endDate'], "%m-%d-%Y").date()
						delta = date_obj - now
						if delta.days < 0 and step.get('completed', False) == False:
							delayed_count = delayed_count + 1
							increased = True
							break
						delta = openposition_obj.target_deadline - now
						if delta.days < 0 and openposition_obj.final_round_completetion_date_completed == False and on_time:
							delayed_count = delayed_count + 1
							increased = True		
						
					if not increased:
						on_scheduled_count = on_scheduled_count + 1

				hiring_groups = HiringGroup.objects.filter(client_id=client)
				hiring_group_load = []
				for i in hiring_groups:
					temp_dict = {}
					temp_dict['hiring_team_name'] = i.name
					temp_dict['load'] = OpenPosition.objects.filter(hiring_group=i.group_id, filled=False, drafted=False, trashed=False).count()
					hiring_group_load.append(temp_dict)
				print(hiring_teams_id, on_scheduled_count, delayed_count, position_in_process)
				rounds = {
					"1": [],
					"2": [],
					"3": [],
					"4": [],
				}
				for openposition_obj in OpenPosition.objects.filter(client=client, drafted=False, trashed=False):
					rounds_qs = OpenPosition.objects.filter(copied_from=openposition_obj.id, drafted=False, trashed=False)
					if rounds_qs.count() == 1:
						for qs in rounds_qs:
							rounds["2"].append(qs.position_title)
					elif rounds_qs.count() == 2:
						for qs in rounds_qs:
							rounds["3"].append(qs.position_title)
					elif rounds_qs.count() == 3:
						for qs in rounds_qs:
							rounds["4"].append(qs.position_title)
				response['position_in_process'] = position_in_process
				response['on_scheduled_count'] = on_scheduled_count
				response['delayed_count'] = delayed_count
				response['hiring_teams_count'] = len(hiring_teams_id)
				response['position_filled'] = position_filled
				response['hiring_group_load'] = hiring_group_load
				response['rounds'] = rounds
				response['candidate_pipeline'] = candidate_pipeline
				response['htm_performace'] = htm_performace
				return Response(response, status=status.HTTP_200_OK)
			elif HiringGroup.objects.filter(hod_profile=request.user.profile):
				hod_of_groups = []
				for i in HiringGroup.objects.filter(hod_profile=request.user.profile):
					hod_of_groups.append(i.group_id)
				open_positions = OpenPosition.objects.filter(hiring_group__in=hod_of_groups, drafted=False, trashed=False)
				position_in_process  = open_positions.count()
				hiring_teams_id = []
				on_scheduled_count = 0
				delayed_count = 0
				position_filled =  []
				candidate_pipeline = []
				htm_performace = []
				for openposition_obj in OpenPosition.objects.filter(hiring_group__in=hod_of_groups, drafted=False, trashed=False):
					print(openposition_obj)
					now = datetime.today().date()
					if openposition_obj.filled and openposition_obj.filled_date.year == now.year and openposition_obj.filled_date.month == now.month:
						temp_dict = {}
						temp_dict['op_name'] = openposition_obj.position_title
						hired = Hired.objects.filter(op_id=openposition_obj.id).count()
						temp_dict['hired'] = hired
						temp_dict['open'] = openposition_obj.no_of_open_positions - hired
						position_filled.append(temp_dict)
				for openposition_obj in open_positions:
					# Candidate Pipeline
					pipeline_dict = {}
					on_time = True
					now = datetime.today().date()
					for step in json.loads(openposition_obj.stages):
						date_obj = datetime.strptime(step['endDate'], "%m-%d-%Y").date()
						delta = date_obj - now
						if delta.days < 0 and step.get('completed', False) == False and on_time:
							on_time = False
							break
					delta = openposition_obj.target_deadline - now
					if delta.days < 0 and openposition_obj.final_round_completetion_date_completed == False and on_time:
						on_time = False				
					if on_time:
						pass
					else:
						candidates_obj = []
						# for k in Candidate.objects.all():
						# 	if openposition_obj.id in json.loads(k.associated_op_ids):
						# 		candidates_obj.append(k)
						for cao in CandidateAssociateData.objects.filter(open_position=openposition_obj, accepted=True, withdrawed=False):
							candidates_obj.append(cao.candidate)
						length_of_candidates = len(candidates_obj)
						if candidates_obj:
							group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
							group_members = list(group_obj.members_list.all().values_list("id", flat=True))
							for member_id in group_members:
								candidate_marks_count = CandidateMarks.objects.filter(op_id=openposition_obj.id, marks_given_by=member_id).count()
								temp_dict = {
									"member_id": None,
									"counts": 0,
									"member_name": None,
								}
								try:
									temp_dict = next(item for item in htm_performace if item["member_id"] == str(member_id))
									index_of_item = htm_performace.index(temp_dict)
									htm_performace[index_of_item]["counts"] = htm_performace[index_of_item]["counts"] + (length_of_candidates - candidate_marks_count)
								except Exception as e:
									temp_dict["member_id"] = str(member_id)
									temp_dict["counts"] = (length_of_candidates - candidate_marks_count)
									try:
										profile_obj = Profile.objects.get(id=member_id)
										temp_dict["member_name"] = profile_obj.user.first_name
									except:
										temp_dict["member_name"] = "None"
									htm_performace.append(temp_dict)
						else:
							pass
					pipeline_dict['on_scheduled'] = on_time
					pipeline_dict['op_name'] = openposition_obj.position_title
					candidates_obj = []
					# for k in Candidate.objects.all():
					# 	if openposition_obj.id in json.loads(k.associated_op_ids):
					# 		candidates_obj.append(k)
					for cao in CandidateAssociateData.objects.filter(open_position=openposition_obj, accepted=True, withdrawed=False):
							candidates_obj.append(cao.candidate)
					pipeline_dict['total_candidates'] = len(candidates_obj)
					hired_count = Hired.objects.filter(op_id=openposition_obj.id).count()
					pipeline_dict['position_filled'] = hired_count
					pipeline_dict['position_remaing'] = openposition_obj.no_of_open_positions - hired_count
					pipeline_dict['likes_count'] = CandidateMarks.objects.filter(op_id=openposition_obj.id, thumbs_up=True).count()
					pipeline_dict['pass_count'] = CandidateMarks.objects.filter(op_id=openposition_obj.id, thumbs_down=True).count()
					candidate_pipeline.append(pipeline_dict)
					if openposition_obj.hiring_group in hiring_teams_id:
						pass
					else:
						hiring_teams_id.append(openposition_obj.hiring_group)
					increased = False
					for step in json.loads(openposition_obj.stages):
						date_obj = datetime.strptime(step['endDate'], "%m-%d-%Y").date()
						delta = date_obj - now
						if delta.days < 0 and step.get('completed', False) == False:
							delayed_count = delayed_count + 1
							increased = True
							break
						delta = openposition_obj.target_deadline - now
						if delta.days < 0 and openposition_obj.final_round_completetion_date_completed == False and on_time:
							delayed_count = delayed_count + 1
							increased = True

					delta = openposition_obj.target_deadline - now
					if delta.days < 0 and openposition_obj.final_round_completetion_date_completed == False:
						delayed_count = delayed_count + 1
						increased = True
						continue
					if not increased:
						on_scheduled_count = on_scheduled_count + 1

				hiring_groups = HiringGroup.objects.filter(hod_profile=request.user.profile)
				hiring_group_load = []
				for i in hiring_groups:
					temp_dict = {}
					temp_dict['hiring_team_name'] = i.name
					temp_dict['load'] = OpenPosition.objects.filter(hiring_group=i.group_id, filled=False, drafted=False, trashed=False).count()
					hiring_group_load.append(temp_dict)
				rounds = {
					"1": [],
					"2": [],
					"3": [],
					"4": [],
				}
				for openposition_obj in OpenPosition.objects.filter(hiring_group__in=hod_of_groups, drafted=False, trashed=False):
					rounds_qs = OpenPosition.objects.filter(copied_from=openposition_obj.id)
					if rounds_qs.count() == 1:
						for qs in rounds_qs:
							rounds["2"].append(qs.position_title)
					elif rounds_qs.count() == 2:
						for qs in rounds_qs:
							rounds["3"].append(qs.position_title)
					elif rounds_qs.count() == 3:
						for qs in rounds_qs:
							rounds["4"].append(qs.position_title)
				response['position_in_process'] = position_in_process
				response['on_scheduled_count'] = on_scheduled_count
				response['delayed_count'] = delayed_count
				response['hiring_teams_count'] = len(hiring_teams_id)
				response['position_filled'] = position_filled
				response['hiring_group_load'] = hiring_group_load
				response['rounds'] = rounds
				response['candidate_pipeline'] = candidate_pipeline
				response['htm_performace'] = htm_performace
				return Response(response, status=status.HTTP_200_OK)
			else:
				response['msg'] = "Unauthorize Access"
				return Response(response, status=status.HTTP_401_UNAUTHORIZED)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class WithdrawHiringMemberView(APIView):
	def post(self, request, op_id, member_id):
		try:
			response = {}
			openposition_obj = OpenPosition.objects.get(id=op_id)
			current_withdrawed_members = json.loads(openposition_obj.withdrawed_members)
			if member_id in current_withdrawed_members:
				pass
			else:
				current_withdrawed_members.append(member_id)
			openposition_obj.withdrawed_members = json.dumps(current_withdrawed_members)
			openposition_obj.save()
			response['msg'] = 'Member Withdrawed'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class RestoreHiringMemberView(APIView):
	def post(self, request, op_id, member_id ):
		try:
			response = {}
			openposition_obj = OpenPosition.objects.get(id=op_id)
			current_withdrawed_members = json.loads(openposition_obj.withdrawed_members)
			if member_id in current_withdrawed_members:
				current_withdrawed_members.remove(member_id)
			openposition_obj.withdrawed_members = json.dumps(current_withdrawed_members)
			openposition_obj.save()

			response['msg'] = 'Member Restored'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


# Open Position Template view
class ScheduleTemplateView(APIView):
	def get(self, request):
		# try:
		response = {}
		template_id = request.query_params.get('id')
		template_obj = ScheduleTemplate.objects.get(id=template_id)
		today = datetime.today().date()
		prev_count = 1

		response['msg'] = 'success'
		response['kickoff_text'] = template_obj.step_1_label
		if today.weekday() == 5:
			response['kickoff_start_date'] = today + timedelta(days=2)
			today = today + timedelta(days=2)
		elif today.weekday() == 6:
			response['kickoff_start_date'] = today + timedelta(days=1)
			today = today + timedelta(days=1)
		else:
			response['kickoff_start_date'] = today


		delta = timedelta(days=1)
		# last_date += delta
		next_day = today
		steps_data = []
		weekend = set([5, 6])
		last_date = today
		for step in json.loads(template_obj.steps):
			temp_dict = {}
			temp_dict['label'] = step['label']
			start_count = int(step['startDate'])
			if prev_count > start_count:
				prev_count = start_count - 1
				last_date -= timedelta(days=start_count-prev_count+1)
			step_date = last_date
			for i in range(prev_count, start_count):
				step_date = step_date + delta
				while step_date.weekday() in weekend:
					step_date += delta
			temp_dict['startDate'] = step_date

			prev_count = start_count
			end_count = int(step['endDate'])
			end_date = step_date
			for i in range(prev_count, end_count):
				end_date = end_date + delta
				while end_date.weekday() in weekend:
					end_date += delta
			temp_dict['endDate'] = end_date
			last_date = end_date
			prev_count = end_count

			steps_data.append(temp_dict)

		response['stages'] = steps_data
		step_8_date = last_date
		for i in range(prev_count, template_obj.step_8_end):
			step_8_date = step_8_date + delta
			while step_8_date.weekday() in weekend:
				step_8_date += delta

		response['final_round_completetion_date'] = step_8_date
		return Response(response, status=status.HTTP_200_OK)
		# except Exception as e:
		# 	return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def post(self, request):
		try:
			response = {}
			count = 0
			kickoff_start_date = datetime.strptime(request.data.get('kickoff_start_date'), '%Y-%m-%d')
			if kickoff_start_date.weekday() == 5:
				response['kickoff_start_date'] = kickoff_start_date + timedelta(days=2)
				kickoff_start_date = kickoff_start_date + timedelta(days=2)
			elif kickoff_start_date.weekday() == 6:
				response['kickoff_start_date'] = kickoff_start_date + timedelta(days=1)
				kickoff_start_date = kickoff_start_date + timedelta(days=1)
			else:
				response['kickoff_start_date'] = kickoff_start_date
			step_1_start = 1
			step_1_end = 1
			step_1_label = request.data.get('kickoff_text')
			steps = request.data.get('stages')

			prev_count = 1
			last_date = kickoff_start_date
			delta = timedelta(days=1)
			last_date += delta
			steps_data = []
			for step in steps:
				temp_dict = {}
				step_start_date = datetime.strptime(step['startDate'], '%m-%d-%Y')
				step_end_date = datetime.strptime(step['endDate'], '%m-%d-%Y')
				if last_date > step_start_date:
					t_d = last_date - step_start_date
					prev_count = prev_count - t_d.days
					last_date -= timedelta(days=t_d.days)
					# return Response({'msg': 'Start date should be greater than the previous stage end date.'}, status=status.HTTP_400_BAD_REQUEST)
				step_lable = step['label']
				weekend = set([5, 6])
				
				while last_date <= step_start_date:
					if last_date.weekday() not in weekend:
						prev_count += 1
					last_date += delta
				temp_dict['startDate'] = prev_count

				while last_date <= step_end_date:
					if last_date.weekday() not in weekend:
						prev_count += 1
					last_date += delta

				temp_dict['endDate'] = prev_count
				temp_dict['label'] = step_lable

				steps_data.append(temp_dict)
				print(temp_dict)

			final_round_completetion_date = datetime.strptime(request.data.get('final_round_completetion_date'), '%Y-%m-%d')
			print(prev_count)
			if last_date > final_round_completetion_date:
				if last_date > step_start_date:
					t_d = last_date - step_start_date
					prev_count = prev_count - t_d.days
					print(prev_count, '(***)')
					last_date -= timedelta(days=t_d.days)
					# return Response({'msg': 'Start date should be greater than the previous stage end date.'}, status=status.HTTP_400_BAD_REQUEST)

			while last_date <= final_round_completetion_date:
				if last_date.weekday() not in weekend:
					prev_count += 1
				last_date += delta

			step_8_end = prev_count
			try:
				client = int(request.user.profile.client)
			except:
				client = 0
			data = {
				'template_name': request.data.get('template_name'),
				'step_1_label': step_1_label,
				'step_1_start': step_1_start,
				'step_1_end': step_1_end,
				'steps': json.dumps(steps_data),
				'step_8_end': step_8_end,
				'client': client
			}
			schdule_template_serializer = ScheduleTemplateSerializer(data=data)
			if schdule_template_serializer.is_valid():
				schdule_template_serializer.save()
			else:
				return Response({'error': schdule_template_serializer.errors, 'data': data}, status=status.HTTP_400_BAD_REQUEST)
			response["msg"] = 'added'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


	def put(self, request):
		try:
			template_obj = ScheduleTemplate.objects.get(id=request.data.get('template_id'))
			response = {}
			count = 0
			kickoff_start_date = datetime.strptime(request.data.get('kickoff_start_date'), '%Y-%m-%d')
			if kickoff_start_date.weekday() == 5:
				response['kickoff_start_date'] = kickoff_start_date + timedelta(days=2)
				kickoff_start_date = kickoff_start_date + timedelta(days=2)
			elif kickoff_start_date.weekday() == 6:
				response['kickoff_start_date'] = kickoff_start_date + timedelta(days=1)
				kickoff_start_date = kickoff_start_date + timedelta(days=1)
			else:
				response['kickoff_start_date'] = kickoff_start_date
			step_1_start = 1
			step_1_end = 1
			step_1_label = request.data.get('kickoff_text')
			steps = request.data.get('stages')

			prev_count = 1
			last_date = kickoff_start_date
			delta = timedelta(days=1)
			last_date += delta
			steps_data = []
			for step in steps:
				temp_dict = {}
				step_start_date = datetime.strptime(step['startDate'], '%m-%d-%Y')
				step_end_date = datetime.strptime(step['endDate'], '%m-%d-%Y')
				if last_date > step_start_date:
					return Response({'msg': 'Start date should be greater than the previous stage end date.'}, status=status.HTTP_400_BAD_REQUEST)
				step_lable = step['label']
				weekend = set([5, 6])
				
				while last_date <= step_start_date:
					if last_date.weekday() not in weekend:
						prev_count += 1
					last_date += delta
				temp_dict['startDate'] = prev_count

				while last_date <= step_end_date:
					if last_date.weekday() not in weekend:
						prev_count += 1
					last_date += delta

				temp_dict['endDate'] = prev_count
				temp_dict['label'] = step_lable

				steps_data.append(temp_dict)

			final_round_completetion_date = datetime.strptime(request.data.get('final_round_completetion_date'), '%Y-%m-%d')

			if last_date > final_round_completetion_date:
					return Response({'msg': 'Start date should be greater than the previous stage end date.'}, status=status.HTTP_400_BAD_REQUEST)

			while last_date <= final_round_completetion_date:
				if last_date.weekday() not in weekend:
					prev_count += 1
				last_date += delta

			step_8_end = prev_count
			try:
				client = int(request.user.profile.client)
			except:
				client = 0
			data = {
				'step_1_label': step_1_label,
				'step_1_start': step_1_start,
				'step_1_end': step_1_end,
				'steps': json.dumps(steps_data),
				'step_8_end': step_8_end,
				'client': client
			}
			schdule_template_serializer = ScheduleTemplateSerializer(template_obj, data=data, partial=True)
			if schdule_template_serializer.is_valid():
				schdule_template_serializer.save()
			else:
				return Response({'error': schdule_template_serializer.errors, 'data': data}, status=status.HTTP_400_BAD_REQUEST)
			response["msg"] = 'updated'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request):
		try:
			id = request.query_params.get('id')
			st_obj = ScheduleTemplate.objects.get(id=id)
			st_obj.delete()
			response = {}
			response["msg"] = "deleted"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AllScheduleTemplateView(APIView):
	def get(self, request):
		try:
			response = {}
			try:
				template_objs = ScheduleTemplate.objects.filter(client=int(request.user.profile.client))
			except:
				template_objs = ScheduleTemplate.objects.all()
			schdule_template_serializer = ScheduleTemplateSerializer(template_objs, many=True)
			response['msg'] = 'success'
			response['data'] = schdule_template_serializer.data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HTMWeightageView(APIView):
	def get(self, request, op_id, htm_id):
		try:
			response = {}
			openposition_obj = OpenPosition.objects.get(id=op_id)
			htm_weightage_objs = HTMWeightage.objects.filter(op_id=op_id, htm_id=htm_id)
			if htm_weightage_objs:
				htm_weightage_obj = htm_weightage_objs[0]
				htm_weightage_serializer = HTMWeightageSerializer(htm_weightage_obj)
				response['data'] = htm_weightage_serializer.data
				response['data']['init_qualify_ques_1'] = openposition_obj.init_qualify_ques_1
				response['data']['init_qualify_ques_2'] = openposition_obj.init_qualify_ques_2
				response['data']['init_qualify_ques_3'] = openposition_obj.init_qualify_ques_3
				response['data']['init_qualify_ques_4'] = openposition_obj.init_qualify_ques_4
				response['data']['init_qualify_ques_5'] = openposition_obj.init_qualify_ques_5
				response['data']['init_qualify_ques_6'] = openposition_obj.init_qualify_ques_6
				response['data']['init_qualify_ques_7'] = openposition_obj.init_qualify_ques_7
				response['data']['init_qualify_ques_8'] = openposition_obj.init_qualify_ques_8
				response['msg'] = 'success'
			else:
				response['data'] = {}
				response['data']['init_qualify_ques_1'] = openposition_obj.init_qualify_ques_1
				response['data']['init_qualify_ques_2'] = openposition_obj.init_qualify_ques_2
				response['data']['init_qualify_ques_3'] = openposition_obj.init_qualify_ques_3
				response['data']['init_qualify_ques_4'] = openposition_obj.init_qualify_ques_4
				response['data']['init_qualify_ques_5'] = openposition_obj.init_qualify_ques_5
				response['data']['init_qualify_ques_6'] = openposition_obj.init_qualify_ques_6
				response['data']['init_qualify_ques_7'] = openposition_obj.init_qualify_ques_7
				response['data']['init_qualify_ques_8'] = openposition_obj.init_qualify_ques_8
				response['data']['init_qualify_ques_1_weightage'] = 10
				response['data']['init_qualify_ques_2_weightage'] = 10
				response['data']['init_qualify_ques_3_weightage'] = 10
				response['data']['init_qualify_ques_4_weightage'] = 10
				response['data']['init_qualify_ques_5_weightage'] = 10
				response['data']['init_qualify_ques_6_weightage'] = 10
				response['data']['init_qualify_ques_7_weightage'] = 10
				response['data']['init_qualify_ques_8_weightage'] = 10
				response['msg'] = 'Weightage Not Found'
			# Add hiring member data
			try:
				profile_obj = Profile.objects.get(id=htm_id)
				response["name"] = profile_obj.user.get_full_name()
				response["job_title"] = profile_obj.job_title
				response["phone"] = profile_obj.phone_number
				response["email"] = profile_obj.email
				response["roles"] = profile_obj.roles
				response["photo"] = profile_obj.profile_photo
			except Exception as e:
				response = {}
				response["msg"] = "Hiring Member data not found!"
				response["error"] = str(e)
				return Response(response)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


	def put(self, request, op_id, htm_id):
		try:
			response = {}
			htm_weightage_objs = HTMWeightage.objects.filter(op_id=op_id, htm_id=htm_id)
			if htm_weightage_objs:
				htm_weightage_obj = htm_weightage_objs[0]
				htm_weightage_serializer = HTMWeightageSerializer(htm_weightage_obj, data=request.data)
				if htm_weightage_serializer.is_valid():
					htm_weightage_serializer.save()
					response['data'] = htm_weightage_serializer.data
					response['msg'] = 'updated'
				else:
					response['msg'] = 'error'
					response['error'] = htm_weightage_serializer.errors
					return Response(response, status=status.HTTP_400_BAD_REQUEST)
			else:
				htm_weightage_serializer = HTMWeightageSerializer(data=request.data)
				if htm_weightage_serializer.is_valid():
					htm_weightage_serializer.save()
				else:
					response['msg'] = 'error'
					response['errpr'] = htm_weightage_serializer.errors
					return Response(response, status=status.HTTP_400_BAD_REQUEST)
				response['msg'] = 'success'
				return Response(response, status=status.HTTP_200_OK)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetHTMCalendarDataView(APIView):
	def get(self, request, op_id):
		try:
			openposition_obj = OpenPosition.objects.get(id=op_id)
			hiring_group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
			members = hiring_group_obj.members_list.all().values_list("id", flat=True)
			if hiring_group_obj.hod_profile:
				members.append(hiring_group_obj.hod_profile.id)
			members_availability = HTMAvailability.objects.filter(htm_id__in=members)
			availability_data = []
			for i in members_availability:
				try:
					temp_dict = {}
					temp_dict['htm_id'] = i.htm_id
					htm_obj = Profile.objects.get(id=i.htm_id)
					avails = json.loads(i.availability)
					avails.sort(key=lambda item:item['date'])
					for avail in avails:
						interview = Interview.objects.filter(htm__id__in=[i.htm_id], texted_start_time=json.dumps(avail)).filter(disabled=False)
						if interview:
							interview_obj = interview.last()
							openposition_obj = OpenPosition.objects.get(id=interview_obj.op_id.id)
							avail["scheduled"] = True
							avail['position_name'] = openposition_obj.position_title
							avail['color'] = 'ff0000'
							try:
								# candidate_obj = Candidate.objects.get(candidate_id=interview_obj.candidate)
								avail['candidate_name'] = "{} {}".format(interview_obj.candidate.name, interview_obj.candidate.last_name)
							except Exception as e:
								avail['candidate_name'] = ""
								avail['errpr'] = str(e)
						else:
							avail["scheduled"] = False
							temp_dict['color'] = i.color
							avail['candidate_name'] = ""
						avail['htm_name'] = "{} {}".format(htm_obj.user.first_name, htm_obj.user.last_name)
						avail['posititon'] = openposition_obj.position_title
						start = datetime.strptime(avail['hours'][0]['startTime'], "%H:%M")
						end = datetime.strptime(avail['hours'][0]['endTime'], "%H:%M")
						avail['time'] = "{} to {}".format(start.strftime("%I:%M %p"), end.strftime("%I:%M %p"))
				except Exception as e:
					print(e)
					temp_dict['error'] = str(e)
				avails.sort(key=lambda item:item['date'])
				temp_dict['availability'] = avails
				temp_dict['color'] = i.color
				availability_data.append(temp_dict)
			response = {}
			response['msg'] = 'success'
			response['data'] = availability_data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Zoom APIs to generate a meeting for scheduled call.
def generateToken():
	token = jwt.encode(

		# Create a payload of the token containing
		# API Key & expiration time
		{'iss': settings.ZOOM_CLIENT_ID, 'exp': time() + 5000},

		# Secret used to generate token signature
		settings.ZOOM_CLIENT_SK,

		# Specify the hashing alg
		algorithm='HS256'
	)
	print(token)
	return token


meetingdetails = {
	"topic": "The title of your zoom meeting",
	"type": 2,
	"start_time": "2022-04-26T9: 7: 00",
	"duration": "45",
	"timezone": "Europe/Madrid",
	"agenda": "test",
	"recurrence": {
					"type": 1,
					"repeat_interval": 1
				},
	"settings": {
					"host_video": "true",
					"participant_video": "true",
					"join_before_host": "False",
					"mute_upon_entry": "False",
					"watermark": "true",
					"audio": "voip",
					"auto_recording": "cloud",
				}
}


def createMeeting():
	headers = {
		'authorization': 'Bearer ' + generateToken(),
		'content-type': 'application/json'
	}
	r = requests.post(f'https://api.zoom.us/v2/users/me/meetings', headers=headers, data=json.dumps(meetingdetails))

	print("\n creating zoom meeting ... \n")
	y = json.loads(r.text)
	print(y)
	join_URL = y["join_url"]
	meetingPassword = y["password"]
	return join_URL


class GenerateZoomMeeting(APIView):
	def get(self, request):
		try:
			response = {}
			try:
				meeting_url = createMeeting()
				response['msg'] = 'success'
				response['meeting_link'] = meeting_url
			except Exception as e:
				response['msg'] = 'error'
				response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SendEmailToHTM(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			response = {}
			op_id = int(request.data.get('op_id'))
			if int(op_id) == int(settings.EXAMPLE_POSITION) and not request.user.is_superuser:
				response['msg'] = 'Interview can not scheduled for this position'
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			candidate = int(request.data.get('candidate'))
			try:
				candidate_obj = Candidate.objects.get(candidate_id=int(candidate))
			except Exception as e:
				return  Response({"error":str(e), "msg": "candidate not found"}, status=status.HTTP_200_OK)
			openposition_obj = OpenPosition.objects.get(id=op_id)
			hiring_group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)

			subject = request.data.get('subject')
			message = request.data.get('mailBody')
			date = "28-04-2022"
			time = "22"
			email_from = settings.EMAIL_HOST_USER
			recipient_list = request.data.get('toEmails').split(',')
			htms_list = []
			non_htms_list = []
			for i in recipient_list:
				if Profile.objects.filter(email=i):
					htms_list.append(i)
				else:
					non_htms_list.append(i)
			scheduled_persons = htms_list.copy()
			try:
				htms_list.append(hiring_group_obj.hod_profile.email)
			except:
				pass
			response['htms_list'] = htms_list
			response['non_htms_list'] = non_htms_list
			non_htms_list.append(candidate_obj.email)
			date = request.data.get('date')
			ICS_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
			start_date_time = datetime.strptime(date + " %d:%02d" % (request.data.get('startTime')['hour'], request.data.get('startTime')['minute']), "%m-%d-%Y %H:%M")
			end_date_time = datetime.strptime(date + " %d:%02d" % (request.data.get('endTime')['hour'], request.data.get('endTime')['minute']), "%m-%d-%Y %H:%M")
			duration = end_date_time - start_date_time
			# send error if time is already ocupied
			if Interview.objects.filter(htm__email__in=scheduled_persons, interview_date_time=start_date_time):
				response['msg'] = 'Mails for some HTM were not sent as their timing is already used.'
				return Response({"msg": "HTM is already scheduled for given time slots", "exists": True}, status=status.HTTP_200_OK)
					
			# creating ics file
			t_start_date_time = start_date_time + timedelta(hours=5)
			t_end_date_time = end_date_time + timedelta(hours=5)
			ICS_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S %Z"
			calendar = Calendar()
			event = Event()
			event.name = subject
			event.begin = t_start_date_time.strftime(ICS_DATETIME_FORMAT) #"2022-04-29 10:00:00"
			event.end = t_end_date_time.strftime(ICS_DATETIME_FORMAT)
			event.organizer = settings.EMAIL_HOST_USER
			calendar.events.add(event)
			filename_event = 'invite.ics'

			booked_htms = []
			for i in recipient_list:
				try:
					htm_profile_obj = Profile.objects.get(email=i)
				except:
					continue
				htm_availability_objs = HTMAvailability.objects.filter(htm_id=htm_profile_obj.id)
				if htm_availability_objs:
					htm_availability_obj = htm_availability_objs[0]
					availability = json.loads(htm_availability_obj.availability)
					date = request.data.get("date")
					date_list = date.split('-')
					start_time = request.data.get("startTime")
					end_time = request.data.get("endTime")
					temp_dict = {
						"day": 1,
						"date": "{}-{}-{}".format(date_list[2], date_list[0], date_list[1]),
						"hours": [
							{
							"startTime": "{}:{}".format(start_time["hour"], start_time["minute"]),
							"endTime": "{}:{}".format(end_time["hour"], end_time["minute"])
							}
						],
						
					}
					interview_date = None
					# te_temp_dict = temp_dict
					# te_temp_dict["htm_created"] = False
					# t_temp_dict = te_temp_dict
					# del te_temp_dict["htm_created"]
					# n_temp_dict = te_temp_dict
					# if n_temp_dict not in availability or t_temp_dict not in availability or temp_dict not in availability:
					if temp_dict not in availability:
						availability.append(temp_dict)
					htm_availability_obj.availability = json.dumps(availability)
					htm_availability_obj.save()
					response['msg'] = 'schedule updated'
				else:
					response['where1'] = 'else'
					availability = []
					date = request.data.get("date")
					date_list = date.split('-')
					start_time = request.data.get("startTime")
					end_time = request.data.get("endTime")
					temp_dict = {
						"day": 1,
						"date": "{}-{}-{}".format(date_list[2], date_list[0], date_list[1]),
						"hours": [
							{
							"startTime": "{}:{}".format(start_time["hour"], start_time["minute"]),
							"endTime": "{}:{}".format(end_time["hour"], end_time["minute"])
							}
						],
						
					}
					availability.append(temp_dict)
					HTMAvailability.objects.create(
						htm_id=htm_profile_obj.id,
						availability=json.dumps(availability)
					)
					response['msg'] = 'schedule added'
			
			htms = request.data.get('htms')
			zoom_link = request.data.get('zoom_link')
			candidate_link = None
			try:
				candidate_link = zoom_link.split('?')[0]
			except:
				candidate_link = zoom_link		
			candidate_message = message
			try:
				candidate_message = candidate_message.replace(zoom_link, candidate_link)
			except:
				pass
			interview_obj = None
			interview_profiles = []
			for i in htms:
				try:
					date = request.data.get("date")
					date_list = date.split('-')
					start_time = request.data.get("startTime")
					end_time = request.data.get("endTime")
					temp_dict = {
						"day": 1,
						"date": "{}-{}-{}".format(date_list[2], date_list[0], date_list[1]),
						"hours": [
							{
							"startTime": "{}:{}".format(start_time["hour"], start_time["minute"]),
							"endTime": "{}:{}".format(end_time["hour"], end_time["minute"])
							}
						],
					}
					htm_profile = Profile.objects.get(id=int(i))
					interview_profiles.append(htm_profile)
					htm_availability_objs = HTMAvailability.objects.filter(htm_id=int(i))
					htm_availability_obj = htm_availability_objs[0]
					availability = json.loads(htm_availability_obj.availability)
					if Interview.objects.filter(htm__in=[htm_profile], interview_date_time=start_date_time).filter(disabled=False):
						response['msg'] = 'Mails for some HTM were not sent as their timing is already used.'
						if interview_obj:
							interview_obj.delete()
						return Response({"msg": "HTM is already scheduled for given time slots", "exists": True}, status=status.HTTP_200_OK)
					else:
						if interview_obj:
							pass
						else:
							interview_obj = Interview.objects.create(op_id=openposition_obj, created_by=request.user.profile, candidate=candidate_obj, subject=subject, body=message, zoom_link=zoom_link, interview_date_time=start_date_time, texted_start_time=json.dumps(temp_dict), duration=duration.seconds, meeting_key=request.data.get('meetingKey'), interview_type=request.data.get('interviewType'), conference_id=request.data.get('conference_id'))
						with open(filename_event, 'w') as ics_file:
							ics_file.writelines(calendar)
						try:
							new_sub = "{} {} - {}".format(htm_profile.user.first_name, htm_profile.user.last_name, subject)
							if len(non_htms_list) > 0:
								tasks.send.delay(new_sub, candidate_message, 'text', non_htms_list, htm_profile.email, htm_profile.user.get_full_name(), filename_event)
							if len(htms_list) > 0:
								cc = request.data.get("ccEmails", "")
								message = message + '\n Click on following link to redirect to candidate marks details: https://app.qorums.com/htm/position/candidateProfile/{}/{}'.format(op_id, candidate)
								tasks.send.delay(new_sub, message, 'text', htms_list, htm_profile.email, htm_profile.user.get_full_name(), filename_event, cc=cc)
						except Exception as e:
							return Response({"message": str(e), "response": response}, status=status.HTTP_400_BAD_REQUEST)
						# os.remove(filename_event)
						# send notitications
						client_obj = Client.objects.get(id=hiring_group_obj.client_id)
						if request.user.profile == hiring_group_obj.hod_profile or request.user.profile == hiring_group_obj.hr_profile:
							# send to account manager
							tasks.send_app_notification.delay(client_obj.ae_assigned, 'An interview has been scheduled for the {} opening at {}'.format(openposition_obj.position_title, client_obj.company_name))
							tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'An interview has been scheduled for the {} opening at {}'.format(openposition_obj.position_title, client_obj.company_name))
						else:
							candidate_obj = Candidate.objects.get(candidate_id=candidate)
							tasks.send_app_notification.delay(htm_profile.user.username, 'An interview has been scheduled for the {} opening.'.format(openposition_obj.position_title))
							tasks.push_notification.delay([htm_profile.user.username], 'Qorums Notification', 'An interview has been scheduled for the {} opening.'.format(openposition_obj.position_title))
				except Exception as e:
					response['error'] = str(e)
			interview_obj.htm.set(interview_profiles)
			response['path'] = os.getcwd()
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		response = {}
		try:
			schedule_id = request.query_params.get("id")
			interview_obj = Interview.objects.get(id=schedule_id)
			response["id"] = interview_obj.id
			response["op_id"] = interview_obj.op_id.id
			response["candidate_email"] = interview_obj.candidate.email
			response["candidate_id"] = interview_obj.candidate.candidate_id
			response["to_email"] = ", ".join(list(interview_obj.htm.all().values_list("email", flat=True)))
			response["time_obj"] = json.loads(interview_obj.texted_start_time)
			response["date"] = interview_obj.interview_date_time.strftime("%m-%d-%Y")
			response["startTime"] = {"hour": interview_obj.interview_date_time.strftime("%-H"),"minute": interview_obj.interview_date_time.strftime("%-M")}
			end_time = interview_obj.interview_date_time + timedelta(minutes=30)
			response["endTime"] = {"hour": end_time.hour,"minute": end_time.minute}
			response["subject"] = interview_obj.subject
			response["body"] = interview_obj.body
			response["interview_type"] = interview_obj.interview_type
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class ArchievePositionView(APIView):
	permission_classes = (permissions.IsAuthenticated,)
	
	def post(self,  request, op_id):
		response = {}
		if int(op_id) == int(settings.EXAMPLE_POSITION) and not request.user.is_superuser:
			response['msg'] = 'This position can not be archived!'
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
		try:
			openposition_obj = OpenPosition.objects.get(id=op_id)
			openposition_obj.archieved = True
			openposition_obj.save()
			try:
				client_obj = Client.objects.get(id=openposition_obj.client)
				tasks.send_app_notification.delay(client_obj.ae_assigned, 'The {} opening at {} has been archived'.format(openposition_obj.position_title, client_obj.company_name))
				tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'The {} opening at {} has been archived'.format(openposition_obj.position_title, client_obj.company_name))

				tasks.send_app_notification.delay(client_obj.key_username, 'The {} opening has been archived'.format(openposition_obj.position_title))
				tasks.push_notification.delay([client_obj.key_username], 'Qorums Notification', 'The {} opening has been archived'.format(openposition_obj.position_title))

				hiring_group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
				
				if hiring_group_obj.hod_profile:
					hod_profile = hiring_group_obj.hod_profile
					tasks.send_app_notification.delay(hod_profile.user.username, 'The {} opening has been archived'.format(openposition_obj.position_title))
					tasks.push_notification.delay([hod_profile.user.username], 'Qorums Notification', 'The {} opening has been archived'.format(openposition_obj.position_title))
				
				if hiring_group_obj.hr_profile:
					hr_profile = hiring_group_obj.hr_profile
					tasks.send_app_notification.delay(hr_profile.user.username, 'The {} opening has been archived'.format(openposition_obj.position_title))
					tasks.push_notification.delay([hr_profile.user.username], 'Qorums Notification', 'The {} opening has been archived'.format(openposition_obj.position_title))
			except Exception as e:
				response['notitication-error'] = str(e)
			response['msg'] = 'Archived'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)

	def put(self,  request, op_id):
		response = {}
		try:
			openposition_obj = OpenPosition.objects.get(id=op_id)
			openposition_obj.archieved = False
			openposition_obj.save()
			response['msg'] = 'Unarchived'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class ZapierWebhookView(APIView):
	def post(self, request):
		response = {}
		APIData.objects.create(data=request.data)
		return Response(response, status=status.HTTP_200_OK)


class SelectAnalyticsView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		response = {}
		try:
			obj, created = SelectedAnalyticsDashboard.objects.get_or_create(user=request.user)
			add_selected = request.data
			if created:
				obj.selected = json.dumps(add_selected)
			else:
				obj.selected = json.dumps(add_selected)
			obj.save()
			response['msg'] = 'added'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = e
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


	def get(self, request):
		response = {}
		try:
			obj, created = SelectedAnalyticsDashboard.objects.get_or_create(user=request.user)
			if created:
				selected = [
								{
								  "class": 'open-position-data',
								  "label": 'Open Position',
								  "isSelected": True
								},
								{
								  "class": 'active-clients',
								  "label": 'Active Clients',
								  "isSelected": True
								},
								{
								  "class": 'liked-candidates',
								  "label": 'Liked Candidates',
								  "isSelected": True
								},
								{
								  "class": 'passed-candidates',
								  "label": 'Passed Candidates',
								  "isSelected": True
								},
								{
								  "class": 'interview-not-scheduled',
								  "label": 'Interview Not Scheduled',
								  "isSelected": True
								},
								{
								  "class": 'interview-scheduled',
								  "label": 'Interview Scheduled',
								  "isSelected": True
								},
								{
								  "class": 'offers-accepted',
								  "label": 'Offers Accepted',
								  "isSelected": True
								},
								{
								  "class": 'top-clients-with-hires',
								  "label": 'Top Clients with Hires',
								  "isSelected": True
								},
								{
								  "class": 'total-hires-this-quater',
								  "label": 'Hires this Quarter',
								  "isSelected": True
								},
								{
								  "class": "top-clients-with-open-position",
								  "label": 'Top Clients with Open Position',
								  "isSelected": True
								},
								{
								  "class": "total-candidates",
								  "label": 'Total Candidates',
								  "isSelected": True
								},
							]
				obj.selected = json.dumps(selected)
				obj.save()
			selected_resp = json.loads(obj.selected)
			if "is_ca" in request.user.profile.roles or "is_sm" in request.user.profile.roles:
				op = [
					{"class": 'active-clients',"label": 'Active Clients',"isSelected": True},
					{"class": 'active-clients',"label": 'Active Clients',"isSelected": False}
				]
				for o in op:
					if o in selected_resp:
						selected_resp.remove(o)
				op = [
					{"class": 'top-clients-with-open-position',"label": 'Top Clients with Open Position',"isSelected": True},
					{"class": 'top-clients-with-open-position',"label": 'Top Clients with Open Position',"isSelected": False}
				]
				for o in op:
					if o in selected_resp:
						selected_resp.remove(o)
				op = [
					{"class": 'top-clients-with-hires',"label": 'Top Clients with Hires',"isSelected": True},
					{"class": 'top-clients-with-hires',"label": 'Top Clients with Hires',"isSelected": False}
				]
				for o in op:
					if o in selected_resp:
						selected_resp.remove(o)
			response = selected_resp
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class QorumsDashboardView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		response = {}
		# try:
		# selected_analytics = SelectedAnalyticsDashboard.objects.get(user=request.user)
		# for selected in json.loads(selected_analytics.selected):
			# if selected['isSelected'] == True:
				# print(selected['class'])
				# if selected['class'] == "open-position":
		# response['open-position-data'] = get_openposition_data(request.user)
				# if selected['class'] == "liked-candidate":
		# response['liked-candidates'] = get_liked_candidates_data(request.user)
				# if selected['class'] == "passed-candidates":
		# response['passed-candidates'] = get_passed_candidates_data(request.user)
		# interview_schedule, interview_not_schedule = get_interview_data(request.user)
				# if selected['class'] == "interview-not-scheduled":
		# response['interview-not-scheduled'] = interview_not_schedule
				# if selected['class'] == "interview-scheduled":
		# response['interview-scheduled'] = interview_schedule
				# if selected['class'] == "offer-accepted":
				# response['open-position-data'] = get_openposition_data(request.user)
				# if selected['class'] == "position-stalled":
				# response['open-position-data'] = get_openposition_data(request.user)
				# if selected['class'] == "canddidates-in-process":
				# response['open-position-data'] = get_openposition_data(request.user)
				# if selected['class'] == "hires-this-month":
				# response['open-position-data'] = get_openposition_data(request.user)
		end_date = datetime.today().date()
		start_date = datetime.today().date() - timedelta(120)
		year_start_date = datetime.today().date() - timedelta(365)
		months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
		foo = [1,6,4,2,8,7,3,5]
		tcwh = None
		if request.user.is_superuser:
			active_clients = Client.objects.filter(disabled=False).count()
			total_candidates = Candidate.objects.all().count()

			current_month = datetime.now().month
			monthly_candidates = []

			while current_month:
				count = Candidate.objects.filter(created_at__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = count
				monthly_candidates.append(temp_dict)
				current_month = current_month - 1

			top_clients_with_open_position = OpenPosition.objects.values('client').annotate(count=Count('client')).order_by('-count')[0:3]
			
			hires_queries = Hired.objects.all()
			total_hires = hires_queries.count()

			current_month = datetime.now().month
			monthly_data = []

			while current_month:
				count = hires_queries.filter(created__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = random.choice(foo)
				monthly_data.append(temp_dict)
				current_month = current_month - 1
			

			current_month = datetime.now().month
			monthly_active_clients = []

			while current_month:
				count = Client.objects.filter(disabled=False, created_at__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = count
				monthly_active_clients.append(temp_dict)
				current_month = current_month - 1
			

			total_hires_this_quater = Hired.objects.filter(created__gte=start_date, created__lte=end_date).count()
			current_month = datetime.now().month
			monthly_total_hires = []
			t_count = 0
			while current_month and t_count < 4:
				count = Hired.objects.filter(created__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = random.choice(foo)
				monthly_total_hires.append(temp_dict)
				current_month = current_month - 1
				t_count += 1
			# get top clients with hires
			top_hires = []
			for client in Client.objects.all():
				open_positions = list(OpenPosition.objects.filter(client=client.id).values_list('id', flat=True))
				total_hires = Hired.objects.filter(op_id__in=open_positions).count()
				if total_hires:
					temp_dict = {}
					temp_dict['client-name'] = client.company_name
					temp_dict['count'] = total_hires
					top_hires.append(temp_dict)
			tcwh = sorted(top_hires, key=lambda d: d['count'], reverse=True)[0:3]
			# response['top-clients-with-hires'] = sorted(top_hires, key=lambda d: d['count'], reverse=True)[0:3]
		elif "is_ae" in request.user.profile.roles:
			clients = json.loads(request.user.profile.client)
			active_clients = Client.objects.filter(id__in=clients, disabled=False).count()
			total_candidates = Candidate.objects.all().count()

			current_month = datetime.now().month
			monthly_candidates = []

			while current_month:
				count = Candidate.objects.filter(created_at__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = count
				monthly_candidates.append(temp_dict)
				current_month = current_month - 1

			top_clients_with_open_position = OpenPosition.objects.values('client').annotate(count=Count('client')).order_by('-count').filter(client__in=json.loads(request.user.profile.client))[0:3]
			open_positions = list(OpenPosition.objects.filter(client__in=clients, drafted=False, archieved=False, trashed=False).values_list('id', flat=True))
			
			hires_queries = Hired.objects.filter(op_id__in=open_positions)
			total_hires = hires_queries.count()

			current_month = datetime.now().month
			monthly_data = []
			while current_month:
				count = hires_queries.filter(created__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = random.choice(foo)
				monthly_data.append(temp_dict)
				current_month = current_month - 1
			

			current_month = datetime.now().month
			monthly_active_clients = []

			while current_month:
				count = Client.objects.filter(id__in=clients, disabled=False, created_at__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = count
				monthly_active_clients.append(temp_dict)
				current_month = current_month - 1


			total_hires_this_quater = Hired.objects.filter(op_id__in=open_positions).filter(created__gte=start_date, created__lte=end_date).count()
			current_month = datetime.now().month
			monthly_total_hires = []
			t_count = 0
			while current_month and t_count < 4:
				count = Hired.objects.filter(op_id__in=open_positions, created__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = random.choice(foo)
				monthly_total_hires.append(temp_dict)
				current_month = current_month - 1
				t_count += 1
			top_hires = []

			for client in clients:
				try:
					client_obj = Client.objects.get(id=clients)
					open_positions = list(OpenPosition.objects.filter(client=client_obj.id).values_list('id', flat=True))
					total_hires = Hired.objects.filter(op_id__in=open_positions).count()
					if total_hires:
						temp_dict = {}
						temp_dict['client-name'] = client_obj.company_name
						temp_dict['count'] = total_hires
						top_hires.append(temp_dict)
				except:
					pass
			tcwh = sorted(top_hires, key=lambda d: d['count'], reverse=True)[0:3]
			# response['top-clients-with-hires'] = sorted(top_hires, key=lambda d: d['count'], reverse=True)[0:3]
		else:
			active_clients = 1
			monthly_active_clients = []
			try:
				client_obj = Client.objects.get(id=int(request.user.profile.client))
				response['client-name'] = client_obj.company_name
				total_candidates = Candidate.objects.filter(created_by_client=client_obj.id).count()
				candidate_query = Candidate.objects.filter(created_by_client=client_obj.id)
			except:
				total_candidates = Candidate.objects.all().count()
				candidate_query = Candidate.objects.all()
			# total_candidates = Candidate.objects.all().count()

			current_month = datetime.now().month
			monthly_candidates = []

			while current_month:
				count = candidate_query.filter(created_at__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = count
				monthly_candidates.append(temp_dict)
				current_month = current_month - 1

			top_clients_with_open_position = OpenPosition.objects.values('client').annotate(count=Count('client')).order_by('-count').filter(client=int(request.user.profile.client))[0:3]
			open_positions = list(OpenPosition.objects.filter(client=request.user.profile.client, drafted=False, archieved=False, trashed=False).values_list('id', flat=True))
			
			hires_queries = Hired.objects.filter(op_id__in=open_positions)
			total_hires = hires_queries.count()

			current_month = datetime.now().month
			monthly_data = []
			while current_month:
				count = hires_queries.filter(created__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = random.choice(foo)
				monthly_data.append(temp_dict)
				current_month = current_month - 1
			
			total_hires_this_quater = Hired.objects.filter(op_id__in=open_positions).filter(created__gte=start_date, created__lte=end_date).count()
			current_month = datetime.now().month
			monthly_total_hires = []
			t_count = 0
			while current_month and t_count < 4:
				count = Hired.objects.filter(op_id__in=open_positions, created__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = random.choice(foo)
				monthly_total_hires.append(temp_dict)
				current_month = current_month - 1
				t_count += 1	
		top_clients_with_open_position = OpenPosition.objects.values('client').annotate(count=Count('client')).order_by('-count')[0:3]
		
		top_cliets_with_open_position_list = []
		for client in top_clients_with_open_position:
			try:
				client_obj = Client.objects.get(id=client['client'])
				temp_dict = {}
				temp_dict['count'] = client['count']
				temp_dict['client_name'] = client_obj.company_name
				top_cliets_with_open_position_list.append(temp_dict)
			except:
				pass

		response['open-position-data'] = get_openposition_data(request.user)

		response['active-clients'] = {}
		response['active-clients']['count'] = active_clients
		response['active-clients']['chart-data'] = monthly_active_clients
		response['active-clients']['class'] = 'active-clients'

		response['liked-candidates'] = get_liked_candidates_data(request.user)
		response['passed-candidates'] = get_passed_candidates_data(request.user)
		interview_schedule, interview_not_schedule = get_interview_data(request.user)
		response['interview-not-scheduled'] = interview_not_schedule
		response['interview-scheduled'] = interview_schedule

		response['offers-accepted'] = {}
		response['offers-accepted']['count'] = total_hires
		response['offers-accepted']['chart-data'] = monthly_data
		response['offers-accepted']['class'] = 'offers-accepted'

		response['top-clients-with-hires'] = {}
		response['top-clients-with-hires']['class'] = 'top-clients-with-hires'
		response['top-clients-with-hires'] = tcwh

		response['total-hires-this-quater'] = {}
		response['total-hires-this-quater']['chart-data'] = monthly_total_hires
		response['total-hires-this-quater']['count'] = total_hires_this_quater
		response['total-hires-this-quater']['class'] = 'total-hires-this-quater'

		response['top-clients-with-open-position'] = {}
		response['top-clients-with-open-position']['class'] = 'top-clients-with-open-position'
		response['top-clients-with-open-position']['data'] = top_cliets_with_open_position_list

		response['total-candidates'] = {}
		response['total-candidates']['count'] = total_candidates
		response['total-candidates']['chart-data'] = monthly_candidates
		response['total-candidates']['class'] = 'total-candidates'	
		if "is_ca" in request.user.profile.roles:
			try:
				response.pop("active-clients", None)
				response.pop("top-clients-with-open-position", None)
				response.pop("top-clients-with-hires", None)
			except:
				pass
		return Response(response, status=status.HTTP_200_OK)
		# except Exception as e:
		# 	response['msg'] = 'error'
		# 	response['error'] = str(e)
		# 	return Response(response, status=status.HTTP_400_BAD_REQUEST)


class AllSeniorManagers(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		sm_objs = None
		if request.user.is_superuser:
			sm_objs = Profile.objects.filter(Q(is_sm=True) | Q(roles__contains="is_sm"))
		else:
			client_id = request.user.profile.client
			sm_objs = Profile.objects.filter(client=client_id).filter(Q(is_sm=True) | Q(roles__contains="is_sm"))
		try:
			data = []
			for i in sm_objs:
				temp_dict = {}
				temp_dict["id"] = i.id
				temp_dict["name"] = i.user.first_name + ' ' + i.user.last_name
				temp_dict["username"] = i.user.username
				temp_dict["mobile_no"] = i.phone_number
				temp_dict["email"] = i.email
				temp_dict['profile_photo'] = i.profile_photo
				temp_dict['client_id'] = i.client
				data.append(temp_dict)
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SeniorManagerView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			if User.objects.filter(username=request.data.get("username")).exists():
				return Response(
					{"error": str(e), "msg": "User with this username already exists!"},
					status=status.HTTP_400_BAD_REQUEST,
				)
			if Profile.objects.filter(email=request.data.get("email")).exists():
				return Response(
					{"error": str(e), "msg": "User with this email already exists!"},
					status=status.HTTP_400_BAD_REQUEST,
				)
			client_id = request.data.get('client_id')
			profile = request.user.profile
			if profile.is_ca:
				client_id = int(profile.client)
			username = request.data.get("username")
			password = request.data.get("password")
			first_name = request.data.get("first_name")
			last_name = request.data.get("last_name")
			user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)
			phone_number = request.data.get("phone_number")
			skype_id = request.data.get("skype_id")
			job_title = request.data.get('job_title')
			email = request.data.get("email")
			if Profile.objects.filter(email=email).exists() or Candidate.objects.filter(email=email).exists():
				return Response({'message': 'Email already exists!'}, status=status.HTTP_400_BAD_REQUEST)
			try:
				profile_photo = request.FILES['profile_photo']
				p_fs = FileSystemStorage()
				profile_filename = p_fs.save(profile_photo.name, profile_photo)
				uploaded_profile_photo = p_fs.url(profile_filename)
			except Exception as e:
				print(e)
				uploaded_profile_photo = "None"
			if request.data.get("profile_photo"):
				uploaded_profile_photo = request.data.get("profile_photo")
			try:
				Profile.objects.create(user=user, phone_number=phone_number, skype_id=skype_id, email=email, is_sm=True, profile_photo=uploaded_profile_photo, client=client_id, job_title=job_title)
			except Exception as e:
				user.delete()
				return Response({'msg': str(e)}, status=status.HTTP_409_CONFLICT)
			response = {}
			response['msg'] = "added"
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		try:
			username = request.query_params.get('username')
			try:
				user_obj = User.objects.get(username=username)
				profile_obj = Profile.objects.get(user=user_obj)
			except Exception as e:
				response = {}
				response["msg"] = str(e)
				return Response(response, status=status.HTTP_204_NO_CONTENT)
			response = {}
			response["username"] = user_obj.username
			response["first_name"] = user_obj.first_name
			response["last_name"] = user_obj.last_name
			response["phone_number"] = profile_obj.phone_number
			response["skype_id"] = profile_obj.skype_id
			response['job_title'] = profile_obj.job_title
			response["email"] = profile_obj.email
			response["client_id"] = profile_obj.client
			response['profile_photo']  = profile_obj.profile_photo.url if profile_obj.profile_photo else None
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request):
		try:
			username = request.data.get("username")
			try:
				user_obj = User.objects.get(username=username)
				user_obj.first_name = request.data.get('first_name')
				user_obj.last_name = request.data.get('last_name')
				user_obj.save()
				profile_obj = Profile.objects.get(user=user_obj)
			except Exception as e:
				response = {}
				response["msg"] = str(e)
				return Response(response, status=status.HTTP_204_NO_CONTENT)
			profile_obj.client = request.data.get('client_id')
			profile_obj.phone_number = request.data.get("phone_number")
			profile_obj.skype_id = request.data.get("skype_id")
			profile_obj.job_title = request.data.get("job_title")
			if profile_obj.email != request.data.get("email"):
				if Profile.objects.filter(email=request.data.get("email")).exists() or Candidate.objects.filter(email=request.data.get("email")).exists():
					return Response({'message': 'Email already exists!'}, status=status.HTTP_400_BAD_REQUEST)
			profile_obj.email = request.data.get("email")
			try:
				profile_photo = request.FILES['profile_photo']
				p_fs = FileSystemStorage()
				profile_filename = p_fs.save(profile_photo.name, profile_photo)
				uploaded_profile_photo = p_fs.url(profile_filename)
			except Exception as e:
				uploaded_profile_photo = profile_obj.profile_photo
			profile_obj.profile_photo = uploaded_profile_photo
			if request.data.get('profile_photo_deleted') == "true":
				profile_obj.profile_photo = None
			if request.data.get('password'):
				profile_obj.user.set_password(request.data.get('password'))
				profile_obj.user.save()
			profile_obj.save()
			response = {}
			response["msg"] = "updated"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request):
		try:
			username = request.query_params.get('username')
			user_obj = User.objects.get(username=username)
			profile_obj = Profile.objects.get(user=user_obj)
			user_obj.delete()
			profile_obj.delete()
			response = {}
			response["msg"] = "deleted"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Email itself is used as the username to match the previous flow.
class SignUpView(APIView):
	"""
		This API is used for Signing up the user once 
		he had finished his payment and all the thing.
		It also creates the client using the data given
		at time of sign up.
	"""
	def post(self, request):
		response = {}
		try:
			email = request.data.get('email')
			first_name = request.data.get('first_name')
			last_name = request.data.get('last_name')
			password = request.data.get('password')
			user_obj = User.objects.create(username=email, email=email, first_name=first_name, last_name=last_name)
			user_obj.set_password(password)
			user_obj.save()
			# Creating client
			client_obj = Client.objects.create(
				company_name=request.data.get('company_name'),
				company_website=request.data.get('company_website'),
			    company_linkedin=request.data.get('company_linkedin'),
			    ca_first_name=request.data.get('first_name'),
			    ca_last_name=request.data.get('last_name'),
			    key_contact_email=request.data.get('email'),
			    key_username=request.data.get('email'),
			)
			create_email_templates(client_obj)
			if Profile.objects.filter(email=request.data.get("email")).exists() or Candidate.objects.filter(email=request.data.get("email")).exists():
				return Response({"msg": "email already exists"}, status=status.HTTP_409_CONFLICT)
			profile_obj = Profile.objects.create(user=user_obj, email=email, is_ca=True, client=client_obj.id)
			# send confirmation mail.
			subject = 'Welcome to the Board - Qorums'
			d = {
				"user_name": "{} {}".format(first_name, last_name)			}
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [email, ]
			# htmly_b = get_template('qorums_welcome.html')
			# text_content = ""
			# html_content = htmly_b.render(d)
			try:
				email_template = EmailTemplate.objects.get(client=client_obj, name="Qorums Welcome Mail to CA")
				template = Template(email_template.content)
				context = Context(d)
			except:
				email_template = EmailTemplate.objects.get(client=None, name="Qorums Welcome Mail to CA")
				template = Template(email_template.content)
				context = Context(d)
			html_content = template.render(context)
			msg = EmailMultiAlternatives(subject, html_content, email_from, recipient_list)
			msg.attach_alternative(html_content, "text/html")
			try:
				msg.send(fail_silently=True)
			except Exception as e:
				print(e)
			response['msg'] = 'created'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class UserProfileAPI(APIView):
	"""
		This API is used to updated or get the current logged user details
		Body for POST:
			- first_name
			- last_name
			- phone_number
			- skype_id
			- job_title
			- profile_photo
	"""
	permission_classes = [IsAuthenticated]
	def get(self, request, profile_id):
		response = {}
		try:
			profile_obj = Profile.objects.get(id=profile_id)
			response['first_name'] = profile_obj.user.first_name
			response['last_name'] = profile_obj.user.last_name
			response['phone_number'] = profile_obj.phone_number
			response['email'] = profile_obj.email
			response['skype_id'] = profile_obj.skype_id
			response['job_title'] = profile_obj.job_title
			if profile_obj.is_candidate:
				try:
					candidate_obj = Candidate.objects.get(email=profile_obj.email)
					if candidate_obj.profile_photo:
						response['profile_photo'] = candidate_obj.profile_photo
					elif "profile_pic_url" in candidate_obj.linkedin_data and candidate_obj.linkedin_data['profile_pic_url'] != "null":
						response['profile_photo'] = candidate_obj.linkedin_data["profile_pic_url"]
					else:
						response['profile_photo'] = 'None'
				except Exception as e:
					print(e)
					response['profile_photo'] = profile_obj.profile_photo
			else:
				# response['profile_photo'] = profile_obj.profile_photo.url
				response['profile_photo'] = None
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)

	def post(self, request, profile_id):
		response = {}
		try:
			profile_obj = Profile.objects.get(id=profile_id)
			data = request.data
			profile_obj.user.first_name = data.get('first_name')
			profile_obj.user.last_name = data.get('last_name')
			profile_obj.phone_number = data.get('phone_number', profile_obj.phone_number)
			profile_obj.skype_id = data.get('skype_id', profile_obj.skype_id)
			profile_obj.job_title = data.get('job_title', profile_obj.job_title)
			email = request.data.get("email")
			if email and email != profile_obj.email:
				if Candidate.objects.filter(email=request.data.get('email')) or Profile.objects.filter(email=request.data.get('email')):
					return Response({'msg': 'existing email'}, status=status.HTTP_409_CONFLICT)
				else:
					try:
						can_obj = Candidate.objects.get(email=profile_obj.email)
						can_obj.email = email
						can_obj.save()
					except:
						pass
					profile_obj.email = email
					profile_obj.save()
			if data.get('password') not in ["null", None]:
				profile_obj.user.set_password(data.get('password'))
				profile_obj.user.save()
			uploaded_profile_photo = None
			try:
				profile_photo = request.FILES['profile_photo']
				p_fs = FileSystemStorage()
				profile_filename = p_fs.save(profile_photo.name, profile_photo)
				uploaded_profile_photo = p_fs.url(profile_filename)
				if profile_obj.is_candidate:
					try:
						candidate_obj = Candidate.objects.get(email=profile_obj.email)
						candidate_obj.profile_photo = uploaded_profile_photo
						candidate_obj.save()
					except:
						pass
				else:
					profile_obj.profile_photo = uploaded_profile_photo
			except Exception as e:
				response["profile_photo_error"] = str(e)
			profile_obj.save()
			profile_obj.user.save()
			response['password'] = data.get('password')
			response['msg'] = 'update'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class ProTipView(APIView):
	def post(self, request):
		response = {}
		try:
			data = request.data
			protip_objs = ProTip.objects.all()
			serializer = None
			if protip_objs:
				serializer = ProTipSerializer(protip_objs.last(), data)
			else:
				serializer = ProTipSerializer(data=data, partial=True)
			if serializer.is_valid():
				serializer.save()
				response['data'] = serializer.data
				return Response(response, status=status.HTTP_201_CREATED)
			else:
				response['msg'] = 'error'
				response['error'] = serializer.errors
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		response = {}
		try:
			protip_obj = ProTip.objects.all().last()
			serializer = ProTipSerializer(protip_obj)
			response['data'] = serializer.data
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetCandidateSummaryData(APIView):
	def get(self, request, candidate_id):
		response = {}
		try:
			try:
				candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
				withdraws = len(json.loads(candidate_obj.withdrawed_op_ids))
			except:
				withdraws = 0
			one_year = datetime.now() - timedelta(days=365)
			interviews = Interview.objects.filter(candidate__candidate_id=candidate_id, interview_date_time__gte=one_year).count()
			likes = CandidateMarks.objects.filter(candidate_id=candidate_id, thumbs_up=True).count()
			passes = CandidateMarks.objects.filter(candidate_id=candidate_id, thumbs_down=True).count()
			golden_glove = CandidateMarks.objects.filter(candidate_id=candidate_id, golden_gloves=True).count()
			hires = Hired.objects.filter(candidate_id=candidate_id).count()
			response['withdraws'] = withdraws
			response['interviews'] = interviews
			response['likes'] = likes
			response['passes'] = passes
			response['golden_glove'] = golden_glove
			response['hires'] = hires
			response['offers'] = 0
			response['final'] = 0
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetLinkedinData(APIView):
	# permission_classes = (permissions.IsAuthenticated,)

	"""
		This API takes the profile url of a linkeding user and fetches all the data
		It uses API from Proxycurl.
	"""

	def get(self, request):
		response = {}
		try:
			url = request.query_params.get('url')
			if url:
				res = {}
				api_endpoint = 'https://nubela.co/proxycurl/api/v2/linkedin'
				linkedin_profile_url = url
				api_key = settings.PROXYCURL_TOKEN
				header_dic = {'Authorization': 'Bearer ' + api_key}

				res = requests.get(api_endpoint,
					params={
						"url": linkedin_profile_url,
						"personal_email": "include",
						"personal_contact_number": "include"
					},
					headers=header_dic
				)
				if res.status_code == 200:
					data = res.json()
					print(data)
					profile_pic_url = data['profile_pic_url']
					if profile_pic_url:
						resp = requests.get(profile_pic_url)
						fp = BytesIO()
						fp.write(resp.content)
						file_name = linkedin_profile_url.split("/")[-1]
						p_fs = FileSystemStorage()
						profile_filename = p_fs.save(file_name, fp)
						uploaded_profile_photo = p_fs.url(profile_filename)
					else:
						uploaded_profile_photo = None
					# response['profile_pic_url'] = uploaded_profile_photo
					response['profile_photo'] = uploaded_profile_photo
					response['about'] = data['summary']
					response['references'] = data['recommendations']
					response['first_name'] = data['first_name']
					response['last_name'] = data['last_name']
					response['full_name'] = data['full_name']
					response['occupation'] = data['occupation']
					response['headline'] = data['headline']
					response['summary'] = data['summary']
					response['country'] = data['country_full_name']
					response['city'] = data['city']
					response['state'] = data['state']
					response['experiences'] = data['experiences']
					response['education'] = data['education']
					response['languages'] = data['languages']
					response['personal_numbers'] = data['personal_numbers']
					response['personal_emails'] = data['personal_emails']
				elif res.status_code == 404:
					response['msg'] = 'Profile not found'
				else:
					response['msg'] = 'something went wrong'
					response['api-code'] = res.status_code
			else:
				response['msg'] = 'No or wrong url passed'
			null = None
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GenerateZohoMeeting(APIView):
	def post(self, request):
		try:
			response = {}
			data = request.data
			presenter = request.data.get('presenter')
			# presenter = settings.ZOHO_EMAIL
			date = request.data.get('date')
			start_time = request.data.get('startTime')
			date = request.data.get('date')
			start_date_time = datetime.strptime(date + " %d:%02d" % (request.data.get('startTime')['hour'], request.data.get('startTime')['minute']), "%m-%d-%Y %H:%M")
			# "Jan 31, 2023 7:00 PM"
			meeting_start = start_date_time.strftime("%b %d, %Y %I:%M %p")			
			try:

				# Get the ZUID of the presenter
				# Get the auth token
				presenter_zuid = None
				url = "https://accounts.zoho.com/oauth/v2/token?refresh_token={}&client_id={}&client_secret={}&grant_type=refresh_token".format(settings.ZOHO_REFRESH_TOKEN_ACC, settings.ZOHO_CLIENT_ID, settings.ZOHO_CLIENT_SECRET)
				payload = {}
				headers = {}
				zoho_response = requests.request("POST", url, headers=headers, data=payload)
				resp = zoho_response.json()
				access_token = resp.get('access_token')
				if access_token:
					url = "https://meeting.zoho.com/api/v2/{}/user".format(settings.ZSOID)
					headers = {
					  'Content-Type': 'application/json;charset=UTF-8',
					  'Authorization': 'Zoho-oauthtoken {}'.format(access_token),
					}
					payload = {}
					zoho_response = requests.request("GET", url, headers=headers, data=payload)
					resp = zoho_response.json()
					representation = resp.get('representation')
					if representation:
						for rep in representation:
							if rep.get('emailId') == presenter:
								presenter_zuid = rep.get('zuid')
								print(presenter_zuid)
				else:
					return Response({'msg': 'error generating user auth token', 'zoho-resp': resp}, status=status.HTTP_400_BAD_REQUEST)

				url = "https://accounts.zoho.com/oauth/v2/token?refresh_token={}&client_id={}&client_secret={}&grant_type=refresh_token".format(settings.ZOHO_REFRESH_TOKEN, settings.ZOHO_CLIENT_ID, settings.ZOHO_CLIENT_SECRET)
				payload={}

				zoho_response = requests.request("POST", url, headers=headers, data=payload)
				resp = zoho_response.json()
				access_token = resp.get('access_token')
				if access_token:
					url = "https://meeting.zoho.com/api/v2/{}/sessions.json".format(settings.ZSOID)
					payload = json.dumps({
					  "session": {
					    "topic": data.get('subject'),
					    "presenter": str(783416134),
					    "startTime": meeting_start,
					    "duration": 3600000,
					    "timezone": "America/Cayman",
					    "participants": [
					      {
					        "email": data.get('toEmails').split(',')
					      }
					    ]
					  }
					})
					headers = {
					  'Authorization': 'Zoho-oauthtoken {}'.format(access_token),
					  'Content-Type': 'application/json',
					}
					zoho_response = requests.request("POST", url, headers=headers, data=payload)
					resp = zoho_response.json()
					if resp.get('session'):
						response['msg'] = 'success'
						response['meeting_link'] = resp['session']['joinLink']
						response['meeting_pwd'] = resp['session']['pwd']
						response['meetingKey'] = resp['session']['meetingKey']
					else:
						response['msg'] = 'meeting not created'
						response['error'] = resp
					# update meeting and add co host
					try:
						url = "https://meeting.zoho.com/api/v2/{}/sessions/{}.json".format(settings.ZSOID, response['meetingKey'])
						payload = json.dumps({
						  "session": {
						    "coHost": [
						      {
						        "name": request.data.get('presenter'),
						        "email": data.get('toEmails').split(',')[0]
						      }
						    ]
						  }
						})
						zoho_response = requests.request("PUT", url, headers=headers, data=payload)
						resp = zoho_response.json()
						response['update-resp'] = resp
					except Exception as e:
						response['error-update'] = str(e)
				else:
					return Response({'msg': 'error generating auth token', 'zoho-resp': resp}, status=status.HTTP_400_BAD_REQUEST)
			except Exception as e:
				response['msg'] = 'error'
				response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
 

class GetEmbedCode(APIView):
	def get(self, request):
		try:
			response = {}
			data = request.GET
			# get auth token
			url = "https://accounts.zoho.com/oauth/v2/token?refresh_token={}&client_id={}&client_secret={}&grant_type=refresh_token".format(settings.ZOHO_REFRESH_TOKEN, settings.ZOHO_CLIENT_ID, settings.ZOHO_CLIENT_SECRET)
			payload={}
			headers = {}

			zoho_response = requests.request("POST", url, headers=headers, data=payload)
			resp = zoho_response.json()
			access_token = resp.get('access_token')
			if access_token:
				url = "https://meeting.zoho.com/api/v2/{}/sessions/{}.json".format(settings.ZSOID, data.get('meetingKey'))
				payload={}
				headers = {
				'Authorization': 'Zoho-oauthtoken {}'.format(access_token),
				}
				zoho_response = requests.request("GET", url, headers=headers, data=payload)
				resp = zoho_response.json()
				if resp.get('session'):
					response['msg'] = 'success'
					response['meetingEmbedUrl'] = resp['session']['meetingEmbedUrl']
				else:
					response['msg'] = 'embed code not fetched'
					response['error'] = resp
				return Response(response, status=status.HTTP_200_OK)
			else:
				return Response({'msg': 'error generating auth token', 'zoho-resp': resp}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Offer candidate view
class OfferCandidateView(APIView):
	def post(self, request, op_id, candidate_id):
		response = {}
		try:
			openposition_obj = OpenPosition.objects.get(id=op_id)
			offer_objs = Offered.objects.filter(op_id=op_id)
			hiring_group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
			client_obj = Client.objects.get(id=openposition_obj.client)
			offer_obj, created = Offered.objects.get_or_create(candidate_id=candidate_id, op_id=op_id)
			# send hired notitcation to CA
			try:
				tasks.send_app_notification.delay(client_obj.ae_assigned, 'A candidate has been marked for offer for the {} opening at {}'.format(openposition_obj.position_title, client_obj.company_name))
				tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'A candidate has been marked for offer for the {} opening at {}'.format(openposition_obj.position_title, client_obj.company_name))
				tasks.send_app_notification.delay(client_obj.key_username, 'A candidate has been marked for hire for the {} opening.'.format(openposition_obj.position_title))
				tasks.push_notification.delay([client_obj.key_username], 'Qorums Notification', 'A candidate has been marked for offer for the {} opening.'.format(openposition_obj.position_title))
				
				if hiring_group_obj.hr_profile:
					hr_profile = hiring_group_obj.hr_profile
					tasks.send_app_notification.delay(hr_profile.user.username, 'A candidate has been marked for offer for the {} opening.'.format(openposition_obj.position_title))
					tasks.push_notification.delay([hr_profile.user.username], 'Qorums Notification', 'A candidate has been marked for offer for the {} opening.'.format(openposition_obj.position_title))
			except Exception as e:
				response['notitication-error'] = str(e)
			response['msg'] = 'success'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def put(self, request, op_id, candidate_id):
		response = {}
		try:
			offer_obj = Offered.objects.filter(candidate_id=candidate_id, op_id=op_id).delete()
			response['msg'] = 'success'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def get(self, request, op_id, candidate_id):
		response = {}
		try:
			offer_obj = Offered.objects.filter(candidate_id=candidate_id, op_id=op_id)
			if offer_obj:
				response['offered'] = True
			else:
				response['offered'] = False
			response['msg'] = 'success'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


def CognitoCallback(request):
    try:
        data = request.GET
        code = data.get('code')
        state = data.get('state')
        scope = data.get('scope')
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            'client_secret.json',
            scopes=SCOPES,
            state=state
        )
        flow.redirect_uri = 'https://qorums.com/oauth/callback/1'

        authorization_response = 'https://qorums.com/oauth/callback/1?state={}&code={}'.format(state, code)
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        service = build('calendar', 'v3', credentials=credentials)
        meeting_data = MeetingData.objects.filter(state=state).last()
        if meeting_data:
            event = {
                'conferenceDataVersion':1,
                'summary': meeting_data.interview_title,
                'start': {
                    'dateTime': meeting_data.start_time + ":00",
                    'timeZone': meeting_data.timezone,
                },
                'end': {
                    'dateTime': meeting_data.end_time + ":00",
                    'timeZone': meeting_data.timezone,
                },
                'attendees': [
                    {'email': meeting_data.candidate_email},
                ],
                "conferenceData": {
                    "createRequest": {
                        "requestId": "sample123", 
                        "conferenceSolutionKey": {
                            "type": "hangoutsMeet"
                        }
                    }
                }
            }
            event = service.events().insert(calendarId='primary', body=event, sendNotifications='true', conferenceDataVersion=1).execute()
            link = event.get('hangoutLink')
            sent = send_meeting_link(link, state)
            if sent:
                applied_position = meeting_data.applied_position
                applied_position.data['meeting_link'] = link
                applied_position.save()
                return render(request, 'meeting_created.html')
            else:
                HttpResponse("Meeting not created. meeting data not found. State is {}".format(state))
        else:
            return HttpResponse("Meeting not created. meeting data not found. State is {}".format(state))
    except Exception as e:
        print(e)
        return HttpResponse("Something went wrong - {}".format(str(e)))


class CognitoLoginView(APIView):
	
	permission_classes = (permissions.IsAuthenticated,)
	
	def get(self, request, format=None):
		try:
			user = request.user
			profile = user.profile
			data = {
				"username": user.username,
				"name": user.first_name,
				"first_name": user.first_name,
				"last_name": None,
				"first_log": profile.first_log,
				"role": "Client Admin",
				"client_id": profile.client,
				"profile_photo": profile.profile_photo,
				"phone_number": profile.phone_number,
				"email": user.email,
				"skype_id": profile.skype_id,
				"tnc_accepted": profile.tnc_accepted,
				"profile_id": profile.id
			}
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': 'error occured', 'error': str(e)}, status=status.HTTP_200_OK)


class GetClientSummary(APIView):

	permission_classes = (permissions.IsAuthenticated,)
	
	def get(self, request, format=None):
		try:
			data = {}
			user = request.user
			client_obj = Client.objects.get(id=int(user.profile.client))
			client_serializer = ClientSerializer(client_obj)
			data['client_data'] = client_serializer.data
			hiring_member_objs = Profile.objects.filter(roles__contains="is_htm", client=int(user.profile.client))			
			members_list = []
			for i in hiring_member_objs:
				temp_dict = {}
				temp_dict["id"] = i.id
				temp_dict["name"] = i.user.first_name + ' ' + i.user.last_name
				temp_dict["username"] = i.user.username
				temp_dict["mobile_no"] = i.phone_number
				temp_dict["email"] = i.email
				temp_dict["profile_photo"] = i.profile_photo
				if i.job_title:
					temp_dict['job_title'] = i.job_title
				else:
					temp_dict['job_title'] = '---'
				members_list.append(temp_dict)
			data['hiring_managers'] = members_list
			hiring_group_objs = HiringGroup.objects.filter(client_id=client_obj.id, disabled=False)
			hiring_groups_serializer = HiringGroupSerializer(hiring_group_objs, many=True)
			data['hiring_groups_data'] = hiring_groups_serializer.data
			senior_managers = []
			client_id = request.user.profile.client
			sm_objs = Profile.objects.filter(is_sm=True, client=client_id)
			for i in sm_objs:
				temp_dict = {}
				temp_dict["id"] = i.id
				temp_dict["name"] = i.user.first_name + ' ' + i.user.last_name
				temp_dict["username"] = i.user.username
				temp_dict["mobile_no"] = i.phone_number
				temp_dict["email"] = i.email
				temp_dict['profile_photo'] = i.profile_photo
				temp_dict['client_id'] = i.client
				senior_managers.append(temp_dict)
			data['senior_manager'] = senior_managers
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': 'error occured', 'error': str(e)}, status=status.HTTP_200_OK)


class GetInterviewList(APIView):

	permission_classes = (permissions.IsAuthenticated,)
	
	def get(self, request, candidate_id):
		try:
			response = {}
			interviews = Interview.objects.filter(candidate__candidate_id=candidate_id).filter(disabled=False)
			data = []
			for interview in interviews:
				try:
					temp_dict = {}
					openposition_obj = OpenPosition.objects.get(id=interview.op_id.id)
					# htm_obj = Profile.objects.get(id=interview.htm)
					# zoom_temp = {}
					temp_dict['link'] = interview.zoom_link
					# timedelta = interview.interview_date_time - datetime.now()
					# if timedelta.seconds > 1800:
					# 	zoom_temp['disabled'] = True
					# else:
					temp_dict['disabled'] = False
					temp_dict['date'] = interview.interview_date_time.strftime("%m-%d-%Y")
					temp_dict['time'] = interview.interview_date_time.strftime("%I:%M %p")
					temp_dict['interview_id'] = interview.id
					temp_dict['op_id'] = openposition_obj.id
					temp_dict['position'] = openposition_obj.position_title
					temp_dict['interview_date_time'] = interview.interview_date_time
					interviewer_name = ", "
					interview_names = []
					interview_ids = []
					for i in interview.htm.all():
						interview_names.append(i.user.get_full_name())
					# if interviews.filter(zoom_link=interview.zoom_link, interview_date_time=interview.interview_date_time, interview_type=interview.interview_type):
						# for t_i in interviews.filter(zoom_link=interview.zoom_link, interview_date_time=interview.interview_date_time, interview_type=interview.interview_type):
							# temp_htm_obj = Profile.objects.get(id=t_i.htm)
							# interview_names.append(temp_htm_obj.user.get_full_name())
							# interview_ids.append(temp_htm_obj.id)
							# temp_dict['interview_id'] = interview_ids
					temp_dict['interviewer_name'] = interviewer_name.join(interview_names)
					temp_dict['interview_type'] = interview.interview_type
					if interview.accepted:
						try:
							temp_dict['meeting_link'] = interview.zoom_link.split('?')[0]
						except:
							pass
					temp_dict['accepted'] = interview.accepted
					if temp_dict in data:
						print("yes")
					else:
						data.append(temp_dict)
				except Exception as e:
					print(e)
			response['data'] = data
			response['msg'] = 'success'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': 'error occured', 'error': str(e)}, status=status.HTTP_200_OK)


class CandidateScheduleView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			candidate_id = int(request.query_params.get('candidate_id'))
			candidate_availability_objs = CandidateAvailability.objects.filter(candidate_id=candidate_id)
			if candidate_availability_objs:
				response['msg'] = 'schedule found'
				avails = json.loads(candidate_availability_objs[0].availability)
				avails.sort(key=lambda item:item['date'])
				show_shedule_data = []
				prev_date = None
				prev_time = None
				for avail in avails:
					if prev_date == avail['date']:
						if prev_time == avail['hours'][0]['startTime']:
							last = show_shedule_data[-1]
							show_shedule_data.pop()
							last['hours'][0]['endTime'] = avail['hours'][0]['endTime']
							prev_time = avail['hours'][0]['endTime']
							show_shedule_data.append(last)
						else:
							show_shedule_data.append(avail)
					else:
						prev_date = avail['date']
						prev_time = avail['hours'][0]['endTime']
						show_shedule_data.append(avail)

					# if avail['date'] in show_shedule_data:
					# 	for i in avail['hours']:
					# 		show_shedule_data[avail['date']].append(i)
					# else:
					# 	show_shedule_data[avail['date']] = []
					# 	for i in avail['hours']:
					# 		show_shedule_data[avail['date']].append(i)
				response['scheduled_found'] = True
				response['schedule_data'] = show_shedule_data
				response['show_shedule_data'] = avails
			else:
				response['candidate_id'] = candidate_id
				response['msg'] = 'schedule not found'
				response['scheduled_found'] = False
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)

	def post(self, request):
		try:
			response = {}
			candidate_id = request.data.get('candidate_id')
			days_availability = request.data.get('availableDays')
			new_availability = []
			for i in days_availability:
				for j in i["hours"]:
					lited_start = j["startTime"].split(":")
					start_hour = int(lited_start[0])
					start_min = int(lited_start[1])
					lited_end = j["endTime"].split(":")
					end_hour = int(lited_end[0])
					end_min = int(lited_end[1])
					run = True
					while run:
						if start_hour == end_hour and start_min == end_min:
							run = False
						else:
							if start_min == 30:
								new_start_hour = start_hour + 1
								new_start_min = 0
							else:
								new_start_hour = start_hour
								new_start_min = 30
							temp_dict = {}
							temp_dict["day"] = 1
							temp_dict["date"] = i["date"]
							temp_dict["hours"] = [{"startTime": "{}:{}".format(start_hour, start_min), "endTime": "{}:{}".format(new_start_hour, new_start_min),}]
							new_availability.append(temp_dict)
							start_hour = new_start_hour
							start_min = new_start_min
				response['msg'] = 'Availability Updated'
			candidate_availability_objs = CandidateAvailability.objects.filter(candidate_id=candidate_id)
			if candidate_availability_objs:
				candidate_availability_obj = candidate_availability_objs[0]
				candidate_avail = json.loads(candidate_availability_obj.availability)
				add_avails = []
				# # for avail in new_availability:
				# # 	# avail = json.loads(avail)
				# # 	avail["htm_created"] = True
				# # 	t_avail = avail
				# # 	avail["htm_created"] = False
				# # 	f_avail = avail
				# # 	del avail["htm_created"]
				# # 	n_avail = avail
				# # 	if t_avail in htm_avail or f_avail in htm_avail or n_avail in htm_avail:
				# # 		pass
				# # 	else:
				# # 		add_avails.append(avail)
				# htm_availability_obj.availability = json.dumps(htm_avail + add_avails)
				candidate_availability_obj.availability = json.dumps(new_availability)
				candidate_availability_obj.save()
				response['msg'] = 'schedule updated'
			else:
				CandidateAvailability.objects.create(
					candidate_id=candidate_id,
					availability=json.dumps(new_availability)
				)
				response['msg'] = 'schedule added'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetPositionToAssociate(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, candidate_id):
		candidate_obj = Candidate.objects.filter(candidate_id=candidate_id).first()
		if candidate_obj:
			if request.user.is_superuser:
				open_position = OpenPosition.objects.exclude(Q(id__in=json.loads(candidate_obj.associated_op_ids))| Q(id__in=json.loads(candidate_obj.withdrawed_op_ids))).filter(drafted=False, archieved=False, filled=False)
			elif "is_ae" in request.user.profile.roles:
				open_position = OpenPosition.objects.filter(client__in=json.loads(request.user.profile.client)).exclude(Q(id__in=json.loads(candidate_obj.associated_op_ids))| Q(id__in=json.loads(candidate_obj.withdrawed_op_ids))).filter(drafted=False, archieved=False, filled=False)
			elif "is_htm" in request.user.profile.roles:
				groups = HiringGroup.objects.filter(hod=request.user.profile.id).values_list('group_id', flat=True)
				open_position = OpenPosition.objects.filter(client=int(request.user.profile.client)).exclude(Q(id__in=json.loads(candidate_obj.associated_op_ids))| Q(id__in=json.loads(candidate_obj.withdrawed_op_ids))).filter(drafted=False, archieved=False, filled=False)
				open_position = open_position.filter(hiring_group__in=groups)
			else:
				try:
					open_position = OpenPosition.objects.filter(client=int(request.user.profile.client)).exclude(Q(id__in=json.loads(candidate_obj.associated_op_ids))| Q(id__in=json.loads(candidate_obj.withdrawed_op_ids))).filter(drafted=False, archieved=False, filled=False)
				except Exception as e:
					print(e)
					open_position = []
			response = {}
			data = []
			for position in open_position:
				temp_dict = {}
				temp_dict['id'] = position.id
				temp_dict['position_title'] = position.position_title
				temp_dict['client_id'] = position.client
				data.append(temp_dict)
			response['data'] = data
			response['msg'] = 'success'
			return Response(response, status=status.HTTP_200_OK)
		else:
			response = {}
			response['error'] = 'Candidate with given id not found.'
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetCandidateInterviews(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, candidate_id):
		try:
			response = {}
			interview_objs = Interview.objects.get(candidate__candidate_id=candidate_id)
			data = []
			for interview in interview_objs:
				try:
					openposition_obj = OpenPosition.objects.get(id=interview.op_id)
					temp_dict = {}
					temp_dict['op_id'] = openposition_obj.id
					temp_dict['position_name'] = openposition_obj.position_title
					temp_dict['accepted'] = interview.accepted
					data.append(temp_dict)
				except Exception as e:
					print(e)
					pass
			response['data'] = data
			response['msg'] = 'success'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['msg'] = 'Candidate with given id not found.'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class UpdateInterviewResp(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request, interview_id):
		try:
			response = {}
			interview_obj = Interview.objects.get(id=interview_id)
			interview_obj.accepted = request.data.get('accepted')
			interview_obj.save()
			response['data'] = None
			response['msg'] = 'updated'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['msg'] = 'Candidate with given id not found.'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetInterviewerFreeSlots(APIView):
	# permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, htm_id):
		try:
			interview = Interview.objects.get(id=htm_id)
			htm_ids = interview.htm.all().values_list("id", flat=True)
			availability_data = []
			try:
				for member_availability in HTMAvailability.objects.filter(htm_id__in=htm_ids):
					avails = json.loads(member_availability.availability)
					avails.sort(key=lambda item:item['date'])
					for avail in avails:
						interview = Interview.objects.filter(htm__id__in=[htm_id], texted_start_time=json.dumps(avail)).filter(disabled=False)
						if interview:
							pass
						else:
							availability_data.append(avail)
			except Exception as e:
				print(e)
			availability_data.sort(key=lambda item:item['date'])
			response = {}
			response['msg'] = 'success'
			response['data'] = availability_data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['msg'] = 'something went wrong'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetCandidateCalendar(APIView):
	def get(self, request, candidate_id):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			scheduled_data = []
			eschedule_data = []
			for interview in Interview.objects.filter(candidate__candidate_id=candidate_id).filter(disabled=False):
				temp_dict = {}
				availability = json.loads(interview.texted_start_time)
				try:
					openposition_obj = OpenPosition.objects.get(id=interview.op_id.id)
					availability['position_name'] = openposition_obj.position_title
				except Exception as e:
					availability['position_name'] = None
				availability["scheduled"] = True
				availability['candidate_name'] = candidate_obj.name
				start = datetime.strptime(availability['hours'][0]['startTime'], "%H:%M")
				end = datetime.strptime(availability['hours'][0]['endTime'], "%H:%M")
				availability['time'] = "{} to {}".format(start.strftime("%I:%M %p"), end.strftime("%I:%M %p"))
				try:
					interviewers_names = interview.htm.all().annotate(full_name=Concat("user__first_name", V(" "), "user__last_name")).values_list("full_name", flat=True)
					temp_dict['htm_name'] =  ", ".join(interviewers_names)
				except Exception as e:
					temp_dict['htm_name'] = [None]
				if interview.accepted:
					temp_dict['color'] = '#5cba83'
				else:
					temp_dict['color'] = '#ff0000'
				temp_dict['availability'] = availability
				temp_dict['op_id'] = interview.op_id.id
				scheduled_data.append(temp_dict)
				htm_name = temp_dict.pop('htm_name')
				eschedule_data.append([htm_name, temp_dict])
			schedule_data = {}
			for schedule in eschedule_data:
				if json.dumps(schedule[1]) in schedule_data:
					schedule_data[json.dumps(schedule[1])] = "{}, {}".format(schedule_data[json.dumps(schedule[1])], str(schedule[0]))
				else:
					schedule_data[json.dumps(schedule[1])] = schedule[0]
			scheduled_data = []
			for sd in schedule_data.items():
				temp_dict = json.loads(sd[0])
				temp_dict['htm_names'] = sd[1]
				scheduled_data.append(temp_dict)
			scheduled_data.sort(key=lambda item:item['availability']['date'])
			return Response({"data": scheduled_data}, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['msg'] = 'something went wrong'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class UpdateCandidateDetail(APIView):
	def put(self, request):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=request.data.get('candidate_id'))
			candidate_obj.work_auth = request.data.get("work_auth")
			candidate_obj.personal_notes = request.data.get("personal_notes")
			candidate_obj.additional_info = request.data.get("additional_info")
			candidate_obj.currency = request.data.get('currency')
			candidate_obj.salaryRange = request.data.get("salaryRange")
			candidate_obj.updated_at =  datetime.now()
			candidate_obj.save()
			return Response({"msg": "updated"}, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['msg'] = 'candidate not found'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class SendProMarkettingEmail(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			response = {}
			body = request.data.get('body')
			to = request.data.get('toEmails').split(',')
			subject = request.data.get('subject')
			tasks.send.delay(subject, body, 'text', to, request.user.email, request.user.get_full_name())
			response['message'] = 'mails sent'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['msg'] = 'candidate not found'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)

class MarkProMarkettingView(APIView):
	def put(self, request, candidate_id):
		try:
			obj = CandidateAssociateData.objects.get(candidate__id=candidate_id)
			obj.pro_marketting = True
			obj.save()
			return Response({"msg": "updated"}, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['msg'] = 'candidate not found'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetProCandidateList(APIView):
	def put(self, request, candidate_id):
		try:
			obj = CandidateAssociateData.objects.get(candidate__id=candidate_id)
			obj.pro_marketting = True
			obj.save()
			return Response({"msg": "updated"}, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['msg'] = 'candidate not found'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class RemoveCandidate(APIView):
	def post(self, request, op_id, candidate_id):
		try:
			response = {}
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			associated_op_ids = json.loads(candidate_obj.associated_op_ids)
			try:
				associated_op_ids.remove(op_id)
				CandidateAssociateData.objects.filter(candidate=candidate_obj, open_position__id=op_id).delete()
			except:
				pass
			Hired.objects.filter(candidate_id=candidate_id, op_id=op_id).delete()
			Offered.objects.filter(candidate_id=candidate_id, op_id=op_id).delete()
			candidate_obj.associated_op_ids = json.dumps(associated_op_ids)
			candidate_obj.save()
			response['msg'] = 'Candidate Removed'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GetModeratorToken(APIView):
	def post(self, request, host_id):
		auth_code = get_iotum_auth_code()
		try:
			url = "https://qorums-internal.meet.qorums.com/enterprise_api/conference/create/reservationless"
			payload = json.dumps({
				"auth_token": auth_code,
				"host_id": host_id,
				"one_time_access_code": True,
				"secure_url": False
			})
			headers = {
				'Content-Type': 'application/json',
			}
			response = requests.request("POST", url, headers=headers, data=payload)
			resp_json = response.json()
			if "moderator_token" in resp_json:
				print(resp_json)
				return Response({"moderator_token": resp_json.get("moderator_token")}, status=status.HTTP_200_OK)
			else:
				return Response({"moderator_token": "None", "error": "something went wrong"}, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)


class GenerateMeeting(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			response = {}
			data = request.data
			profile = request.user.profile
			date = request.data.get('date')
			start_time = request.data.get('startTime')
			date = request.data.get('date')
			start_date_time = datetime.strptime(date + " %d:%02d" % (request.data.get('startTime')['hour'], request.data.get('startTime')['minute']), "%m-%d-%Y %H:%M")
			meeting_start = start_date_time.strftime("%Y-%m-%d %H:%M:%S") # "2023-03-23 23:00:00"
			emails = data.get('toEmails').split(',')
			emails_list = []
			for email in emails:
				temp_dict = {}
				temp_dict['email'] = email
				# if Candidate.objects.filter(email=email):
				# 	temp_dict['moderator'] = False
				# else:
				temp_dict['moderator'] = False
				emails_list.append(temp_dict)
			
			try:
				meeting_url, moderator_token, conference_id = get_host_and_create_meeting(profile, data.get("subject"), meeting_start, emails_list)
				url = "{}?moderator_token={}".format(meeting_url, moderator_token)
				return Response({"meeting_link": url, "conference_id": conference_id}, status=status.HTTP_200_OK)
			except Exception as e:
				response['msg'] = "Some error occured while creating QVideo's HTM ID, try with another email"
				response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': "LinkedIn data not available now. Please try after sometime."}, status=status.HTTP_400_BAD_REQUEST)


class  UpdateCandidateData(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request, candidate_id):
		try:
			response = {}
			data = request.data
			obj = Candidate.objects.get(candidate_id=candidate_id)
			serializer = CandidateSerializer(obj, data=data, partial=True)
			if serializer.is_valid():
				serializer.save()
				return Response(serializer.data, status=status.HTTP_200_OK)
			else:
				response['msg'] = 'error'
				response['error'] = str(e)
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetCHSM3(APIView):
	# permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			openposition_obj =  OpenPosition.objects.get(id=op_id)
			client_obj = Client.objects.get(id=openposition_obj.client)
			client_admin =  Profile.objects.get(is_ca=True, user__username=client_obj.key_username)
			hiring_groups = HiringGroup.objects.filter(group_id=openposition_obj.hiring_group)
			duplicates = []
			data = []
			client_admin_dict = {}
			client_admin_dict['id'] = client_admin.id
			client_admin_dict['name'] = client_admin.user.first_name + ' ' + client_admin.user.last_name
			client_admin_dict['email'] = client_admin.email
			client_admin_dict['role'] = "Client Admin"
			client_admin_dict['profile_picture'] = client_admin.profile_photo
			data.append(client_admin_dict)
			for group in hiring_groups:
				try:
					hm_profile = group.hod_profile
					temp_dict = {}
					temp_dict['id'] = hm_profile.id
					temp_dict['name'] = hm_profile.user.first_name + ' ' + hm_profile.user.last_name
					temp_dict['email'] = hm_profile.email
					temp_dict['role'] = "Hiring Manager"
					temp_dict['profile_picture'] = hm_profile.profile_photo
					if hm_profile.id not in duplicates:
						data.append(temp_dict)
						duplicates.append(hm_profile.id)
				except Exception as e:
					print(e)
			for sm_profile in Profile.objects.filter(is_sm=True, client=str(client_obj.id)):
				temp_dict = {}
				temp_dict['id'] = sm_profile.id
				temp_dict['name'] = sm_profile.user.first_name + ' ' + sm_profile.user.last_name
				temp_dict['email'] = sm_profile.email
				temp_dict['role'] = "Senior Manager"
				temp_dict['profile_picture'] = sm_profile.profile_photo
				if sm_profile.id not in duplicates:
					data.append(temp_dict)
					duplicates.append(sm_profile.id)
			
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
		

class CompareCandidateMarks(APIView):
	def post(self, request, op_id, candidate_id):
		try:
			openposition_obj = OpenPosition.objects.get(id=op_id)
			group_obj = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
			all_colors = ['#a7a1a1']
			htms  = request.data.get("htmsId")
			row1 = ['Skill', 'Average']
			for i in htms:
				htm_obj = Profile.objects.get(id=i)
				row1.append(htm_obj.user.get_full_name())
				try:
					color = [d["color"] for d in group_obj.members_color if i == d["htm"]][0]
				except Exception as e:
					color = "#000000"
				all_colors.append(color)
			response = {}
			
			
			voting_data = [
				row1,
				[openposition_obj.init_qualify_ques_1, 0],
				[openposition_obj.init_qualify_ques_2, 0],
				[openposition_obj.init_qualify_ques_3, 0],
				[openposition_obj.init_qualify_ques_4, 0],
				[openposition_obj.init_qualify_ques_5, 0],
				[openposition_obj.init_qualify_ques_6, 0],
				[openposition_obj.init_qualify_ques_7, 0],
				[openposition_obj.init_qualify_ques_8, 0],
			]
			response["quesAnsData"] = []
			response["quesAnsData"].append({"quesFor": openposition_obj.init_qualify_ques_1, "quesText": openposition_obj.init_qualify_ques_suggestion_1, "comments": {}})
			response["quesAnsData"].append({"quesFor": openposition_obj.init_qualify_ques_2, "quesText": openposition_obj.init_qualify_ques_suggestion_2, "comments": {}})
			response["quesAnsData"].append({"quesFor": openposition_obj.init_qualify_ques_3, "quesText": openposition_obj.init_qualify_ques_suggestion_3, "comments": {}})
			response["quesAnsData"].append({"quesFor": openposition_obj.init_qualify_ques_4, "quesText": openposition_obj.init_qualify_ques_suggestion_4, "comments": {}})
			response["quesAnsData"].append({"quesFor": openposition_obj.init_qualify_ques_5, "quesText": openposition_obj.init_qualify_ques_suggestion_5, "comments": {}})
			response["quesAnsData"].append({"quesFor": openposition_obj.init_qualify_ques_6, "quesText": openposition_obj.init_qualify_ques_suggestion_6, "comments": {}})
			response["quesAnsData"].append({"quesFor": openposition_obj.init_qualify_ques_7, "quesText": openposition_obj.init_qualify_ques_suggestion_7, "comments": {}})
			response["quesAnsData"].append({"quesFor": openposition_obj.init_qualify_ques_8, "quesText": openposition_obj.init_qualify_ques_suggestion_8, "comments": {}})
			# [
			# 		['Skill', 'Average', 'Nelly Korda Votes', 'Justin Thomas Votes', 'Nigel Ng Votes'],
			# 		['Python', 8.1, 7.2, 5.4, 6.8],
			# 		['React', 5.4, 5.1, 4.2, 4.5],
			# 		['AWS', 6.3, 7.2, 3.4, 6.8],
			# 		['Citrix', 8.2, 7.1, 5.4, 6.7],
			# ],	
			# 
			htm_count = 2
			for htm in htms:
				objs = CandidateMarks.objects.filter(candidate_id=candidate_id, marks_given_by=htm, op_id=op_id)
				if objs:
					marks_obj  =  objs.first()
					marks = [
						voting_data[1].append(marks_obj.criteria_1_marks),
						voting_data[2].append(marks_obj.criteria_2_marks),
						voting_data[3].append(marks_obj.criteria_3_marks),
						voting_data[4].append(marks_obj.criteria_4_marks),
						voting_data[5].append(marks_obj.criteria_5_marks),
						voting_data[6].append(marks_obj.criteria_6_marks),
						voting_data[7].append(marks_obj.criteria_7_marks),
						voting_data[8].append(marks_obj.criteria_8_marks),
					]
					response['quesAnsData'][0]["comments"][row1[htm_count]] = marks_obj.suggestion_1
					response['quesAnsData'][1]["comments"][row1[htm_count]] = marks_obj.suggestion_2
					response['quesAnsData'][2]["comments"][row1[htm_count]] = marks_obj.suggestion_3
					response['quesAnsData'][3]["comments"][row1[htm_count]] = marks_obj.suggestion_4
					response['quesAnsData'][4]["comments"][row1[htm_count]] = marks_obj.suggestion_5
					response['quesAnsData'][5]["comments"][row1[htm_count]] = marks_obj.suggestion_6
					response['quesAnsData'][6]["comments"][row1[htm_count]] = marks_obj.suggestion_7
					response['quesAnsData'][7]["comments"][row1[htm_count]] = marks_obj.suggestion_8
					if None not in marks:
						voting_data.append(marks)
				else:
					marks = [
						voting_data[1].append(0),
						voting_data[2].append(0),
						voting_data[3].append(0),
						voting_data[4].append(0),
						voting_data[5].append(0),
						voting_data[6].append(0),
						voting_data[7].append(0),
						voting_data[8].append(0),
					]
					response['quesAnsData'][0]["comments"][row1[htm_count]] = None
					response['quesAnsData'][1]["comments"][row1[htm_count]] = None
					response['quesAnsData'][2]["comments"][row1[htm_count]] = None
					response['quesAnsData'][3]["comments"][row1[htm_count]] = None
					response['quesAnsData'][4]["comments"][row1[htm_count]] = None
					response['quesAnsData'][5]["comments"][row1[htm_count]] = None
					response['quesAnsData'][6]["comments"][row1[htm_count]] = None
					response['quesAnsData'][7]["comments"][row1[htm_count]] = None
					voting_data.append(marks)
				htm_count += 1
			response['voting_data'] = []
			for data in voting_data:
				if data[0]:
					response['voting_data'].append(data)
			count = 0
			avgs = [0,0,0,0,0,0,0,0]
			for obj in CandidateMarks.objects.filter(candidate_id=candidate_id, op_id=op_id):
				avgs[0] += obj.criteria_1_marks
				avgs[1] += obj.criteria_2_marks
				avgs[2] += obj.criteria_3_marks
				avgs[3] += obj.criteria_4_marks
				avgs[4] += obj.criteria_5_marks
				avgs[5] += obj.criteria_6_marks
				avgs[6] += obj.criteria_7_marks
				avgs[7] += obj.criteria_8_marks
				count += 1
			for i in range(1, len(response['voting_data'])):
				if count > 0:
					response['voting_data'][i][1] = round(avgs[i-1]/count, 1)
				else:
					response['voting_data'][i][1] = 0
			response["htmColorsArr"] = all_colors
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EvaluationCommentView(APIView):

	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			data = request.data
			data['given_by'] = request.user.profile.id
			serializer = EvaluationCommentSerializer(data=data)
			if serializer.is_valid():
				serializer.save()
				return Response({"msg": "Success"}, status=status.HTTP_200_OK)
			else:
				return Response({'msg': str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
	
	def get(self, request):
		try:
			data = request.GET
			objs = EvaluationComment.objects.filter(position__id=data.get("position"), candidate__candidate_id=data.get("candidate"))
			data = {}
			for obj in objs:
				temp_data = {}
				temp_data['notes'] = obj.notes
				temp_data['given_by'] = obj.given_by.user.get_full_name()
				temp_data['given_by_pic'] = obj.given_by.profile_photo
				temp_data['date'] = obj.date.strftime("%m-%d-%Y %I:%M %p")
				temp_data['label'] = "{} - {}".format(obj.position.position_title, obj.date.strftime("%m-%d-%Y %I:%M %p"))
				if obj.given_by.id in data:
					data[obj.given_by.id].append(temp_data)
				else:
					data[obj.given_by.id] = []
					data[obj.given_by.id].append(temp_data)
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CandidateChangePassword(APIView):
	def post(self, request, candidate_id):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			user_obj = User.objects.get(username=candidate_obj.username)
			if request.data.get("hashed_password"):
				user_obj.set_password(request.data.get("hashed_password"))
				user_obj.save()
				subject = 'New User Created - Qorums'
				d = {
					"user_name": "{} {}".format(candidate_obj.name, candidate_obj.last_name),
					"username": user_obj.username,
					"password": request.data.get("password"),
				}
				email_from = settings.EMAIL_HOST_USER
				recipient_list = [candidate_obj.email, ]
				htmly_b = get_template('password_reset.html')
				text_content = ""
				html_content = htmly_b.render(d)
				msg = EmailMultiAlternatives(subject, text_content, email_from, recipient_list)
				msg.attach_alternative(html_content, "text/html")
				try:
					msg.send(fail_silently=True)
				except Exception as e:
					print(e)
				return Response({'msg': "password reset"}, status=status.HTTP_200_OK)
			else:
				return Response({'msg': "password not passed"}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EndMeetingAPI(APIView):
	def post(self, request, conference_id):
		try:
			end_meeting(conference_id)
			return Response({'msg': "meeting ended"}, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, force_str, smart_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
class PasswordResetView(APIView):
	def post(self, request):
		try:
			email = request.data.get("email")
			user_obj = User.objects.filter(Q(username=email) | Q(email=email) | Q(profile__email=email)).last()
			if user_obj:
				email = user_obj.email
				if email:
					pass
				else:
					try:
						email = user_obj.profile.email
					except Exception as e:
						return Response({'msg': "User does not exits"}, status=status.HTTP_400_BAD_REQUEST)
				uidb64 = urlsafe_base64_encode(smart_bytes(user_obj.id))
				token = PasswordResetTokenGenerator().make_token(user_obj)
				url = "{}/reset-password?token={}&uidb64={}".format(settings.DOMAIN, str(token), uidb64)
				d = {
					"url": url,
					"user_name": user_obj.username
				}
				subject = "Password Reset - Qorums"
				htmly_b = get_template('reset-password.html')
				text_content = ""
				html_content = htmly_b.render(d)
				try:
					tasks.send.delay(subject, html_content, 'html', [email], settings.EMAIL_HOST_USER, "Qorums")
					# send_mail(subject, html_content, settings.EMAIL_HOST_USER, [user_obj.email])
				except Exception as e:
					return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
				return Response({'msg': "reset email sent"}, status=status.HTTP_200_OK)
			else:
				return Response({'msg': "User does not exits"}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PasswordCheckAndResetView(APIView):
	def post(self, request, uidb64, token):
		try:
			data = request.data
			id = smart_str(urlsafe_base64_decode(uidb64))
			user = User.objects.get(id=id)

			if not PasswordResetTokenGenerator().check_token(user, token):
				return Response({'msg': "Wrong token. Or link already used!"}, status=status.HTTP_400_BAD_REQUEST)
			password = data.get("password")
			id = force_str(urlsafe_base64_decode(uidb64))
			user = User.objects.get(id=id)
			if not PasswordResetTokenGenerator().check_token(user, token):
				return Response({'msg': "The code is invalid. Or link already used!"}, status=status.HTTP_400_BAD_REQUEST)
			user.set_password(password)
			user.save()
			return Response({"msg": "Password reset. Please login"}, status=status.HTTP_200_OK)
		except DjangoUnicodeDecodeError as identifier:
			try:
				if not PasswordResetTokenGenerator().check_token(user):
					return Response({'msg': "Wrong token"}, status=status.HTTP_400_BAD_REQUEST)

			except UnboundLocalError as e:
				return Response(
					{"error": "Token is not valid, please request a new one"},
					status=status.HTTP_400_BAD_REQUEST,
				)


class GetPositionSummary(APIView):

	# permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		response = {}
		try:
			open_position = OpenPosition.objects.get(id=op_id)
			dates = {}
			start = open_position.kickoff_start_date
			htm_deadlines = []
			hiring_group = None
			try:
				hiring_group = HiringGroup.objects.get(group_id=open_position.hiring_group)
				members_list = list(hiring_group.members_list.all())
				if hiring_group.hr_profile in members_list:
					members_list.remove(hiring_group.hr_profile)
			except Exception as e:
				members_list = []
			for deadline in HTMsDeadline.objects.filter(open_position=open_position):
				temp_dict = {}
				temp_dict["deadline"] = deadline.deadline.strftime("%Y-%m-%d")
				temp_dict["htm"] = deadline.htm.id
				temp_dict["htm_name"] = deadline.htm.user.get_full_name()
				try:
					temp_dict["color"] = [d["color"] for d in hiring_group.members_color if d['htm'] == deadline.htm.id][0]
				except Exception as e:
					temp_dict["color"] = None
				temp_dict["profile_pic"] = deadline.htm.profile_photo				
				htm_deadlines.append(temp_dict)
			
			if start and open_position.target_deadline:
				while start <= open_position.target_deadline:
					if start.weekday() in [5, 6]:
						bg_color = "#b5b5b5"
					else:
						bg_color = "#5cba83"
					if start == open_position.kickoff_start_date:
						stage = "kickoff"
					elif start == open_position.sourcing_deadline:
						stage = "sourcing"
					elif start == open_position.target_deadline:
						stage = "target"
					else:
						stage = None
					cur_date = start
					interview = []
					# given_interviews = CandidateMarks.objects.filter(op_id=op_id, feedback_date__year=cur_date.year, feedback_date__month=cur_date.month,feedback_date__day=cur_date.day)
					given_interviews = Interview.objects.filter(op_id__id=op_id, interview_date_time__year=cur_date.year, interview_date_time__month=cur_date.month,interview_date_time__day=cur_date.day)
					for inter in given_interviews:
						temp_dict = {}
						htms = []
						for htm in inter.htm.all():
							htms.append(htm.user.get_full_name())
						temp_dict["htmName"] = ", ".join(htms)
						# temp_dict["htmId"] = inter.marks_given_by
						color = []
						# if hiring_group:
						# 	color = [d["color"] for d in hiring_group.members_color if d['htm'] == inter.marks_given_by]
						# if color:
						# 	temp_dict["htmColorCode"] = color[0]
						# else:
						# 	temp_dict["htmColorCode"] = None
						temp_dict["candidateId"] = inter.candidate.candidate_id
						temp_dict["time"] = inter.interview_date_time.strftime("%I:%M %p")
						try:
							candidate_obj = Candidate.objects.get(candidate_id=inter.candidate.candidate_id)
							temp_dict["candidateProfilePic"] = candidate_obj.profile_photo
							temp_dict["candidateName"] = "{} {}".format(candidate_obj.name, candidate_obj.last_name) 
						except:
							temp_dict["candidateName"] = None
							temp_dict["candidateProfilePic"] = None
						if ("is_htm" in request.user.profile.roles) and request.user.profile not in [hiring_group.hod_profile, hiring_group.hr_profile]:
							if request.user.profile.id in inter.htm.all().values_list('id', flat=True):
								interview.append(temp_dict)
						else:
							interview.append(temp_dict)
					if interview:
						bg_color = "#000000"
					deadlines = []
					for d in htm_deadlines:
						if d['deadline'] == start.strftime("%Y-%m-%d"):
							if ("is_htm" in request.user.profile.roles) and request.user.profile not in [hiring_group.hod_profile, hiring_group.hr_profile]:
								if request.user.profile.id == d["htm"]:
									temp_dict = {"htmId": d["htm"], "htmProfPic": d["profile_pic"], "htmColorCode": d["color"]}
									deadlines.append(temp_dict)
							else:
								temp_dict = {"htmId": d["htm"], "htmProfPic": d["profile_pic"], "htmColorCode": d["color"]}
								deadlines.append(temp_dict)
					temp_dict = {
						"background": bg_color,
						"stage": stage,
						"additional": {},
						"deadlines": deadlines,
						"interviews_list": interview,
						"date": start.strftime("%m/%d/%Y")
					}
					dates[start.strftime("%m/%d")] = temp_dict
					start = start + timedelta(days=1)
			response["dates"] = dates
			htms_detail = []
			for j in members_list:
				try:
					profile = j
					color = []
					if hiring_group:
						color = [d["color"] for d in hiring_group.members_color if d['htm'] == profile.id]
					member_dict = {}
					member_dict['id'] = profile.id
					member_dict['job_title'] = profile.job_title
					member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
					member_dict['profile_pic'] = profile.profile_photo
					if profile==hiring_group.hod_profile:
						member_dict['isHod'] = True
						member_dict['role'] = "Hiring Manager"
					else:
						member_dict['isHod'] = False
					if profile == hiring_group.hr_profile:
						member_dict['isHr'] = True
						member_dict['role'] = "Team Cordinator"
					else:
						member_dict['isHr'] = False
					if color:
						member_dict['color'] = color[0]
					if member_dict.get('role') == None:
						member_dict['role'] = "Hiring Team Memeber"
					htms_detail.append(member_dict)
				except Exception as e:
					print(e)
					pass
			response["htm_deadlines"] = htm_deadlines
			response["htms"] = htms_detail
			if hiring_group:
				response["team_name"] = hiring_group.name
			else:
				response["team_name"] = None
			response["position_status"] = "open"
			if open_position.drafted:
				response["position_status"] = "draft"
			if open_position.trashed:
				response["position_status"] = "trashed"
			if open_position.archieved:
				response["position_status"] = "archieved"
			if open_position.filled:
				response["position_status"] = "completed"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetTempPositionSummary(APIView):
	def post(self, request):
		response = {}
		try:
			dates = {}
			kick_off = datetime.strptime(request.data.get("kickoff_start_date"), "%Y-%m-%d")
			start = datetime.strptime(request.data.get("kickoff_start_date"), "%Y-%m-%d")
			target_deadline = datetime.strptime(request.data.get("target_deadline"), "%Y-%m-%d")
			sourcing_deadline = datetime.strptime(request.data.get("sourcing_deadline"), "%Y-%m-%d")
			deadlines = request.data.get("htm_deadlines")
			if start and target_deadline:
				while start <= target_deadline:
					if start.weekday() in [5, 6]:
						color = "#b5b5b5"
					else:
						color = "#5cba83"
					if start == kick_off:
						stage = "kickoff"
					elif start == sourcing_deadline:
						stage = "sourcing"
					elif start == target_deadline:
						stage = "target"
					else:
						stage = None
					cur_date = start
					interviews_list = []
					
					htm_deadlines = []
					temp_dict = {
						"background": color,
						"stage": stage,
						"additional": {},
						"deadlines": [d["htm"] for d in deadlines if d['deadline'] == start.strftime("%m-%d-%Y")],
						"date": start.strftime("%m/%d/%Y")
					}
					dates[start.strftime("%m/%d")] = temp_dict
					start = start + timedelta(days=1)
			response["dates"] = dates
			
			htms_detail = []
			hiring_group = HiringGroup.objects.get(group_id=request.data.get("hiring_group"))
			try:
				members_list = list(hiring_group.members_list.all())
				if hiring_group.hr_profile in members_list:
					members_list.remove(hiring_group.hr_profile)
			except Exception as e:
				print(e)
				members_list = []
			for profile in members_list:
				try:
					member_dict = {}
					member_dict['id'] = profile.id
					member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
					member_dict['profile_pic'] = profile.profile_photo
					if profile == hiring_group.hod_profile:
						member_dict['isHod'] = True
					else:
						member_dict['isHod'] = False
					if profile == hiring_group.hr_profile:
						member_dict['isHr'] = True
					else:
						member_dict['isHr'] = False
					# color = random.choice(COLORS)
					# while color in selected_color:
					# 	color = random.choice(COLORS)
					# 	selected_color.append(color)
					# else:
					# 	selected_color.append(color)
					color = []
					if hiring_group:
						color = [d["color"] for d in hiring_group.members_color if d['htm'] == profile.id]
					if color:
						member_dict['color'] = color[0]
					htms_detail.append(member_dict)
				except Exception as e:
					pass
			response["htms"] = htms_detail
			try:
				htm_deadlines = []
				for deadline in deadlines:
					temp_dict = {}
					temp_dict["deadline"] = datetime.strptime(deadline.get("deadline"), "%m-%d-%Y").strftime("%Y-%m-%d")
					temp_dict["htm"] = deadline.get("htm")
					temp_dict["profile_pic"] = deadline.get("profile_photo")
					htm_deadlines.append(temp_dict)
				response["htm_deadlines"] = htm_deadlines
			except Exception as e:
				print(e)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpdateDarkModeAPI(APIView):
	"""
		This API is used to updated dark mode
		Body for POST:
			- first_name
			- last_name
			- phone_number
			- skype_id
			- job_title
			- profile_photo
	"""
	permission_classes = [IsAuthenticated]

	def post(self, request, profile_id):
		response = {}
		try:
			profile_obj = Profile.objects.get(id=profile_id)
			profile_obj.dark_mode = request.data.get("dark_mode")
			profile_obj.save()
			response['msg'] = 'update'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetArchivedOpenPosition(APIView):

	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			position_obj = OpenPosition.objects.get(id=op_id)
			openposition_serializer = OpenPositionSerializer(position_obj)
			data = openposition_serializer.data
			if position_obj.sourcing_deadline:
				data['sourcing_deadline'] = position_obj.sourcing_deadline.strftime("%m-%d-%Y")
			htm_deadlines = []
			for deadline in HTMsDeadline.objects.filter(open_position=position_obj):
				temp_dict = {}
				temp_dict["deadline"] = deadline.deadline.strftime("%m-%d-%Y")
				temp_dict["htm"] = deadline.htm.id
				htm_deadlines.append(temp_dict)
			data["htm_deadlines"] = htm_deadlines
			data['withdrawed_members'] = position_obj.withdrawed_members.all().values_list("id", flat=True)
			if position_obj.kickoff_start_date:
				data['kickoff_start_date'] = position_obj.kickoff_start_date.strftime("%m-%d-%Y")
			if position_obj.target_deadline:
				data['target_deadline'] = position_obj.target_deadline.strftime("%m-%d-%Y")
				now = datetime.today().date()
				candidates_obj = []
				for cao in CandidateAssociateData.objects.filter(open_position__id=op_id, accepted=True, withdrawed=False):
					candidates_obj.append(cao.candidate)
				members_list = position_obj.htms.all()
				for member in members_list:
					try:
						interview_taken = CandidateMarks.objects.filter(op_id=position_obj.id, marks_given_by=member.id).count()
						if interview_taken <= len(candidates_obj):
							data['deadline'] = True
					except:
						pass
				delta = position_obj.target_deadline - now
				for stage in data['stages']:
					if 'completed' in stage:
						pass
					else:
						stage['completed'] = False
				if delta.days < 0 and position_obj.target_deadline == False:
					data['deadline'] = True
				
			candidates_objs = []
			candidates_list = []
			for cao in CandidateAssociateData.objects.filter(open_position__id=op_id, accepted=True, withdrawed=False):
				candidates_objs.append(cao.candidate.candidate_id)
				candidates_list.append(cao)
			data['total_candidates'] = len(candidates_objs)
			if "is_htm" in request.user.profile.roles:
				marks_given_to = CandidateMarks.objects.filter(candidate_id__in=candidates_objs, op_id=op_id, marks_given_by=request.user.profile.id)
				data['interviews_to_complete'] = len(candidates_objs) - marks_given_to.count()
				data['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
				data['voting_history_golden'] = marks_given_to.filter(golden_gloves=True).count()
				data['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
			else:
				marks_given_to = CandidateMarks.objects.filter(candidate_id__in=candidates_objs, op_id=op_id)
				data['interviews_to_complete'] = 0
				data['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
				data['voting_history_golden'] = marks_given_to.filter(golden_gloves=True).count()
				data['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
			data['delayed'] = False
			data['no_of_hired_positions'] = Hired.objects.filter(op_id=op_id).count()
			# get_candidate data
			candidate_data = []
			for can in candidates_list:
				temp_can = {}
				temp_can["name"] = can.candidate.name
				temp_can["id"] = can.candidate.candidate_id
				temp_can["last_name"] = can.candidate.last_name
				temp_can["full_name"] = can.candidate.user.get_full_name()
				temp_can["linkedin"] = can.candidate.email
				temp_can["phone_no"] = can.candidate.phone_number
				if can.candidate.linkedin_data.get("profile_pic_url") and can.candidate.linkedin_data.get("profile_pic_url") != "null":
					temp_can["profile_photo"] = can.candidate.linkedin_data.get("profile_pic_url")
				else:
					temp_can["profile_photo"] = can.candidate.profile_photo

				if "is_htm" in request.user.profile.roles:
					marks_given_to = CandidateMarks.objects.filter(candidate_id=can.candidate.candidate_id, op_id=op_id, marks_given_by=request.user.profile.id)
					temp_can['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
					temp_can['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
					temp_can['voting_history_golden'] = marks_given_to.filter(golden_gloves=True).count()
				else:
					marks_given_to = CandidateMarks.objects.filter(candidate_id=can.candidate.candidate_id, op_id=op_id)
					temp_can['interviews_to_complete'] = 0
					temp_can['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
					temp_can['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
					temp_can['voting_history_golden'] = marks_given_to.filter(golden_gloves=True).count()
				# get if candidate is hired
				if Hired.objects.filter(candidate_id=can.candidate.candidate_id, op_id=op_id):
					temp_can['isHired'] = True
				else:
					temp_can['isHired'] = False
				# candidate associated data
				temp_can["location"] = cao.location
				temp_can["desired_location"] = cao.desired_work_location
				temp_can["salary_req"] = cao.salary_req
				temp_can["work_auth"] = cao.work_auth
				temp_can["current_position"] = cao.currently
				candidate_data.append(temp_can)
			data["candidate_data"] = candidate_data
			response = {}
			response['data'] = data

			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetFitAnalysis(APIView):

	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			position_obj = OpenPosition.objects.get(id=op_id)
			openposition_serializer = OpenPositionSerializer(position_obj)
			data = openposition_serializer.data
			data['decumentation'] = json.loads(data['decumentation'])
			candidates_objs = []
			candidates_list = []
			hired_candidates = Hired.objects.filter(op_id=op_id).values_list("candidate_id", flat=True)
			# for i in Candidate.objects.all():
			# 	if op_id in json.loads(i.associated_op_ids):
			# 		candidates_objs.append(i.candidate_id)
			# 		if i.candidate_id not in hired_candidates:
			# 			candidates_list.append(i)
			data['total_candidates'] = len(candidates_objs)
			data['no_of_hired_positions'] = Hired.objects.filter(op_id=op_id).count()
			data['no_of_hireds'] = Hired.objects.filter(op_id=op_id).count()
			data['docucments'] = data['decumentation']
			data["special_intruction"] = position_obj.special_intruction
			# get hiring group
			try:
				hiring_group_obj = HiringGroup.objects.get(group_id=position_obj.hiring_group)
				hiring_group_ser = GetHiringGroupSerializer(hiring_group_obj)
				data["hiring_group"] = hiring_group_ser.data
			except Exception as e:
				data["hiring_group"] = {}
			# get_candidate data
			candidate_data = []
			chart_data = []
			for candidate_id in hired_candidates:
				try:
					can = Candidate.objects.get(candidate_id=candidate_id)
					temp_can = {}
					# get associated data
					temp_can["associated_ddata"] = {}
					try:
						cao = CandidateAssociateData.objects.get(candidate=can, open_position=position_obj)
						temp_can["location"] = cao.location
						temp_can["work_auth"] = cao.work_auth
						temp_can["currently"] = cao.currently
						temp_can["position_work_location"] = cao.open_position.work_location
						temp_can["position_work_auth"] = cao.open_position.work_auth
						temp_can["position_location_preference"] = cao.open_position.local_preference
						# temp_can["position_remote_only"] = cao.remote_only
						# temp_can["position_remote_pref"] = cao.remote_pref
						# temp_can["position_some_in_office"] = cao.some_in_office
						# temp_can["position_office_only"] = cao.office_only
					except Exception as e:
						temp_can["location"] = can.location
						temp_can["work_auth"] = can.work_auth
						temp_can["currently"] = can.desired_work_location
						temp_can["position_work_location"] = position_obj.work_location
						temp_can["position_work_auth"] = position_obj.work_auth
						temp_can["position_location_preference"] = position_obj.local_preference
					
					temp_can["candidate_id"] = can.candidate_id
					temp_can["name"] = can.name
					temp_can["last_name"] = can.last_name
					temp_can["full_name"] = "{} {}".format(can.name, can.last_name)
					temp_can["offers"] = Offered.objects.filter(candidate_id=can.candidate_id).count()
					temp_can["interviews_last_30"] = Interview.objects.filter(candidate=can).count()
					if can.linkedin_data.get("profile_pic_url"):
						temp_can["profile_photo"] = can.linkedin_data.get("profile_pic_url")
					else:
						temp_can["profile_photo"] = can.profile_photo
						# Check Candidate Marks Code from here
					marks_dict = {}
					marks_dict['init_qualify_ques_1'] = 0
					marks_dict['init_qualify_ques_2'] = 0
					marks_dict['init_qualify_ques_3'] = 0
					marks_dict['init_qualify_ques_4'] = 0
					marks_dict['init_qualify_ques_5'] = 0
					marks_dict['init_qualify_ques_6'] = 0
					marks_dict['init_qualify_ques_7'] = 0
					marks_dict['init_qualify_ques_8'] = 0
					# Get all scheduled interviews for the candidate
					HM_vote = {}
					members_list = hiring_group_obj.members_list.all()
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=can.candidate_id, op_id=op_id)
					htm_weightage_1_total = 0
					htm_weightage_2_total = 0
					htm_weightage_3_total = 0
					htm_weightage_4_total = 0
					htm_weightage_5_total = 0
					htm_weightage_6_total = 0
					htm_weightage_7_total = 0
					htm_weightage_8_total = 0
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						try:
							htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
							htm_weightage_1_total = htm_weightage_1_total + htm_weightage_obj.init_qualify_ques_1_weightage
							htm_weightage_2_total = htm_weightage_2_total + htm_weightage_obj.init_qualify_ques_2_weightage
							htm_weightage_3_total = htm_weightage_3_total + htm_weightage_obj.init_qualify_ques_3_weightage
							htm_weightage_4_total = htm_weightage_4_total + htm_weightage_obj.init_qualify_ques_4_weightage
							htm_weightage_5_total = htm_weightage_5_total + htm_weightage_obj.init_qualify_ques_5_weightage
							htm_weightage_6_total = htm_weightage_6_total + htm_weightage_obj.init_qualify_ques_6_weightage
							htm_weightage_7_total = htm_weightage_7_total + htm_weightage_obj.init_qualify_ques_7_weightage
							htm_weightage_8_total = htm_weightage_8_total + htm_weightage_obj.init_qualify_ques_8_weightage
						except Exception as e:
							htm_weightage_1_total = htm_weightage_1_total + 10
							htm_weightage_2_total = htm_weightage_2_total + 10
							htm_weightage_3_total = htm_weightage_3_total + 10
							htm_weightage_4_total = htm_weightage_4_total + 10
							htm_weightage_5_total = htm_weightage_5_total + 10
							htm_weightage_6_total = htm_weightage_6_total + 10
							htm_weightage_7_total = htm_weightage_7_total + 10
							htm_weightage_8_total = htm_weightage_8_total + 10
					if candidate_marks_obj:
						for c_obj in candidate_marks_obj:
							given_by = c_obj.marks_given_by
							try:
								htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
								htm_weightage_1 = htm_weightage_obj.init_qualify_ques_1_weightage
								htm_weightage_2 = htm_weightage_obj.init_qualify_ques_2_weightage
								htm_weightage_3 = htm_weightage_obj.init_qualify_ques_3_weightage
								htm_weightage_4 = htm_weightage_obj.init_qualify_ques_4_weightage
								htm_weightage_5 = htm_weightage_obj.init_qualify_ques_5_weightage
								htm_weightage_6 = htm_weightage_obj.init_qualify_ques_6_weightage
								htm_weightage_7 = htm_weightage_obj.init_qualify_ques_7_weightage
								htm_weightage_8 = htm_weightage_obj.init_qualify_ques_8_weightage
							except Exception as e:
								print(e)
								htm_weightage_1 = 10
								htm_weightage_2 = 10
								htm_weightage_3 = 10
								htm_weightage_4 = 10
								htm_weightage_5 = 10
								htm_weightage_6 = 10
								htm_weightage_7 = 10
								htm_weightage_8 = 10
							marks_dict['init_qualify_ques_1'] = marks_dict['init_qualify_ques_1'] + c_obj.criteria_1_marks * htm_weightage_1
							marks_dict['init_qualify_ques_2'] = marks_dict['init_qualify_ques_2'] + c_obj.criteria_2_marks * htm_weightage_2
							marks_dict['init_qualify_ques_3'] = marks_dict['init_qualify_ques_3'] + c_obj.criteria_3_marks * htm_weightage_3
							marks_dict['init_qualify_ques_4'] = marks_dict['init_qualify_ques_4'] + c_obj.criteria_4_marks * htm_weightage_4
							marks_dict['init_qualify_ques_5'] = marks_dict['init_qualify_ques_5'] + c_obj.criteria_5_marks * htm_weightage_5
							marks_dict['init_qualify_ques_6'] = marks_dict['init_qualify_ques_6'] + c_obj.criteria_6_marks * htm_weightage_6
							marks_dict['init_qualify_ques_7'] = marks_dict['init_qualify_ques_7'] + c_obj.criteria_7_marks * htm_weightage_7
							marks_dict['init_qualify_ques_8'] = marks_dict['init_qualify_ques_8'] + c_obj.criteria_8_marks * htm_weightage_8
						marks_dict['init_qualify_ques_1'] = round(marks_dict['init_qualify_ques_1'] / htm_weightage_1_total, 1)
						marks_dict['init_qualify_ques_2'] = round(marks_dict['init_qualify_ques_2'] / htm_weightage_2_total, 1)
						marks_dict['init_qualify_ques_3'] = round(marks_dict['init_qualify_ques_3'] / htm_weightage_3_total, 1)
						marks_dict['init_qualify_ques_4'] = round(marks_dict['init_qualify_ques_4'] / htm_weightage_4_total, 1)
						marks_dict['init_qualify_ques_5'] = round(marks_dict['init_qualify_ques_5'] / htm_weightage_5_total, 1)
						marks_dict['init_qualify_ques_6'] = round(marks_dict['init_qualify_ques_6'] / htm_weightage_6_total, 1)
						marks_dict['init_qualify_ques_7'] = round(marks_dict['init_qualify_ques_7'] / htm_weightage_7_total, 1)
						marks_dict['init_qualify_ques_8'] = round(marks_dict['init_qualify_ques_8'] / htm_weightage_8_total, 1)
						temp_can['marks'] = marks_dict
						# chart data
						chart_data = []
						if position_obj.init_qualify_ques_1:
							chart_data.append({"skill": position_obj.init_qualify_ques_1, "candidate_score": marks_dict['init_qualify_ques_1'], "skill_weightage": position_obj.init_qualify_ques_weightage_1})
						if position_obj.init_qualify_ques_2:
							chart_data.append({"skill": position_obj.init_qualify_ques_2, "candidate_score": marks_dict['init_qualify_ques_2'], "skill_weightage": position_obj.init_qualify_ques_weightage_2})
						if position_obj.init_qualify_ques_3:
							chart_data.append({"skill": position_obj.init_qualify_ques_3, "candidate_score": marks_dict['init_qualify_ques_3'], "skill_weightage": position_obj.init_qualify_ques_weightage_3})
						if position_obj.init_qualify_ques_4:
							chart_data.append({"skill": position_obj.init_qualify_ques_4, "candidate_score": marks_dict['init_qualify_ques_4'], "skill_weightage": position_obj.init_qualify_ques_weightage_4})
						if position_obj.init_qualify_ques_5:
							chart_data.append({"skill": position_obj.init_qualify_ques_5, "candidate_score": marks_dict['init_qualify_ques_5'], "skill_weightage": position_obj.init_qualify_ques_weightage_5})
						if position_obj.init_qualify_ques_6:
							chart_data.append({"skill": position_obj.init_qualify_ques_6, "candidate_score": marks_dict['init_qualify_ques_6'], "skill_weightage": position_obj.init_qualify_ques_weightage_6})
						if position_obj.init_qualify_ques_7:
							chart_data.append({"skill": position_obj.init_qualify_ques_7, "candidate_score": marks_dict['init_qualify_ques_7'], "skill_weightage": position_obj.init_qualify_ques_weightage_7})
						if position_obj.init_qualify_ques_8:
							chart_data.append({"skill": position_obj.init_qualify_ques_8, "candidate_score": marks_dict['init_qualify_ques_8'], "skill_weightage": position_obj.init_qualify_ques_weightage_8})
						temp_can["chart_data"] = chart_data
						count = 0
						avg_marks = 0
						if marks_dict['init_qualify_ques_1'] not in [0, 0.0]:
							count = count + position_obj.init_qualify_ques_weightage_1
							avg_marks = avg_marks + marks_dict['init_qualify_ques_1'] * position_obj.init_qualify_ques_weightage_1
						if marks_dict['init_qualify_ques_2'] not in [0, 0.0]:
							count = count + position_obj.init_qualify_ques_weightage_2
							avg_marks = avg_marks + marks_dict['init_qualify_ques_2'] * position_obj.init_qualify_ques_weightage_2
						if marks_dict['init_qualify_ques_3'] not in [0, 0.0]:
							count = count + position_obj.init_qualify_ques_weightage_3
							avg_marks = avg_marks + marks_dict['init_qualify_ques_3'] * position_obj.init_qualify_ques_weightage_3
						if marks_dict['init_qualify_ques_4'] not in [0, 0.0]:
							count = count + position_obj.init_qualify_ques_weightage_4
							avg_marks = avg_marks + marks_dict['init_qualify_ques_4'] * position_obj.init_qualify_ques_weightage_4
						if marks_dict['init_qualify_ques_5'] not in [0, 0.0]:
							count = count + position_obj.init_qualify_ques_weightage_5
							avg_marks = avg_marks + marks_dict['init_qualify_ques_5'] * position_obj.init_qualify_ques_weightage_5
						if marks_dict['init_qualify_ques_6'] not in [0, 0.0]:
							count = count + position_obj.init_qualify_ques_weightage_6
							avg_marks = avg_marks + marks_dict['init_qualify_ques_6'] * position_obj.init_qualify_ques_weightage_6
						if marks_dict['init_qualify_ques_7'] not in [0, 0.0]:
							count = count + position_obj.init_qualify_ques_weightage_7
							avg_marks = avg_marks + marks_dict['init_qualify_ques_7'] * position_obj.init_qualify_ques_weightage_7
						if marks_dict['init_qualify_ques_8'] not in [0, 0.0]:
							count = count + position_obj.init_qualify_ques_weightage_8
							avg_marks = avg_marks + marks_dict['init_qualify_ques_8'] * position_obj.init_qualify_ques_weightage_8
						if count:
							temp_can['final_avg_marks'] = round(avg_marks / count, 1)
						else:
							temp_can['final_avg_marks'] = 0.0
					else:
						temp_can['marks'] = {}
						temp_can['final_avg_marks'] = 0
					candidate_data.append(temp_can)
				except:
					pass
			data["hired_candidates"] = candidate_data
			response = {}
			response['data'] = data

			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetAllOPData(APIView):
	
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			position_obj = OpenPosition.objects.get(id=op_id)
			openposition_serializer = OpenPositionSerializer(position_obj)
			data = openposition_serializer.data
			docs = []
			for j in PositionDoc.objects.filter(openposition__id=op_id):
				docs.append(j.file.url)
			data['documentations'] = docs
			candidates_objs = []
			candidate_ids = []
			for cao in CandidateAssociateData.objects.filter(open_position__id=op_id, accepted=True, withdrawed=False):
				candidates_objs.append(cao.candidate)
				candidate_ids.append(cao.candidate.candidate_id)
			
			if "is_htm" in request.user.profile.roles:
				marks_given_to = CandidateMarks.objects.filter(candidate_id__in=candidate_ids, op_id=op_id, marks_given_by=request.user.profile.id)
				data['interviews_to_complete'] = len(candidate_ids) - marks_given_to.count()
				data['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
				data['voting_history_golden'] = marks_given_to.filter(golden_gloves=True).count()
				data['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
			else:
				marks_given_to = CandidateMarks.objects.filter(candidate_id__in=candidate_ids, op_id=op_id)
				data['interviews_to_complete'] = 0
				data['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
				data['voting_history_golden'] = marks_given_to.filter(golden_gloves=True).count()
				data['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
			data['total_candidates'] = len(candidate_ids)
			data['no_of_hired_positions'] = Hired.objects.filter(op_id=op_id).count()
			data['no_of_hireds'] = Hired.objects.filter(op_id=op_id).count()
			data["special_intruction"] = "some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name"
			data["special_intruction"] = "some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name"
			# get hiring group
			try:
				hiring_group_obj = HiringGroup.objects.get(group_id=position_obj.hiring_group)
				hiring_group_ser = GetHiringGroupSerializer(hiring_group_obj)
				data["hiring_group"] = hiring_group_ser.data
			except Exception as e:
				print(e)
				data["hiring_group"] = {}
			# get_candidate data
			print(candidates_objs)
			candidate_data = []
			for can in candidates_objs:
				print("in can")
				try:
					temp_can = {}
					temp_can["associated_data"] = {}
					try:
						cao = CandidateAssociateData.objects.get(candidate=can, open_position=position_obj)
						temp_can["location"] = cao.location
						temp_can["work_auth"] = cao.work_auth
						temp_can["remote_only"] = cao.remote_only
						temp_can["remote_pref"] = cao.remote_pref
						temp_can["office_only"] = cao.office_only
						temp_can["some_in_office"] = cao.some_in_office
						temp_can["nickname"] = cao.nickname
						temp_can["current_position"] = cao.currently
						temp_can["salary_req"] = cao.salary_req
						temp_can["desired_work_location"] = cao.desired_work_location
						temp_can["comments"] = cao.comments
						temp_can["resume"] = can.documents
						temp_can["references"] = can.references
					except Exception as e:
						print(e)
						temp_can["location"] = can.location
						temp_can["work_auth"] = can.work_auth
						temp_can["remote_only"] = "Not Specified"
						temp_can["remote_pref"] = "Not Specified"
						temp_can["some_in_office"] = "Not Specified"
						temp_can["office_only"] = "Not Specified"
						temp_can["office_only"] = "Not Specified"
						temp_can["office_only"] = "Not Specified"
						temp_can['currency'] = can.currency
						temp_can["salary_req"] = can.salaryRange
						temp_can["desired_work_location"] = can.desired_work_location
						temp_can["comments"] = can.comments
						temp_can["resume"] = can.documents
						temp_can["references"] = can.references
					temp_can["candidate_id"] = can.candidate_id
					temp_can["name"] = can.name
					temp_can["email"] = can.email
					temp_can["linkedin"] = can.skype_id
					temp_can["last_name"] = can.last_name
					temp_can["updated_at"] = can.updated_at
					eval_objs = EvaluationComment.objects.filter(position=position_obj, candidate=can)
					eval_data = []
					for e in eval_objs:
						t_data = {}
						t_data["notes"] = e.notes
						t_data["date"] = str(e.date)
						t_data["position"] = e.position.position_title
						t_data["given_by"] = e.given_by.user.get_full_name()
						t_data["given_by_pic"] = e.given_by.profile_photo.url if e.given_by.profile_photo else None
						eval_data.append(t_data)
					temp_can["full_name"] = "{} {}".format(can.name, can.last_name)
					temp_can["eval_notes"] = eval_data
					temp_can["offers"] = Offered.objects.filter(candidate_id=can.candidate_id).count()
					temp_can["interviews_last_30"] = Interview.objects.filter(candidate=can).count()
					if can.linkedin_data.get("profile_pic_url"):
						temp_can["profile_photo"] = can.linkedin_data.get("profile_pic_url")
					else:
						temp_can["profile_photo"] = can.profile_photo
					# get hire status
					if Hired.objects.filter(candidate_id=can.candidate_id, op_id=op_id):
						temp_can['isHired'] = True
					else:
						temp_can['isHired'] = False
						# Check Candidate Marks Code from here
					# Get all scheduled interviews for the candidate
					HM_vote = {}
					members_list = position_obj.htms.all()
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=can.candidate_id, op_id=op_id)
					marks_by_htms = []
					# for calculation avg marks
					avg_marks_dict = {}
					htms_total_weightages = {}
					skill_scount = 1
					for skill in position_obj.skillsets:
						avg_marks_dict["init_qualify_ques_{}".format(skill_scount)] = 0
						htms_total_weightages["htm_weightage_{}_total".format(skill_scount)] = 0
						skill_scount += 1
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						try:
							htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
							weightage_count = 1
							for weightage in htm_weightage_obj.weightages:
								htms_total_weightages["htm_weightage_{}_total".format(weightage_count)] += htm_weightage_obj.weightages[weightage]
								# htms_total_weightages.append(htm_weightage_obj.weightages[weightage])
						except Exception as e:
							weightage_count = 1
							for weightage in htm_weightage_obj.weightages:
								htms_total_weightages["htm_weightage_{}_total".format(weightage_count)] += 10
								# htms_total_weightages.append(10)
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						marks_dict = {}
						marks_dict["given_by"] = given_by
						for k,v in c_obj.marks["marks"].items():
							marks_dict[k] = v
						marks_dict["question_answer"] = c_obj.marks["answers"]
						marks_by_htms.append(marks_dict)
						# for calculating avg marks
						htm_weightage = {}
						# htm_weightage = []
						try:
							htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
							weightage_count = 1
							for weightage in htm_weightage_obj.weightages:
								htm_weightage[weightage] = htm_weightage_obj.weightages[weightage]
								# htm_weightage.append(htm_weightage_obj.weightages[weightage])
						except Exception as e:
							weightage_count = 1
							for weightage in htm_weightage_obj.weightages:
								htm_weightage[weightage] = 10
								# htm_weightage.append(10)
						weightage_count = 0
						for k in avg_marks_dict:
							avg_marks_dict[k] = avg_marks_dict[k] + c_obj.marks[k] * htm_weightage[weightage_count]
							weightage_count += 1
					# Calculate avg marks
					# if candidate_marks_obj:
					# 	weightage_count = 0
					# 	for k in avg_marks_dict:
					# 		avg_marks_dict[k] = round(avg_marks_dict[k] / htms_total_weightages[weightage_count], 1)
					# 		weightage_count += 1
					# 	count = 0
					# 	avg_marks = 0
					# 	for k in avg_marks_dict:
					# 		skillsets_count = 1
					# 		if avg_marks_dict[k] not in [0, 0.0]:
					# 			count = count + position_obj.skillsets[]
					# 			avg_marks = avg_marks + avg_marks_dict['init_qualify_ques_1'] * position_obj.init_qualify_ques_weightage_1
					# 	if avg_marks_dict['init_qualify_ques_2'] not in [0, 0.0]:
					# 		count = count + position_obj.init_qualify_ques_weightage_2
					# 		avg_marks = avg_marks + avg_marks_dict['init_qualify_ques_2'] * position_obj.init_qualify_ques_weightage_2
					# 	if avg_marks_dict['init_qualify_ques_3'] not in [0, 0.0]:
					# 		count = count + position_obj.init_qualify_ques_weightage_3
					# 		avg_marks = avg_marks + avg_marks_dict['init_qualify_ques_3'] * position_obj.init_qualify_ques_weightage_3
					# 	if avg_marks_dict['init_qualify_ques_4'] not in [0, 0.0]:
					# 		count = count + position_obj.init_qualify_ques_weightage_4
					# 		avg_marks = avg_marks + avg_marks_dict['init_qualify_ques_4'] * position_obj.init_qualify_ques_weightage_4
					# 	if avg_marks_dict['init_qualify_ques_5'] not in [0, 0.0]:
					# 		count = count + position_obj.init_qualify_ques_weightage_5
					# 		avg_marks = avg_marks + avg_marks_dict['init_qualify_ques_5'] * position_obj.init_qualify_ques_weightage_5
					# 	if avg_marks_dict['init_qualify_ques_6'] not in [0, 0.0]:
					# 		count = count + position_obj.init_qualify_ques_weightage_6
					# 		avg_marks = avg_marks + avg_marks_dict['init_qualify_ques_6'] * position_obj.init_qualify_ques_weightage_6
					# 	if avg_marks_dict['init_qualify_ques_7'] not in [0, 0.0]:
					# 		count = count + position_obj.init_qualify_ques_weightage_7
					# 		avg_marks = avg_marks + avg_marks_dict['init_qualify_ques_7'] * position_obj.init_qualify_ques_weightage_7
					# 	if avg_marks_dict['init_qualify_ques_8'] not in [0, 0.0]:
					# 		count = count + position_obj.init_qualify_ques_weightage_8
					# 		avg_marks = avg_marks + avg_marks_dict['init_qualify_ques_8'] * position_obj.init_qualify_ques_weightage_8
					# 	if count:
					# 		temp_can['avg_marks'] = round(avg_marks / count, 1)
					# 	else:
					# 		temp_can['avg_marks'] = 0.0
					# else:
					# 	temp_can['avg_marks'] = 0.0
					temp_can['avg_marks'] = 0.0
					temp_can["marks_by_htms"] = marks_by_htms
					candidate_data.append(temp_can)
				except Exception as e:
					print(e, "candidate")
			candidate_data = sorted(candidate_data, key=lambda i: i['isHired'], reverse=True)
			candidate_data = sorted(candidate_data, key=lambda i: i['avg_marks'], reverse=True)
			data["candidates_data"] = candidate_data
			response = {}
			response['data'] = data

			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SingleClientDashboardView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, client_id):
		response = {}
		try:
			end_date = datetime.today().date()
			start_date = datetime.today().date() - timedelta(120)
			year_start_date = datetime.today().date() - timedelta(365)
			months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
			foo = [1,6,4,2,8,7,3,5]
			tcwh = None
			active_clients = 1
			monthly_active_clients = []
			try:
				client_obj = Client.objects.get(id=client_id)
				response['client-name'] = client_obj.company_name
				total_candidates = Candidate.objects.filter(created_by_client=client_obj.id).count()
				candidate_query = Candidate.objects.filter(created_by_client=client_obj.id)
			except:
				return Response({"msg": "Client not found!"}, status=status.HTTP_400_BAD_REQUEST)

			current_month = datetime.now().month
			monthly_candidates = []

			while current_month:
				count = candidate_query.filter(created_at__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = count
				monthly_candidates.append(temp_dict)
				current_month = current_month - 1

			top_clients_with_open_position = OpenPosition.objects.values('client').annotate(count=Count('client')).order_by('-count').filter(client=client_id)[0:3]
			open_positions = list(OpenPosition.objects.filter(client=client_id, drafted=False, archieved=False, trashed=False).values_list('id', flat=True))
			
			hires_queries = Hired.objects.filter(op_id__in=open_positions)
			total_hires = hires_queries.count()

			current_month = datetime.now().month
			monthly_data = []
			while current_month:
				count = hires_queries.filter(created__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = random.choice(foo)
				monthly_data.append(temp_dict)
				current_month = current_month - 1
			
			total_hires_this_quater = Hired.objects.filter(op_id__in=open_positions).filter(created__gte=start_date, created__lte=end_date).count()
			current_month = datetime.now().month
			monthly_total_hires = []
			t_count = 0
			while current_month and t_count < 4:
				count = Hired.objects.filter(op_id__in=open_positions, created__month=current_month).count()
				temp_dict = {}
				temp_dict['month'] = months[current_month-1]
				temp_dict['count'] = random.choice(foo)
				monthly_total_hires.append(temp_dict)
				current_month = current_month - 1
				t_count += 1	
			top_clients_with_open_position = OpenPosition.objects.values('client').annotate(count=Count('client')).order_by('-count')[0:3]
			
			top_cliets_with_open_position_list = []
			for client in top_clients_with_open_position:
				try:
					client_obj = Client.objects.get(id=client['client'])
					temp_dict = {}
					temp_dict['count'] = client['count']
					temp_dict['client_name'] = client_obj.company_name
					top_cliets_with_open_position_list.append(temp_dict)
				except:
					pass

			response['open-position-data'] = get_client_openposition_data(client_id)

			response['liked-candidates'] = get_client_liked_candidates_data(client_id)
			response['passed-candidates'] = get_client_passed_candidates_data(client_id)
			interview_schedule, interview_not_schedule = get_client_interview_data(client_id)
			response['interview-not-scheduled'] = interview_not_schedule
			response['interview-scheduled'] = interview_schedule

			response['offers-accepted'] = {}
			response['offers-accepted']['count'] = total_hires
			response['offers-accepted']['chart-data'] = monthly_data
			response['offers-accepted']['class'] = 'offers-accepted'

			response['total-hires-this-quater'] = {}
			response['total-hires-this-quater']['chart-data'] = monthly_total_hires
			response['total-hires-this-quater']['count'] = total_hires_this_quater
			response['total-hires-this-quater']['class'] = 'total-hires-this-quater'

			response['total-candidates'] = {}
			response['total-candidates']['count'] = total_candidates
			response['total-candidates']['chart-data'] = monthly_candidates
			response['total-candidates']['class'] = 'total-candidates'	
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class RequestPositionAssociation(APIView):
	def post(self, request, candidate_id, position):
		try:
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			request_positions = candidate_obj.requested_op_ids
			request_positions.append(position)
			candidate_obj.save()
			return Response({"msg": "Position requested for the candidate"}, status=status.HTTP_200_OK)
		except:
			return Response(
				{"error": "Token is not valid, please request a new one"},
				status=status.HTTP_400_BAD_REQUEST,
			)

	def put(self, request, candidate_id, position):
		try:
			response = {}
			openposition_obj = OpenPosition.objects.get(id=position)
			client_obj = Client.objects.get(id=openposition_obj.client)
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			request_positions = candidate_obj.requested_op_ids
			associsted_ids = json.loads(candidate_obj.associated_op_ids)
			if request.data.get('accept'):
				associsted_ids.append(position)
				# Send mail to SM
				try:
					sm_obj = Profile.objects.filter(is_sm=True, client=str(openposition_obj.client))
					for sm in sm_obj:
						subject = 'New Candidate Submitted to {}!'.format(openposition_obj.position_title)
						try:
							d = {
								"position_title": openposition_obj.position_title,
								"user_name": sm.user.get_full_name(),
								"candidate_name": candidate_obj.name,
							}
							htmly_b = get_template('candidate_added_sm.html')
							text_content = ""
							html_content = htmly_b.render(d)
							profile = Profile.objects.get(user=request.user)
							reply_to = profile.email
							sender_name = profile.user.get_full_name()
						except:
							reply_to = 'noreply@qorums.com'
							sender_name = 'No Reply'
						try:
							tasks.send.delay(subject, html_content, 'html', [htm_data['email']], reply_to, sender_name)
						except Exception as e:
							pass
				except:
					pass
				# Sending Mail to HTMs
				try:
					subject = 'New Candidate Submitted to {}!'.format(openposition_obj.position_title)
					try:
						user_obj = User.objects.get(username=client_obj.ae_assigned)
						ae_obj = Profile.objects.get(user=user_obj)
						ae_email = ae_obj.email
					except Exception as e:
						response['ae_error'] = str(e)
						ae_email = 'noreply@qorums.com'
					email_from = settings.EMAIL_HOST_USER
					htm_emails = []
					hiring_group = HiringGroup.objects.get(group_id=openposition_obj.hiring_group)
					if hiring_group.hod_profile:
						hod_profile = hiring_group.hod_profile
						htm_emails.append(hod_profile.email)
						tasks.send_app_notification.delay(hod_profile.user.username, 'A new candidate has been submitted for the {} opening.'.format(openposition_obj.position_title))
						tasks.push_notification.delay([hod_profile.user.username], 'Qorums Notification', 'A new candidate has been submitted for the {} opening.'.format(openposition_obj.position_title))
					else:
						response['notification-error'] = "No HM"
						
					htms = list(hiring_group.members_list.all().values_list("id", flat=True))
					if hiring_group.hod_profile.id in htms:
						htms.remove(hiring_group.hod_profile.id)
					htms_data = []
					for htm in htms:
						try:
							profile_obj = Profile.objects.get(id=int(htm))
							temp_htm_data = {}
							temp_htm_data['name'] = profile_obj.user.get_full_name()
							temp_htm_data['email'] = profile_obj.email
							htms_data.append(temp_htm_data)
							htm_emails.append(profile_obj.email)
							tasks.send_app_notification.delay(profile_obj.user.username, 'A new candidate has been submitted for the {} opening.'.format(openposition_obj.position_title))
							tasks.push_notification.delay([profile_obj.user.username], 'Qorums Notification', 'A new candidate has been submitted for the {} opening.'.format(openposition_obj.position_title))
						except Exception as e:
							response['notitication-error'] = str(e)						
					for htm_data in htms_data:
						try:
							try:
								manager_name = hiring_group.hod_profile.user.get_full_name()
							except:
								manager_name = "{} {}".format(client_obj.hr_first_name, client_obj.hr_last_name)
							d = {
								"position_title": openposition_obj.position_title,
								"user_name": htm_data['name'],
								"manager_name": manager_name,
							}
							htmly_b = get_template('htm_email.html')
							text_content = ""
							html_content = htmly_b.render(d)
							profile = Profile.objects.get(user=request.user)
							reply_to = profile.email
							sender_name = profile.user.get_full_name()
						except:
							reply_to = 'noreply@qorums.com'
							sender_name = 'No Reply'
						try:
							tasks.send.delay(subject, html_content, 'html', [htm_data['email']], reply_to, sender_name)
						except Exception as e:
							pass
				except Exception as e:
					response['email-error'] = str(e)
				
				try:
					request_positions.remove(position)
				except:
					pass
				candidate_obj.requested_op_ids = request_positions
				candidate_obj.associated_op_ids = json.dumps(associsted_ids)
				can_associated_obj = CandidateAssociateData.objects.filter(candidate=candidate_obj, open_position=openposition_obj)
				if can_associated_obj:
					t_obj = can_associated_obj.first()
					t_obj.accepted = True
					t_obj.save()
				response["msg"] = "Candidate Associated"
				candidate_obj.save()
				return Response(response, status=status.HTTP_200_OK)
			else:
				can_associated_obj = CandidateAssociateData.objects.filter(candidate=candidate_obj, open_position=openposition_obj)
				if can_associated_obj:
					t_obj = can_associated_obj.first()
					t_obj.accepted = False
					t_obj.save()
				response["msg"] = "Request Rejected!"
				candidate_obj.save()
				return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "Candidate not Associated!"},
				status=status.HTTP_400_BAD_REQUEST,
			)


class CreateMultiRoleUser(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			if User.objects.filter(username=request.data.get("username")):
				return Response(
					{"error": None, "msg": "User with this username already exists!"},
					status=status.HTTP_400_BAD_REQUEST,
				)
			if Profile.objects.filter(email=request.data.get("email")):
				return Response(
					{"error": None, "msg": "User with this email already exists!"},
					status=status.HTTP_400_BAD_REQUEST,
				)
			username = request.data.get("username")
			password = request.data.get("password")
			npassword = request.data.get("npassword")
			first_name = request.data.get("first_name")
			last_name = request.data.get("last_name")
			user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)
			phone_number = request.data.get("phone_number")
			skype_id = request.data.get("skype_id")
			job_title = request.data.get('job_title')
			email = request.data.get("email")
			if Profile.objects.filter(email=email).exists() or Candidate.objects.filter(email=email).exists():
				return Response({'message': 'Email already exists!'}, status=status.HTTP_400_BAD_REQUEST)
			try:
				profile_photo = request.FILES['profile_photo']
				p_fs = FileSystemStorage()
				profile_filename = p_fs.save(profile_photo.name, profile_photo)
				uploaded_profile_photo = p_fs.url(profile_filename)
			except Exception as e:
				print(e)
				uploaded_profile_photo = "None"
			# geting or creating client
			if request.data.get("client_id"):
				client_id = request.data.get("client_id")
				if "is_ca" in request.data.get("roles") and Profile.objects.filter(roles__contains=["is_ca"], client=str(client_id)):
					return Response({'message': 'A Client Admin already exists!'}, status=status.HTTP_400_BAD_REQUEST)
			else:
				client_obj = Client.objects.create(
					company_name=request.data.get('company_name'),
					company_website=request.data.get('company_website'),
					company_linkedin=request.data.get('company_linkedin'),
					ca_first_name=request.data.get('first_name'),
					ca_last_name=request.data.get('last_name'),
					key_contact_email=request.data.get('email'),
					key_username=request.data.get('username'),
				)
				create_email_templates(client_obj)
				client_id = client_obj.id
			roles = request.data.get("roles").split(',')
			if "is_ca" in roles:
				is_ca = True
			else:
				is_ca = False
			if "is_sm" in roles:
				is_sm = True
			else:
				is_sm = False
			if "is_htm" in roles:
				is_he = True
			else:
				is_he = False
			try:
				if len(roles) > 1:
					Profile.objects.create(user=user, phone_number=phone_number, skype_id=skype_id, email=email, is_ca=False, is_he=False, is_sm=False, profile_photo=uploaded_profile_photo, client=client_id, job_title=job_title, roles=roles)
				else:
					Profile.objects.create(user=user, phone_number=phone_number, skype_id=skype_id, email=email, is_ca=is_ca, is_he=is_he, is_sm=is_sm, profile_photo=uploaded_profile_photo, client=client_id, job_title=job_title, roles=roles)
			except Exception as e:
				user.delete()
				return Response({'msg': str(e)}, status=status.HTTP_409_CONFLICT)
			response = {}
			# send mail to newly added user
			try:
				client_obj = Client.objects.get(id=int(client_id))
				company_name = client_obj.company_name
			except:
				company_name = None
			subject = 'New User Created - Qorums'
			d = {
				"user_name": user.get_full_name(),
				"username": user.username,
				"password": npassword,
				"company": company_name
			}
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [email, ]
			# htmly_b = get_template('user_created.html')
			# text_content = ""
			# html_content = htmly_b.render(d)
			try:
				email_template = EmailTemplate.objects.get(client__name=company_name, name="User created")
				template = Template(email_template.content)
			except:
				email_template = EmailTemplate.objects.get(client=None, name="User created")
				template = Template(email_template.content)
			context = Context(d)
			html_content = template.render(context)	
			msg = EmailMultiAlternatives(subject, html_content, email_from, recipient_list)
			msg.attach_alternative(html_content, "text/html")
			try:
				msg.send(fail_silently=True)
			except Exception as e:
				print(e)
			response['msg'] = "user created"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not created!"},
				status=status.HTTP_400_BAD_REQUEST,
			)


	def put(self, request):
		try:
			user_obj = User.objects.get(username=request.data.get("username"))
			profile_obj = Profile.objects.get(id=request.data.get("profile_id"))
			first_name = request.data.get("first_name")
			last_name = request.data.get("last_name")
			user_obj.first_name = first_name
			user_obj.last_name = last_name
			user_obj.save()
			phone_number = request.data.get("phone_number")
			skype_id = request.data.get("skype_id")
			job_title = request.data.get('job_title')
			email = request.data.get("email")
			if profile_obj.email != email and Profile.objects.filter(email=request.data.get("email")):
				return Response(
					{"error": None, "msg": "User with this email already exists!"},
					status=status.HTTP_400_BAD_REQUEST,
				)
			try:
				profile_photo = request.FILES['profile_photo']
				p_fs = FileSystemStorage()
				profile_filename = p_fs.save(profile_photo.name, profile_photo)
				uploaded_profile_photo = p_fs.url(profile_filename)
			except Exception as e:
				uploaded_profile_photo = profile_obj.profile_photo
			roles = request.data.get("roles").split(',')
			profile_obj.profile_photo = uploaded_profile_photo
			profile_obj.phone_number = phone_number
			profile_obj.skype_id = skype_id
			profile_obj.job_title = job_title
			profile_obj.email = email
			if "is_htm" in profile_obj.roles and "is_htm" not in roles:
				if Interview.objects.filter(htm__in=[profile_obj], interview_date_time__gt=datetime.now()):
					return Response({'errMsg': "The selected user already has interviews scheduled. Kindly delete the interviews so roles can be switched."}, status=status.HTTP_200_OK)
			profile_obj.roles = roles
			if len(profile_obj.roles) > 1:
				profile_obj.is_ca = False
				profile_obj.is_he = False
				profile_obj.is_sm = False
			else:
				if "is_ca" in roles:
					is_ca = True
				else:
					is_ca = False
				if "is_sm" in roles:
					is_sm = True
				else:
					is_sm = False
				if "is_htm" in roles:
					is_he = True
				else:
					is_he = False
				profile_obj.is_ca = is_ca
				profile_obj.is_sm = is_sm
				profile_obj.is_he = is_he
			profile_obj.save()
			response = {}
			response['msg'] = "user updated"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not updated!"},
				status=status.HTTP_400_BAD_REQUEST,
			)
	
	def delete(self, request):
		try:
			response = {}
			user_obj = User.objects.get(username=request.query_params.get('username'))
			user_obj.delete()
			response['msg'] = "user deleted"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not deleted or not found!"},
				status=status.HTTP_400_BAD_REQUEST,
			)
	
	def get(self, request):
		try:
			response = {}
			profile_obj = Profile.objects.get(id=request.query_params.get('id'))
			profile_serializer = CustomProfileSerializer(profile_obj)
			response["data"] = profile_serializer.data
			response['msg'] = "user data fetched"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not found!"},
				status=status.HTTP_400_BAD_REQUEST,
			)


class GetAllUser(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			if request.user.is_superuser:
				profile_objs = Profile.objects.all().filter(user__is_superuser=False).filter(roles__contains="is_ae").exclude(roles=[]).exclude(client='[]')
			elif "is_ae" in request.user.profile.roles:
				clients = json.loads(request.user.profile.client)
				clients_list = [str(x) for x in clients] 
				profile_objs = Profile.objects.all().filter(user__is_superuser=False).filter(roles__contains="is_ae").exclude(roles=[]).exclude(client='[]').filter(client__in=clients_list)
			else:
				profile_objs = Profile.objects.all().filter(user__is_superuser=False).filter(roles__contains="is_ae").exclude(roles=[]).exclude(client='[]').exclude(roles__contains="is_ca").filter(client=request.user.profile.client)
			# profile_serializer = CustomProfileSerializer(profile_objs, many=True)
			query = request.query_params.get("search", None)
			if query:
				q = Q()
				splited_query = query.split()
				for squery in splited_query:
					q |= Q(user__first_name__icontains=squery) | Q(user__last_name__icontains=squery)
				profile_objs = profile_objs.filter(q)
			filtered_users = []
			filters = request.GET.get("type", "")
			if "is_htm" in filters:
				profile_objs = profile_objs.filter(roles__contains="is_htm")
				for i in profile_objs:
					if HiringGroup.objects.filter(hod_profile=i):
						pass
					elif i.id not in filtered_users:
						filtered_users.append(i.id)
			if "is_hm" in filters:
				profile_objs = profile_objs.filter(roles__contains="is_htm")
				for i in profile_objs:
					if HiringGroup.objects.filter(hod_profile=i):
						if i.id not in filtered_users:
							filtered_users.append(i.id)
			if "is_tc" in filters:
				profile_objs = profile_objs.filter(roles__contains="is_htm")
				for i in profile_objs:
					if HiringGroup.objects.filter(hr_profile=i):
						if i.id not in filtered_users:
							filtered_users.append(i.id)
			if "is_sm" in filters:
				profile_objs = profile_objs.filter(roles__contains="is_sm")
				for i in profile_objs:
					if i.id not in filtered_users:
						filtered_users.append(i.id)
			if "is_ca" in filters:
				profile_objs = profile_objs.filter(roles__contains="is_ca")
				for i in profile_objs:
					if i.id not in filtered_users:
						filtered_users.append(i.id)
			if request.GET.get("type"):
				profile_objs = Profile.objects.filter(id__in=filtered_users)
			data = {}
			for i in profile_objs.order_by('user__last_name'):
				temp_dict = CustomProfileSerializer(i).data
				try:
					data[temp_dict['last_name'][0].upper()].append(temp_dict)
					l = data[temp_dict['last_name'][0].upper()]
					sorted_list = sorted(l, key=lambda d: d['last_name'], reverse=False)
					data[temp_dict['last_name'][0].upper()] = sorted_list
				except Exception as e:
					data[temp_dict['last_name'][0].upper()] = [temp_dict]
			
			response["data"] = data
			response['msg'] = "user data fetched"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not found!"},
				status=status.HTTP_400_BAD_REQUEST,
			)


class ChangeUserRole(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			profile_obj = request.user.profile
			role = request.data.get("role")
			if "is_ca" == role:
				is_ca = True
			else:
				is_ca = False
			if "is_sm" == role:
				is_sm = True
			else:
				is_sm = False
			if role in ["is_htm", "is_hr", "is_hm"]:
				is_he = True
			else:
				is_he = False
			try:
				profile_obj.is_ca = is_ca
				profile_obj.is_sm = is_sm
				profile_obj.is_he = is_he
				profile_obj.save()
			except Exception as e:
				return Response({'msg': str(e)}, status=status.HTTP_409_CONFLICT)
			response = {}
			response['msg'] = "user role changed"
			response['role'] = role
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not created!"},
				status=status.HTTP_400_BAD_REQUEST,
			)


class GetHTMAudit(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			response = {}
			open_position_obj = OpenPosition.objects.get(id=op_id)
			start_date = open_position_obj.kickoff_start_date
			source_date = open_position_obj.sourcing_deadline
			end_date = None
			if open_position_obj.target_deadline > open_position_obj.filled_date.date():
				end_date = open_position_obj.target_deadline
			else:
				end_date = open_position_obj.filled_date.date()
			data = {}
			str_date = start_date.strftime("%d-%m-%Y")
			data[str_date] = {}
			data[str_date]["icons"] = [{"name": "kickoff", "color": "#808080", "msg": None, "color_name": "gray"}]
			data[str_date]["color"] = "#cccccc"
			data[str_date]["color_name"] = "silver"
			last_assciation_obj = CandidateAssociateData.objects.filter(open_position=open_position_obj).order_by('association_date').last()
			if last_assciation_obj:
				last_assciation_date = CandidateAssociateData.objects.filter(open_position=open_position_obj).order_by('association_date').last().association_date
			else:
				last_assciation_date = source_date
			for single_date in daterange(start_date + timedelta(days=1), end_date + timedelta(days=1)):
				str_date = single_date.strftime("%d-%m-%Y")
				data[str_date] = {}
				if single_date > open_position_obj.target_deadline:
					color = "#ff0000"
					color_name = "red"
				else:
					color = "#cccccc"
					color_name = "silver"
				data[str_date]["color"] = color
				data[str_date]["color_name"] = color_name
				icons = []
				htm_deadlines = HTMsDeadline.objects.filter(open_position=open_position_obj, deadline__date=single_date)
				for deadline in htm_deadlines:
					temp_dict = {}
					temp_dict["name"] = "htm"
					temp_dict["color"] = deadline.color
					temp_dict["color_name"] = COLORS_DICT.get(deadline.color, deadline.color)
					temp_dict["msg"] = "Deadline for {} to complete all Interviews".format(deadline.htm.user.get_full_name())
					icons.append(temp_dict)
				if single_date == open_position_obj.target_deadline:
					icons.append({"name": "target", "color": "#808080", "color_name": "gray", "msg": None})
				if single_date == source_date:
					icons.append({"name": "source", "color": "#808080", "color_name": "gray", "msg": None})
				if single_date == last_assciation_date:
					if last_assciation_date > source_date:
						icons.append({"name": "source", "color": "#ff0000", "color_name": "red", "msg": None})
					else:
						icons.append({"name": "source", "color": "#7CFC00", "color_name": "lawngreen", "msg": None})
				if single_date == open_position_obj.filled_date.date():
					if single_date > open_position_obj.target_deadline:
						icons.append({"name": "filled", "color": "#ff0000", "color_name": "red", "msg": None})
					else:
						icons.append({"name": "filled", "color": "#7CFC00", "color_name": "lawngreen", "msg": None})
				data[str_date]["icons"] = icons
			response['msg'] = "htm audit-data"
			response["data"] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not found!"},
				status=status.HTTP_400_BAD_REQUEST,
			)

class GetSingleHTMAudit(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id, htm):
		try:
			response = {}
			open_position_obj = OpenPosition.objects.get(id=op_id)
			start_date = open_position_obj.kickoff_start_date
			source_date = open_position_obj.sourcing_deadline
			end_date = None
			if open_position_obj.target_deadline > open_position_obj.filled_date.date():
				end_date = open_position_obj.target_deadline
			else:
				end_date = open_position_obj.filled_date.date()
			data = {}
			str_date = start_date.strftime("%d-%m-%Y")
			data[str_date] = {}
			data[str_date]["icons"] = [{"name": "kickoff", "color": "#808080", "msg": None, "color_name": "gray"}]
			data[str_date]["color"] = "#cccccc"
			data[str_date]["color_name"] = "silver"
			last_assciation_obj = CandidateAssociateData.objects.filter(open_position=open_position_obj).order_by('association_date').last()
			if last_assciation_obj:
				last_assciation_date = CandidateAssociateData.objects.filter(open_position=open_position_obj).order_by('association_date').last().association_date
			else:
				last_assciation_date = source_date
			for single_date in daterange(start_date + timedelta(days=1), end_date + timedelta(days=1)):
				str_date = single_date.strftime("%d-%m-%Y")
				data[str_date] = {}
				if single_date > open_position_obj.target_deadline:
					color = "#ff0000"
					color_name = "red"
				else:
					color = "#cccccc"
					color_name = "silver"
				data[str_date]["color"] = color
				data[str_date]["color"] = color_name
				icons = []
				htm_deadlines = HTMsDeadline.objects.filter(open_position=open_position_obj, deadline__date=single_date, htm__id=htm)
				for deadline in htm_deadlines:
					temp_dict = {}
					temp_dict["name"] = "htm"
					temp_dict["color"] = deadline.color
					temp_dict["color_name"] = COLORS_DICT.get(deadline.color, deadline.color)
					temp_dict["msg"] = "Deadline for {} to complete all Interviews".format(deadline.htm.user.get_full_name())
					icons.append(temp_dict)
				if single_date == open_position_obj.target_deadline:
					icons.append({"name": "target", "color": "#808080", "msg": None, "color_name": "gray"})
				if single_date == source_date:
					availability = [{"day": 1, "date": "2023-05-13", "hours": [{"startTime": "13:30", "endTime": "14:0"}]}, {"day": 1, "date": "2023-05-13", "hours": [{"startTime": "14:0", "endTime": "14:30"}]}]
					icons.append({"name": "availability", "color": "#808080", "msg": None, "availability": availability, "color_name": "gray"})
				if single_date == last_assciation_date:
					if last_assciation_date > source_date:
						icons.append({"name": "source", "color": "#ff0000", "color_name": "red", "msg": None})
					else:
						icons.append({"name": "source", "color": "#7CFC00", "color_name": "lawngreen", "msg": None})
				if single_date == open_position_obj.filled_date.date():
					if single_date > open_position_obj.target_deadline:
						icons.append({"name": "filled", "color": "#ff0000", "color_name": "red", "msg": None})
					else:
						icons.append({"name": "filled", "color": "#7CFC00", "color_name": "lawngreen", "msg": None})
				# 	icons.append({"name": "source", "color": "#808080", "msg": None})
				# if single_date == open_position_obj.filled_date.date():
				# 	icons.append({"name": "filled", "color": "#808080", "msg": None, "color_name": "gray"})
				# # add availability data
				# availability = [{"day": 1, "date": "2023-07-11", "hours": [{"startTime": "13:30", "endTime": "14:0"}]}, {"day": 1, "date": "2023-07-11", "hours": [{"startTime": "14:0", "endTime": "14:30"}]}]
				# icons.append({"name": "availability", "color": "#808080", "msg": None, "availability": availability, "color_name": "gray"})
				# get interviews conducted
				interviews_conducted = CandidateMarks.objects.filter(marks_given_by=htm, op_id=op_id, feedback_date=single_date)
				candidate_names = []
				for interview in interviews_conducted:
					try:
						candidate = Candidate.objects.get(candidate_id=interview.candidate_id)
						full_name = '%s %s' % (candidate.name, candidate.last_name)
						candidate_names.append(full_name.strip())
					except:
						pass
				if candidate_names:
					icons.append({"name": "interview", "color": "#808080", "msg": "Interview with {}".format(", ".join(candidate_names))})
				# get availability of the htm
				availability_list = []
				try:
					availability = HTMAvailability.objects.get(htm_id=htm)
					for i in availability:
						if single_date.strftime("%Y-%m-%d") in i.values():
							availability_list.append(i)
				except:
					pass
				if availability_list:
					icons.append({"name": "availability", "color": "#808080", "msg": None, "availability": availability_list, "color_name": "gray"})
				data[str_date]["icons"] = icons
			response['msg'] = "htm audit-data"
			response["data"] = data
			skillset_data = []
			htm_weightages = HTMWeightage.objects.filter(op_id=open_position_obj.id, htm_id=htm)
			if htm_weightages:
				htm_weightage = htm_weightages.first()
				skill_weight = {
					open_position_obj.init_qualify_ques_1: htm_weightage.init_qualify_ques_1_weightage,
					open_position_obj.init_qualify_ques_2: htm_weightage.init_qualify_ques_2_weightage,
					open_position_obj.init_qualify_ques_3: htm_weightage.init_qualify_ques_3_weightage,
					open_position_obj.init_qualify_ques_4: htm_weightage.init_qualify_ques_4_weightage,
					open_position_obj.init_qualify_ques_5: htm_weightage.init_qualify_ques_5_weightage,
					open_position_obj.init_qualify_ques_6: htm_weightage.init_qualify_ques_6_weightage,
					open_position_obj.init_qualify_ques_7: htm_weightage.init_qualify_ques_7_weightage,
					open_position_obj.init_qualify_ques_8: htm_weightage.init_qualify_ques_8_weightage,
				}
			else:
				skill_weight = {
					open_position_obj.init_qualify_ques_1: 10,
					open_position_obj.init_qualify_ques_2: 10,
					open_position_obj.init_qualify_ques_3: 10,
					open_position_obj.init_qualify_ques_4: 10,
					open_position_obj.init_qualify_ques_5: 10,
					open_position_obj.init_qualify_ques_6: 10,
					open_position_obj.init_qualify_ques_7: 10,
					open_position_obj.init_qualify_ques_8: 10,
				}
			
			if open_position_obj.init_qualify_ques_1:
				skillset_data.append(
					{
						"skillName": open_position_obj.init_qualify_ques_1,
						"importance": open_position_obj.init_qualify_ques_weightage_1,
						"weighting": skill_weight.get(open_position_obj.init_qualify_ques_1, 10)
					}
				)
			if open_position_obj.init_qualify_ques_2:
				skillset_data.append(
					{
						"skillName": open_position_obj.init_qualify_ques_2,
						"importance": open_position_obj.init_qualify_ques_weightage_2,
						"weighting": skill_weight.get(open_position_obj.init_qualify_ques_2, 10)
					}
				)
			if open_position_obj.init_qualify_ques_3:
				skillset_data.append(
					{
						"skillName": open_position_obj.init_qualify_ques_3,
						"importance": open_position_obj.init_qualify_ques_weightage_3,
						"weighting": skill_weight.get(open_position_obj.init_qualify_ques_3, 10)
					}
				)
			if open_position_obj.init_qualify_ques_4:
				skillset_data.append(
					{
						"skillName": open_position_obj.init_qualify_ques_4,
						"importance": open_position_obj.init_qualify_ques_weightage_4,
						"weighting": skill_weight.get(open_position_obj.init_qualify_ques_4, 10)
					}
				)
			if open_position_obj.init_qualify_ques_5:
				skillset_data.append(
					{
						"skillName": open_position_obj.init_qualify_ques_5,
						"importance": open_position_obj.init_qualify_ques_weightage_5,
						"weighting": skill_weight.get(open_position_obj.init_qualify_ques_5, 10)
					}
				)
			if open_position_obj.init_qualify_ques_6:
				skillset_data.append(
					{
						"skillName": open_position_obj.init_qualify_ques_6,
						"importance": open_position_obj.init_qualify_ques_weightage_6,
						"weighting": skill_weight.get(open_position_obj.init_qualify_ques_6, 10)
					}
				)
			if open_position_obj.init_qualify_ques_7:
				skillset_data.append(
					{
						"skillName": open_position_obj.init_qualify_ques_7,
						"importance": open_position_obj.init_qualify_ques_weightage_7,
						"weighting": skill_weight.get(open_position_obj.init_qualify_ques_7, 10)
					}
				)
			if open_position_obj.init_qualify_ques_8:
				skillset_data.append(
					{
						"skillName": open_position_obj.init_qualify_ques_8,
						"importance": open_position_obj.init_qualify_ques_weightage_8,
						"weighting": skill_weight.get(open_position_obj.init_qualify_ques_8, 10)
					}
				)
			candidates_submitted = 0
			# for can in Candidate.objects.all():
			# 	if open_position_obj.id in json.loads(can.associated_op_ids):
			# 		candidates_submitted += 1
			for cao in CandidateAssociateData.objects.filter(open_position=open_position_obj, accepted=True, withdrawed=False):
				candidates_submitted += 1
			overall_activity = {
				"candidates_submitted": candidates_submitted,
				"candidate_interviewed": CandidateMarks.objects.filter(marks_given_by=htm, op_id=open_position_obj.id).count()
			}
			voting = {
				"golden_glove": CandidateMarks.objects.filter(marks_given_by=htm, op_id=open_position_obj.id, golden_gloves=True).count(),
				"thumbs_up": CandidateMarks.objects.filter(marks_given_by=htm, op_id=open_position_obj.id, thumbs_up=True).count(),
				"thumbs_down": CandidateMarks.objects.filter(marks_given_by=htm, op_id=open_position_obj.id, thumbs_down=True).count(),
			}
			response["other_data"] = {
				"skillset_data": skillset_data,
				"skill_weight": skill_weight,
				"voting": voting,
				"overall_activity": overall_activity,
			}
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not found!"},
				status=status.HTTP_400_BAD_REQUEST,
			)


class GetCandidateAssociateData(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id, candidate_id):
		try:
			response = {}
			associate_obj = CandidateAssociateData.objects.filter(candidate__candidate_id=candidate_id, open_position__id=op_id).order_by('id').last()
			if associate_obj:
				data = CandidateAssociateDataSerializer(associate_obj).data
			else:
				return Response(
					{"error": str(e), "msg": "Candidate not found!"},
					status=status.HTTP_400_BAD_REQUEST,
				)
			try:
				if associate_obj.resume:
					docs = []
					for doc in associate_obj.resume:
						temp_doc = {}
						temp_doc["url"] = doc
						temp_doc["name"] = doc.split('/')[-1]
						docs.append(temp_doc)
					data['resume'] = docs
				else:
					docs = []
					for doc in json.loads(associate_obj.candidate.documents):
						temp_doc = {}
						temp_doc["url"] = doc
						temp_doc["name"] = doc.split('/')[-1]
						docs.append(temp_doc)
					data['resume'] = docs
				
			except Exception as e:
				data['resume'] = []
			try:
				docs = []
				if associate_obj.references:
					for doc in associate_obj.references:
						temp_doc = {}
						temp_doc["url"] = doc
						temp_doc["name"] = doc.split('/')[-1]
						docs.append(temp_doc)
					data['references'] = docs
				else:
					for doc in json.loads(associate_obj.candidate.references):
						temp_doc = {}
						temp_doc["url"] = doc
						temp_doc["name"] = doc.split('/')[-1]
						docs.append(temp_doc)
					data['references'] = docs
			except Exception as e:
				data['references'] = []
			response["data"] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not found!"},
				status=status.HTTP_400_BAD_REQUEST,
			)


class FetchProfileImage(APIView):
	def get(self, request, candidate_id):
		try:
			response = {}
			api_endpoint = 'https://nubela.co/proxycurl/api/v2/linkedin'
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			linkedin_profile_url = candidate_obj.skype_id
			if (candidate_obj.last_fetched and candidate_obj.last_fetched < datetime.today().date() - timedelta(days=30)) or candidate_obj.last_fetched is None:
				api_key = settings.PROXYCURL_TOKEN
				header_dic = {'Authorization': 'Bearer ' + api_key}

				res = requests.get(api_endpoint,
					params={
						"url": linkedin_profile_url,
						"personal_email": "include",
						"personal_contact_number": "include"
					},
					headers=header_dic
				)
				if res.status_code == 200:
					data = res.json()
					profile_pic_url = data['profile_pic_url']
					if profile_pic_url:
						resp = requests.get(profile_pic_url)
						fp = BytesIO()
						fp.write(resp.content)
						file_name = linkedin_profile_url.split("/")[-1]
						p_fs = FileSystemStorage()
						profile_filename = p_fs.save(file_name, fp)
						uploaded_profile_photo = p_fs.url(profile_filename)
					else:
						uploaded_profile_photo = None
					response['profile_photo'] = uploaded_profile_photo
					response['about'] = data['summary']
					response['references'] = data['recommendations']
					response['first_name'] = data['first_name']
					response['last_name'] = data['last_name']
					response['full_name'] = data['full_name']
					response['occupation'] = data['occupation']
					response['headline'] = data['headline']
					response['summary'] = data['summary']
					response['country'] = data['country_full_name']
					response['city'] = data['city']
					response['state'] = data['state']
					response['experiences'] = data['experiences']
					response['education'] = data['education']
					response['languages'] = data['languages']
					response['personal_numbers'] = data['personal_numbers']
					response['personal_emails'] = data['personal_emails']
					candidate_obj.last_fetched = datetime.today().date()
					candidate_obj.save()
				elif res.status_code == 404:
					response['msg'] = 'Profile not found'
			else:
				if candidate_obj.last_fetched:
					diff = datetime.today().date() - candidate_obj.last_fetched
					remaining_days = 30 - diff.days
					response['msg'] = 'Please wait for {} days to fetch the linkedin profile again.'.format(remaining_days)
				else:
					response['msg'] = 'something went wrong'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "User not found!"},
			)


class EmailTemplateView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			response = {}
			data = request.data
			if "is_ca" in request.user.profile.roles or "is_sm" in request.user.profile.roles:
				data["client"] = int(request.user.profile.client)
			else:
				data["client"] = None
			serializer = EmailTemplateSerializer(data=request.data)
			if serializer.is_valid():
				template_obj = serializer.save()
			else:
				return Response(
				{"error": serializer.errors, "msg": "Template not created!"},
			)
			response['msg'] = 'created'
			response['data'] = serializer.data
			return Response(response, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "Template not created!"},
			)
	
	def put(self, request):
		try:
			response = {}
			template_obj = EmailTemplate.objects.get(id=request.data.get('id'))
			serializer = EmailTemplateSerializer(template_obj, data=request.data, partial=True)
			if serializer.is_valid():
				serializer.save()
			else:
				return Response(
				{"error": serializer.errors, "msg": "Template not updated!"},
			)
			response['msg'] = 'updated'
			response['data'] = serializer.data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "Template not updated!"},
			)
	
	def get(self, request):
		try:
			response = {}
			template_obj = EmailTemplate.objects.get(id=int(request.query_params.get('id')))
			serializer = EmailTemplateSerializer(template_obj)
			response['msg'] = 'fetched'
			response['data'] = serializer.data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "Template not found!"},
			)


class AllEmailTemplateView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			print(request.user.profile.roles)
			if "is_ca" in request.user.profile.roles or "is_sm" in request.user.profile.roles:
				template_objs = EmailTemplate.objects.filter(client__id=int(request.user.profile.client))
			else:
				template_objs = EmailTemplate.objects.filter(client=None)
			serializer = EmailTemplateSerializer(template_objs, many=True)
			response['msg'] = 'fetched'
			response['data'] = serializer.data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "Template not found!"},
			)

class GetHTMAvailability(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			op_id = request.GET.get("op_id")
			open_position_obj = OpenPosition.objects.get(id=op_id)
			htms = request.GET.get('htms')
			htms_list = htms.split(',')
			month = (request.GET.get('month'))
			year = request.GET.get('year')
			combined = "{}-{}".format(year, month)
			first, last = monthrange(int(year), int(month))
			start_date = datetime(int(year), int(month), 1)
			end_date = datetime(int(year), int(month), last)
			data = {}
			for single_date in daterange(start_date, end_date + timedelta(days=1)):
				str_date = single_date.strftime("%d-%m-%Y")
				data[str_date] = {}
				availabilities = []
				schedules = []
				try:
					for htm in htms_list:
						availability_obj = HTMAvailability.objects.get(htm_id=int(htm))
						avails = [avail for avail in json.loads(availability_obj.availability) if avail["date"].startswith(single_date.strftime("%Y-%m-%d"))]
						combined_hours = []
						for avail in avails:
							try:
								for hour_dict in avail["hours"]:
									combined_hours.append(hour_dict)
							except Exception as e:
								pass
						availabilities.append({"htm": htm, "avails": {"day": 1, "hours": single_date.strftime("%Y-%m-%d"), "hours": combined_hours}})
						# Get scheduled
						scheduled = Interview.objects.filter(htm__id__in=[int(htm)], interview_date_time__year=single_date.year, interview_date_time__month=single_date.month, interview_date_time__day=single_date.day)
						for schedule in scheduled:
							temp_dict = {}
							temp_dict["id"] = schedule.id
							if request.user.profile == schedule.created_by:
								temp_dict["created_by_current"] = True
							else:
								temp_dict["created_by_current"] = False
							temp_dict['candidate'] = "{} {}".format(schedule.candidate.name, schedule.candidate.last_name)
							temp_dict['date'] = schedule.interview_date_time.strftime("%b %d, %Y %I:%M %p")
							interview_names = []
							for i in schedule.htm.all():
								interview_names.append(i.user.get_full_name())
							temp_dict['interviewer_names'] = ",".join(interview_names)
							temp_dict["accepted"] = schedule.accepted
							schedules.append(temp_dict)
				except Exception as e:
					print(e)
				data[str_date]["availabilities"] = availabilities
				data[str_date]["scheduled"] = schedules
				if single_date.date() == open_position_obj.target_deadline:
					data[str_date]["target_deadline"] = True
				else:
					data[str_date]["target_deadline"] = False
				if single_date.date() == open_position_obj.sourcing_deadline:
					data[str_date]["source_date"] = True
				else:
					data[str_date]["source_date"] = False
				if single_date.date() == open_position_obj.kickoff_start_date:
					data[str_date]["kickoff_date"] = True
				else:
					data[str_date]["kickoff_date"] = False
				curr_deadline = []
				htm_deadlines = HTMsDeadline.objects.filter(open_position=open_position_obj, deadline__date=single_date)
				for deadline in htm_deadlines:
					temp_dict = {}
					temp_dict["name"] = "htm"
					temp_dict["msg"] = "Deadline for {} to complete all Interviews".format(deadline.htm.user.get_full_name())
					curr_deadline.append(temp_dict)	
				data[str_date]["deadlines"] = curr_deadline
				interviews_done = []
				for marks in CandidateMarks.objects.filter(feedback_date=single_date, op_id=op_id):
					temp_dict = {}
					temp_dict["htm"] = marks.marks_given_by
					temp_dict["candidate_id"] = marks.marks_given_by
					profile_obj = Profile.objects.get(id=marks.marks_given_by)
					candidate_obj = Candidate.objects.get(candidate_id=marks.candidate_id)
					temp_dict["msg"] = "{} completed their interview with {}.".format(profile_obj.user.get_full_name(), candidate_obj.name)
					interviews_done.append(temp_dict)
				data[str_date]["interview_done"] = interviews_done
			response["data"] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "Something went wrong"},
			)


class TrashPositionView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request, op_id):
		try:
			if int(op_id) == int(settings.EXAMPLE_POSITION) and not request.user.is_superuser:
				response = {}
				response['msg'] = 'This position can not be trashed!'
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			trashed = request.data.get("trashed")
			open_position = OpenPosition.objects.get(id=op_id)
			open_position.trashed = trashed
			open_position.save()
			response = {}
			response['msg'] = 'position updated'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': "Position not found!"}, status=status.HTTP_400_BAD_REQUEST)


class GetCurrentHTMData(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, id):
		try:
			response = {}
			try:
				profile_obj = Profile.objects.get(id=id)
			except:
				response["msg"] = "No User Found!"
				return Response(response, status=status.HTTP_200_OK)
			data = []
			for i in HiringGroup.objects.filter(members_list__in=[profile_obj]):
				temp_data = {}
				temp_data["group_name"] = i.name
				if i.hod_profile  and id == i.hod_profile.id:
					temp_data["role"] = "Hiring Manager"
				elif i.hr_profile and id == i.hr_profile.id:
					temp_data["role"] = "Human Resource"
				else:
					temp_data["role"] = "Hiring Team Member"
				temp_data["positions"] = None
				positions = []
				for j in OpenPosition.objects.filter(hiring_group=i.group_id):
					t_p = {}
					t_p["position_name"] = j.position_title
					t_p["id"] = j.id
					positions.append(t_p)
				temp_data["positions"] = positions
				data.append(temp_data)
			response['msg'] = 'fetched'
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "profile not found!"},
			)

	def put(self, request, id):
		try:
			response = {}
			try:
				profile_obj = Profile.objects.get(id=id)
			except:
				response["msg"] = "No User Found!"
				return Response(response, status=status.HTTP_200_OK)
			data = []
			for i in HiringGroup.objects.all():
				current_members = json.loads(i.members)
				if id in current_members:
					current_members.remove(id)
					if id == i.hod_profile.id:
						i.hod = 0
					elif id == i.hr_profile.id:
						i.hr = 0
					i.save()
			for i in request.data.get('updated_data'):
				op_obj = OpenPosition.objects.filter(id=i)
				if op_obj:
					position_obj = op_obj.first()
					CandidateMarks.objects.filter(marks_given_by=id, op_id=i).delete()
					HTMWeightage.objects.filter(htm_id=id, op_id=i).delete()
					for interview in Interview.objects.filter(op_id=position_obj, htm=profile_obj):
						interview.htm.remove(id)
						interview.save()
					EvaluationComment.objects.filter(given_by=profile_obj, position=position_obj).delete()
					HTMsDeadline.objects.filter(open_position=position_obj, htm=profile_obj)
				else:
					pass
			response['msg'] = 'saved!'
			response['data'] = None
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "profile not found!"},
			)

class PackageListView(APIView):

	def get(self, request):
		try:
			response = {}
			data = []
			package_objs = Package.objects.all()
			for i in package_objs:
				temp_data = PackageSerializer(i).data
				obj, created = ExtraAccountsPrice.objects.get_or_create(package=i)
				temp_data["extra_price"] = ExtraAccountsPriceSerializer(obj).data
				data.append(temp_data)
			response['msg'] = 'fetched'
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "packages not found!"},
				status=status.HTTP_400_BAD_REQUEST
			)


class PackageView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			package_id = request.GET.get("id")
			package_obj = Package.objects.get(id=package_id)
			serializer = PackageSerializer(package_obj)
			response['msg'] = 'fetched'
			response['data'] = serializer.data
			obj, created = ExtraAccountsPrice.objects.get_or_create(package=package_obj)
			response['data']["extra_price"] = ExtraAccountsPriceSerializer(obj).data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "packages not found!"},
				status=status.HTTP_200_OK
			)
	
	def post(self, request):
		try:
			response = {}
			serializer = PackageSerializer(data=request.data)
			if serializer.is_valid():
				serializer.save()
				response['msg'] = 'created!'
				response['data'] = serializer.data
				return Response(response, status=status.HTTP_200_OK)
			else:
				return Response(
					{"error": serializer.errors, "msg": "package not created!"},
					status=status.HTTP_200_OK
				)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "packages not created!"},
				status=status.HTTP_200_OK
			)
	
	def put(self, request):
		try:
			response = {}
			package_id = request.data.get("id")
			package_obj = Package.objects.get(id=package_id)
			serializer = PackageSerializer(package_obj, data=request.data, partial=True)
			if serializer.is_valid():
				serializer.save()
				response['msg'] = 'updated!'
				response['data'] = serializer.data
				extra_price = request.data.get("extra_price")
				if extra_price:
					obj, created = ExtraAccountsPrice.objects.get_or_create(package=package_obj)
					extp_serializer = ExtraAccountsPriceSerializer(obj, data=extra_price, partial=True)
					if extp_serializer.is_valid():
						extp_serializer.save()
					else:
						response["extra_price_error"] = str(extp_serializer.errors)
				return Response(response, status=status.HTTP_200_OK)
			else:
				return Response(
					{"error": serializer.errors, "msg": "package not updated!"},
					status=status.HTTP_400_BAD_REQUEST
				)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "packages not updated!"},
				status=status.HTTP_400_BAD_REQUEST
			)


class GenerateOTPView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request, client_id):
		try:
			ca_obj = Profile.objects.filter(client=client_id, roles__contains="is_ca").order_by('id').first()
			if ca_obj:
				subject = 'OTP For Package Change'
				otp = ''
				for i in range(0,6):
					otp += str(random.randint(0,9))
				client_obj = Client.objects.get(id=client_id)
				OTPRequested.objects.filter(client=client_obj).delete()
				OTPRequested.objects.create(otp=otp, client=client_obj)
				d = {
					"user_name": ca_obj.user.get_full_name(),
					"otp": otp,
				}
				email_from = settings.EMAIL_HOST_USER
				recipient_list = [ca_obj.email, ]
				htmly_b = get_template('otp.html')
				text_content = ""
				html_content = htmly_b.render(d)
				msg = EmailMultiAlternatives(subject, text_content, email_from, recipient_list)
				msg.attach_alternative(html_content, "text/html")
				try:
					msg.send(fail_silently=True)
				except Exception as e:
					print(e)
					return Response({"error": str(e), "msg": "otp not sent!"}, status=status.HTTP_200_OK)
				return Response({"msg": "otp sent!"}, status=status.HTTP_200_OK)
			else:
				return Response(
					{"error": str(e), "msg": "opt not generated"},
					status=status.HTTP_400_BAD_REQUEST
				)	
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "opt not generated"},
				status=status.HTTP_400_BAD_REQUEST
			)


class ClientPackageView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, client_id):
		try:
			response = {}
			try:
				package_obj = ClientPackage.objects.get(client__id=client_id)
			except:
				response["msg"] = "No package"
				return Response(response, status=status.HTTP_200_OK)
			if package_obj.package:
				data = {
					"client": package_obj.client.id,
					"senior_managers": package_obj.package.senior_managers + package_obj.senior_managers,
					"hiring_managers": package_obj.package.hiring_managers + package_obj.hiring_managers,
					"hiring_team_members": package_obj.package.hiring_team_members + package_obj.hiring_team_members,
					"contributors": package_obj.package.contributors + package_obj.contributors,
					"overall_price": package_obj.overall_price,
					"base_price": package_obj.package.price
				}
			else:
				data = {
					"client": package_obj.client.id,
					"senior_managers": 0,
					"hiring_managers": 0,
					"hiring_team_members": 0,
					"contributors": 0,
					"overall_price": 0,
					"base_price": 0
				}
			if package_obj.is_trial:
				data["package_id"] = 0
				data["package"] = "Trial"
				data["trial_expired"] = package_obj.trial_expired.strformat()
			else:
				data["package_id"] = package_obj.package.id
				data["package"] = package_obj.package.name
			response['msg'] = 'fetched'
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "packages not found!"},
			)
	
	def post(self, request, client_id):
		try:
			response = {}
			package_id = request.data.get("package_id")
			package_obj = Package.objects.get(id=package_id)
			client_obj = Client.objects.get(id=client_id)
			print(package_obj, client_obj,'---------------------')
			try:
				client_packages = ClientPackage.objects.filter(client=client_obj)
				print(client_packages, '************************')
				if client_packages:
					client_package = client_packages.order_by('-id').first()
					client_package.package = package_obj
					client_package.save()
				else:
					package_obj = ClientPackage.objects.create(
						client=client_obj,
						package=package_obj,
						km_accounts=package_obj.key_masters_accounts,
						senior_managers=0,
						hiring_managers=0,
						hiring_team_members=0,
						contributors=0,
						open_positions=package_obj.open_positions,
						overall_price=package_obj.price + 0,
						strip_subs_status="inactive",
						old_status=None,
					)
			except Exception as e:
				response['error'] = str(e)
				response["msg"] = "No package"
				return Response(response, status=status.HTTP_200_OK)
			response['msg'] = 'created'
			response['data'] = None
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "packages not found!"},
			)

	def put(self, request, client_id):
		try:
			response = {}
			# verify otp and then continue to change anything
			opt = OTPRequested.objects.filter(otp=str(request.data.get("otp")), client__id=client_id).last()
			if opt:
				pass
			else:
				response["msg"] = "OTP not matched"
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			package_id = int(request.data.get("package_id"))
			client_obj = Client.objects.get(id=client_id)
			client_package_obj, created = ClientPackage.objects.get_or_create(client=client_obj)
			additional_price = 0
			if package_id:
				package_obj = Package.objects.get(id=package_id)
			elif package_id == 0:
				additional_price = 0
				client_package_obj.is_trial = True
				client_package_obj.trial_expired = request.data.get("trial_expired")
				client_package_obj.save()
				response["msg"] = "updated"
				return Response(response, status=status.HTTP_200_OK)
			ext_acc_price_obj, create = ExtraAccountsPrice.objects.get_or_create(package=package_obj)
			
			# price breakdown used in invoice
			price_breakdown = {}
			# try:
			prev_ext_acc_price_obj, created = ExtraAccountsPrice.objects.get_or_create(package=package_obj)
			# calculating additional amount
			if client_package_obj.package is None:
				price_breakdown["package"] = {
					"price": package_obj.price,
					"name": "Monthly {} Level Acouunt".format(package_obj.name)
				}
				additional_price = package_obj.price
				sm_count = int(request.data.get("ext_senior_managers", 0))
				additional_price += sm_count * ext_acc_price_obj.sm_price
				if sm_count:
					price_breakdown["senior_managers"] = []
					price_breakdown["senior_managers"].append("Monthly additional Senior Manager")
					price_breakdown["senior_managers"].append(sm_count * ext_acc_price_obj.sm_price)
					price_breakdown["senior_managers"].append("{} Accounts @ {} per month".format(sm_count, ext_acc_price_obj.sm_price))
				hm_count = int(request.data.get("ext_hiring_managers", 0))
				additional_price += hm_count * ext_acc_price_obj.hm_price
				if hm_count:
					price_breakdown["hiring_managers"] = []
					price_breakdown["hiring_managers"].append("Monthly additional Hiring Manager")
					price_breakdown["hiring_managers"].append(hm_count * ext_acc_price_obj.hm_price)
					price_breakdown["hiring_managers"].append("{} Accounts @ {} per month".format(hm_count, ext_acc_price_obj.hm_price))
				htm_count = int(request.data.get("ext_hiring_team_members", 0))
				additional_price += htm_count * ext_acc_price_obj.htm_price
				if htm_count:
					price_breakdown["hiring_team_member"] = []
					price_breakdown["hiring_team_member"].append("Monthly additional Hiring Team Member")
					price_breakdown["hiring_team_member"].append(htm_count * ext_acc_price_obj.htm_price)
					price_breakdown["hiring_team_member"].append("{} Accounts @ {} per month".format(htm_count, ext_acc_price_obj.htm_price))
				# additional_price += int(request.data.get("ext_hiring_team_members", 0))/ext_acc_price_obj.htm_count * ext_acc_price_obj.sm_price
			elif client_package_obj.package == package_obj:
				sm_count = int(request.data.get("ext_senior_managers", 0))
				additional_price += sm_count * ext_acc_price_obj.sm_price
				if sm_count:
					price_breakdown["senior_managers"] = []
					price_breakdown["senior_managers"].append("Monthly additional Senior Manager")
					price_breakdown["senior_managers"].append(sm_count * ext_acc_price_obj.sm_price)
					price_breakdown["senior_managers"].append("{} Accounts @ {} per month".format(sm_count, ext_acc_price_obj.sm_price))
				hm_count = int(request.data.get("ext_hiring_managers", 0))
				additional_price += hm_count * ext_acc_price_obj.hm_price
				if hm_count:
					price_breakdown["hiring_managers"] = []
					price_breakdown["hiring_managers"].append("Monthly additional Hiring Manager")
					price_breakdown["hiring_managers"].append(hm_count * ext_acc_price_obj.hm_price)
					price_breakdown["hiring_managers"].append("{} Accounts @ {} per month".format(hm_count, ext_acc_price_obj.hm_price))
				htm_count = int(request.data.get("ext_hiring_team_members", 0))
				additional_price += htm_count * ext_acc_price_obj.htm_price
				if htm_count:
					price_breakdown["hiring_team_member"] = []
					price_breakdown["hiring_team_member"].append("Monthly additional Hiring Team Member")
					price_breakdown["hiring_team_member"].append(htm_count * ext_acc_price_obj.htm_price)
					price_breakdown["hiring_team_member"].append("{} Accounts @ {} per month".format(htm_count, ext_acc_price_obj.htm_price))
				# additional_price += int(request.data.get("ext_hiring_team_members", 0))/ext_acc_price_obj.htm_count * ext_acc_price_obj.sm_price
			else:
				additional_price = package_obj.price - client_package_obj.package.price
				price_breakdown["package"] = {
					"price": package_obj.price - client_package_obj.package.price,
					"name": "Upgraded from {} to {} Level Acouunt".format(client_package_obj.package.name, package_obj.name)
				}
				sm_count = int(request.data.get("ext_senior_managers", 0))
				additional_price += sm_count * ext_acc_price_obj.sm_price
				if sm_count:
					price_breakdown["senior_managers"] = []
					price_breakdown["senior_managers"].append("Monthly additional Senior Manager")
					price_breakdown["senior_managers"].append(sm_count * ext_acc_price_obj.sm_price)
					price_breakdown["senior_managers"].append("{} Accounts @ {} per month".format(sm_count, ext_acc_price_obj.sm_price))
				hm_count = int(request.data.get("ext_hiring_managers", 0))
				additional_price += hm_count * ext_acc_price_obj.hm_price
				if hm_count:
					price_breakdown["hiring_managers"] = []
					price_breakdown["hiring_managers"].append("Monthly additional Hiring Manager")
					price_breakdown["hiring_managers"].append(hm_count * ext_acc_price_obj.hm_price)
					price_breakdown["hiring_managers"].append("{} Accounts @ {} per month".format(hm_count, ext_acc_price_obj.hm_price))
				htm_count = int(request.data.get("ext_hiring_team_members", 0))
				additional_price += htm_count * ext_acc_price_obj.htm_price
				if htm_count:
					price_breakdown["hiring_team_member"] = []
					price_breakdown["hiring_team_member"].append("Monthly additional Hiring Team Member")
					price_breakdown["hiring_team_member"].append(htm_count * ext_acc_price_obj.htm_price)
					price_breakdown["hiring_team_member"].append("{} Accounts @ {} per month".format(htm_count, ext_acc_price_obj.htm_price))
			future_charge = 0
			future_charge += package_obj.price
			future_charge += ext_acc_price_obj.sm_price * (client_package_obj.senior_managers + int(request.data.get("ext_senior_managers", 0)) )
			future_charge += ext_acc_price_obj.hm_price * (client_package_obj.hiring_managers + int(request.data.get("ext_hiring_managers", 0)) )
			future_charge += ext_acc_price_obj.htm_price * (client_package_obj.hiring_team_members + int(request.data.get("ext_hiring_team_members", 0)))
			
			if additional_price:
				response["additional_amt"] = additional_price
			response["future_charge"] = future_charge
			# calcuate the initial charge depending on the no of days left
			remaining_days = 31 - datetime.today().day
			one_day_price = additional_price / 30
			charge_amount = remaining_days * one_day_price
			price_breakdown["total"] = {
				"amount": round(charge_amount, 2),
				"days": remaining_days
			}
			customer = get_or_create_stripe_customer(request.user)
			# creating a payment intent
			if charge_amount > 0:
				intent = stripe.PaymentIntent.create(
					amount=int(charge_amount * 100),
					currency='usd',
					automatic_payment_methods={
						'enabled': True,
					},
					customer=customer,
					description="Payment for change in account levels",
					receipt_email=request.user.profile.email,
					setup_future_usage="off_session"
				)
				payment_intent_id = intent["id"]
				payment_secret = intent["client_secret"]
				#  saving current data for later use when payment is success
				StripePayments.objects.create(
					customer=customer,
					client=client_obj, 
					payment_id=payment_intent_id, 
					payment_secret=payment_secret,
					data=request.data, 
					type="one-time", 
					amount=charge_amount,
					price_breakdown=price_breakdown,
					status="incomplete"
				)
				# Update later when payment is success
				# client_package_obj.package = package_obj
				# client_package_obj.km_accounts = package_obj.key_masters_accounts
				# client_package_obj.senior_managers = int(request.data.get("ext_senior_managers", 0))
				# client_package_obj.hiring_managers = int(request.data.get("ext_hiring_managers", 0))
				# client_package_obj.hiring_team_members = int(request.data.get("ext_hiring_team_members", client_package_obj.hiring_team_members))
				# client_package_obj.contributors = int(request.data.get("ext_contributors", 0))
				# client_package_obj.open_positions = package_obj.open_positions
				# client_package_obj.overall_price = package_obj.price + int(request.data.get("ext_price", 0))
				# client_package_obj.save()
				response["msg"] = "payment_required"
				response["payment_intent_id"] = payment_intent_id
				response["payment_secret"] = payment_secret
				response["key"] = settings.STRIPE_KEY
				return Response(response, status=status.HTTP_200_OK)
			else:
				# Update later when payment is success
				client_package_obj.package = package_obj
				client_package_obj.km_accounts = package_obj.key_masters_accounts
				client_package_obj.senior_managers = int(request.data.get("ext_senior_managers", 0))
				client_package_obj.hiring_managers = int(request.data.get("ext_hiring_managers", 0))
				client_package_obj.hiring_team_members = int(request.data.get("ext_hiring_team_members", client_package_obj.hiring_team_members))
				client_package_obj.contributors = int(request.data.get("ext_contributors", 0))
				client_package_obj.open_positions = package_obj.open_positions
				next_price = 0
				next_price = next_price + client_package_obj.senior_managers * ext_acc_price_obj.sm_price
				next_price = next_price + client_package_obj.hiring_managers * ext_acc_price_obj.hm_price
				next_price = next_price + client_package_obj.hiring_team_members * ext_acc_price_obj.htm_price
				client_package_obj.overall_price = package_obj.price + next_price
				client_package_obj.save()
				response["msg"] = "updated"
				return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['error'] = str(e)
			response["msg"] = "No package"
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
		# except Exception as e:
		# 	return Response({"error": str(e), "msg": "packages not found!"}, status=status.HTTP_400_BAD_REQUEST)


class InitialPaymentView(APIView):
	permission_classes = (permissions.IsAuthenticated,)
 
	def post(self, request, client_id):
		try:
			response = {}
			
			client_obj = Client.objects.get(id=client_id)
			# price breakdown used in invoice
			price_breakdown = {}
			try:
				client_package_obj = ClientPackage.objects.get(client=client_obj)
			except Exception as e:
				return Response({'msg': "package not selected", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
			# calculating additional amount
			additional_price = 0
			price_breakdown["package"] = {
				"price": client_package_obj.package.price,
				"name": "Monthly {} Level Acouunt".format(client_package_obj.package.name)
			}
			additional_price = client_package_obj.package.price
			remaining_days = 31 - datetime.today().day
			one_day_price = additional_price / 30
			charge_amount = remaining_days * one_day_price
			price_breakdown["total"] = {
				"amount": round(charge_amount, 2),
				"days": remaining_days
			}
			
			customer = get_or_create_stripe_customer(request.user)
			# creating a payment intent
			if charge_amount > 0:
				intent = stripe.PaymentIntent.create(
					amount=int(charge_amount * 100),
					currency='usd',
					automatic_payment_methods={
						'enabled': True,
					},
					customer=customer,
					description="Payment for change in account levels",
					receipt_email=request.user.profile.email,
					setup_future_usage="off_session"
				)
				payment_intent_id = intent["id"]
				payment_secret = intent["client_secret"]
				#  saving current data for later use when payment is success
				StripePayments.objects.create(
					customer=customer,
					client=client_obj, 
					payment_id=payment_intent_id, 
					payment_secret=payment_secret,
					data={"package_id": client_package_obj.package.id}, 
					type="one-time", 
					amount=charge_amount,
					price_breakdown=price_breakdown,
					status="incomplete"
				)
				response["msg"] = "payment_required"
				response["payment_intent_id"] = payment_intent_id
				response["payment_secret"] = payment_secret
				response["key"] = settings.STRIPE_KEY
				return Response(response, status=status.HTTP_200_OK)
			else:
				response["msg"] = "please select a package"
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			response['error'] = str(e)
			response["msg"] = "No package"
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class ExtraAccountsPriceView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, package_id):
		try:
			response = {}
			package = Package.objects.get(id=package_id)
			obj, created = ExtraAccountsPrice.objects.get_or_create(package=package)
			serializer = ExtraAccountsPriceSerializer(obj)
			response['msg'] = 'fetched'
			response['data'] = serializer.data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
	
	def post(self, request, package_id):
		try:
			response = {}
			obj = ExtraAccountsPrice.objects.get_or_create(package__id=package_id)
			serializer = ExtraAccountsPriceSerializer(data=request.data)
			if serializer.is_valid():
				serializer.save()
				response['msg'] = 'created'
			else:
				response['msg'] = str(serializer.errors)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(response, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request, package_id):
		try:
			response = {}
			obj = ExtraAccountsPrice.objects.get_or_create(package__id=package_id)
			serializer = ExtraAccountsPriceSerializer(obj, data=request.data, partial=True)
			if serializer.is_valid():
				serializer.save()
				response['msg'] = 'updated'
			else:
				response['msg'] = str(serializer.errors)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
		

class UserBillingView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			client = request.GET.get("client")
			if client:
				client_obj = Client.objects.get(id=int(client))
				profile_obj = Profile.objects.get(user__username=client_obj.key_username)
				obj, created = BillingDetail.objects.get_or_create(profile=profile_obj)
			else:
				obj, created = BillingDetail.objects.get_or_create(profile=request.user.profile)
			response['data'] = BillingDetailSerializer(obj).data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'Card Details not added!'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
	
	def post(self, request):
		try:
			response = {}
			client = request.GET.get("client")
			if client:
				client_obj = Client.objects.get(id=int(client))
				profile_obj = Profile.objects.get(user__username=client_obj.key_username)
				obj, created = BillingDetail.objects.get_or_create(profile=profile_obj)
			else:
				obj, created = BillingDetail.objects.get_or_create(profile=request.user.profile)
			data = request.data
			serializer = BillingDetailSerializer(obj, data=request.data, partial=True)
			if serializer.is_valid():
				biiling_obj = serializer.save()
				biiling_obj.billing_contact = request.data.get("billing_contact", request.user.get_full_name())
				biiling_obj.save()
				response['data'] = serializer.data
				response['msg'] = 'updated'
				return Response(response, status=status.HTTP_200_OK)
			else:
				response['msg'] = 'error'
				response['error'] = str(serializer.errors)
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
		

class ListClients(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			user = request.user
			if "is_ae" in user.profile.roles:
				clients_objs = Client.objects.filter(id__in=json.loads(user.profile.client)).order_by('-updated_at')
			elif user.is_superuser:
				clients_objs = Client.objects.filter(disabled=False).order_by('-updated_at')
			else:
				response['msg'] = 'error'
				response['error'] = 'You are not Authorized!'
				return Response(response, status=status.HTTP_400_BAD_REQUEST) 
			data = []
			for client in clients_objs:
				temp_data = {}
				temp_data["id"] = client.id
				temp_data["name"] = client.company_name
				data.append(temp_data)
			response['data'] = data
			response['msg'] = 'fetched'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
		

class GetStripeKey(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			user = request.user
			if "is_ae" in user.profile.roles or "is_ca" in user.profile or user.is_superuser:
				response['key'] = settings.STRIPE_SECRET_KEY
				response['msg'] = 'fetched'
				return Response(response, status=status.HTTP_200_OK)
			else:
				response['msg'] = 'error'
				response['error'] = 'You are not Authorized!'
				return Response(response, status=status.HTTP_400_BAD_REQUEST) 
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class CreateSubscriptionView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			response = {}
			client_obj = Client.objects.get(id=request.data.get("client"))
			package = Package.objects.get(id=request.data.get("package"))
			customer = get_or_create_stripe_customer(request.user)
			price = create_price(name="{} for {}".format(client_obj.company_name, package.name), amount=package.price*100)
			subscription_id, lastest_invoice = create_subscription(request.user, price, "default_incomplete")
			invoice = stripe.Invoice.retrieve(lastest_invoice)
			payment_intent = stripe.PaymentIntent.retrieve(invoice.payment_intent)
			client_secret = payment_intent.client_secret
			data = {}
			data["subscription_id"] = subscription_id
			data["client_secret"] = client_secret
			response["data"] = data
			response['msg'] = "fetched"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class ChangeSubscriptionView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		try:
			response = {}
			opt = OTPRequested.objects.filter(otp=str(request.data.get("otp")), client__id=client_id).last()
			if opt:
				pass
			else:
				response["msg"] = "OTP not matched"
				return Response(response, status=status.HTTP_400_BAD_REQUEST)
			client_obj = Client.objects.get(id=request.data.get("client"))
			# calculate the money
			package_id = request.data.get("package_id")
			package_obj = Package.objects.get(id=package_id)
			ext_acc_price_obj = ExtraAccountsPrice.objects.get_or_create(package=package_obj)
			
			try:
				client_package_obj = ClientPackage.objects.get(client=client_obj)
				prev_ext_acc_price_obj = ExtraAccountsPrice.objects.get_or_create(package=package_obj)
				# calculating additional amount
				additional_amt = 0
				if client_package_obj.package.price < package_obj.price:
					additional_amt = additional_amt + package_obj.price - client_package_obj.package.price
				# adding additional amount for sm
				additional_amt = additional_amt + (client_package_obj.senior_managers * prev_ext_acc_price_obj.sm_price) - (package_obj.senior_managers * ext_acc_price_obj.sm_price)
				additional_amt = additional_amt + (client_package_obj.hiring_managers * prev_ext_acc_price_obj.hm_price) - (package_obj.hiring_managers * ext_acc_price_obj.hm_price)
				additional_amt = additional_amt + (client_package_obj.hiring_team_members / prev_ext_acc_price_obj.htm_count * prev_ext_acc_price_obj.htm_price) - (package_obj.hiring_managers / ext_acc_price_obj.htm_count * ext_acc_price_obj.htm_price)
			except:
				pass
			price = create_price(name="{} for {}".format(client_obj.company_name, package.name), amount=package.price*100)
			subscription_id, lastest_invoice = create_subscription(request.user, price, "default_incomplete")
			invoice = stripe.Invoice.retrieve(lastest_invoice)
			payment_intent = stripe.PaymentIntent.retrieve(invoice.payment_intent)
			client_secret = payment_intent.client_secret
			data = {}
			data["subscription_id"] = subscription_id
			data["client_secret"] = client_secret
			response["data"] = data
			response['msg'] = "fetched"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class CalculateAdditionalAmount(APIView):
	def post(self, request):
		try:
			response = {}
			client_obj = Client.objects.get(id=request.data.get("client"))
			# calculate the money
			package_id = request.data.get("package_id")
			package_obj = Package.objects.get(id=package_id)
			ext_acc_price_obj, created = ExtraAccountsPrice.objects.get_or_create(package=package_obj)
			try:
				client_package_obj = ClientPackage.objects.get(client=client_obj)
				# calculating additional amount
				print(ext_acc_price_obj.sm_price, ext_acc_price_obj.hm_price, ext_acc_price_obj.htm_price)
				additional_price = 0
				if client_package_obj.package == None:
					additional_price = package_obj.price
					additional_price += int(request.data.get("ext_senior_managers", 0)) * ext_acc_price_obj.sm_price
					additional_price += int(request.data.get("ext_hiring_managers", 0)) * ext_acc_price_obj.hm_price
					# additional_price += int(request.data.get("ext_hiring_team_members", 0))/ext_acc_price_obj.htm_count * ext_acc_price_obj.htm_price
					additional_price += int(request.data.get("ext_hiring_team_members", 0)) * ext_acc_price_obj.htm_price
				elif client_package_obj.package == package_obj:
					additional_price += int(request.data.get("ext_senior_managers", 0)) * ext_acc_price_obj.sm_price
					additional_price += int(request.data.get("ext_hiring_managers", 0)) * ext_acc_price_obj.hm_price
					# additional_price += int(request.data.get("ext_hiring_team_members", 0))/ext_acc_price_obj.htm_count * ext_acc_price_obj.htm_price
					additional_price += int(request.data.get("ext_hiring_team_members", 0)) * ext_acc_price_obj.htm_price
				else:
					additional_price = package_obj.price - client_package_obj.package.price
					additional_price += int(request.data.get("ext_senior_managers", 0)) * ext_acc_price_obj.sm_price
					additional_price += int(request.data.get("ext_hiring_managers", 0)) * ext_acc_price_obj.hm_price
					# additional_price += int(request.data.get("ext_hiring_team_members", 0))/ext_acc_price_obj.htm_count * ext_acc_price_obj.htm_price
					additional_price += int(request.data.get("ext_hiring_team_members", 0)) * ext_acc_price_obj.htm_price
				future_charge = 0
				future_charge += package_obj.price
				future_charge += ext_acc_price_obj.sm_price * (client_package_obj.senior_managers + int(request.data.get("ext_senior_managers", 0)) )
				future_charge += ext_acc_price_obj.hm_price * (client_package_obj.hiring_managers + int(request.data.get("ext_hiring_managers", 0)) )
				# future_charge += ext_acc_price_obj.htm_price * (client_package_obj.hiring_team_members + int(request.data.get("ext_hiring_team_members", 0)))/ext_acc_price_obj.htm_count
				future_charge += ext_acc_price_obj.htm_price * (client_package_obj.hiring_team_members + int(request.data.get("ext_hiring_team_members", 0)))
				if additional_price:
					response["additional_amt"] = additional_price
				response["future_charge"] = future_charge
				"""
				Old Calculation
				package_additional_amt = 0
				if client_package_obj.package.price < package_obj.price:
					package_additional_amt = package_obj.price - client_package_obj.package.price
				# adding additional amount for sm
				old_additional_amt = 0
				old_additional_amt = old_additional_amt + (client_package_obj.senior_managers * prev_ext_acc_price_obj.sm_price)
				old_additional_amt = old_additional_amt + (client_package_obj.hiring_managers * prev_ext_acc_price_obj.hm_price)
				old_additional_amt = old_additional_amt + (client_package_obj.hiring_team_members / prev_ext_acc_price_obj.htm_count * prev_ext_acc_price_obj.htm_price)
				new_additiona_amt = 0
				new_additiona_amt = new_additiona_amt + int(request.data.get("ext_senior_managers", 0)) * ext_acc_price_obj.sm_price
				new_additiona_amt = new_additiona_amt + int(request.data.get("ext_hiring_managers", 0)) * ext_acc_price_obj.hm_price
				new_additiona_amt = new_additiona_amt + int(request.data.get("ext_hiring_team_members", 0)) / ext_acc_price_obj.htm_count * ext_acc_price_obj.htm_price
				additional_amt = new_additiona_amt - old_additional_amt
				if additional_amt:
					response["additional_amt"] = package_additional_amt + additional_amt
				else:
					response["additional_amt"] = package_additional_amt
				"""
				response['msg'] = "fetched"
				return Response(response, status=status.HTTP_200_OK)
			except Exception as e:
				response['error'] = str(e)
				response["additional_amt"] = 0
				response['msg'] = "fetched"
				return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['error'] = str(e)
			response['msg'] = "error"
			return Response(response, status=status.HTTP_200_OK)
			

class ConfirmPayment(APIView):
	def post(self, request):
		try:
			response = {}
			payment_intent = request.data.get("payment_intent")
			pi = stripe.PaymentIntent.retrieve(payment_intent)
			if pi.status == "succeeded":
				obj = StripePayments.objects.get(payment_id=payment_intent)
				obj.status = "succeeded"
				obj.save()
				package_id = obj.data.get("package_id")
				package_obj = Package.objects.get(id=package_id)
				client_package_obj = ClientPackage.objects.get(client=obj.client)
				client_package_obj.package = package_obj
				client_package_obj.km_accounts = package_obj.key_masters_accounts
				client_package_obj.senior_managers = int(obj.data.get("ext_senior_managers", 0))
				client_package_obj.hiring_managers = int(obj.data.get("ext_hiring_managers", 0))
				client_package_obj.hiring_team_members = int(obj.data.get("ext_hiring_team_members", client_package_obj.hiring_team_members))
				client_package_obj.contributors = int(obj.data.get("ext_contributors", 0))
				client_package_obj.open_positions = package_obj.open_positions
				ext_price_obj, created = ExtraAccountsPrice.objects.get_or_create(package=package_obj)
				next_price = 0
				next_price = next_price + client_package_obj.senior_managers * ext_price_obj.sm_price
				next_price = next_price + client_package_obj.hiring_managers * ext_price_obj.hm_price
				next_price = next_price + client_package_obj.hiring_team_members * ext_price_obj.htm_price
				client_package_obj.overall_price = package_obj.price + next_price
				client_package_obj.save()
				# create price
				price_id = create_price("{} for {}".format(package_obj.name, client_package_obj.client.company_name), client_package_obj.overall_price)
				# get payment method
				payment_method_id = get_payment_method(obj.customer)
				if not payment_method_id:
					# and send a mail too
					response["msg"] = "No payment method found please contact."
					return Response(response, status=status.HTTP_200_OK)
				# cancel previous subscriptions of the customer - uncomment later
				# if client_package_obj.strip_subs_id:
				# 	try:
				# 		s = stripe.Subscription.delete(client_package_obj.strip_subs_id, cancellation_details={"comment": "changed subscription package"})
				# 	except:
				# 		pass
				# create subscription
				subscription_obj = create_subscription(obj.customer, price_id, payment_method_id)
				client_package_obj.strip_subs_id = subscription_obj.id
				client_package_obj.strip_subs_status = "active"
				client_package_obj.save()
				response["msg"] = "updated"
				response["status"] = "updated"
				return Response(response, status=status.HTTP_200_OK)
			elif pi.status == "processing":
				response["status"] = "processing"
				response["msg"] = "Your payment is processing please contact support"
				return Response(response, status=status.HTTP_200_OK)
			elif pi.status == "payment_failed":
				response["status"] = "payment failed"
				response["msg"] = "Your payment failed please contact support"
			else:
				response["status"] = "something went wrong"
				response["msg"] = "something went wrong please contact support"
			return Response(response, status=status.HTTP_200_OK)			
		except Exception as e:
			response['error'] = str(e)
			response['msg'] = "error"
			return Response(response, status=status.HTTP_200_OK)


class InvoiceListView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			client_id = request.GET.get("client")
			invoices = StripePayments.objects.filter(client__id=client_id)
			if invoices:
				invoice_data = []
				for i in invoices:
					temp_data = {}
					temp_data["id_int"] = i.id
					temp_data["id"] = "invoice#" + str(i.id)
					temp_data["date"] = i.created.strftime("%b %d, %Y")
					temp_data["status"] = i.status
					if i.type=="subs":
						temp_data["period"] = "Some Period"
					else:
						temp_data["period"] = None
					temp_data["id"] = "invoice#" + str(i.id)
					temp_data["amount"] = round(i.amount, 2)
					temp_data["payment_intent"] = i.payment_id
					temp_data["payment_secret"] = i.payment_secret
					temp_data["key"] = settings.STRIPE_KEY
					temp_data["client"] = i.client.company_name
					temp_data["amt_breakdown"] = i.price_breakdown
					invoice_data.append(temp_data)
				response["data"] = invoice_data
				response['msg'] = "fetched"
				return Response(response, status=status.HTTP_200_OK)
			else:
				response['msg'] = 'No Invoiced Found!'
				return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['msg'] = 'error'
			response['error'] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class StripeWebhookView(APIView):
	def post(self, request):
		try:
			response = {}
			event = None
			payload = request.body
			StripeWebhookData.objects.create(data=request.data)
			sig_header = request.headers['STRIPE_SIGNATURE']
			endpoint_secret = 'whsec_8c6569e85d67ad5ae6f0c92df3f6b31edb00f97e92d2e18244a9ef926348846f'
			try:
				event = stripe.Webhook.construct_event(
					payload, sig_header, endpoint_secret
				)
			except ValueError as e:
				# Invalid payload
				raise e
			except stripe.error.SignatureVerificationError as e:
				# Invalid signature
				raise e
			# Handle the event
			if event['type'] == 'subscription_schedule.aborted':
				subscription_schedule = event['data']['object']
			elif event['type'] == 'subscription_schedule.canceled':
				subscription_schedule = event['data']['object']
			elif event['type'] == 'subscription_schedule.updated':
				subscription_schedule = event['data']['object']
			elif event["type"] == "customer.subscription.paused":
				subscription_schedule = event['data']['object']
				subs_id = subscription_schedule["id"]
				client_objs = ClientPackage.objects.filter(strip_subs_id=subs_id)
				if client_objs:
					client_obj = client_objs.first()
					old_status = client_obj.strip_subs_status
					client_obj.strip_subs_status = subscription_schedule["status"]
					client_obj.old_status = old_status
					client_obj.save()
			elif event["type"] == "customer.subscription.updated":
				subscription_schedule = event['data']['object']
				subs_id = subscription_schedule["id"]
				client_objs = ClientPackage.objects.filter(strip_subs_id=subs_id)
				if client_objs:
					client_obj = client_objs.first()
					old_status = client_obj.strip_subs_status
					client_obj.strip_subs_status = subscription_schedule["status"]
					client_obj.old_status = old_status
					period_start = datetime.fromtimestamp(subscription_schedule["current_period_start"])
					period_end = datetime.fromtimestamp(subscription_schedule["current_period_end"])
					customer = subscription_schedule["customer"]
					client_obj.save()
					try:
						customer_profile = Profile.objects.get(customer=customer)
					except:
						response['error'] = "".format(subs_id)
						response['msg'] = "error"
						return Response(response, status=status.HTTP_200_OK)
					payment_id = None
					payment_secret = None
					try:
						subs = stripe.Subscription.retrieve(subs_id)
						invoice = stripe.Invoice.retrieve(subs.latest_invoice)
						payment_intent = stripe.PaymentIntent.retrieve(invoice.payment_intent)
						payment_id = payment_intent.id
						payment_secret = payment_intent.client_secret
					except:
						pass
					data = {}
					# create price breakdown
					price_breakdown = {}
					price_breakdown["package"] = {
						"price": client_obj.package.price,
						"name": "Monthly {} Level Acouunt".format(client_obj.package.name)
					}
					ext_acc_price_obj, create = ExtraAccountsPrice.objects.get_or_create(package=client_obj.package)
					sm_count = client_obj.senior_managers
					if sm_count:
						price_breakdown["senior_managers"] = []
						price_breakdown["senior_managers"].append("Monthly additional Senior Manager")
						price_breakdown["senior_managers"].append(sm_count * ext_acc_price_obj.sm_price)
						price_breakdown["senior_managers"].append("{} Accounts @ {} per month".format(sm_count, ext_acc_price_obj.sm_price))
					hm_count = int(request.data.get("ext_hiring_managers", 0))
					additional_price += hm_count * ext_acc_price_obj.hm_price
					if hm_count:
						price_breakdown["hiring_managers"] = []
						price_breakdown["hiring_managers"].append("Monthly additional Hiring Manager")
						price_breakdown["hiring_managers"].append(hm_count * ext_acc_price_obj.hm_price)
						price_breakdown["hiring_managers"].append("{} Accounts @ {} per month".format(hm_count, ext_acc_price_obj.hm_price))
					htm_count = int(request.data.get("ext_hiring_team_members", 0))
					additional_price += htm_count * ext_acc_price_obj.htm_price
					if htm_count:
						price_breakdown["hiring_team_member"] = []
						price_breakdown["hiring_team_member"].append("Monthly additional Hiring Team Member")
						price_breakdown["hiring_team_member"].append(htm_count * ext_acc_price_obj.htm_price)
						price_breakdown["hiring_team_member"].append("{} Accounts @ {} per month".format(htm_count, ext_acc_price_obj.htm_price))
					
					StripePayments.objects.create(
						customer=customer,
						client=client_obj.client,
						payment_id=payment_id,
						payment_secret=payment_secret,
						type="subscription",
						cycle="{} - {}".format(period_start.strftime("%b %-d"), period_end.strftime("%b %-d, %Y")),
						amount=subscription_schedule["plan"]["amount"] / 100,
						status=subscription_schedule["status"],
						data=data,
						price_breakdown=price_breakdown,
					)
					response['msg'] = "Client Package Updated"
					return Response(response, status=status.HTTP_200_OK) 
				else:
					response['error'] = "Client Package or Subscription with id {} not found!".format(subs_id)
					response['msg'] = "error"
					return Response(response, status=status.HTTP_200_OK)
			# ... handle other event types
			else:
				print('Unhandled event type {}'.format(event['type']))
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['error'] = str(e)
			response['msg'] = "error"
			return Response(response, status=status.HTTP_200_OK)
		

class GenerateInvoice(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, invoice):
		response = {}
		try:
			invoice = StripePayments.objects.get(id=invoice)
			file_path = "invoice.pdf"
			generate_pdf(invoice)
			if os.path.exists(file_path):
				with open(file_path, "rb") as fh:
					response = HttpResponse(fh.read(), content_type="application/pdf")
					response["Content-Disposition"] = "inline; filename=" + os.path.basename(file_path)
					return response
			else:
				response['error'] = "File Not Found!"
				response['msg'] = "error"
				return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response['error'] = str(e)
			response['msg'] = "error"
			return Response(response, status=status.HTTP_200_OK)


class ResendCandidateCreds(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, candidate_id):
		response = {}
		try:
			candidate_obj = Candidate.objects.get(candidate_id=candidate_id)
			# Send mail to candidate
			d = {
				"user_name": candidate_obj.name,
				"username": candidate_obj.username,
				"password": candidate_obj.key,
			}
			subject = "Your details to login - Qorums"
			htmly_b = get_template('candidate_resend_creds.html')
			text_content = ""
			html_content = htmly_b.render(d)
			reply_to = 'noreply@qorums.com'
			sender_name = 'No Reply'
			try:
				tasks.send.delay(subject, html_content, 'html', [candidate_obj.email], reply_to, sender_name)
				return Response({"message": 'success'}, status=status.HTTP_200_OK)
			except Exception as e:
				return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
		
		except Exception as e:
			response['error'] = str(e)
			response['msg'] = "error"
			return Response(response, status=status.HTTP_200_OK)


class GetMultipleQuestionsView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		response = {}
		try:
			try:
				skill = request.data.get("skill")
				# bedrock = boto3.client(
				# 	service_name="bedrock-runtime",
				# 	region_name="us-east-1",
				# 	aws_access_key_id=settings.AWS_ACCESS_KEY,
				# 	aws_secret_access_key=settings.AWS_SECRET_KEY,
				# )
				# body = {
				# 	"prompt":"give me 5 questions for css",
				# 	"maxTokens":96,
				# 	"temperature":0.7,
				# 	"topP":1,
				# 	"stopSequences":[],
				# 	"countPenalty":{"scale":0},
				# 	"presencePenalty":{"scale":0},
				# 	"frequencyPenalty":{"scale":0}
				# }
				# data = {
				# 	"modelId": "ai21.j2-mid-v1",
				# 	"contentType": "application/json",
				# 	"accept": "*/*",
				# 	"body": json.dumps(body)
				# }

				# response = bedrock.invoke_model(
				# 	body=data["body"],
				# 	modelId=data["modelId"],
				# 	accept=data["accept"],
				# 	contentType=data["contentType"]
				# )
				# response_body = json.loads(response['body'].read())
				# questions = response_body.get("completions", [{"data": []}])[0].get("data", {}).get("text")
				while True:
					response_body = get_five_question(skill)
					questions = response_body.get("results", [{"outputText": []}])[0].get("outputText", [])
					if len(questions) > 5:
						break
					else:
						continue
				questions = re.sub('[0-9]. ', '', questions)
				questions = questions.split("\n")[-1:-6:-1]
			except Exception as e:
				print(e)
				questions =  [
					"Question 1 Generated",
					"Question 2 Generated",
					"Question 3 Generated",
					"Question 4 Generated",
					"Question 5 Generated",
				]
			return Response({"message": "success", "questions": questions}, status=status.HTTP_200_OK)
		
		except Exception as e:
			response['error'] = str(e)
			response['msg'] = "error"
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetSingleQuestionView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		response = {}
		try:
			skill = request.data.get("skill")
			while True:
				response_body = get_single_question(skill)
				questions = response_body.get("results", [{"outputText": []}])[0].get("outputText", [])
				if questions.endswith("?"):
					break
				else:
					continue
			questions = re.sub('[0-9]. ', '', questions)
			questions = questions.split("\n")[-1:-6:-1]
			question =  questions[0]
			return Response({"message": "success", "question": question}, status=status.HTTP_200_OK)
		
		except Exception as e:
			response['error'] = str(e)
			response['msg'] = "error"
			return Response(response, status=status.HTTP_400_BAD_REQUEST)


class GetAllPositionByClient(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, client_id):
		response = {}
		try:
			user = request.user
			if user.profile.is_candidate:
				try:
					response = {}
					candidates_obj = Candidate.objects.get(user=user.id)
					# openposition_objs = OpenPosition.objects.filter(id__in=json.loads(candidates_obj.associated_op_ids))
					# requested_objs = OpenPosition.objects.filter(id__in=candidates_obj.requested_op_ids)
					openposition_objs = OpenPosition.objects.filter(id__in=CandidateAssociateData.objects.filter(candidate=candidates_obj, accepted=True).values_list('open_position__id', flat=True))
					requested_objs = OpenPosition.objects.filter(id__in=CandidateAssociateData.objects.filter(candidate=candidates_obj, accepted=None).values_list('open_position__id', flat=True))

					# openposition_data = OpenPositionSerializer(openposition_objs, many=True).data
					# clients_list = []
					# for obj in openposition_objs:
					# 	if obj.client not in clients_list:
					# 		clients_list.append(obj.client)
					clients_objs = Client.objects.filter(id__in=json.loads(candidates_obj.associated_client_ids)).order_by('-updated_at')
					clients_serializer = ClientSerializer(clients_objs, many=True)
					clients_serializer_data = clients_serializer.data
					for i in clients_serializer_data:
						openposition_data = OpenPositionSerializer(openposition_objs.filter(client=i["id"]), many=True).data
						i["open_position_data"] = openposition_data
						requested_positions = OpenPositionSerializer(requested_objs.filter(client=i["id"]), many=True).data
						i["requested_positions"] = requested_positions
					response["data"] = clients_serializer_data
					return Response(response, status=status.HTTP_200_OK)
				except Exception as e:
					return Response({'msg': "candidate not found", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
			
			clients_obj = Client.objects.get(id=client_id)
			clients_serializer = ClientSerializer(clients_obj)
			total_open_positions = 0
			i = clients_serializer.data
			del clients_serializer
			if HiringGroup.objects.filter(client_id=i["id"]):
				i["team_exists"] = True
			else:
				i["team_exists"] = False
			ordered_ops = []
			if "is_htm" in user.profile.roles:
				hg_list = []
				for hg in HiringGroup.objects.all():
					if user.profile in hg.members_list.all() or hg.hr_profile == user.profile:
						hg_list.append(hg.group_id)
					total_positions_obj = OpenPosition.objects.filter(client=i["id"], hiring_group__in=hg_list).order_by('target_deadline').order_by('id')
			else:
				total_positions_obj = OpenPosition.objects.filter(Q(client=i["id"]) | Q(id=int(settings.EXAMPLE_POSITION))).order_by('target_deadline').order_by('id')
			positions_data = []
			for j in total_positions_obj:
				temp_data = {}
				temp_data["id"] = j.id
				temp_data["position_title"] = j.position_title
				temp_data["target_deadline"] = j.target_deadline
				temp_data["no_of_open_positions"] = j.no_of_open_positions
				temp_data["position_filled"] = Hired.objects.filter(op_id=j.id).count()
				try:
					hiring_group_obj = HiringGroup.objects.get(group_id=j.hiring_group)
					if hiring_group_obj.hod_profile:
						temp_data["hiring_manager"] = hiring_group_obj.hod_profile.user.get_full_name()
					else:
						temp_data["hiring_manager"] = "No Manager"
					temp_data["hiring_team"] = hiring_group_obj.name
					members_list = list(hiring_group_obj.members_list.all().values_list("id", flat=True))
				except Exception as e:
					temp_data["hiring_team"] = "No Team"
					temp_data["hiring_manager"] = "No Team"
					members_list = []
				temp_data["deadline"] = None
				now = datetime.today().date()
				for member in members_list:
					try:
						interview_taken = CandidateMarks.objects.filter(op_id=j.id, marks_given_by=member).count()
						htm_deadline = HTMsDeadline.objects.get(open_position=j, htm__id=member)
						if interview_taken < len(candidates_obj) and htm_deadline.deadline > now:
							temp_data['deadline'] = True
							break
					except:
						pass
				if j.sourcing_deadline and CandidateAssociateData.objects.filter(open_position=j, accepted=True, withdrawed=False).count() == 0 and j.sourcing_deadline < now:
					temp_data['deadline'] = True
				try:
					delta = j.target_deadline - now
					if delta.days < 0:
						temp_data['deadline'] = True
				except:
					pass
				if j.drafted:
					temp_data["status"] = "Drafted"
				elif j.archieved:
					temp_data["status"] = "On Hold"
				elif j.trashed:
					temp_data["status"] = "Trashed"
				elif j.disabled:
					temp_data["status"] = "Disabled"
				elif j.filled:
					temp_data["status"] = "Completed"
				else:
					temp_data["status"] = "Active"
				positions_data.append(temp_data)
			response = {}
			# response["data"] = i
			response["all_open_positions"] = positions_data
			return Response(response, status=status.HTTP_200_OK)	
		except Exception as e:
			response['error'] = str(e)
			response['msg'] = "error"
			return Response(response, status=status.HTTP_200_OK)


class GetAllClientsList(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		response = {}
		try:
			user = request.user
			if "is_ae" in user.profile.roles:
				clients_objs = Client.objects.filter(id__in=json.loads(user.profile.client)).order_by('-updated_at')
			elif user.is_superuser:
				clients_objs = Client.objects.filter(disabled=False).order_by('-updated_at')
			data = CustomClientSerializer(clients_objs)
			response["msg"] = "success"
			response["data"] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response["msg"] = "error"
			response["error"] = str(e)
			return Response(response, status=status.HTTP_400_BAD_REQUEST)
