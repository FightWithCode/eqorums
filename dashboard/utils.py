from openposition.models import (
	OpenPosition,
	Interview,
	CandidateAssociateData
)
from candidates.models import Candidate
from .models import (
	CandidateMarks,
	EmailTemplate
)
from clients.models import Client
from hiringgroup.models import HiringGroup
from .serializers import OpenPositionSerializer, CandidateSerializer
import json
from django.db.models.functions import TruncMonth
from django.db.models import Count, Q
from datetime import datetime
from datetime import date, timedelta
import pytz

# Accepts datetime
def get_timediff(dt):
	try:
		current = datetime.now(pytz.timezone('EST'))
		datetime2 = datetime.combine(current.date(), current.time())
		time_diff = dt - datetime2
		if time_diff.days < 0:
			start_in = "Delayed by:"
		else:
			start_in = "Starts in:"
		hours_difference, remainder = divmod(time_diff.seconds, 3600)
		minutes_difference, _ = time_diff(remainder, 60)
		return "{} {}H {}M".format(start_in, hours_difference, minutes_difference)
	except:
		return ""


def get_htm_flag_data(htm_profile, op_id, candidate_id):
	hm_marks_obj = CandidateMarks.objects.filter(candidate_id=candidate_id, op_id=op_id, marks_given_by=int(htm_profile.id))
	temp_dict = {}
	temp_dict['id'] = htm_profile.id
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
			interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[htm_profile], candidate__candidate_id=candidate_id)[0]
			extra_data = get_htm_specific_data(interview_obj, htm_profile)
			temp_dict.update(extra_data)
		except:
			pass
	return temp_dict


def get_htm_specific_data(interview_obj, logged_user_profile):
	temp_dict = {}
	try:
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
		temp_dict['interviewer'] = logged_user_profile.user.get_full_name()
		temp_dict['date'] = interview_obj.interview_date_time.strftime("%B %d, %Y")
		temp_dict['time'] = interview_obj.interview_date_time.strftime("%I:%M %p")
		return temp_dict
	except:
		return temp_dict

def get_openposition_data(user):
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	open_position_data = {}
	if user.is_superuser:
		open_positions = OpenPosition.objects.filter(archieved=False, drafted=False, filled=False, trashed=False)
		openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		open_position_data['open-position'] = openposition_serializer.data
		open_position_data['count'] = open_positions.count()
		
		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			count = open_positions.filter(created_at__month=current_month, created_at__year=current_year).count()
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1

		# open_positions = OpenPosition.objects.filter(archieved=False)
		# openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		# open_position_data['archived-position'] = openposition_serializer.data

		# open_positions = OpenPosition.objects.filter(drafted=False)
		# openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		# open_position_data['drafted-position'] = openposition_serializer.data
	elif user.profile.is_ae:
		open_positions = OpenPosition.objects.filter(client__in=json.loads(user.profile.client), archieved=False, drafted=False, filled=False, trashed=False)
		openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		open_position_data['open-position'] = openposition_serializer.data
		open_position_data['count'] = open_positions.count()

		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			count = open_positions.filter(created_at__month=current_month, created_at__year=current_year).count()
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1

		# open_positions = OpenPosition.objects.filter(client__in=json.loads(user.profile.client), archieved=False)
		# openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		# open_position_data['archived-position'] = openposition_serializer.data

		# open_positions = OpenPosition.objects.filter(client__in=json.loads(user.profile.client), drafted=False)
		# openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		# open_position_data['drafted-position'] = openposition_serializer.data
	else:
		client = Client.objects.get(id=int(user.profile.client))
		open_positions = OpenPosition.objects.filter(client=client.id, archieved=False, drafted=False, filled=False, trashed=False)
		openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		open_position_data['open-position'] = openposition_serializer.data
		open_position_data['count'] = open_positions.count()

		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			count = open_positions.filter(created_at__month=current_month, created_at__year=current_year).count()
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1

		# open_positions = OpenPosition.objects.filter(client=client.id, archieved=False)
		# openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		# open_position_data['archived-position'] = openposition_serializer.data

		# open_positions = OpenPosition.objects.filter(client=client.id, drafted=False)
		# openposition_serializer = OpenPositionSerializer(open_positions, many=True)
		# open_position_data['drafted-position'] = openposition_serializer.data
	open_position_data['class'] = 'open-position'
	open_position_data['chart-data'] = monthly_data
	return open_position_data


