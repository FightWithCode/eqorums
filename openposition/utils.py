# python imports
import json
import pytz
from datetime import datetime

# import models
from openposition.models import CandidateMarks, Interview


def get_skillsets_data(data):
    skillsets = []
    skillset_data = []
    temp_data = {}
    temp_data["init_qualify_ques_1"] = data.get("init_qualify_ques_1")
    temp_data["init_qualify_ques_weightage_1"] = data.get("init_qualify_ques_weightage_1")
    temp_data["init_qualify_ques_suggestion_1"] = json.loads(data.get("init_qualify_ques_suggestion_1"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_2"] = data.get("init_qualify_ques_2")
    temp_data["init_qualify_ques_weightage_2"] = data.get("init_qualify_ques_weightage_2")
    temp_data["init_qualify_ques_suggestion_2"] = json.loads(data.get("init_qualify_ques_suggestion_2"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_3"] = data.get("init_qualify_ques_3")
    temp_data["init_qualify_ques_weightage_3"] = data.get("init_qualify_ques_weightage_3")
    temp_data["init_qualify_ques_suggestion_3"] = json.loads(data.get("init_qualify_ques_suggestion_3"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_4"] = data.get("init_qualify_ques_4")
    temp_data["init_qualify_ques_weightage_4"] = data.get("init_qualify_ques_weightage_4")
    temp_data["init_qualify_ques_suggestion_4"] = json.loads(data.get("init_qualify_ques_suggestion_4"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_5"] = data.get("init_qualify_ques_5")
    temp_data["init_qualify_ques_weightage_5"] = data.get("init_qualify_ques_weightage_5")
    temp_data["init_qualify_ques_suggestion_5"] = json.loads(data.get("init_qualify_ques_suggestion_5"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_6"] = data.get("init_qualify_ques_6")
    temp_data["init_qualify_ques_weightage_6"] = data.get("init_qualify_ques_weightage_6")
    temp_data["init_qualify_ques_suggestion_6"] = json.loads(data.get("init_qualify_ques_suggestion_6"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_7"] = data.get("init_qualify_ques_7")
    temp_data["init_qualify_ques_weightage_7"] = data.get("init_qualify_ques_weightage_7")
    temp_data["init_qualify_ques_suggestion_7"] = json.loads(data.get("init_qualify_ques_suggestion_7"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_8"] = data.get("init_qualify_ques_8")
    temp_data["init_qualify_ques_weightage_8"] = data.get("init_qualify_ques_weightage_8")
    temp_data["init_qualify_ques_suggestion_8"] = json.loads(data.get("init_qualify_ques_suggestion_8"))
    skillset_data.append(temp_data)
    return skillsets


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
		print("in else")
		temp_dict['flag'] = 'Not Given'
		try:
			interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[htm_profile], candidate__candidate_id=candidate_id)[0]
			extra_data = get_htm_specific_data(interview_obj, htm_profile)
			print(extra_data)
			temp_dict.update(extra_data)
		except Exception as e:
			print(e, htm_profile.user.get_full_name(), candidate_id)
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
