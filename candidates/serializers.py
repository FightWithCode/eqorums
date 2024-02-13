# python imports
import json

# drf imports
from rest_framework import serializers

# models import
from candidates.models import Candidate
from openposition.models import CandidateMarks


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
		if 'profile_pic_url' in instance.linkedin_data and instance.linkedin_data['profile_pic_url'] and instance.linkedin_data['profile_pic_url'] != "null":
			return instance.linkedin_data['profile_pic_url']
		else:
			return instance.profile_photo
	
	def get_is_withdrawn(self, obj):
		if json.loads(obj.withdrawed_op_ids):
			return True
		else:
			return False

