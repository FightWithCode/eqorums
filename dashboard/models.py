# python imports
import uuid
import secrets
import json
import random
from datetime import date
from datetime import datetime
# django imports
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
from django.conf import settings


EMAIL_TYPES = (
    ("candidate", "Candidate"),
    ("team", "Team"),
    ("announcements", "Announcements"),
)


SUBS_STATUS = (
    ("active", "Active"),
    ("inactive", "Inactive"),
)


def get_json_default():
    return []


def get_json_default():
    return {}


def get_listed_json_default():
    return []


class Profile(models.Model):
    """
        Proxy model to use User model. It contains all the related 
        data to all the users like SA, QA, HTM, HM SM
    """
    old_id = models.IntegerField(default=0)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=17, blank=False)
    cell_phone = models.CharField(max_length=17, blank=True, null=True)
    
    nickname = models.CharField(max_length=255, null=True, blank=True, default=None)
    skype_id = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=255, unique=True) # Check all the email before migration on server
    job_title = models.CharField(max_length=255, default=None, null=True, blank=True)
    roles = models.JSONField(default=get_listed_json_default) # 
    is_candidate = models.BooleanField(default=False, verbose_name="Is Candidate")
    client = models.CharField(max_length=512, default='[]') # Stores json list if profile is AM/SM, else stores integer
    color = models.CharField(max_length=10, default="#ff00aa")
    rankings = models.JSONField(default=get_listed_json_default) # Works same as JOSNField using import json
    tnc_accepted = models.BooleanField(default=False)
    profile_photo = models.FileField(default=None, null=True, upload_to="profiles")

    notification_data = models.JSONField(default=[])
    # For CA to check if its their first log to show form or to not.
    first_log = models.BooleanField(default=True)
    cognito_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    dark_mode = models.BooleanField(default=False)

    iotum_host_id = models.CharField(max_length=50, default=None, blank=True, null=True)
    # stripe customer id
    customer_id = models.CharField(max_length=50, default=None, blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.user.get_full_name()


class OpenPositionStageCompletion(models.Model):
    """
        Used to store Stage related Data. Not used any more.
    """
    op_id = models.IntegerField(default=0)
    hiring_team_interviews_days = models.BooleanField(default=False)
    short_list_selection_days = models.BooleanField(default=False)
    second_round_interview_days = models.BooleanField(default=False)
    final_selection_days = models.BooleanField(default=False)
    make_offer_days = models.BooleanField(default=False)
    decision_days = models.BooleanField(default=False)


class PositionTitle(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class QualifyingQuestion(models.Model):
    question = models.CharField(max_length=255)

    def __str__(self):
        return self.question


class CandidatePositionDetails(models.Model):
    candidate_id = models.IntegerField()
    op_id = models.IntegerField()
    question_response = models.TextField(default='[]')
    uploaded_docs = models.TextField(default='[]')


class TempCandidate(models.Model):
    """
        Used to store temporary candidates - Not used anymore
    """
    uid = models.CharField(max_length=255)
    linkedin_first_name = models.CharField(max_length=255)
    linkedin_last_name = models.CharField(max_length=255)
    linkedin_email = models.CharField(max_length=255)


class CandidateMarks(models.Model):
    """
        Stores marks of candidates which are given by
        different HTMs
    """
    old_id = models.IntegerField(default=0)
    candidate_id = models.IntegerField()
    marks_given_by = models.IntegerField()
    op_id = models.IntegerField()
    client_id = models.IntegerField(default=0)
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


# Not used anymore
class Department(models.Model):
    client = models.IntegerField()
    name = models.CharField(max_length=255)
    hod = models.IntegerField(default=0)

    def __str__(self):
        return str(self.id) + '. ' + self.name


class InterviewSchedule(models.Model):
    candidate = models.IntegerField()
    event_id = models.CharField(max_length=255)
    start_time = models.CharField(max_length=255)
    end_time = models.CharField(max_length=255)
    timezone = models.CharField(max_length=255, default='IST')
    candidate_response = models.TextField(default='No Response')
    htm_message = models.TextField(default='None')
    op_id = models.IntegerField()


class AskedNotification(models.Model):
    user = models.IntegerField()
    op_id = models.IntegerField()
    asked = models.BooleanField(default=False)


class Hired(models.Model):
    candidate_id = models.IntegerField()
    op_id = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)


class Offered(models.Model):
    candidate_id = models.IntegerField()
    op_id = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)


