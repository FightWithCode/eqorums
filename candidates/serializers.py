# python imports
import json

# drf imports
from rest_framework import serializers

# models import
from candidates.models import Candidate
from openposition.models import CandidateMarks
from candidates.utils import get_candidate_profile

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
