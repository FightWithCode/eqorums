# python imports
import requests
import json

# django imports
from django.conf import settings

# drf imports
from rest_framework import status
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

# model imports
from schedules.models import CronofyAuthCode

# utils import
from schedules.coronfy_utils import GetAccessToken

class GetAuthCode(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, code):
        try:
            url = "https://api.cronofy.com/oauth/token"
            payload = json.dumps({
                "client_id": settings.CRONOFY_CLIENT_ID,
                "client_secret": settings.CRONOFY_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:4200/ca/my-calender"
            })
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
                resp_data = response.json()
                obj, created = CronofyAuthCode.objects.get_or_create(user=request.user)
                if created:
                    obj.access_token = resp_data.get("access_token")
                    obj.refresh_token=resp_data.get("access_token")
                    obj.sub = resp_data.get("sub")
                    obj.account_id = resp_data.get("account_id")
                else:
                    obj.access_token = resp_data.get("access_token")
                    obj.refresh_token=resp_data.get("access_token")
                obj.save()
                return Response({"data": "token generated"}, status=status.HTTP_200_OK)
            else:
                return Response({"data": response.json()}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class ListCalendars(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, code):
        try:
            url = "https://api.cronofy.com/v1/calendars"
            access_token = GetAccessToken(request.user)
            payload = {}
            headers = {
                'Authorization': 'Bearer {}'.format(access_token)
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
                return Response({"data": response.json(), "msg": "Calendars Fetched"}, status=status.HTTP_200_OK)
            else:
                return Response({"data": response.json()}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    