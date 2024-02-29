
from django.urls import path
from . import views

app_name = "candidates"

urlpatterns = [
    path(
        "search-candidates",
        views.SearchCandidateView.as_view(),
        name="search-candidates",
    ),
    path(
        "get-all-candidates",
        views.AllCandidateDataView.as_view(),
        name="get-all-candidates",
    ),
]