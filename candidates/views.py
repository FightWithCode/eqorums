# python imports
import json
import string
from datetime import datetime
from datetime import timedelta
# django import
from django.db.models import Q, F
# drf imports 
from rest_framework import status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
# models imports
from candidates.models import Candidate
from openposition.models import (
	CandidateAssociateData,
	CandidateMarks,
	Hired,
	Offered,
	OpenPosition
)
# serializer imports
from candidates.serializers import CandidateSerializer
# utils import
from candidates.utils import (
	get_candidate_profile, 
	get_current_submission_status
)


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
			email = request.data.get("email")
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
					queryset = queryset.filter(job_title__icontains=job_title)
				if email:
					queryset = queryset.filter(email__icontains=email)
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
			response['data'] = candidate_data
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
				temp_dict['profile_photo'] = get_candidate_profile(i)
				temp_dict['current_position'] = i.job_title
				temp_dict['location'] = i.location
				temp_dict['skillsets'] = i.skillsets
				temp_dict['linkedin_data'] = i.linkedin_data
				temp_dict['currency'] = i.currency
				temp_dict['salaryRange'] = i.salaryRange
				temp_dict['desired_work_location'] = i.desired_work_location
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


class CandidateListForSubmission(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			op_obj = OpenPosition.objects.get(id=op_id)
			response = {}
			data = []
			if "is_ca" in request.user.profile.roles or "is_sm" in request.user.profile.roles:
				queryset = Candidate.objects.filter(Q(created_by_client=request.user.profile.client)|Q(created_by_client=0))
			else:
				queryset = Candidate.objects.all()
			for i in queryset:
				
				temp_dict = {}
				temp_dict['candidate_id'] = i.candidate_id
				temp_dict['first_name'] = i.name
				temp_dict["last_name"] = i.last_name
				temp_dict["email"] = i.email
				temp_dict["full_name"] = i.user.get_full_name()
				temp_dict['skillsets'] = i.skillsets
				temp_dict['profile_photo'] = get_candidate_profile(i)
				temp_dict["status"] = get_current_submission_status(i, op_obj)
				data.append(temp_dict)
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			response = {}
			response['error'] = str(e)
			return Response(response, status=status.HTTP_200_OK)
