
from django.urls import path
from . import views

app_name = "clients"

urlpatterns = [
    path(
        "signup-client",
        views.SignupClientDataView.as_view(),
        name="signup-client",
    ),
    path(
        "client-data",
        views.SingleClientDataView.as_view(),
        name="client-data",
    ),
    path(
        "get-all-client",
        views.GetAllClientsData.as_view(),
        name="get-all-client",
    ),
]