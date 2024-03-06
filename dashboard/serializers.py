from rest_framework import serializers
import json
from datetime import datetime
from clients.models import Client, ClientPackage, Package
from openposition.models import Interview, OpenPosition, HTMsDeadline, CandidateAssociateData, CandidateStatus, HTMWeightage
from hiringgroup.models import HiringGroup
from .models import (
	Profile,
	PositionTitle,
	QualifyingQuestion,
	OpenPositionStageCompletion,
	CandidateMarks,
	Department,
	ScheduleTemplate,
	ProTip,
	EvaluationComment,
	EmailTemplate,
	ExtraAccountsPrice,
	BillingDetail,
	Hired,
	StripePayments,
	InvitedUser
)
from django.contrib.auth.models import User
from django.db.models import Sum
from candidates.models import Candidate
# Utils imports
from candidates.utils import get_candidate_profile


class ChangePasswordSerializer(serializers.Serializer):
    model = User
    username = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class UsernameSerializer(serializers.Serializer):
	class Meta:
		model = User
		fields = ['username']


class ProfileSerializer(serializers.ModelSerializer):
	class Meta:
		model = Profile
		fields = '__all__'
	

class CustomProfileSerializer(serializers.ModelSerializer):
	username = serializers.SerializerMethodField()
	first_name = serializers.SerializerMethodField()
	last_name = serializers.SerializerMethodField()
	client_id = serializers.SerializerMethodField()
	client_names = serializers.SerializerMethodField()
	class Meta:
		model = Profile
		fields = ('username', 'id', 'first_name', 'last_name', 'phone_number', 'skype_id', 'job_title', 'email', 'profile_photo', 'roles', 'client_id', 'client_names')
	
	def get_username(self, obj):
		return obj.user.username
	
	def get_first_name(self, obj):
		return obj.user.first_name

	def get_last_name(self, obj):
		return obj.user.last_name

	def get_client_id(self, obj):
		clients = []
		try:
			for i in json.loads(obj.client):
				clients.append(i)
		except:
			clients.append(obj.client)
		return clients
	def get_client_names(self, obj):
		clients_name = []
		try:
			for i in json.loads(obj.client):
				clients = Client.objects.filter(id=i)
				for client in clients:
					clients_name.append(client.company_name)
		except:
			clients = Client.objects.filter(id=obj.client)
			for client in clients:
				clients_name.append(client.company_name)
		return ", ".join(clients_name)

class OpenPositionSerializer(serializers.ModelSerializer):
	updated_by_name = serializers.SerializerMethodField(read_only=True)
	members = serializers.SerializerMethodField(read_only=True)
	position_completion = serializers.SerializerMethodField(read_only=True)
	formated_target_deadline = serializers.SerializerMethodField(read_only=True)
	has_pending_int = serializers.SerializerMethodField(read_only=True)
	hiring_manager = serializers.SerializerMethodField(read_only=True)
	hiring_team = serializers.SerializerMethodField(read_only=True)
	position_filled = serializers.SerializerMethodField(read_only=True)
	status = serializers.SerializerMethodField(read_only=True)
	decumentation = serializers.SerializerMethodField(read_only=True)
	class Meta:
		model = OpenPosition
		fields = '__all__'
	
	def get_hiring_manager(self, obj):
		try:
			hiring_group_obj = HiringGroup.objects.get(group_id=obj.hiring_group)
			if hiring_group_obj.hod_profile:
				return hiring_group_obj.hod_profile.user.get_full_name()
			else:
				return "Not Selected"
		except Exception as e:
			return "No Team"
	def get_hiring_team(self, obj):
		try:
			hiring_group_obj = HiringGroup.objects.get(group_id=obj.hiring_group)
			return hiring_group_obj.name
		except Exception as e:
			return "No Team"
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
			group_obj = HiringGroup.objects.get(group_id=obj.hiring_group)
			members = list(group_obj.members_list.all())
			if group_obj.hr_profile in members:
				members.remove(group_obj.hr_profile)
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
				try:
					htm_obj = i
					temp_dict["name"] = htm_obj.user.get_full_name()
					temp_dict["profile_pic"] = htm_obj.profile_photo
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
					if htm_obj==group_obj.hod_profile:
						temp_dict['isHod'] = True
					else:
						temp_dict['isHod'] = False
					if htm_obj == group_obj.hr_profile:
						temp_dict['isHr'] = True
					else:
						temp_dict['isHr'] = False
				except:
					pass
				if i in json.loads(obj.withdrawed_members):
					temp_dict['is_withdrawed'] = True
				else:
					temp_dict['is_withdrawed'] = False
				data.append(temp_dict)
			return data
		except:
			return []
	
	def get_position_completion(self, obj):
		try:
			data = {}
			group_obj = HiringGroup.objects.get(group_id=obj.hiring_group)
			members = list(group_obj.members_list.all())
			if group_obj.hr_profile in members:
				try:
					members.remove(group_obj.hr_profile)
				except:
					pass
			candidates_obj = 0
			for k in Candidate.objects.all():
				if obj.id in json.loads(k.associated_op_ids):
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
		except:
			return {"percentageCompletion": 0}

