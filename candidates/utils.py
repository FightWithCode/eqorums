from candidates.models import Candidate
from openposition.models import CandidateMarks


def get_candidate_profile(instance):
    if 'profile_pic_url' in instance.linkedin_data and instance.linkedin_data['profile_pic_url'] not in ["null", "", None]:
        return instance.linkedin_data['profile_pic_url']
    else:
        return instance.temp_profile_photo.url if str(instance.temp_profile_photo) not in ["null", "", "None"] else None
    

def get_candidate_profile_by_id(candidate_id):
    try:
        instance = Candidate.objects.get(candidate_id=candidate_id)
        if 'profile_pic_url' in instance.linkedin_data and instance.linkedin_data['profile_pic_url'] not in ["null", "", None]:
            return instance.linkedin_data['profile_pic_url']
        else:
            return instance.temp_profile_photo.url if str(instance.temp_profile_photo) not in ["null", "", "None"] else None
    except:
        return None

def get_holds_no(instance):
		return CandidateMarks.objects.filter(candidate_id=instance.candidate_id, op_id=instance.candidate_id, hold=True).count()

def get_offer_no(instance):
    return CandidateMarks.objects.filter(candidate_id=instance.candidate_id, op_id=instance.candidate_id, thumbs_up=True).count()

def get_pass_no(instance):
    return CandidateMarks.objects.filter(candidate_id=instance.candidate_id, op_id=instance.candidate_id, thumbs_down=True).count()
