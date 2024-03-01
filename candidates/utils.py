from candidates.models import Candidate
from openposition.models import CandidateMarks, CandidateAssociateData


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


def get_current_submission_status(candidate, op_obj):
    try:
        cao_obj = CandidateAssociateData.objects.get(candidate=candidate, open_position=op_obj)
        if cao_obj.modification:
            result = "modification"
        elif cao_obj.accepted:
            result = "accepted"
        elif cao_obj.accepted == False:
            result = "rejected"
        else:
            result = "invited"
        return result
    except:
         return None