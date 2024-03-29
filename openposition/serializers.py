# python imports
import json
from datetime import datetime

# drf imports
from rest_framework import serializers

# model imports
from openposition.models import (
    OpenPosition,
	HTMsDeadline,
	CandidateMarks,
	Hired,
	Interview,
	PositionDoc,
	CandidateAssociateData
)
from candidates.models import (
	Candidate
)
from dashboard.models import Profile
from hiringgroup.models import HiringGroup

class OpenPositionSerializer(serializers.ModelSerializer):
	updated_by_name = serializers.SerializerMethodField(read_only=True)
	members = serializers.SerializerMethodField(read_only=True)
	position_completion = serializers.SerializerMethodField(read_only=True)
	formated_target_deadline = serializers.SerializerMethodField(read_only=True)
	has_pending_int = serializers.SerializerMethodField(read_only=True)
	position_filled = serializers.SerializerMethodField(read_only=True)
	status = serializers.SerializerMethodField(read_only=True)
	decumentation = serializers.SerializerMethodField(read_only=True)
	senior_manager = serializers.SerializerMethodField(read_only=True)

	class Meta:
		model = OpenPosition
		fields = '__all__'
	def get_senior_manager(self, obj):
		try:
			senior_managers = []
			for sm in Profile.objects.filter(roles__contains=["is_sm"], client=str(obj.client.id)):
				senior_managers.append(sm.user.get_full_name())
			if senior_managers:
				return ", ".join(senior_managers)
			else:
				return "{}()".format(Profile.objects.filter(roles__contains=["is_ca"], client=str(obj.client.id)))[0].user.get_full_name()
		except:
			return "NA"
	def get_decumentation(self, obj):
		doc_urls = []
		for i in PositionDoc.objects.filter(openposition=obj):
			doc_urls.append(i.file.url)
		return doc_urls
	def get_position_filled(self, obj):
		return Hired.objects.filter(op_id=obj.id).count()
	def get_status(self, obj):
		if obj.drafted:
			return "Drafted"
		elif obj.archieved:
			return "On Hold"
		elif obj.trashed:
			return "Trashed"
		elif obj.disabled:
			return "Disabled"
		elif obj.filled:
			return"Completed"
		else:
			return "Active"
	def get_formated_target_deadline(self, obj):
		try:
			return obj.target_deadline.strftime("%B %d, %Y")
		except Exception as e:
			return obj.target_deadline

	def get_updated_by_name(self, obj):
		if obj.updated_by:
			return obj.updated_by.get_full_name()
		else:
			return None
	
	def get_has_pending_int(self, obj):
		candidate_id = self.context.get("candidate_id")
		if Interview.objects.filter(op_id__id=obj.id, candidate__candidate_id=candidate_id).filter(disabled=False).filter(accepted=None):
			return True
		else:
			return False
	def get_members(self, obj):
		try:
			members = obj.htms.all()
			data = []
			candidates_obj = 0
			for k in Candidate.objects.all():
				if obj.id in json.loads(k.associated_op_ids):
					candidates_obj += 1
			for i in members:
				temp_dict = {}
				temp_dict["id"] = i.id
				deadline  = HTMsDeadline.objects.filter(open_position=obj, htm=i)
				interview_taken = CandidateMarks.objects.filter(marks_given_by=i.id, op_id=obj.id).count()
				if deadline:
					delta  = deadline.first().deadline - datetime.now()
					temp_dict["daysToDeadline"] = delta.days
					if candidates_obj:
						temp_dict["percentageCompletion"] = round(interview_taken / candidates_obj * 100)
					else:
						temp_dict["percentageCompletion"] = 0
					temp_dict["weightage"] = deadline.first().skillset_weightage
				else:
					temp_dict["percentageCompletion"] = 0
					temp_dict["wightage"] = None
				try:
					htm_obj = i
					temp_dict["name"] = htm_obj.user.get_full_name()
					temp_dict["profile_pic"] = htm_obj.profile_photo.url if str(htm_obj.profile_photo) not in ["", "None", "null"] else None
					temp_dict["job_title"] = htm_obj.job_title
					temp_dict["phone"] = htm_obj.phone_number
					temp_dict["email"] = htm_obj.email
					temp_dict["roles"] = htm_obj.roles
					try:
						temp_dict["masked_phone"] = htm_obj.phone_number[-4:].rjust(len(htm_obj.phone_number), '*')
						listed_email = htm_obj.email.split('@')
						listed_email[0] = listed_email[0][-4:].rjust(len(listed_email[0]), '*')
						temp_dict["masked_email"] = "@".join(listed_email)
					except:
						temp_dict["masked_email"] = htm_obj.email
						temp_dict["masked_phone"] = htm_obj.phone_number
					temp_dict["skype"] = htm_obj.skype_id
				except:
					pass
				if i in obj.withdrawed_members.all():
					temp_dict['is_withdrawed'] = True
				else:
					temp_dict['is_withdrawed'] = False
				data.append(temp_dict)
			return data
		except Exception as e:
			return []
	
	def get_position_completion(self, obj):
		try:
			data = {}
			members = obj.htms.all()
			candidates_obj = 0
			for cao in CandidateAssociateData.objects.filter(open_position=obj, accepted=True, withdrawed=False):
				candidates_obj += 1
			oldest_deadline = None
			interview_taken = 0
			total_interview = 0
			for i in members:
				temp_dict = {}
				deadline  = HTMsDeadline.objects.filter(open_position=obj, htm=i)
				if oldest_deadline and deadline.first() and deadline.first().deadline > oldest_deadline:
					oldest_deadline = deadline.first().deadline
				elif oldest_deadline is None:
					oldest_deadline = deadline.first().deadline
				interview_taken += CandidateMarks.objects.filter(marks_given_by=i.id, op_id=obj.id).count()
				total_interview += candidates_obj
			delta  = oldest_deadline - datetime.now()
			data["daysToDeadline"] = delta.days
			if candidates_obj:
				data["percentageCompletion"] = round(interview_taken / total_interview * 100)
			else:
				data["percentageCompletion"] = 0
			return data
		except Exception as e:
			print(e, '-----------------')
			return {"percentageCompletion": 0}