def get_client_openposition_data(client_id):
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	open_position_data = {}
	client = Client.objects.get(id=client_id)
	open_positions = OpenPosition.objects.filter(client=client.id, archieved=False, drafted=False, filled=False, trashed=False)
	openposition_serializer = OpenPositionSerializer(open_positions, many=True)
	open_position_data['open-position'] = openposition_serializer.data
	open_position_data['count'] = open_positions.count()

	current_month = datetime.now().month
	current_year = datetime.now().year
	monthly_data = []
	for i in range(0, 12):
		count = open_positions.filter(created_at__month=current_month, created_at__year=current_year).count()
		month = months[current_month-1]
		temp_dict = {}
		temp_dict['count'] = count
		temp_dict['month'] = month
		monthly_data.append(temp_dict)
		current_month -= 1
		if current_month == 0:
			current_month = 12
			current_year = current_year - 1
	open_position_data['class'] = 'open-position'
	open_position_data['chart-data'] = monthly_data
	return open_position_data



def get_liked_candidates_data(user):
	liked_candidates_data = {}
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	if user.is_superuser:
		open_position_list = list(OpenPosition.objects.filter(drafted=False, archieved=False, filled=False, trashed=False).values_list('id', flat=True))
		candidates_obj = []
		# for i in Candidate.objects.all():
		# 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
		# 		candidates_obj.append(i.candidate_id)
		for cao in CandidateAssociateData.objects.filter(open_position__id__in=open_position_list):
			candidates_obj.append(cao.candidate.candidate_id)
		# candidates_serializer = CandidateSerializer(candidates_obj, many=True)
		# data = candidates_serializer.data
		liked_candidates_data['count'] = CandidateMarks.objects.filter(candidate_id__in=candidates_obj, op_id__in=open_position_list, thumbs_up=True).count()
		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			count = CandidateMarks.objects.filter(candidate_id__in=candidates_obj, op_id__in=open_position_list, feedback_date__month=current_month, feedback_date__year=current_year, thumbs_up=True).count()
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1
	elif user.profile.is_ae:
		open_position_list = list(OpenPosition.objects.filter(client__in=json.loads(user.profile.client), drafted=False, archieved=False, filled=False, trashed=False).values_list('id', flat=True))
		candidates_obj = []
		# for i in Candidate.objects.all():
		# 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
		# 		candidates_obj.append(i.candidate_id)
		for cao in CandidateAssociateData.objects.filter(open_position__id__in=open_position_list):
			candidates_obj.append(cao.candidate.candidate_id)
		count = 0
		# candidate_ids = []
		# for candidate in candidates_obj:
		# 	temp_count = CandidateMarks.objects.filter(candidate_id=candidate.candidate_id, thumbs_up=True).count()
		# 	count += temp_count
		# 	candidate_ids.append(candidate.candidate_id)
		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			temp_count = CandidateMarks.objects.filter(candidate_id__in=candidates_obj, op_id__in=open_position_list, feedback_date__month=current_month, feedback_date__year=current_year, thumbs_up=True).count()
			count += temp_count
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = temp_count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1
		liked_candidates_data['count'] = count
	else:
		client = Client.objects.get(id=int(user.profile.client))
		open_position_list = list(OpenPosition.objects.filter(client=client.id, drafted=False, archieved=False, filled=False, trashed=False).values_list('id', flat=True))
		candidates_obj = []
		# for i in Candidate.objects.all():
		# 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
		# 		candidates_obj.append(i.candidate_id)
		for cao in CandidateAssociateData.objects.filter(open_position__id__in=open_position_list):
			candidates_obj.append(cao.candidate.candidate_id)
		count = 0
		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			temp_count = CandidateMarks.objects.filter(candidate_id__in=candidates_obj, op_id__in=open_position_list, feedback_date__month=current_month, feedback_date__year=current_year).filter(Q(thumbs_up=True)|Q(golden_gloves=True)).count()
			count += temp_count
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = temp_count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1
		liked_candidates_data['count'] = count
	liked_candidates_data['chart-data'] = monthly_data
	liked_candidates_data['class'] = 'liked-candidate'
	return liked_candidates_data


