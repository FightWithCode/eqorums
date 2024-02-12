# django imports
from django.contrib import admin

# models import
from dashboard.models import (
    Profile, 
    EmailTemplate, 
    ProTip
)


admin.site.register(Profile)
admin.site.register(EmailTemplate)
admin.site.register(ProTip)
