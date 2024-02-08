import csv
from django.contrib.auth.models import User
from dashboard.models import Profile
import json

def backup_users():
    fobj = open("users.csv", "w")
    csv_writer = csv.writer(fobj)
    for i in User.objects.all().exclude(username="superadmin"):
        row = [
            i.id,
            i.username,
            i.first_name,
            i.last_name,
            i.password
        ]
        csv_writer.writerow(row)
    fobj.close()

def restore_users():
    fobj = open("users.csv", "r")
    csv_reader = csv.reader(fobj)
    for row in csv_reader:
        User.objects.create(
            username=row[1],
            first_name=row[2],
            last_name=row[3],
            password=row[4]
        )

def backup_profile():
    fobj = open("profiles.csv", "w")
    csv_writer = csv.writer(fobj)
    
    for i in Profile.objects.all().exclude(user__username="superadmin"):
        row = [
            i.user.username,
            i.phone_number,
            i.cell_phone,
            i.skype_id,
            i.email,
            i.job_title,
            json.dumps(i.roles),
            i.is_candidate,
            i.client,
            i.color,
            json.dumps(json.loads(i.rankings)),
            i.tnc_accepted,
            i.profile_photo,
            json.dumps(i.notification_data),
            i.first_log,
            i.cognito_id,
            i.iotum_host_id,
            i.customer_id
        ]
        csv_writer.writerow(row)
    fobj.close()

def restore_profile():
    fobj = open("profiles.csv", "r")
    csv_reader = csv.reader(fobj)
    for row in csv_reader:
        try:
            user_obj = User.objects.get(username=row[0])
        except:
            continue
        Profile.objects.create(
            user=user_obj,
            phone_number=row[1],
            cell_phone=row[1],
            skype_id=row[1],
            email=row[1],
            job_title=row[1],
            roles=row[1],
            is_candidate=row[1],
            client=row[1],
            phone_number=row[1],
            phone_number=row[1],
            phone_number=row[1],
            phone_number=row[1],
        )