class ScheduleTemplate(models.Model):
    template_name = models.CharField(max_length=255, default='None', null=True, blank=True)

    step_1_label = models.TextField(default='None', null=True, blank=True)
    step_1_start = models.IntegerField()
    step_1_end = models.IntegerField()

    steps = models.TextField(default=json.dumps([]))
    
    step_8_end = models.IntegerField()

    client = models.IntegerField(default=0)


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
    weightages = models.JSONField(default=get_json_default)


class HTMAvailability(models.Model):
    htm_id = models.IntegerField()
    availability = models.TextField(default='[]')
    color = models.CharField(default=None, null=True, blank=True, max_length=7)

    def save(self, *args, **kwargs):
        if self.color is None:
            r = lambda: random.randint(0,255)
            self.color = '#%02X%02X%02X' % (r(),r(),r())
        super(HTMAvailability, self).save(*args, **kwargs)


class CandidateAvailability(models.Model):
    candidate_id = models.IntegerField()
    availability = models.TextField(default='[]')
    color = models.CharField(default=None, null=True, blank=True, max_length=7)

    def save(self, *args, **kwargs):
        if self.color is None:
            r = lambda: random.randint(0,255)
            self.color = '#%02X%02X%02X' % (r(),r(),r())
        super(CandidateAvailability, self).save(*args, **kwargs)


# class Interview(models.Model):
#     op_id = models.ForeignKey("openposition.OpenPosition", default=None, null=True, blank=True, on_delete=models.CASCADE)
#     created_by = models.ForeignKey(Profile, default=None, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_by")
#     htm = models.ManyToManyField(Profile, default=None, null=True, blank=True)
#     candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE, default=None, blank=True, null=True)
#     subject = models.CharField(max_length=255, default="No Subject")
#     body = models.TextField(default="No Body")
#     zoom_link = models.TextField(default="none", null=True, blank=True)
#     interview_date_time = models.DateTimeField(default=None, null=True, blank=True)
#     texted_start_time = models.CharField(max_length=255, default=json.dumps([]))
#     duration = models.IntegerField(default=30) # in minutes
#     initial_informed = models.BooleanField(default=False)
#     informed = models.BooleanField(default=False)
#     meeting_key = models.CharField(max_length=256, default=None, null=True, blank=True)
#     interview_type = models.CharField(max_length=255, default="zoho")
#     accepted = models.BooleanField(default=None, null=True, blank=True)
#     conference_id = models.CharField(max_length=50, default=None, null=True, blank=True)
#     disabled = models.BooleanField(default=False)


class APIData(models.Model):
    data = models.TextField()


class SelectedAnalyticsDashboard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    selected = models.TextField(default=json.dumps([]))



class ProTip(models.Model):
    candidate_protip = models.TextField(default='', blank=True, null=True)
    dashboard_protip = models.TextField(default='', blank=True, null=True)
    new_position_protip = models.TextField(default='', blank=True, null=True)
    hiring_teams_protip = models.TextField(default='', blank=True, null=True)
    team_members_protip = models.TextField(default='', blank=True, null=True)
    senior_manager_protip = models.TextField(default='', blank=True, null=True)
    support_protip = models.TextField(default='', blank=True, null=True)
    client_protip = models.TextField(default='', blank=True, null=True)
    open_position_protip = models.TextField(default='', blank=True, null=True)
    position_protip = models.TextField(default='', blank=True, null=True)
    settings_protip = models.TextField(default='', blank=True, null=True)
    candidate_adv_search_protip = models.TextField(default='', blank=True, null=True)
    candidate_dash_protip = models.TextField(default='', blank=True, null=True)
    three_col_page_protip = models.TextField(default='', blank=True, null=True)
    # Add more here if required


# class CandidateAssociateData(models.Model):
#     candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE)   
#     open_position = models.ForeignKey("openposition.OpenPosition", on_delete=models.CASCADE)
#     nickname = models.CharField(max_length=255, default=None, blank=True, null=True)
#     location = models.CharField(max_length=255, default=None, blank=True, null=True)
#     currently = models.CharField(max_length=255, default=None, blank=True, null=True)
#     email = models.CharField(max_length=255, default=None, blank=True, null=True)
#     phone = models.CharField(max_length=255, default=None, blank=True, null=True)
#     linkedin = models.CharField(max_length=255, default=None, blank=True, null=True)
#     generalComments = models.TextField(default=None, blank=True, null=True)
#     remote_only = models.BooleanField(default=True)
#     remote_pref = models.BooleanField(default=True)
#     some_in_office = models.BooleanField(default=True)
#     office_only = models.BooleanField(default=True)
#     work_auth = models.CharField(max_length=255, null=True, blank=True)
#     currency = models.CharField(max_length=10, null=True, blank=True, default='$')
#     salary_req = models.CharField(max_length=255, null=True, blank=True)
#     desired_work_location = models.JSONField(default=get_json_default)
#     comments = models.CharField(max_length=255, null=True, blank=True)
#     resume = models.JSONField(default=get_listed_json_default)
#     references = models.JSONField(default=get_listed_json_default)
#     pro_marketting = models.BooleanField(default=False)
#     association_date = models.DateField(default=None, null=True, blank=True)
#     # None - Requested, True - Acceppted, False - Rejected
#     accepted = models.BooleanField(default=None, null=True, blank=True)
#     withdrawed = models.BooleanField(default=False)