def get_client_liked_candidates_data(client_id):
	liked_candidates_data = {}
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	client = Client.objects.get(id=client_id)
	open_position_list = list(OpenPosition.objects.filter(client=client.id, drafted=False, archieved=False, filled=False, trashed=False).values_list('id', flat=True))
	candidates_obj = []
	# for i in Candidate.objects.all():
	# 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
	# 		candidates_obj.append(i.candidate_id)
	for cao in CandidateAssociateData.objects.filter(open_position__id__in=open_position_list):
		candidates_obj.append(cao.candidate.candidate_id)
	count = 0
	current_month = datetime.now().month
	current_year = datetime.now().year
	monthly_data = []
	for i in range(0, 12):
		temp_count = CandidateMarks.objects.filter(candidate_id__in=candidates_obj, op_id__in=open_position_list, feedback_date__month=current_month, feedback_date__year=current_year).filter(Q(thumbs_up=True)|Q(golden_gloves=True)).count()
		count += temp_count
		month = months[current_month-1]
		temp_dict = {}
		temp_dict['count'] = temp_count
		temp_dict['month'] = month
		monthly_data.append(temp_dict)
		current_month -= 1
		if current_month == 0:
			current_month = 12
			current_year = current_year - 1
	liked_candidates_data['count'] = count
	liked_candidates_data['chart-data'] = monthly_data
	liked_candidates_data['class'] = 'liked-candidate'
	return liked_candidates_data


def get_passed_candidates_data(user):
	passed_candidates_data = {}
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]	
	if user.is_superuser:
		open_position_list = list(OpenPosition.objects.filter(drafted=False, archieved=False, filled=False, trashed=False).values_list('id', flat=True))
		candidates_obj = []
		# for i in Candidate.objects.all():
		# 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
		# 		candidates_obj.append(i.candidate_id)
		for cao in CandidateAssociateData.objects.filter(open_position__id__in=open_position_list):
			candidates_obj.append(cao.candidate.candidate_id)
		# candidates_serializer = CandidateSerializer(candidates_obj, many=True)
		# data = candidates_serializer.data
		# for i in data:
		# 	pass
		queryset = CandidateMarks.objects.filter(candidate_id__in=candidates_obj, op_id__in=open_position_list, thumbs_down=True)
		passed_candidates_data['count'] = queryset.count()
		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			count = queryset.filter(candidate_id__in=candidates_obj, op_id__in=open_position_list, feedback_date__month=current_month, feedback_date__year=current_year, thumbs_down=True).count()
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1
	elif user.profile.is_ae:
		open_position_list = list(OpenPosition.objects.filter(client__in=json.loads(user.profile.client), drafted=False, archieved=False, filled=False, trashed=False).values_list('id', flat=True))
		candidates_obj = []
		# for i in Candidate.objects.all():
		# 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
		# 		candidates_obj.append(i.candidate_id)
		for cao in CandidateAssociateData.objects.filter(open_position__id__in=open_position_list):
			candidates_obj.append(cao.candidate.candidate_id)
		count = 0
		# candidate_ids = []
		# for candidate in candidates_obj:
		# 	temp_count = CandidateMarks.objects.filter(candidate_id=candidate.candidate_id, thumbs_down=True).count()
		# 	count += temp_count
		# 	candidate_ids.append(candidate.candidate_id)
		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			temp_count = CandidateMarks.objects.filter(candidate_id__in=candidates_obj, op_id__in=open_position_list, thumbs_down=True, feedback_date__month=current_month, feedback_date__year=current_year).count()
			count += temp_count
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = temp_count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1
		passed_candidates_data['count'] = count
	else:
		client = Client.objects.get(id=int(user.profile.client))
		open_position_list = list(OpenPosition.objects.filter(client=client.id, drafted=False, archieved=False, filled=False, trashed=False).values_list('id', flat=True))
		candidates_obj = []
		# for i in Candidate.objects.all():
		# 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
		# 		candidates_obj.append(i.candidate_id)
		for cao in CandidateAssociateData.objects.filter(open_position__id__in=open_position_list):
			candidates_obj.append(cao.candidate.candidate_id)
		count = 0
		current_month = datetime.now().month
		current_year = datetime.now().year
		monthly_data = []
		for i in range(0, 12):
			temp_count = CandidateMarks.objects.filter(candidate_id__in=candidates_obj,  op_id__in=open_position_list, thumbs_down=True, feedback_date__month=current_month, feedback_date__year=current_year).count()
			count += temp_count
			month = months[current_month-1]
			temp_dict = {}
			temp_dict['count'] = temp_count
			temp_dict['month'] = month
			monthly_data.append(temp_dict)
			current_month -= 1
			if current_month == 0:
				current_month = 12
				current_year = current_year - 1
		passed_candidates_data['count'] = count
	passed_candidates_data['chart-data'] = monthly_data
	passed_candidates_data['class'] = 'passed-candidate'
	return passed_candidates_data


