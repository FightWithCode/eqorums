from django.conf import settings 
import requests
import json


def get_flexb_auth_code():
	try:
		url = "https://auth.flexbooker.com/connect/token"

		payload = 'grant_type=client_credentials&client_id=' + str(settings.FLEX_BOOKER_ID) + '&client_secret=' + str(settings.FLEX_BOOKER_SECRET)
		headers = {
		  'Content-Type': 'application/x-www-form-urlencoded'
		}

		response = requests.request("POST", url, headers=headers, data=payload)

		json_response = json.loads(response.text)
		return json_response['access_token']
	except Exception as e:
		print(e)
		return 0


def get_employees_detail():
	try:
		url = "https://merchant-api.flexbooker.com/account"
		payload = {}
		token = get_flexb_auth_code()
		headers = {
		  'Authorization': 'Bearer ' + token
		}
		response = requests.request("GET", url, headers=headers, data=payload)
		json_response = json.loads(response.text)
		# print(json_response)
		return json_response['employees']
	except Exception as e:
		print(e)
		return []


def create_flexb_employee(email, name, phone):
	try:
		url = "https://merchant-api.flexbooker.com/employee?disableInviteSend=true"
		print(email)
		print(name)
		print(phone)
		payload = {
			"Email": email,
			"FullName": name,
			"Phone": phone,
			"IsAdmin": False,
			"EditOwnBookings": True,
			"EditOwnSchedules": True
		}
		token = get_flexb_auth_code()
		if token:
			pass
		else:
			print('else')
			return "Error Getting Token."
		headers = {
		  'Authorization': 'Bearer ' + token,
		  'Content-Type': 'application/json'
		}
		response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
		json_response = json.loads(response.text)
		print(json_response)
		if json_response['id'] == 0:
			employees = get_employees_detail()
			print('___________________________________')
			print(employees)
			for i in employees:
				if i['email'] == email:
					return i['id']
		return json_response['id']
	except Exception as e:
		print(e)
		return 0


def get_schedules():
	try:
		url = "https://merchant-api.flexbooker.com/schedules"
		payload = {}
		token = get_flexb_auth_code()
		headers = {
		  'Authorization': 'Bearer ' + token
		}
		response = requests.request("GET", url, headers=headers, data=payload)
		json_response = json.loads(response.text)
		return json_response
	except Exception as e:
		print(e)
		return 0


def create_schedule(employee_id, available_days, flexbooker_employee_id):
	try:
		url = "https://merchant-api.flexbooker.com/schedule"
		payload = {}
		payload['employeeId'] = employee_id
		payload['services'] = [
			{
				"serviceId": SERVICE_ID,
				"price": 0
			}
		]
		payload['bufferTimeInMinutes'] = 0
		payload['startDate'] = datetime.today().strftime('%Y-%m-%d')
		payload['endDate'] = ""
		payload['recurs'] = False
		payload['availableDays'] = available_days
		payload['scheduleType'] = 0
		payload['slots'] = 0
		print(payload)
		token = get_flexb_auth_code()
		headers = {
		  'Authorization': 'Bearer ' + token,
		  'Content-Type': 'application/json'
		}
		all_schedules = get_schedules()
		response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
		json_response = json.loads(response.text)
		print(json_response)
		return json_response['id']
	except Exception as e:
		print(e)
		return 0


def update_schedule(employee_id, available_days, schedule_id):
	try:
		url = "https://merchant-api.flexbooker.com/schedule"
		schedule_id = schedule_id
		print(schedule_id)
		payload = {}
		payload['id'] = schedule_id
		payload['employeeId'] = employee_id
		payload['services'] = [
			{
				"serviceId": SERVICE_ID,
				"price": 0
			}
		]
		payload['bufferTimeInMinutes'] = 0
		payload['startDate'] = datetime.today().strftime('%Y-%m-%d')
		payload['endDate'] = ""
		payload['recurs'] = False
		payload['availableDays'] = available_days
		payload['scheduleType'] = 0
		payload['slots'] = 0
		print(payload)
		token = get_flexb_auth_code()
		headers = {
		  'Authorization': 'Bearer ' + token,
		  'Content-Type': 'application/json'
		}
		response = requests.request("PUT", url, headers=headers, data=json.dumps(payload))
		json_response = json.loads(response.text)
		print(json_response)
		return json_response['id']
	except Exception as e:
		print(e)
		return 0


def delete_schedule(schedule_id):
	try:
		url = "https://merchant-api.flexbooker.com/schedule?id=" + str(schedule_id)
		schedule_id = 0
		schedule_id = schedule_id
		print(schedule_id)
		payload = {}
		token = get_flexb_auth_code()
		headers = {
		  'Authorization': 'Bearer ' + token,
		  'Content-Type': 'application/json'
		}
		response = requests.request("DELETE", url, headers=headers, data=json.dumps(payload))
		json_response = json.loads(response.text)
		print(json_response)
		return json_response['id']
	except Exception as e:
		print(e)
		return 0
