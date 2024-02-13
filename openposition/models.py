# python imports
import json
from datetime import datetime
from datetime import date

# django imports
from django.db import models
from django.conf import settings

# models import
from dashboard.models import (
    Profile
)
from clients.models import (
    Client
)

def get_listed_json_default():
    return []

def get_json_default():
    return {}


class OpenPosition(models.Model):
    """
        Stores all the Open Positions of a Client
    """
    old_id = models.IntegerField(default=0)
    position_id = models.CharField(default=None, max_length=25, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    position_title = models.CharField(max_length=100)
    reference = models.TextField(null=True, blank=True)
    special_intruction = models.TextField(null=True, blank=True)

    hiring_group = models.ForeignKey("openposition.HiringGroup", on_delete=models.SET_NULL, null=True, blank=True)
    htms = models.ManyToManyField(Profile, related_name="htms")
    htms_color = models.JSONField(default=get_listed_json_default)
    withdrawed_members = models.ManyToManyField(Profile, related_name="withdrawed_members")

    kickoff_start_date = models.DateField(default=date.today(), null=True, blank=True)
    sourcing_deadline = models.DateField(default=date.today(), null=True, blank=True)
    target_deadline = models.DateField(default=date.today(), null=True, blank=True)
    
    stages = models.JSONField(default=get_listed_json_default)

    final_round_completetion_date = models.DateField(null=True, blank=True)
    final_round_completetion_date_completed = models.BooleanField(default=False, null=True, blank=True)
    
    # Skillsets - each item contains {skillset_name:, skillset_weightage:, skillset_questions:[]}
    skillsets = models.JSONField(default=get_listed_json_default)
    # init_qualify_ques_1 = models.CharField(max_length=255, null=True, blank=True)
    # init_qualify_ques_2 = models.CharField(max_length=255, null=True, blank=True)
    # init_qualify_ques_3 = models.CharField(max_length=255, default='NA', null=True, blank=True)
    # init_qualify_ques_4 = models.CharField(max_length=255, default='NA', null=True, blank=True)
    # init_qualify_ques_5 = models.CharField(max_length=255, default='NA', null=True, blank=True)
    # init_qualify_ques_6 = models.CharField(max_length=255, default='NA', null=True, blank=True)
    # init_qualify_ques_7 = models.CharField(max_length=255, default='NA', null=True, blank=True)
    # init_qualify_ques_8 = models.CharField(max_length=255, default='NA', null=True, blank=True)

    # Skillset weightage
    # init_qualify_ques_weightage_1 = models.IntegerField(default=0, null=True, blank=True)
    # init_qualify_ques_weightage_2 = models.IntegerField(default=0, null=True, blank=True)
    # init_qualify_ques_weightage_3 = models.IntegerField(default=0, null=True, blank=True)
    # init_qualify_ques_weightage_4 = models.IntegerField(default=0, null=True, blank=True)
    # init_qualify_ques_weightage_5 = models.IntegerField(default=0, null=True, blank=True)
    # init_qualify_ques_weightage_6 = models.IntegerField(default=0, null=True, blank=True)
    # init_qualify_ques_weightage_7 = models.IntegerField(default=0, null=True, blank=True)
    # init_qualify_ques_weightage_8 = models.IntegerField(default=0, null=True, blank=True)

    # Suggested question corresponding skillset
    # init_qualify_ques_suggestion_1 = models.TextField(default=None, null=True, blank=True)
    # init_qualify_ques_suggestion_2 = models.TextField(default=None, null=True, blank=True)
    # init_qualify_ques_suggestion_3 = models.TextField(default=None, null=True, blank=True)
    # init_qualify_ques_suggestion_4 = models.TextField(default=None, null=True, blank=True)
    # init_qualify_ques_suggestion_5 = models.TextField(default=None, null=True, blank=True)
    # init_qualify_ques_suggestion_6 = models.TextField(default=None, null=True, blank=True)
    # init_qualify_ques_suggestion_7 = models.TextField(default=None, null=True, blank=True)
    # init_qualify_ques_suggestion_8 = models.TextField(default=None, null=True, blank=True)
    
    currency = models.CharField(max_length=10, default='$', blank=True, null=True)
    salary_range = models.CharField(max_length=255, default='NIL', null=True, blank=True)
    local_preference = models.CharField(max_length=255, default='NIL', null=True, blank=True)
    other_criteria = models.TextField(default='NIL', null=True, blank=True)
    disabled = models.BooleanField(default=False)
    no_of_open_positions = models.IntegerField(default=1, null=True, blank=True)
    filled = models.BooleanField(default=False)
    filled_date = models.DateTimeField(default=None, blank=True, null=True)
    work_auth = models.CharField(max_length=255, default=None, blank=True, null=True)
    work_location = models.CharField(max_length=255, default=None, blank=True, null=True)
    # For Copying a OpenPosition
    copied_from = models.IntegerField(default=0) # Copied OP ID
    copied_from_position = models.ForeignKey("openposition.OpenPosition", on_delete=models.SET_NULL, default=None, null=True, blank=True) # Copied OP ID
    drafted = models.BooleanField(default=False)

    archieved = models.BooleanField(default=False)
    trashed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.filled and self.filled_date is None:
            self.filled_date = datetime.now()
        elif self.filled is False:
            self.filled_date = None
        if self.position_id == None:
            self.created_at = datetime.now()
            self.position_id = self.created_at.strftime("%m%d%Y%H%S")
        super(OpenPosition, self).save(*args, **kwargs)

    def __str__(self):
        return self.position_title


class PositionDoc(models.Model):
    openposition = models.ForeignKey(OpenPosition, on_delete=models.CASCADE)
    file = models.FileField(upload_to="position")


class HTMsDeadline(models.Model):
    """
        Contains details of HTMs dead lines for a specific open position
    """
    open_position = models.ForeignKey("openposition.OpenPosition",  on_delete=models.CASCADE)
    htm = models.ForeignKey(Profile, on_delete=models.CASCADE)
    deadline = models.DateTimeField()
    color = models.CharField(max_length=10, default="#ff00aa", null=True, blank=True)


class HiringGroup(models.Model):
    """
        Contains details of a Hiring Group
    """
    group_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    members_list = models.ManyToManyField(Profile, default=None, blank=True, null=True)
    client_id = models.IntegerField(default=0, null=True, blank=True)
    disabled = models.BooleanField(default=False)


class CandidateAssociateData(models.Model):
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE)   
    open_position = models.ForeignKey("openposition.OpenPosition", on_delete=models.CASCADE)
    nickname = models.CharField(max_length=255, default=None, blank=True, null=True)
    location = models.CharField(max_length=255, default=None, blank=True, null=True)
    currently = models.CharField(max_length=255, default=None, blank=True, null=True)
    email = models.CharField(max_length=255, default=None, blank=True, null=True)
    phone = models.CharField(max_length=255, default=None, blank=True, null=True)
    linkedin = models.CharField(max_length=255, default=None, blank=True, null=True)
    generalComments = models.TextField(default=None, blank=True, null=True)
    remote_only = models.BooleanField(default=True)
    remote_pref = models.BooleanField(default=True)
    some_in_office = models.BooleanField(default=True)
    office_only = models.BooleanField(default=True)
    work_auth = models.CharField(max_length=255, null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True, default='$')
    salary_req = models.CharField(max_length=255, null=True, blank=True)
    desired_work_location = models.JSONField(default=get_json_default)
    comments = models.CharField(max_length=255, null=True, blank=True)
    resume = models.JSONField(default=get_listed_json_default)
    references = models.JSONField(default=get_listed_json_default)
    pro_marketting = models.BooleanField(default=False)
    association_date = models.DateField(default=None, null=True, blank=True)
    # None - Requested, True - Acceppted, False - Rejected
    accepted = models.BooleanField(default=None, null=True, blank=True)
    withdrawed = models.BooleanField(default=False)


