from django.urls import path
from . import views

app_name = "schedules"

urlpatterns = [
    path(
        "get-auth-code/<str:code>",
        views.GetAuthCode.as_view(),
        name="get-auth-code",
    ),
    path(
        "list-calendars",
        views.ListCalendars.as_view(),
        name="list-calendars",
    ),
    path(
        "get-element-token",
        views.GetElementToken.as_view(),
        name="get-element-token",
    ),
]