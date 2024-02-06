from django.contrib import admin
from clients.models import Client, Package, ClientPackage

admin.site.register(Client)
admin.site.register(Package)
admin.site.register(ClientPackage)