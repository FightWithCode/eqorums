import json

from dashboard.models import EmailTemplate
from dashboard.models import Profile
from clients.models import Client


def update_assigned_clients():
	for i in Profile.objects.filter(is_ae=True):
		client_list = []
		for j in Client.objects.filter(ae_assigned=i.user.username, disabled=False):
			client_list.append(j.id)
		i.client = json.dumps(client_list)
		i.save()
	return True


def create_email_templates(client_obj):
	try:
		email_templates = EmailTemplate.objects.filter(client=None).exclude(name="Qorums Welcome Mail to CA")
		for template in email_templates:
			template.pk = None
			template.client = client_obj
			template.save()
		return "created"
	except:
		return "error"
	
def get_ca_data(profile, data={}):
	data["ca_first_name"] = profile.user.first_name
	data["ca_last_name"] = profile.user.last_name
	data["key_contact_phone_no"] = profile.phone_number
	data["key_contact_skype_id"] = profile.skype_id
	data["job_title"] = profile.job_title
	data["key_contact_email"] = profile.email
	data["key_username"] = profile.user.username
	return data
