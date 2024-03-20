# python imports
import requests
import json
from datetime import datetime, timedelta

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
                "redirect_uri": request.GET.get("redirect_uri")
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
                    obj.refresh_token=resp_data.get("refresh_token")
                    obj.sub = resp_data.get("sub")
                    obj.account_id = resp_data.get("account_id")
                else:
                    obj.access_token = resp_data.get("access_token")
                    obj.refresh_token=resp_data.get("refresh_token")
                obj.save()
                return Response({"data": "token generated"}, status=status.HTTP_200_OK)
            else:
                return Response({"data": response.json()}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class ListCalendars(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        try:
            url = "https://api.cronofy.com/v1/calendars"
            access_token = GetAccessToken(request.user)
            payload = {}
            headers = {
                'Authorization': 'Bearer {}'.format(access_token)
            }
            response = requests.request("GET", url, headers=headers, data=payload)
            if response.status_code == 200:
                return Response({"data": response.json(), "msg": "Calendars Fetched"}, status=status.HTTP_200_OK)
            else:
                return Response({"data": response.json()}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

class GetElementToken(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        try:
            response = {}
            url = "https://api.cronofy.com/v1/element_tokens"
            obj, created = CronofyAuthCode.objects.get_or_create(user=request.user)
            if created:
                response["msg"] = "User not authenticated with Cronofy. Please authenticate!"
                return Response(response, status=status.HTTP_401_UNAUTHORIZED)

            payload = json.dumps({
                "version": "1",
                "permissions": [
                    "account_management",
                    "availability",
                    "managed_availability"
                ],
                "subs": [
                    obj.sub
                ],
                "origin": request.GET.get("origin")
            })

            headers = {
                'Authorization': 'Bearer {}'.format(settings.CRONOFY_CLIENT_SECRET),
                'Content-Type': 'application/json'
            }

            api_resp = requests.request("POST", url, headers=headers, data=payload)
            if api_resp.status_code in [200, 201]:
                response["msg"] = "success"
                response["data"] = api_resp.json()
                return Response(response, status=status.HTTP_200_OK)
            else:
                response["msg"] = "error"
                response["data"] = api_resp.json()
                return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CheckAccessToken(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        try:
            response = {}
            obj, created = CronofyAuthCode.objects.get_or_create(user=request.user)
            if created:
                response["msg"] = "invalid token"
                return Response(response, status=status.HTTP_200_OK)
            else:
                current_time = datetime.now()
                three_hours_ago = current_time - timedelta(minutes=175)
                if obj.updated_at > three_hours_ago:
                    response["msg"] = "valid token"
                    response["data"] = None
                    return Response(response, status=status.HTTP_200_OK)
                else:
                    # get refresh token and auth token
                    url = "https://api.cronofy.com/oauth/token"
                    print(obj.refresh_token, obj.access_token)
                    payload = json.dumps({
                        "client_id": settings.CRONOFY_CLIENT_ID,
                        "client_secret": settings.CRONOFY_CLIENT_SECRET,
                        "grant_type": "refresh_token",
                        "refresh_token": obj.refresh_token
                    })
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    cronofy_resp = requests.request("POST", url, headers=headers, data=payload)
                    print(cronofy_resp.text)
                    if cronofy_resp.status_code == 200:
                        resp_data = cronofy_resp.json()
                        obj.access_token = resp_data.get("access_token")
                        obj.save()
                        response["msg"] = "valid token"
                        response["data"] = None
                        return Response(response, status=status.HTTP_200_OK)
                    else:
                        response["msg"] = "invalid token"
                        response["data"] = cronofy_resp.json()
                        return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
