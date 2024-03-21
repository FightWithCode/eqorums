# python imports
import requests
import json
from datetime import datetime, timedelta
from calendar import monthrange


# django imports
from django.conf import settings

# drf imports
from rest_framework import status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

# model imports
from schedules.models import CronofyAuthCode
from openposition.models import (
	OpenPosition,
	HTMsDeadline, 
	CandidateMarks, 
	Interview
)
from candidates.models import Candidate
from dashboard.models import Profile

# utils import
from schedules.coronfy_utils import GetAccessToken
from schedules.utils import daterange


class GetAuthCode(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, code):
		try:
			url = "https://api.cronofy.com/oauth/token"
			payload = json.dumps({
				"client_id": settings.CRONOFY_CLIENT_ID,
				"client_secret": settings.CRONOFY_CLIENT_SECRET,
				"grant_type": "authorization_code",
				"code": code,
				"redirect_uri": request.GET.get("redirect_uri")
			})
			headers = {
				'Content-Type': 'application/json'
			}
			response = requests.request("POST", url, headers=headers, data=payload)
			if response.status_code == 200:
				resp_data = response.json()
				obj, created = CronofyAuthCode.objects.get_or_create(user=request.user)
				if created:
					obj.access_token = resp_data.get("access_token")
					obj.refresh_token=resp_data.get("refresh_token")
					obj.sub = resp_data.get("sub")
					obj.account_id = resp_data.get("account_id")
				else:
					obj.access_token = resp_data.get("access_token")
					obj.refresh_token=resp_data.get("refresh_token")
					obj.sub = resp_data.get("sub")
					obj.account_id = resp_data.get("account_id")
				obj.save()
				return Response({"data": "token generated"}, status=status.HTTP_200_OK)
			else:
				return Response({"data": response.json()}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
		

class ListCalendars(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			url = "https://api.cronofy.com/v1/calendars"
			access_token = GetAccessToken(request.user)
			payload = {}
			headers = {
				'Authorization': 'Bearer {}'.format(access_token)
			}
			response = requests.request("GET", url, headers=headers, data=payload)
			if response.status_code == 200:
				return Response({"data": response.json(), "msg": "Calendars Fetched"}, status=status.HTTP_200_OK)
			else:
				return Response({"data": response.json()}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
	

class GetElementToken(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			url = "https://api.cronofy.com/v1/element_tokens"
			obj, created = CronofyAuthCode.objects.get_or_create(user=request.user)
			if created:
				response["msg"] = "User not authenticated with Cronofy. Please authenticate!"
				return Response(response, status=status.HTTP_401_UNAUTHORIZED)

			payload = json.dumps({
				"version": "1",
				"permissions": [
					"account_management",
					"availability",
					"managed_availability"
				],
				"subs": [
					obj.sub
				],
				"origin": request.GET.get("origin")
			})

			headers = {
				'Authorization': 'Bearer {}'.format(settings.CRONOFY_CLIENT_SECRET),
				'Content-Type': 'application/json'
			}

			api_resp = requests.request("POST", url, headers=headers, data=payload)
			if api_resp.status_code in [200, 201]:
				response["msg"] = "success"
				response["data"] = api_resp.json()
				return Response(response, status=status.HTTP_200_OK)
			else:
				response["msg"] = "error"
				response["data"] = api_resp.json()
				return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CheckAccessToken(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			obj, created = CronofyAuthCode.objects.get_or_create(user=request.user)
			if created:
				response["msg"] = "invalid token"
				return Response(response, status=status.HTTP_200_OK)
			else:
				current_time = datetime.now()
				three_hours_ago = current_time - timedelta(minutes=175)
				if obj.access_token and obj.updated_at > three_hours_ago:
					response["msg"] = "valid token"
					response["data"] = None
					return Response(response, status=status.HTTP_200_OK)
				else:
					# get refresh token and auth token
					url = "https://api.cronofy.com/oauth/token"
					payload = json.dumps({
						"client_id": settings.CRONOFY_CLIENT_ID,
						"client_secret": settings.CRONOFY_CLIENT_SECRET,
						"grant_type": "refresh_token",
						"refresh_token": obj.refresh_token
					})
					headers = {
						'Content-Type': 'application/json'
					}
					cronofy_resp = requests.request("POST", url, headers=headers, data=payload)
					if cronofy_resp.status_code == 200:
						resp_data = cronofy_resp.json()
						obj.access_token = resp_data.get("access_token")
						obj.save()
						response["msg"] = "valid token"
						response["data"] = None
						return Response(response, status=status.HTTP_200_OK)
					else:
						response["msg"] = "invalid token"
						response["data"] = cronofy_resp.json()
						return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetUserCalendar(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			htm = request.user.profile.id
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
				schedules = []
				try:
					# Get scheduled
					scheduled = Interview.objects.filter(htm__id__in=[int(htm)], interview_date_time__year=single_date.year, interview_date_time__month=single_date.month, interview_date_time__day=single_date.day)
					for schedule in scheduled:
						temp_dict = {}
						# add dummy data remove later
						if str_date.startswith("11"):
							temp_dict["id"] = 2
							temp_dict['candidate'] = "Json Roy"
							temp_dict['date'] = "Mar 11, 2024 10:30 PM"
							interview_names = []
							for i in schedule.htm.all():
								interview_names.append(i.user.get_full_name())
							temp_dict['interviewer_names'] = "Json Sanga"
							temp_dict["accepted"] = True
							continue
						if str_date.startswith("15"):
							temp_dict["id"] = 2
							temp_dict['candidate'] = "Jason Jordan"
							temp_dict['date'] = "Mar 15, 2024 10:30 PM"
							interview_names = []
							for i in schedule.htm.all():
								interview_names.append(i.user.get_full_name())
							temp_dict['interviewer_names'] = "Jason Smith"
							temp_dict["accepted"] = False
							continue
						temp_dict["id"] = schedule.id
						temp_dict['candidate'] = "{} {}".format(schedule.candidate.name, schedule.candidate.last_name)
						temp_dict['date'] = schedule.interview_date_time.strftime("%b %d, %Y %I:%M %p")
						interview_names = []
						for i in schedule.htm.all():
							interview_names.append(i.user.get_full_name())
						temp_dict['interviewer_names'] = ",".join(interview_names)
						temp_dict["accepted"] = schedule.accepted
						schedules.append(temp_dict)
				except Exception as e:
					data["error"] = str(e)
				data[str_date]["scheduled"] = schedules
				curr_deadline = []
				htm_deadlines = HTMsDeadline.objects.filter(deadline__date=single_date, htm__id=htm)
				for deadline in htm_deadlines:
					temp_dict = {}
					# add dummy data
					if str_date.startswith("11"):
						temp_dict["name"] = "htm"
						temp_dict["msg"] = "Deadline to complete all Interviews for position Analysit"
						continue
					if str_date.startswith("17"):
						temp_dict["name"] = "htm"
						temp_dict["msg"] = "Deadline to complete all Interviews for position My Position"
						continue
					temp_dict["name"] = "htm"
					temp_dict["msg"] = "Deadline to complete all Interviews for position {}".format(deadline.open_position.position_title)
					curr_deadline.append(temp_dict)	
				data[str_date]["deadlines"] = curr_deadline
			response["data"] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response(
				{"error": str(e), "msg": "Something went wrong"},
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
