import requests
import json
from django.conf import settings

BASE_URL = settings.IOTUM_BASE_URL

def  get_iotum_auth_code():
    url = "{}/enterprise_api/authenticate".format(BASE_URL)
    payload = json.dumps({
		"email": settings.IOTUM_EMAIL,
		"password": settings.IOTUM_PASSWORD
    })
    headers = {
		'Content-Type': 'application/json',
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    resp_json = response.json()
    if "auth_token" in resp_json:
        return resp_json['auth_token']
    else:
        return None


def get_host_and_create_meeting(htm, subject, start_time, emails):
	auth_token = get_iotum_auth_code()
	if htm.iotum_host_id:
		pass
	else:
		url = "{}/enterprise_api/host/create".format(BASE_URL)
		payload = json.dumps({
			"auth_token": auth_token,
			"company_id": 1184916,
			"name": htm.user.get_full_name(),
			"email": htm.email,
			"password": settings.IOTUM_PASSWORD_RAN,
			"one_time_access_code": True,
			"no_welcome_email": True,
			"role": "HOST",
			"auto_record": True,
			"auto_stream": "none",
			"host_initiated_recording": False,
			"waiting_room": True,
			"stream_preview": {
				"duration": 60,
				"interval": 300,
				"image_preview": True
			}
		})
		headers = {
		'Content-Type': 'application/json',
		}
		response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
		resp_json = response.json()
		if "host_id" in resp_json:
			htm.iotum_host_id  = resp_json.get('host_id')
			htm.save()
	url = "{}/enterprise_api/conference/create/reservationless".format(BASE_URL)
	payload = json.dumps({
		"auth_token": auth_token,
		"host_id": htm.iotum_host_id,
		"subject": subject,
		"agenda": subject,
		"start": start_time, #"2023-03-23 23:00:00",
		"time_zone": "EST",
		"duration": 60,
		"auto_record": True,
		"auto_stream": "none",
		"auto_transcribe": False,
		"one_time_access_code": True,
		"secure_url": False,
		"host_initiated_recording": True,
		"security_pin": "123456",
		"mute_mode": "conversation",
		"participant_emails": emails
	})
	headers = {
		'Content-Type': 'application/json',
	}
	response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
	resp_json = response.json()
	if "room_url" in resp_json:
		return resp_json.get("room_url"), resp_json.get("moderator_token"), resp_json.get("conference_id")
	else:
		return None
        
def create_meeting_room(host_id, subject, start_time, emails):
	auth_token = get_iotum_auth_code()
	url = "{}/enterprise_api/conference/create/reservationless".format(BASE_URL)
	payload = json.dumps({
		"auth_token": auth_token,
		"host_id": host_id,
		"subject": subject,
		"agenda": subject,
		"start": start_time, #"2023-03-23 23:00:00",
		"time_zone": "EST",
		"duration": 60,
		"auto_record": True,
		"auto_stream": "none",
		"auto_transcribe": False,
		"one_time_access_code": False,
		"secure_url": False,
		"host_initiated_recording": True,
		"security_pin": "123456",
		"mute_mode": "conversation",
		"participant_emails": emails
	})
	headers = {
		'Content-Type': 'application/json',
	}
	response = requests.request("POST", url, headers=headers, data=payload)
	resp_json = response.json()
	if "room_url" in resp_json:
		return resp_json.get("room_url"), resp_json.get("moderator_token")
	else:
		return None


def end_meeting(conference_id):
	auth_token = get_iotum_auth_code()
	url = "{}/enterprise_api/conference/end".format(BASE_URL)
	payload = json.dumps({
		"auth_token": auth_token,
		"conference_id": conference_id
	})
	headers = {
		'Content-Type': 'application/json',
	}
	response = requests.request("POST", url, headers=headers, data=payload)
	resp_json = response.json()
	return True
	
