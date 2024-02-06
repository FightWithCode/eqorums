from django.urls import path
from . import views

app_name = 'websockets'

urlpatterns = [
    path(
        "app-notification/<str:username>",
        views.AppNotificationView.as_view(),
        name="app-notification",
    ),
    path(
        "send/",
        views.SendNotification.as_view(),
        name="send",
    ),
]