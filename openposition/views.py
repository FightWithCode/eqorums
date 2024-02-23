# python imports
import json
from datetime import timedelta, datetime

# django imports
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template

# django rest framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions

# models import
from openposition.models import (
	PositionDoc,
    OpenPosition,
	HTMsDeadline,
	Interview,
	CandidateMarks,
	CandidateAssociateData,
	Hired,
	Offered,
	HTMWeightage,
	CandidateStatus
)
from clients.models import (
	Client
)
from dashboard.models import (
	Profile,
	EmailTemplate,
	HTMAvailability,
	EvaluationComment
)
from candidates.models import (
	Candidate
)
from hiringgroup.models import (
	HiringGroup
)

# serializers imports
from openposition.serializers import OpenPositionSerializer
from candidates.serializers import CandidateSerializer

# utils import
from candidates.utils import get_candidate_profile, get_holds_no, get_offer_no, get_pass_no
from openposition.utils import get_htm_specific_data
from openposition.utils import get_skillsets_data, get_htm_flag_data
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
            if request.data.get('drafted') in ["false", "False", "", None]:
                drafted = False
            else:
                drafted = True
            
            position_obj = OpenPosition.objects.create(
                client=client_obj,
                position_title=request.data.get('position_title'),
                special_intruction=request.data.get('special_intruction'),
                hiring_group=None,
                kickoff_start_date=kickoff_start_date,
                sourcing_deadline=sourcing_deadline,
                target_deadline=target_deadline,

                stages=[],

                final_round_completetion_date=request.data.get('final_round_completetion_date'),

                skillsets=json.loads(request.data.get("skillsets")),
    			nskillsets=json.loads(request.data.get("skillsets")),

                no_of_open_positions=request.data.get('no_of_open_positions'),
                currency=request.data.get('currency'),
                salary_range = request.data.get('salary_range'),
                candidate_location = request.data.get('candidate_location'),
                drafted=drafted,
                work_auth=request.data.get("work_auth"),
                work_location=request.data.get("work_location"),
            )
            for i in request.FILES:
                file = request.FILES[i]
                PositionDoc.objects.create(openposition=position_obj, file=file)
            # add deadlines
            if not position_obj.drafted or position_obj.drafted == "False":
                for deadline in json.loads(request.data.get("htm_deadlines", "[]")):
                    htm_prof = Profile.objects.get(id=int(deadline.get("htm")))
                    position_obj.htms.add(htm_prof)
                    position_obj.save()
                    HTMsDeadline.objects.create(open_position=position_obj, deadline=deadline.get('deadline'), htm=htm_prof, skillset_weightage=deadline.get("weightages"))
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
            return Response({'msg': str(e), "req": request.data}, status=status.HTTP_400_BAD_REQUEST)
    
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
            position_obj.position_type = request.data.get('position_type', position_obj.position_type)
            position_obj.special_intruction = request.data.get('special_intruction')
            current_grp = position_obj.hiring_group.group_id if position_obj.hiring_group else None 
            position_obj.kickoff_start_date = request.data.get('kickoff_start_date')
            position_obj.sourcing_deadline = request.data.get('sourcing_deadline')
            position_obj.target_deadline = request.data.get('target_deadline')

            position_obj.stages = request.data.get('stages', json.dumps([]))

            position_obj.final_round_completetion_date = request.data.get('final_round_completetion_date')

            position_obj.skillsets = json.loads(request.data.get("skillsets"))
            position_obj.nskillsets = json.loads(request.data.get("skillsets"))
            if request.data.get('drafted') in ['False', "false", False, None, ""]:
                position_obj.drafted = False
            else:
                position_obj.drafted = True
            position_obj.currency = request.data.get('currency')
            position_obj.salary_range = request.data.get('salary_range')
            position_obj.candidate_location = request.data.get('candidate_location')
            position_obj.no_of_open_positions = request.data.get('no_of_open_positions')
            position_obj.updated_by = request.user
            position_obj.work_auth = request.data.get("work_auth")
            position_obj.work_location = request.data.get("work_location")
            # add deadlines
            try:
                HTMsDeadline.objects.filter(open_position=position_obj).delete()
                for deadline in json.loads(request.data.get("htm_deadlines", "[]")):
                    htm_prof = Profile.objects.get(id=int(deadline.get("htm")))
                    position_obj.htms.add(htm_prof)
                    position_obj.save()
                    if htm_prof not in position_obj.htms.all():
                        position_obj.withdrawed_members.remove(htm_prof)
                    HTMsDeadline.objects.create(open_position=position_obj, deadline=deadline.get('deadline'), htm=htm_prof, skillset_weightage=deadline.get("weightages"))
            except Exception as e:
                print(e)
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
                # for skillset in i["skillsets"]:
                #     for skill in skillset:
                #         i[skill] = skillset[skill]
                # del i["skillsets"]
            response = {}
            response['data'] = data
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetPositionSummary(APIView):

	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		response = {}
		try:
			open_position = OpenPosition.objects.get(id=op_id)
			dates = {}
			start = open_position.kickoff_start_date
			htm_deadlines = []
			hiring_group = None
			try:
				hiring_group = HiringGroup.objects.get(group_id=open_position.hiring_group)
				members_list = list(hiring_group.members_list.all())
				if hiring_group.hr_profile in members_list:
					members_list.remove(hiring_group.hr_profile)
			except Exception as e:
				members_list = []
			for deadline in HTMsDeadline.objects.filter(open_position=open_position):
				temp_dict = {}
				temp_dict["deadline"] = deadline.deadline.strftime("%Y-%m-%d")
				temp_dict["htm"] = deadline.htm.id
				temp_dict["htm_name"] = deadline.htm.user.get_full_name()
				try:
					temp_dict["color"] = [d["color"] for d in hiring_group.members_color if d['htm'] == deadline.htm.id][0]
				except Exception as e:
					temp_dict["color"] = None
				temp_dict["profile_pic"] = deadline.htm.profile_photo.url if str(deadline.htm.profile_photo) not in ["", "None", "null"] else None 				
				htm_deadlines.append(temp_dict)
			
			if start and open_position.target_deadline:
				while start <= open_position.target_deadline:
					if start.weekday() in [5, 6]:
						bg_color = "#b5b5b5"
					else:
						bg_color = "#5cba83"
					if start == open_position.kickoff_start_date:
						stage = "kickoff"
					elif start == open_position.sourcing_deadline:
						stage = "sourcing"
					elif start == open_position.target_deadline:
						stage = "target"
					else:
						stage = None
					cur_date = start
					interview = []
					# given_interviews = CandidateMarks.objects.filter(op_id=op_id, feedback_date__year=cur_date.year, feedback_date__month=cur_date.month,feedback_date__day=cur_date.day)
					given_interviews = Interview.objects.filter(op_id__id=op_id, interview_date_time__year=cur_date.year, interview_date_time__month=cur_date.month,interview_date_time__day=cur_date.day)
					for inter in given_interviews:
						temp_dict = {}
						htms = []
						for htm in inter.htm.all():
							htms.append(htm.user.get_full_name())
						temp_dict["htmName"] = ", ".join(htms)
						# temp_dict["htmId"] = inter.marks_given_by
						color = []
						# if hiring_group:
						# 	color = [d["color"] for d in hiring_group.members_color if d['htm'] == inter.marks_given_by]
						# if color:
						# 	temp_dict["htmColorCode"] = color[0]
						# else:
						# 	temp_dict["htmColorCode"] = None
						temp_dict["candidateId"] = inter.candidate.candidate_id
						temp_dict["time"] = inter.interview_date_time.strftime("%I:%M %p")
						try:
							candidate_obj = Candidate.objects.get(candidate_id=inter.candidate.candidate_id)
							temp_dict["candidateProfilePic"] = candidate_obj.profile_photo
							temp_dict["candidateName"] = "{} {}".format(candidate_obj.name, candidate_obj.last_name) 
						except:
							temp_dict["candidateName"] = None
							temp_dict["candidateProfilePic"] = None
						if "is_htm" in request.user.profile.roles and request.user.profile not in [hiring_group.hod_profile, hiring_group.hr_profile]:
							if request.user.profile.id in inter.htm.all().values_list('id', flat=True):
								interview.append(temp_dict)
						else:
							interview.append(temp_dict)
					if interview:
						bg_color = "#000000"
					deadlines = []
					for d in htm_deadlines:
						if d['deadline'] == start.strftime("%Y-%m-%d"):
							if "is_htm" in request.user.profile.roles and request.user.profile not in [hiring_group.hod_profile, hiring_group.hr_profile]:
								if request.user.profile.id == d["htm"]:
									temp_dict = {"htmId": d["htm"], "htmProfPic": d["profile_pic"], "htmColorCode": d["color"]}
									deadlines.append(temp_dict)
							else:
								temp_dict = {"htmId": d["htm"], "htmProfPic": d["profile_pic"], "htmColorCode": d["color"]}
								deadlines.append(temp_dict)
					temp_dict = {
						"background": bg_color,
						"stage": stage,
						"additional": {},
						"deadlines": deadlines,
						"interviews_list": interview,
						"date": start.strftime("%m/%d/%Y")
					}
					dates[start.strftime("%m/%d")] = temp_dict
					start = start + timedelta(days=1)
			response["dates"] = dates
			htms_detail = []
			for j in members_list:
				try:
					profile = j
					color = []
					if hiring_group:
						color = [d["color"] for d in hiring_group.members_color if d['htm'] == profile.id]
					member_dict = {}
					member_dict['id'] = profile.id
					member_dict['job_title'] = profile.job_title
					member_dict['name'] = profile.user.first_name + ' ' + profile.user.last_name
					member_dict['profile_pic'] = profile.profile_photo
					if profile==hiring_group.hod_profile:
						member_dict['isHod'] = True
						member_dict['role'] = "Hiring Manager"
					else:
						member_dict['isHod'] = False
					if profile == hiring_group.hr_profile:
						member_dict['isHr'] = True
						member_dict['role'] = "Team Cordinator"
					else:
						member_dict['isHr'] = False
					if color:
						member_dict['color'] = color[0]
					if member_dict.get('role') == None:
						member_dict['role'] = "Hiring Team Memeber"
					htms_detail.append(member_dict)
				except Exception as e:
					print(e)
					pass
			response["htm_deadlines"] = htm_deadlines
			response["htms"] = htms_detail
			if hiring_group:
				response["team_name"] = hiring_group.name
			else:
				response["team_name"] = None
			response["position_status"] = "open"
			if open_position.drafted:
				response["position_status"] = "draft"
			if open_position.trashed:
				response["position_status"] = "trashed"
			if open_position.archieved:
				response["position_status"] = "archieved"
			if open_position.filled:
				response["position_status"] = "completed"
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AllCandidateFeedback(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			open_position_obj = OpenPosition.objects.get(id=op_id)
			cao_objs = []
			data = []
			logged_user = request.user
			logged_user_profile = Profile.objects.get(user=logged_user)
			for cao in CandidateAssociateData.objects.filter(open_position=open_position_obj).distinct("candidate"):
				temp_can = {}
				temp_can["candidate_id"] = cao.candidate.candidate_id
				temp_can["profile_photo"] = get_candidate_profile(cao.candidate)
				temp_can["name"] = cao.candidate.user.get_full_name()
				temp_can["first_name"] = cao.candidate.user.first_name
				temp_can["last_name"] = cao.candidate.user.last_name
				temp_can["offer_no"] = get_offer_no(cao.candidate)
				temp_can["pass_no"] = get_pass_no(cao.candidate)
				temp_can["like_count"] = 0
				temp_can["pass_count"] = 0
				temp_can['golden_glove_count'] = 0
				try:
					hire_obj = Hired.objects.get(candidate_id=cao.candidate.candidate_id, op_id=op_id)
					temp_can['hired'] = True
				except:
					temp_can['hired'] = False
				# Getting Offered or not
				try:
					hire_obj = Offered.objects.get(candidate_id=cao.candidate.candidate_id, op_id=op_id)
					temp_can['offered'] = True
				except:
					temp_can['offered'] = False
				temp_can['op_id'] = op_id
				temp_can['withdrawed'] = cao.withdrawed if cao.withdrawed else False
				temp_can["requested"] = False if cao.accepted else True
				temp_can['client_id'] = open_position_obj.client.id
				if "is_htm" in logged_user_profile.roles:
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=logged_user_profile.id)
					given_by = candidate_marks_obj.marks_given_by
					try:
						htm_weightage_obj = HTMsDeadline.objects.get(open_position=open_position_obj, htm__id=given_by)
						htm_weightage = htm_weightage_obj.skillset_weightage
					except HTMsDeadline.DoesNotExist:
						htm_weightage = []
						for idx in range(0, len(open_position_obj.nskillsets)):
							htm_weightage.append({"skillset_weightage": 10})
					except Exception as e:
						print("some error occured while totaling weightages", str(e))
						# remove this later
						htm_weightage = []
						for idx in range(0, len(open_position_obj.nskillsets)):
							htm_weightage.append({"skillset_weightage": 10})
					if candidate_marks_obj:
						temp_can["marks"] = candidate_marks_obj[0]
					# continue this later
				else:
					# data for the CA, SMs and SA
					candidate_schedule_list = []
					for interview in Interview.objects.filter(candidate=cao.candidate, op_id__id=op_id).filter(disabled=False):
						try:
							temp_dict = {}
							interviewers_names = interview.htm.all().values_list("user__first_name", flat=True)
							temp_dict['interviewer_name'] = ", ".join(interviewers_names)
							temp_dict['time'] = interview.interview_date_time.strftime("%m/%d/%Y, %H:%M:%S")
							candidate_schedule_list.append(temp_dict)
						except:
							continue
					temp_can['candidate_schedule'] = candidate_schedule_list
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=cao.candidate_id, op_id=op_id)
					"""
					uncomment from here if avg marks is needed
					# for calculation avg marks
					avg_marks = []
					total_weightages = []
					for skill in open_position_obj.nskillsets:
						temp_avg_skillset = {}
						temp_avg_skillset["skillset_name"] = skill["skillset_name"]
						temp_avg_skillset["skillset_marks"] = 0
						avg_marks.append(temp_avg_skillset)

						temp_total_weightages = {}
						temp_total_weightages["skillset_name"] = skill["skillset_name"]
						temp_total_weightages["skillset_weightage"] = 0
						total_weightages.append(temp_total_weightages)
					# calculates total weightage of htms
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						try:
							# remove this
							raise ValueError("This is awesome!!")
							htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
							weightage_count = 1
							for idx in range(0, len(position_obj.nskillsets)):
								total_weightages[idx]["skillset_weightage"] += htm_weightage_obj.weightages[idx]["skillset_weightage"]
						except HTMWeightage.DoesNotExist:
							for idx in range(0, len(open_position_obj.nskillsets)):
								total_weightages[idx]["skillset_weightage"] += 10
						except Exception as e:
							print("some error occured while totaling weightages", str(e))
							# remove this later
							for idx in range(0, len(open_position_obj.nskillsets)):
								total_weightages[idx]["skillset_weightage"] += 10
					# part of avg marks calculation algo
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						# for calculating avg marks
						try:
							htm_weightage_obj = HTMsDeadline.objects.get(open_position=open_position_obj, htm__id=given_by)
							htm_weightage = htm_weightage_obj.skillset_weightage
						except HTMsDeadline.DoesNotExist:
							htm_weightage = []
							for idx in range(0, len(open_position_obj.nskillsets)):
								htm_weightage.append({"skillset_weightage": 10})
						except Exception as e:
							print("some error occured while totaling weightages", str(e))
							# remove this later
							htm_weightage = []
							for idx in range(0, len(open_position_obj.nskillsets)):
								htm_weightage.append({"skillset_weightage": 10})
						for count in range(0, len(open_position_obj.nskillsets)):
							avg_marks[count]["skillset_marks"] += c_obj.nmarks[count]["skillset_marks"] * htm_weightage[count]["skillset_weightage"]
					# Calculate avg marks
					if candidate_marks_obj:
						overall_avg_marks = 0
						total_position_weightage = 0
						for idx in range(0, len(open_position_obj.nskillsets)):
							avg_marks[idx]["skillset_marks"] = round(avg_marks[idx]["skillset_marks"] / total_weightages[idx]["skillset_weightage"], 1)
							overall_avg_marks += avg_marks[idx]["skillset_marks"] * open_position_obj.nskillsets[idx]["skillset_weightage"]
							total_position_weightage += open_position_obj.nskillsets[idx]["skillset_weightage"]
							print(overall_avg_marks, total_position_weightage)
						if total_position_weightage:
							temp_can['avg_marks'] = round(overall_avg_marks / total_position_weightage, 1)
						else:
							temp_can['avg_marks'] = 0.0
					else:
						temp_can['avg_marks'] = 0.0
					"""
					temp_can['total_hiring_members'] = open_position_obj.htms.all().count()
					temp_can['interviews_done'] = candidate_marks_obj.count()
					if candidate_marks_obj:
						temp_can['marks_given_by'] = candidate_marks_obj.count()
						temp_can['flag_by_hiring_manager'] = []
						for hm in open_position_obj.htms.all():
							flag_data = get_htm_flag_data(hm, op_id, cao.candidate.candidate_id)
							temp_can['flag_by_hiring_manager'].append(flag_data)
					else:
						temp_can['marks_given_by'] = 0
						temp_can['flag_by_hiring_manager'] = []
						for hm in open_position_obj.htms.all():
							flag_data = get_htm_flag_data(hm, op_id, cao.candidate.candidate_id)
							temp_can['flag_by_hiring_manager'].append(flag_data)
					data.append(temp_can)	
			# for i in data:
			# 	caobj = CandidateAssociateData.objects.get(open_position=open_position_obj, candidate__candidate_id=i["candidate_id"])
			# 	# Additin Profile Picture
				
				
			# 	if "is_htm" in logged_user_profile.roles:
			# 		# Sending data as a HTM perspective
			# 		candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id, marks_given_by=logged_user_profile.id)
			# 		given_by = logged_user_profile.id
			# 		# Get weighage of the HTM if not found then assign 10 by default - Not being used
					
			# 		if candidate_marks_obj:
			# 			avg_marks = 0
			# 			count = 0
			# 			# Algorith to calculate marks based on HTM Weightage and Skills Weightage
			# 			if candidate_marks_obj[0].criteria_1_marks not in [None]: 
			# 				count = count + 1
			# 				avg_marks = avg_marks + candidate_marks_obj[0].criteria_1_marks * open_position_obj.init_qualify_ques_weightage_1
			# 			if candidate_marks_obj[0].criteria_2_marks not in [None]:
			# 				count = count + 1
			# 				avg_marks = avg_marks + candidate_marks_obj[0].criteria_2_marks* open_position_obj.init_qualify_ques_weightage_2
			# 			if candidate_marks_obj[0].criteria_3_marks not in [None]:
			# 				count = count + 1
			# 				avg_marks = avg_marks + candidate_marks_obj[0].criteria_3_marks* open_position_obj.init_qualify_ques_weightage_3
			# 			if candidate_marks_obj[0].criteria_4_marks not in [None]:
			# 				count = count + 1
			# 				avg_marks = avg_marks + candidate_marks_obj[0].criteria_4_marks* open_position_obj.init_qualify_ques_weightage_4
			# 			if candidate_marks_obj[0].criteria_5_marks not in [None]:
			# 				count = count + 1
			# 				avg_marks = avg_marks + candidate_marks_obj[0].criteria_5_marks * open_position_obj.init_qualify_ques_weightage_5
			# 			if candidate_marks_obj[0].criteria_6_marks not in [None]:
			# 				count = count + 1
			# 				avg_marks = avg_marks + candidate_marks_obj[0].criteria_6_marks * open_position_obj.init_qualify_ques_weightage_6
			# 			if candidate_marks_obj[0].criteria_7_marks not in [ None]:
			# 				count = count + 1
			# 				avg_marks = avg_marks + candidate_marks_obj[0].criteria_7_marks * open_position_obj.init_qualify_ques_weightage_7
			# 			if candidate_marks_obj[0].criteria_8_marks not in [None]:
			# 				count = count + 1
			# 				avg_marks = avg_marks + candidate_marks_obj[0].criteria_8_marks * open_position_obj.init_qualify_ques_weightage_8
			# 			i['avg_marks'] = round(avg_marks / count, 1)
			# 			i['total_hiring_members'] = open_position_obj.htms.all().count()
			# 			all_marks_candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=i['candidate_id'], op_id=op_id)
			# 			i['final_avg_marks'] = i['avg_marks']  # (all_marks_candidate_marks_obj.aggregate(Avg('criteria_1_marks'))['criteria_1_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_2_marks'))['criteria_2_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_3_marks'))['criteria_3_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_4_marks'))['criteria_4_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_5_marks'))['criteria_5_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_6_marks'))['criteria_6_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_7_marks'))['criteria_7_marks__avg'] + all_marks_candidate_marks_obj.aggregate(Avg('criteria_8_marks'))['criteria_8_marks__avg']) / 8
			# 			i['marks_given_by'] = all_marks_candidate_marks_obj.count()
			# 			if candidate_marks_obj[0].thumbs_up:
			# 				i['he_flag'] = 'Thumbs Up'
			# 				i['flag'] = 'Thumbs Up'
			# 			if candidate_marks_obj[0].thumbs_down:
			# 				i['he_flag'] = 'Thumbs Down'
			# 				i['flag'] = 'Thumbs Down'
			# 			if candidate_marks_obj[0].hold:
			# 				i['he_flag'] = 'Hold'
			# 				i['flag'] = 'Hold'
			# 			if candidate_marks_obj[0].golden_gloves:
			# 				i['he_flag'] = 'Golden Glove'
			# 				i['flag'] = 'Golden Glove'
			# 			i['flag_by_hiring_manager'] = []
			# 			temp_dict = {}
			# 			temp_dict['id'] = int(logged_user_profile.id)
			# 			candidate_marks_obj = candidate_marks_obj[0]
			# 			if candidate_marks_obj.thumbs_up:
			# 				temp_dict['flag'] = 'Thumbs Up'
			# 			if candidate_marks_obj.thumbs_down:
			# 				temp_dict['flag'] = 'Thumbs Down'
			# 			if candidate_marks_obj.hold:
			# 				temp_dict['flag'] = 'Hold'
			# 			if candidate_marks_obj.golden_gloves:
			# 				temp_dict['flag'] = 'Golden Glove'
			# 			# get other htm specific data
			# 			try:
			# 				interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[logged_user_profile], candidate__candidate_id=i['candidate_id'])[0]
			# 				# call the function and pass interview_obj and logged_user_profile
			# 				extra_data = get_htm_specific_data(interview_obj, logged_user_profile)
			# 				temp_dict.update(extra_data)
			# 			except:
			# 				pass
			# 			temp_dict["marks"] = i['final_avg_marks']
			# 			i['flag_by_hiring_manager'].append(temp_dict)
			# 		else:
			# 			i['marks'] = {}
			# 			i['final_avg_marks'] = 0
			# 			i['total_hiring_members'] = open_position_obj.htms.all().count()
			# 			i['marks_given_by'] = 0
			# 			i['flag'] = 'Not Given'
			# 			i['flag_by_hiring_manager'] = []
			# 			temp_dict = {}
			# 			temp_dict['id'] = int(logged_user_profile.id)
			# 			try:
			# 				interview_obj = Interview.objects.filter(op_id__id=op_id, htm__in=[logged_user_profile], candidate__candidate_id=i['candidate_id'])[0]
			# 				extra_data = get_htm_specific_data(interview_obj, logged_user_profile)
			# 				temp_dict.update(extra_data)
			# 			except:
			# 				pass
			# 			temp_dict["marks"] = i['final_avg_marks']
			# 			i['flag_by_hiring_manager'].append(temp_dict)
			# 	else:
			# 		# Sending data as HM, HR, SM, CA or SA
			# 		# Get all scheduled interviews for the candidate
			# 		# marks calculation
			# 		avg_marks = []
			# 		total_weightages = []
			# 		for skill in open_position_obj.nskillsets:
			# 			temp_avg_skillset = {}
			# 			temp_avg_skillset["skillset_name"] = skill["skillset_name"]
			# 			temp_avg_skillset["skillset_marks"] = 0
			# 			avg_marks.append(temp_avg_skillset)

			# 			temp_total_weightages = {}
			# 			temp_total_weightages["skillset_name"] = skill["skillset_name"]
			# 			temp_total_weightages["skillset_weightage"] = 0
			# 			total_weightages.append(temp_total_weightages)
			# 		for c_obj in candidate_marks_obj:
			# 			given_by = c_obj.marks_given_by
			# 			try:
			# 				# remove this
			# 				raise ValueError("This is awesome!!")
			# 				htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
			# 				weightage_count = 1
			# 				for idx in range(0, len(position_obj.nskillsets)):
			# 					total_weightages[idx]["skillset_weightage"] += htm_weightage_obj.weightages[idx]["skillset_weightage"]
			# 			except HTMWeightage.DoesNotExist:
			# 				for idx in range(0, len(open_position_obj.nskillsets)):
			# 					total_weightages[idx]["skillset_weightage"] += 10
			# 			except Exception as e:
			# 				print("some error occured while totaling weightages", str(e))
			# 				# remove this later
			# 				for idx in range(0, len(open_position_obj.nskillsets)):
			# 					total_weightages[idx]["skillset_weightage"] += 10
			# 		for c_obj in candidate_marks_obj:
			# 			given_by = c_obj.marks_given_by
			# 			# for calculating avg marks
			# 			try:
			# 				htm_weightage_obj = HTMsDeadline.objects.get(open_position=open_position_obj, htm__id=given_by)
			# 				htm_weightage = htm_weightage_obj.skillset_weightage
			# 			except HTMsDeadline.DoesNotExist:
			# 				htm_weightage = []
			# 				for idx in range(0, len(open_position_obj.nskillsets)):
			# 					htm_weightage.append({"skillset_weightage": 10})
			# 			except Exception as e:
			# 				print("some error occured while totaling weightages", str(e))
			# 				# remove this later
			# 				htm_weightage = []
			# 				for idx in range(0, len(open_position_obj.nskillsets)):
			# 					htm_weightage.append({"skillset_weightage": 10})
			# 			for count in range(0, len(open_position_obj.nskillsets)):
			# 				avg_marks[count]["skillset_marks"] += c_obj.nmarks[count]["skillset_marks"] * htm_weightage[count]["skillset_weightage"]
			# 		print("avg marks after initial cal")
			# 		print(avg_marks)
			# 		if candidate_marks_obj:
			# 			for c_obj in candidate_marks_obj:
			# 				given_by = c_obj.marks_given_by
			# 				try:
			# 					htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
			# 					htm_weightage_1 = htm_weightage_obj.init_qualify_ques_1_weightage
			# 					htm_weightage_2 = htm_weightage_obj.init_qualify_ques_2_weightage
			# 					htm_weightage_3 = htm_weightage_obj.init_qualify_ques_3_weightage
			# 					htm_weightage_4 = htm_weightage_obj.init_qualify_ques_4_weightage
			# 					htm_weightage_5 = htm_weightage_obj.init_qualify_ques_5_weightage
			# 					htm_weightage_6 = htm_weightage_obj.init_qualify_ques_6_weightage
			# 					htm_weightage_7 = htm_weightage_obj.init_qualify_ques_7_weightage
			# 					htm_weightage_8 = htm_weightage_obj.init_qualify_ques_8_weightage
			# 				except Exception as e:
			# 					print(e)
			# 					i['error-in-htm-wightage'] = str(e)
			# 					htm_weightage_1 = 10
			# 					htm_weightage_2 = 10
			# 					htm_weightage_3 = 10
			# 					htm_weightage_4 = 10
			# 					htm_weightage_5 = 10
			# 					htm_weightage_6 = 10
			# 					htm_weightage_7 = 10
			# 					htm_weightage_8 = 10
			# 				marks_dict['init_qualify_ques_1'] = marks_dict['init_qualify_ques_1'] + c_obj.criteria_1_marks * htm_weightage_1
			# 				marks_dict['init_qualify_ques_2'] = marks_dict['init_qualify_ques_2'] + c_obj.criteria_2_marks * htm_weightage_2
			# 				marks_dict['init_qualify_ques_3'] = marks_dict['init_qualify_ques_3'] + c_obj.criteria_3_marks * htm_weightage_3
			# 				marks_dict['init_qualify_ques_4'] = marks_dict['init_qualify_ques_4'] + c_obj.criteria_4_marks * htm_weightage_4
			# 				marks_dict['init_qualify_ques_5'] = marks_dict['init_qualify_ques_5'] + c_obj.criteria_5_marks * htm_weightage_5
			# 				marks_dict['init_qualify_ques_6'] = marks_dict['init_qualify_ques_6'] + c_obj.criteria_6_marks * htm_weightage_6
			# 				marks_dict['init_qualify_ques_7'] = marks_dict['init_qualify_ques_7'] + c_obj.criteria_7_marks * htm_weightage_7
			# 				marks_dict['init_qualify_ques_8'] = marks_dict['init_qualify_ques_8'] + c_obj.criteria_8_marks * htm_weightage_8
			# 			marks_dict['init_qualify_ques_1'] = round(marks_dict['init_qualify_ques_1'] / htm_weightage_1_total, 1)
			# 			marks_dict['init_qualify_ques_2'] = round(marks_dict['init_qualify_ques_2'] / htm_weightage_2_total, 1)
			# 			marks_dict['init_qualify_ques_3'] = round(marks_dict['init_qualify_ques_3'] / htm_weightage_3_total, 1)
			# 			marks_dict['init_qualify_ques_4'] = round(marks_dict['init_qualify_ques_4'] / htm_weightage_4_total, 1)
			# 			marks_dict['init_qualify_ques_5'] = round(marks_dict['init_qualify_ques_5'] / htm_weightage_5_total, 1)
			# 			marks_dict['init_qualify_ques_6'] = round(marks_dict['init_qualify_ques_6'] / htm_weightage_6_total, 1)
			# 			marks_dict['init_qualify_ques_7'] = round(marks_dict['init_qualify_ques_7'] / htm_weightage_7_total, 1)
			# 			marks_dict['init_qualify_ques_8'] = round(marks_dict['init_qualify_ques_8'] / htm_weightage_8_total, 1)
			# 			i['marks'] = marks_dict
			# 			count = 0
			# 			avg_marks = 0
			# 			if marks_dict['init_qualify_ques_1'] not in [0, 0.0]:
			# 				count = count + open_position_obj.init_qualify_ques_weightage_1
			# 				avg_marks = avg_marks + marks_dict['init_qualify_ques_1'] * open_position_obj.init_qualify_ques_weightage_1
			# 			if marks_dict['init_qualify_ques_2'] not in [0, 0.0]:
			# 				count = count + open_position_obj.init_qualify_ques_weightage_2
			# 				avg_marks = avg_marks + marks_dict['init_qualify_ques_2'] * open_position_obj.init_qualify_ques_weightage_2
			# 			if marks_dict['init_qualify_ques_3'] not in [0, 0.0]:
			# 				count = count + open_position_obj.init_qualify_ques_weightage_3
			# 				avg_marks = avg_marks + marks_dict['init_qualify_ques_3'] * open_position_obj.init_qualify_ques_weightage_3
			# 			if marks_dict['init_qualify_ques_4'] not in [0, 0.0]:
			# 				count = count + open_position_obj.init_qualify_ques_weightage_4
			# 				avg_marks = avg_marks + marks_dict['init_qualify_ques_4'] * open_position_obj.init_qualify_ques_weightage_4
			# 			if marks_dict['init_qualify_ques_5'] not in [0, 0.0]:
			# 				count = count + open_position_obj.init_qualify_ques_weightage_5
			# 				avg_marks = avg_marks + marks_dict['init_qualify_ques_5'] * open_position_obj.init_qualify_ques_weightage_5
			# 			if marks_dict['init_qualify_ques_6'] not in [0, 0.0]:
			# 				count = count + open_position_obj.init_qualify_ques_weightage_6
			# 				avg_marks = avg_marks + marks_dict['init_qualify_ques_6'] * open_position_obj.init_qualify_ques_weightage_6
			# 			if marks_dict['init_qualify_ques_7'] not in [0, 0.0]:
			# 				count = count + open_position_obj.init_qualify_ques_weightage_7
			# 				avg_marks = avg_marks + marks_dict['init_qualify_ques_7'] * open_position_obj.init_qualify_ques_weightage_7
			# 			if marks_dict['init_qualify_ques_8'] not in [0, 0.0]:
			# 				count = count + open_position_obj.init_qualify_ques_weightage_8
			# 				avg_marks = avg_marks + marks_dict['init_qualify_ques_8'] * open_position_obj.init_qualify_ques_weightage_8
			# 			i['total_hiring_members'] = open_position_obj.htms.all().count()
			# 			i['marks_given_by'] = candidate_marks_obj.count()
			# 			thumbs_up = 0
			# 			thumbs_down = 0
			# 			hold = 0
			# 			print(count, avg_marks)
			# 			if count:
			# 				i['final_avg_marks'] = round(avg_marks / count, 1)
			# 			else:
			# 				i['final_avg_marks'] = 0.0
			# 			i['he_flag'] = None
			# 			i['flag_by_hiring_manager'] = []
			# 			i['like_count'] = 0
			# 			i['hold_count'] = 0
			# 			i['pass_count'] = 0
			# 			i['golden_glove_count'] = 0
			# 			hm_list = open_position_obj.htms.all()
			# 			for hm in hm_list:
			# 				flag_data = get_htm_flag_data(hm, op_id, i["candidate_id"])
			# 				i['flag_by_hiring_manager'].append(flag_data)
			# 			i['interviews_done'] = candidate_marks_obj.count()
			# 		else:
			# 			i['flag_by_hiring_manager'] = []
			# 			i['marks'] = {}
			# 			i['final_avg_marks'] = 0
			# 			i['total_hiring_members'] = open_position_obj.htms.all().count()
			# 			i['marks_given_by'] = 0
			# 			i['flag'] = 'Not Given'
			# 			i['like_count'] = 0
			# 			i['hold_count'] = 0
			# 			i['pass_count'] = 0
			# 			i['golden_glove_count'] = 0
			# 			hm_list = open_position_obj.htms.all()
			# 			for hm in hm_list:
			# 				flag_data = get_htm_flag_data(hm, op_id, i["candidate_id"])
			# 				i['flag_by_hiring_manager'].append(flag_data)
			# 			continue
			# data = sorted(data, key=lambda i: i['avg_marks'])
			# data.reverse()
			return Response(data, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetSingleOpenPosition(APIView):
	def get(self, request, op_id):
		try:
			position_obj = OpenPosition.objects.get(id=op_id)
			openposition_serializer = OpenPositionSerializer(position_obj)
			data = openposition_serializer.data
			if position_obj.sourcing_deadline:
				data['sourcing_deadline'] = position_obj.sourcing_deadline.strftime("%m-%d-%Y")
			htm_deadlines = []
			for deadline in HTMsDeadline.objects.filter(open_position=position_obj):
				temp_dict = {}
				temp_dict["deadline"] = deadline.deadline.strftime("%m-%d-%Y")
				temp_dict["htm"] = deadline.htm.id
				temp_dict["weightages"] = deadline.skillset_weightage
				htm_deadlines.append(temp_dict)
			data["htm_deadlines"] = htm_deadlines
			data['withdrawed_members'] = position_obj.withdrawed_members.all().values_list("id", flat=True)
			if position_obj.kickoff_start_date:
				data['kickoff_start_date'] = position_obj.kickoff_start_date.strftime("%m-%d-%Y")
			if position_obj.target_deadline:
				data['target_deadline'] = position_obj.target_deadline.strftime("%m-%d-%Y")
				now = datetime.today().date()
				candidates_obj = []
				for cao in CandidateAssociateData.objects.filter(open_position__id=op_id, accepted=True, withdrawed=False):
					candidates_obj.append(cao.candidate)
				members_list = position_obj.htms.all()
				for member in members_list:
					try:
						interview_taken = CandidateMarks.objects.filter(op_id=position_obj.id, marks_given_by=member.id).count()
						if interview_taken <= len(candidates_obj):
							data['deadline'] = True
					except:
						pass
				delta = position_obj.target_deadline - now
				if delta.days < 0 and position_obj.target_deadline == False:
					data['deadline'] = True
				
			candidates_objs = []
			for cao in CandidateAssociateData.objects.filter(open_position__id=op_id, accepted=True, withdrawed=False):
				candidates_objs.append(cao.candidate.candidate_id)
			data['total_candidates'] = len(candidates_objs)
			if "is_htm" in request.user.profile.roles:
				marks_given_to = CandidateMarks.objects.filter(candidate_id__in=candidates_objs, op_id=op_id, marks_given_by=request.user.profile.id)
				data['interviews_to_complete'] = len(candidates_objs) - marks_given_to.count()
				data['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
				data['voting_history_holds'] = marks_given_to.filter(hold=True).count()
				data['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
			else:
				marks_given_to = CandidateMarks.objects.filter(candidate_id__in=candidates_objs, op_id=op_id)
				data['interviews_to_complete'] = 0
				data['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
				data['voting_history_holds'] = marks_given_to.filter(hold=True).count()
				data['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
			data['delayed'] = False
			data['no_of_hired_positions'] = Hired.objects.filter(op_id=op_id).count()
			try:
				data["formated_target_deadline"] = position_obj.target_deadline.strftime("%B %d, %Y")
			except Exception as e:
				print(e)
			data["skillsets"] = position_obj.nskillsets
			response = {}
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GetAllOPData(APIView):
	
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, op_id):
		try:
			position_obj = OpenPosition.objects.get(id=op_id)
			openposition_serializer = OpenPositionSerializer(position_obj)
			data = openposition_serializer.data
			docs = []
			for j in PositionDoc.objects.filter(openposition__id=op_id):
				docs.append(j.file.url)
			data['documentations'] = docs
			candidates_objs = []
			candidate_ids = []
			for cao in CandidateAssociateData.objects.filter(open_position__id=op_id, accepted=True, withdrawed=False):
				candidates_objs.append(cao.candidate)
				candidate_ids.append(cao.candidate.candidate_id)
			
			if "is_htm" in request.user.profile.roles:
				marks_given_to = CandidateMarks.objects.filter(candidate_id__in=candidate_ids, op_id=op_id, marks_given_by=request.user.profile.id)
				data['interviews_to_complete'] = len(candidate_ids) - marks_given_to.count()
				data['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
				data['voting_history_golden'] = marks_given_to.filter(golden_gloves=True).count()
				data['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
			else:
				marks_given_to = CandidateMarks.objects.filter(candidate_id__in=candidate_ids, op_id=op_id)
				data['interviews_to_complete'] = 0
				data['voting_history_likes'] = marks_given_to.filter(thumbs_up=True).count()
				data['voting_history_golden'] = marks_given_to.filter(golden_gloves=True).count()
				data['voting_history_passes'] = marks_given_to.filter(thumbs_down=True).count()
			data['total_candidates'] = len(candidate_ids)
			data['no_of_hired_positions'] = Hired.objects.filter(op_id=op_id).count()
			data['no_of_hireds'] = Hired.objects.filter(op_id=op_id).count()
			data["special_intruction"] = "some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name"
			data["special_intruction"] = "some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name some name"
			# get_candidate data
			candidate_data = []
			print(candidates_objs)
			for can in candidates_objs:
				try:
					temp_can = {}
					temp_can["associated_data"] = {}
					try:
						cao = CandidateAssociateData.objects.get(candidate=can, open_position=position_obj)
						temp_can["location"] = cao.location
						temp_can["work_auth"] = cao.work_auth
						temp_can["remote_only"] = cao.remote_only
						temp_can["remote_pref"] = cao.remote_pref
						temp_can["office_only"] = cao.office_only
						temp_can["some_in_office"] = cao.some_in_office
						temp_can["nickname"] = cao.nickname
						temp_can["current_position"] = cao.currently
						temp_can["salary_req"] = cao.salary_req
						temp_can["desired_work_location"] = cao.desired_work_location
						temp_can["comments"] = cao.comments
						temp_can["resume"] = can.documents
						temp_can["references"] = can.references
					except Exception as e:
						print(e)
						temp_can["location"] = can.location
						temp_can["work_auth"] = can.work_auth
						temp_can["remote_only"] = "Not Specified"
						temp_can["remote_pref"] = "Not Specified"
						temp_can["some_in_office"] = "Not Specified"
						temp_can["office_only"] = "Not Specified"
						temp_can["office_only"] = "Not Specified"
						temp_can["office_only"] = "Not Specified"
						temp_can['currency'] = can.currency
						temp_can["salary_req"] = can.salaryRange
						temp_can["desired_work_location"] = can.desired_work_location
						temp_can["comments"] = can.comments
						temp_can["resume"] = can.documents
						temp_can["references"] = can.references
					temp_can["candidate_id"] = can.candidate_id
					temp_can["name"] = can.name
					temp_can["email"] = can.email
					temp_can["linkedin"] = can.skype_id
					temp_can["last_name"] = can.last_name
					temp_can["updated_at"] = can.updated_at
					eval_objs = EvaluationComment.objects.filter(position=position_obj, candidate=can)
					eval_data = []
					for e in eval_objs:
						t_data = {}
						t_data["notes"] = e.notes
						t_data["date"] = str(e.date)
						t_data["position"] = e.position.position_title
						t_data["given_by"] = e.given_by.user.get_full_name()
						t_data["given_by_pic"] = e.given_by.profile_photo.url if str(e.given_by.profile_photo) not in ["", "None", "null"] else None
						eval_data.append(t_data)
					temp_can["full_name"] = "{} {}".format(can.name, can.last_name)
					temp_can["eval_notes"] = eval_data
					temp_can["offers"] = Offered.objects.filter(candidate_id=can.candidate_id).count()
					temp_can["interviews_last_30"] = Interview.objects.filter(candidate=can).count()
					temp_can["profile_photo"] = get_candidate_profile(can)
					# get hire status
					if Hired.objects.filter(candidate_id=can.candidate_id, op_id=op_id):
						temp_can['isHired'] = True
					else:
						temp_can['isHired'] = False
						# Check Candidate Marks Code from here
					# Get all scheduled interviews for the candidate
					HM_vote = {}
					members_list = position_obj.htms.all()
					candidate_marks_obj = CandidateMarks.objects.filter(candidate_id=can.candidate_id, op_id=op_id)
					marks_by_htms = []
					# for calculation avg marks
					avg_marks = []
					total_weightages = []
					for skill in position_obj.nskillsets:
						temp_avg_skillset = {}
						temp_avg_skillset["skillset_name"] = skill["skillset_name"]
						temp_avg_skillset["skillset_marks"] = 0
						avg_marks.append(temp_avg_skillset)

						temp_total_weightages = {}
						temp_total_weightages["skillset_name"] = skill["skillset_name"]
						temp_total_weightages["skillset_weightage"] = 0
						total_weightages.append(temp_total_weightages)
					# calculates total weightage of htms
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						try:
							# remove this
							raise ValueError("This is awesome!!")
							htm_weightage_obj = HTMWeightage.objects.get(op_id=op_id, htm_id=given_by)
							weightage_count = 1
							for idx in range(0, len(position_obj.nskillsets)):
								total_weightages[idx]["skillset_weightage"] += htm_weightage_obj.weightages[idx]["skillset_weightage"]
						except HTMWeightage.DoesNotExist:
							for idx in range(0, len(position_obj.nskillsets)):
								total_weightages[idx]["skillset_weightage"] += 10
						except Exception as e:
							print("some error occured while totaling weightages", str(e))
							# remove this later
							for idx in range(0, len(position_obj.nskillsets)):
								total_weightages[idx]["skillset_weightage"] += 10
					# part of avg marks calculation algo
					for c_obj in candidate_marks_obj:
						given_by = c_obj.marks_given_by
						marks_by_htms.append(c_obj.nmarks)
						# for calculating avg marks
						try:
							htm_weightage_obj = HTMsDeadline.objects.get(open_position=position_obj, htm__id=given_by)
							htm_weightage = htm_weightage_obj.skillset_weightage
						except HTMsDeadline.DoesNotExist:
							htm_weightage = []
							for idx in range(0, len(position_obj.nskillsets)):
								htm_weightage.append({"skillset_weightage": 10})
						except Exception as e:
							print("some error occured while totaling weightages", str(e))
							# remove this later
							htm_weightage = []
							for idx in range(0, len(position_obj.nskillsets)):
								htm_weightage.append({"skillset_weightage": 10})
						for count in range(0, len(position_obj.nskillsets)):
							avg_marks[count]["skillset_marks"] += c_obj.nmarks[count]["skillset_marks"] * htm_weightage[count]["skillset_weightage"]
					print("avg marks after initial cal")
					print(avg_marks)
					# Calculate avg marks
					if candidate_marks_obj:
						overall_avg_marks = 0
						total_position_weightage = 0
						for idx in range(0, len(position_obj.nskillsets)):
							avg_marks[idx]["skillset_marks"] = round(avg_marks[idx]["skillset_marks"] / total_weightages[idx]["skillset_weightage"], 1)
							overall_avg_marks += avg_marks[idx]["skillset_marks"] * position_obj.nskillsets[idx]["skillset_weightage"]
							total_position_weightage += position_obj.nskillsets[idx]["skillset_weightage"]
							print(overall_avg_marks, total_position_weightage)
						if total_position_weightage:
							temp_can['avg_marks'] = round(overall_avg_marks / total_position_weightage, 1)
						else:
							temp_can['avg_marks'] = 0.0
					else:
						temp_can['avg_marks'] = 0.0
					temp_can["marks_by_htms"] = marks_by_htms
					candidate_data.append(temp_can)
				except Exception as e:
					print(str(e), "candidate")
			candidate_data = sorted(candidate_data, key=lambda i: i['isHired'], reverse=True)
			candidate_data = sorted(candidate_data, key=lambda i: i['avg_marks'], reverse=True)
			data["candidates_data"] = candidate_data
			response = {}
			response['data'] = data
			return Response(response, status=status.HTTP_200_OK)
		except Exception as e:
			return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

