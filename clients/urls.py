
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
    path(
        "get-client-positions/<int:client_id>",
        views.GetPositionByClient.as_view(),
        name="get-client-positions"
    ),
    path(
        "get-all-htms/<int:client_id>",
        views.GetHTMsByClient.as_view(),
        name="get-all-htms"
    ),
    path(
        "delete-clients",
        views.DeleteClients.as_view(),
        name="delete-clients"
    ),
    path(
        "suspend-clients",
        views.SuspendClients.as_view(),
        name="suspend-clients"
    ),
    path(
        "activate-clients",
        views.ActivateClients.as_view(),
        name="activate-clients"
    ),
    path(
        "basic-client-details",
        views.BasicClientDetailView.as_view(),
        name="basic-client-details"
    ),
]