def get_client_passed_candidates_data(client_id):
	passed_candidates_data = {}
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]	
	client = Client.objects.get(id=client_id)
	open_position_list = list(OpenPosition.objects.filter(client=client.id, drafted=False, archieved=False, filled=False, trashed=False).values_list('id', flat=True))
	candidates_obj = []
	# for i in Candidate.objects.all():
	# 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
	# 		candidates_obj.append(i.candidate_id)
	for cao in CandidateAssociateData.objects.filter(open_position__id__in=open_position_list):
			candidates_obj.append(cao.candidate.candidate_id)
	count = 0
	current_month = datetime.now().month
	current_year = datetime.now().year
	monthly_data = []
	for i in range(0, 12):
		temp_count = CandidateMarks.objects.filter(candidate_id__in=candidates_obj,  op_id__in=open_position_list, thumbs_down=True, feedback_date__month=current_month, feedback_date__year=current_year).count()
		count += temp_count
		month = months[current_month-1]
		temp_dict = {}
		temp_dict['count'] = temp_count
		temp_dict['month'] = month
		monthly_data.append(temp_dict)
		current_month -= 1
		if current_month == 0:
			current_month = 12
			current_year = current_year - 1
	passed_candidates_data['count'] = count
	passed_candidates_data['chart-data'] = monthly_data
	passed_candidates_data['class'] = 'passed-candidate'
	return passed_candidates_data


