from django.urls import path
from . import views

app_name = "schedules"

urlpatterns = [
    path(
        "get-auth-code",
        views.GetAuthCode.as_view(),
        name="get-auth-code",
    )
]