class EvaluationComment(models.Model):
    given_by = models.ForeignKey(Profile, on_delete=models.CASCADE)
    position = models.ForeignKey("openposition.OpenPosition", on_delete=models.CASCADE)
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE)
    notes = models.TextField()
    date = models.DateTimeField(auto_now=True)


class WithdrawCandidateData(models.Model):
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.CASCADE)
    open_position = models.ForeignKey("openposition.OpenPosition", on_delete=models.SET_NULL, null=True, blank=True)


class EmailTemplate(models.Model):
    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)
    description = models.TextField(default=None, null=True, blank=True)
    type = models.CharField(max_length=255, choices=EMAIL_TYPES, default="candidate")
    content = models.TextField()

    def __str__(self):
        try:
            return str(self.client.company_name) + ' - ' + self.name    
        except:
            return str("None") + ' - ' + self.name

class OTPRequested(models.Model):
    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)


class ExtraAccountsPrice(models.Model):
    package = models.ForeignKey("clients.Package", on_delete=models.CASCADE)
    sm_count = models.IntegerField(default=1)
    sm_price = models.FloatField(default=1)
    hm_count = models.IntegerField(default=1)
    hm_price = models.FloatField(default=1)
    htm_count = models.IntegerField(default=1)
    htm_price = models.FloatField(default=1)
    tc_count = models.IntegerField(default=1)
    tc_price = models.FloatField(default=1)


class BillingDetail(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    # addr details
    billing_contact = models.CharField(max_length=255, default="None", blank=True, null=True)
    billing_email = models.CharField(max_length=255, default="None", blank=True, null=True)
    billing_phone = models.CharField(max_length=255, default="None", blank=True, null=True)
    addr_line_1 = models.TextField(default=None, blank=True, null=True)
    addr_line_2 = models.TextField(default=None, blank=True, null=True)
    city = models.CharField(max_length=255, default=None, blank=True, null=True)
    state = models.CharField(max_length=255, default=None, blank=True, null=True)
    pincode = models.CharField(max_length=10, default=None, blank=True, null=True)
    # cards details
    card_number = models.CharField(max_length=50, default=None, blank=True, null=True)
    name_on_card = models.CharField(max_length=100, default=None, blank=True, null=True)
    exp_date = models.CharField(max_length=5, default=None, blank=True, null=True)
    security = models.CharField(max_length=3, default=None, blank=True, null=True)

# handled for invoicing
class StripePayments(models.Model):
    customer = models.CharField(max_length=255)
    client = models.ForeignKey("clients.Client", on_delete=models.SET_NULL, default=None, blank=True, null=True)
    payment_id = models.CharField(max_length=255, default=None, null=True, blank=True)
    payment_secret = models.CharField(max_length=255, default=None, null=True, blank=True)
    type = models.CharField(max_length=255, default="one-time")
    cycle = models.CharField(max_length=255, default=None, null=True, blank=True)
    amount = models.FloatField(default=0.0)
    created = models.DateTimeField(auto_now=True)
    updated = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, choices=SUBS_STATUS, default='incomplete')
    data = models.JSONField(default=get_json_default)
    price_breakdown = models.JSONField(default=get_json_default)


class StripeWebhookData(models.Model):
    data = models.JSONField()
    created = models.DateTimeField(auto_now=True)
    updated = models.DateTimeField(auto_now_add=True)


class UserActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_name = models.CharField(max_length=255)
    resp_data = models.JSONField(default=get_json_default)
    status = models.IntegerField(default=200)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()}'s activity of {self.activity_name} on {self.created_at.strftime('%b %d, %Y')}"


class InvitedUser(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.CharField(max_length=255, unique=True)
    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE)
    role = models.CharField(max_length=255, default="is_candidate")
    accepted = models.BooleanField(default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Email: {self.email}, Accepted: {self.accepted}"
