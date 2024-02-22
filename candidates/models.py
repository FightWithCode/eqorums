from django.db import models
from django.conf import settings
from clients.models import Client

def get_json_default():
    return {}


def get_listed_json_default():
    return []


class Candidate(models.Model):
    """
        Contains Data of a Candidate that has been created.
        Many of the fields are not used now.
    """
    old_id = models.IntegerField(default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_by_client = models.ForeignKey(Client, default=None, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=255, default='None')
    key = models.CharField(max_length=255, default='None')
    candidate_id = models.AutoField(primary_key=True)
    associated_client_ids = models.CharField(max_length=255, default='[]')
    associated_op_ids = models.CharField(max_length=255, default='[]')
    withdrawed_op_ids = models.CharField(max_length=255, default='[]')
    requested_op_ids = models.JSONField(max_length=255, default=get_listed_json_default)
    name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, default = 'Last Name')
    nickname = models.CharField(max_length=255, default="None", null=True, blank=True)
    linkedin_first_name = models.CharField(max_length=255, blank=True)
    linkedin_last_name = models.CharField(max_length=255, blank=True)
    linkedin_data = models.JSONField(default=get_json_default, null=True, blank=True)
    last_fetched = models.DateField(default=None, null=True, blank=True)
    phone_number = models.CharField(max_length=17, blank=False)
    skype_id = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=255)
    alernate_email = models.CharField(max_length=255, blank=True)
    document = models.FileField(blank=True, null=True)
    documents = models.CharField(max_length=10000, default='[]')
    references = models.CharField(max_length=10000, default='[]')
    profile_photo = models.CharField(max_length=500, default=None, null=True)
    temp_profile_photo = models.FileField(upload_to="candidates", default=None, null=True)
    interview_status = models.CharField(default='NotSet', null=True, blank=True, max_length=255)
    job_title = models.CharField(max_length=255, default="Not Specified",null=True, blank=True)
    location = models.CharField(max_length=255, default="Not Specified",null=True, blank=True)
    
    # Association data
    desired_work_location = models.CharField(max_length=255, default="Not Specified",null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True, default='$')
    salaryRange = models.CharField(max_length=255, default="Not Specified",null=True, blank=True)
    work_auth = models.CharField(max_length=255, default="Not Specified",null=True, blank=True)
    personal_notes = models.CharField(max_length=255, default="Not Specified",null=True, blank=True)
    comments = models.TextField(default="Not Specified",null=True, blank=True)
    skillsets = models.JSONField(default=get_json_default(), null=True, blank=True)
    additional_info = models.TextField(default="N.A", null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True)
    last_associated_at = models.DateTimeField(null=True, blank=True, default=None)
