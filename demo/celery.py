# django_celery/celery.py

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")
app = Celery("demo")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.task_always_eager = False
app.conf.timezone = 'EST'
app.autodiscover_tasks()
