#  Python imports
import json

# Django imports 
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum

# DRF imports
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions

# Import models
from dashboard.models import (
	Profile
)
from openposition.models import (
	OpenPosition
)
from clients.models import (
	Client,
	Package,
	ClientPackage,
	StripePayments
)
from candidates.models import (
	Candidate
)

# Serializers import
from clients.serializers import (
	ClientSerializer
)

# Utilities import
from dashboard import tasks

from .utils import (
	create_email_templates,
	update_assigned_clients,
	get_ca_data
)

# APIs
class SignupClientDataView(APIView):

	def post(self, request):
		data = request.data.copy()
		if data.get('logo') == 'null':
			data.pop('logo', None)
		try:
			client_serializer = ClientSerializer(data=data)
			if client_serializer.is_valid():
				client_obj = client_serializer.save()
				key_users_details = False
				try:
					key_username = request.data["key_username"]
					key_password = request.data["key_password"]
					key_users_details = True
				except Exception as e:
					key_users_details = False
				if key_users_details:
					user_obj = User.objects.filter(username__in=[key_username])
					if user_obj:	
						client_obj.delete()
						return Response({'msg': 'Username ' + key_username + ' already exists.'}, status=status.HTTP_400_BAD_REQUEST)
					else:
						pass
					key_user = User.objects.create(username=key_username, first_name=request.data.get("ca_first_name"), last_name=request.data.get('ca_last_name'))
					try:
						key_user.set_password(key_password)
						key_user.save()
						try:
							profile_photo = request.FILES['ca_profile_pic']
						except Exception as e:
							profile_photo = None
						if Profile.objects.filter(email=request.data.get("key_contact_email")).exists() or Candidate.objects.filter(email=request.data.get("key_contact_email")).exists():
							return Response({'message': "Email already exists!"}, status=status.HTTP_400_BAD_REQUEST)
						key_profile = Profile.objects.create(user=key_user, phone_number=request.data.get("key_contact_phone_no"), skype_id=request.data.get("key_contact_skype_id"), job_title=request.data.get('job_title'), email=request.data.get("key_contact_email"), client=client_obj.id, profile_photo=profile_photo, first_log=True, roles=["is_ca"])
						client_obj.ca_profile = key_profile
					except Exception as e:
						key_user.delete()
						client_obj.delete()
						response = {}
						response['msg'] = 'error'
						response['error'] = str(e)
						return Response(response, status=status.HTTP_400_BAD_REQUEST)
					try:
						user_obj = User.objects.get(username=request.data.get('ae_assigned'))
						ae_obj = Profile.objects.get(user=user_obj)
						prev_client_list = json.loads(ae_obj.client)
						if client_obj.id not in prev_client_list:
							prev_client_list.append(client_obj.id)
						ae_obj.client = json.dumps(prev_client_list)
						ae_obj.save()
					except Exception as e:
						print(e)
					response = {}
					response["msg"] = "added"
				else:
					key_user = User.objects.get(username=request.data.get('key_username'))
					key_user.profile.client = client_obj.id
					key_user.save()
					key_user.profile.save()
				client_obj.save()
				# send notification to AM
				try:
					tasks.send_app_notification.delay(client_obj.ae_assigned, 'You have been assigned as the Qorums Support for ' + client_obj.company_name)
					tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'You have been assigned as the Qorums Support for ' + client_obj.company_name)
					for admin in User.objects.filter(is_superuser=True):
						tasks.send_app_notification.delay(admin.username, 'A Qorums Support has been assigned for ' + client_obj.company_name)
						tasks.push_notification.delay([admin.username], 'Qorums Notification', 'A Qorums Support has been assigned for ' + client_obj.company_name)
				except Exception as e:
					response['notitication-error'] = str(e)
				# create email templates
				create_email_templates(client_obj)
				response["client_id"] = client_obj.id
				return Response(response, status=status.HTTP_200_OK)
			else:
				return Response({'msg': str(client_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SingleClientDataView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		data = request.data.copy()
		if data.get('logo') == 'null':
			data.pop('logo', None)
		try:
			client_serializer = ClientSerializer(data=data)
			if client_serializer.is_valid():
				client_obj = client_serializer.save()
				key_users_details = False
				try:
					key_username = request.data["key_username"]
					key_password = request.data["key_password"]
					key_users_details = True
				except Exception as e:
					key_users_details = False
				if key_users_details:
					user_obj = User.objects.filter(username__in=[key_username])
					if user_obj:	
						client_obj.delete()
						return Response({'msg': 'Username ' + key_username + ' already exists.'}, status=status.HTTP_400_BAD_REQUEST)
					else:
						pass
					key_user = User.objects.create(username=key_username, first_name=request.data.get("ca_first_name"), last_name=request.data.get('ca_last_name'))
					try:
						key_user.set_password(key_password)
						key_user.save()
						try:
							profile_photo = request.FILES['ca_profile_pic']
						except Exception as e:
							profile_photo = None
						if Profile.objects.filter(email=request.data.get("key_contact_email")).exists() or Candidate.objects.filter(email=request.data.get("key_contact_email")).exists():
							return Response({'message': "Email already exists!"}, status=status.HTTP_400_BAD_REQUEST)
						key_profile = Profile.objects.create(user=key_user, phone_number=request.data.get("key_contact_phone_no"), skype_id=request.data.get("key_contact_skype_id"), job_title=request.data.get('job_title'), email=request.data.get("key_contact_email"), client=client_obj.id, profile_photo=profile_photo, first_log=True, roles=["is_ca"])
						client_obj.ca_profile = key_profile
					except Exception as e:
						key_user.delete()
						client_obj.delete()
						response = {}
						response['msg'] = 'error'
						response['error'] = str(e)
						return Response(response, status=status.HTTP_400_BAD_REQUEST)
					try:
						user_obj = User.objects.get(username=request.data.get('ae_assigned'))
						ae_obj = Profile.objects.get(user=user_obj)
						prev_client_list = json.loads(ae_obj.client)
						if client_obj.id not in prev_client_list:
							prev_client_list.append(client_obj.id)
						ae_obj.client = json.dumps(prev_client_list)
						ae_obj.save()
					except Exception as e:
						print(e)
					response = {}
					response["msg"] = "added"
				else:
					key_user = User.objects.get(username=request.data.get('key_username'))
					key_user.profile.client = client_obj.id
					key_user.save()
					key_user.profile.save()
				client_obj.save()
				# update the client if logged user is CA
				if "is_ca" in request.user.profile.roles:
					request.user.profile.client = client_obj.id
					request.user.profile.save()
				# create package
				package_id = int(request.data.get("package"))
				client_package = ClientPackage.objects.create(client=client_obj)
				if package_id != 0:
					package_obj = Package.objects.get(id=package_id)
					client_package.package = package_obj
					client_package.save()
				elif package_id == 0:
					client_package.is_trial = True
					client_package.trial_expired = request.data.get("trial_expired")
					client_package.save()
				# send notification to AM
				try:
					tasks.send_app_notification.delay(client_obj.ae_assigned, 'You have been assigned as the Qorums Support for ' + client_obj.company_name)
					tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'You have been assigned as the Qorums Support for ' + client_obj.company_name)
					for admin in User.objects.filter(is_superuser=True):
						tasks.send_app_notification.delay(admin.username, 'A Qorums Support has been assigned for ' + client_obj.company_name)
						tasks.push_notification.delay([admin.username], 'Qorums Notification', 'A Qorums Support has been assigned for ' + client_obj.company_name)
				except Exception as e:
					response['notitication-error'] = str(e)
				# create email templates
				create_email_templates(client_obj)
				return Response(response, status=status.HTTP_200_OK)
			else:
				return Response({'msg': str(client_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request):
		try:
			client_id = int(request.query_params.get('id'))
			client_obj = Client.objects.get(id=client_id)
			client_serializer = ClientSerializer(client_obj)
			response = {}

			response["client"] = client_serializer.data
			ca_data = get_ca_data(client_obj.ca_profile, response["client"])
			response["client"].update(ca_data)
			try:
				ca_user = User.objects.get(username=client_obj.key_username)
				response['client']['ca_profile_pic'] = ca_user.profile.profile_photo
			except:
				response['client']['ca_profile_pic'] = None
			try:
				package_obj = ClientPackage.objects.get(client=client_obj)
				if package_obj.is_trial:
					response["client"]["package_name"] = "Trial"
					response["client"]["package"] = 0
				else:	
					response["client"]["package_name"] = package_obj.package.name
					response["client"]["package"] = package_obj.package.id
			except:
				response["client"]["package_name"] = None
				response["client"]["package"] = None
			response['msg'] = 'fetched'
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def put(self, request):
		try:
			response = {}
			client_id = request.data.get("id")
			client_obj = Client.objects.get(id=client_id)
			client_obj.company_name = request.data.get('company_name', client_obj.company_name)
			client_obj.company_contact_full_name = request.data.get('company_contact_full_name', client_obj.company_contact_full_name)
			client_obj.company_contact_phone = request.data.get('company_contact_phone', client_obj.company_contact_phone)
			client_obj.company_contact_email = request.data.get('company_contact_email', client_obj.company_contact_email)
			
			if isinstance(request.data.get("logo"), str):
				if request.data.get("logo") == "null":
					client_obj.logo = None
				else:
					pass
			else:
				client_obj.logo = request.data.get('logo')
			key_profile_obj = client_obj.ca_profile
			key_profile_obj.user.first_name = request.data.get('ca_first_name', key_profile_obj.user.first_name)
			key_profile_obj.user.last_name = request.data.get('ca_last_name', key_profile_obj.user.last_name)
			key_profile_obj.user.save()
			key_profile_obj.phone_number = request.data.get('key_contact_phone_no', key_profile_obj.phone_number)
			key_profile_obj.skype_id = request.data.get('key_contact_skype_id', key_profile_obj.skype_id)
			key_profile_obj.job_title = request.data.get('job_title', key_profile_obj.job_title)
			if request.data.get('key_contact_email') and key_profile_obj.email != request.data.get('key_contact_email'):
				if Profile.objects.filter(email=request.data.get("key_contact_email")).exists() or Candidate.objects.filter(email=request.data.get("key_contact_email")).exists():
					return Response({'message': "Email already exists!"}, status=status.HTTP_400_BAD_REQUEST)
			key_profile_obj.email = request.data.get('key_contact_email', key_profile_obj.email)
			try:
				profile_photo = request.FILES['ca_profile_pic']
				key_profile_obj.profile_photo = profile_photo
			except Exception as e:
				print(e)
			
			client_obj.hr_first_name = request.data.get('hr_first_name', client_obj.hr_first_name)
			client_obj.hr_last_name = request.data.get('hr_last_name', client_obj.hr_last_name)
			client_obj.hr_contact_phone_no = request.data.get('hr_contact_phone_no', client_obj.hr_contact_phone_no)
			client_obj.hr_contact_skype_id = request.data.get('hr_contact_skype_id', client_obj.hr_contact_skype_id)
			client_obj.hr_contact_email = request.data.get('hr_contact_email', client_obj.hr_contact_email)
			client_obj.special_req = request.data.get('special_req', client_obj.special_req)
			# check if new ae is assigned.
			if request.data.get('ae_assigned') == None or client_obj.ae_assigned == request.data.get('ae_assigned'):
				pass
			else:
				try:
					old_user_obj = User.objects.get(username=client_obj.ae_assigned)
					old_ae_obj = Profile.objects.get(user=old_user_obj)
					prev_client_list = json.loads(old_ae_obj.client)
					if client_obj.id not in prev_client_list:
						pass
					else:
						prev_client_list.remove(client_obj.id)
					old_ae_obj.client = json.dumps(prev_client_list)
					old_ae_obj.save()
				except Exception as e:
					pass
				try:
					user_obj = User.objects.get(username=request.data.get('ae_assigned'))
					ae_obj = Profile.objects.get(user=user_obj)
					prev_client_list = json.loads(ae_obj.client)
					if client_obj.id not in prev_client_list:
						prev_client_list.append(client_obj.id)
					ae_obj.client = json.dumps(prev_client_list)
					ae_obj.save()
				except Exception as e:
					pass
				client_obj.ae_assigned = request.data.get('ae_assigned')
				# send notification to SM
				try:
					tasks.send_app_notification.delay(client_obj.ae_assigned, 'You have been assigned as the Qorums Support for ' + client_obj.company_name)
					tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'You have been assigned as the Qorums Support for ' + client_obj.company_name)
					for admin in User.objects.filter(is_superuser=True):
						tasks.send_app_notification.delay(admin.username, 'A Qorums Support has been assigned for ' + client_obj.company_name)
						tasks.push_notification.delay([admin.username], 'Qorums Notification', 'A Qorums Support has been assigned for ' + client_obj.company_name)
				except Exception as e:
					response['notification-error'] = str(e)
			client_obj.save()
			response['msg'] = 'updated'
			client_obj.save()
			# update the remaining fields
			temp_data = {}
			temp_data['cto_first_name'] = request.data.get('cto_first_name', client_obj.cto_first_name)
			temp_data['cto_last_name'] = request.data.get('cto_last_name', client_obj.cto_last_name)
			temp_data['cto_phone_no'] = request.data.get('cto_phone_no', client_obj.cto_phone_no)
			temp_data['cto_skype_id'] = request.data.get('cto_skype_id', client_obj.cto_skype_id)
			temp_data['cto_email'] = request.data.get('cto_email', client_obj.cto_email)

			temp_data['billing_first_name'] = request.data.get('billing_first_name', client_obj.billing_first_name)
			temp_data['billing_last_name'] = request.data.get('billing_last_name', client_obj.billing_last_name)
			temp_data['billing_phone_no'] = request.data.get('billing_phone_no', client_obj.billing_phone_no)
			temp_data['billing_email'] = request.data.get('billing_email', client_obj.billing_email)

			temp_data['billing_addr_line_1'] = request.data.get('billing_addr_line_1', client_obj.billing_addr_line_1)
			temp_data['billing_addr_line_2'] = request.data.get('billing_addr_line_2', client_obj.billing_addr_line_2)
			temp_data['billing_city'] = request.data.get('billing_city', client_obj.billing_city)
			temp_data['billing_state'] = request.data.get('billing_state', client_obj.billing_state)
			temp_data['billing_pincode'] = request.data.get('billing_pincode', client_obj.billing_pincode)

			temp_data['addr_line_1'] = request.data.get('addr_line_1', client_obj.addr_line_1)
			temp_data['addr_line_2'] = request.data.get('addr_line_2', client_obj.addr_line_2)
			temp_data['city'] = request.data.get('city', client_obj.city)
			temp_data['state'] = request.data.get('state', client_obj.state)
			temp_data['pincode'] = request.data.get('pincode', client_obj.pincode)

			temp_data['company_contact_full_name'] = request.data.get('company_contact_full_name', client_obj.company_contact_full_name)
			temp_data['company_contact_phone'] = request.data.get('company_contact_phone', client_obj.billing_last_name)
			temp_data['company_contact_email'] = request.data.get('company_contact_email', client_obj.billing_phone_no)
			client_serializer = ClientSerializer(client_obj, data=temp_data, partial=True)
			if client_serializer.is_valid():
				client_serializer.save()
			key_profile_obj.save()
			# create package
			package_id = int(request.data.get("package"))
			client_package, created = ClientPackage.objects.get_or_create(client=client_obj)
			if package_id == 0:
				client_package.is_trial = True
				client_package.trial_expired = request.data.get("trial_expired", client_package.trial_expired)
				client_package.save()
			elif package_id is not None:
				package_obj = Package.objects.get(id=package_id)
				client_package.package = package_obj
				client_package.is_trial = False
				client_package.trial_expired = None
				client_package.save()
			
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request):
		try:
			client_id = int(request.query_params.get('id'))
			client_obj = Client.objects.get(id=client_id)
			client_obj.delete()
			hiring_group_objs = HiringGroup.objects.filter(client_id=client_id)
			for i in hiring_group_objs:
				i.delete()
			hiring_member_objs = Profile.objects.filter(client=client_obj.id, is_he=True)
			for i in hiring_member_objs:
				try:
					user_obj = User.objects.get(username=i.user.username)
					user_obj.delete()
				except:
					pass

			p_error = None
			for i in Profile.objects.all():
				if i.client == str(client_obj.id):
					i.user.delete()
				else:
					try:
						p_c = json.loads(i.client)
						n_p_c = []
						for j in p_c:
							if j == client_obj.id:
								pass
							else:
								n_p_c.append(j)
						i.client = json.dumps(n_p_c)
						i.save()
					except Exception as e:
						p_error = e
						print(e)
			try:
				User.objects.get(username=client_obj.key_username).delete()
			except Exception as e:
				key_user = 0
			try:
				User.objects.get(username=client_obj.hr_username).delete()
			except Exception as e:
				hr_user = 0
			update_assigned_clients()
			response = {}
			response["msg"] = "deleted"
			response["p_error"] = str(p_error)
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetAllClientsData(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request):
		try:
			response = {}
			user = request.user
			if "is_ae" in user.profile.roles:
				clients_objs = Client.objects.filter(id__in=json.loads(user.profile.client)).order_by('-updated_at')
			elif user.is_superuser:
				clients_objs = Client.objects.filter(disabled=False).order_by('-updated_at')
			else:
				try:
					clients_objs = Client.objects.filter(id=int(user.profile.client)).order_by('-updated_at')
				except:
					return Response({}, status=status.HTTP_200_OK)
			client_data = []
			for client in clients_objs:
				temp_client = {}
				temp_client["id"] = client.id
				temp_client["company_name"] = client.company_name
				temp_client["client_admin"] = client.ca_profile.user.get_full_name()
				# get subscription name
				try:
					temp_client["subscription"] = ClientPackage.objects.get(client=client).package.name
				except:
					temp_client["subscription"] = None
				temp_client["payment"] = StripePayments.objects.filter(client=client).aggregate(Sum('amount')).get("amount__sum")
				temp_client["no_of_clients"] = Candidate.objects.filter(created_by_client=client.id).count()
				temp_client["interviews_conducted"] = 0
				client_data.append(temp_client)
			response["clients"] = client_data
			response["active"] = 0
			response["inactive"] = 0
			response["hold"] = 0
			response["trial"] = ClientPackage.objects.filter(package=None).distinct("client").count()
			response["starter"] = ClientPackage.objects.filter(package__name="Starter").distinct("client").count()
			response["growth"] = ClientPackage.objects.filter(package__name="Growth").distinct("client").count()
			response["enterprise"] = ClientPackage.objects.filter(package__name="Enterprise").distinct("client").count()
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
		

