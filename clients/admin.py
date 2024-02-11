from django.contrib import admin
from clients.models import (
    Client,
    Package, 
    ClientPackage,
    ExtraAccountsPrice,
    StripePayments
)

admin.site.register(Client)
admin.site.register(Package)
admin.site.register(ClientPackage)
admin.site.register(ExtraAccountsPrice)
admin.site.register(StripePayments)
