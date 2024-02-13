# djago imports
from django.db import models
# models import
from dashboard.models import Profile


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
