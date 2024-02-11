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
