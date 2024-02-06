from django.shortcuts import render
from channels.layers import get_channel_layer
from rest_framework.views import APIView
from rest_framework.response import Response
from asgiref.sync import async_to_sync
import json
from rest_framework import status
from .models import AppNotification


class SendNotification(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(data.get("to"), {
            'type': 'chat.message', 'msg': data.get("message")
        })
        return Response({})


class AppNotificationView(APIView):
    def get(self, request, username):
        response = {}
        try:
            notifications = []
            new_found = False
            for notification in AppNotification.objects.filter(username=username, read=False).order_by('-id'):
                temp_dict = {}
                temp_dict['id'] = notification.id
                temp_dict['username'] = notification.username
                temp_dict['message'] = notification.message
                if notification.new:
                    new_found = True
                    notification.new = False
                    notification.save()
                notifications.append(temp_dict)
            response['msg'] = 'success'
            response['notifications'] = notifications
            response['new_notification'] = new_found
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response['msg'] = 'error'
            response['error'] = str(e)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, username):
        response = {}
        try:
            notifications = request.data.get('notifications')
            for i in notifications:
                try:
                    obj = AppNotification.objects.get(id=i)
                    obj.read = True
                    obj.save()
                except:
                    pass
            response['msg'] = 'notifications read'
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            response['msg'] = 'error'
            response['error'] = str(e)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
