# Django imports
from django.contrib import admin

# models imports
from openposition.models import (
    OpenPosition, 
    CandidateMarks,
    Interview,
    Hired,
    Offered,
    HTMWeightage,
    CandidateAssociateData
)

admin.site.register(OpenPosition)
admin.site.register(CandidateMarks)
admin.site.register(Interview)
admin.site.register(Hired)
admin.site.register(HTMWeightage)
admin.site.register(Offered)
admin.site.register(CandidateAssociateData)
