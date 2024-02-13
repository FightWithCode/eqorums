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
    path(
        "get-position-summary/<int:op_id>",
        views.GetPositionSummary.as_view(),
        name="get-position-summary"
    ),
    path(
        "all-candidate-feedback/<int:op_id>",
        views.AllCandidateFeedback.as_view(),
        name="candidate-feedback",
    ),
]
