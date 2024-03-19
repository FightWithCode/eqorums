# authURL = https://app.cronofy.com/oauth/authorize?response_type=code&client_id={{client_id}}&redirect_uri=localhost&scope=read_write

# models import
from schedules.models import CronofyAuthCode


def GetAccessToken(user):
    obj = CronofyAuthCode.objects.get(user=user)
    return obj.access_token