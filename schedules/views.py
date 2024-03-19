# python imports
import requests
import json

# django imports
from django.conf import settings

# drf imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class GetAuthCode(APIView):
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
                return Response({"data": response.json()}, status=status.HTTP_200_OK)
            else:
                return Response({"data": response.json()}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"msg": "error", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)