def get_interview_data(user):
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	total_interviews_done_data = {}
	total_interviews_not_done_data = {}
	total_interviews_done = 0
	total_interviews_not_done = 0
	if user.is_superuser:
		open_position_list = list(OpenPosition.objects.all().filter(drafted=False, archieved=False, filled=False).values_list("id", flat=True))
	elif user.profile.is_ae:
		open_position_list = list(OpenPosition.objects.filter(client__in=json.loads(user.profile.client)).filter(drafted=False, archieved=False, filled=False, trashed=False).values_list("id", flat=True))
	else:
		client = Client.objects.get(id=int(user.profile.client))
		open_position_list = list(OpenPosition.objects.filter(client=client.id).filter(drafted=False, archieved=False, filled=False, trashed=False).values_list("id", flat=True))
	interviews_count = 0
	all_candidate = []
	for op in open_position_list:
		op_obj = OpenPosition.objects.get(id=op)
		candidates = []
		for cao in CandidateAssociateData.objects.filter(open_position__id=op, withdrawed=False, accepted=True):
			candidates.append(cao.candidate.candidate_id)
			all_candidate.append(cao.candidate.candidate_id)
		# for can in Candidate.objects.all():
		# 	if op in json.loads(can.associated_op_ids):
		# 		candidates.append(can.candidate_id)
		# 		all_candidate.append(can.candidate_id)
		# 	if op in json.loads(can.withdrawed_op_ids):
		# 		try:
		# 			candidates.remove(can.candidate_id)
		# 			all_candidate.remove(can.candidate_id)
		# 		except Exception as e:
		# 			print(e, '-------')
		try:
			members = op_obj.htms.all()
			members_len = members.count()
		except:
			members = []
			members_len = 0
		interviews_count += len(candidates) * members_len
	all_candidate = set(all_candidate)
	# interviews_scheduled = Interview.objects.filter(op_id__in=open_position_list).count()
	# interview_done = 
	completed_count = 0
	scheduled = Interview.objects.filter(op_id__id__in=open_position_list, candidate__candidate_id__in=all_candidate).distinct("candidate", "htm").values("candidate", "htm", "op_id")
	scheduled_count = scheduled.count()
	# for can in set(all_candidates):
	d = CandidateMarks.objects.filter(op_id__in=open_position_list).values("candidate_id",  "marks_given_by", "op_id")
	completed_count += d.count()
	scheduled_completed = [x for x in d if {"candidate":x["candidate_id"], "htm":x["marks_given_by"], "op_id":x["op_id"]} in scheduled]
	scheduled_count -= len(scheduled_completed)
	# total_interviews_done = completed_count
	if completed_count > scheduled.count():
		if scheduled == 0:
			total_interviews_done = 0
		else:
			total_interviews_done = scheduled.count()
	else:
		total_interviews_done = completed_count
	total_interviews_not_done = interviews_count - total_interviews_done
	print(interviews_count, total_interviews_done, total_interviews_not_done, scheduled_count)
	# # candidates_obj = []
	# # for i in Candidate.objects.all():
	# # 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
	# # 		candidates_obj.append(i)
	# # print(candidates_obj, '88')
	# for candidate in candidates_obj:
	# 	total_interviews = 0
	# 	for inter in Interview.objects.filter(candidate=candidate.candidate_id).distinct('op_id'):
	# 		print(inter, '--')
	# 		try:
	# 			op_obj = OpenPosition.objects.get(id=inter.op_id)
	# 			group_obj = HiringGroup.objects.get(group_id=op_obj.hiring_group)
	# 			members = json.loads(group_obj.members)
	# 			print(len(members),'8888888')
	# 			total_interviews += len(members) - 1
	# 		except Exception as e:
	# 			print(e)
	# 		print(interviews_count, '---')
	# 	print(total_interviews, '8888')
	# 	interviews_count = Interview.objects.filter(candidate=candidate.candidate_id).count()
	# 	if interviews_count:
	# 		total_interviews_done += interviews_count
	# 	else:
	# 		total_interviews_not_done = total_interviews_not_done + total_interviews - interviews_count
	# 	print(total_interviews_not_done, total_interviews_done,'***---')
	# print(total_interviews_not_done, total_interviews_done,'***')

	current_month = datetime.now().month
	current_year = datetime.now().year
	monthly_data = []
	for i in range(0, 12):
		count = CandidateMarks.objects.filter(op_id__in=open_position_list, feedback_date__month=current_month, feedback_date__year=current_year).count()
		month = months[current_month-1]
		temp_dict = {}
		temp_dict['count'] = count
		temp_dict['month'] = month
		monthly_data.append(temp_dict)
		current_month -= 1
		if current_month == 0:
			current_month = 12
			current_year = current_year - 1

	total_interviews_done_data['count'] = scheduled_count
	total_interviews_done_data['class'] = 'interview-scheduled'
	total_interviews_done_data['chart-data'] = monthly_data
	total_interviews_not_done_data['count'] = total_interviews_not_done - scheduled_count
	total_interviews_not_done_data['class'] = 'interview-not-scheduled'
	return total_interviews_done_data, total_interviews_not_done_data