class CandidateMarks(models.Model):
    """
        Stores marks of candidates which are given by
        different HTMs
    """
    old_id = models.IntegerField()
    candidate_id = models.IntegerField()
    marks_given_by = models.IntegerField()
    op_id = models.IntegerField()
    client_id = models.IntegerField(default=0)
    
    # marks = models.JSONField(default=get_listed_json_default)

    criteria_1_marks = models.FloatField(null=True, blank=True)
    criteria_2_marks = models.FloatField(null=True, blank=True)
    criteria_3_marks = models.FloatField(null=True, blank=True)
    criteria_4_marks = models.FloatField(null=True, blank=True)
    criteria_5_marks = models.FloatField(null=True, blank=True)
    criteria_6_marks = models.FloatField(null=True, blank=True)
    criteria_7_marks = models.FloatField(null=True, blank=True)
    criteria_8_marks = models.FloatField(null=True, blank=True)

    suggestion_1 = models.TextField(null=True, blank=True, default="None")
    suggestion_2 = models.TextField(null=True, blank=True, default="None")
    suggestion_3 = models.TextField(null=True, blank=True, default="None")
    suggestion_4 = models.TextField(null=True, blank=True, default="None")
    suggestion_5 = models.TextField(null=True, blank=True, default="None")
    suggestion_6 = models.TextField(null=True, blank=True, default="None")
    suggestion_7 = models.TextField(null=True, blank=True, default="None")
    suggestion_8 = models.TextField(null=True, blank=True, default="None")

    all_marks_given = models.BooleanField(default=False)
    thumbs_up = models.BooleanField(default=False)
    thumbs_down = models.BooleanField(default=False)
    hold = models.BooleanField(default=False)
    thumbs = models.IntegerField(default=0) # 1 - for thumbs up, 2 - for thumbs down, 3 - for hold
    golden_gloves = models.BooleanField(default=False)
    feedback_date = models.DateField(auto_now=True)
    feedback = models.TextField(default='None', null=True, blank=True)


