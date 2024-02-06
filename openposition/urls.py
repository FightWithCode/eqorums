# python imports
from knox import views as knox_views

# django imports
from django.urls import path

# utils import
from openposition import views

app_name = "openposition"

urlpatterns = [
    path(
        "open-position",
        views.OpenPositionView.as_view(),
        name="open-position",
    ),
]