def get_client_interview_data(client_id):
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
	total_interviews_done_data = {}
	total_interviews_not_done_data = {}
	total_interviews_done = 0
	total_interviews_not_done = 0
	client = Client.objects.get(id=client_id)
	open_position_list = list(OpenPosition.objects.filter(client=client.id).filter(drafted=False, archieved=False, filled=False, trashed=False).values_list("id", flat=True))
	interviews_count = 0
	all_candidate = []
	for op in open_position_list:
		op_obj = OpenPosition.objects.get(id=op)
		candidates = []
		# for can in Candidate.objects.all():
		# 	if op in json.loads(can.associated_op_ids):
		# 		candidates.append(can.candidate_id)
		# 		all_candidate.append(can.candidate_id)
		# 	if op in json.loads(can.withdrawed_op_ids):
		# 		try:
		# 			candidates.remove(can.candidate_id)
		# 			all_candidate.remove(can.candidate_id)
		# 		except Exception as e:
		# 			print(e)
		for cao in CandidateAssociateData.objects.filter(open_position__id=op, withdrawed=False, accepted=True):
			candidates.append(cao.candidate.candidate_id)
			all_candidate.append(cao.candidate.candidate_id)
		members = op_obj.htms.all()
		if group_obj.hr_profile in members:
			members_len = members.count() - 1
		else:
			members_len = members.count()
		interviews_count += len(candidates) * members_len
	all_candidate = set(all_candidate)
	# interviews_scheduled = Interview.objects.filter(op_id__in=open_position_list).count()
	# interview_done = 
	completed_count = 0
	scheduled = Interview.objects.filter(op_id__id__in=open_position_list, candidate__candidate_id__in=all_candidate).distinct("candidate", "htm").values("candidate", "htm", "op_id")
	scheduled_count = scheduled.count()
	# for can in set(all_candidates):
	d = CandidateMarks.objects.filter(op_id__in=open_position_list).values("candidate_id",  "marks_given_by", "op_id")
	completed_count += d.count()
	scheduled_completed = [x for x in d if {"candidate":x["candidate_id"], "htm":x["marks_given_by"], "op_id":x["op_id"]} in scheduled]
	scheduled_count -= len(scheduled_completed)
	if completed_count > scheduled.count():
		if scheduled == 0:
			total_interviews_done = 0
		else:
			total_interviews_done = scheduled.count()
	else:
		total_interviews_done = completed_count
	total_interviews_not_done = interviews_count - total_interviews_done
	# # candidates_obj = []
	# # for i in Candidate.objects.all():
	# # 	if any(x in json.loads(i.associated_op_ids) for x in open_position_list):
	# # 		candidates_obj.append(i)
	# # print(candidates_obj, '88')
	# for candidate in candidates_obj:
	# 	total_interviews = 0
	# 	for inter in Interview.objects.filter(candidate=candidate.candidate_id).distinct('op_id'):
	# 		print(inter, '--')
	# 		try:
	# 			op_obj = OpenPosition.objects.get(id=inter.op_id)
	# 			group_obj = HiringGroup.objects.get(group_id=op_obj.hiring_group)
	# 			members = json.loads(group_obj.members)
	# 			print(len(members),'8888888')
	# 			total_interviews += len(members) - 1
	# 		except Exception as e:
	# 			print(e)
	# 		print(interviews_count, '---')
	# 	print(total_interviews, '8888')
	# 	interviews_count = Interview.objects.filter(candidate=candidate.candidate_id).count()
	# 	if interviews_count:
	# 		total_interviews_done += interviews_count
	# 	else:
	# 		total_interviews_not_done = total_interviews_not_done + total_interviews - interviews_count
	# 	print(total_interviews_not_done, total_interviews_done,'***---')
	# print(total_interviews_not_done, total_interviews_done,'***')

	current_month = datetime.now().month
	current_year = datetime.now().year
	monthly_data = []
	for i in range(0, 12):
		count = CandidateMarks.objects.filter(op_id__in=open_position_list, feedback_date__month=current_month, feedback_date__year=current_year).count()
		month = months[current_month-1]
		temp_dict = {}
		temp_dict['count'] = count
		temp_dict['month'] = month
		monthly_data.append(temp_dict)
		current_month -= 1
		if current_month == 0:
			current_month = 12
			current_year = current_year - 1

	total_interviews_done_data['count'] = scheduled_count
	total_interviews_done_data['class'] = 'interview-scheduled'
	total_interviews_done_data['chart-data'] = monthly_data
	total_interviews_not_done_data['count'] = total_interviews_not_done - scheduled_count
	total_interviews_not_done_data['class'] = 'interview-not-scheduled'
	return total_interviews_done_data, total_interviews_not_done_data


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def create_email_templates(client_obj):
	try:
		email_templates = EmailTemplate.objects.filter(client=None).exclude(name="Qorums Welcome Mail to CA")
		for template in email_templates:
			template.pk = None
			template.client = client_obj
			template.save()
		return "created"
	except:
		return "error"
