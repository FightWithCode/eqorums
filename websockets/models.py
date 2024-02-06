from django.db import models


class AppNotification(models.Model):
	username = models.CharField(max_length=255)
	message = models.CharField(max_length=255)
	read = models.BooleanField(default=False)
	new = models.BooleanField(default=True)
