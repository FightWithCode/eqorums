# Django imports
from django.contrib import admin

# models imports
from openposition.models import (
    OpenPosition, 
    CandidateMarks,
)

admin.site.register(OpenPosition)
admin.site.register(CandidateMarks)