class Interview(models.Model):
    old_id = models.IntegerField(default=0)
    op_id = models.ForeignKey("openposition.OpenPosition", default=None, null=True, blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(Profile, default=None, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_by")
    htm = models.ManyToManyField(Profile, default=None, null=True, blank=True)
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, default=None, blank=True, null=True)
    subject = models.CharField(max_length=255, default="No Subject")
    body = models.TextField(default="No Body")
    zoom_link = models.TextField(default="none", null=True, blank=True)
    interview_date_time = models.DateTimeField(default=None, null=True, blank=True)
    texted_start_time = models.CharField(max_length=255, default=json.dumps([]))
    duration = models.IntegerField(default=30) # in minutes
    initial_informed = models.BooleanField(default=False)
    informed = models.BooleanField(default=False)
    meeting_key = models.CharField(max_length=256, default=None, null=True, blank=True)
    interview_type = models.CharField(max_length=255, default="zoho")
    accepted = models.BooleanField(default=None, null=True, blank=True)
    conference_id = models.CharField(max_length=50, default=None, null=True, blank=True)
    disabled = models.BooleanField(default=False)


class Hired(models.Model):
    candidate_id = models.IntegerField()
    op_id = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)


class CandidateStatus(models.Model):
    candidate_id = models.IntegerField()
    op_id = models.IntegerField()
    shortlist_status = models.BooleanField(default=False)
    make_offer_status = models.BooleanField(default=False)
    finall_selection_status = models.BooleanField(default=False)

    def __str__(self):
        return str(self.candidate_id)


class Offered(models.Model):
    candidate_id = models.IntegerField()
    op_id = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)


class HTMWeightage(models.Model):
    op_id = models.IntegerField()
    htm_id = models.IntegerField()
    init_qualify_ques_1_weightage = models.IntegerField(default=0)
    init_qualify_ques_2_weightage = models.IntegerField(default=0)
    init_qualify_ques_3_weightage = models.IntegerField(default=0)
    init_qualify_ques_4_weightage = models.IntegerField(default=0) 
    init_qualify_ques_5_weightage = models.IntegerField(default=0)
    init_qualify_ques_6_weightage = models.IntegerField(default=0)
    init_qualify_ques_7_weightage = models.IntegerField(default=0)
    init_qualify_ques_8_weightage = models.IntegerField(default=0)