# class HiringStageTimeSerializers(serializers.ModelSerializer):
# 	class Meta:
# 		model = HiringStageTime
# 		fields = '__all__'

class ClientSerializer(serializers.ModelSerializer):
	class Meta:
		model = Client
		fields = '__all__'


class HiringGroupSerializer(serializers.ModelSerializer):
	class Meta:
		model = HiringGroup
		fields = '__all__'

class GetHiringGroupSerializer(serializers.ModelSerializer):
	members = serializers.SerializerMethodField()
	hiring_manager = serializers.SerializerMethodField()
	hiring_resource = serializers.SerializerMethodField()
	members_color = serializers.SerializerMethodField()
	def get_members(self, obj):
		return list(obj.members_list.all().values_list("id", flat=True))
	def get_hiring_manager(self, obj):
		try:
			return obj.hod_profile.user.get_full_name()
		except:
			return ""
	def get_hiring_resource(self, obj):
		try:
			return obj.hr_profile.user.get_full_name()
		except:
			return ""
	
	def get_members_color(self, obj):
		data = []
		for i in obj.members_color:
			temp_data = {}
			temp_data["htm"] = i["htm"]
			temp_data["color"] = i["color"]
			if obj.hod_profile and i["htm"] == obj.hod_profile.id:
				temp_data["isHm"] = True
				temp_data["isHr"] = False
			elif obj.hr_profile and i["htm"] == obj.hr_profile.id:
				temp_data["isHm"] = False
				temp_data["isHr"] = True
			else:
				temp_data["isHm"] = False
				temp_data["isHr"] = False
			htm_obj = Profile.objects.get(id=i["htm"])
			temp_data["name"] = htm_obj.user.get_full_name()
			temp_data["profile_pic"] = htm_obj.profile_photo
			data.append(temp_data)
		return data
	class Meta:
		model = HiringGroup
		fields = '__all__'


class PositionTitleSerializer(serializers.ModelSerializer):
	class Meta:
		model = PositionTitle
		fields = '__all__'


class QualifyingQuestionSerializer(serializers.ModelSerializer):
	class Meta:
		model = QualifyingQuestion
		fields = '__all__'


class OpenPositionStageCompletionSerializer(serializers.ModelSerializer):
	class Meta:
		model = OpenPositionStageCompletion
		fields = '__all__'


class CandidateSerializer(serializers.ModelSerializer):
	holds_no = serializers.SerializerMethodField()
	offer_no = serializers.SerializerMethodField()
	pass_no = serializers.SerializerMethodField()
	profile_photo = serializers.SerializerMethodField()
	is_withdrawn = serializers.SerializerMethodField()
	class Meta:
		model = Candidate
		exclude = ('key', 'username')

	def get_holds_no(self, instance):
		return CandidateMarks.objects.filter(candidate_id=instance.candidate_id, op_id=instance.candidate_id, hold=True).count()

	def get_offer_no(self, instance):
		return CandidateMarks.objects.filter(candidate_id=instance.candidate_id, op_id=instance.candidate_id, thumbs_up=True).count()

	def get_pass_no(self, instance):
		return CandidateMarks.objects.filter(candidate_id=instance.candidate_id, op_id=instance.candidate_id, thumbs_down=True).count()

	def get_profile_photo(self, instance):
		return get_candidate_profile(instance)
	
	def get_is_withdrawn(self, obj):
		if json.loads(obj.withdrawed_op_ids):
			return True
		else:
			return False


class CandidateMarksSerializer(serializers.ModelSerializer):
	class Meta:
		model = CandidateMarks
		fields = '__all__'


class DepartmentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Department
		fields = '__all__'


class CandidateStatusSerializer(serializers.ModelSerializer):
	class Meta:
		model = CandidateStatus
		fields = '__all__'


class ScheduleTemplateSerializer(serializers.ModelSerializer):
	class Meta:
		model = ScheduleTemplate
		fields = '__all__'


class HTMWeightageSerializer(serializers.ModelSerializer):
	class Meta:
		model = HTMWeightage
		fields = '__all__'


class ProTipSerializer(serializers.ModelSerializer):
	class Meta:
		model = ProTip
		fields = '__all__'


class CandidateAssociateDataSerializer(serializers.ModelSerializer):
	class Meta:
		model = CandidateAssociateData
		fields = '__all__'


class EvaluationCommentSerializer(serializers.ModelSerializer):
	class Meta:
		model = EvaluationComment
		fields = '__all__'


