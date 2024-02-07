# python imports
import json

# django imports
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template

# django rest framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# models import
from openposition.models import (
	PositionDoc,
    OpenPosition,
	HTMsDeadline,
	HiringGroup
)
from clients.models import (
	Client
)
from dashboard.models import (
	Profile,
	EmailTemplate
)

# serializers imports
from openposition.serializers import OpenPositionSerializer
# utils import
from openposition.utils import get_skillsets_data
from dashboard import tasks

# Open Position View Step 1
class OpenPositionView(APIView):
    def post(self, request):
        response = {}
        try:
            if request.data.get('position_title'):
                pass
            else:
                return Response({'msg': 'Please enter Position name!'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                hiring_group= HiringGroup.objects.get(group_id=request.data.get('hiring_group'))
            except:
                hiring_group = None
            if request.data.get('kickoff_start_date'):
                kickoff_start_date = request.data.get('kickoff_start_date')
            else:
                kickoff_start_date = None
            if request.data.get('sourcing_deadline'):
                sourcing_deadline = request.data.get('sourcing_deadline')
            else:
                sourcing_deadline = None
            if request.data.get('target_deadline'):
                target_deadline = request.data.get('target_deadline')
            else:
                target_deadline = None
            try:
                client_obj = Client.objects.get(id=int(request.data.get('client_id')))
            except:
                return Response({'error': 'Client with id {} not found'.format(request.data.get('client_id'))}, status=status.HTTP_400_BAD_REQUEST)
            if request.data.get('drafted') in ["false", "False", ""]:
                drafted = False
            else:
                drafted = True
            skillsets = get_skillsets_data(request.data)
            position_obj = OpenPosition.objects.create(
                client=client_obj,
                position_title=request.data.get('position_title'),
                reference=request.data.get('reference'),
                special_intruction=request.data.get('special_intruction'),
                hiring_group=None,
                kickoff_start_date=kickoff_start_date,
                sourcing_deadline=sourcing_deadline,
                target_deadline=target_deadline,

                stages=request.data.get('stages', json.dumps([])),

                final_round_completetion_date=request.data.get('final_round_completetion_date'),

                skillsets=skillsets,

                no_of_open_positions=request.data.get('no_of_open_positions'),
                currency=request.data.get('currency'),
                salary_range = request.data.get('salary_range'),
                local_preference = request.data.get('local_preference'),
                other_criteria = request.data.get('other_criteria'),
                drafted=drafted,
                work_auth=request.data.get("work_auth"),
                work_location=request.data.get("work_location"),
            )
            for i in request.FILES:
                file = request.FILES[i]
                PositionDoc.objects.create(openposition=position_obj, file=file)
            # add deadlines
            if not position_obj.drafted or position_obj.drafted == "False":
                for deadline in json.loads(json.loads(request.data.get("htm_deadlines"))):
                    htm_prof = Profile.objects.get(id=int(deadline.get("htm")))
                    position_obj.htms.add(htm_prof)
                    position_obj.save()
                    HTMsDeadline.objects.create(open_position=position_obj, deadline=deadline.get('deadline'), htm=htm_prof, color=deadline.get('color'))
                # send notifications
                try:
                    for admin in User.objects.filter(is_superuser=True):
                        tasks.send_app_notification.delay(admin.username, 'A new position has been created for {} - {}'.format(client_obj.company_name, request.data.get('position_title')))
                        tasks.push_notification.delay([admin.username], 'Qorums Notification', 'A new position has been created for {} - {}'.format(client_obj.company_name, request.data.get('position_title')))
                    tasks.send_app_notification.delay(client_obj.ae_assigned, 'A new position has been created for {} - {}'.format(client_obj.company_name, request.data.get('position_title')))
                    tasks.push_notification.delay([client_obj.ae_assigned], 'Qorums Notification', 'A new position has been created for {} - {}'.format(client_obj.company_name, request.data.get('position_title')))

                    tasks.send_app_notification.delay(client_obj.ca_profile.user.username, 'A new position has been created - ' + position_obj.position_title)
                    tasks.push_notification.delay([client_obj.ca_profile.user.username], 'Qorums Notification', 'A new position has been created - ' + position_obj.position_title)
                    # send notifications to HTMs
                    for profile_obj in position_obj.htms.all():
                        tasks.send_app_notification.delay(profile_obj.user.username, 'You have been assigned as a hiring team member for a new open position, ' + position_obj.position_title)
                        tasks.push_notification.delay([profile_obj.user.username], 'Qorums Notification', 'You have been assigned as a hiring team member for a new open position, ' + position_obj.position_title)
                except Exception as e:
                    response['notification-error'] = str(e)
                # send emails
                for htm_profile in position_obj.htms.all():
                    try:
                        subject = 'New Open Position - Qorums'
                        names = []
                        for i in Profile.objects.filter(roles__contains="is_sm", client=str(position_obj.client)):
                            names.append(i.user.get_full_name())
                            d = {
                                "user_name": htm_profile.user.get_full_name(),
                                "hiring_team_name": hiring_group.name if hiring_group else "",
                                "senior_manager_name": ", ".join(names),
                                "position_title": position_obj.position_title
                            }
                            email_from = settings.EMAIL_HOST_USER
                            recipient_list = [htm_profile.email, ]
                            try:
                                email_template = EmailTemplate.objects.get(client__id=position_obj.client, name="Position Created")
                                template = Template(email_template.content)
                                context = Context(d)
                            except:
                                email_template = EmailTemplate.objects.get(client=None, name="Position Created")
                                template = Template(email_template.content)
                                context = Context(d)
                            html_content = template.render(context)
                            msg = EmailMultiAlternatives(subject, html_content, email_from, recipient_list)
                            msg.attach_alternative(html_content, "text/html")
                            try:
                                msg.send(fail_silently=False)
                            except Exception as e:
                                pass
                    except Exception as e:
                        response['error'] = 'error sending mails ' + str(e)
            response['msg'] = 'added'
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        response = {}
        try:
            op_id = request.data.get("op_id")
            if int(op_id) == int(settings.EXAMPLE_POSITION) and not request.user.is_superuser:
                response['msg'] = 'This position can not be edited'
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
            position_obj = OpenPosition.objects.get(id=op_id)
            # for i in request.FILES:
            #     file = request.FILES[i]
            #     file = request.FILES[i]
            #     PositionDoc.objects.create(openposition=position_obj, file=file)
            if position_obj.client.id != request.data.get('client_id'):
                try:
                    client_obj = Client.objects.get(id=request.data.get('client_id'))
                    position_obj.client = client_obj
                except:
                    pass
            position_obj.position_title = request.data.get('position_title')
            position_obj.reference = request.data.get('reference')
            position_obj.special_intruction = request.data.get('special_intruction')
            current_grp = position_obj.hiring_group.group_id if position_obj.hiring_group else None 
            if current_grp and current_grp == request.data.get('hiring_group'):
                pass
            else:
                try:
                    group_obj = HiringGroup.objects.get(group_id=request.data.get('hiring_group'))
                    position_obj.hiring_group = group_obj
                    position_obj.withdrawed_members.clear() 
                except:
                    pass
            
            position_obj.kickoff_start_date = request.data.get('kickoff_start_date')
            position_obj.sourcing_deadline = request.data.get('sourcing_deadline')
            position_obj.target_deadline = request.data.get('target_deadline')

            position_obj.stages = request.data.get('stages', json.dumps([]))

            position_obj.final_round_completetion_date = request.data.get('final_round_completetion_date')

            position_obj.other_criteria = request.data.get('other_criteria')
            position_obj.skillsets = get_skillsets_data(request.data)
            if request.data.get('drafted') in ['False', "false", False]:
                position_obj.drafted = False
            else:
                position_obj.drafted = True
            position_obj.currency = request.data.get('currency')
            position_obj.salary_range = request.data.get('salary_range')
            position_obj.local_preference = request.data.get('local_preference')
            position_obj.no_of_open_positions = request.data.get('no_of_open_positions')
            position_obj.updated_by = request.user
            position_obj.work_auth = request.data.get("work_auth")
            position_obj.work_location = request.data.get("work_location")
            # add deadlines
            try:
                HTMsDeadline.objects.filter(open_position=position_obj).delete()
                for deadline in json.loads(json.loads(request.data.get("htm_deadlines"))):
                    htm_prof = Profile.objects.get(id=int(deadline.get("htm")))
                    position_obj.htms.add(htm_prof)
                    position_obj.save()
                    if htm_prof not in position_obj.htms.all():
                        position_obj.withdrawed_members.remove(htm_prof)
                    HTMsDeadline.objects.create(open_position=position_obj, deadline=deadline.get('deadline'), htm=htm_prof, color=deadline.get('color'))
            except:
                pass
            position_obj.save()
            response['msg'] = 'edited'
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        try:
            openposition_objs = OpenPosition.objects.all()
            openposition_serializers = OpenPositionSerializer(openposition_objs, many=True)
            data = openposition_serializers.data
            for i in data:
                docs = []
                for j in PositionDoc.objects.filter(openposition__id=i["id"]):
                    docs.append(j.file.url)
                i['documentations'] = docs
            response = {}
            response['data'] = data
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