class HTMsDeadlineSerializer(serializers.ModelSerializer):
	class Meta:
		model = HTMsDeadline
		fields = '__all__'


class EmailTemplateSerializer(serializers.ModelSerializer):
	class Meta:
		model = EmailTemplate
		fields = '__all__'


class PackageSerializer(serializers.ModelSerializer):
	class Meta:
		model = Package
		fields = '__all__'


class ClientPackageSerializer(serializers.ModelSerializer):
	class Meta:
		model = ClientPackage
		fields = '__all__'


class ExtraAccountsPriceSerializer(serializers.ModelSerializer):
	class Meta:
		model = ExtraAccountsPrice
		fields = '__all__'


class BillingDetailSerializer(serializers.ModelSerializer):
	class Meta:
		model = BillingDetail
		fields = '__all__'



def CustomClientSerializer(objs):
	data = []
	for i in objs:
		temp_dict = {}
		temp_dict["id"] = i.id
		temp_dict["logo"] = i.logo.url if i.logo else None 
		temp_dict["client_name"] = i.company_name
		temp_dict["client_admin"] = "{} {}".format(i.ca_first_name, i.ca_last_name)
		# Get Subscription Data
		try:
			client_package = ClientPackage.objects.get(client=i)
			temp_dict["subscription"] = client_package.package.name
		except:
			temp_dict["subscription"] = None
		# Get total amt paid
		avt_amt = StripePayments.objects.filter(client=i).aggregate(Sum('amount', default=0))['amount__sum']
		temp_dict["total_paid"] = round(avt_amt, 2) if avt_amt else 0
		# Get total candidates added
		temp_dict["candidates_added"] = Candidate.objects.filter(created_by_client=i.id).count()
		temp_dict["interviews_done"] = Interview.objects.filter(op_id__client=i.id).count()
		data.append(temp_dict)
	return data


class InvitedUserSerializer(serializers.ModelSerializer):
	class Meta:
		model = InvitedUser
		fields = '__all__'


class SignupUserSerializer(serializers.ModelSerializer):
	confirm_password = serializers.CharField(write_only=True)

	class Meta:
		model = User
		fields = ["confirm_password", "email", "password", "first_name", "last_name"]

	def validate_email(self, value):
		if User.objects.filter(email=value.lower()):
			raise serializers.ValidationError("User with this email already exists!")
		return value



class SignupProfileSerializer(serializers.ModelSerializer):
	user = SignupUserSerializer(required=True)
	
	class Meta:
		model = Profile
		fields = ["user", "phone_number", "cell_phone", "skype_id", "email", "job_title", "profile_photo"]
	
	def create(self, validated_data):
		user_data = validated_data.pop("user")
		user_data.pop("confirm_password")
		user_obj = User(**user_data)
		user_obj.set_password(user_data['password'])
		user_obj.save()
		profile_obj = Profile.objects.create(user=user_obj, **validated_data)
		return profile_obj
	
	def validate_email(self, value):
		if Profile.objects.filter(email=value.lower()) or User.objects.filter(email=value.lower()):
			raise serializers.ValidationError("User with this email already exists!")
		return value


class SignupCandidateSerializer(serializers.ModelSerializer):
	user = SignupUserSerializer(required=True)
	
	class Meta:
		model = Candidate
		fields = ["user", "phone_number", "cell_phone", "skype_id", "email", "job_title", "profile_photo"]
	
	def create(self, validated_data):
		user_data = validated_data.pop("user")
		user_data.pop("confirm_password")
		user_obj = User(**user_data)
		user_obj.set_password(user_data['password'])
		user_obj.save()
		profile_obj = Profile.objects.create(user=user_obj, **validated_data)
		candidate_obj = Candidate.objects.create(**validated_data)
		return candidate_obj
	
	def validate_email(self, value):
		if Profile.objects.filter(email=value.lower()) or User.objects.filter(email=value.lower()):
			raise serializers.ValidationError("User with this email already exists!")
		return value

class SignupInvitedUserSerializer(serializers.Serializer):
	email = serializers.EmailField()
	password = serializers.CharField(max_length=255)
	confirm_password = serializers.CharField(max_length=255)
	first_name = serializers.CharField(max_length=255)
	list_name = serializers.CharField(max_length=255)
	salary_range = serializers.CharField(max_length=255, allow_blank=True)
	location = serializers.CharField(max_length=255, allow_blank=True)
	phone_no = serializers.CharField(max_length=15, allow_blank=True)
	work_auth = serializers.CharField(max_length=255, allow_blank=True)
	email = serializers.CharField(max_length=255, allow_blank=True)
	email = serializers.CharField(max_length=255, allow_blank=True)
	email = serializers.CharField(max_length=255, allow_blank=True)
	email = serializers.CharField(max_length=255, allow_blank=True)
